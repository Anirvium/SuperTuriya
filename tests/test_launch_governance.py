import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from superturiya.api import build_server


class LaunchGovernanceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = build_server(host="127.0.0.1", port=0,
            db_path=str(Path(self.tmp.name) / "test.db"), api_token="test-token",
            principal_id="server-reviewer", tenant_id="tenant-a")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.engine = self.server.RequestHandlerClass.engine
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.engine.store.close()
        self.server.server_close()
        self.tmp.cleanup()

    def request(self, route, body=None, **headers):
        request = urllib.request.Request(self.base + route,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"content-type": "application/json", "authorization": "Bearer test-token", **headers})
        with self.opener.open(request, timeout=3) as response:
            return json.load(response)

    def denied(self, route, body, status=403, **headers):
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request(route, body, **headers)
        self.assertEqual(error.exception.code, status)

    def test_foreign_trace_writes_reads_and_upserts_are_denied(self):
        run = self.engine.store.start_trace({"tenant_id": "tenant-b", "subject_id": "s", "goal": "synthetic"})
        for route, body in [
            ("/traces/step", {"run_id": run["run_id"], "output": "foreign"}),
            ("/traces/start", {"run_id": run["run_id"], "goal": "overwrite"}),
            ("/trajectories/score", {"run_id": run["run_id"]}),
            ("/oversight/graph", {"run_id": run["run_id"]}),
            ("/observations", {"observations": [{"run_id": run["run_id"], "subject_id": "s", "content": "foreign"}]}),
        ]:
            self.denied(route, body)
        self.denied("/traces/" + run["run_id"], None)
        self.assertEqual(len(self.engine.store.get_trace(run["run_id"])["steps"]), 0)

    def test_foreign_intervention_and_policy_mutations_are_denied(self):
        p = self.engine.prepare_hackathon_case({"tenant_id": "tenant-b", "case_id": "eval-006"})
        iid = p["stored_intervention"]["intervention_id"]
        self.denied("/hackathon/interventions/review", {"intervention_id": iid, "decision": "approved", "reviewer_id": "spoof"})
        self.denied("/hackathon/interventions/activate", {"intervention_id": iid, "reviewer_id": "spoof"})
        policy = self.engine.store.add_policy({"tenant_id": "tenant-b", "body": "foreign"})
        self.denied("/policies/review", {"policy_id": policy["policy_id"], "decision": "approved", "reviewer_id": "spoof"})

    def test_generic_activation_without_replay_is_rejected(self):
        p = self.engine.store.add_policy({"tenant_id": "tenant-a", "body": "No replay"})
        self.request("/policies/review", {"policy_id": p["policy_id"], "decision": "approved", "reviewer_id": "spoof"})
        self.denied("/policies/review", {"policy_id": p["policy_id"], "decision": "active", "reviewer_id": "spoof"}, 400)
        with self.assertRaisesRegex(ValueError, "verified safe replay"):
            self.engine.store.transition_policy(p["policy_id"], "active", "reviewer")

    def test_authenticated_review_activation_and_revocation(self):
        p = self.request("/hackathon/cases/prepare", {"case_id": "eval-006", "tenant_id": "spoof"})
        iid = p["stored_intervention"]["intervention_id"]
        r = self.request("/hackathon/interventions/review", {"intervention_id": iid, "decision": "approved", "reviewer_id": "spoof"})
        self.assertEqual(r["intervention"]["reviewer_id"], "server-reviewer")
        self.assertEqual(r["intervention"]["tenant_id"], "tenant-a")
        a = self.request("/hackathon/interventions/activate", {"intervention_id": iid, "reviewer_id": "spoof"})
        self.assertEqual(a["procedural_policy"]["status"], "active")
        self.denied("/hackathon/interventions/activate", {"intervention_id": iid}, 400)
        revoked = self.request("/policies/review", {"policy_id": a["procedural_policy"]["policy_id"], "decision": "revoked"})
        self.assertEqual(revoked["status"], "revoked")
        self.assertEqual(self.engine.store.list_policies("tenant-a", status="active"), [])

    def test_failed_replay_cannot_activate(self):
        p = self.request("/hackathon/cases/prepare", {"case_id": "eval-012"})
        iid = p["stored_intervention"]["intervention_id"]
        r = self.request("/hackathon/interventions/review", {"intervention_id": iid, "decision": "approved"})
        self.assertFalse(r["replay"]["verified_safe_recovery"])
        self.denied("/hackathon/interventions/activate", {"intervention_id": iid}, 400)

    def test_hostile_origin_and_implicit_live_inference_are_denied(self):
        self.denied("/hackathon/cases/prepare", {"case_id": "eval-006"}, origin="https://hostile.example")
        self.denied("/hackathon/cases/prepare", {"case_id": "eval-006", "mode": "live"})

    def test_benchmark_simulated_approval_is_not_human_authority(self):
        self.engine.run_hackathon_evaluation({"tenant_id": "tenant-a", "mode": "frozen"})
        item = next(i for i in self.engine.store.list_interventions("tenant-a") if i["case_id"] == "eval-006")
        self.denied("/hackathon/interventions/activate", {"intervention_id": item["intervention_id"]}, 400)

    def test_changed_approved_content_cannot_reuse_old_verification(self):
        p = self.request("/hackathon/cases/prepare", {"case_id": "eval-006"})
        iid = p["stored_intervention"]["intervention_id"]
        self.request("/hackathon/interventions/review", {"intervention_id": iid, "decision": "approved"})
        stored = self.engine.store.get_intervention(iid)
        stored["payload"]["rationale"] = "Content changed after approval"
        self.engine.store.add_intervention(stored)
        self.denied("/hackathon/interventions/activate", {"intervention_id": iid}, 400)

    def test_nested_observation_scope_and_existing_step_ids(self):
        result = self.request("/observations", {"observations": [{"tenant_id": "tenant-b", "subject_id": "s", "content": "Scoped synthetic content", "type": "message"}]})
        self.assertEqual(result["observations"][0]["tenant_id"], "tenant-a")
        foreign = self.engine.store.start_trace({"tenant_id": "tenant-b", "subject_id": "s"})
        step = self.engine.store.add_trace_step({"run_id": foreign["run_id"], "output": "original"})
        own = self.request("/traces/start", {"subject_id": "s", "goal": "own"})
        self.denied("/traces/step", {"run_id": own["run_id"], "step_id": step["step_id"], "output": "overwrite"})


if __name__ == "__main__":
    unittest.main()
