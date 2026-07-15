import tempfile
import unittest
from pathlib import Path

from superturiya.intelligence import SuperTuriyaEngine
from superturiya.store import SuperTuriyaStore


class SuperTuriyaFlowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        db = Path(self.tmp.name) / "test.db"
        self.store = SuperTuriyaStore(str(db))
        self.engine = SuperTuriyaEngine(self.store)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_full_trajectory_loop(self):
        run = self.engine.start_trace(
            {
                "tenant_id": "t1",
                "subject_id": "s1",
                "agent_id": "agent",
                "goal": "Use memory and evidence.",
            }
        )
        captured = self.engine.capture_observations(
            {
                "observations": [
                    {
                        "tenant_id": "t1",
                        "subject_id": "s1",
                        "run_id": run["run_id"],
                        "type": "tool_result",
                        "source": "calendar.lookup",
                        "content": "Subject missed therapy session twice and prefers concise messages.",
                        "entities": ["subject", "therapy_session"],
                        "relations": [
                            {"from": "subject", "type": "MISSED", "to": "therapy_session"}
                        ],
                        "labels": {"clinical_relevance": 0.8},
                    }
                ]
            }
        )
        self.assertEqual(len(captured["observations"]), 1)
        self.assertGreaterEqual(captured["graph"]["nodes_created"], 2)

        memories = self.engine.extract_memories(
            {"tenant_id": "t1", "subject_id": "s1", "run_id": run["run_id"]}
        )
        self.assertGreaterEqual(len(memories["stored"]), 2)
        memory_refs = [memory["memory_id"] for memory in memories["stored"][:2]]

        self.engine.record_step(
            {
                "run_id": run["run_id"],
                "kind": "memory",
                "input": "Retrieve context.",
                "output": "Retrieved subject memory.",
                "memory_refs": memory_refs,
            }
        )
        self.engine.record_step(
            {
                "run_id": run["run_id"],
                "kind": "decision",
                "input": "Recommend action.",
                "output": "Recovered with concise evidence-linked plan.",
                "status": "completed",
                "trace_status": "completed",
                "memory_refs": memory_refs,
            }
        )

        score = self.engine.score_trajectory({"run_id": run["run_id"]})
        self.assertGreater(score["utility"], 0.5)
        self.assertIn("evidence_grounding", score["metrics"])

        search = self.engine.search_memories(
            {"tenant_id": "t1", "subject_id": "s1", "query": "concise therapy"}
        )
        self.assertGreaterEqual(len(search["results"]), 1)

        audit = self.engine.counterfactuals({"run_id": run["run_id"]})
        self.assertEqual(len(audit["counterfactuals"]), 2)

        quantum = self.engine.quantum_interpret_trajectory({"run_id": run["run_id"]})
        self.assertIn("dominant_interpretation", quantum)
        self.assertIn("density_matrix", quantum)
        self.assertIn("experience_state", quantum)
        self.assertAlmostEqual(quantum["density_matrix"]["trace"], 1.0, places=4)
        self.assertGreaterEqual(quantum["ambiguity_score"], 0.0)
        self.assertGreaterEqual(len(quantum["relational_couplings"]), 1)
        experience = quantum["experience_state"]
        self.assertGreaterEqual(experience["function_score"], 0.0)
        self.assertLessEqual(experience["function_score"], 1.0)
        self.assertGreaterEqual(experience["experience_coherence"], 0.0)
        self.assertLessEqual(experience["experience_coherence"], 1.0)
        self.assertIn("attention_memory_fidelity", experience)
        self.assertIn("state_transition_graph", experience)
        self.assertGreaterEqual(len(experience["state_transition_graph"]["nodes"]), 2)
        self.assertIn("candidate_edges", experience["graph_discovery"])

        policies = self.engine.synthesise_policies({"run_id": run["run_id"]})
        self.assertIn("stored", policies)

        erased = self.engine.forget_subject("t1", "s1")
        self.assertGreater(erased["deleted"]["observations"], 0)
        self.assertGreater(erased["deleted"]["quantum_trajectory_reports"], 0)
        self.assertEqual(self.store.counts("t1", "s1")["observations"], 0)


if __name__ == "__main__":
    unittest.main()
