from __future__ import annotations

import json
import random
import time
from collections import Counter, deque
from dataclasses import asdict

from .config import Config
from .observation import Action, Observation, delta, objects
from .programs import ProgramExecutor, WorldModel
from .provider import ProviderError, grid_image, parse_response


SYSTEM = """You are an autonomous agent in a novel, deterministic visual environment.
Infer controls, mechanics, and goals from observations. The objective is to complete
all levels with few real actions. No game source, hidden state or answer is available.
Use only available_actions. ACTION6 is a click at integer x,y in 0..63; ACTION7 is
undo when available. Directions usually correspond to 1 up,2 down,3 left,4 right;
infer actual effects. RESET is managed by the runner. Preserve useful causal rules,
goals and coordinate conventions in notes. Avoid repeating ineffective actions.
Reason internally, then return one JSON object, without markdown:
{"actions":[{"id":1}],"notes":"compact rules, evidence, uncertainties, next goal",
 "reason":"brief evidence for the action"}.
Actions may have x,y only for id 6. Propose at most 4 actions. You can supply
"expected_grids": [grid_after_action1,...] to make plans falsifiable.
Instead of acting, request pure computation with {"analyze":"def analyze(data):\\n ..."}.
The data object contains observation, transitions (before/action/after), notes,
and optional world_model. Use computation for board parsing, search, counting,
testing candidate rules or planning. Return a small JSON-compatible result.
Python supports basic builtins, list/dict/set methods and sqrt. No imports,
filesystem, network, introspection, printing, environment calls or hidden state.
Computation has a short timeout. Do not use tools for trivial calculations.
All coordinates in grids use grid[y][x]. Component candidates may be misleading.
"""

REPAIR_SYSTEM = """
You may also propose "world_model":"def predict(grid, action):\\n ..." alongside
actions. It must predict the entire NEXT visible grid given grid and an action dict.
Use observed counterexamples to repair the smallest incorrect rule. The runner
checks all retained same-level transitions and rejects regressions. A consistent
program is provisional until two nontrivial future predictions succeed. Predictions
can be revoked at any time; they are not an oracle. Do not invent game-specific
rules without evidence. World-model programs reset between levels.
"""


class Agent:
    """Consumes observations only; the runner owns the environment and scoring."""
    def __init__(self, config: Config, journal, provider=None, deadline=None):
        self.config, self.journal, self.provider = config, journal, provider
        self.deadline = deadline if deadline is not None else time.monotonic()+config.game_seconds
        self.rng = random.Random(config.seed)
        self.notes = ""
        self.transitions = deque(maxlen=32)
        self.history = deque(maxlen=256)
        self.visits = Counter()
        self.no_effect = Counter()
        self.plan = deque()
        self.last_observation = None
        self.last_action = None
        self.prediction = None
        self.pending_expected = None
        self.executor = ProgramExecutor(config.tool_seconds, config.max_program_chars)
        self.world = WorldModel(self.executor, config.min_rule_examples)
        self.stats = Counter()
        self.failure_streak = 0
        self.model_disabled = False

    def remaining(self):
        return max(0.0, self.deadline-time.monotonic())

    def observe(self, observation: Observation):
        self.journal.write("observation", observation=observation.to_dict(), hash=observation.key)
        before = self.last_observation
        if before is not None and self.last_action is not None:
            transition = {"before": before.grid, "action": self.last_action.to_dict(),
                          "after": observation.grid, "level": before.level,
                          "next_level": observation.level, "state": observation.state,
                          "delta": delta(before.grid, observation.grid)}
            self.history.append(transition)
            same_level = before.level == observation.level and self.last_action.id != 0
            if same_level and observation.state == "NOT_FINISHED":
                self.transitions.append(transition)
            if before.key == observation.key:
                self.no_effect[(before.key, self.last_action.key)] += 1
            prediction = self.prediction if self.prediction is not None else self.pending_expected
            if prediction is not None and prediction != observation.grid:
                self.plan.clear()
                self.stats["prediction_mismatches"] += 1
                self.journal.write("counterexample", action=self.last_action.to_dict(),
                                   difference=delta(prediction, observation.grid))
            if same_level:
                evidence = self.world.observe(before.grid, self.prediction, observation.grid)
                if evidence:
                    self.journal.write("rule_evidence", **evidence)
            if not same_level or observation.state in {"WIN", "GAME_OVER"}:
                self.plan.clear()
                self.transitions.clear()
                self.world.rule = None
            self.prediction = self.pending_expected = None
        self.last_observation = observation
        self.last_action = None

    def _fallback(self, obs, uniform=False):
        if not obs.available:
            raise ValueError("no legal action in active state")
        candidates = [Action(a) for a in obs.available if a != 6]
        if 6 in obs.available:
            points = [o["point"] for o in objects(obs.grid, 64)]
            if uniform:
                points = [[self.rng.randrange(64), self.rng.randrange(64)]]
            # Include spatial coverage: background can contain meaningful controls.
            points += [[x, y] for y in range(4, 64, 16) for x in range(4, 64, 16)]
            candidates += [Action(6, x, y) for x, y in dict.fromkeys(map(tuple, points))]
        if uniform:
            # Uniform over legal ACTION IDs, then uniform coordinates for a click.
            aid = self.rng.choice(obs.available)
            return Action(6, self.rng.randrange(64), self.rng.randrange(64)) if aid == 6 else Action(aid)
        self.rng.shuffle(candidates)
        return min(candidates, key=lambda a: self.visits[(obs.key, a.key)]
                   + 2*self.no_effect[(obs.key, a.key)] + (0.25 if a.id == 7 else 0))

    def _data(self, obs):
        history = list(self.history)
        summaries = [{"action": t["action"], "delta": t["delta"], "level": t["level"],
                      "next_level": t["next_level"], "state": t["state"]}
                     for t in history[-self.config.recent_transitions:]]
        data = {"observation": obs.to_dict(), "components": objects(obs.grid),
                "recent": summaries, "notes": self.notes if self.config.profile != "reactive" else "",
                "budget": {"seconds_left": round(self.remaining(), 1),
                           "model_calls_left": self.config.max_model_calls-self.stats["model_calls"]}}
        if self.config.profile == "repair" and self.world.rule:
            data["world_model"] = asdict(self.world.rule)
        while len(json.dumps(data, separators=(",", ":"))) > self.config.context_chars:
            if data["recent"]:
                data["recent"].pop(0)
            elif data["components"]:
                data["components"] = data["components"][:len(data["components"])//2]
            elif data["notes"]:
                data["notes"] = data["notes"][:len(data["notes"])//2]
            elif "world_model" in data:
                data.pop("world_model")
            else:
                raise ValueError("context budget cannot hold current observation")
        return data

    def _model_action(self, obs):
        data = self._data(obs)
        text = json.dumps(data, separators=(",", ":"))
        user = text
        if self.config.vision:
            user = [{"type": "text", "text": text},
                    {"type": "image_url", "image_url": {"url": grid_image(obs.grid)}}]
        messages = [{"role": "system", "content": SYSTEM + (REPAIR_SYSTEM if self.config.profile == "repair" else "")},
                    {"role": "user", "content": user}]
        for round_index in range(self.config.max_tool_rounds+1):
            if self.remaining() < 0.1 or self.stats["model_calls"] >= self.config.max_model_calls:
                raise ProviderError("model budget exhausted")
            self.stats["model_calls"] += 1
            content, usage = self.provider.complete(messages, self.remaining())
            self.journal.write("model_response", content=content, **usage)
            try:
                response = parse_response(content)
                if "analyze" in response:
                    if round_index == self.config.max_tool_rounds:
                        raise ValueError("tool-round budget exhausted; return actions")
                    tool_data = {"observation": obs.to_dict(), "notes": self.notes,
                                 "transitions": list(self.history)[-48:],
                                 "world_model": self.world.rule.source if self.world.rule else None}
                    result = self.executor.run(response["analyze"], "analyze", [[tool_data]], self.remaining())
                    self.stats["tool_calls"] += 1
                    self.journal.write("tool_result", result=result)
                    rendered = json.dumps(result)
                    if len(rendered) > 10000:
                        rendered = json.dumps({"ok": False, "error": "result too large; return a concise summary"})
                    messages += [{"role": "assistant", "content": content[:self.config.max_program_chars+1000]},
                                 {"role": "user", "content": rendered}]
                    continue
                raw_actions = response.get("actions")
                if not isinstance(raw_actions, list) or not raw_actions:
                    raise ValueError("actions must be a nonempty list")
                plan = [Action.parse(a, obs.available) for a in raw_actions[:self.config.plan_length]]
                notes = response.get("notes", "")
                if not isinstance(notes, str):
                    raise ValueError("notes must be a string")
                if self.config.profile != "reactive":
                    self.notes = notes[:4000]
                if self.config.profile == "repair" and "world_model" in response:
                    proposal = self.world.propose(response["world_model"], list(self.transitions), self.remaining())
                    self.journal.write("rule_proposal", result=proposal, source=response["world_model"])
                expected = response.get("expected_grids", [])
                if not isinstance(expected, list):
                    raise ValueError("expected_grids must be a list")
                from .observation import grid_value
                expected = [grid_value(g) for g in expected[:len(plan)]]
                self.plan.extend((a, expected[i] if i < len(expected) else None) for i, a in enumerate(plan))
                self.failure_streak = 0
                self.journal.write("plan", actions=[a.to_dict() for a in plan], notes=self.notes,
                                   reason=str(response.get("reason", ""))[:2000])
                return self.plan.popleft()
            except (ValueError, TypeError) as exc:
                self.stats["invalid_model_responses"] += 1
                self.journal.write("schema_error", error=str(exc)[:300])
                if round_index == self.config.max_tool_rounds:
                    raise ProviderError("model did not return a valid action") from exc
                messages += [{"role": "assistant", "content": content[:8000]},
                             {"role": "user", "content": f"Invalid response: {exc}. Return valid JSON actions now."}]
        raise ProviderError("tool loop produced no action")

    def choose(self, obs: Observation):
        if obs.state in {"NOT_PLAYED", "GAME_OVER"}:
            self.plan.clear()
            action, expected, source = Action(0), None, "lifecycle"
        elif self.config.profile in {"random", "explore"}:
            action, expected, source = self._fallback(obs, self.config.profile == "random"), None, self.config.profile
        else:
            while self.plan:
                candidate, expected = self.plan.popleft()
                if candidate.id in obs.available:
                    action, source = candidate, "plan"
                    break
                self.plan.clear()
            else:
                if self.stats["model_calls"] >= self.config.max_model_calls:
                    self.model_disabled = True
                if self.model_disabled:
                    action, expected, source = self._fallback(obs), None, "fallback_disabled"
                else:
                    try:
                        action, expected = self._model_action(obs)
                        source = "model"
                    except ProviderError as exc:
                        self.failure_streak += 1
                        self.stats["model_errors"] += 1
                        self.journal.write("model_error", error=str(exc))
                        if self.failure_streak >= 3:
                            self.model_disabled = True
                            self.journal.write("model_disabled", reason="three consecutive failures")
                        action, expected, source = self._fallback(obs), None, "fallback"
        self.last_action = action
        self.pending_expected = expected
        if self.config.profile == "repair" and action.id != 0:
            self.prediction = self.world.predict(obs.grid, action.to_dict(), self.remaining())
        self.visits[(obs.key, action.key)] += 1
        self.stats["decisions"] += 1
        self.stats[f"source_{source}"] += 1
        self.journal.write("action", action=action.to_dict(), source=source,
                           prediction=self.prediction, expected=expected)
        return action
