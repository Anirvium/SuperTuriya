from __future__ import annotations

import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path

from .agent import Agent
from .artifacts import Journal, atomic_json, provenance
from .config import Config
from .observation import Observation
from .provider import LocalModel


def clean_score(value):
    if isinstance(value, dict):
        return {k: clean_score(v) for k, v in value.items() if k not in {"api_key", "guid"}}
    if isinstance(value, list):
        return [clean_score(v) for v in value]
    return value


def arcade(mode, environments, recordings, gateway=None):
    from arc_agi import Arcade, OperationMode
    logger = logging.getLogger("superturiya.arc_agi.sdk")
    logger.setLevel(logging.ERROR)
    args = {"operation_mode": OperationMode(mode), "environments_dir": str(environments),
            "recordings_dir": str(recordings), "logger": logger}
    if mode == "competition":
        if gateway != "http://gateway:8001":
            raise ValueError("competition runner is restricted to the Kaggle gateway")
        args.update(arc_base_url=gateway, arc_api_key="test-key-123")
    return Arcade(**args)


def play_game(env, config, journal, provider=None, deadline=None):
    from arcengine import GameAction
    start = time.monotonic()
    deadline = min(deadline or start+config.game_seconds, start+config.game_seconds)
    agent = Agent(config, journal, provider, deadline)
    actions = resets = 0
    observation = None
    reason = "action_limit"
    error = None
    try:
        raw = env.observation_space
        if raw is None:
            raw = env.reset()
            actions += 1
        observation = Observation.from_frame(raw)
        agent.observe(observation)
        while actions < config.max_actions:
            if observation.state == "WIN":
                reason = "win"
                break
            if time.monotonic() >= deadline:
                reason = "time_limit"
                break
            if observation.state == "GAME_OVER" and resets >= config.max_resets:
                reason = "reset_limit"
                break
            action = agent.choose(observation)
            if time.monotonic() >= deadline:
                reason = "time_limit"
                break
            if action.id == 0 and observation.state == "GAME_OVER":
                resets += 1
            data = {"x": action.x, "y": action.y} if action.id == 6 else {}
            # Exactly one real environment call. Never retry an ambiguous step.
            raw = env.step(GameAction.from_id(action.id), data=data,
                           reasoning={"agent": "superturiya", "profile": config.profile})
            actions += 1
            observation = Observation.from_frame(raw)
            agent.observe(observation)
        if observation and observation.state == "WIN":
            reason = "win"
    except Exception as exc:
        reason, error = "error", f"{type(exc).__name__}: {str(exc)[:300]}"
        journal.write("runtime_error", error=error)
    result = {"state": observation.state if observation else None,
              "levels_completed": observation.level if observation else 0,
              "actions": actions, "resets": resets, "seconds": time.monotonic()-start,
              "stop_reason": reason, "error": error, "agent_stats": dict(agent.stats),
              "rule_rejections": agent.world.rejections, "rule_revocations": agent.world.revocations}
    journal.write("game_end", **result)
    return result


def run(config: Config, output: Path, environments: Path, game_ids=None, mode="offline",
        gateway=None, provider=None, sdk=None, run_deadline=None):
    """One scorecard, one make per selected game; all games remain in the report."""
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    run_deadline = min(run_deadline or started+config.total_seconds, started+config.total_seconds)
    execution_deadline = run_deadline-config.reserve_seconds
    report = {"schema": "superturiya-arc-agi-run-v1", "provenance": provenance(),
              "config": config.to_dict(), "mode": mode, "games": [], "status": "running",
              "scorecard": None, "scorecard_error": None}
    atomic_json(output/"report.json", report)
    arc = sdk or arcade(mode, environments, output/"sdk_recordings", gateway)
    available = sorted(e.game_id for e in arc.get_environments())
    if not available:
        raise ValueError("no environments found; run the cache command first")
    if mode == "competition" and game_ids:
        raise ValueError("competition runs must include all gateway environments")
    if game_ids:
        selected = []
        for wanted in game_ids:
            matches = [g for g in available if g == wanted or ("-" not in wanted and g.split("-")[0] == wanted)]
            if len(matches) != 1:
                raise ValueError(f"game id must resolve to exactly one version: {wanted}")
            selected.extend(matches)
        if len(selected) != len(set(selected)):
            raise ValueError("duplicate games are not allowed")
    else:
        selected = available
    report["selected_games"] = selected
    report["available_game_count"] = len(available)
    report["evaluation_scope"] = "all_available" if len(selected) == len(available) else "selected_subset"
    if config.profile not in {"random", "explore"}:
        provider = provider or LocalModel(config)
    scorecard_id = None
    report_lock = threading.Lock()
    game_results: list[dict | None] = [None] * len(selected)

    def persist(index, entry):
        with report_lock:
            game_results[index] = entry
            report["games"] = [item for item in game_results if item is not None]
            atomic_json(output/"report.json", report)
            print(json.dumps({"game": entry["game_id"],
                              "levels": entry["levels_completed"],
                              "actions": entry["actions"],
                              "stop": entry["stop_reason"]}), flush=True)

    def play_indexed(index, game_id):
        remaining = execution_deadline-time.monotonic()
        if remaining <= 0:
            return {"game_id": game_id, "stop_reason": "global_time_limit", "error": None,
                    "levels_completed": 0, "actions": 0, "resets": 0, "seconds": 0,
                    "state": None, "agent_stats": {}}
        seconds = min(config.game_seconds, remaining)
        journal = Journal(output/f"game-{index:03d}.jsonl")
        journal.write("game_start", game_id=game_id, config=config.to_dict(), budget_seconds=seconds)
        try:
            env = arc.make(game_id, seed=config.seed+index, scorecard_id=scorecard_id)
            if env is None:
                raise RuntimeError("SDK could not create environment")
            result = play_game(env, replace(config, game_seconds=seconds), journal, provider,
                               min(execution_deadline, time.monotonic()+seconds))
        except Exception as exc:
            result = {"stop_reason": "error", "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                      "levels_completed": 0, "actions": 0, "resets": 0, "seconds": 0,
                      "state": None, "agent_stats": {}}
            journal.write("runtime_error", **result)
        finally:
            journal.close()
        result["journal_events"] = journal.sequence
        result["journal_tip"] = journal.previous
        return {"game_id": game_id, "journal": f"game-{index:03d}.jsonl", **result}

    try:
        scorecard_id = arc.open_scorecard(tags=["superturiya", config.profile])
        workers = min(config.max_parallel_games, len(selected))
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="arc-game") as executor:
            futures = {executor.submit(play_indexed, index, game_id): index
                       for index, game_id in enumerate(selected)}
            for future in as_completed(futures):
                index = futures[future]
                try:
                    entry = future.result()
                except Exception as exc:
                    entry = {"game_id": selected[index], "stop_reason": "error",
                             "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                             "levels_completed": 0, "actions": 0, "resets": 0,
                             "seconds": 0, "state": None, "agent_stats": {}}
                persist(index, entry)
    finally:
        if scorecard_id:
            try:
                scorecard = arc.close_scorecard(scorecard_id)
                if scorecard is None:
                    raise RuntimeError("SDK returned no closed scorecard")
                report["scorecard"] = clean_score(scorecard.model_dump(mode="json"))
            except Exception as exc:
                report["scorecard_error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
        report["seconds"] = time.monotonic()-started
        report["game_error_count"] = sum(g["stop_reason"] == "error" for g in report["games"])
        report["status"] = "complete" if (len(report["games"]) == len(selected)
            and not report["scorecard_error"]) else "incomplete"
        if provider:
            report["model_usage"] = {"calls": provider.calls, **provider.tokens}
        atomic_json(output/"report.json", report)
    return report
