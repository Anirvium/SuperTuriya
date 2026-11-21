import copy
import tempfile
import unittest
from pathlib import Path

from superturiya.evidence_integrity import (
    build_evidence_projection,
    reveal_hidden_unicode,
    verify_evidence_projection,
)
from superturiya.intelligence import SuperTuriyaEngine
from superturiya.store import SuperTuriyaStore


class EvidenceIntegrityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = SuperTuriyaStore(str(Path(self.tmp.name) / "evidence.db"))
        self.engine = SuperTuriyaEngine(self.store)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_projection_is_bound_to_raw_and_reveals_hidden_unicode(self):
        raw = {
            "content": "safe\u202Etxt <script>alert(1)</script>",
            "evidence_refs": ["ev-1"],
            "private": "not projected",
        }
        projection = build_evidence_projection(raw, "ev-record")
        self.assertIn("U+202E", projection["display"]["content"])
        self.assertIn("<script>", projection["display"]["content"])
        self.assertNotIn("private", projection["display"])
        self.assertTrue(verify_evidence_projection(raw, projection)["verified"])

        tampered = copy.deepcopy(projection)
        tampered["display"]["content"] = "altered"
        self.assertFalse(verify_evidence_projection(raw, tampered)["verified"])

    def test_raw_record_is_append_only_and_fetched_separately(self):
        created = self.engine.ingest_evidence(
            {
                "tenant_id": "t1",
                "subject_id": "s1",
                "record_id": "record-1",
                "record": {"content": "untrusted <svg onload=alert(1)>"},
            }
        )
        self.assertTrue(created["integrity"]["verified"])
        self.assertNotIn("raw_payload", created)
        stored = self.store.get_evidence_record("record-1")
        self.assertEqual(stored["raw_payload"]["content"], "untrusted <svg onload=alert(1)>")
        with self.assertRaisesRegex(ValueError, "append-only"):
            self.engine.ingest_evidence(
                {
                    "tenant_id": "t1",
                    "subject_id": "s1",
                    "record_id": "record-1",
                    "record": {"content": "replacement"},
                }
            )

    def test_nested_hidden_characters_are_visible(self):
        value = {"items": ["a\u200Bb", "plain"]}
        shown = reveal_hidden_unicode(value)
        self.assertIn("U+200B", shown["items"][0])


if __name__ == "__main__":
    unittest.main()
