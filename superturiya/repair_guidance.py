from __future__ import annotations

import copy
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .adaptive import (
    PATCH_SURFACES,
    DeterministicVerifier,
    DeterministicWorkload,
    add_safety_regression,
    content_hash,
    is_verified_safe_recovery,
    transition_intervention,
    validate_intervention,
)
from .models import JsonDict, clean_text, new_id, utc_now


REPAIR_EFFECTS: Dict[str, Sequence[str]] = {
    "retrieval.filter::context.region": ("state.region_matches_request",),
    "prompt_rule.replace::planner.region_precedence": ("state.region_matches_request",),
    "prompt_rule.add::final_response.evidence": ("evidence.final_has_catalog_ref",),
    "recovery_step.insert::finalizer.attach_evidence": ("evidence.final_has_catalog_ref",),
    "tool_argument.constraint::fulfill.quantity": ("tool.quantity_is_positive_integer",),
    "prompt_rule.add::planner.quantity_type": ("tool.quantity_is_positive_integer",),
    "prompt_rule.add::planner.quantity_range": ("tool.quantity_is_positive_integer",),
    "tool_result.validation::catalog.status": ("tool.available_status_respected",),
    "prompt_rule.replace::planner.catalog_mapping": ("tool.available_status_respected",),
    "approval_rule.add::fulfill.approval": (
        "policy.approval_checked_when_required",
    ),
    "route.condition::workflow.approval_route": (
        "policy.approval_checked_when_required",
    ),
    "route.condition::workflow.order": ("workflow.catalog_before_fulfill",),
    "recovery_step.insert::workflow.preflight": ("workflow.catalog_before_fulfill",),
    "prompt_rule.add::planner.be_careful": (),
}

# Prefer enforcement at the narrowest executable boundary over a broad prompt rule.
SURFACE_PRIORITY = {
    "retrieval.filter::context.region": 0,
    "tool_argument.constraint::fulfill.quantity": 0,
    "tool_result.validation::catalog.status": 0,
    "approval_rule.add::fulfill.approval": 0,
    "route.condition::workflow.order": 0,
    "prompt_rule.add::final_response.evidence": 0,
    "prompt_rule.replace::planner.region_precedence": 1,
    "prompt_rule.add::planner.quantity_type": 1,
    "prompt_rule.add::planner.quantity_range": 2,
    "prompt_rule.replace::planner.catalog_mapping": 1,
    "route.condition::workflow.approval_route": 1,
    "recovery_step.insert::workflow.preflight": 1,
    "recovery_step.insert::finalizer.attach_evidence": 1,
    "prompt_rule.add::planner.be_careful": 99,
}

TARGET_CONFIG_KEYS = {
    "retrieval.filter::context.region": "retrieval_filter",
    "prompt_rule.replace::planner.region_precedence": "retrieval_filter",
    "prompt_rule.add::final_response.evidence": "require_evidence",
    "recovery_step.insert::finalizer.attach_evidence": "require_evidence",
    "tool_argument.constraint::fulfill.quantity": "quantity_constraint",
    "prompt_rule.add::planner.quantity_type": "quantity_constraint",
    "prompt_rule.add::planner.quantity_range": "quantity_constraint",
    "tool_result.validation::catalog.status": "result_validation",
    "prompt_rule.replace::planner.catalog_mapping": "result_validation",
    "approval_rule.add::fulfill.approval": "approval_rule",
    "route.condition::workflow.approval_route": "approval_rule",
    "route.condition::workflow.order": "enforce_order",
    "recovery_step.insert::workflow.preflight": "enforce_order",
    "prompt_rule.add::planner.be_careful": "",
}


class ReplayGuidedRepairSelector:
    """Select a bounded repair through declared causal effects and frozen replay.

    This is intentionally a versioned post-v2 layer. It does not change the
    External-v2 inference runtime or any frozen benchmark artifact.
    """

    strategy_id = "replay_guided_repair_v1"

    def __init__(
        self,
        workload: Optional[DeterministicWorkload] = None,
        verifier: Optional[DeterministicVerifier] = None,
    ) -> None:
        self.workload = workload or DeterministicWorkload()
        self.verifier = verifier or DeterministicVerifier()

    def compatible_surfaces(self, decisive_invariant: str) -> List[str]:
        invariant = clean_text(decisive_invariant)
        return sorted(
            [surface for surface, effects in REPAIR_EFFECTS.items() if invariant in effects],
            key=lambda surface: (SURFACE_PRIORITY.get(surface, 50), surface),
        )

    def select(
        self,
        case: Mapping[str, Any],
        investigation: Mapping[str, Any],
    ) -> JsonDict:
        decisive = clean_text(investigation.get("decisive_invariant"))
        candidate_surfaces = self.compatible_surfaces(decisive)
        original = self.verifier.verify(case, self.workload.run(case))
        evaluated = [
            self._evaluate_surface(case, investigation, original, surface)
            for surface in candidate_surfaces
        ]
        recoveries = [item for item in evaluated if item["verified_safe_recovery"]]
        selected = recoveries[0] if recoveries else None
        result: JsonDict = {
            "strategy_id": self.strategy_id,
            "created_at": utc_now(),
            "case_id": case["case_id"],
            "decisive_invariant": decisive,
            "candidate_surfaces": candidate_surfaces,
            "candidate_evaluations": evaluated,
            "abstained": selected is None,
            "abstention_reason": (
                "no compatible one-patch candidate achieved verified safe recovery"
                if selected is None
                else None
            ),
            "recommended_intervention": (
                copy.deepcopy(selected["candidate_intervention"]) if selected else None
            ),
            "selected_surface": selected["repair_surface_id"] if selected else None,
            "verified_safe_recovery": bool(selected),
        }
        result["decision_hash"] = content_hash(
            {key: value for key, value in result.items() if key != "decision_hash"}
        )
        return result

    def oracle_ceiling(
        self,
        cases: Sequence[Mapping[str, Any]],
        split: str = "held_out",
    ) -> JsonDict:
        results = []
        for case in cases:
            if clean_text(case.get("split")) != split:
                continue
            original = self.verifier.verify(case, self.workload.run(case))
            evaluated = [
                self._evaluate_surface(
                    case,
                    {
                        "decisive_invariant": "oracle_one_patch",
                        "evidence_refs": [case["trajectory"][-1]["step_id"]],
                    },
                    original,
                    surface,
                )
                for surface in sorted(
                    PATCH_SURFACES,
                    key=lambda item: (SURFACE_PRIORITY.get(item, 50), item),
                )
                if REPAIR_EFFECTS.get(surface)
            ]
            recovered = next(
                (item for item in evaluated if item["verified_safe_recovery"]), None
            )
            results.append(
                {
                    "case_id": case["case_id"],
                    "initially_failed": not original["task_success"],
                    "one_patch_recoverable": recovered is not None,
                    "first_recovering_surface": (
                        recovered["repair_surface_id"] if recovered else None
                    ),
                    "failed_invariants": list(original["failed_invariants"]),
                }
            )
        eligible = [item for item in results if item["initially_failed"]]
        recoverable = [item for item in eligible if item["one_patch_recoverable"]]
        report: JsonDict = {
            "strategy_id": "one_patch_oracle_v1",
            "split": split,
            "eligible_initial_failures": len(eligible),
            "one_patch_recoverable": len(recoverable),
            "ceiling_rate": round(len(recoverable) / max(1, len(eligible)), 4),
            "results": results,
        }
        report["report_hash"] = content_hash(report)
        return report

    def _evaluate_surface(
        self,
        case: Mapping[str, Any],
        investigation: Mapping[str, Any],
        original: Mapping[str, Any],
        surface_id: str,
    ) -> JsonDict:
        candidate = self._candidate(case, investigation, surface_id)
        approved = transition_intervention(
            candidate,
            "approved",
            reviewer_id="replay-guidance-simulator",
            note="Ephemeral approval for candidate comparison only.",
            simulated=True,
        )
        replay_sim = self.workload.run(case, approved)
        replay = add_safety_regression(
            original,
            self.verifier.verify(case, replay_sim),
        )
        decisive = clean_text(investigation.get("decisive_invariant"))
        decisive_check = next(
            (
                item
                for item in replay["invariants"]
                if item["invariant_id"] == decisive
            ),
            None,
        )
        return {
            "repair_surface_id": surface_id,
            "declared_effects": list(REPAIR_EFFECTS[surface_id]),
            "candidate_intervention": candidate,
            "decisive_invariant_passed": (
                bool(decisive_check["passed"]) if decisive_check else None
            ),
            "failed_invariants_after": list(replay["failed_invariants"]),
            "safety_regression": bool(replay["safety_regression"]),
            "config_diff": copy.deepcopy(replay_sim.config_diff),
            "verification_hash": replay["verification_hash"],
            "verified_safe_recovery": is_verified_safe_recovery(original, replay),
        }

    def _candidate(
        self,
        case: Mapping[str, Any],
        investigation: Mapping[str, Any],
        surface_id: str,
    ) -> JsonDict:
        patch = PATCH_SURFACES[surface_id]
        config_key = TARGET_CONFIG_KEYS[surface_id]
        before = case["workflow_config"].get(config_key) if config_key else None
        evidence_refs = [
            clean_text(item)
            for item in investigation.get("evidence_refs") or []
            if clean_text(item)
        ]
        if not evidence_refs:
            evidence_refs = [case["trajectory"][-1]["step_id"]]
        return validate_intervention(
            {
                "intervention_id": new_id("guided"),
                "operation": patch["operation"],
                "target_id": patch["target_id"],
                "before_hash": content_hash(before),
                "after_value": patch["after_value"],
                "evidence_refs": evidence_refs,
                "rationale": (
                    "Declared repair effects include %s; verify through frozen replay."
                    % clean_text(investigation.get("decisive_invariant"))
                ),
                "expected_metric_effect": {
                    "summary": "repair the decisive invariant without a safety regression"
                },
                "risks": [
                    "one bounded patch may not repair an independent second failure"
                ],
                "requires_approval": True,
                "approval_state": "candidate",
                "verification_conditions": [
                    "decisive invariant passes",
                    "all invariants pass",
                    "no safety regression is introduced",
                ],
            }
        )
