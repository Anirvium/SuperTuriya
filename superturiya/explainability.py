from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from .models import JsonDict, clean_text


DEFAULT_LIVE_EVIDENCE = (
    Path(__file__).resolve().parent.parent
    / "evidence"
    / "external_validity"
    / "v1"
    / "live_comparison.json"
)
GROQ_ENDPOINT_SHA256 = (
    "dfd2a15f09373fda210f3abc40f9c258363058225f1ec5b33ce607d37ff1ae57"
)


def _index_results(report: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    return {
        clean_text(item.get("case_id")): item
        for item in report.get("results", [])
        if clean_text(item.get("case_id"))
    }


def live_explainability_state(path: Optional[Path] = None) -> JsonDict:
    """Return a safe, judge-facing view of recorded LIVE evidence.

    Prompts, provider credentials, and hidden reasoning traces are intentionally excluded.
    The returned explanations are the model's structured, auditable outputs only.
    """

    evidence_path = Path(path or DEFAULT_LIVE_EVIDENCE)
    if not evidence_path.exists():
        return {
            "status": "unavailable",
            "message": "No completed same-model LIVE comparison artifact is available.",
            "artifact_path": str(evidence_path),
        }

    document = json.loads(evidence_path.read_text(encoding="utf-8"))
    trials = list(document.get("trials") or [])
    if not trials:
        return {
            "status": "unavailable",
            "message": "The LIVE comparison artifact contains no completed trial.",
            "artifact_path": str(evidence_path),
        }

    scored_trial = trials[-1]
    runtime = scored_trial.get("runtime") or {}
    baseline = _index_results(runtime.get("baseline") or {})
    final = _index_results(runtime.get("final") or {})
    scored_cases = {
        clean_text(item.get("case_id")): item
        for item in scored_trial.get("cases", [])
        if clean_text(item.get("case_id"))
    }
    contract = document.get("contract") or {}
    endpoint_hash = clean_text(contract.get("endpoint_sha256"))
    ledger = runtime.get("provider_ledger") or {}
    usage = ledger.get("usage") or {}
    provider = "Groq" if endpoint_hash == GROQ_ENDPOINT_SHA256 else "OpenAI-compatible provider"

    cases = []
    for case_id, result in final.items():
        investigation = (result.get("investigator_trajectory") or {}).get("output") or {}
        adaptation = (result.get("adaptation_trajectory") or {}).get("output") or {}
        original = result.get("original") or {}
        replay = result.get("replay") or {}
        baseline_result = baseline.get(case_id) or {}
        scored = scored_cases.get(case_id) or {}
        cases.append(
            {
                "case_id": case_id,
                "difficult": bool(result.get("difficult")),
                "original_failed_invariants": list(original.get("failed_invariants") or []),
                "investigator": {
                    "critical_step": investigation.get("critical_step"),
                    "decisive_invariant": investigation.get("decisive_invariant"),
                    "failure_class": investigation.get("failure_class"),
                    "root_cause": investigation.get("root_cause"),
                    "observed_divergence": investigation.get("observed_divergence"),
                    "evidence_refs": list(investigation.get("evidence_refs") or []),
                    "confidence": investigation.get("confidence"),
                },
                "adaptation": {
                    "operation": adaptation.get("operation"),
                    "target_id": adaptation.get("target_id"),
                    "after_value": adaptation.get("after_value"),
                    "rationale": adaptation.get("rationale"),
                    "risks": list(adaptation.get("risks") or []),
                    "verification_conditions": list(
                        adaptation.get("verification_conditions") or []
                    ),
                    "approval_state": adaptation.get("approval_state"),
                },
                "verifier": {
                    "verified_safe_recovery": bool(result.get("verified_safe_recovery")),
                    "failed_after_replay": list(replay.get("failed_invariants") or []),
                    "safety_regression": bool(replay.get("safety_regression")),
                    "verification_hash": replay.get("verification_hash"),
                },
                "baseline_verified_safe_recovery": bool(
                    baseline_result.get("verified_safe_recovery")
                ),
                "scoring": {
                    "critical_step_correct": bool(scored.get("critical_step_correct")),
                    "failure_class_correct": bool(scored.get("failure_class_correct")),
                    "repair_surface_correct": bool(scored.get("repair_surface_correct")),
                },
            }
        )

    history_root = evidence_path.parent / "history"
    history_count = len(list(history_root.glob("live_comparison_*.json"))) if history_root.exists() else 0
    return {
        "status": "available",
        "evidence_class": "development",
        "headline": "Same-model LIVE parity; structured diagnosis is stronger than recovery lift.",
        "disclosure": (
            "This v1 benchmark became development evidence after prompt tuning. "
            "It is not the final untouched held-out claim."
        ),
        "created_at": document.get("created_at"),
        "benchmark_id": document.get("benchmark_id"),
        "trial_count": document.get("trial_count"),
        "provider": {
            "name": provider,
            "display_name": "GPT-OSS-120B reasoning model",
            "model": contract.get("requested_model"),
            "temperature": contract.get("temperature"),
            "same_model_enforced": bool(contract.get("baseline_and_final_share_environment")),
            "credential_present_during_run": bool(contract.get("credential_present")),
            "credential_recorded": bool(contract.get("credential_recorded")),
            "call_count": usage.get("call_count"),
            "total_tokens": usage.get("total_tokens"),
        },
        "aggregate": document.get("aggregate") or {},
        "metrics": scored_trial.get("metrics") or {},
        "cases": cases,
        "history_count": history_count,
        "explainability_contract": {
            "visible": [
                "structured diagnosis",
                "evidence references",
                "typed repair candidate",
                "risks and verification conditions",
                "deterministic replay verdict",
                "human approval state",
            ],
            "not_exposed": [
                "private chain-of-thought",
                "provider credential",
                "hidden evaluator labels during inference",
            ],
            "authority": "The model proposes; deterministic verification and human approval decide.",
        },
    }
