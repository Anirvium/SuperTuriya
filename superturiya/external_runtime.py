from __future__ import annotations

import copy
import hashlib
import os
import statistics
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional
from unittest import mock

from .adaptive import (
    AdaptiveEvaluationRunner,
    LiveOpenAICompatibleProvider,
    add_safety_regression,
    content_hash,
    is_verified_safe_recovery,
    transition_intervention,
    validate_intervention,
)
from .models import JsonDict, clean_text, utc_now


EXTERNAL_BENCHMARK_ROOT = (
    Path(__file__).resolve().parent.parent / "benchmark" / "external_v1"
)
EXTERNAL_BENCHMARK_ID = "superturiya-external-structural-transfer-v1"
LIVE_PROBE_RESPONSE_SCHEMA = {
    "title": "superturiya_live_probe",
    "type": "object",
    "properties": {"status": {"type": "string", "enum": ["ok"]}},
    "required": ["status"],
    "additionalProperties": False,
}


class SameModelContractError(RuntimeError):
    pass


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _live_environment() -> Dict[str, str]:
    endpoint = clean_text(os.environ.get("SUPERTURIYA_LLM_ENDPOINT"))
    api_key = clean_text(os.environ.get("SUPERTURIYA_LLM_API_KEY"))
    model = clean_text(os.environ.get("SUPERTURIYA_LLM_MODEL"))
    if not endpoint or not api_key or not model:
        raise SameModelContractError(
            "same-model LIVE evaluation requires SUPERTURIYA_LLM_ENDPOINT, "
            "SUPERTURIYA_LLM_API_KEY, and SUPERTURIYA_LLM_MODEL"
        )
    return {"endpoint": endpoint, "api_key": api_key, "model": model}


def _public_live_contract(
    config: Mapping[str, str], transport_policy: Optional[Mapping[str, Any]] = None
) -> JsonDict:
    return {
        "requested_model": config["model"],
        "endpoint_sha256": _sha256_text(config["endpoint"]),
        "credential_present": bool(config["api_key"]),
        "credential_recorded": False,
        "temperature": 0.0,
        "baseline_and_final_share_environment": True,
        "transport_policy": dict(transport_policy or _transport_policy()),
    }


def _transport_policy() -> JsonDict:
    """Read optional, public transport controls for constrained provider tiers."""

    try:
        min_interval = float(
            os.environ.get("SUPERTURIYA_LLM_MIN_INTERVAL_SECONDS", "0")
        )
        max_retries = int(os.environ.get("SUPERTURIYA_LLM_MAX_RETRIES", "4"))
        retry_base = float(
            os.environ.get("SUPERTURIYA_LLM_RETRY_BASE_SECONDS", "2")
        )
    except ValueError as exc:
        raise SameModelContractError(
            "LIVE transport controls must be numeric"
        ) from exc
    if not 0 <= min_interval <= 60:
        raise SameModelContractError(
            "SUPERTURIYA_LLM_MIN_INTERVAL_SECONDS must be between 0 and 60"
        )
    if not 0 <= max_retries <= 10:
        raise SameModelContractError(
            "SUPERTURIYA_LLM_MAX_RETRIES must be between 0 and 10"
        )
    if not 0.1 <= retry_base <= 60:
        raise SameModelContractError(
            "SUPERTURIYA_LLM_RETRY_BASE_SECONDS must be between 0.1 and 60"
        )
    return {
        "min_interval_seconds": min_interval,
        "max_retries": max_retries,
        "retry_base_seconds": retry_base,
    }


def _transient_failure_reason(exc: RuntimeError) -> Optional[str]:
    message = str(exc).lower()
    if "429" in message or "too many requests" in message:
        return "rate_limit_429"
    for status in ("500", "502", "503", "504"):
        if "http error %s" % status in message:
            return "provider_http_%s" % status
    if "timed out" in message or "timeout" in message:
        return "provider_timeout"
    if "temporarily unavailable" in message or "connection reset" in message:
        return "provider_temporarily_unavailable"
    return None


@contextmanager
def _guard_provider_transport(policy: Mapping[str, Any]) -> Iterator[JsonDict]:
    """Pace LIVE calls and retry only explicit transient provider failures."""

    original = LiveOpenAICompatibleProvider.complete_json
    state: JsonDict = {
        "policy": dict(policy),
        "request_attempts": 0,
        "successful_calls": 0,
        "retry_count": 0,
        "paced_sleep_seconds": 0.0,
        "retry_sleep_seconds": 0.0,
        "retry_events": [],
    }
    last_attempt_started: List[Optional[float]] = [None]

    def guarded(
        provider: LiveOpenAICompatibleProvider,
        system: str,
        prompt: str,
        temperature: float = 0.0,
        response_schema: Optional[Mapping[str, Any]] = None,
    ) -> JsonDict:
        max_retries = int(policy["max_retries"])
        min_interval = float(policy["min_interval_seconds"])
        retry_base = float(policy["retry_base_seconds"])
        for attempt in range(max_retries + 1):
            now = time.monotonic()
            if last_attempt_started[0] is not None:
                remaining = min_interval - (now - last_attempt_started[0])
                if remaining > 0:
                    time.sleep(remaining)
                    state["paced_sleep_seconds"] += remaining
            last_attempt_started[0] = time.monotonic()
            state["request_attempts"] += 1
            try:
                result = original(
                    provider, system, prompt, temperature, response_schema
                )
            except RuntimeError as exc:
                reason = _transient_failure_reason(exc)
                if reason is None or attempt >= max_retries:
                    raise
                delay = min(60.0, retry_base * (2**attempt))
                state["retry_count"] += 1
                state["retry_events"].append(
                    {
                        "reason": reason,
                        "failed_attempt": attempt + 1,
                        "next_delay_seconds": delay,
                    }
                )
                time.sleep(delay)
                state["retry_sleep_seconds"] += delay
                continue
            state["successful_calls"] += 1
            return result
        raise AssertionError("unreachable LIVE retry state")

    with mock.patch.object(LiveOpenAICompatibleProvider, "complete_json", guarded):
        yield state


@contextmanager
def _capture_provider_calls() -> Iterator[List[JsonDict]]:
    calls: List[JsonDict] = []
    original = LiveOpenAICompatibleProvider.complete_json

    def wrapped(
        provider: LiveOpenAICompatibleProvider,
        system: str,
        prompt: str,
        temperature: float = 0.0,
        response_schema: Optional[Mapping[str, Any]] = None,
    ) -> JsonDict:
        result = original(provider, system, prompt, temperature, response_schema)
        calls.append(
            {
                "system_role": system.split(".", 1)[0][:120],
                "prompt_hash": content_hash(prompt),
                "requested_model": provider.model,
                "returned_model": clean_text(result.get("_provider_model")) or provider.model,
                "temperature": temperature,
                "response_schema_hash": (
                    content_hash(response_schema) if response_schema else None
                ),
                "usage": copy.deepcopy(result.get("_provider_usage") or {}),
            }
        )
        return result

    with mock.patch.object(LiveOpenAICompatibleProvider, "complete_json", wrapped):
        yield calls


def _case_ids(report: Mapping[str, Any]) -> List[str]:
    return [str(item["case_id"]) for item in report.get("results", [])]


def _assert_case_parity(baseline: Mapping[str, Any], final: Mapping[str, Any]) -> None:
    baseline_ids = _case_ids(baseline)
    final_ids = _case_ids(final)
    if baseline_ids != final_ids:
        raise SameModelContractError("baseline/final case order or membership differs")
    for left, right in zip(baseline["results"], final["results"]):
        if left["original"]["verification_hash"] != right["original"]["verification_hash"]:
            raise SameModelContractError(
                "baseline/final original verification differs for %s" % left["case_id"]
            )


def _provider_totals(calls: List[Mapping[str, Any]]) -> JsonDict:
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    for call in calls:
        usage = call.get("usage") or {}
        prompt_tokens += int(usage.get("prompt_tokens") or 0)
        completion_tokens += int(usage.get("completion_tokens") or 0)
        total_tokens += int(usage.get("total_tokens") or 0)
    return {
        "call_count": len(calls),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "source": "provider_response",
    }


def _mean(values: List[float]) -> float:
    return round(statistics.mean(values), 6) if values else 0.0


def _stdev(values: List[float]) -> float:
    return round(statistics.stdev(values), 6) if len(values) > 1 else 0.0


class ExternalRuntimeRunner:
    """Runtime-only external evaluation stage. It never owns evaluator gold data."""

    def __init__(
        self, root: Optional[Path] = None, benchmark_id: Optional[str] = None
    ) -> None:
        self.root = Path(root or EXTERNAL_BENCHMARK_ROOT)
        self.benchmark_id = benchmark_id or EXTERNAL_BENCHMARK_ID
        self.runner = AdaptiveEvaluationRunner(self.root)

    def probe_live_provider(self) -> JsonDict:
        """Verify endpoint, credential, JSON mode, usage, and model identity once."""

        config = _live_environment()
        policy = _transport_policy()
        provider = LiveOpenAICompatibleProvider()
        prompt = '{"probe":"return status ok as a JSON object"}'
        with _guard_provider_transport(policy) as transport:
            result = provider.complete_json(
                "Return only a valid JSON object with a status field set to ok.",
                prompt,
                0.0,
                LIVE_PROBE_RESPONSE_SCHEMA,
            )
        if clean_text(result.get("status")).lower() != "ok":
            raise SameModelContractError(
                "LIVE provider probe did not return the required JSON status"
            )
        returned_model = clean_text(result.get("_provider_model")) or provider.model
        return {
            "artifact_schema": "same-model-live-probe-v1",
            "created_at": utc_now(),
            "status": "ready",
            "contract": _public_live_contract(config, policy),
            "returned_model": returned_model,
            "provider_identity_present": bool(returned_model),
            "json_object_received": isinstance(result, dict),
            "strict_schema_enforced": True,
            "prompt_hash": content_hash(prompt),
            "usage": copy.deepcopy(result.get("_provider_usage") or {}),
            "transport": transport,
            "response_content_recorded": False,
        }

    def run_comparison(self, mode: str = "frozen") -> JsonDict:
        if mode not in {"frozen", "live"}:
            raise ValueError("mode must be frozen or live")
        baseline = self.runner.run_baseline(mode=mode, split="held_out")
        final = self.runner.run_final(mode=mode, split="held_out")
        _assert_case_parity(baseline, final)
        return {
            "artifact_schema": "external-runtime-comparison-v1",
            "benchmark_id": self.benchmark_id,
            "created_at": utc_now(),
            "mode": mode,
            "case_count": len(baseline["results"]),
            "baseline": baseline,
            "final": final,
            "resource_parity": {
                "same_case_ids": True,
                "same_case_order": True,
                "same_original_verification": True,
                "same_replay_engine": True,
                "same_verifier": True,
                "same_approval_semantics": True,
            },
        }

    def run_same_model_live(self, trials: int = 3) -> JsonDict:
        if trials < 1:
            raise ValueError("trials must be positive")
        config = _live_environment()
        policy = _transport_policy()
        public_contract = _public_live_contract(config, policy)
        trial_results: List[JsonDict] = []
        with _guard_provider_transport(policy) as transport:
            for trial_index in range(1, trials + 1):
                before = _live_environment()
                before_policy = _transport_policy()
                if before != config or before_policy != policy:
                    raise SameModelContractError(
                        "LIVE environment changed before trial"
                    )
                with _capture_provider_calls() as calls:
                    comparison = self.run_comparison(mode="live")
                after = _live_environment()
                after_policy = _transport_policy()
                if after != config or after_policy != policy:
                    raise SameModelContractError(
                        "LIVE environment changed during trial"
                    )
                returned_models = sorted(
                    {str(call["returned_model"]) for call in calls}
                )
                requested_models = sorted(
                    {str(call["requested_model"]) for call in calls}
                )
                if requested_models != [config["model"]]:
                    raise SameModelContractError(
                        "more than one requested model was observed"
                    )
                if len(returned_models) != 1:
                    raise SameModelContractError(
                        "provider returned multiple model identities"
                    )
                comparison["trial_index"] = trial_index
                comparison["provider_ledger"] = {
                    "requested_models": requested_models,
                    "returned_models": returned_models,
                    "same_model_enforced": True,
                    "usage": _provider_totals(calls),
                    "calls": calls,
                }
                trial_results.append(comparison)

        baseline_rates = [
            float(item["baseline"]["metrics"]["coverage_adjusted_verified_recovery_rate"])
            for item in trial_results
        ]
        final_rates = [
            float(item["final"]["metrics"]["coverage_adjusted_verified_recovery_rate"])
            for item in trial_results
        ]
        return {
            "artifact_schema": "same-model-live-runtime-v1",
            "benchmark_id": self.benchmark_id,
            "created_at": utc_now(),
            "mode": "live",
            "trial_count": trials,
            "contract": public_contract,
            "transport": transport,
            "aggregate": {
                "baseline_cavrr_mean": _mean(baseline_rates),
                "baseline_cavrr_stdev": _stdev(baseline_rates),
                "final_cavrr_mean": _mean(final_rates),
                "final_cavrr_stdev": _stdev(final_rates),
                "mean_absolute_improvement": round(
                    _mean(final_rates) - _mean(baseline_rates), 6
                ),
            },
            "trials": trial_results,
        }

    def run_ablations(self, mode: str = "frozen") -> JsonDict:
        if mode not in {"frozen", "live"}:
            raise ValueError("mode must be frozen or live")
        if mode == "frozen":
            return self._run_ablations(mode)

        config = _live_environment()
        policy = _transport_policy()
        with _guard_provider_transport(policy) as transport:
            with _capture_provider_calls() as calls:
                payload = self._run_ablations(mode)
        if _live_environment() != config or _transport_policy() != policy:
            raise SameModelContractError("LIVE environment changed during ablation")
        returned_models = sorted({str(call["returned_model"]) for call in calls})
        requested_models = sorted({str(call["requested_model"]) for call in calls})
        if requested_models != [config["model"]]:
            raise SameModelContractError(
                "more than one requested model was observed during ablation"
            )
        if len(returned_models) != 1:
            raise SameModelContractError(
                "provider returned multiple model identities during ablation"
            )
        payload["live_contract"] = _public_live_contract(config, policy)
        payload["provider_ledger"] = {
            "requested_models": requested_models,
            "returned_models": returned_models,
            "same_model_enforced": True,
            "usage": _provider_totals(calls),
            "calls": calls,
        }
        payload["transport"] = transport
        return payload

    def _run_ablations(self, mode: str) -> JsonDict:
        direct = self.runner.run_baseline(mode=mode, split="held_out")
        preflight_only = self._run_preflight_only(mode)
        full = self.runner.run_final(mode=mode, split="held_out")
        _assert_case_parity(direct, full)

        task_completion_cases = []
        for item in full["results"]:
            task_check = next(
                check
                for check in item["replay"]["invariants"]
                if check["invariant_id"] == "task.fulfilled"
            )
            task_completion_cases.append(
                {
                    "case_id": item["case_id"],
                    "task_completion_without_full_verifier": bool(task_check["passed"]),
                    "full_verifier_accepts": bool(item["verified_safe_recovery"]),
                    "failed_invariants": list(item["replay"]["failed_invariants"]),
                }
            )
        raw_task_count = sum(
            bool(item["task_completion_without_full_verifier"])
            for item in task_completion_cases
        )
        verified_count = int(full["metrics"]["verified_safe_recoveries"])
        governed_cases = [
            {
                "case_id": item["case_id"],
                "candidate_requires_approval": bool(
                    item["adaptation_trajectory"]["output"]["requires_approval"]
                ),
                "replay_was_approved": item["intervention"]["approval_state"] == "approved",
                "activation_eligible": bool(
                    item["learning_candidate"]["eligible_for_activation"]
                ),
                "verified_safe_recovery": bool(item["verified_safe_recovery"]),
            }
            for item in full["results"]
        ]
        governance_consistent = all(
            item["candidate_requires_approval"]
            and item["replay_was_approved"]
            and item["activation_eligible"] == item["verified_safe_recovery"]
            for item in governed_cases
        )
        return {
            "artifact_schema": "external-ablation-runtime-v1",
            "benchmark_id": self.benchmark_id,
            "created_at": utc_now(),
            "mode": mode,
            "case_count": len(full["results"]),
            "variants": {
                "direct_raw_trace": direct,
                "invariant_preflight_without_typed_repair": preflight_only,
                "structured_repair_without_full_verifier": {
                    "interpretation": "unsafe upper bound; counts task completion even when another invariant remains failed",
                    "task_completions": raw_task_count,
                    "rate": round(raw_task_count / max(1, len(task_completion_cases)), 4),
                    "cases": task_completion_cases,
                },
                "full_verified_repair": full,
                "full_verified_and_governed": {
                    "verified_safe_recoveries": verified_count,
                    "activation_eligible": sum(
                        bool(item["activation_eligible"]) for item in governed_cases
                    ),
                    "governance_consistent": governance_consistent,
                    "cases": governed_cases,
                },
            },
            "ablation_contract": {
                "same_cases": True,
                "same_initial_state": True,
                "same_replay_engine": True,
                "same_verifier_for_verified_variants": True,
                "unsafe_upper_bound_explicitly_not_a_product_metric": True,
            },
        }

    def _run_preflight_only(self, mode: str) -> JsonDict:
        results: List[JsonDict] = []
        for case in self.runner._cases("held_out"):
            original_sim = self.runner.workload.run(case)
            original = self.runner.verifier.verify(case, original_sim)
            candidate = validate_intervention(
                {
                    "intervention_id": "abl_preflight_%s" % case["case_id"],
                    "operation": "prompt_rule.add",
                    "target_id": "planner.be_careful",
                    "before_hash": content_hash(None),
                    "after_value": "review the trace before acting",
                    "evidence_refs": [case["trajectory"][-1]["step_id"]],
                    "rationale": "Ablation exposes invariants but withholds structured diagnosis and typed repair.",
                    "expected_metric_effect": {"verified_recovery": "+unknown"},
                    "risks": ["preflight alone does not alter the causal configuration"],
                    "requires_approval": True,
                    "approval_state": "candidate",
                    "verification_conditions": ["all deterministic invariants pass"],
                }
            )
            approved = transition_intervention(
                candidate,
                "approved",
                reviewer_id="external-ablation-reviewer",
                note="Simulated approval for fixed ablation parity.",
                simulated=True,
            )
            replay_sim = self.runner.workload.run(case, approved)
            replay = add_safety_regression(
                original, self.runner.verifier.verify(case, replay_sim)
            )
            results.append(
                {
                    "case_id": case["case_id"],
                    "eligible": bool(case.get("eligible", True)),
                    "original": {**original, "simulation": original_sim.to_dict()},
                    "intervention": approved,
                    "replay": {**replay, "simulation": replay_sim.to_dict()},
                    "verified_safe_recovery": is_verified_safe_recovery(original, replay),
                }
            )
        return self.runner._report("invariant_preflight_only", mode, results)
