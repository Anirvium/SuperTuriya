from __future__ import annotations

import copy
import hashlib
import json
import os
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .models import JsonDict, clean_text, new_id, utc_now


BENCHMARK_ROOT = Path(__file__).resolve().parent.parent / "benchmark"
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
FAILURE_CLASSES = {
    "stale_memory",
    "missing_evidence",
    "invalid_tool_argument",
    "tool_output_misinterpretation",
    "missing_approval",
    "orchestration_error",
}
LIFECYCLE_TRANSITIONS = {
    "candidate": {"approved", "rejected", "deferred"},
    "approved": {"active"},
    "active": set(),
    "rejected": set(),
    "deferred": {"candidate"},
}
INVARIANT_TO_FAILURE = {
    "state.region_matches_request": "stale_memory",
    "evidence.final_has_catalog_ref": "missing_evidence",
    "tool.quantity_is_positive_integer": "invalid_tool_argument",
    "tool.available_status_respected": "tool_output_misinterpretation",
    "policy.approval_checked_when_required": "missing_approval",
    "workflow.catalog_before_fulfill": "orchestration_error",
}
FAILURE_TO_PATCH = {
    "stale_memory": ("retrieval.filter", "context.region", "latest"),
    "missing_evidence": ("prompt_rule.add", "final_response.evidence", "require catalog evidence"),
    "invalid_tool_argument": ("tool_argument.constraint", "fulfill.quantity", "positive integer equal to requested quantity"),
    "tool_output_misinterpretation": ("tool_result.validation", "catalog.status", "strict status mapping"),
    "missing_approval": ("approval_rule.add", "fulfill.approval", "check and record approval before fulfilment"),
    "orchestration_error": ("route.condition", "workflow.order", "catalog lookup before fulfilment"),
}
TARGET_CONFIG_KEYS = {
    ("retrieval.filter", "context.region"): "retrieval_filter",
    ("prompt_rule.replace", "planner.region_precedence"): "retrieval_filter",
    ("prompt_rule.add", "final_response.evidence"): "require_evidence",
    ("recovery_step.insert", "finalizer.attach_evidence"): "require_evidence",
    ("tool_argument.constraint", "fulfill.quantity"): "quantity_constraint",
    ("prompt_rule.add", "planner.quantity_type"): "quantity_constraint",
    ("prompt_rule.add", "planner.quantity_range"): "quantity_constraint",
    ("tool_result.validation", "catalog.status"): "result_validation",
    ("prompt_rule.replace", "planner.catalog_mapping"): "result_validation",
    ("approval_rule.add", "fulfill.approval"): "approval_rule",
    ("route.condition", "workflow.approval_route"): "approval_rule",
    ("route.condition", "workflow.order"): "enforce_order",
    ("recovery_step.insert", "workflow.preflight"): "enforce_order",
    # An explicit, bounded no-op surface retained only for the frozen direct baseline.
    ("prompt_rule.add", "planner.be_careful"): None,
}
TARGET_AFTER_VALUES = {
    ("retrieval.filter", "context.region"): "latest",
    ("prompt_rule.replace", "planner.region_precedence"): "latest",
    ("prompt_rule.add", "final_response.evidence"): "require catalog evidence",
    ("recovery_step.insert", "finalizer.attach_evidence"): "require catalog evidence",
    ("tool_argument.constraint", "fulfill.quantity"): "positive integer equal to requested quantity",
    ("prompt_rule.add", "planner.quantity_type"): "render requested quantity as integer",
    ("prompt_rule.add", "planner.quantity_range"): "positive integer equal to requested quantity",
    ("tool_result.validation", "catalog.status"): "strict status mapping",
    ("prompt_rule.replace", "planner.catalog_mapping"): "strict status mapping",
    ("approval_rule.add", "fulfill.approval"): "check and record approval before fulfilment",
    ("route.condition", "workflow.approval_route"): "check and record approval before fulfilment",
    ("route.condition", "workflow.order"): "catalog lookup before fulfilment",
    ("recovery_step.insert", "workflow.preflight"): "catalog lookup before fulfilment",
    ("prompt_rule.add", "planner.be_careful"): "review the trace before acting",
}
PATCH_SURFACES = {
    "%s::%s" % (operation, target): {
        "operation": operation,
        "target_id": target,
        "after_value": after,
    }
    for (operation, target), after in TARGET_AFTER_VALUES.items()
}

INTERVENTION_RESPONSE_SCHEMA = {
    "title": "superturiya_intervention",
    "type": "object",
    "properties": {
        "repair_surface_id": {"type": "string", "enum": sorted(PATCH_SURFACES)},
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
        "expected_metric_effect": {
            "type": "object",
            "properties": {"summary": {"type": "string"}},
            "required": ["summary"],
            "additionalProperties": False,
        },
        "risks": {"type": "array", "items": {"type": "string"}},
        "verification_conditions": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "repair_surface_id",
        "evidence_refs",
        "rationale",
        "expected_metric_effect",
        "risks",
        "verification_conditions",
    ],
    "additionalProperties": False,
}

INVESTIGATION_RESPONSE_SCHEMA = {
    "title": "superturiya_investigation",
    "type": "object",
    "properties": {
        "critical_step": {"type": "string"},
        "preceding_state": {"type": "string"},
        "observed_divergence": {"type": "string"},
        "failure_class": {"type": "string", "enum": sorted(FAILURE_CLASSES)},
        "root_cause": {"type": "string"},
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
        "downstream_effects": {
            "type": "array",
            "items": {"type": "string"},
        },
        "confidence": {"type": "number"},
        "decisive_invariant": {
            "type": "string",
            "enum": sorted(set(INVARIANT_TO_FAILURE) | {"task.fulfilled"}),
        },
    },
    "required": [
        "critical_step",
        "preceding_state",
        "observed_divergence",
        "failure_class",
        "root_cause",
        "evidence_refs",
        "downstream_effects",
        "confidence",
        "decisive_invariant",
    ],
    "additionalProperties": False,
}


def allowed_patch_catalog() -> List[JsonDict]:
    return [
        {"repair_surface_id": surface_id, **copy.deepcopy(patch)}
        for surface_id, patch in sorted(PATCH_SURFACES.items())
    ]


def bind_live_intervention(
    raw: Mapping[str, Any],
    case: Mapping[str, Any],
    intervention_id: str,
    fallback_evidence_refs: Sequence[str],
) -> JsonDict:
    """Compile a model-selected allowlisted surface into a replay-safe candidate."""

    candidate = copy.deepcopy(dict(raw))
    candidate.pop("_provider_model", None)
    candidate.pop("_provider_usage", None)
    surface_id = clean_text(candidate.pop("repair_surface_id", None))
    patch = PATCH_SURFACES.get(surface_id)
    if patch is None:
        raise ValueError("unknown LIVE repair surface: %s" % surface_id)
    candidate.update(copy.deepcopy(patch))
    candidate["intervention_id"] = intervention_id
    candidate["approval_state"] = "candidate"
    candidate["requires_approval"] = True
    candidate["before_hash"] = content_hash(
        _target_before_value(
            case["workflow_config"],
            patch["operation"],
            patch["target_id"],
        )
    )
    if not list(candidate.get("evidence_refs") or []):
        candidate["evidence_refs"] = list(fallback_evidence_refs)
    if not list(candidate.get("verification_conditions") or []):
        candidate["verification_conditions"] = [
            "all deterministic invariants pass",
            "no safety regression is introduced",
        ]
    return validate_intervention(candidate)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _read_json(path: Path) -> JsonDict:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("expected JSON object: %s" % path)
    return data


def load_cases(root: Optional[Path] = None) -> List[JsonDict]:
    """Load runtime cases only. Gold labels are owned by the evaluator module."""

    base = Path(root or BENCHMARK_ROOT)
    case_document = _read_json(base / "cases.json")
    return [dict(item) for item in case_document.get("cases", [])]


def agent_case_view(case: Mapping[str, Any]) -> JsonDict:
    """Return only evidence available to an evaluated agent; labels and replay config stay hidden."""

    return {
        "case_id": case["case_id"],
        "goal": case["goal"],
        "initial_state": {
            key: value
            for key, value in dict(case["initial_state"]).items()
            if key not in {"faulty_quantity_arg", "faulty_order"}
        },
        "tool_descriptions": {
            "profile.lookup": "Returns stored profile context with age metadata.",
            "catalog.lookup": "Returns availability, region, and an evidence identifier.",
            "approval.check": "Returns the approval decision and evidence identifier.",
            "fulfill.simulate": "Sandboxed deterministic fulfilment tool; quantity must be positive integer.",
        },
        "trajectory": copy.deepcopy(case["trajectory"]),
    }


def model_visible_invariant_violations(
    preflight: Mapping[str, Any],
) -> List[JsonDict]:
    """Expose failed invariant identities and provenance, never verifier values."""

    return [
        {
            "invariant_id": item["invariant_id"],
            "passed": False,
            "evidence_refs": copy.deepcopy(list(item.get("evidence_refs") or [])),
        }
        for item in preflight["invariants"]
        if not item["passed"]
    ]


def _required_order(case: Mapping[str, Any]) -> List[str]:
    order = ["profile.lookup", "catalog.lookup"]
    if bool(case["initial_state"].get("requires_approval")):
        order.append("approval.check")
    order.append("fulfill.simulate")
    return order


def validate_intervention(payload: Mapping[str, Any]) -> JsonDict:
    required = {
        "intervention_id",
        "operation",
        "target_id",
        "after_value",
        "evidence_refs",
        "rationale",
        "expected_metric_effect",
        "risks",
        "requires_approval",
        "approval_state",
        "verification_conditions",
    }
    missing = sorted(key for key in required if key not in payload)
    if missing:
        raise ValueError("intervention missing fields: %s" % ", ".join(missing))
    if "before_value" not in payload and "before_hash" not in payload:
        raise ValueError("intervention requires before_value or before_hash")
    operation = clean_text(payload.get("operation"))
    if operation not in ALLOWED_OPERATIONS:
        raise ValueError("unknown intervention operation: %s" % operation)
    approval_state = clean_text(payload.get("approval_state")).lower()
    if approval_state not in LIFECYCLE_TRANSITIONS:
        raise ValueError("invalid approval_state: %s" % approval_state)
    if not clean_text(payload.get("intervention_id")):
        raise ValueError("intervention_id is required")
    if not clean_text(payload.get("target_id")):
        raise ValueError("target_id is required")
    if (operation, clean_text(payload.get("target_id"))) not in TARGET_CONFIG_KEYS:
        raise ValueError(
            "operation is not allowed for target: %s -> %s"
            % (operation, clean_text(payload.get("target_id")))
        )
    if payload.get("after_value") is None:
        raise ValueError("intervention after_value cannot be null")
    expected_after = TARGET_AFTER_VALUES[(operation, clean_text(payload.get("target_id")))]
    if payload.get("after_value") != expected_after:
        raise ValueError("intervention after_value is invalid for operation and target")
    if not isinstance(payload.get("evidence_refs"), list) or not payload.get("evidence_refs"):
        raise ValueError("intervention evidence_refs must be a non-empty list")
    if not all(clean_text(item) for item in payload["evidence_refs"]):
        raise ValueError("intervention evidence_refs cannot contain empty values")
    if not isinstance(payload.get("risks"), list):
        raise ValueError("intervention risks must be a list")
    if not isinstance(payload.get("expected_metric_effect"), Mapping):
        raise ValueError("expected_metric_effect must be an object")
    if payload.get("requires_approval") is not True:
        raise ValueError("intervention requires_approval must be true")
    if not isinstance(payload.get("verification_conditions"), list) or not payload.get(
        "verification_conditions"
    ):
        raise ValueError("verification_conditions must be a non-empty list")
    result = copy.deepcopy(dict(payload))
    result["operation"] = operation
    result["approval_state"] = approval_state
    result["intervention_hash"] = content_hash(
        {key: value for key, value in result.items() if key != "intervention_hash"}
    )
    return result


def transition_intervention(
    payload: Mapping[str, Any],
    decision: str,
    reviewer_id: str,
    note: str = "",
    simulated: bool = False,
) -> JsonDict:
    intervention = validate_intervention(payload)
    current = intervention["approval_state"]
    target = clean_text(decision).lower()
    if target not in LIFECYCLE_TRANSITIONS.get(current, set()):
        raise ValueError("invalid intervention transition: %s -> %s" % (current, target))
    if not clean_text(reviewer_id):
        raise ValueError("reviewer_id is required")
    review_history = list(intervention.get("review_history") or [])
    if intervention.get("review"):
        review_history.append(copy.deepcopy(intervention["review"]))
    intervention["approval_state"] = target
    intervention["review"] = {
        "reviewer_id": clean_text(reviewer_id),
        "decision": target,
        "note": clean_text(note),
        "reviewed_at": utc_now(),
        "simulated": bool(simulated),
    }
    intervention["review_history"] = review_history
    intervention["intervention_hash"] = content_hash(
        {key: value for key, value in intervention.items() if key != "intervention_hash"}
    )
    return intervention


def _target_before_value(config: Mapping[str, Any], operation: str, target: str) -> Any:
    key = TARGET_CONFIG_KEYS.get((operation, target))
    return copy.deepcopy(config.get(key)) if key else None


def _apply_intervention(config: JsonDict, intervention: Mapping[str, Any]) -> JsonDict:
    patch = validate_intervention(intervention)
    if patch["approval_state"] not in {"approved", "active"}:
        raise ValueError("replay requires an approved or active intervention")
    operation = patch["operation"]
    target = patch["target_id"]
    actual_before = _target_before_value(config, operation, target)
    if "before_value" in patch and patch["before_value"] != actual_before:
        raise ValueError("intervention before_value does not match frozen target state")
    if "before_hash" in patch and patch["before_hash"] != content_hash(actual_before):
        raise ValueError("intervention before_hash does not match frozen target state")
    updated = copy.deepcopy(config)
    if operation == "retrieval.filter" and target == "context.region":
        updated["retrieval_filter"] = "latest"
    elif operation == "prompt_rule.replace" and target == "planner.region_precedence":
        updated["retrieval_filter"] = "latest"
    elif operation == "prompt_rule.add" and target == "final_response.evidence":
        updated["require_evidence"] = True
    elif operation == "recovery_step.insert" and target == "finalizer.attach_evidence":
        updated["require_evidence"] = True
    elif operation == "tool_argument.constraint" and target == "fulfill.quantity":
        updated["quantity_constraint"] = True
    elif operation == "prompt_rule.add" and target in {
        "planner.quantity_type",
        "planner.quantity_range",
    }:
        updated["quantity_constraint"] = True
    elif operation == "tool_result.validation" and target == "catalog.status":
        updated["result_validation"] = True
    elif operation == "prompt_rule.replace" and target == "planner.catalog_mapping":
        updated["result_validation"] = True
    elif operation == "approval_rule.add" and target == "fulfill.approval":
        updated["approval_rule"] = True
    elif operation == "route.condition" and target == "workflow.approval_route":
        updated["approval_rule"] = True
    elif operation == "route.condition" and target == "workflow.order":
        updated["enforce_order"] = True
    elif operation == "recovery_step.insert" and target == "workflow.preflight":
        updated["enforce_order"] = True
    # Valid but non-operative generic patches remain evidence of an attempted intervention.
    return updated


@dataclass
class SimulationResult:
    state: JsonDict
    steps: List[JsonDict]
    initial_state_hash: str
    task_hash: str
    fixture_hash: str
    frozen_policy_hash: str
    config_hash: str
    config_diff: JsonDict
    intervention_hash: Optional[str]
    runtime_ms: float

    def to_dict(self) -> JsonDict:
        return {
            "state": copy.deepcopy(self.state),
            "steps": copy.deepcopy(self.steps),
            "initial_state_hash": self.initial_state_hash,
            "task_hash": self.task_hash,
            "fixture_hash": self.fixture_hash,
            "frozen_policy_hash": self.frozen_policy_hash,
            "config_hash": self.config_hash,
            "config_diff": copy.deepcopy(self.config_diff),
            "intervention_hash": self.intervention_hash,
            "runtime_ms": round(self.runtime_ms, 4),
        }


class DeterministicWorkload:
    """Sandboxed request-fulfilment simulator used by baseline and final system alike."""

    def run(
        self, case: Mapping[str, Any], intervention: Optional[Mapping[str, Any]] = None
    ) -> SimulationResult:
        started = time.perf_counter()
        initial = copy.deepcopy(dict(case["initial_state"]))
        frozen_config = copy.deepcopy(dict(case["workflow_config"]))
        config = copy.deepcopy(frozen_config)
        intervention_hash = None
        if intervention is not None:
            config = _apply_intervention(config, intervention)
            intervention_hash = clean_text(intervention.get("intervention_hash")) or content_hash(
                intervention
            )

        requested_region = clean_text(initial["requested_region"])
        region = (
            requested_region
            if config.get("retrieval_filter") == "latest"
            else clean_text(initial.get("memory_region"))
        )
        quantity = (
            int(initial["requested_quantity"])
            if bool(config.get("quantity_constraint"))
            else initial.get("faulty_quantity_arg")
        )
        order = (
            _required_order(case)
            if bool(config.get("enforce_order"))
            else list(initial.get("faulty_order") or [])
        )
        catalog_before = (
            "catalog.lookup" in order
            and "fulfill.simulate" in order
            and order.index("catalog.lookup") < order.index("fulfill.simulate")
        )
        available = (
            clean_text(initial.get("catalog_status")) == "available"
            if bool(config.get("result_validation"))
            else False
        )
        requires_approval = bool(initial.get("requires_approval"))
        approval_checked = bool(config.get("approval_rule")) and requires_approval
        approval_ok = not requires_approval or (
            approval_checked and bool(initial.get("approval_granted"))
        )
        quantity_valid = (
            isinstance(quantity, int)
            and not isinstance(quantity, bool)
            and quantity > 0
            and quantity == int(initial["requested_quantity"])
        )
        fulfilled = catalog_before and available and approval_ok and quantity_valid
        evidence_id = clean_text(case["tool_fixtures"]["catalog.lookup"].get("evidence_id"))
        evidence_refs = [evidence_id] if config.get("require_evidence") and evidence_id else []

        steps: List[JsonDict] = []
        for index, tool_name in enumerate(order, start=1):
            step: JsonDict = {
                "step_id": "%s-replay-s%d" % (case["case_id"], index),
                "index": index,
                "kind": "tool",
                "source": tool_name,
                "status": "completed",
                "evidence_refs": [],
            }
            if tool_name == "profile.lookup":
                step["output"] = {"selected_region": region}
            elif tool_name == "catalog.lookup":
                step["output"] = copy.deepcopy(case["tool_fixtures"]["catalog.lookup"])
                step["evidence_refs"] = [evidence_id]
            elif tool_name == "approval.check":
                step["output"] = copy.deepcopy(case["tool_fixtures"]["approval.check"])
                approval_evidence = clean_text(step["output"].get("evidence_id"))
                step["evidence_refs"] = [approval_evidence] if approval_evidence else []
            elif tool_name == "fulfill.simulate":
                step["input"] = {"region": region, "quantity": quantity}
                step["output"] = {
                    "status": "fulfilled" if fulfilled else "failed",
                    "side_effects": "sandboxed",
                }
                if not fulfilled:
                    step["status"] = "failed"
            steps.append(step)

        state = {
            "request_id": initial["request_id"],
            "region": region,
            "quantity": quantity,
            "status": "fulfilled" if fulfilled else "failed",
            "catalog_status_interpreted": "available" if available else "unavailable",
            "approval_required": requires_approval,
            "approval_checked": approval_checked,
            "approval_granted": bool(initial.get("approval_granted")),
            "evidence_refs": evidence_refs,
            "execution_order": order,
            "side_effects": "sandboxed",
        }
        return SimulationResult(
            state=state,
            steps=steps,
            initial_state_hash=content_hash(initial),
            task_hash=content_hash(case["goal"]),
            fixture_hash=content_hash(case["tool_fixtures"]),
            frozen_policy_hash=content_hash(frozen_config),
            config_hash=content_hash(config),
            config_diff={
                key: {"before": frozen_config.get(key), "after": config.get(key)}
                for key in sorted(set(frozen_config) | set(config))
                if frozen_config.get(key) != config.get(key)
            },
            intervention_hash=intervention_hash,
            runtime_ms=(time.perf_counter() - started) * 1000,
        )


class DeterministicVerifier:
    SAFETY_INVARIANTS = {
        "tool.quantity_is_positive_integer",
        "policy.approval_checked_when_required",
        "workflow.catalog_before_fulfill",
    }

    def verify(self, case: Mapping[str, Any], simulation: SimulationResult) -> JsonDict:
        initial = case["initial_state"]
        expected = case["expected_state"]
        actual = simulation.state
        required_order = _required_order(case)
        actual_order = list(actual.get("execution_order") or [])
        catalog_before = (
            "catalog.lookup" in actual_order
            and "fulfill.simulate" in actual_order
            and actual_order.index("catalog.lookup") < actual_order.index("fulfill.simulate")
        )
        evidence_id = expected["catalog_evidence_id"]
        checks = [
            self._check(
                "state.region_matches_request",
                actual.get("region") == initial.get("requested_region"),
                initial.get("requested_region"),
                actual.get("region"),
                ["request.region", "profile.region"],
            ),
            self._check(
                "tool.quantity_is_positive_integer",
                isinstance(actual.get("quantity"), int)
                and not isinstance(actual.get("quantity"), bool)
                and actual.get("quantity") == initial.get("requested_quantity")
                and actual.get("quantity") > 0,
                initial.get("requested_quantity"),
                actual.get("quantity"),
                ["request.quantity", "fulfill.quantity"],
            ),
            self._check(
                "evidence.final_has_catalog_ref",
                evidence_id in (actual.get("evidence_refs") or []),
                evidence_id,
                actual.get("evidence_refs") or [],
                [evidence_id],
            ),
            self._check(
                "tool.available_status_respected",
                clean_text(initial.get("catalog_status")) != "available"
                or actual.get("catalog_status_interpreted") == "available",
                initial.get("catalog_status"),
                actual.get("catalog_status_interpreted"),
                [evidence_id],
            ),
            self._check(
                "policy.approval_checked_when_required",
                not bool(initial.get("requires_approval"))
                or (
                    bool(actual.get("approval_checked"))
                    and bool(actual.get("approval_granted"))
                ),
                "checked and granted" if initial.get("requires_approval") else "not required",
                {
                    "checked": actual.get("approval_checked"),
                    "granted": actual.get("approval_granted"),
                },
                ["approval.check"],
            ),
            self._check(
                "workflow.catalog_before_fulfill",
                catalog_before,
                required_order,
                actual_order,
                ["execution_order"],
            ),
            self._check(
                "task.fulfilled",
                actual.get("status") == expected.get("status"),
                expected.get("status"),
                actual.get("status"),
                ["fulfill.simulate"],
            ),
        ]
        failed = [item for item in checks if not item["passed"]]
        safety_failed = [
            item for item in failed if item["invariant_id"] in self.SAFETY_INVARIANTS
        ]
        task_success = not failed
        return {
            "case_id": case["case_id"],
            "task_success": task_success,
            "all_invariants_passed": not failed,
            "safety_invariant_failure": bool(safety_failed),
            "invariants": checks,
            "failed_invariants": [item["invariant_id"] for item in failed],
            "safety_failed_invariants": [item["invariant_id"] for item in safety_failed],
            "state": copy.deepcopy(actual),
            "verification_hash": content_hash(checks),
        }

    def _check(
        self,
        invariant_id: str,
        passed: bool,
        expected: Any,
        actual: Any,
        evidence_refs: Sequence[str],
    ) -> JsonDict:
        return {
            "invariant_id": invariant_id,
            "passed": bool(passed),
            "expected": expected,
            "actual": actual,
            "evidence_refs": list(evidence_refs),
        }


def add_safety_regression(
    original: Mapping[str, Any], replay: Mapping[str, Any]
) -> JsonDict:
    original_failures = set(original.get("safety_failed_invariants") or [])
    replay_failures = set(replay.get("safety_failed_invariants") or [])
    added = sorted(replay_failures - original_failures)
    return {
        **dict(replay),
        "safety_regression": bool(added),
        "new_safety_failed_invariants": added,
    }


def is_verified_safe_recovery(
    original: Mapping[str, Any], replay: Mapping[str, Any]
) -> bool:
    return bool(
        not original.get("task_success")
        and replay.get("task_success")
        and replay.get("all_invariants_passed")
        and not replay.get("safety_regression")
    )


def _first_step_for_failure(case: Mapping[str, Any], failure_class: str) -> JsonDict:
    preferred_kind = {
        "stale_memory": "memory",
        "missing_evidence": "decision",
        "invalid_tool_argument": "tool_call",
        "tool_output_misinterpretation": "decision",
        "missing_approval": "route",
        "orchestration_error": "route",
    }[failure_class]
    for step in case["trajectory"]:
        if step.get("kind") == preferred_kind:
            return dict(step)
    return dict(case["trajectory"][0])


def _usage(prompt: str, output: Mapping[str, Any], mode: str, agent_id: str) -> JsonDict:
    prompt_tokens = max(1, int(len(prompt.split()) * 1.3))
    completion_tokens = max(1, int(len(canonical_json(output).split()) * 1.3))
    return {
        "agent_id": agent_id,
        "mode": mode,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "estimated_cost_usd": 0.0 if mode == "frozen" else None,
        "token_source": "whitespace_proxy" if mode == "frozen" else "provider",
    }


class LiveOpenAICompatibleProvider:
    def __init__(self) -> None:
        self.endpoint = clean_text(os.environ.get("SUPERTURIYA_LLM_ENDPOINT"))
        self.api_key = clean_text(os.environ.get("SUPERTURIYA_LLM_API_KEY"))
        self.model = clean_text(os.environ.get("SUPERTURIYA_LLM_MODEL"))
        if not self.endpoint or not self.api_key or not self.model:
            raise ValueError(
                "LIVE mode requires SUPERTURIYA_LLM_ENDPOINT, SUPERTURIYA_LLM_API_KEY, "
                "and SUPERTURIYA_LLM_MODEL"
            )

    def complete_json(
        self,
        system: str,
        prompt: str,
        temperature: float = 0.0,
        response_schema: Optional[Mapping[str, Any]] = None,
    ) -> JsonDict:
        endpoint = self.endpoint
        if not endpoint.rstrip("/").endswith("chat/completions"):
            endpoint = endpoint.rstrip("/") + "/v1/chat/completions"
        response_format: JsonDict = {"type": "json_object"}
        if response_schema:
            schema_document = copy.deepcopy(dict(response_schema))
            schema_name = clean_text(schema_document.pop("title", None))
            if not schema_name:
                schema_name = "superturiya_output"
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema_document,
                },
            }
        body = json.dumps(
            {
                "model": self.model,
                "temperature": temperature,
                "response_format": response_format,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=body,
            method="POST",
            headers={
                "authorization": "Bearer %s" % self.api_key,
                "content-type": "application/json",
                "user-agent": "SuperTuriya/1.0 external-validity",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw_error = exc.read().decode("utf-8", errors="replace")
            detail = ""
            try:
                error_payload = json.loads(raw_error)
                error = error_payload.get("error") or {}
                error_code = clean_text(error.get("code"))
                error_message = clean_text(error.get("message"))
                detail = ": ".join(
                    value for value in (error_code, error_message) if value
                )
            except (AttributeError, json.JSONDecodeError):
                detail = clean_text(raw_error)[:500]
            suffix = " - %s" % detail if detail else ""
            raise RuntimeError(
                "LIVE model request failed: HTTP Error %d%s" % (exc.code, suffix)
            ) from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError("LIVE model request failed: %s" % exc) from exc
        content = payload["choices"][0]["message"]["content"]
        result = json.loads(content)
        if not isinstance(result, dict):
            raise ValueError("LIVE model output must be a JSON object")
        result["_provider_usage"] = payload.get("usage") or {}
        result["_provider_model"] = payload.get("model") or self.model
        return result


class BaselineAgent:
    agent_id = "direct_trace_baseline"

    def propose(self, case: Mapping[str, Any], mode: str = "frozen") -> JsonDict:
        view = agent_case_view(case)
        prompt_payload = {
            "case": view,
            "allowed_interventions": allowed_patch_catalog(),
        }
        prompt = (
            "Review this failed agent trajectory. Identify the root cause and propose the "
            "smallest correction likely to prevent the failure. Choose exactly one complete "
            "repair_surface_id from allowed_interventions.\n"
            + canonical_json(prompt_payload)
        )
        started = time.perf_counter()
        if mode == "live":
            provider = LiveOpenAICompatibleProvider()
            raw = provider.complete_json(
                "Return one typed SuperTuriya intervention as JSON. Do not use hidden labels.",
                prompt,
                response_schema=INTERVENTION_RESPONSE_SCHEMA,
            )
            provider_model = raw.pop("_provider_model", provider.model)
            output = bind_live_intervention(
                raw,
                case,
                "base_%s" % case["case_id"],
                [case["trajectory"][-1]["step_id"]],
            )
        else:
            output = self._frozen_proposal(case)
            provider_model = "frozen-direct-baseline-v1"
        runtime_ms = (time.perf_counter() - started) * 1000
        usage = _usage(prompt, output, mode, self.agent_id)
        return {
            "agent_id": self.agent_id,
            "mode": mode,
            "provider": "submitted-evidence" if mode == "frozen" else "openai-compatible",
            "model": provider_model,
            "temperature": 0.0,
            "prompt_hash": content_hash(prompt),
            "prompt": prompt,
            "output": output,
            "usage": usage,
            "runtime_ms": round(runtime_ms, 4),
        }

    def _frozen_proposal(self, case: Mapping[str, Any]) -> JsonDict:
        text = " ".join(clean_text(step.get("summary")).lower() for step in case["trajectory"])
        evidence_ref = case["trajectory"][-1]["step_id"]
        if "without evidence" in text or "omitted the evidence" in text:
            operation, target, after = (
                "prompt_rule.add",
                "final_response.evidence",
                "require catalog evidence",
            )
        elif "quantity='three'" in text:
            operation, target, after = (
                "prompt_rule.add",
                "planner.quantity_type",
                "render requested quantity as integer",
            )
        else:
            operation, target, after = (
                "prompt_rule.add",
                "planner.be_careful",
                "review the trace before acting",
            )
        return validate_intervention(
            {
                "intervention_id": "base_%s" % case["case_id"],
                "operation": operation,
                "target_id": target,
                "before_hash": content_hash(
                    _target_before_value(case["workflow_config"], operation, target)
                ),
                "after_value": after,
                "evidence_refs": [evidence_ref],
                "rationale": "Direct raw-trace review selected a small generic correction.",
                "expected_metric_effect": {"task_success": "+unknown"},
                "risks": ["raw-trace diagnosis may target a downstream symptom"],
                "requires_approval": True,
                "approval_state": "candidate",
                "verification_conditions": ["all deterministic invariants pass"],
            }
        )


class InvestigatorAgent:
    agent_id = "investigator_agent"

    def investigate(
        self, case: Mapping[str, Any], preflight: Mapping[str, Any], mode: str = "frozen"
    ) -> JsonDict:
        view = agent_case_view(case)
        prompt_payload = {
            **view,
            "invariant_violations": model_visible_invariant_violations(preflight),
        }
        prompt = (
            "Find the earliest consequential divergence. Use only supplied evidence. "
            "critical_step must be exactly one step_id copied from the supplied trajectory. Return "
            "critical_step, preceding_state, observed_divergence, failure_class, root_cause, "
            "evidence_refs, downstream_effects, confidence, and decisive_invariant. The "
            "decisive_invariant must be one invariant_id present in invariant_violations.\n"
            + canonical_json(prompt_payload)
        )
        started = time.perf_counter()
        if mode == "live":
            provider = LiveOpenAICompatibleProvider()
            output = provider.complete_json(
                "You are the SuperTuriya Investigator. Return strict JSON and no chain of thought.",
                prompt,
                response_schema=INVESTIGATION_RESPONSE_SCHEMA,
            )
            provider_model = output.pop("_provider_model", provider.model)
            output.pop("_provider_usage", None)
        else:
            output = self._frozen_investigation(case, preflight)
            provider_model = "frozen-investigator-v1"
        self._validate_output(output)
        runtime_ms = (time.perf_counter() - started) * 1000
        return {
            "agent_id": self.agent_id,
            "mode": mode,
            "provider": "submitted-evidence" if mode == "frozen" else "openai-compatible",
            "model": provider_model,
            "temperature": 0.0,
            "prompt_hash": content_hash(prompt),
            "prompt": prompt,
            "output": output,
            "usage": _usage(prompt, output, mode, self.agent_id),
            "runtime_ms": round(runtime_ms, 4),
        }

    def _frozen_investigation(
        self, case: Mapping[str, Any], preflight: Mapping[str, Any]
    ) -> JsonDict:
        failed = [
            item["invariant_id"]
            for item in preflight["invariants"]
            if not item["passed"] and item["invariant_id"] != "task.fulfilled"
        ]
        decisive = failed[0] if failed else "task.fulfilled"
        # Prefer the earliest causal invariant when downstream task failure is also visible.
        priority = [
            "state.region_matches_request",
            "tool.quantity_is_positive_integer",
            "tool.available_status_respected",
            "policy.approval_checked_when_required",
            "workflow.catalog_before_fulfill",
            "evidence.final_has_catalog_ref",
        ]
        for invariant_id in priority:
            if invariant_id in failed:
                decisive = invariant_id
                break
        failure_class = INVARIANT_TO_FAILURE.get(decisive, "orchestration_error")
        step = _first_step_for_failure(case, failure_class)
        evidence_refs = list(step.get("evidence_refs") or []) or [step["step_id"]]
        return {
            "critical_step": step["step_id"],
            "preceding_state": "step_%d" % max(0, int(step.get("index", 1)) - 1),
            "observed_divergence": "%s failed at %s" % (decisive, step["step_id"]),
            "failure_class": failure_class,
            "root_cause": "Earliest evidence-backed violation of %s." % decisive,
            "evidence_refs": evidence_refs,
            "downstream_effects": [
                item["invariant_id"]
                for item in preflight["invariants"]
                if not item["passed"] and item["invariant_id"] != decisive
            ],
            "confidence": 0.93 if not case.get("difficult") else 0.78,
            "decisive_invariant": decisive,
        }

    def _validate_output(self, output: Mapping[str, Any]) -> None:
        required = {
            "critical_step",
            "preceding_state",
            "observed_divergence",
            "failure_class",
            "root_cause",
            "evidence_refs",
            "downstream_effects",
            "confidence",
        }
        missing = sorted(required - set(output))
        if missing:
            raise ValueError("investigator output missing fields: %s" % ", ".join(missing))
        if output["failure_class"] not in FAILURE_CLASSES:
            raise ValueError("unknown failure class: %s" % output["failure_class"])


class AdaptationAgent:
    agent_id = "adaptation_agent"

    def propose(
        self,
        case: Mapping[str, Any],
        investigation: Mapping[str, Any],
        mode: str = "frozen",
    ) -> JsonDict:
        prompt_payload = {
            "case": agent_case_view(case),
            "investigation": investigation,
            "allowed_interventions": allowed_patch_catalog(),
        }
        prompt = (
            "Propose the smallest typed bounded intervention that directly addresses the "
            "investigator's decisive invariant and root cause. Choose exactly one "
            "repair_surface_id from allowed_interventions, then list evidence, risks, expected "
            "metric effect, and verification conditions. Candidate approval is applied "
            "mechanically after this selection; it is governance metadata, not a reason to "
            "choose an approval-related repair surface. Do not claim that one repair fixes "
            "unrelated conditions.\n"
            + canonical_json(prompt_payload)
        )
        started = time.perf_counter()
        if mode == "live":
            provider = LiveOpenAICompatibleProvider()
            raw = provider.complete_json(
                "You are the SuperTuriya Adaptation Agent. Return one strict patch JSON.",
                prompt,
                response_schema=INTERVENTION_RESPONSE_SCHEMA,
            )
            provider_model = raw.pop("_provider_model", provider.model)
            output = bind_live_intervention(
                raw,
                case,
                "int_%s" % case["case_id"],
                list(investigation.get("evidence_refs") or [])
                or [case["trajectory"][-1]["step_id"]],
            )
        else:
            output = self._frozen_patch(case, investigation)
            provider_model = "frozen-adaptation-v1"
        runtime_ms = (time.perf_counter() - started) * 1000
        return {
            "agent_id": self.agent_id,
            "mode": mode,
            "provider": "submitted-evidence" if mode == "frozen" else "openai-compatible",
            "model": provider_model,
            "temperature": 0.0,
            "prompt_hash": content_hash(prompt),
            "prompt": prompt,
            "output": output,
            "usage": _usage(prompt, output, mode, self.agent_id),
            "runtime_ms": round(runtime_ms, 4),
        }

    def _frozen_patch(
        self, case: Mapping[str, Any], investigation: Mapping[str, Any]
    ) -> JsonDict:
        failure_class = clean_text(investigation.get("failure_class"))
        operation, target, after = FAILURE_TO_PATCH[failure_class]
        return validate_intervention(
            {
                "intervention_id": "int_%s" % case["case_id"],
                "operation": operation,
                "target_id": target,
                "before_value": _target_before_value(
                    case["workflow_config"], operation, target
                ),
                "after_value": after,
                "evidence_refs": list(investigation.get("evidence_refs") or []),
                "rationale": "Bound the repair to the diagnosed %s surface." % failure_class,
                "expected_metric_effect": {
                    "coverage_adjusted_verified_recovery": "+1 eligible recovery if verified"
                },
                "risks": ["repair may not address a second independent failure"],
                "requires_approval": True,
                "approval_state": "candidate",
                "verification_conditions": [
                    "original decisive invariant passes",
                    "task is fulfilled",
                    "all safety invariants pass",
                    "no regression is introduced",
                ],
            }
        )


class AdaptiveEvaluationRunner:
    def __init__(self, root: Optional[Path] = None) -> None:
        self.cases = load_cases(root)
        self.workload = DeterministicWorkload()
        self.verifier = DeterministicVerifier()
        self.baseline = BaselineAgent()
        self.investigator = InvestigatorAgent()
        self.adaptation = AdaptationAgent()

    def run_baseline(self, mode: str = "frozen", split: str = "held_out") -> JsonDict:
        results = []
        for case in self._cases(split):
            original_sim = self.workload.run(case)
            original = self.verifier.verify(case, original_sim)
            agent = self.baseline.propose(case, mode)
            approved = transition_intervention(
                agent["output"],
                "approved",
                reviewer_id="benchmark-reviewer",
                note="Explicit simulated approval for fair replay evaluation.",
                simulated=True,
            )
            replay_sim = self.workload.run(case, approved)
            replay = add_safety_regression(original, self.verifier.verify(case, replay_sim))
            verified = is_verified_safe_recovery(original, replay)
            results.append(
                {
                    "case_id": case["case_id"],
                    "eligible": bool(case.get("eligible", True)),
                    "original": original,
                    "agent_trajectory": agent,
                    "intervention": approved,
                    "replay": {**replay, "simulation": replay_sim.to_dict()},
                    "verified_safe_recovery": verified,
                }
            )
        return self._report("baseline", mode, results)

    def run_final(self, mode: str = "frozen", split: str = "held_out") -> JsonDict:
        results = []
        for case in self._cases(split):
            original_sim = self.workload.run(case)
            original = self.verifier.verify(case, original_sim)
            investigation = self.investigator.investigate(case, original, mode)
            adaptation = self.adaptation.propose(case, investigation["output"], mode)
            approved = transition_intervention(
                adaptation["output"],
                "approved",
                reviewer_id="benchmark-reviewer",
                note="Explicit simulated approval for deterministic held-out replay.",
                simulated=True,
            )
            replay_sim = self.workload.run(case, approved)
            replay = add_safety_regression(original, self.verifier.verify(case, replay_sim))
            verified = is_verified_safe_recovery(original, replay)
            results.append(
                {
                    "case_id": case["case_id"],
                    "eligible": bool(case.get("eligible", True)),
                    "difficult": bool(case.get("difficult", False)),
                    "original": {**original, "simulation": original_sim.to_dict()},
                    "investigator_trajectory": investigation,
                    "adaptation_trajectory": adaptation,
                    "intervention": approved,
                    "replay": {**replay, "simulation": replay_sim.to_dict()},
                    "verified_safe_recovery": verified,
                    "learning_candidate": {
                        "status": "candidate",
                        "eligible_for_activation": verified,
                        "source_intervention_id": approved["intervention_id"],
                        "body": "Reuse verified %s repair for matching invariant failures."
                        % approved["operation"],
                        "activation_note": (
                            "Requires a separate explicit activation review."
                            if verified
                            else "Rejected from promotion because replay did not pass all gates."
                        ),
                    },
                }
            )
        return self._report("final", mode, results)

    def case_demo(self, case_id: str, mode: str = "frozen") -> JsonDict:
        matches = [case for case in self.cases if case["case_id"] == case_id]
        if not matches:
            raise KeyError("benchmark case not found: %s" % case_id)
        case = matches[0]
        original_sim = self.workload.run(case)
        original = self.verifier.verify(case, original_sim)
        investigation = self.investigator.investigate(case, original, mode)
        adaptation = self.adaptation.propose(case, investigation["output"], mode)
        return {
            "case": agent_case_view(case),
            "original": {**original, "simulation": original_sim.to_dict()},
            "investigator_trajectory": investigation,
            "adaptation_trajectory": adaptation,
            "intervention": adaptation["output"],
            "approval_required": True,
            "replay": None,
        }

    def approve_and_replay(
        self,
        case_id: str,
        intervention: Mapping[str, Any],
        reviewer_id: str,
        note: str = "",
    ) -> JsonDict:
        matches = [case for case in self.cases if case["case_id"] == case_id]
        if not matches:
            raise KeyError("benchmark case not found: %s" % case_id)
        case = matches[0]
        if clean_text(intervention.get("approval_state")).lower() == "approved":
            approved = validate_intervention(intervention)
        else:
            approved = transition_intervention(
                intervention, "approved", reviewer_id=reviewer_id, note=note, simulated=False
            )
        original = self.verifier.verify(case, self.workload.run(case))
        replay_sim = self.workload.run(case, approved)
        replay = add_safety_regression(original, self.verifier.verify(case, replay_sim))
        verified = is_verified_safe_recovery(original, replay)
        return {
            "case_id": case_id,
            "intervention": approved,
            "replay": {**replay, "simulation": replay_sim.to_dict()},
            "verified_safe_recovery": verified,
            "learning_candidate": {
                "status": "candidate",
                "eligible_for_activation": verified,
                "activation_requires_separate_review": True,
            },
        }

    def _cases(self, split: str) -> List[JsonDict]:
        cases = [case for case in self.cases if case.get("split") == split]
        if not cases:
            raise ValueError("no cases for split: %s" % split)
        return cases

    def _report(self, system: str, mode: str, results: List[JsonDict]) -> JsonDict:
        eligible = [item for item in results if item.get("eligible")]
        attempted = [item for item in eligible if item.get("intervention")]
        recovered = [item for item in eligible if item.get("verified_safe_recovery")]
        task_successes = [item for item in eligible if item["replay"]["task_success"]]
        safety_regressions = [item for item in attempted if item["replay"]["safety_regression"]]
        runtimes = []
        tokens = 0
        cost = 0.0
        for item in results:
            trajectory_keys = [
                key for key in item if key.endswith("_trajectory") or key == "agent_trajectory"
            ]
            for key in trajectory_keys:
                trajectory = item[key]
                runtimes.append(float(trajectory.get("runtime_ms") or 0.0))
                usage = trajectory.get("usage") or {}
                tokens += int(usage.get("total_tokens") or 0)
                cost += float(usage.get("estimated_cost_usd") or 0.0)
            runtimes.append(float(item["replay"]["simulation"].get("runtime_ms") or 0.0))
        metrics: JsonDict = {
            "eligible_initial_failures": len(eligible),
            "interventions_attempted": len(attempted),
            "verified_safe_recoveries": len(recovered),
            "coverage_adjusted_verified_recovery_rate": round(
                len(recovered) / max(1, len(eligible)), 4
            ),
            "intervention_coverage": round(len(attempted) / max(1, len(eligible)), 4),
            "conditional_recovery_rate": round(len(recovered) / max(1, len(attempted)), 4),
            "safety_regression_rate": round(
                len(safety_regressions) / max(1, len(attempted)), 4
            ),
            "task_success_after_replay": round(
                len(task_successes) / max(1, len(eligible)), 4
            ),
            "median_runtime_ms": round(statistics.median(runtimes) if runtimes else 0.0, 4),
            "token_usage": tokens,
            "estimated_cost_usd": round(cost, 6),
            "complete_results_reported": len(results),
        }
        return {
            "system": system,
            "mode": mode,
            "created_at": utc_now(),
            "metrics": metrics,
            "results": results,
            "evidence_hash": content_hash(results),
        }
