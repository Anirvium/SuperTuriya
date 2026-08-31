"""Independent external-v2 benchmark, execution, and isolation controls.

The prediction stage reads only ``cases/`` plus public hash manifests. Private
gold is first opened by the later scoring stage, after raw predictions have
already been persisted.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import re
import statistics
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROOT = PROJECT_ROOT / "benchmark" / "external_v2"
CASE_ID_PATTERN = re.compile(r"^v2-\d{3}$")
MIN_CASES = 12
MAX_CASES = 16
BENCHMARK_ID = "superturiya-independent-external-v2"
SUT_MANIFEST_NAME = "system_under_test.json"
TAXONOMY_NAME = "failure_taxonomy.v1.json"
SUT_SOURCE_FILES = (
    "superturiya/adaptive.py",
    "superturiya/external_runtime.py",
    "superturiya/external_v2.py",
)
SUPPORTED_FAILURE_CLASSES = {
    "stale_memory",
    "missing_evidence",
    "invalid_tool_argument",
    "tool_output_misinterpretation",
    "missing_approval",
    "orchestration_error",
}
INITIAL_STATE_REQUIRED = {
    "request_id",
    "requested_region",
    "requested_quantity",
    "memory_region",
    "catalog_status",
    "requires_approval",
    "approval_granted",
    "faulty_quantity_arg",
    "faulty_order",
}
WORKFLOW_REQUIRED = {
    "retrieval_filter",
    "require_evidence",
    "quantity_constraint",
    "result_validation",
    "approval_rule",
    "enforce_order",
}
EXPECTED_STATE_REQUIRED = {
    "region",
    "quantity",
    "status",
    "approval_checked",
    "catalog_evidence_id",
}
TOOL_FIXTURES_REQUIRED = {
    "catalog.lookup",
    "approval.check",
    "fulfill.simulate",
}
TOOL_FIXTURE_FIELDS = {
    "catalog.lookup": {"status", "region", "evidence_id"},
    "approval.check": {"granted", "evidence_id"},
    "fulfill.simulate": {"side_effects"},
}
SCENARIO_FAMILIES = {
    "resource_provisioning",
    "software_release_control",
    "data_access_control",
    "incident_recovery_control",
}

CASE_REQUIRED = {
    "case_id",
    "split",
    "difficult",
    "scenario_family",
    "goal",
    "initial_state",
    "tool_fixtures",
    "workflow_config",
    "trajectory",
    "expected_state",
}
STEP_REQUIRED = {"step_id", "index", "kind", "source", "summary", "evidence_refs"}
CASE_ALLOWED = set(CASE_REQUIRED)
STEP_ALLOWED = set(STEP_REQUIRED)
GOLD_REQUIRED = {
    "case_id",
    "gold_critical_steps",
    "gold_failure_class",
    "decisive_invariant",
    "expected_repair_surface",
    "acceptable_repairs",
    "adjudication_note",
    "label_canary",
}
MODEL_VISIBLE_CASE_FIELDS = {
    "case_id",
    "goal",
    "initial_state",
    "tool_descriptions",
    "trajectory",
}
MODEL_VISIBLE_INITIAL_FIELDS = INITIAL_STATE_REQUIRED - {
    "faulty_quantity_arg",
    "faulty_order",
}
MODEL_HIDDEN_CASE_KEYS = {
    "expected_state",
    "workflow_config",
    "tool_fixtures",
    "eligible",
    "difficult",
    "scenario_family",
    "faulty_quantity_arg",
    "faulty_order",
    *(GOLD_REQUIRED - {"case_id"}),
}
ALLOWED_OPERATIONS = {
    "prompt_rule.add",
    "prompt_rule.replace",
    "tool_argument.constraint",
    "tool_result.validation",
    "retrieval.filter",
    "route.condition",
    "recovery_step.insert",
    "approval_rule.add",
}
VISIBLE_FORBIDDEN_KEYS = {
    "gold_critical_steps",
    "gold_failure_class",
    "decisive_invariant",
    "expected_repair_surface",
    "acceptable_repairs",
    "acceptable_alternative_repairs",
    "adjudication_note",
    "adjudication_notes",
    "label_canary",
}
VISIBLE_FORBIDDEN_MARKERS = ("GOLD_CANARY", "XVAL_GOLD", "EXPECTED_REPAIR_SURFACE")


class ExternalV2Error(ValueError):
    """A benchmark contract, isolation, or freeze violation."""


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExternalV2Error("cannot read valid JSON from %s: %s" % (path, exc)) from exc


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _nonempty_string(value: Any, field: str, path: Path) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ExternalV2Error("%s must be a non-empty string in %s" % (field, path))


def _require_fields(payload: dict, required: set[str], path: Path) -> None:
    missing = sorted(required - set(payload))
    if missing:
        raise ExternalV2Error("missing required fields in %s: %s" % (path, ", ".join(missing)))


def _reject_unknown_fields(
    payload: dict, allowed: set[str], location: str, path: Path
) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ExternalV2Error(
            "undeclared fields are not allowed at %s in %s: %s"
            % (location, path, ", ".join(unknown))
        )


def _walk_items(value: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, nested in value.items():
            location = "%s.%s" % (prefix, key) if prefix else str(key)
            yield location, nested
            yield from _walk_items(nested, location)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            location = "%s[%d]" % (prefix, index)
            yield from _walk_items(nested, location)


def validate_visible_case(payload: Any, path: Path = Path("<case>")) -> dict:
    if not isinstance(payload, dict):
        raise ExternalV2Error("visible case must be an object in %s" % path)
    _require_fields(payload, CASE_REQUIRED, path)
    _reject_unknown_fields(payload, CASE_ALLOWED, "case", path)
    case_id = payload["case_id"]
    if not isinstance(case_id, str) or not CASE_ID_PATTERN.fullmatch(case_id):
        raise ExternalV2Error("case_id must use opaque form v2-NNN in %s" % path)
    if payload["split"] != "held_out":
        raise ExternalV2Error("external-v2 cases must use split=held_out in %s" % path)
    if not isinstance(payload["difficult"], bool):
        raise ExternalV2Error("difficult must be boolean in %s" % path)
    if payload["scenario_family"] not in SCENARIO_FAMILIES:
        raise ExternalV2Error("scenario_family is outside the frozen cloud-operations families in %s" % path)
    for field in ("scenario_family", "goal"):
        _nonempty_string(payload[field], field, path)
    for field in ("initial_state", "tool_fixtures", "workflow_config", "expected_state"):
        if not isinstance(payload[field], dict):
            raise ExternalV2Error("%s must be an object in %s" % (field, path))
    _require_fields(payload["initial_state"], INITIAL_STATE_REQUIRED, path)
    _require_fields(payload["workflow_config"], WORKFLOW_REQUIRED, path)
    _require_fields(payload["expected_state"], EXPECTED_STATE_REQUIRED, path)
    _require_fields(payload["tool_fixtures"], TOOL_FIXTURES_REQUIRED, path)
    _reject_unknown_fields(
        payload["initial_state"], INITIAL_STATE_REQUIRED, "initial_state", path
    )
    _reject_unknown_fields(
        payload["workflow_config"], WORKFLOW_REQUIRED, "workflow_config", path
    )
    _reject_unknown_fields(
        payload["expected_state"], EXPECTED_STATE_REQUIRED, "expected_state", path
    )
    _reject_unknown_fields(
        payload["tool_fixtures"], TOOL_FIXTURES_REQUIRED, "tool_fixtures", path
    )
    for tool_name, allowed_fields in TOOL_FIXTURE_FIELDS.items():
        fixture = payload["tool_fixtures"][tool_name]
        if not isinstance(fixture, dict):
            raise ExternalV2Error("tool fixture %s must be an object in %s" % (tool_name, path))
        _require_fields(fixture, allowed_fields, path)
        _reject_unknown_fields(fixture, allowed_fields, "tool_fixtures.%s" % tool_name, path)
    initial = payload["initial_state"]
    if not isinstance(initial["requested_quantity"], int) or initial["requested_quantity"] <= 0:
        raise ExternalV2Error("requested_quantity must be a positive integer in %s" % path)
    if not isinstance(initial["requires_approval"], bool) or not isinstance(
        initial["approval_granted"], bool
    ):
        raise ExternalV2Error("approval flags must be booleans in %s" % path)
    if not isinstance(initial["faulty_order"], list):
        raise ExternalV2Error("faulty_order must be a list in %s" % path)
    for field in ("request_id", "requested_region", "memory_region", "catalog_status"):
        _nonempty_string(initial[field], "initial_state.%s" % field, path)
    for field in WORKFLOW_REQUIRED:
        if field != "retrieval_filter" and not isinstance(payload["workflow_config"][field], bool):
            raise ExternalV2Error("workflow_config.%s must be boolean in %s" % (field, path))
    _nonempty_string(
        payload["workflow_config"]["retrieval_filter"],
        "workflow_config.retrieval_filter",
        path,
    )
    trajectory = payload["trajectory"]
    if not isinstance(trajectory, list) or len(trajectory) < 3:
        raise ExternalV2Error("trajectory must contain at least three steps in %s" % path)
    step_ids: set[str] = set()
    indices: list[int] = []
    for step in trajectory:
        if not isinstance(step, dict):
            raise ExternalV2Error("trajectory steps must be objects in %s" % path)
        _require_fields(step, STEP_REQUIRED, path)
        _reject_unknown_fields(step, STEP_ALLOWED, "trajectory.step", path)
        for field in ("step_id", "kind", "source", "summary"):
            _nonempty_string(step[field], "trajectory.%s" % field, path)
        if step["step_id"] in step_ids:
            raise ExternalV2Error("duplicate step_id %s in %s" % (step["step_id"], path))
        step_ids.add(step["step_id"])
        if not isinstance(step["index"], int):
            raise ExternalV2Error("trajectory.index must be an integer in %s" % path)
        indices.append(step["index"])
        refs = step["evidence_refs"]
        if not isinstance(refs, list) or not all(isinstance(item, str) for item in refs):
            raise ExternalV2Error("evidence_refs must be a string list in %s" % path)
    if indices != sorted(indices) or len(indices) != len(set(indices)):
        raise ExternalV2Error("trajectory indices must be unique and increasing in %s" % path)
    for location, value in _walk_items(payload):
        key = location.rsplit(".", 1)[-1].split("[", 1)[0]
        if key in VISIBLE_FORBIDDEN_KEYS or key.startswith("gold_"):
            raise ExternalV2Error("private gold field leaked into visible case at %s" % location)
        if isinstance(value, str) and any(marker in value.upper() for marker in VISIBLE_FORBIDDEN_MARKERS):
            raise ExternalV2Error("private gold marker leaked into visible case at %s" % location)
    return payload


def validate_private_gold(payload: Any, path: Path = Path("<gold>")) -> dict:
    if not isinstance(payload, dict):
        raise ExternalV2Error("private gold must be an object in %s" % path)
    _require_fields(payload, GOLD_REQUIRED, path)
    _reject_unknown_fields(payload, GOLD_REQUIRED, "private_gold", path)
    case_id = payload["case_id"]
    if not isinstance(case_id, str) or not CASE_ID_PATTERN.fullmatch(case_id):
        raise ExternalV2Error("gold case_id must use opaque form v2-NNN in %s" % path)
    steps = payload["gold_critical_steps"]
    if not isinstance(steps, list) or not steps or not all(isinstance(item, str) and item for item in steps):
        raise ExternalV2Error("gold_critical_steps must be a non-empty string list in %s" % path)
    for field in (
        "gold_failure_class",
        "decisive_invariant",
        "adjudication_note",
        "label_canary",
    ):
        _nonempty_string(payload[field], field, path)
    if payload["gold_failure_class"] not in SUPPORTED_FAILURE_CLASSES:
        raise ExternalV2Error(
            "gold_failure_class is outside the frozen taxonomy in %s: %s"
            % (path, payload["gold_failure_class"])
        )
    if not re.fullmatch(r"V2_GOLD_CANARY_[A-Z0-9_]+", payload["label_canary"]):
        raise ExternalV2Error("label_canary must use V2_GOLD_CANARY_* form in %s" % path)
    surface = payload["expected_repair_surface"]
    if not isinstance(surface, dict) or set(("operation", "target_id")) - set(surface):
        raise ExternalV2Error("expected_repair_surface requires operation and target_id in %s" % path)
    repairs = payload["acceptable_repairs"]
    if not isinstance(repairs, list) or not repairs:
        raise ExternalV2Error("acceptable_repairs must be a non-empty list in %s" % path)
    for repair in [surface, *repairs]:
        if not isinstance(repair, dict):
            raise ExternalV2Error("repair entries must be objects in %s" % path)
        _require_fields(repair, {"operation", "target_id"}, path)
        _reject_unknown_fields(
            repair, {"operation", "target_id"}, "private_gold.repair", path
        )
        operation = repair.get("operation")
        if operation not in ALLOWED_OPERATIONS:
            raise ExternalV2Error("repair operation is not allowlisted in %s: %s" % (path, operation))
        _nonempty_string(repair.get("target_id"), "repair.target_id", path)
    return payload


def _json_files(directory: Path) -> list[Path]:
    return sorted(path for path in directory.glob("*.json") if path.is_file())


def load_external_v2_cases(root: Path = DEFAULT_ROOT) -> list[dict]:
    """Load only agent-visible inputs; never touches the private-gold directory."""

    cases_dir = Path(root) / "cases"
    files = _json_files(cases_dir)
    cases = [
        {**validate_visible_case(_read_json(path), path), "eligible": True}
        for path in files
    ]
    ids = [case["case_id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ExternalV2Error("duplicate case_id in visible cases")
    return cases


def load_external_v2_gold_for_adjudication(root: Path = DEFAULT_ROOT) -> list[dict]:
    """Reviewer/evaluator-only loader. Runtime code must not call this function."""

    gold_dir = Path(root) / "gold_private"
    files = _json_files(gold_dir)
    labels = [validate_private_gold(_read_json(path), path) for path in files]
    ids = [label["case_id"] for label in labels]
    if len(ids) != len(set(ids)):
        raise ExternalV2Error("duplicate case_id in private gold")
    return labels


def validate_failure_taxonomy(root: Path = DEFAULT_ROOT) -> dict:
    path = Path(root) / TAXONOMY_NAME
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise ExternalV2Error("failure taxonomy must be a JSON object")
    _require_fields(
        payload, {"taxonomy_id", "version", "scope", "classes"}, path
    )
    _reject_unknown_fields(
        payload,
        {"taxonomy_id", "version", "scope", "classes"},
        "failure_taxonomy",
        path,
    )
    if payload.get("taxonomy_id") != "superturiya-cloud-operations-failure-taxonomy":
        raise ExternalV2Error("failure taxonomy ID differs from the v2 contract")
    if payload.get("version") != "1.0.0":
        raise ExternalV2Error("failure taxonomy version must be 1.0.0")
    classes = payload.get("classes")
    if not isinstance(classes, list) or not classes:
        raise ExternalV2Error("failure taxonomy classes must be a non-empty list")
    class_ids = set()
    invariant_space = set()
    for item in classes:
        if not isinstance(item, dict):
            raise ExternalV2Error("failure taxonomy entries must be objects")
        _require_fields(item, {"id", "definition", "decisive_invariants"}, path)
        _reject_unknown_fields(
            item,
            {"id", "definition", "decisive_invariants"},
            "failure_taxonomy.class",
            path,
        )
        _nonempty_string(item["id"], "failure_taxonomy.class.id", path)
        _nonempty_string(item["definition"], "failure_taxonomy.class.definition", path)
        invariants = item["decisive_invariants"]
        if not isinstance(invariants, list) or not invariants or not all(
            isinstance(value, str) and value for value in invariants
        ):
            raise ExternalV2Error("decisive_invariants must be a non-empty string list")
        if item["id"] in class_ids:
            raise ExternalV2Error("duplicate failure taxonomy class: %s" % item["id"])
        class_ids.add(item["id"])
        invariant_space.update(invariants)
    if class_ids != SUPPORTED_FAILURE_CLASSES:
        raise ExternalV2Error("failure taxonomy classes differ from the frozen label space")
    return {
        "taxonomy_id": payload["taxonomy_id"],
        "version": payload["version"],
        "class_ids": sorted(class_ids),
        "invariant_space": sorted(invariant_space),
        "sha256": _sha256(path),
        "document": payload,
    }


def validate_model_visible_projection(case: dict) -> dict:
    """Audit the exact case object used by all three outbound model prompts."""

    from .adaptive import agent_case_view

    projection = agent_case_view(case)
    if set(projection) != MODEL_VISIBLE_CASE_FIELDS:
        raise ExternalV2Error(
            "model-visible case projection fields differ from the frozen contract"
        )
    if set(projection["initial_state"]) != MODEL_VISIBLE_INITIAL_FIELDS:
        raise ExternalV2Error(
            "model-visible initial_state fields differ from the frozen contract"
        )
    for location, _value in _walk_items(projection):
        key = location.rsplit(".", 1)[-1].split("[", 1)[0]
        if key in MODEL_HIDDEN_CASE_KEYS:
            raise ExternalV2Error(
                "verifier-only or private field reached model projection at %s" % location
            )
    return {
        "case_id": case["case_id"],
        "projection_sha256": _canonical_hash(projection),
        "top_level_fields": sorted(projection),
        "initial_state_fields": sorted(projection["initial_state"]),
        "hidden_fields_present": False,
    }


def validate_authoring_bundle(root: Path = DEFAULT_ROOT, require_full: bool = True) -> dict:
    root = Path(root)
    taxonomy = validate_failure_taxonomy(root)
    cases = load_external_v2_cases(root)
    labels = load_external_v2_gold_for_adjudication(root)
    case_ids = {item["case_id"] for item in cases}
    label_ids = {item["case_id"] for item in labels}
    if case_ids != label_ids:
        raise ExternalV2Error(
            "visible/private case ID mismatch: missing_gold=%s missing_case=%s"
            % (sorted(case_ids - label_ids), sorted(label_ids - case_ids))
        )
    if require_full and not MIN_CASES <= len(cases) <= MAX_CASES:
        raise ExternalV2Error("external-v2 requires %d-%d cases; found %d" % (MIN_CASES, MAX_CASES, len(cases)))
    scenario_families = sorted({item["scenario_family"] for item in cases})
    difficult_count = sum(1 for item in cases if item["difficult"])
    if require_full and len(scenario_families) < 3:
        raise ExternalV2Error(
            "external-v2 requires at least three cloud-operations scenario families"
        )
    if require_full and difficult_count < 3:
        raise ExternalV2Error("external-v2 requires at least three difficult cases")
    critical_ids_by_case = {
        case["case_id"]: {step["step_id"] for step in case["trajectory"]}
        for case in cases
    }
    case_lookup = {case["case_id"]: case for case in cases}
    taxonomy_by_id = {
        item["id"]: item for item in taxonomy["document"]["classes"]
    }
    from .adaptive import TARGET_CONFIG_KEYS

    for label in labels:
        unknown = sorted(
            set(label["gold_critical_steps"])
            - critical_ids_by_case[label["case_id"]]
        )
        if unknown:
            raise ExternalV2Error("gold references unknown critical steps: %s" % unknown)
        taxonomy_class = taxonomy_by_id[label["gold_failure_class"]]
        if label["decisive_invariant"] not in taxonomy_class["decisive_invariants"]:
            raise ExternalV2Error(
                "decisive_invariant is outside the frozen class definition for %s"
                % label["case_id"]
            )
        case = case_lookup[label["case_id"]]
        for repair in [
            label["expected_repair_surface"],
            *label["acceptable_repairs"],
        ]:
            pair = (repair["operation"], repair["target_id"])
            config_key = TARGET_CONFIG_KEYS.get(pair)
            if pair not in TARGET_CONFIG_KEYS or config_key is None:
                raise ExternalV2Error(
                    "private repair does not resolve to an allowlisted mutable surface "
                    "for %s: %s::%s"
                    % (label["case_id"], repair["operation"], repair["target_id"])
                )
            if config_key not in case["workflow_config"]:
                raise ExternalV2Error(
                    "private repair target is absent from corresponding case config: %s"
                    % label["case_id"]
                )
    projections = [validate_model_visible_projection(case) for case in cases]
    initially_failing = []
    if cases:
        from .adaptive import DeterministicVerifier, DeterministicWorkload

        workload = DeterministicWorkload()
        verifier = DeterministicVerifier()
        for case in cases:
            verification = verifier.verify(case, workload.run(case))
            if verification["task_success"] or not verification["failed_invariants"]:
                raise ExternalV2Error(
                    "case is not an initially failing trajectory: %s" % case["case_id"]
                )
            initially_failing.append(case["case_id"])
    return {
        "schema": "superturiya-external-v2-authoring-validation-v1",
        "valid": True,
        "case_count": len(cases),
        "eligible_count": sum(1 for item in cases if item["eligible"]),
        "eligibility_rule": "derived_true_after_initial_failure_validation",
        "difficult_count": difficult_count,
        "scenario_families": scenario_families,
        "claim_scope": "cloud_operations_scenario_families",
        "case_ids": sorted(case_ids),
        "initially_failing_count": len(initially_failing),
        "gold_isolation": "separate_directory",
        "failure_taxonomy": {
            "taxonomy_id": taxonomy["taxonomy_id"],
            "version": taxonomy["version"],
            "sha256": taxonomy["sha256"],
        },
        "model_projection_contract": {
            "top_level_fields": sorted(MODEL_VISIBLE_CASE_FIELDS),
            "initial_state_fields": sorted(MODEL_VISIBLE_INITIAL_FIELDS),
            "case_count_audited": len(projections),
            "hidden_fields_present": False,
        },
    }


def _git_state() -> dict:
    def run(args: list[str]) -> str:
        try:
            return subprocess.run(
                args, cwd=PROJECT_ROOT, check=True, capture_output=True, text=True
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return "unavailable"

    commit = run(["git", "rev-parse", "HEAD"])
    status = run(["git", "status", "--porcelain"])
    return {"commit": commit, "worktree_dirty": bool(status and status != "unavailable")}


def _sut_source_hashes() -> dict[str, str]:
    return {name: _sha256(PROJECT_ROOT / name) for name in SUT_SOURCE_FILES}


def freeze_system_under_test(
    root: Path = DEFAULT_ROOT,
    model: str = "openai/gpt-oss-120b",
    trial_count: int = 3,
) -> dict:
    """Seal the exact code and experiment contract before independent authoring."""

    root = Path(root)
    _nonempty_string(model, "model", root)
    if trial_count < 3:
        raise ExternalV2Error("the final experiment requires at least three trials")
    source_hashes = _sut_source_hashes()
    taxonomy = validate_failure_taxonomy(root)
    contract = {
        "mode": "live",
        "model": model,
        "temperature": 0.0,
        "trial_count": trial_count,
        "baseline_and_final_same_model": True,
        "baseline_and_final_same_cases": True,
        "baseline_and_final_same_replay_and_verifier": True,
        "scoring_after_raw_prediction_persistence": True,
        "prompt_or_rule_tuning_after_freeze": False,
    }
    sealed = {
        "source_hashes": source_hashes,
        "experiment_contract": contract,
        "allowed_operations": sorted(ALLOWED_OPERATIONS),
        "supported_failure_classes": sorted(SUPPORTED_FAILURE_CLASSES),
        "evaluation_boundary": {
            "claim_scope": "cloud_operations_scenario_families",
            "eligibility_rule": "derived_true_after_initial_failure_validation",
            "failure_taxonomy_version": taxonomy["version"],
            "failure_taxonomy_sha256": taxonomy["sha256"],
            "model_visible_case_fields": sorted(MODEL_VISIBLE_CASE_FIELDS),
            "model_visible_initial_state_fields": sorted(
                MODEL_VISIBLE_INITIAL_FIELDS
            ),
            "model_visible_invariant_fields": [
                "evidence_refs",
                "invariant_id",
                "passed",
            ],
        },
    }
    manifest = {
        "artifact_schema": "superturiya-system-under-test-freeze-v1",
        "status": "frozen",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "system_under_test_sha256": _canonical_hash(sealed),
        **sealed,
        "git_state_at_freeze": _git_state(),
        "credential_values_recorded": False,
    }
    path = root / SUT_MANIFEST_NAME
    if path.exists():
        existing = _read_json(path)
        if existing.get("status") == "frozen":
            if existing.get("system_under_test_sha256") == manifest["system_under_test_sha256"]:
                return existing
            raise ExternalV2Error(
                "system-under-test source changed after freeze; create a new SUT namespace"
            )
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def validate_system_under_test(root: Path = DEFAULT_ROOT) -> dict:
    root = Path(root)
    manifest = _read_json(root / SUT_MANIFEST_NAME)
    if manifest.get("status") != "frozen":
        raise ExternalV2Error("system-under-test is not frozen")
    actual = _sut_source_hashes()
    taxonomy = validate_failure_taxonomy(root)
    if actual != manifest.get("source_hashes"):
        changed = sorted(
            name
            for name in set(actual) | set(manifest.get("source_hashes") or {})
            if actual.get(name) != (manifest.get("source_hashes") or {}).get(name)
        )
        raise ExternalV2Error(
            "system-under-test changed after freeze: %s" % ", ".join(changed)
        )
    sealed = {
        "source_hashes": actual,
        "experiment_contract": manifest.get("experiment_contract"),
        "allowed_operations": manifest.get("allowed_operations"),
        "supported_failure_classes": manifest.get("supported_failure_classes"),
        "evaluation_boundary": manifest.get("evaluation_boundary"),
    }
    if _canonical_hash(sealed) != manifest.get("system_under_test_sha256"):
        raise ExternalV2Error("system-under-test contract hash mismatch")
    boundary = manifest.get("evaluation_boundary") or {}
    if boundary.get("failure_taxonomy_sha256") != taxonomy["sha256"]:
        raise ExternalV2Error("system-under-test failure taxonomy hash mismatch")
    return {
        "status": "frozen",
        "system_under_test_sha256": manifest["system_under_test_sha256"],
        "source_hashes_valid": True,
        "experiment_contract": copy.deepcopy(manifest["experiment_contract"]),
    }


def validate_runtime_case_freeze(root: Path = DEFAULT_ROOT) -> dict:
    """Verify public case hashes without opening reviewer-only label files."""

    root = Path(root)
    manifest = _read_json(root / "manifest.json")
    if manifest.get("status") != "frozen":
        raise ExternalV2Error("external-v2 is not frozen")
    cases = load_external_v2_cases(root)
    if not MIN_CASES <= len(cases) <= MAX_CASES:
        raise ExternalV2Error("runtime case count is outside the frozen 12-16 contract")
    actual = {path.name: _sha256(path) for path in _json_files(root / "cases")}
    expected = (manifest.get("file_hashes") or {}).get("cases")
    if actual != expected:
        raise ExternalV2Error("visible cases differ from the frozen byte hashes")
    if _canonical_hash(actual) != manifest.get("cases_aggregate_sha256"):
        raise ExternalV2Error("visible case aggregate hash mismatch")
    projection_audit = [validate_model_visible_projection(case) for case in cases]
    return {
        "status": "frozen",
        "case_count": len(cases),
        "case_ids": [case["case_id"] for case in cases],
        "cases_aggregate_sha256": manifest["cases_aggregate_sha256"],
        "reviewer_only_files_opened": False,
        "model_projection_audited": len(projection_audit),
        "hidden_fields_present": False,
    }


def freeze_external_v2(root: Path, author_id: str, reviewer_id: str) -> dict:
    root = Path(root)
    _nonempty_string(author_id, "author_id", root)
    _nonempty_string(reviewer_id, "reviewer_id", root)
    if author_id.strip().lower() == reviewer_id.strip().lower():
        raise ExternalV2Error("author_id and reviewer_id must identify different people")
    manifest_path = root / "manifest.json"
    existing = _read_json(manifest_path) if manifest_path.exists() else {}
    if existing.get("status") == "frozen":
        raise ExternalV2Error("external-v2 is already frozen; create a new namespace for changes")
    validation = validate_authoring_bundle(root, require_full=True)
    case_files = _json_files(root / "cases")
    gold_files = _json_files(root / "gold_private")
    file_hashes = {
        "cases": {path.name: _sha256(path) for path in case_files},
        "gold_private": {path.name: _sha256(path) for path in gold_files},
    }
    manifest = {
        "benchmark_id": BENCHMARK_ID,
        "schema_version": "2.1",
        "status": "frozen",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "author_id": author_id,
        "reviewer_id": reviewer_id,
        "independence_attestation": (
            "Cases and private gold were authored without access to SuperTuriya prompts "
            "or model outputs; the named reviewer checked the final package before freeze."
        ),
        "validation": validation,
        "file_hashes": file_hashes,
        "cases_aggregate_sha256": _canonical_hash(file_hashes["cases"]),
        "gold_aggregate_sha256": _canonical_hash(file_hashes["gold_private"]),
        "failure_taxonomy_sha256": _sha256(root / TAXONOMY_NAME),
        "git_state_at_freeze": _git_state(),
        "post_freeze_tuning_prohibited": True,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def validate_frozen_external_v2(root: Path = DEFAULT_ROOT) -> dict:
    root = Path(root)
    manifest = _read_json(root / "manifest.json")
    if manifest.get("status") != "frozen":
        raise ExternalV2Error("external-v2 is not frozen")
    validation = validate_authoring_bundle(root, require_full=True)
    actual = {
        "cases": {path.name: _sha256(path) for path in _json_files(root / "cases")},
        "gold_private": {path.name: _sha256(path) for path in _json_files(root / "gold_private")},
    }
    if actual != manifest.get("file_hashes"):
        raise ExternalV2Error("post-freeze mutation detected in external-v2 files")
    if _canonical_hash(actual["cases"]) != manifest.get("cases_aggregate_sha256"):
        raise ExternalV2Error("visible case aggregate hash mismatch")
    if _canonical_hash(actual["gold_private"]) != manifest.get("gold_aggregate_sha256"):
        raise ExternalV2Error("private gold aggregate hash mismatch")
    if _sha256(root / TAXONOMY_NAME) != manifest.get("failure_taxonomy_sha256"):
        raise ExternalV2Error("failure taxonomy differs from the frozen byte hash")
    return {**validation, "status": "frozen", "hashes_valid": True}


def _write_new_json(path: Path, payload: Any) -> None:
    if path.exists():
        raise ExternalV2Error(
            "refusing to overwrite evidence artifact; choose a new path: %s" % path
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_external_v2_predictions(
    root: Path,
    output: Path,
    mode: str = "live",
    experiment: str = "comparison",
    trials: Optional[int] = None,
) -> dict:
    """Persist cases-only raw outputs. This stage never loads private labels."""

    if mode not in {"live", "frozen"}:
        raise ExternalV2Error("prediction mode must be live or frozen")
    if experiment not in {"comparison", "ablation"}:
        raise ExternalV2Error("experiment must be comparison or ablation")
    root = Path(root)
    output = Path(output)
    runtime_freeze = validate_runtime_case_freeze(root)
    sut = validate_system_under_test(root)
    contract = sut["experiment_contract"]
    expected_trials = int(contract["trial_count"])
    requested_trials = trials if trials is not None else expected_trials
    if mode == "live" and experiment == "comparison" and requested_trials != expected_trials:
        raise ExternalV2Error(
            "LIVE trial count differs from frozen SUT contract: %d != %d"
            % (requested_trials, expected_trials)
        )
    cases = load_external_v2_cases(root)
    with tempfile.TemporaryDirectory() as directory:
        runtime_root = Path(directory)
        (runtime_root / "cases.json").write_text(
            json.dumps({"benchmark_id": BENCHMARK_ID, "cases": cases}, sort_keys=True),
            encoding="utf-8",
        )
        from .external_runtime import ExternalRuntimeRunner

        runner = ExternalRuntimeRunner(runtime_root, benchmark_id=BENCHMARK_ID)
        if experiment == "ablation":
            runtime = runner.run_ablations(mode)
        elif mode == "live":
            runtime = runner.run_same_model_live(requested_trials)
        else:
            runtime = runner.run_comparison("frozen")
    if mode == "live":
        live_contract = runtime.get("contract") or runtime.get("live_contract") or {}
        if live_contract.get("requested_model") != contract["model"]:
            raise ExternalV2Error("LIVE model differs from the frozen SUT contract")
    payload = {
        "artifact_schema": "superturiya-external-v2-raw-predictions-v1",
        "benchmark_id": BENCHMARK_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "experiment": experiment,
        "claim_eligible": mode == "live",
        "system_under_test_sha256": sut["system_under_test_sha256"],
        "cases_aggregate_sha256": runtime_freeze["cases_aggregate_sha256"],
        "case_ids": runtime_freeze["case_ids"],
        "private_labels_loaded": False,
        "runtime": runtime,
    }
    _write_new_json(output, payload)
    return {
        "status": "raw_predictions_persisted",
        "output": str(output),
        "sha256": _sha256(output),
        "case_count": len(cases),
        "mode": mode,
        "experiment": experiment,
        "private_labels_loaded": False,
    }


def _repair_matches_v2(label: dict, patch: dict) -> bool:
    candidate = {
        "operation": patch.get("operation"),
        "target_id": patch.get("target_id"),
    }
    allowed = [label["expected_repair_surface"], *label["acceptable_repairs"]]
    return candidate in allowed


def _score_v2_comparison(
    comparison: dict, cases: list[dict], labels: dict[str, dict]
) -> dict:
    baseline = comparison["baseline"]
    final = comparison["final"]
    expected_ids = [case["case_id"] for case in cases]
    baseline_ids = [str(item["case_id"]) for item in baseline.get("results", [])]
    final_ids = [str(item["case_id"]) for item in final.get("results", [])]
    if baseline_ids != expected_ids or final_ids != expected_ids:
        raise ExternalV2Error("prediction case order or membership differs from frozen v2")
    case_lookup = {case["case_id"]: case for case in cases}
    scored_cases = []
    for item in final["results"]:
        case_id = str(item["case_id"])
        label = labels[case_id]
        diagnosis = item["investigator_trajectory"]["output"]
        patch = item["adaptation_trajectory"]["output"]
        scored_cases.append(
            {
                "case_id": case_id,
                "difficult": bool(case_lookup[case_id]["difficult"]),
                "critical_step_correct": diagnosis.get("critical_step")
                in label["gold_critical_steps"],
                "failure_class_correct": diagnosis.get("failure_class")
                == label["gold_failure_class"],
                "decisive_invariant_correct": diagnosis.get("decisive_invariant")
                == label["decisive_invariant"],
                "repair_surface_correct": _repair_matches_v2(label, patch),
                "baseline_verified_safe_recovery": bool(
                    next(
                        result
                        for result in baseline["results"]
                        if result["case_id"] == case_id
                    )["verified_safe_recovery"]
                ),
                "verified_safe_recovery": bool(item["verified_safe_recovery"]),
                "safety_regression": bool(item["replay"]["safety_regression"]),
            }
        )
    count = len(scored_cases)
    if not count:
        raise ExternalV2Error("prediction artifact contains no scored cases")
    baseline_rate = float(
        baseline["metrics"]["coverage_adjusted_verified_recovery_rate"]
    )
    final_rate = float(final["metrics"]["coverage_adjusted_verified_recovery_rate"])
    return {
        "metrics": {
            "eligible_cases": count,
            "baseline_verified_safe_recoveries": int(
                baseline["metrics"]["verified_safe_recoveries"]
            ),
            "baseline_cavrr": baseline_rate,
            "final_verified_safe_recoveries": int(
                final["metrics"]["verified_safe_recoveries"]
            ),
            "final_cavrr": final_rate,
            "absolute_improvement": round(final_rate - baseline_rate, 4),
            "safety_regression_rate": float(final["metrics"]["safety_regression_rate"]),
            "critical_step_localization_accuracy": round(
                sum(item["critical_step_correct"] for item in scored_cases) / count, 4
            ),
            "failure_class_accuracy": round(
                sum(item["failure_class_correct"] for item in scored_cases) / count, 4
            ),
            "decisive_invariant_accuracy": round(
                sum(item["decisive_invariant_correct"] for item in scored_cases) / count,
                4,
            ),
            "repair_surface_accuracy": round(
                sum(item["repair_surface_correct"] for item in scored_cases) / count,
                4,
            ),
        },
        "cases": scored_cases,
    }


def _mean(values: list[float]) -> float:
    return round(statistics.mean(values), 4) if values else 0.0


def _stdev(values: list[float]) -> float:
    return round(statistics.stdev(values), 4) if len(values) > 1 else 0.0


def _paired_case_uncertainty(scored_trials: list[dict]) -> dict:
    """Paired bootstrap over cases after aggregating repeated trials per case."""

    case_ids = [item["case_id"] for item in scored_trials[0]["cases"]]
    case_level = []
    for case_id in case_ids:
        rows = [
            next(item for item in trial["cases"] if item["case_id"] == case_id)
            for trial in scored_trials
        ]
        baseline = [float(item["baseline_verified_safe_recovery"]) for item in rows]
        final = [float(item["verified_safe_recovery"]) for item in rows]
        baseline_rate = statistics.mean(baseline)
        final_rate = statistics.mean(final)
        case_level.append(
            {
                "case_id": case_id,
                "baseline_trial_outcomes": [bool(value) for value in baseline],
                "final_trial_outcomes": [bool(value) for value in final],
                "baseline_recovery_rate": round(baseline_rate, 4),
                "final_recovery_rate": round(final_rate, 4),
                "paired_difference": round(final_rate - baseline_rate, 4),
            }
        )
    differences = [float(item["paired_difference"]) for item in case_level]
    rng = random.Random(20260830)
    resamples = 10000
    bootstrapped = []
    for _ in range(resamples):
        sample = [differences[rng.randrange(len(differences))] for _ in differences]
        bootstrapped.append(statistics.mean(sample))
    bootstrapped.sort()
    lower = bootstrapped[int(0.025 * (resamples - 1))]
    upper = bootstrapped[int(0.975 * (resamples - 1))]
    return {
        "method": "paired_nonparametric_bootstrap_over_cases",
        "unit_of_resampling": "case",
        "trial_handling": "trial outcomes aggregated within case before resampling",
        "case_count": len(case_level),
        "trial_count": len(scored_trials),
        "resamples": resamples,
        "random_seed": 20260830,
        "mean_paired_cavrr_difference": round(statistics.mean(differences), 4),
        "confidence_level": 0.95,
        "percentile_interval": [round(lower, 4), round(upper, 4)],
        "small_sample_warning": True,
        "case_level_outcomes": case_level,
    }


def score_external_v2_predictions(
    root: Path, raw_path: Path, output: Path
) -> dict:
    """Open private labels only after a content-addressed raw artifact exists."""

    root = Path(root)
    raw_path = Path(raw_path)
    output = Path(output)
    raw_sha = _sha256(raw_path)
    raw = _read_json(raw_path)
    if raw.get("artifact_schema") != "superturiya-external-v2-raw-predictions-v1":
        raise ExternalV2Error("not an external-v2 raw prediction artifact")
    freeze = validate_frozen_external_v2(root)
    sut = validate_system_under_test(root)
    if raw.get("system_under_test_sha256") != sut["system_under_test_sha256"]:
        raise ExternalV2Error("raw predictions use a different system-under-test")
    manifest = _read_json(root / "manifest.json")
    if raw.get("cases_aggregate_sha256") != manifest.get("cases_aggregate_sha256"):
        raise ExternalV2Error("raw predictions use different visible cases")
    labels_list = load_external_v2_gold_for_adjudication(root)
    serialized_raw = json.dumps(raw, sort_keys=True)
    leaked = [
        label["label_canary"]
        for label in labels_list
        if label["label_canary"] in serialized_raw
    ]
    if leaked:
        raise ExternalV2Error("private label canary leaked into raw predictions")
    cases = load_external_v2_cases(root)
    labels = {label["case_id"]: label for label in labels_list}
    runtime = raw["runtime"]
    experiment = raw["experiment"]
    if experiment == "comparison":
        comparisons = runtime.get("trials") or [runtime]
        scored = [_score_v2_comparison(item, cases, labels) for item in comparisons]
        metric_names = (
            "baseline_cavrr",
            "final_cavrr",
            "absolute_improvement",
            "safety_regression_rate",
            "critical_step_localization_accuracy",
            "failure_class_accuracy",
            "decisive_invariant_accuracy",
            "repair_surface_accuracy",
        )
        aggregate = {
            "%s_mean" % name: _mean([float(item["metrics"][name]) for item in scored])
            for name in metric_names
        }
        aggregate.update(
            {
                "%s_stdev" % name: _stdev(
                    [float(item["metrics"][name]) for item in scored]
                )
                for name in metric_names
            }
        )
        scored_payload: dict = {
            "trial_count": len(scored),
            "aggregate": aggregate,
            "paired_case_uncertainty": _paired_case_uncertainty(scored),
            "trials": scored,
        }
    else:
        variants = runtime["variants"]
        comparison = {
            "baseline": variants["direct_raw_trace"],
            "final": variants["full_verified_repair"],
        }
        scored_comparison = _score_v2_comparison(comparison, cases, labels)
        scored_payload = {
            "comparison": scored_comparison,
            "matrix": {
                "direct_raw_trace": variants["direct_raw_trace"]["metrics"][
                    "coverage_adjusted_verified_recovery_rate"
                ],
                "invariant_preflight_without_typed_repair": variants[
                    "invariant_preflight_without_typed_repair"
                ]["metrics"]["coverage_adjusted_verified_recovery_rate"],
                "structured_repair_without_full_verifier": variants[
                    "structured_repair_without_full_verifier"
                ]["rate"],
                "full_verified_repair": variants["full_verified_repair"]["metrics"][
                    "coverage_adjusted_verified_recovery_rate"
                ],
                "full_verified_and_governed": round(
                    variants["full_verified_and_governed"]["activation_eligible"]
                    / max(1, len(cases)),
                    4,
                ),
            },
            "governance_consistent": variants["full_verified_and_governed"][
                "governance_consistent"
            ],
        }
    payload = {
        "artifact_schema": "superturiya-external-v2-scored-evidence-v1",
        "benchmark_id": BENCHMARK_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": raw["mode"],
        "experiment": experiment,
        "claim_eligible": bool(raw["claim_eligible"]),
        "raw_predictions_path": str(raw_path),
        "raw_predictions_sha256": raw_sha,
        "raw_predictions_persisted_before_scoring": True,
        "system_under_test_sha256": sut["system_under_test_sha256"],
        "benchmark_freeze": {
            "case_count": freeze["case_count"],
            "cases_aggregate_sha256": manifest["cases_aggregate_sha256"],
            "gold_aggregate_sha256": manifest["gold_aggregate_sha256"],
            "author_id": manifest["author_id"],
            "reviewer_id": manifest["reviewer_id"],
        },
        "private_canary_leakage_detected": False,
        **scored_payload,
    }
    _write_new_json(output, payload)
    return {
        "status": "scored_evidence_persisted",
        "output": str(output),
        "sha256": _sha256(output),
        "raw_predictions_sha256": raw_sha,
        "experiment": experiment,
    }


def _author_templates() -> dict[str, str]:
    case = {
        "case_id": "v2-001",
        "split": "held_out",
        "difficult": False,
        "scenario_family": "resource_provisioning",
        "goal": "Describe the independently authored governed tool-use goal.",
        "initial_state": {
            "request_id": "opaque-request-001",
            "requested_region": "region-current",
            "requested_quantity": 2,
            "memory_region": "region-stale",
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
                "region": "region-current",
                "evidence_id": "opaque-evidence-001",
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
                "step_id": "v2-001-s1",
                "index": 1,
                "kind": "input",
                "source": "request",
                "summary": "Describe the current request.",
                "evidence_refs": [],
            },
            {
                "step_id": "v2-001-s2",
                "index": 2,
                "kind": "memory",
                "source": "profile.lookup",
                "summary": "Describe the earliest consequential divergence.",
                "evidence_refs": ["opaque-memory-001"],
            },
            {
                "step_id": "v2-001-s3",
                "index": 3,
                "kind": "action",
                "source": "fulfill.simulate",
                "summary": "Describe the failed outcome.",
                "evidence_refs": ["opaque-evidence-001"],
            },
        ],
        "expected_state": {
            "region": "region-current",
            "quantity": 2,
            "status": "fulfilled",
            "approval_checked": False,
            "catalog_evidence_id": "opaque-evidence-001",
        },
    }
    gold = {
        "case_id": "v2-001",
        "gold_critical_steps": ["v2-001-s2"],
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
        "adjudication_note": "Explain why this is the earliest consequential divergence.",
        "label_canary": "V2_GOLD_CANARY_REPLACE_WITH_UNIQUE_VALUE_001",
    }
    return {
        "templates/case.template.json": json.dumps(case, indent=2, sort_keys=True) + "\n",
        "templates/gold.template.json": json.dumps(gold, indent=2, sort_keys=True) + "\n",
    }


def create_author_packet(
    output: Path,
    root: Path = DEFAULT_ROOT,
) -> dict:
    output = Path(output)
    root = Path(root)
    if output.exists():
        raise ExternalV2Error("refusing to overwrite author packet: %s" % output)
    members: dict[str, bytes] = {}
    for source, target in (
        (root / "case.schema.json", "case.schema.json"),
        (root / "gold.schema.json", "gold.schema.json"),
        (root / TAXONOMY_NAME, TAXONOMY_NAME),
        (root / "reviewer_instructions.md", "reviewer_instructions.md"),
        (root / "protocol.md", "protocol.md"),
    ):
        members[target] = source.read_bytes()
    for name, content in _author_templates().items():
        members[name] = content.encode("utf-8")
    readme = """# External-v2 independent-author packet

## Scope

Create 12-16 synthetic, initially failing cases across at least three of the
frozen cloud-operations scenario families. All accepted cases enter the CAVRR
denominator mechanically; the author does not set eligibility.

This evaluates transfer across scenario families implemented over the same
frozen region, quantity, validation-evidence, approval, and execution-order
simulator. It is not a claim of unrelated-domain external validity.

## Critical-step definition

The critical step is the earliest trajectory step whose faithful correction
makes successful continuation possible under the frozen replay contract.
For a genuinely multi-causal case, list every defensible earliest step in the
private `gold_critical_steps` array and explain the adjudication.

## Visible and private boundary

Visible `cases/v2-NNN.json` files may contain only fields declared by
`case.schema.json`. They must not contain expected answers, failure labels,
decisive invariants, repair targets, acceptable repairs, adjudication notes, or
canaries. `expected_state` is verifier-only and is removed mechanically from all
model-visible projections.

Private `gold_private/v2-NNN.json` files contain the labels, acceptable typed
repairs, adjudication note, and one unique canary. Return the visible and private
folders separately. Never place `gold_private/` in the prediction runtime.

## Difficult cases

Mark at least three cases difficult. A difficult case should require resolving
ambiguous evidence, a longer causal chain, or more than one independent failed
condition. Do not make difficulty depend on missing information that prevents a
fair human adjudication.

## Typed-operation semantics

- `prompt_rule.add`: add one bounded instruction at a declared prompt target.
- `prompt_rule.replace`: replace one declared prompt rule.
- `tool_argument.constraint`: constrain one tool argument.
- `tool_result.validation`: validate one tool-result interpretation.
- `retrieval.filter`: constrain retrieved operational context.
- `route.condition`: add one routing/order condition.
- `recovery_step.insert`: insert one bounded recovery step.
- `approval_rule.add`: require and record an approval check.

The validator confirms that every private operation/target pair resolves to an
actual mutable surface in its corresponding case. The packet does not contain
system prompts, repair mappings, prior cases, model outputs, credentials, or
current model behavior.

## Return format

```text
cases/
  v2-001.json
  ...
gold_private/
  v2-001.json
  ...
```

Use `case.schema.json`, `gold.schema.json`, the versioned failure taxonomy, and
the reviewer checklist before returning the package.
"""
    members["README.md"] = readme.encode("utf-8")
    member_hashes = {
        name: hashlib.sha256(content).hexdigest()
        for name, content in sorted(members.items())
    }
    members["PACKET_MANIFEST.json"] = (
        json.dumps(
            {
                "artifact_schema": "external-v2-author-packet-v1",
                "member_hashes": member_hashes,
                "contains_system_prompts": False,
                "contains_model_outputs": False,
                "contains_credentials": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, content)
    return {
        "status": "author_packet_created",
        "output": str(output),
        "sha256": _sha256(output),
        "member_count": len(members),
        "contains_system_prompts": False,
        "contains_model_outputs": False,
    }


def build_external_v2_evidence_manifest(
    root: Path, evidence_root: Path, output: Path
) -> dict:
    root = Path(root)
    evidence_root = Path(evidence_root)
    sut = validate_system_under_test(root)
    benchmark = validate_frozen_external_v2(root)
    files = []
    for path in sorted(evidence_root.glob("*.json")):
        if path.resolve() == Path(output).resolve():
            continue
        files.append(
            {
                "path": path.name,
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )
    if not files:
        raise ExternalV2Error("no external-v2 evidence JSON files found")
    payload = {
        "artifact_schema": "external-v2-evidence-manifest-v1",
        "benchmark_id": BENCHMARK_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "system_under_test_sha256": sut["system_under_test_sha256"],
        "case_count": benchmark["case_count"],
        "benchmark_manifest_sha256": _sha256(root / "manifest.json"),
        "system_under_test_manifest_sha256": _sha256(root / SUT_MANIFEST_NAME),
        "files": files,
        "artifact_count": len(files),
        "credential_values_recorded": False,
    }
    _write_new_json(Path(output), payload)
    return payload


def status_external_v2(root: Path = DEFAULT_ROOT) -> dict:
    root = Path(root)
    manifest_path = root / "manifest.json"
    manifest = _read_json(manifest_path) if manifest_path.exists() else {}
    cases = load_external_v2_cases(root)
    gold = load_external_v2_gold_for_adjudication(root)
    sut_path = root / SUT_MANIFEST_NAME
    sut_status = "not_frozen"
    if sut_path.exists():
        try:
            validate_system_under_test(root)
            sut_status = "frozen"
        except ExternalV2Error:
            sut_status = "invalidated"
    return {
        "benchmark_id": BENCHMARK_ID,
        "status": manifest.get("status", "awaiting_independent_cases"),
        "system_under_test_status": sut_status,
        "case_count": len(cases),
        "gold_count": len(gold),
        "required_case_range": [MIN_CASES, MAX_CASES],
        "ready_to_freeze": MIN_CASES <= len(cases) <= MAX_CASES and len(cases) == len(gold),
        "next_action": (
            "independent author supplies visible cases and sealed gold"
            if not cases
            else "run validation and independent review before freeze"
        ),
    }


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Manage the independent external-v2 benchmark boundary.")
    parser.add_argument(
        "command",
        choices=(
            "status",
            "validate",
            "freeze",
            "verify",
            "runtime-load",
            "sut-freeze",
            "sut-verify",
            "author-packet",
            "predict",
            "score",
            "evidence-manifest",
        ),
    )
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--author-id")
    parser.add_argument("--reviewer-id")
    parser.add_argument("--model", default="openai/gpt-oss-120b")
    parser.add_argument("--trials", type=int)
    parser.add_argument("--mode", choices=("live", "frozen"), default="live")
    parser.add_argument("--experiment", choices=("comparison", "ablation"), default="comparison")
    parser.add_argument("--output")
    parser.add_argument("--raw")
    parser.add_argument("--evidence-root")
    args = parser.parse_args(argv)
    root = Path(args.root)
    if args.command == "status":
        payload = status_external_v2(root)
    elif args.command == "validate":
        payload = validate_authoring_bundle(root, require_full=True)
    elif args.command == "freeze":
        if not args.author_id or not args.reviewer_id:
            parser.error("freeze requires --author-id and --reviewer-id")
        payload = freeze_external_v2(root, args.author_id, args.reviewer_id)
    elif args.command == "verify":
        payload = validate_frozen_external_v2(root)
    elif args.command == "runtime-load":
        cases = load_external_v2_cases(root)
        payload = {"loaded": len(cases), "case_ids": [item["case_id"] for item in cases], "private_gold_accessed": False}
    elif args.command == "sut-freeze":
        payload = freeze_system_under_test(
            root, args.model, args.trials if args.trials is not None else 3
        )
    elif args.command == "sut-verify":
        payload = validate_system_under_test(root)
    elif args.command == "author-packet":
        output = Path(args.output or PROJECT_ROOT / "output" / "external_v2_author_packet.zip")
        payload = create_author_packet(output, root)
    elif args.command == "predict":
        if not args.output:
            parser.error("predict requires --output")
        payload = run_external_v2_predictions(
            root,
            Path(args.output),
            mode=args.mode,
            experiment=args.experiment,
            trials=args.trials,
        )
    elif args.command == "score":
        if not args.raw or not args.output:
            parser.error("score requires --raw and --output")
        payload = score_external_v2_predictions(
            root, Path(args.raw), Path(args.output)
        )
    else:
        if not args.evidence_root or not args.output:
            parser.error("evidence-manifest requires --evidence-root and --output")
        payload = build_external_v2_evidence_manifest(
            root, Path(args.evidence_root), Path(args.output)
        )
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
