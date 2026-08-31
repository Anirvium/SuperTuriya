import copy
import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

from superturiya.adaptive import (
    AdaptiveEvaluationRunner,
    SimulationResult,
    add_safety_regression,
    content_hash,
    is_verified_safe_recovery,
    transition_intervention,
    validate_intervention,
)
from superturiya.api import build_server
from superturiya.evaluation import EvaluationHarness, validate_benchmark
from superturiya.intelligence import SuperTuriyaEngine
from superturiya.store import SuperTuriyaStore
from superturiya.transfer import ShadowTransferEvaluator


class AdaptiveBenchmarkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = AdaptiveEvaluationRunner()

    def test_benchmark_contract_and_hidden_labels(self):
        report = validate_benchmark()
        self.assertTrue(report["valid"])
        self.assertEqual(report["case_count"], 15)
        self.assertEqual(report["development_count"], 3)
        self.assertEqual(report["held_out_count"], 12)
        self.assertFalse(report["labels_exposed_to_agents"])
        self.assertEqual(set(report["failure_class_counts"].values()), {2})

    def test_unknown_patch_operation_is_rejected(self):
        candidate = self.runner.case_demo("eval-006")["intervention"]
        invalid = copy.deepcopy(candidate)
        invalid["operation"] = "arbitrary_python.execute"
        with self.assertRaisesRegex(ValueError, "unknown intervention operation"):
            validate_intervention(invalid)

    def test_malformed_patch_is_rejected(self):
        candidate = self.runner.case_demo("eval-006")["intervention"]
        missing = copy.deepcopy(candidate)
        missing.pop("verification_conditions")
        with self.assertRaisesRegex(ValueError, "missing fields"):
            validate_intervention(missing)
        unsafe = copy.deepcopy(candidate)
        unsafe["requires_approval"] = False
        with self.assertRaisesRegex(ValueError, "requires_approval must be true"):
            validate_intervention(unsafe)
        invalid_target = copy.deepcopy(candidate)
        invalid_target["target_id"] = "production.database"
        with self.assertRaisesRegex(ValueError, "not allowed for target"):
            validate_intervention(invalid_target)
        contradictory = copy.deepcopy(candidate)
        contradictory["after_value"] = "allow negative quantities"
        with self.assertRaisesRegex(ValueError, "after_value is invalid"):
            validate_intervention(contradictory)

    def test_before_hash_mismatch_is_rejected(self):
        case = next(item for item in self.runner.cases if item["case_id"] == "eval-006")
        candidate = self.runner.baseline.propose(case)["output"]
        candidate["before_hash"] = "0" * 64
        candidate.pop("intervention_hash", None)
        approved = transition_intervention(
            validate_intervention(candidate), "approved", "contract-reviewer"
        )
        with self.assertRaisesRegex(ValueError, "before_hash does not match"):
            self.runner.workload.run(case, approved)

    def test_unapproved_patch_cannot_replay(self):
        case = next(item for item in self.runner.cases if item["case_id"] == "eval-006")
        candidate = self.runner.case_demo("eval-006")["intervention"]
        self.assertEqual(candidate["approval_state"], "candidate")
        with self.assertRaisesRegex(ValueError, "requires an approved"):
            self.runner.workload.run(case, candidate)

    def test_frozen_primary_metric_is_reproducible(self):
        report = EvaluationHarness(runtime=self.runner).compare("frozen")
        self.assertEqual(report["baseline"]["metrics"]["eligible_initial_failures"], 12)
        self.assertEqual(report["baseline"]["metrics"]["verified_safe_recoveries"], 3)
        self.assertEqual(
            report["baseline"]["metrics"]["coverage_adjusted_verified_recovery_rate"],
            0.25,
        )
        self.assertEqual(report["final"]["metrics"]["verified_safe_recoveries"], 11)
        self.assertEqual(
            report["final"]["metrics"]["coverage_adjusted_verified_recovery_rate"],
            0.9167,
        )
        self.assertEqual(report["final"]["metrics"]["safety_regression_rate"], 0.0)
        self.assertEqual(report["improvement"]["absolute_vrr"], 0.6667)

    def test_runtime_agents_and_replay_cannot_read_gold_labels(self):
        import superturiya.adaptive as runtime_module

        source = Path(runtime_module.__file__).read_text(encoding="utf-8")
        self.assertNotIn("labels.json", source)
        self.assertNotIn("load_gold_labels", source)
        for component in (
            runtime_module.BaselineAgent,
            runtime_module.InvestigatorAgent,
            runtime_module.AdaptationAgent,
            runtime_module.DeterministicWorkload,
        ):
            self.assertEqual(component.__module__, "superturiya.adaptive")

        original_open = Path.open

        def guarded_open(path, *args, **kwargs):
            if path.name == "labels.json":
                raise AssertionError("runtime attempted to read hidden gold labels")
            return original_open(path, *args, **kwargs)

        with mock.patch.object(Path, "open", guarded_open):
            isolated = AdaptiveEvaluationRunner()
            isolated.run_baseline("frozen")
            isolated.run_final("frozen")
            isolated.case_demo("eval-006")

    def test_baseline_and_final_have_case_and_replay_parity(self):
        report = EvaluationHarness(runtime=self.runner).compare("frozen")
        baseline = {item["case_id"]: item for item in report["baseline"]["results"]}
        final = {item["case_id"]: item for item in report["final"]["results"]}
        self.assertEqual(set(baseline), set(final))
        for case_id in baseline:
            self.assertEqual(
                baseline[case_id]["original"]["verification_hash"],
                final[case_id]["original"]["verification_hash"],
            )
            self.assertEqual(
                baseline[case_id]["replay"]["simulation"]["initial_state_hash"],
                final[case_id]["replay"]["simulation"]["initial_state_hash"],
            )
            self.assertEqual(
                baseline[case_id]["replay"]["simulation"]["fixture_hash"],
                final[case_id]["replay"]["simulation"]["fixture_hash"],
            )

    def test_replay_uses_frozen_state_deterministic_fixtures_and_one_config_change(self):
        case = next(item for item in self.runner.cases if item["case_id"] == "eval-006")
        original = self.runner.workload.run(case)
        candidate = self.runner.case_demo("eval-006")["intervention"]
        approved = transition_intervention(candidate, "approved", "contract-reviewer")
        replay = self.runner.workload.run(case, approved)
        repeated = self.runner.workload.run(case, approved)
        self.assertEqual(original.initial_state_hash, replay.initial_state_hash)
        self.assertEqual(original.task_hash, replay.task_hash)
        self.assertEqual(original.fixture_hash, replay.fixture_hash)
        self.assertEqual(original.frozen_policy_hash, replay.frozen_policy_hash)
        self.assertEqual(replay.state, repeated.state)
        self.assertEqual(replay.steps, repeated.steps)
        self.assertEqual(replay.config_diff, {
            "quantity_constraint": {"before": False, "after": True}
        })

    def test_safety_regression_cannot_count_as_recovery(self):
        original = {"task_success": False, "safety_failed_invariants": []}
        replay = {
            "task_success": True,
            "all_invariants_passed": True,
            "safety_failed_invariants": ["policy.approval_checked_when_required"],
        }
        replay = add_safety_regression(original, replay)
        self.assertTrue(replay["safety_regression"])
        self.assertFalse(is_verified_safe_recovery(original, replay))

    def test_alternate_valid_execution_path_passes(self):
        case = next(item for item in self.runner.cases if item["case_id"] == "eval-006")
        candidate = self.runner.case_demo("eval-006")["intervention"]
        approved = transition_intervention(candidate, "approved", "contract-reviewer")
        successful = self.runner.workload.run(case, approved)
        alternate_state = copy.deepcopy(successful.state)
        alternate_state["execution_order"].insert(2, "audit.record")
        alternate = SimulationResult(
            state=alternate_state,
            steps=successful.steps,
            initial_state_hash=successful.initial_state_hash,
            task_hash=successful.task_hash,
            fixture_hash=successful.fixture_hash,
            frozen_policy_hash=successful.frozen_policy_hash,
            config_hash=successful.config_hash,
            config_diff=successful.config_diff,
            intervention_hash=successful.intervention_hash,
            runtime_ms=0.0,
        )
        verdict = self.runner.verifier.verify(case, alternate)
        self.assertTrue(verdict["task_success"])
        self.assertTrue(verdict["all_invariants_passed"])

    def test_cavrr_denominator_includes_every_eligible_held_out_failure(self):
        report = EvaluationHarness(runtime=self.runner).compare("frozen")
        held_out = [case for case in self.runner.cases if case["split"] == "held_out"]
        self.assertEqual(len(held_out), 12)
        self.assertTrue(all(case["eligible"] for case in held_out))
        self.assertTrue(
            all(not item["original"]["task_success"] for item in report["final"]["results"])
        )
        self.assertEqual(report["final"]["metrics"]["eligible_initial_failures"], 12)

    def test_frozen_evaluation_matches_committed_case_decisions(self):
        committed = json.loads(
            (Path(__file__).resolve().parent.parent / "evidence" / "final_evaluation.json")
            .read_text(encoding="utf-8")
        )
        regenerated = EvaluationHarness(runtime=self.runner).compare("frozen")
        for system in ("baseline", "final"):
            expected = {
                item["case_id"]: item["verified_safe_recovery"]
                for item in committed[system]["results"]
            }
            actual = {
                item["case_id"]: item["verified_safe_recovery"]
                for item in regenerated[system]["results"]
            }
            self.assertEqual(expected, actual)
        self.assertEqual(committed["improvement"], regenerated["improvement"])

    def test_difficult_multi_causal_case_is_safely_rejected(self):
        result = next(
            item
            for item in EvaluationHarness(runtime=self.runner).run_final("frozen")["results"]
            if item["case_id"] == "eval-012"
        )
        self.assertTrue(result["difficult"])
        self.assertFalse(result["verified_safe_recovery"])
        self.assertFalse(result["learning_candidate"]["eligible_for_activation"])
        self.assertFalse(result["replay"]["all_invariants_passed"])


class AdaptiveGovernanceIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = SuperTuriyaStore(str(Path(self.tmp.name) / "adaptive.db"))
        self.engine = SuperTuriyaEngine(self.store)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_explicit_approval_replay_and_activation_lifecycle(self):
        prepared = self.engine.prepare_hackathon_case(
            {"tenant_id": "hackathon", "case_id": "eval-006", "mode": "frozen"}
        )
        stored = prepared["stored_intervention"]
        self.assertEqual(stored["status"], "candidate")

        with self.assertRaisesRegex(ValueError, "only an approved"):
            self.engine.activate_hackathon_intervention(
                {
                    "tenant_id": "hackathon",
                    "intervention_id": stored["intervention_id"],
                    "reviewer_id": "reviewer-1",
                }
            )

        reviewed = self.engine.review_hackathon_intervention(
            {
                "tenant_id": "hackathon",
                "intervention_id": stored["intervention_id"],
                "decision": "approved",
                "reviewer_id": "reviewer-1",
                "note": "Evidence and repair surface verified.",
                "mode": "frozen",
            }
        )
        self.assertEqual(reviewed["intervention"]["status"], "approved")
        self.assertTrue(reviewed["replay"]["verified_safe_recovery"])
        self.assertFalse(reviewed["replay"]["replay"]["safety_regression"])
        self.assertEqual(
            reviewed["intervention"]["payload"]["intervention_hash"],
            reviewed["replay"]["intervention"]["intervention_hash"],
        )

        activated = self.engine.activate_hackathon_intervention(
            {
                "tenant_id": "hackathon",
                "intervention_id": stored["intervention_id"],
                "reviewer_id": "reviewer-2",
                "note": "Promote only after verified replay.",
            }
        )
        self.assertEqual(activated["intervention"]["status"], "active")
        self.assertEqual(activated["procedural_policy"]["status"], "active")
        self.assertEqual(len(activated["intervention"]["payload"]["review_history"]), 1)

        actions = [item["action"] for item in self.store.list_audit("hackathon", limit=50)]
        self.assertIn("intervention.write", actions)
        self.assertIn("policy.review", actions)

    def test_policy_defaults_to_candidate_and_requires_valid_transitions(self):
        policy = self.store.add_policy(
            {
                "tenant_id": "hackathon",
                "body": "Require fresh evidence before fulfilment.",
                "title": "Evidence gate",
            }
        )
        self.assertEqual(policy["status"], "candidate")
        with self.assertRaisesRegex(ValueError, "invalid policy transition"):
            self.store.transition_policy(policy["policy_id"], "active", "reviewer")
        approved = self.store.transition_policy(policy["policy_id"], "approved", "reviewer")
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(self.store.list_policies("hackathon", status="active"), [])

    def test_failed_replay_cannot_activate_intervention(self):
        prepared = self.engine.prepare_hackathon_case(
            {"tenant_id": "hackathon", "case_id": "eval-012", "mode": "frozen"}
        )
        intervention_id = prepared["stored_intervention"]["intervention_id"]
        reviewed = self.engine.review_hackathon_intervention(
            {
                "tenant_id": "hackathon",
                "intervention_id": intervention_id,
                "decision": "approved",
                "reviewer_id": "reviewer-1",
                "mode": "frozen",
            }
        )
        self.assertFalse(reviewed["replay"]["verified_safe_recovery"])
        with self.assertRaisesRegex(ValueError, "verified safe replay"):
            self.engine.activate_hackathon_intervention(
                {
                    "tenant_id": "hackathon",
                    "intervention_id": intervention_id,
                    "reviewer_id": "reviewer-2",
                }
            )

    def test_active_policy_transfers_to_separate_shadow_case(self):
        prepared = self.engine.prepare_hackathon_case(
            {"tenant_id": "hackathon", "case_id": "eval-006", "mode": "frozen"}
        )
        intervention_id = prepared["stored_intervention"]["intervention_id"]
        self.engine.review_hackathon_intervention(
            {
                "tenant_id": "hackathon",
                "intervention_id": intervention_id,
                "decision": "approved",
                "reviewer_id": "reviewer-1",
                "mode": "frozen",
            }
        )
        activated = self.engine.activate_hackathon_intervention(
            {
                "tenant_id": "hackathon",
                "intervention_id": intervention_id,
                "reviewer_id": "reviewer-2",
            }
        )
        transfer = ShadowTransferEvaluator().evaluate(activated["procedural_policy"])
        self.assertTrue(transfer["outside_primary_benchmark"])
        self.assertFalse(transfer["original"]["task_success"])
        self.assertTrue(transfer["verified_safe_transfer"])
        self.assertEqual(
            transfer["replay"]["simulation"]["config_diff"],
            {"quantity_constraint": {"before": False, "after": True}},
        )


class HackathonApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = build_server(
            host="127.0.0.1",
            port=0,
            db_path=str(Path(self.tmp.name) / "api.db"),
            seed=False,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.RequestHandlerClass.engine.store.close()
        self.server.server_close()
        self.tmp.cleanup()

    def test_ui_state_and_prepare_api(self):
        with self.opener.open(self.base + "/", timeout=2) as response:
            html = response.read().decode("utf-8")
        self.assertIn("Enterprise resource provisioning", html)

        with self.opener.open(self.base + "/hackathon/state", timeout=2) as response:
            state = json.load(response)
        self.assertTrue(state["benchmark"]["valid"])
        self.assertEqual(len(state["cases"]), 15)

        request = urllib.request.Request(
            self.base + "/hackathon/cases/prepare",
            data=json.dumps(
                {"tenant_id": "hackathon", "case_id": "eval-006", "mode": "frozen"}
            ).encode("utf-8"),
            headers={"content-type": "application/json"},
            method="POST",
        )
        with self.opener.open(request, timeout=2) as response:
            prepared = json.load(response)
        self.assertEqual(prepared["stored_intervention"]["status"], "candidate")
        self.assertTrue(prepared["approval_required"])

    def test_ui_exposes_safe_live_explainability(self):
        with self.opener.open(
            self.base + "/hackathon/external-validity", timeout=2
        ) as response:
            payload = json.load(response)
        self.assertEqual(payload["status"], "available")
        self.assertEqual(payload["provider"]["name"], "Groq")
        self.assertEqual(len(payload["cases"]), 12)
        self.assertNotIn('"prompt"', json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
