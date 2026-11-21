import copy
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from superturiya.api import build_server
from superturiya.recorder import TraceRecorder
from superturiya.store import SuperTuriyaStore
from superturiya.trace_workspace import export_trace, import_trace, normalize


def recording():
    return {"schema": "superturiya-trace-v1", "agent": "test-agent", "goal": "Test a tool request", "status": "failed", "spans": [
        {"span_id": "root", "name": "request", "kind": "step", "status": "failed", "input": {"authorization": "Bearer private-token", "token_count": 42, "OPENAI_API_KEY": "private-provider-key", "token": "private-session-token"}, "output": None},
        {"span_id": "tool", "parent_span_id": "root", "name": "catalog", "kind": "tool", "status": "completed", "input": "password=secret-value", "output": {"api_key": "private-key", "value": 3}},
    ]}


class TraceWorkspaceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / "test.db")
        self.store = SuperTuriyaStore(self.path)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def ingest(self, record=None, tenant="a"):
        return import_trace(self.store, {"record": record or recording(), "tenant_id": tenant, "principal_id": "reviewer"})

    def test_redaction_precedes_storage_and_preserves_useful_values(self):
        result = self.ingest()
        bundle = export_trace(self.store, result["run_id"], "a")
        stored = json.dumps(bundle)
        for secret in ("private-token", "private-key", "secret-value", "private-provider-key", "private-session-token"):
            self.assertNotIn(secret, stored)
            self.assertNotIn(secret, json.dumps(self.store.get_trace(result["run_id"])))
        self.assertEqual(bundle["record"]["spans"][0]["input"]["token_count"], 42)
        self.assertFalse(bundle["report"]["replay_available"])
        self.assertFalse(bundle["report"]["activation_available"])

    def test_invalid_hierarchies_and_statuses_leave_no_state(self):
        changes = [lambda d: d["spans"][1].update(span_id="root"), lambda d: d["spans"][0].update(parent_span_id="tool"),
                   lambda d: d["spans"][0].update(parent_span_id="missing"), lambda d: d.update(status=[]),
                   lambda d: d["spans"][0].update(kind={}), lambda d: d["spans"][0].update(span_id="password=foo"),
                   lambda d: d["spans"][0].update(started_at="yesterday"), lambda d: d["spans"][0].update(input=float("nan"))]
        for change in changes:
            doc = recording(); change(doc)
            with self.assertRaises(ValueError):
                self.ingest(doc)
        self.assertEqual(self.store.list_traces("a"), [])

    def test_duplicates_are_tenant_bound_and_concurrent_safe(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.ingest(), range(8)))
        self.assertEqual(len({r["run_id"] for r in results}), 1)
        self.assertEqual(sum(not r["duplicate"] for r in results), 1)
        self.assertNotEqual(self.ingest(tenant="b")["run_id"], results[0]["run_id"])
        self.assertEqual(len(self.store.list_audit("a")), 1)

    def test_import_is_atomic_when_database_write_fails(self):
        self.store._connection.execute("CREATE TRIGGER deny_import BEFORE INSERT ON trace_imports BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        with self.assertRaises(Exception): self.ingest()
        self.assertEqual(self.store.list_traces("a"), [])
        self.assertEqual(self.store._connection.execute("SELECT COUNT(*) FROM trace_steps").fetchone()[0], 0)
        self.assertEqual(self.store.list_audit("a"), [])

    def test_snapshot_is_immutable_and_survives_restart(self):
        result = self.ingest()
        for call in (lambda: self.store.start_trace({"run_id": result["run_id"], "tenant_id": "a"}), lambda: self.store.add_trace_step({"run_id": result["run_id"]})):
            with self.assertRaisesRegex(ValueError, "immutable"): call()
        original_step = self.store.get_trace(result["run_id"])["steps"][0]
        other = self.store.start_trace({"tenant_id": "a"})
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.store.add_trace_step({"run_id": other["run_id"], "step_id": original_step["step_id"]})
        self.store.close(); self.store = SuperTuriyaStore(self.path)
        self.assertTrue(export_trace(self.store, result["run_id"], "a")["integrity_verified"])

    def test_export_checks_tenant_and_detects_record_and_report_tampering(self):
        result = self.ingest()
        with self.assertRaises(KeyError): export_trace(self.store, result["run_id"], "b")
        self.store._connection.execute("UPDATE trace_imports SET document='{}' WHERE run_id=?", (result["run_id"],))
        with self.assertRaisesRegex(ValueError, "integrity"): export_trace(self.store, result["run_id"], "a")
        self.store._connection.rollback()
        self.store._connection.execute("UPDATE trace_imports SET report=? WHERE run_id=?", (json.dumps({"report_hash": "wrong"}), result["run_id"]))
        with self.assertRaisesRegex(ValueError, "integrity"): export_trace(self.store, result["run_id"], "a")

    def test_subject_deletion_removes_snapshot_payload(self):
        result = self.ingest()
        self.store.delete_subject("a", "imported-traces")
        with self.assertRaises(KeyError): export_trace(self.store, result["run_id"], "a")

    def test_time_order_and_limits_are_enforced(self):
        doc = recording(); doc["spans"][0].update(started_at="2026-11-21T03:00:00+00:00", ended_at="2026-11-21T02:00:00+00:00")
        with self.assertRaises(ValueError): normalize(doc)
        doc = recording(); doc["spans"] = doc["spans"] * 251
        with self.assertRaises(ValueError): normalize(doc)
        doc = recording(); doc["spans"][0]["input"] = "x" * 900001
        with self.assertRaises(ValueError): normalize(doc)

    def test_recorder_tracks_nested_failures_without_capturing_exception_values(self):
        trace = TraceRecorder("recorder-agent", "test nested execution")
        with self.assertRaises(ValueError):
            with trace.span("request"):
                with trace.span("tool", kind="tool", input={"access_token": "private-token"}) as step:
                    step.output({"value": 7})
                    raise ValueError("confidential exception message")
        doc = trace.document()
        self.assertEqual(doc["status"], "failed")
        self.assertEqual(doc["spans"][1]["parent_span_id"], doc["spans"][0]["span_id"])
        self.assertNotIn("confidential", json.dumps(doc))
        self.assertNotIn("private-token", json.dumps(doc))
        self.assertEqual(doc["spans"][1]["attributes"]["exception_type"], "ValueError")
        self.assertTrue(trace.export(str(Path(self.tmp.name) / "trace.json")).exists())


class TraceWorkspaceApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = build_server(port=0, db_path=str(Path(self.tmp.name) / "api.db"), api_token="test-token", tenant_id="a", principal_id="bound-reviewer")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def tearDown(self):
        self.server.shutdown(); self.thread.join(2); self.server.server_close(); self.server.RequestHandlerClass.engine.store.close(); self.tmp.cleanup()

    def request(self, route, body=None, token="test-token"):
        req = urllib.request.Request(self.base + route, data=json.dumps(body).encode() if body is not None else None, headers={"Content-Type": "application/json", "Authorization": "Bearer " + token})
        with self.opener.open(req, timeout=3) as response: return json.load(response)

    def test_authentication_and_authenticated_identity_apply_to_workspace(self):
        for route in ("/workspace/runs", "/workspace/audit"):
            with self.assertRaises(urllib.error.HTTPError) as denied: self.request(route, token="invalid")
            self.assertEqual(denied.exception.code, 401)
        receipt = self.request("/workspace/import", {"tenant_id": "b", "principal_id": "spoof", "record": recording()})
        self.assertEqual(len(self.request("/workspace/runs")["runs"]), 1)
        bundle = self.request("/workspace/runs/" + receipt["run_id"])
        self.assertTrue(bundle["integrity_verified"])
        event = self.request("/workspace/audit")["events"][0]
        self.assertEqual(event["metadata"]["principal_id"], "bound-reviewer")
        self.assertEqual(event["tenant_id"], "a")

    def test_foreign_export_is_hidden_and_preview_does_not_persist(self):
        store = self.server.RequestHandlerClass.engine.store
        foreign = import_trace(store, {"record": recording(), "tenant_id": "b"})
        with self.assertRaises(urllib.error.HTTPError) as denied: self.request("/workspace/runs/" + foreign["run_id"])
        self.assertEqual(denied.exception.code, 404)
        preview = self.request("/workspace/preview", {"record": recording()})
        self.assertNotIn("private-token", json.dumps(preview))
        self.assertEqual(self.request("/workspace/runs")["runs"], [])


if __name__ == "__main__": unittest.main()
