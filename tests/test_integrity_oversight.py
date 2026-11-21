import tempfile
import unittest
from pathlib import Path

from superturiya.intelligence import SuperTuriyaEngine
from superturiya.integrity_cards import build_integrity_card
from superturiya.store import SuperTuriyaStore


class IntegrityAndOversightTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = SuperTuriyaStore(str(Path(self.tmp.name) / "oversight.db"))
        self.engine = SuperTuriyaEngine(self.store)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def _card_payload(self):
        return {
            "tenant_id": "t1",
            "evaluation_id": "eval-run-1",
            "assessor_id": "reviewer-1",
            "revisions": {
                "model": "model@sha256:abc",
                "code": "git:123",
                "dataset": "dataset:456",
                "runner": "runner:789",
            },
            "channels": {
                "training_time_exposure": {
                    "state": "?",
                    "missing_evidence": ["provider training manifest"],
                },
                "evaluation_time_retrieval": {
                    "state": "C",
                    "observed_facts": ["no retrieval tool configured"],
                    "evidence_refs": ["runner-config:tools"],
                },
                "scaffold_leakage": {
                    "state": "P",
                    "evidence_refs": ["projection-test"],
                    "missing_evidence": ["independent outbound traffic log"],
                },
            },
            "incident": {
                "confirmed": False,
                "susceptibility": "medium",
                "description": "Training provenance is unavailable.",
            },
            "score_impact": None,
        }

    def test_integrity_card_separates_channels_and_has_no_cleanliness_score(self):
        result = self.engine.create_integrity_card(self._card_payload())
        card = result["card"]
        self.assertEqual(card["channels"]["training_time_exposure"]["state"], "?")
        self.assertIsNone(card["aggregate_cleanliness_score"])
        self.assertEqual(len(card["card_hash"]), 64)
        listed = self.store.list_integrity_cards("t1", "eval-run-1")
        self.assertEqual(listed[0]["card_hash"], card["card_hash"])

    def test_closed_channel_requires_evidence(self):
        payload = self._card_payload()
        payload["channels"]["evaluation_time_retrieval"]["evidence_refs"] = []
        with self.assertRaisesRegex(ValueError, "requires evidence_refs"):
            build_integrity_card(payload)

    def test_evidence_grounded_graph_preserves_raw_refs_and_typed_edges(self):
        run = self.engine.start_trace(
            {
                "tenant_id": "t1",
                "subject_id": "s1",
                "agent_id": "agent-1",
                "goal": "Safely complete the task.",
            }
        )
        self.engine.record_step(
            {
                "run_id": run["run_id"],
                "kind": "decision",
                "source": "planner",
                "input": "Should the tool run?",
                "output": "Run after checking evidence.",
                "status": "completed",
                "capture_observation": False,
            }
        )
        self.engine.record_step(
            {
                "run_id": run["run_id"],
                "kind": "tool",
                "source": "executor",
                "input": "Execute bounded action.",
                "output": "Action completed.",
                "status": "completed",
                "capture_observation": False,
            }
        )
        graph = self.engine.oversight_graph({"run_id": run["run_id"]})
        self.assertTrue(graph["raw_trace_preserved"])
        self.assertEqual(len(graph["behaviors"]), 2)
        self.assertEqual(graph["edges"][0]["type"], "PRECEDES")
        self.assertGreaterEqual(len(graph["consequential_decisions"]), 2)
        self.assertTrue(
            all(item["raw_ref"].startswith("trace_step:") for item in graph["evidence_units"])
        )


if __name__ == "__main__":
    unittest.main()
