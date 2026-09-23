from __future__ import annotations

import importlib.util
import json
import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from superturiya_arc.agent import Agent
from superturiya_arc.artifacts import Journal, verify_journal
from superturiya_arc.config import Config
from superturiya_arc.diagnostics import diagnose_run
from superturiya_arc.evaluation import compare, create_split, load_split
from superturiya_arc.notebook import build
from superturiya_arc.observation import Action, Observation, objects
from superturiya_arc.programs import ProgramExecutor, WorldModel
from superturiya_arc.provider import ProviderError, parse_response


class Log:
    def __init__(self):
        self.events = []

    def write(self, kind, **payload):
        self.events.append({"kind": kind, **payload})


class ScriptedModel:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = 0
        self.tokens = {}
        self.messages = []

    def complete(self, messages, timeout):
        self.messages.append(messages.copy())
        self.calls += 1
        return next(self.responses), {"usage": {}, "seconds": 0, "model": "fixture"}


class FailingModel:
    calls = 0

    def complete(self, messages, timeout):
        self.calls += 1
        raise ProviderError("fixture failure")


def observation(grid=None, level=0, available=(1, 2, 3, 4, 6), state="NOT_FINISHED"):
    return Observation(grid or [[0, 1], [0, 0]], state, level, available)


class Arc3ContractTests(unittest.TestCase):
    def test_competition_ablation_changes_only_profile(self):
        root = Path(__file__).resolve().parents[1]
        memory = Config.load(root/"configs"/"competition.json").to_dict()
        repair = Config.load(root/"configs"/"repair-ablation.json").to_dict()
        self.assertEqual(
            {key: (memory[key], repair[key]) for key in memory if memory[key] != repair[key]},
            {"profile": ("memory", "repair")},
        )

    def test_diagnostics_flag_repeated_no_effect_exploration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            journal = Journal(root/"game-000.jsonl")
            journal.write("game_start", game_id="test-v1")
            journal.write("observation", hash="same")
            journal.write("action", action={"id": 1}, source="model")
            journal.write("observation", hash="same")
            journal.write(
                "game_end",
                levels_completed=0,
                actions=1,
                stop_reason="action_limit",
            )
            journal.close()
            (root/"report.json").write_text(json.dumps({
                "config": {"profile": "memory"},
                "scorecard": {"score": 0.0},
                "games": [{"game_id": "test-v1", "journal": "game-000.jsonl"}],
            }))

            result = diagnose_run(root)
            self.assertEqual(result["signal_counts"], {"exploration": 1})
            self.assertEqual(result["games"][0]["unchanged_transition_rate"], 1.0)

    def test_only_available_actions_and_valid_clicks(self):
        for payload in ({"id": 7}, {"id": True}, {"id": 6, "x": -1, "y": 0},
                        {"id": 6, "x": 1.5, "y": 0}, {"id": 1, "x": 2}, {"id": 0}):
            with self.assertRaises(ValueError):
                Action.parse(payload, (1, 6))
        self.assertEqual(Action.parse({"id": 6, "x": 63, "y": 0}, (6,)).x, 63)

    def test_external_endpoints_and_bad_budgets_rejected(self):
        for endpoint in ("https://api.example.com/v1", "http://127.0.0.1.evil/v1", "http://u:p@localhost/v1"):
            with self.assertRaises(ValueError):
                Config(endpoint=endpoint)
        for kwargs in ({"max_actions": 0}, {"total_seconds": float("nan")},
                       {"reserve_seconds": 99999}, {"max_tokens": 3.5},
                       {"top_p": 0}, {"max_parallel_games": 33}):
            with self.assertRaises(ValueError):
                Config(**kwargs)

    def test_observation_does_not_project_hidden_fields(self):
        frame = SimpleNamespace(frame=[[[1]]], state=SimpleNamespace(name="NOT_FINISHED"),
                                levels_completed=0, available_actions=[1], hidden_answer="secret")
        self.assertNotIn("secret", json.dumps(Observation.from_frame(frame).to_dict()))

    def test_component_click_is_inside_shape(self):
        grid = [[0]*5 for _ in range(5)]
        for x, y in ((1,1),(2,1),(3,1),(1,2),(3,2),(1,3),(2,3),(3,3)):
            grid[y][x] = 2
        for item in objects(grid):
            x, y = item["point"]
            self.assertEqual(grid[y][x], item["color"])

    def test_json_fences_are_supported_not_arbitrary_text(self):
        self.assertEqual(parse_response('```json\n{"actions": [{"id": 1}]}\n```')["actions"][0]["id"], 1)
        with self.assertRaises(ValueError):
            parse_response("I think {\"actions\": []}")

    def test_journal_detects_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"events.jsonl"
            journal = Journal(path)
            journal.write("observation", value=1)
            journal.write("action", value=2)
            journal.close()
            self.assertEqual(verify_journal(path)["events"], 2)
            path.write_text(path.read_text().replace('"value": 1', '"value": 9'))
            with self.assertRaises(ValueError):
                verify_journal(path)

    def test_split_keeps_versions_together_and_is_immutable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"split.json"
            split = create_split(["aa00-v1", "aa00-v2", "bb00-v1", "cc00-v1"], path)
            self.assertTrue(any("aa00-v1" in split[p] and "aa00-v2" in split[p] for p in ("development", "holdout")))
            self.assertEqual(load_split(path, "holdout"), split["holdout"])
            with self.assertRaises(ValueError):
                create_split(["aa", "bb"], path)


class Arc3ProgramTests(unittest.TestCase):
    def test_pure_search_program_executes(self):
        code = "def analyze(data):\n    q = [(0, [])]\n    while q:\n        n, path = q.pop(0)\n        if n == data:\n            return path\n        q.append((n+1, path+[1]))"
        result = ProgramExecutor().run(code, "analyze", [[4]])
        self.assertEqual(result, {"ok": True, "values": [[1,1,1,1]]})

    def test_worker_rejects_host_access_and_times_out(self):
        for code in ("import os\ndef analyze(data): return os.environ",
                     "def analyze(data): return data.__class__",
                     "def analyze(data): return open('/etc/passwd').read()"):
            self.assertFalse(ProgramExecutor().run(code, "analyze", [[{}]])["ok"])
        result = ProgramExecutor(seconds=0.2).run("def analyze(data):\n    while True: pass", "analyze", [[{}]])
        self.assertEqual(result["error"], "program timed out")

    def test_rule_requires_evidence_then_future_checks_and_revocation(self):
        world = WorldModel(ProgramExecutor())
        program = "def predict(grid, action):\n    return [[(grid[0][0]+1)%16]]"
        transitions = [{"before": [[i]], "action": {"id": 1}, "after": [[i+1]]} for i in range(4)]
        self.assertFalse(world.propose(program, transitions[:1])["accepted"])
        self.assertTrue(world.propose(program, transitions)["accepted"])
        self.assertEqual(world.rule.status, "provisional")
        world.observe([[4]], [[5]], [[5]])
        world.observe([[5]], [[6]], [[6]])
        self.assertEqual(world.rule.status, "accepted_on_observed_evidence")
        result = world.observe([[6]], [[7]], [[8]])
        self.assertEqual(result["status"], "revoked")
        self.assertIsNone(world.rule)

    def test_bad_repair_cannot_replace_existing_model(self):
        world = WorldModel(ProgramExecutor())
        transitions = [{"before": [[i]], "action": {"id": 1}, "after": [[i+1]]} for i in range(4)]
        good = "def predict(grid, action): return [[grid[0][0]+1]]"
        world.propose(good, transitions)
        self.assertFalse(world.propose("def predict(grid, action): return grid", transitions)["accepted"])
        self.assertEqual(world.rule.source, good)


class Arc3AgentTests(unittest.TestCase):
    def test_reproducible_legal_exploration(self):
        agents = [Agent(Config(profile="explore"), Log()) for _ in range(2)]
        obs = observation(available=(6,))
        sequences = []
        for agent in agents:
            sequence = []
            for _ in range(8):
                agent.observe(obs)
                action = agent.choose(obs)
                self.assertEqual(action.id, 6)
                sequence.append(action)
            sequences.append(sequence)
        self.assertEqual(*sequences)

    def test_invalid_action_repaired_before_environment_use(self):
        provider = ScriptedModel(['{"actions":[{"id":7}]}', '{"actions":[{"id":1}]}'])
        agent = Agent(Config(model="fixture"), Log(), provider)
        obs = observation(available=(1,))
        agent.observe(obs)
        self.assertEqual(agent.choose(obs).id, 1)
        self.assertEqual(agent.stats["invalid_model_responses"], 1)

    def test_program_tool_then_action(self):
        provider = ScriptedModel([json.dumps({"analyze": "def analyze(data): return len(data['observation']['grid'])"}),
                                  '{"actions":[{"id":2}],"notes":"move down"}'])
        agent = Agent(Config(model="fixture"), Log(), provider)
        obs = observation()
        agent.observe(obs)
        self.assertEqual(agent.choose(obs).id, 2)
        self.assertEqual(agent.stats["tool_calls"], 1)

    def test_counterexample_cancels_stale_plan(self):
        provider = ScriptedModel([json.dumps({"actions": [{"id": 1}, {"id": 2}],
                                             "expected_grids": [[[1]]]}), '{"actions":[{"id":3}]}'])
        agent = Agent(Config(model="fixture"), Log(), provider)
        agent.observe(observation())
        agent.choose(observation())
        agent.observe(observation([[2]]))
        self.assertEqual(agent.choose(observation([[2]])).id, 3)
        self.assertEqual(agent.stats["prediction_mismatches"], 1)

    def test_legal_action_change_invalidates_queue(self):
        provider = ScriptedModel(['{"actions":[{"id":1},{"id":2}]}', '{"actions":[{"id":3}]}'])
        agent = Agent(Config(model="fixture"), Log(), provider)
        obs = observation()
        agent.observe(obs)
        agent.choose(obs)
        new = observation(available=(3,))
        agent.observe(new)
        self.assertEqual(agent.choose(new).id, 3)

    def test_repeated_model_failures_degrade_to_legal_fallback(self):
        agent = Agent(Config(model="fixture"), Log(), FailingModel())
        obs = observation(available=(1,))
        for _ in range(4):
            agent.observe(obs)
            self.assertEqual(agent.choose(obs).id, 1)
        self.assertTrue(agent.model_disabled)
        self.assertEqual(agent.stats["model_errors"], 3)


class Arc3PackagingTests(unittest.TestCase):
    def test_nested_kaggle_model_and_dataset_mounts_are_resolved(self):
        from superturiya_arc.notebook import resolve_kaggle_input

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root/"models"/"owner"/"qwen3-8-27b-fp8-repacked-v1"/"1"
            model.mkdir(parents=True)
            (model/"config.json").write_text("{}")
            (model/"weights.safetensors").write_bytes(b"fixture")
            wheels = root/"datasets"/"owner"/"arc3-vllm-h100-wheelhouse-v3"/"versions"/"3"
            wheels.mkdir(parents=True)
            (wheels/"vllm-1.0.whl").write_bytes(b"fixture")

            self.assertEqual(
                resolve_kaggle_input(
                    root, "auto:qwen3-8-27b-fp8-repacked-v1", "config.json", True
                ),
                model,
            )
            self.assertEqual(
                resolve_kaggle_input(
                    root, "auto:arc3-vllm-h100-wheelhouse-v3", "*.whl"
                ),
                wheels,
            )

    def test_notebook_is_offline_and_all_python_cells_compile(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"build"
            build(Config(profile="explore"), path)
            notebook = json.loads((path/"submission.ipynb").read_text())
            metadata = json.loads((path/"kernel-metadata.json").read_text())
            self.assertFalse(metadata["enable_internet"])
            self.assertEqual(metadata["id"], "piyusha1234/notebook5326562b0c")
            self.assertEqual(metadata["machine_shape"], "NvidiaRtxPro6000")
            for entry in notebook["cells"]:
                if entry["cell_type"] == "code":
                    compile(entry["source"], "notebook", "exec")
            with self.assertRaises(ValueError):
                build(Config(profile="explore"), path)

    def test_model_build_fails_without_attached_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                build(Config(model="local"), Path(directory)/"model", accelerator="rtx6000")

    def test_model_build_pins_offline_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"model"
            build(
                Config(profile="memory", model="fixture"),
                path,
                model_path="auto:qwen",
                model_sources=["owner/model/pyTorch/fp8/1"],
                wheel_path="auto:wheelhouse",
                dataset_sources=["owner/wheelhouse"],
            )
            metadata = json.loads((path/"kernel-metadata.json").read_text())
            self.assertEqual(metadata["model_sources"], ["owner/model/pyTorch/fp8/1"])
            self.assertEqual(metadata["dataset_sources"], ["owner/wheelhouse"])

    def test_public_validation_games_are_frozen_in_notebook(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"model"
            build(
                Config(profile="memory", model="fixture"),
                path,
                model_path="auto:qwen",
                model_sources=["owner/model/pyTorch/fp8/1"],
                wheel_path="auto:wheelhouse",
                dataset_sources=["owner/wheelhouse"],
                validation_games=["r11l", "tu93"],
            )
            manifest = json.loads((path/"build-manifest.json").read_text())
            self.assertEqual(manifest["settings"]["validation_games"], ["r11l", "tu93"])
            notebook = json.loads((path/"submission.ipynb").read_text())
            source = "\n".join(cell["source"] for cell in notebook["cells"] if cell["cell_type"] == "code")
            self.assertIn("Public benchmark passed:", source)

            with self.assertRaises(ValueError):
                build(
                    Config(profile="memory", model="fixture"),
                    Path(directory)/"bad",
                    model_path="auto:qwen",
                    model_sources=["owner/model/pyTorch/fp8/1"],
                    validation_games=["../../secret"],
                )


@unittest.skipUnless(importlib.util.find_spec("arcengine"), "requires ARC SDK environment")
class Arc3RuntimeTests(unittest.TestCase):
    def test_exact_action_limit_and_one_scorecard_lifecycle(self):
        from superturiya_arc.runtime import run
        from arcengine import FrameDataRaw, GameState
        import numpy as np

        class Env:
            observation_space = FrameDataRaw(frame=[np.zeros((2,2), dtype=int)], state=GameState.NOT_FINISHED,
                                              levels_completed=0, available_actions=[1])
            def step(self, action, **kwargs):
                return self.observation_space

        class SDK:
            made = []
            opens = closes = 0
            def get_environments(self):
                return [SimpleNamespace(game_id="test-v1")]
            def open_scorecard(self, **kwargs):
                self.opens += 1
                return "one"
            def make(self, game_id, **kwargs):
                self.made.append(game_id)
                return Env()
            def close_scorecard(self, card_id):
                self.closes += 1
                return SimpleNamespace(model_dump=lambda **kwargs: {"score": 0, "api_key": "secret"})

        sdk = SDK()
        with tempfile.TemporaryDirectory() as directory:
            result = run(Config(profile="explore", max_actions=3), Path(directory)/"run", Path(directory), sdk=sdk)
            self.assertEqual(result["games"][0]["actions"], 3)
            self.assertEqual((sdk.opens, sdk.closes, sdk.made), (1,1,["test-v1"]))
            self.assertNotIn("api_key", result["scorecard"])

    def test_parallel_games_share_one_scorecard(self):
        from superturiya_arc.runtime import run
        from arcengine import FrameDataRaw, GameState
        import numpy as np
        import threading

        barrier = threading.Barrier(2)

        class Env:
            observation_space = FrameDataRaw(
                frame=[np.zeros((2, 2), dtype=int)],
                state=GameState.NOT_FINISHED,
                levels_completed=0,
                available_actions=[1],
            )

            def step(self, action, **kwargs):
                barrier.wait(timeout=2)
                return self.observation_space

        class SDK:
            def __init__(self):
                self.opens = self.closes = 0
                self.made = []

            def get_environments(self):
                return [SimpleNamespace(game_id="aa00-v1"), SimpleNamespace(game_id="bb00-v1")]

            def open_scorecard(self, **kwargs):
                self.opens += 1
                return "one"

            def make(self, game_id, **kwargs):
                self.made.append(game_id)
                return Env()

            def close_scorecard(self, card_id):
                self.closes += 1
                return SimpleNamespace(model_dump=lambda **kwargs: {"score": 0})

        sdk = SDK()
        with tempfile.TemporaryDirectory() as directory:
            result = run(
                Config(profile="explore", max_actions=1, max_parallel_games=2),
                Path(directory)/"run",
                Path(directory),
                sdk=sdk,
            )
        self.assertEqual(result["status"], "complete")
        self.assertEqual((sdk.opens, sdk.closes), (1, 1))
        self.assertCountEqual(sdk.made, ["aa00-v1", "bb00-v1"])
        self.assertTrue(all(game["actions"] == 1 for game in result["games"]))

    def test_ambiguous_environment_step_is_not_retried(self):
        from superturiya_arc.runtime import play_game
        from arcengine import FrameDataRaw, GameState
        import numpy as np
        class Env:
            calls = 0
            observation_space = FrameDataRaw(frame=[np.zeros((2,2), dtype=int)], state=GameState.NOT_FINISHED,
                                              levels_completed=0, available_actions=[1])
            def step(self, *args, **kwargs):
                self.calls += 1
                return None
        env = Env()
        result = play_game(env, Config(profile="explore"), Log())
        self.assertEqual(env.calls, 1)
        self.assertEqual(result["stop_reason"], "error")


if __name__ == "__main__":
    unittest.main()
