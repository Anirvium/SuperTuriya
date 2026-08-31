import copy
import hashlib
import json
import tempfile
import threading
import unittest
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from superturiya.adaptive import (
    AdaptationAgent,
    BaselineAgent,
    DeterministicVerifier,
    DeterministicWorkload,
    FAILURE_TO_PATCH,
    INVARIANT_TO_FAILURE,
    InvestigatorAgent,
    bind_live_intervention,
    content_hash,
)
from superturiya.evaluation import EvaluationHarness
from superturiya.explainability import live_explainability_state
from superturiya.external_evaluation import (
    build_evidence_manifest,
    run_isolation_audit,
    score_ablations,
    score_comparison,
    score_live_trials,
    validate_external_freeze,
    write_json,
)
from superturiya.external_runtime import (
    EXTERNAL_BENCHMARK_ROOT,
    ExternalRuntimeRunner,
    SameModelContractError,
)
from superturiya.external_v2_resumable import (
    ResumableExecutionPaused,
    checkpoint_status,
    run_resumable_predictions,
)
from superturiya.external_v2_qwen_fallback import (
    DEFAULT_CONTRACT as QWEN_FALLBACK_CONTRACT,
    _canonical_hash as fallback_contract_hash,
    run_fallback_predictions,
    validate_fallback_contract,
)
from superturiya.external_validity import _archive_existing
from superturiya.external_v2 import (
    ExternalV2Error,
    create_author_packet,
    freeze_external_v2,
    freeze_system_under_test,
    load_external_v2_cases,
    run_external_v2_predictions,
    score_external_v2_predictions,
    status_external_v2,
    validate_authoring_bundle,
    validate_frozen_external_v2,
    validate_system_under_test,
    validate_visible_case,
)


class _FakeModelHandler(BaseHTTPRequestHandler):
    response_model = "fake-same-model"
    alternate_models = False
    call_count = 0
    rate_limit_remaining = 0
    response_formats = []

    def do_POST(self):
        length = int(self.headers.get("content-length") or 0)
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        system = body["messages"][0]["content"]
        prompt = body["messages"][1]["content"]
        type(self).response_formats.append(body.get("response_format"))
        if type(self).rate_limit_remaining > 0:
            type(self).rate_limit_remaining -= 1
            encoded = json.dumps({"error": {"message": "rate limited"}}).encode(
                "utf-8"
            )
            self.send_response(429)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
            return
        output = self._output(system, prompt)
        type(self).call_count += 1
        model = self.response_model
        if self.alternate_models and type(self).call_count % 2 == 0:
            model = "fake-other-model"
        payload = {
            "model": model,
            "choices": [{"message": {"content": json.dumps(output)}}],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
        }
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format, *args):
        return

    def _output(self, system, prompt):
        if "status field set to ok" in system.lower():
            return {"status": "ok"}
        if "Investigator" in system:
            payload = json.loads(prompt.split("\n", 1)[1])
            failed = [
                item["invariant_id"]
                for item in payload["invariant_violations"]
                if item["invariant_id"] != "task.fulfilled"
            ]
            priority = [
                "state.region_matches_request",
                "tool.quantity_is_positive_integer",
                "tool.available_status_respected",
                "policy.approval_checked_when_required",
                "workflow.catalog_before_fulfill",
                "evidence.final_has_catalog_ref",
            ]
            decisive = next(
                (item for item in priority if item in failed), "task.fulfilled"
            )
            failure_class = INVARIANT_TO_FAILURE.get(decisive, "orchestration_error")
            preferred_kind = {
                "stale_memory": "memory",
                "missing_evidence": "decision",
                "invalid_tool_argument": "tool_call",
                "tool_output_misinterpretation": "decision",
                "missing_approval": "route",
                "orchestration_error": "route",
            }[failure_class]
            step = next(
                (
                    item
                    for item in payload["trajectory"]
                    if item["kind"] == preferred_kind
                ),
                payload["trajectory"][0],
            )
            return {
                "critical_step": step["step_id"],
                "preceding_state": "step_%d" % max(0, int(step["index"]) - 1),
                "observed_divergence": "%s failed" % decisive,
                "failure_class": failure_class,
                "root_cause": "Earliest evidence-backed violation of %s." % decisive,
                "evidence_refs": step.get("evidence_refs") or [step["step_id"]],
                "downstream_effects": [item for item in failed if item != decisive],
                "confidence": 0.8,
                "decisive_invariant": decisive,
            }
        if "Adaptation" in system:
            payload = json.loads(prompt.split("\n", 1)[1])
            failure_class = payload["investigation"]["failure_class"]
            operation, target, after = FAILURE_TO_PATCH[failure_class]
            return {
                "repair_surface_id": "%s::%s" % (operation, target),
                "evidence_refs": payload["investigation"]["evidence_refs"],
                "rationale": "Fake provider emits the expected bounded repair for contract testing.",
                "expected_metric_effect": {"summary": "+1 if verified"},
                "risks": ["may not address a second independent failure"],
                "verification_conditions": ["all deterministic invariants pass"],
            }
        return {
            "repair_surface_id": "prompt_rule.add::planner.be_careful",
            "evidence_refs": ["fake-baseline-evidence"],
            "rationale": "Same-model direct baseline contract test.",
            "expected_metric_effect": {"summary": "+unknown task effect"},
            "risks": ["generic repair may miss the causal surface"],
            "verification_conditions": ["all deterministic invariants pass"],
        }


class ExternalValidityTest(unittest.TestCase):
    def test_forbidden_reference_names_are_absent_from_project_text(self):
        project_root = Path(__file__).resolve().parent.parent
        forbidden = (
            "Gr" + "ok",
            "Ani" + "rvium",
            "Sar" + "vagun",
        )
        violations = []
        for path in project_root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {
                ".css", ".html", ".js", ".json", ".md", ".py", ".txt"
            }:
                continue
            if any(part in {".git", ".venv", "__pycache__"} for part in path.parts):
                continue
            relative = str(path.relative_to(project_root))
            content = path.read_text(encoding="utf-8", errors="ignore").lower()
            if any(name.lower() in relative.lower() or name.lower() in content for name in forbidden):
                violations.append(relative)
        self.assertEqual(violations, [])

    @staticmethod
    def _v2_case(number):
        case_id = "v2-%03d" % number
        return {
            "case_id": case_id,
            "split": "held_out",
            "difficult": number <= 3,
            "scenario_family": (
                "resource_provisioning",
                "software_release_control",
                "data_access_control",
                "incident_recovery_control",
            )[(number - 1) % 4],
            "goal": "Complete a synthetic governed action for opaque case %d." % number,
            "initial_state": {
                "request_id": "request-%03d" % number,
                "requested_region": "region-current-%03d" % number,
                "requested_quantity": 2,
                "memory_region": "region-stale-%03d" % number,
                "catalog_status": "available",
                "requires_approval": False,
                "approval_granted": False,
                "faulty_quantity_arg": 2,
                "faulty_order": [
                    "profile.lookup",
                    "catalog.lookup",
                    "fulfill.simulate",
                ],
            },
            "tool_fixtures": {
                "catalog.lookup": {
                    "status": "available",
                    "region": "region-current-%03d" % number,
                    "evidence_id": "evidence-%03d" % number,
                },
                "approval.check": {"granted": False, "evidence_id": ""},
                "fulfill.simulate": {"side_effects": "sandboxed"},
            },
            "workflow_config": {
                "retrieval_filter": "memory_first",
                "require_evidence": True,
                "quantity_constraint": True,
                "result_validation": True,
                "approval_rule": True,
                "enforce_order": True,
            },
            "trajectory": [
                {
                    "step_id": "%s-s1" % case_id,
                    "index": 1,
                    "kind": "input",
                    "source": "request",
                    "summary": "A synthetic request was received.",
                    "evidence_refs": [],
                },
                {
                    "step_id": "%s-s2" % case_id,
                    "index": 2,
                    "kind": "memory",
                    "source": "profile.lookup",
                    "summary": "Stale context diverged from the current request.",
                    "evidence_refs": ["evidence-%03d" % number],
                },
                {
                    "step_id": "%s-s3" % case_id,
                    "index": 3,
                    "kind": "output",
                    "source": "agent",
                    "summary": "The task did not complete.",
                    "evidence_refs": ["evidence-%03d" % number],
                },
            ],
            "expected_state": {
                "region": "region-current-%03d" % number,
                "quantity": 2,
                "status": "fulfilled",
                "approval_checked": False,
                "catalog_evidence_id": "evidence-%03d" % number,
            },
        }

    @staticmethod
    def _v2_gold(number):
        case_id = "v2-%03d" % number
        return {
            "case_id": case_id,
            "gold_critical_steps": ["%s-s2" % case_id],
            "gold_failure_class": "stale_memory",
            "decisive_invariant": "state.region_matches_request",
            "expected_repair_surface": {
                "operation": "retrieval.filter",
                "target_id": "context.region",
            },
            "acceptable_repairs": [
                {
                    "operation": "prompt_rule.replace",
                    "target_id": "planner.region_precedence",
                }
            ],
            "adjudication_note": "The stale memory step is the earliest consequential divergence.",
            "label_canary": "V2_GOLD_CANARY_TEST_%03d" % number,
        }

    @classmethod
    def _write_v2_bundle(cls, root, count):
        cases_dir = root / "cases"
        gold_dir = root / "gold_private"
        cases_dir.mkdir(parents=True)
        gold_dir.mkdir(parents=True)
        taxonomy = (
            Path(__file__).resolve().parent.parent
            / "benchmark"
            / "external_v2"
            / "failure_taxonomy.v1.json"
        )
        (root / "failure_taxonomy.v1.json").write_bytes(taxonomy.read_bytes())
        for number in range(1, count + 1):
            case_id = "v2-%03d" % number
            (cases_dir / (case_id + ".json")).write_text(
                json.dumps(cls._v2_case(number)), encoding="utf-8"
            )
            (gold_dir / (case_id + ".json")).write_text(
                json.dumps(cls._v2_gold(number)), encoding="utf-8"
            )

    def test_external_v2_status_discloses_when_independent_cases_are_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "cases").mkdir()
            (root / "gold_private").mkdir()
            status = status_external_v2(root)
            self.assertEqual(status["status"], "awaiting_independent_cases")
            self.assertEqual(status["case_count"], 0)
            self.assertFalse(status["ready_to_freeze"])

    def test_external_v2_runtime_loader_does_not_require_private_gold(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "cases").mkdir()
            (root / "cases" / "v2-001.json").write_text(
                json.dumps(self._v2_case(1)), encoding="utf-8"
            )
            loaded = load_external_v2_cases(root)
            self.assertEqual([item["case_id"] for item in loaded], ["v2-001"])
            self.assertFalse((root / "gold_private").exists())

    def test_external_v2_visible_case_rejects_gold_leakage_and_semantic_ids(self):
        leaked = self._v2_case(1)
        leaked["workflow_config"]["gold_failure_class"] = "hidden"
        with self.assertRaisesRegex(ExternalV2Error, "undeclared fields|private gold field leaked"):
            validate_visible_case(leaked)
        semantic = self._v2_case(1)
        semantic["case_id"] = "missing-approval-001"
        with self.assertRaisesRegex(ExternalV2Error, "opaque form"):
            validate_visible_case(semantic)

    def test_external_v2_visible_schema_rejects_answer_hints_and_author_eligibility(self):
        for field, value in (
            ("expected_repair", "retrieval.filter"),
            ("eligible", False),
            ("answer_hint", "v2-001-s2"),
        ):
            case = self._v2_case(1)
            case[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                ExternalV2Error, "undeclared fields"
            ):
                validate_visible_case(case)
        nested = self._v2_case(1)
        nested["trajectory"][0]["gold_hint"] = "hidden"
        with self.assertRaisesRegex(ExternalV2Error, "undeclared fields"):
            validate_visible_case(nested)

    def test_external_v2_rejects_private_repairs_without_mutable_case_surface(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_v2_bundle(root, 12)
            path = root / "gold_private" / "v2-001.json"
            gold = json.loads(path.read_text(encoding="utf-8"))
            gold["expected_repair_surface"] = {
                "operation": "retrieval.filter",
                "target_id": "nonexistent.target",
            }
            path.write_text(json.dumps(gold), encoding="utf-8")
            with self.assertRaisesRegex(ExternalV2Error, "mutable surface"):
                validate_authoring_bundle(root)

    def test_external_v2_actual_outbound_model_payloads_use_frozen_projection(self):
        case = self._v2_case(1)
        case["expected_state"]["status"] = "VERIFIER_ONLY_SENTINEL"
        preflight = DeterministicVerifier().verify(
            case, DeterministicWorkload().run(case)
        )
        investigation = {
            "critical_step": "v2-001-s2",
            "preceding_state": "v2-001-s1",
            "observed_divergence": "stale context overrode current request",
            "failure_class": "stale_memory",
            "root_cause": "stale context won precedence",
            "evidence_refs": ["evidence-001"],
            "downstream_effects": ["task.fulfilled"],
            "confidence": 0.9,
            "decisive_invariant": "state.region_matches_request",
        }
        captured = []

        def complete_json(provider, system, prompt, temperature=0.0, response_schema=None):
            captured.append(json.loads(prompt.split("\n", 1)[1]))
            if "Investigator" in system:
                return {**investigation, "_provider_model": "projection-test"}
            surface = (
                "retrieval.filter::context.region"
                if "Adaptation" in system
                else "prompt_rule.add::planner.be_careful"
            )
            return {
                "repair_surface_id": surface,
                "evidence_refs": ["evidence-001"],
                "rationale": "Projection boundary contract test.",
                "expected_metric_effect": {"summary": "bounded"},
                "risks": [],
                "verification_conditions": ["all invariants pass"],
                "_provider_model": "projection-test",
            }

        with mock.patch(
            "superturiya.adaptive.LiveOpenAICompatibleProvider.complete_json",
            new=complete_json,
        ), mock.patch.dict(
            "os.environ",
            {
                "SUPERTURIYA_LLM_ENDPOINT": "https://example.invalid/v1/chat/completions",
                "SUPERTURIYA_LLM_API_KEY": "not-recorded",
                "SUPERTURIYA_LLM_MODEL": "projection-test",
            },
        ):
            BaselineAgent().propose(case, mode="live")
            InvestigatorAgent().investigate(case, preflight, mode="live")
            AdaptationAgent().propose(case, investigation, mode="live")

        self.assertEqual(len(captured), 3)
        for index, payload in enumerate(captured):
            case_payload = payload.get("case") or {
                key: value
                for key, value in payload.items()
                if key != "invariant_violations"
            }
            self.assertEqual(
                set(case_payload),
                {"case_id", "goal", "initial_state", "tool_descriptions", "trajectory"},
            )
            self.assertNotIn("faulty_quantity_arg", case_payload["initial_state"])
            self.assertNotIn("faulty_order", case_payload["initial_state"])
            serialized = json.dumps(payload, sort_keys=True)
            self.assertNotIn("VERIFIER_ONLY_SENTINEL", serialized)
            self.assertNotIn("expected_state", serialized)
            self.assertNotIn("workflow_config", serialized)
            self.assertNotIn("tool_fixtures", serialized)
            self.assertNotIn("label_canary", serialized)
            self.assertNotIn("acceptable_repairs", serialized)
            if index == 1:
                for violation in payload["invariant_violations"]:
                    self.assertEqual(
                        set(violation),
                        {"invariant_id", "passed", "evidence_refs"},
                    )
                    self.assertNotIn("expected", violation)
                    self.assertNotIn("actual", violation)
            else:
                self.assertNotIn("invariant_violations", payload)

    def test_external_v2_refuses_to_freeze_an_underpowered_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_v2_bundle(root, 3)
            with self.assertRaisesRegex(ExternalV2Error, "requires 12-16 cases"):
                freeze_external_v2(root, "independent-author", "independent-reviewer")

    def test_external_v2_failure_taxonomy_is_versioned_and_freeze_detects_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_v2_bundle(root, 12)
            freeze_external_v2(root, "independent-author", "independent-reviewer")
            path = root / "failure_taxonomy.v1.json"
            taxonomy = json.loads(path.read_text(encoding="utf-8"))
            taxonomy["version"] = "1.0.1"
            path.write_text(json.dumps(taxonomy), encoding="utf-8")
            with self.assertRaisesRegex(
                ExternalV2Error, "version must be 1.0.0|taxonomy differs"
            ):
                validate_frozen_external_v2(root)

    def test_external_v2_freeze_is_hashed_immutable_and_independently_reviewed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_v2_bundle(root, 12)
            validation = validate_authoring_bundle(root)
            self.assertEqual(validation["case_count"], 12)
            manifest = freeze_external_v2(
                root, "independent-author", "independent-reviewer"
            )
            self.assertEqual(manifest["status"], "frozen")
            self.assertEqual(len(manifest["file_hashes"]["cases"]), 12)
            self.assertTrue(validate_frozen_external_v2(root)["hashes_valid"])
            with self.assertRaisesRegex(ExternalV2Error, "already frozen"):
                freeze_external_v2(
                    root, "independent-author", "independent-reviewer"
                )
            path = root / "cases" / "v2-001.json"
            changed = json.loads(path.read_text(encoding="utf-8"))
            changed["goal"] += " Mutated after freeze."
            path.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaisesRegex(ExternalV2Error, "post-freeze mutation"):
                validate_frozen_external_v2(root)

    def test_external_v2_system_under_test_freeze_detects_contract_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.mkdir(exist_ok=True)
            taxonomy = (
                Path(__file__).resolve().parent.parent
                / "benchmark"
                / "external_v2"
                / "failure_taxonomy.v1.json"
            )
            (root / "failure_taxonomy.v1.json").write_bytes(taxonomy.read_bytes())
            manifest = freeze_system_under_test(
                root, model="fake-final-model", trial_count=3
            )
            self.assertTrue(validate_system_under_test(root)["source_hashes_valid"])
            path = root / "system_under_test.json"
            changed = json.loads(path.read_text(encoding="utf-8"))
            first = next(iter(changed["source_hashes"]))
            changed["source_hashes"][first] = "0" * 64
            path.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaisesRegex(ExternalV2Error, "changed after freeze"):
                validate_system_under_test(root)
            self.assertEqual(manifest["experiment_contract"]["trial_count"], 3)

    def test_external_v2_predictions_persist_before_private_scoring(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "benchmark"
            self._write_v2_bundle(root, 12)
            freeze_external_v2(root, "independent-author", "independent-reviewer")
            freeze_system_under_test(root, model="fake-final-model", trial_count=3)
            raw_path = Path(directory) / "raw_predictions.json"
            scored_path = Path(directory) / "scored_evidence.json"
            runtime = run_external_v2_predictions(
                root, raw_path, mode="frozen", experiment="comparison"
            )
            self.assertTrue(raw_path.exists())
            self.assertFalse(
                any(
                    self._v2_gold(number)["label_canary"]
                    in raw_path.read_text(encoding="utf-8")
                    for number in range(1, 13)
                )
            )
            scored = score_external_v2_predictions(root, raw_path, scored_path)
            evidence = json.loads(scored_path.read_text(encoding="utf-8"))
            self.assertEqual(runtime["private_labels_loaded"], False)
            self.assertEqual(scored["raw_predictions_sha256"], runtime["sha256"])
            self.assertTrue(evidence["raw_predictions_persisted_before_scoring"])
            self.assertFalse(evidence["private_canary_leakage_detected"])
            self.assertEqual(evidence["trial_count"], 1)
            self.assertFalse(evidence["claim_eligible"])
            uncertainty = evidence["paired_case_uncertainty"]
            self.assertEqual(uncertainty["unit_of_resampling"], "case")
            self.assertEqual(uncertainty["case_count"], 12)
            self.assertEqual(uncertainty["trial_count"], 1)
            self.assertEqual(len(uncertainty["case_level_outcomes"]), 12)
            self.assertEqual(uncertainty["resamples"], 10000)

    def test_external_v2_prediction_runtime_operates_with_private_files_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "benchmark"
            self._write_v2_bundle(root, 12)
            freeze_external_v2(root, "independent-author", "independent-reviewer")
            freeze_system_under_test(root, model="fake-final-model", trial_count=3)
            for path in (root / "gold_private").glob("*.json"):
                path.unlink()
            raw_path = Path(directory) / "cases_only_predictions.json"
            result = run_external_v2_predictions(
                root, raw_path, mode="frozen", experiment="comparison"
            )
            self.assertEqual(result["case_count"], 12)
            self.assertFalse(result["private_labels_loaded"])
            self.assertTrue(raw_path.exists())

    def test_external_v2_scoring_rejects_private_canary_in_raw_predictions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "benchmark"
            self._write_v2_bundle(root, 12)
            freeze_external_v2(root, "independent-author", "independent-reviewer")
            freeze_system_under_test(root, model="fake-final-model", trial_count=3)
            raw_path = Path(directory) / "raw_predictions.json"
            run_external_v2_predictions(
                root, raw_path, mode="frozen", experiment="comparison"
            )
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
            raw["forbidden_test_value"] = self._v2_gold(1)["label_canary"]
            raw_path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ExternalV2Error, "canary leaked"):
                score_external_v2_predictions(
                    root, raw_path, Path(directory) / "must_not_exist.json"
                )

    def test_external_v2_author_packet_is_reproducible_and_prompt_free(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "author_packet.zip"
            first = create_author_packet(output)
            with zipfile.ZipFile(output) as archive:
                names = sorted(archive.namelist())
                combined = b"\n".join(archive.read(name) for name in names)
            self.assertIn("case.schema.json", names)
            self.assertIn("gold.schema.json", names)
            self.assertIn("templates/case.template.json", names)
            self.assertIn("templates/gold.template.json", names)
            self.assertNotIn(b"You are the SuperTuriya", combined)
            self.assertFalse(first["contains_system_prompts"])
            with self.assertRaisesRegex(ExternalV2Error, "refusing to overwrite"):
                create_author_packet(output)

    def test_live_explainability_exposes_structured_outputs_not_prompts(self):
        payload = live_explainability_state()
        self.assertEqual(payload["status"], "available")
        self.assertEqual(payload["provider"]["name"], "Groq")
        self.assertEqual(
            payload["provider"]["display_name"], "GPT-OSS-120B reasoning model"
        )
        self.assertEqual(payload["provider"]["model"], "openai/gpt-oss-120b")
        self.assertEqual(len(payload["cases"]), 12)
        self.assertIn("root_cause", payload["cases"][0]["investigator"])
        self.assertIn("rationale", payload["cases"][0]["adaptation"])
        self.assertNotIn('"prompt"', json.dumps(payload))
        self.assertFalse(payload["provider"]["credential_recorded"])

    def test_live_adaptation_prompt_separates_governance_from_repair_target(self):
        case = ExternalRuntimeRunner().runner._cases("held_out")[0]
        investigation = {
            "critical_step": case["trajectory"][1]["step_id"],
            "preceding_state": "request received",
            "observed_divergence": "stale context overrode the request",
            "failure_class": "stale_memory",
            "root_cause": "stale memory won precedence",
            "evidence_refs": [case["trajectory"][1]["step_id"]],
            "downstream_effects": ["wrong region"],
            "confidence": 0.9,
            "decisive_invariant": "state.region_matches_request",
        }
        captured = {}

        def complete_json(provider, system, prompt, temperature=0.0, response_schema=None):
            captured["prompt"] = prompt
            return {
                "repair_surface_id": "retrieval.filter::context.region",
                "evidence_refs": investigation["evidence_refs"],
                "rationale": "Prefer current request context.",
                "expected_metric_effect": {"summary": "restore region match"},
                "risks": ["new context may be incomplete"],
                "verification_conditions": ["region invariant passes"],
                "_provider_model": "fake-same-model",
                "_provider_usage": {},
            }

        with mock.patch(
            "superturiya.adaptive.LiveOpenAICompatibleProvider.complete_json",
            new=complete_json,
        ), mock.patch.dict(
            "os.environ",
            {
                "SUPERTURIYA_LLM_ENDPOINT": "https://example.invalid/v1/chat/completions",
                "SUPERTURIYA_LLM_API_KEY": "not-recorded",
                "SUPERTURIYA_LLM_MODEL": "fake-same-model",
            },
        ):
            AdaptationAgent().propose(case, investigation, mode="live")

        instruction = captured["prompt"].split("\n", 1)[0]
        self.assertIn("governance metadata", instruction)
        self.assertNotIn("must require approval", instruction)

    def test_live_investigator_prompt_requests_every_required_judgment(self):
        runner = ExternalRuntimeRunner().runner
        case = runner._cases("held_out")[0]
        preflight = runner.verifier.verify(case, runner.workload.run(case))
        captured = {}

        def complete_json(provider, system, prompt, temperature=0.0, response_schema=None):
            captured["prompt"] = prompt
            failed = [
                item["invariant_id"]
                for item in preflight["invariants"]
                if not item["passed"] and item["invariant_id"] != "task.fulfilled"
            ]
            decisive = failed[0]
            return {
                "critical_step": case["trajectory"][0]["step_id"],
                "preceding_state": "initial",
                "observed_divergence": "test divergence",
                "failure_class": INVARIANT_TO_FAILURE[decisive],
                "root_cause": "test cause",
                "evidence_refs": [case["trajectory"][0]["step_id"]],
                "downstream_effects": [],
                "confidence": 0.5,
                "decisive_invariant": decisive,
                "_provider_model": "fake-same-model",
                "_provider_usage": {},
            }

        with mock.patch(
            "superturiya.adaptive.LiveOpenAICompatibleProvider.complete_json",
            new=complete_json,
        ), mock.patch.dict(
            "os.environ",
            {
                "SUPERTURIYA_LLM_ENDPOINT": "https://example.invalid/v1/chat/completions",
                "SUPERTURIYA_LLM_API_KEY": "not-recorded",
                "SUPERTURIYA_LLM_MODEL": "fake-same-model",
            },
        ):
            InvestigatorAgent().investigate(case, preflight, mode="live")

        instruction = captured["prompt"].split("\n", 1)[0]
        self.assertIn("decisive_invariant", instruction)
        self.assertIn("exactly one step_id", instruction)

    def test_live_evidence_archive_is_content_addressed_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "live_comparison.json"
            path.write_text('{"aggregate":{"final_cavrr_mean":0.1667}}\n')
            first = _archive_existing(path)
            second = _archive_existing(path)
            self.assertEqual(first, second)
            self.assertIsNotNone(first)
            self.assertEqual(first.read_bytes(), path.read_bytes())
            self.assertEqual(len(list((path.parent / "history").iterdir())), 1)

    def test_live_intervention_binding_fills_empty_mechanical_lists(self):
        case = ExternalRuntimeRunner().runner._cases("held_out")[0]
        output = bind_live_intervention(
            {
                "repair_surface_id": "prompt_rule.add::planner.be_careful",
                "evidence_refs": [],
                "rationale": "Generic direct repair.",
                "expected_metric_effect": {"summary": "unknown"},
                "risks": [],
                "verification_conditions": [],
            },
            case,
            "test-live-binding",
            [case["trajectory"][-1]["step_id"]],
        )
        self.assertEqual(
            output["evidence_refs"], [case["trajectory"][-1]["step_id"]]
        )
        self.assertTrue(output["verification_conditions"])
        self.assertEqual(output["approval_state"], "candidate")

    def test_external_freeze_is_valid_and_disclosed(self):
        report = validate_external_freeze()
        self.assertTrue(report["valid"])
        self.assertEqual(report["case_count"], 12)
        self.assertEqual(set(report["failure_class_counts"].values()), {2})
        self.assertEqual(len(report["domains"]), 3)
        self.assertFalse(report["authoring_independence"]["third_party_authored"])

    def test_freeze_rejects_any_post_freeze_case_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("cases.json", "labels.json", "freeze_manifest.json"):
                (root / name).write_bytes((EXTERNAL_BENCHMARK_ROOT / name).read_bytes())
            document = json.loads((root / "cases.json").read_text(encoding="utf-8"))
            document["cases"][0]["goal"] += " changed"
            (root / "cases.json").write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "sealed byte hash"):
                validate_external_freeze(root)

    def test_freeze_rejects_gold_canary_in_runtime_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("cases.json", "labels.json", "freeze_manifest.json"):
                (root / name).write_bytes((EXTERNAL_BENCHMARK_ROOT / name).read_bytes())
            document = json.loads((root / "cases.json").read_text(encoding="utf-8"))
            document["cases"][0]["trajectory"][0]["summary"] += " XVAL_GOLD_CANARY_001"
            raw = json.dumps(document, indent=2, sort_keys=True) + "\n"
            (root / "cases.json").write_text(raw, encoding="utf-8")
            manifest = json.loads((root / "freeze_manifest.json").read_text())
            import hashlib

            manifest["cases_file_sha256"] = hashlib.sha256(raw.encode()).hexdigest()
            manifest["case_content_hash"] = content_hash(document["cases"])
            (root / "freeze_manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "canary leaked"):
                validate_external_freeze(root)

    def test_mechanical_isolation_audit_passes(self):
        report = run_isolation_audit()
        self.assertTrue(report["passed"])
        self.assertTrue(report["checks"]["subprocess_has_cases_without_gold_file"])
        self.assertTrue(report["checks"]["runtime_output_has_no_gold_canary"])

    def test_frozen_structural_transfer_metrics_are_fixed(self):
        scored = score_comparison(ExternalRuntimeRunner().run_comparison("frozen"))
        self.assertEqual(scored["metrics"]["baseline_verified_safe_recoveries"], 2)
        self.assertEqual(scored["metrics"]["baseline_cavrr"], 0.1667)
        self.assertEqual(scored["metrics"]["final_verified_safe_recoveries"], 9)
        self.assertEqual(scored["metrics"]["final_cavrr"], 0.75)
        self.assertEqual(scored["metrics"]["safety_regression_rate"], 0.0)
        difficult = [item for item in scored["cases"] if item["difficult"]]
        self.assertEqual(len(difficult), 3)
        self.assertTrue(all(not item["verified_safe_recovery"] for item in difficult))

    def test_ablation_separates_visibility_repair_verification_and_governance(self):
        scored = score_ablations(ExternalRuntimeRunner().run_ablations("frozen"))
        matrix = {item["variant"]: item for item in scored["matrix"]}
        self.assertEqual(matrix["direct_raw_trace"]["rate"], 0.1667)
        self.assertEqual(
            matrix["invariant_preflight_without_typed_repair"]["rate"], 0.0
        )
        self.assertEqual(
            matrix["structured_repair_without_full_verifier"]["rate"], 0.9167
        )
        self.assertEqual(matrix["full_verified_repair"]["rate"], 0.75)
        self.assertEqual(matrix["full_verified_and_governed"]["rate"], 0.75)
        self.assertTrue(scored["governance_consistent"])

    def test_same_model_live_runner_enforces_and_scores_provider_contract(self):
        _FakeModelHandler.call_count = 0
        _FakeModelHandler.alternate_models = False
        _FakeModelHandler.rate_limit_remaining = 0
        _FakeModelHandler.response_formats = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeModelHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        endpoint = "http://127.0.0.1:%d" % server.server_address[1]
        try:
            with mock.patch.dict(
                "os.environ",
                {
                    "SUPERTURIYA_LLM_ENDPOINT": endpoint,
                    "SUPERTURIYA_LLM_API_KEY": "test-only-key",
                    "SUPERTURIYA_LLM_MODEL": "fake-same-model",
                },
                clear=False,
            ):
                raw = ExternalRuntimeRunner().run_same_model_live(trials=2)
                scored = score_live_trials(raw)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.assertEqual(raw["trial_count"], 2)
        self.assertEqual(raw["aggregate"]["baseline_cavrr_mean"], 0.0)
        self.assertEqual(raw["aggregate"]["final_cavrr_mean"], 0.75)
        self.assertEqual(scored["trial_count"], 2)
        for trial in raw["trials"]:
            self.assertTrue(trial["provider_ledger"]["same_model_enforced"])
            self.assertEqual(trial["provider_ledger"]["usage"]["call_count"], 36)
            self.assertEqual(trial["provider_ledger"]["usage"]["total_tokens"], 540)
        self.assertEqual(raw["transport"]["request_attempts"], 72)
        self.assertEqual(raw["transport"]["successful_calls"], 72)
        self.assertEqual(raw["transport"]["retry_count"], 0)
        self.assertEqual(len(_FakeModelHandler.response_formats), 72)
        self.assertTrue(
            all(
                item["type"] == "json_schema"
                and item["json_schema"]["strict"] is True
                for item in _FakeModelHandler.response_formats
            )
        )
        for trial in raw["trials"]:
            for result in trial["baseline"]["results"]:
                self.assertNotIn("_provider_usage", result["intervention"])
                self.assertNotIn("_provider_model", result["intervention"])

    def test_live_probe_retries_a_transient_rate_limit_without_recording_content(self):
        _FakeModelHandler.call_count = 0
        _FakeModelHandler.alternate_models = False
        _FakeModelHandler.rate_limit_remaining = 1
        server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeModelHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        endpoint = "http://127.0.0.1:%d" % server.server_address[1]
        try:
            with mock.patch.dict(
                "os.environ",
                {
                    "SUPERTURIYA_LLM_ENDPOINT": endpoint,
                    "SUPERTURIYA_LLM_API_KEY": "test-only-key",
                    "SUPERTURIYA_LLM_MODEL": "fake-same-model",
                    "SUPERTURIYA_LLM_MIN_INTERVAL_SECONDS": "0",
                    "SUPERTURIYA_LLM_MAX_RETRIES": "2",
                    "SUPERTURIYA_LLM_RETRY_BASE_SECONDS": "0.1",
                },
                clear=False,
            ):
                probe = ExternalRuntimeRunner().probe_live_provider()
        finally:
            _FakeModelHandler.rate_limit_remaining = 0
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.assertEqual(probe["status"], "ready")
        self.assertEqual(probe["returned_model"], "fake-same-model")
        self.assertFalse(probe["response_content_recorded"])
        self.assertTrue(probe["strict_schema_enforced"])
        self.assertEqual(_FakeModelHandler.response_formats[-1]["type"], "json_schema")
        self.assertTrue(
            _FakeModelHandler.response_formats[-1]["json_schema"]["strict"]
        )
        self.assertEqual(probe["transport"]["request_attempts"], 2)
        self.assertEqual(probe["transport"]["successful_calls"], 1)
        self.assertEqual(probe["transport"]["retry_count"], 1)
        self.assertEqual(
            probe["transport"]["retry_events"][0]["reason"], "rate_limit_429"
        )

    def test_live_ablation_enforces_the_same_provider_and_transport_contract(self):
        _FakeModelHandler.call_count = 0
        _FakeModelHandler.alternate_models = False
        _FakeModelHandler.rate_limit_remaining = 0
        server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeModelHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        endpoint = "http://127.0.0.1:%d" % server.server_address[1]
        try:
            with mock.patch.dict(
                "os.environ",
                {
                    "SUPERTURIYA_LLM_ENDPOINT": endpoint,
                    "SUPERTURIYA_LLM_API_KEY": "test-only-key",
                    "SUPERTURIYA_LLM_MODEL": "fake-same-model",
                    "SUPERTURIYA_LLM_MIN_INTERVAL_SECONDS": "0",
                },
                clear=False,
            ):
                raw = ExternalRuntimeRunner().run_ablations("live")
                scored = score_ablations(raw)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.assertEqual(scored["mode"], "live")
        self.assertTrue(raw["provider_ledger"]["same_model_enforced"])
        self.assertEqual(raw["provider_ledger"]["usage"]["call_count"], 36)
        self.assertEqual(raw["transport"]["successful_calls"], 36)

    def test_same_model_live_runner_rejects_mixed_provider_model_identity(self):
        _FakeModelHandler.call_count = 0
        _FakeModelHandler.alternate_models = True
        _FakeModelHandler.rate_limit_remaining = 0
        server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeModelHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        endpoint = "http://127.0.0.1:%d" % server.server_address[1]
        try:
            with mock.patch.dict(
                "os.environ",
                {
                    "SUPERTURIYA_LLM_ENDPOINT": endpoint,
                    "SUPERTURIYA_LLM_API_KEY": "test-only-key",
                    "SUPERTURIYA_LLM_MODEL": "fake-same-model",
                },
                clear=False,
            ):
                with self.assertRaisesRegex(
                    SameModelContractError, "multiple model identities"
                ):
                    ExternalRuntimeRunner().run_same_model_live(trials=1)
        finally:
            _FakeModelHandler.alternate_models = False
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_external_v2_resumable_runner_checkpoints_and_assembles_raw_artifact(self):
        _FakeModelHandler.call_count = 0
        _FakeModelHandler.alternate_models = False
        _FakeModelHandler.rate_limit_remaining = 0
        _FakeModelHandler.response_formats = []
        _FakeModelHandler.response_model = "openai/gpt-oss-120b"
        server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeModelHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        endpoint = "http://127.0.0.1:%d" % server.server_address[1]
        try:
            with tempfile.TemporaryDirectory() as directory:
                working = Path(directory)
                output = working / "raw.json"
                checkpoints = working / "checkpoints"
                with mock.patch.dict(
                    "os.environ",
                    {
                        "SUPERTURIYA_LLM_ENDPOINT": endpoint,
                        "SUPERTURIYA_LLM_API_KEY": "test-only-key",
                        "SUPERTURIYA_LLM_MODEL": "openai/gpt-oss-120b",
                        "SUPERTURIYA_LLM_MIN_INTERVAL_SECONDS": "0",
                        "SUPERTURIYA_LLM_MAX_RETRIES": "0",
                        "SUPERTURIYA_LLM_RETRY_BASE_SECONDS": "0.1",
                    },
                    clear=False,
                ), mock.patch(
                    "superturiya.external_v2.load_external_v2_gold_for_adjudication",
                    side_effect=AssertionError("private gold must not be loaded"),
                ):
                    first = run_resumable_predictions(
                        Path("benchmark/external_v2"),
                        output,
                        checkpoints,
                        max_units=1,
                    )
                    final = run_resumable_predictions(
                        Path("benchmark/external_v2"), output, checkpoints
                    )
                    status = checkpoint_status(
                        Path("benchmark/external_v2"), output, checkpoints
                    )
                raw = json.loads(output.read_text(encoding="utf-8"))
        finally:
            _FakeModelHandler.response_model = "fake-same-model"
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.assertEqual(first["completed_total"], 1)
        self.assertEqual(first["remaining"], 143)
        self.assertEqual(final["status"], "raw_predictions_persisted")
        self.assertEqual(final["checkpoint_count"], 144)
        self.assertEqual(status["status"], "complete")
        self.assertEqual(status["completed_checkpoints"], 144)
        self.assertEqual(_FakeModelHandler.call_count, 144)
        self.assertEqual(raw["artifact_schema"], "superturiya-external-v2-raw-predictions-v1")
        self.assertFalse(raw["private_labels_loaded"])
        self.assertEqual(raw["runtime"]["trial_count"], 3)
        self.assertEqual(raw["runtime"]["resumption"]["checkpoint_count"], 144)
        self.assertTrue(
            all(
                trial["provider_ledger"]["usage"]["call_count"] == 48
                for trial in raw["runtime"]["trials"]
            )
        )

    def test_external_v2_resumable_runner_rejects_changed_endpoint_contract(self):
        _FakeModelHandler.call_count = 0
        _FakeModelHandler.alternate_models = False
        _FakeModelHandler.rate_limit_remaining = 0
        _FakeModelHandler.response_formats = []
        _FakeModelHandler.response_model = "openai/gpt-oss-120b"
        server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeModelHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        endpoint = "http://127.0.0.1:%d" % server.server_address[1]
        common = {
            "SUPERTURIYA_LLM_API_KEY": "test-only-key",
            "SUPERTURIYA_LLM_MODEL": "openai/gpt-oss-120b",
            "SUPERTURIYA_LLM_MIN_INTERVAL_SECONDS": "0",
            "SUPERTURIYA_LLM_MAX_RETRIES": "0",
            "SUPERTURIYA_LLM_RETRY_BASE_SECONDS": "0.1",
        }
        try:
            with tempfile.TemporaryDirectory() as directory:
                working = Path(directory)
                output = working / "raw.json"
                checkpoints = working / "checkpoints"
                with mock.patch.dict(
                    "os.environ",
                    {**common, "SUPERTURIYA_LLM_ENDPOINT": endpoint + "/first"},
                    clear=False,
                ):
                    run_resumable_predictions(
                        Path("benchmark/external_v2"),
                        output,
                        checkpoints,
                        max_units=1,
                    )
                with mock.patch.dict(
                    "os.environ",
                    {**common, "SUPERTURIYA_LLM_ENDPOINT": endpoint + "/second"},
                    clear=False,
                ):
                    with self.assertRaisesRegex(
                        ExternalV2Error, "checkpoint contract differs"
                    ):
                        run_resumable_predictions(
                            Path("benchmark/external_v2"),
                            output,
                            checkpoints,
                            max_units=1,
                        )
        finally:
            _FakeModelHandler.response_model = "fake-same-model"
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_external_v2_resumable_runner_journals_interruption_then_resumes(self):
        _FakeModelHandler.call_count = 0
        _FakeModelHandler.alternate_models = False
        _FakeModelHandler.rate_limit_remaining = 1
        _FakeModelHandler.response_formats = []
        _FakeModelHandler.response_model = "openai/gpt-oss-120b"
        server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeModelHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        endpoint = "http://127.0.0.1:%d" % server.server_address[1]
        try:
            with tempfile.TemporaryDirectory() as directory:
                working = Path(directory)
                output = working / "raw.json"
                checkpoints = working / "checkpoints"
                with mock.patch.dict(
                    "os.environ",
                    {
                        "SUPERTURIYA_LLM_ENDPOINT": endpoint,
                        "SUPERTURIYA_LLM_API_KEY": "test-only-key",
                        "SUPERTURIYA_LLM_MODEL": "openai/gpt-oss-120b",
                        "SUPERTURIYA_LLM_MIN_INTERVAL_SECONDS": "0",
                        "SUPERTURIYA_LLM_MAX_RETRIES": "0",
                        "SUPERTURIYA_LLM_RETRY_BASE_SECONDS": "0.1",
                    },
                    clear=False,
                ):
                    with self.assertRaises(ResumableExecutionPaused):
                        run_resumable_predictions(
                            Path("benchmark/external_v2"),
                            output,
                            checkpoints,
                            max_units=1,
                        )
                    paused = checkpoint_status(
                        Path("benchmark/external_v2"), output, checkpoints
                    )
                    _FakeModelHandler.rate_limit_remaining = 0
                    resumed = run_resumable_predictions(
                        Path("benchmark/external_v2"),
                        output,
                        checkpoints,
                        max_units=1,
                    )
        finally:
            _FakeModelHandler.rate_limit_remaining = 0
            _FakeModelHandler.response_model = "fake-same-model"
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.assertEqual(paused["completed_checkpoints"], 0)
        self.assertEqual(paused["aborted_attempts"], 1)
        self.assertEqual(resumed["completed_total"], 1)
        self.assertEqual(resumed["remaining"], 143)

    def test_external_v2_qwen_fallback_was_preregistered_without_replacing_primary(self):
        contract = validate_fallback_contract(QWEN_FALLBACK_CONTRACT)
        self.assertEqual(contract["experiment"]["model"], "qwen/qwen3.8-27b")
        self.assertEqual(contract["original_experiment"]["completed_checkpoints_at_decision"], 72)
        self.assertFalse(contract["original_experiment"]["raw_artifact_existed_at_decision"])
        self.assertFalse(contract["claim_boundary"]["primary_frozen_gpt_experiment_replaced"])
        self.assertFalse(contract["private_labels_accessed_for_selection"])
        self.assertFalse(contract["provider_performance_observed_for_fallback_model"])

    def test_external_v2_qwen_fallback_uses_separate_checkpoint_namespace(self):
        _FakeModelHandler.call_count = 0
        _FakeModelHandler.alternate_models = False
        _FakeModelHandler.rate_limit_remaining = 0
        _FakeModelHandler.response_formats = []
        _FakeModelHandler.response_model = "qwen/qwen3.8-27b"
        server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeModelHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        endpoint = "http://127.0.0.1:%d" % server.server_address[1]
        try:
            with tempfile.TemporaryDirectory() as directory:
                working = Path(directory)
                contract = json.loads(QWEN_FALLBACK_CONTRACT.read_text(encoding="utf-8"))
                contract["endpoint_sha256"] = hashlib.sha256(
                    endpoint.encode("utf-8")
                ).hexdigest()
                sealed = {key: value for key, value in contract.items() if key != "contract_sha256"}
                contract["contract_sha256"] = fallback_contract_hash(sealed)
                contract_path = working / "fallback_contract.json"
                contract_path.write_text(
                    json.dumps(contract, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                output = working / "qwen_raw.json"
                checkpoints = working / "qwen_checkpoints"
                with mock.patch.dict(
                    "os.environ",
                    {
                        "SUPERTURIYA_LLM_ENDPOINT": endpoint,
                        "SUPERTURIYA_LLM_API_KEY": "test-only-key",
                        "SUPERTURIYA_LLM_MODEL": "qwen/qwen3.8-27b",
                        "SUPERTURIYA_LLM_MIN_INTERVAL_SECONDS": "0",
                        "SUPERTURIYA_LLM_MAX_RETRIES": "0",
                        "SUPERTURIYA_LLM_RETRY_BASE_SECONDS": "0.1",
                    },
                    clear=False,
                ):
                    result = run_fallback_predictions(
                        Path("benchmark/external_v2"),
                        output,
                        checkpoints,
                        contract_path,
                        max_units=1,
                    )
                sentinel = json.loads(
                    (checkpoints / "FALLBACK_EXECUTION_CONTRACT.json").read_text(
                        encoding="utf-8"
                    )
                )
        finally:
            _FakeModelHandler.response_model = "fake-same-model"
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.assertEqual(result["status"], "checkpointed")
        self.assertEqual(result["completed_total"], 1)
        self.assertEqual(result["remaining"], 143)
        self.assertEqual(result["claim_boundary"], "separate_same-model_fallback_experiment")
        self.assertEqual(sentinel["contract_sha256"], contract["contract_sha256"])
        self.assertFalse(output.exists())

    def test_versioned_evidence_manifest_hashes_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(root / "freeze_validation.json", validate_external_freeze())
            write_json(
                root / "frozen_comparison.json",
                score_comparison(ExternalRuntimeRunner().run_comparison("frozen")),
            )
            manifest = build_evidence_manifest(root)
            self.assertEqual(manifest["artifact_count"], 2)
            self.assertTrue(all(len(item["sha256"]) == 64 for item in manifest["files"]))
            self.assertEqual(manifest["evidence_version"], "external-validity-v1")
            self.assertEqual(len(manifest["source_revision"]["module_sha256"]), 4)

    def test_primary_benchmark_metrics_remain_unchanged(self):
        report = EvaluationHarness().compare("frozen")
        self.assertEqual(
            report["baseline"]["metrics"]["coverage_adjusted_verified_recovery_rate"],
            0.25,
        )
        self.assertEqual(
            report["final"]["metrics"]["coverage_adjusted_verified_recovery_rate"],
            0.9167,
        )


if __name__ == "__main__":
    unittest.main()
