import json
import tempfile
import unittest
from pathlib import Path

from superturiya.operations import restore, snapshot
from superturiya.store import SuperTuriyaStore
from superturiya.trace_workspace import export_trace, import_trace


class OperationsTest(unittest.TestCase):
    def test_live_backup_round_trip_and_refusal_to_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            store = SuperTuriyaStore(str(root / "source.db"))
            record = {"schema": "superturiya-trace-v1", "agent": "test", "goal": "backup", "spans": [{"span_id": "one", "name": "step", "output": 3}]}
            result = import_trace(store, {"record": record, "tenant_id": "a"})
            try:
                backup = root / "backup.db"
                receipt = snapshot(str(root / "source.db"), str(backup))
                with self.assertRaises(FileExistsError): snapshot(str(root / "source.db"), str(backup))
                manifest = root / "manifest.json"; manifest.write_text(json.dumps(receipt))
                restore(str(backup), str(manifest), str(root / "restored.db"))
                restored = SuperTuriyaStore(str(root / "restored.db"))
                try:
                    self.assertTrue(export_trace(restored, result["run_id"], "a")["integrity_verified"])
                finally: restored.close()
                receipt["sha256"] = "wrong"; manifest.write_text(json.dumps(receipt))
                with self.assertRaisesRegex(ValueError, "digest"): restore(str(backup), str(manifest), str(root / "rejected.db"))
                self.assertFalse((root / "rejected.db").exists())
            finally: store.close()

    def test_missing_or_non_database_source_does_not_create_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); bad = root / "bad.db"; bad.write_text("invalid")
            for source in (root / "missing.db", bad):
                with self.assertRaises(Exception): snapshot(str(source), str(root / "output.db"))
                self.assertFalse((root / "output.db").exists())


if __name__ == "__main__": unittest.main()
