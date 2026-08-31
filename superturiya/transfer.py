from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional

from .adaptive import (
    DeterministicVerifier,
    DeterministicWorkload,
    add_safety_regression,
    is_verified_safe_recovery,
    validate_intervention,
)
from .models import JsonDict, clean_text, new_id


DEFAULT_SHADOW_CASE = (
    Path(__file__).resolve().parent.parent / "showcase" / "shadow_transfer_case.json"
)


class ShadowTransferEvaluator:
    """Evaluate one activated procedural policy outside the primary benchmark."""

    def __init__(self, case_path: Optional[Path] = None) -> None:
        document = json.loads(Path(case_path or DEFAULT_SHADOW_CASE).read_text(encoding="utf-8"))
        self.case = dict(document["case"])
        self.workload = DeterministicWorkload()
        self.verifier = DeterministicVerifier()

    def evaluate(self, policy: Mapping[str, Any]) -> JsonDict:
        if clean_text(policy.get("status")).lower() != "active":
            raise ValueError("shadow transfer requires an active procedural policy")
        operation, target, after = self._structured_policy(policy)
        intervention = validate_intervention(
            {
                "intervention_id": new_id("transfer"),
                "operation": operation,
                "target_id": target,
                "before_value": self.case["workflow_config"]["quantity_constraint"],
                "after_value": after,
                "evidence_refs": ["policy:%s" % policy["policy_id"]],
                "rationale": "Apply an already activated procedural policy to a separate structurally matching shadow case.",
                "expected_metric_effect": {"shadow_verified_recovery": "+1 if verified"},
                "risks": ["single synthetic shadow case does not establish broad transfer"],
                "requires_approval": True,
                "approval_state": "active",
                "verification_conditions": [
                    "shadow task succeeds",
                    "all shadow invariants pass",
                    "no safety regression is introduced",
                ],
                "source_policy_id": policy["policy_id"],
            }
        )
        original_sim = self.workload.run(self.case)
        original = self.verifier.verify(self.case, original_sim)
        replay_sim = self.workload.run(self.case, intervention)
        replay = add_safety_regression(
            original, self.verifier.verify(self.case, replay_sim)
        )
        verified = is_verified_safe_recovery(original, replay)
        return {
            "outside_primary_benchmark": True,
            "case_id": self.case["case_id"],
            "trajectory_length": len(self.case["trajectory"]),
            "source_policy": dict(policy),
            "matched_signature": {
                "operation": operation,
                "target_id": target,
            },
            "transfer_intervention": intervention,
            "original": {**original, "simulation": original_sim.to_dict()},
            "replay": {**replay, "simulation": replay_sim.to_dict()},
            "verified_safe_transfer": verified,
            "claim_boundary": "One curated shadow case demonstrates policy reuse; it does not alter CAVRR or prove production generalization.",
        }

    def _structured_policy(self, policy: Mapping[str, Any]) -> tuple:
        title = clean_text(policy.get("title"))
        body = clean_text(policy.get("body"))
        if "tool_argument.constraint" not in title or "fulfill.quantity" not in body:
            raise ValueError("active policy does not match the shadow case repair surface")
        return (
            "tool_argument.constraint",
            "fulfill.quantity",
            "positive integer equal to requested quantity",
        )
