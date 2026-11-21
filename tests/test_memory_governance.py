import tempfile
import unittest
from pathlib import Path

from superturiya.intelligence import SuperTuriyaEngine
from superturiya.store import SuperTuriyaStore


class MemoryGovernanceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = SuperTuriyaStore(str(Path(self.tmp.name) / "memory.db"))
        self.engine = SuperTuriyaEngine(self.store)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def _add(self, memory_id, metadata=None, expires_at=None):
        return self.store.add_memory(
            {
                "memory_id": memory_id,
                "tenant_id": "t1",
                "subject_id": "s1",
                "memory_type": "profile",
                "text": "The subject prefers concise therapy reminders.",
                "derived_from": ["obs-1"],
                "expires_at": expires_at,
                "metadata": metadata or {},
            }
        )

    def _search(self, **overrides):
        payload = {
            "tenant_id": "t1",
            "subject_id": "s1",
            "principal_id": "s1",
            "purpose": "assist_subject",
            "policy_version": "v1",
            "intent": "current",
            "query": "concise therapy",
        }
        payload.update(overrides)
        return self.engine.search_memories(payload)

    def test_admissible_memory_is_exposed_and_audited(self):
        self._add("mem-ok")
        result = self._search()
        self.assertEqual(result["trace"]["exposed_ids"], ["mem-ok"])
        self.assertIn("concise therapy", result["context"])
        audit = self.store.list_audit("t1", "s1", limit=10)
        self.assertIn("memory.exposure_decision", [item["action"] for item in audit])

    def test_cross_principal_and_wrong_purpose_fail_closed(self):
        self._add("mem-private")
        cross_principal = self._search(principal_id="operator-2")
        self.assertEqual(cross_principal["results"], [])
        self.assertEqual(cross_principal["withheld"][0]["decision"], "no")

        wrong_purpose = self._search(purpose="marketing")
        self.assertEqual(wrong_purpose["results"], [])
        self.assertEqual(wrong_purpose["withheld"][0]["axes"]["policy"]["decision"], "no")

    def test_unresolved_authorization_is_never_exposed(self):
        self._add(
            "mem-unresolved",
            {
                "authorization_state": "unresolved",
                "owner_principal_id": "s1",
                "allowed_purposes": ["assist_subject"],
                "policy_version": "v1",
            },
        )
        result = self._search()
        self.assertEqual(result["results"], [])
        self.assertEqual(result["withheld"][0]["decision"], "unresolved")
        self.assertEqual(result["metrics"]["unresolved_exposure_rate"], 0.0)

    def test_superseded_memory_is_historical_only(self):
        self._add(
            "mem-old",
            {
                "lifecycle_state": "superseded",
                "owner_principal_id": "s1",
                "allowed_purposes": ["assist_subject"],
                "policy_version": "v1",
            },
        )
        self.assertEqual(self._search(intent="current")["results"], [])
        historical = self._search(intent="historical")
        self.assertEqual(historical["trace"]["exposed_ids"], ["mem-old"])

    def test_expired_memory_is_withheld(self):
        self._add("mem-expired", expires_at="2020-01-01T00:00:00Z")
        result = self._search(evaluated_at="2026-10-09T00:00:00Z")
        self.assertEqual(result["results"], [])
        self.assertEqual(result["withheld"][0]["axes"]["lifecycle"]["decision"], "no")

    def test_subject_is_required(self):
        self._add("mem-ok")
        with self.assertRaisesRegex(ValueError, "subject_id is required"):
            self.engine.search_memories({"tenant_id": "t1", "query": "therapy"})


if __name__ == "__main__":
    unittest.main()
