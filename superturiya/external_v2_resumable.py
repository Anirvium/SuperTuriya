"""Quota-resilient, cases-only execution for the frozen External-v2 study.

This module is deliberately outside ``SUT_SOURCE_FILES``.  It changes only how
completed LIVE work is persisted: the frozen agents, prompts, model calls,
repair logic, replay engine, verifier, cases, and scoring code remain unchanged.
Private gold is never imported or opened here.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from .adaptive import (
    add_safety_regression,
    is_verified_safe_recovery,
    transition_intervention,
)
from .external_runtime import (
    ExternalRuntimeRunner,
    SameModelContractError,
    _assert_case_parity,
    _capture_provider_calls,
    _guard_provider_transport,
    _live_environment,
    _mean,
    _provider_totals,
    _public_live_contract,
    _stdev,
    _transient_failure_reason,
    _transport_policy,
)
from .external_v2 import (
    BENCHMARK_ID,
    DEFAULT_ROOT,
    ExternalV2Error,
    load_external_v2_cases,
    validate_runtime_case_freeze,
    validate_system_under_test,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
HARNESS_PATH = Path(__file__).resolve()
CHECKPOINT_SCHEMA = "superturiya-external-v2-resumable-checkpoint-v1"
JOURNAL_SCHEMA = "superturiya-external-v2-resumable-attempt-v1"
RAW_SCHEMA = "superturiya-external-v2-raw-predictions-v1"
RUNTIME_SCHEMA = "same-model-live-runtime-v1"
PHASES = ("baseline", "investigator", "adaptation")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExternalV2Error("invalid resumable artifact %s: %s" % (path, exc)) from exc
    if not isinstance(value, dict):
        raise ExternalV2Error("resumable artifact must be an object: %s" % path)
    return value


def _atomic_write_new(path: Path, payload: Mapping[str, Any]) -> None:
    """Create one immutable JSON artifact without exposing a partial file."""

    if path.exists():
        raise ExternalV2Error("refusing to overwrite resumable artifact: %s" % path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=".%s." % path.name, suffix=".tmp", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # A hard-link publish is atomic and fails instead of overwriting if a
        # second process raced this writer. Both paths are on the same volume.
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise ExternalV2Error(
                "concurrent resumable writer detected: %s" % path
            ) from exc
    finally:
        if temporary.exists():
            temporary.unlink()


def _checkpoint_path(
    checkpoint_root: Path, trial_index: int, phase: str, case_id: str
) -> Path:
    return checkpoint_root / ("trial-%02d" % trial_index) / phase / (case_id + ".json")


def _unit_sequence(case_ids: Iterable[str], trial_count: int) -> list[tuple[int, str, str]]:
    ids = list(case_ids)
    units = []
    for trial_index in range(1, trial_count + 1):
        units.extend((trial_index, "baseline", case_id) for case_id in ids)
        for case_id in ids:
            units.append((trial_index, "investigator", case_id))
            units.append((trial_index, "adaptation", case_id))
    return units


def _transport_delta(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict:
    numeric = (
        "request_attempts",
        "successful_calls",
        "retry_count",
        "paced_sleep_seconds",
        "retry_sleep_seconds",
    )
    before_events = list(before.get("retry_events") or [])
    after_events = list(after.get("retry_events") or [])
    return {
        "policy": copy.deepcopy(after.get("policy") or {}),
        **{
            key: round(float(after.get(key) or 0) - float(before.get(key) or 0), 6)
            if key.endswith("seconds")
            else int(after.get(key) or 0) - int(before.get(key) or 0)
            for key in numeric
        },
        "retry_events": copy.deepcopy(after_events[len(before_events) :]),
    }


def _sum_transport(items: Iterable[Mapping[str, Any]], policy: Mapping[str, Any]) -> dict:
    rows = list(items)
    return {
        "policy": dict(policy),
        "request_attempts": sum(int(row.get("request_attempts") or 0) for row in rows),
        "successful_calls": sum(int(row.get("successful_calls") or 0) for row in rows),
        "retry_count": sum(int(row.get("retry_count") or 0) for row in rows),
        "paced_sleep_seconds": round(
            sum(float(row.get("paced_sleep_seconds") or 0.0) for row in rows), 6
        ),
        "retry_sleep_seconds": round(
            sum(float(row.get("retry_sleep_seconds") or 0.0) for row in rows), 6
        ),
        "retry_events": [
            copy.deepcopy(event)
            for row in rows
            for event in list(row.get("retry_events") or [])
        ],
    }


def _identity(
    runtime_freeze: Mapping[str, Any],
    sut: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict:
    return {
        "benchmark_id": BENCHMARK_ID,
        "system_under_test_sha256": sut["system_under_test_sha256"],
        "cases_aggregate_sha256": runtime_freeze["cases_aggregate_sha256"],
        "case_ids": list(runtime_freeze["case_ids"]),
        "trial_count": int(sut["experiment_contract"]["trial_count"]),
        "live_contract": copy.deepcopy(dict(contract)),
        "harness_sha256": _sha256(HARNESS_PATH),
    }


def _validate_checkpoint(
    path: Path,
    expected_identity: Mapping[str, Any],
    trial_index: int,
    phase: str,
    case_id: str,
) -> dict:
    payload = _read_json(path)
    if payload.get("artifact_schema") != CHECKPOINT_SCHEMA:
        raise ExternalV2Error("unknown resumable checkpoint schema: %s" % path)
    if payload.get("identity") != expected_identity:
        raise ExternalV2Error(
            "checkpoint contract differs from the current frozen execution: %s" % path
        )
    if payload.get("trial_index") != trial_index:
        raise ExternalV2Error("checkpoint trial index mismatch: %s" % path)
    if payload.get("phase") != phase or payload.get("case_id") != case_id:
        raise ExternalV2Error("checkpoint phase/case mismatch: %s" % path)
    result = payload.get("result")
    if not isinstance(result, dict) or result.get("case_id") != case_id:
        raise ExternalV2Error("checkpoint result does not match case: %s" % path)
    ledger = payload.get("provider_ledger")
    if not isinstance(ledger, dict):
        raise ExternalV2Error("checkpoint provider ledger is missing: %s" % path)
    calls = ledger.get("calls")
    if not isinstance(calls, list) or len(calls) != 1:
        raise ExternalV2Error(
            "checkpoint must contain exactly one frozen model call: %s" % path
        )
    requested = sorted({str(call.get("requested_model")) for call in calls})
    returned = sorted({str(call.get("returned_model")) for call in calls})
    if requested != [expected_identity["live_contract"]["requested_model"]]:
        raise ExternalV2Error("checkpoint requested-model identity mismatch: %s" % path)
    if len(returned) != 1 or not ledger.get("same_model_enforced"):
        raise ExternalV2Error("checkpoint provider-model identity is not singular: %s" % path)
    if ledger.get("usage") != _provider_totals(calls):
        raise ExternalV2Error("checkpoint usage totals do not match its call ledger: %s" % path)
    sealed = {
        key: copy.deepcopy(value)
        for key, value in payload.items()
        if key not in {"checkpoint_sha256"}
    }
    if payload.get("checkpoint_sha256") != _canonical_hash(sealed):
        raise ExternalV2Error("checkpoint canonical hash mismatch: %s" % path)
    return payload


def _checkpoint_payload(
    identity: Mapping[str, Any],
    trial_index: int,
    phase: str,
    case_id: str,
    result: Mapping[str, Any],
    calls: list[dict],
    transport: Mapping[str, Any],
) -> dict:
    requested = sorted({str(call["requested_model"]) for call in calls})
    returned = sorted({str(call["returned_model"]) for call in calls})
    if requested != [identity["live_contract"]["requested_model"]]:
        raise SameModelContractError("resumable unit observed another requested model")
    if len(returned) != 1:
        raise SameModelContractError("resumable unit observed multiple returned models")
    sealed = {
        "artifact_schema": CHECKPOINT_SCHEMA,
        "created_at": _utc_now(),
        "identity": copy.deepcopy(dict(identity)),
        "trial_index": trial_index,
        "phase": phase,
        "case_id": case_id,
        "result": copy.deepcopy(dict(result)),
        "provider_ledger": {
            "requested_models": requested,
            "returned_models": returned,
            "same_model_enforced": True,
            "usage": _provider_totals(calls),
            "calls": copy.deepcopy(calls),
        },
        "transport": copy.deepcopy(dict(transport)),
        "private_labels_loaded": False,
    }
    return {**sealed, "checkpoint_sha256": _canonical_hash(sealed)}


def _write_failed_attempt(
    checkpoint_root: Path,
    identity: Mapping[str, Any],
    trial_index: int,
    phase: str,
    case_id: str,
    calls: list[dict],
    transport: Mapping[str, Any],
    exc: BaseException,
) -> Path:
    path = checkpoint_root / "attempts" / (
        "%s_trial-%02d_%s_%s.json" % (
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
            trial_index,
            phase,
            case_id,
        )
    )
    payload = {
        "artifact_schema": JOURNAL_SCHEMA,
        "created_at": _utc_now(),
        "identity": copy.deepcopy(dict(identity)),
        "trial_index": trial_index,
        "phase": phase,
        "case_id": case_id,
        "status": "aborted_before_checkpoint",
        "error_type": type(exc).__name__,
        "error": str(exc)[:2000],
        "successful_orphaned_calls": len(calls),
        "provider_ledger": {
            "usage": _provider_totals(calls),
            "calls": copy.deepcopy(calls),
        },
        "transport": copy.deepcopy(dict(transport)),
        "credential_recorded": False,
        "private_labels_loaded": False,
    }
    _atomic_write_new(path, payload)
    return path


def _load_all_checkpoints(
    checkpoint_root: Path,
    identity: Mapping[str, Any],
) -> dict[tuple[int, str, str], dict]:
    loaded: dict[tuple[int, str, str], dict] = {}
    for trial_index, phase, case_id in _unit_sequence(
        identity["case_ids"], int(identity["trial_count"])
    ):
        path = _checkpoint_path(checkpoint_root, trial_index, phase, case_id)
        if path.exists():
            loaded[(trial_index, phase, case_id)] = _validate_checkpoint(
                path, identity, trial_index, phase, case_id
            )
    expected_paths = {
        _checkpoint_path(checkpoint_root, trial_index, phase, case_id).resolve()
        for trial_index, phase, case_id in _unit_sequence(
            identity["case_ids"], int(identity["trial_count"])
        )
    }
    unexpected = sorted(
        str(path)
        for path in checkpoint_root.glob("trial-*/*/*.json")
        if path.resolve() not in expected_paths
    )
    if unexpected:
        raise ExternalV2Error(
            "unexpected resumable checkpoint files: %s" % ", ".join(unexpected)
        )
    return loaded


def _assemble_runtime(
    runner: ExternalRuntimeRunner,
    checkpoints: Mapping[tuple[int, str, str], Mapping[str, Any]],
    identity: Mapping[str, Any],
    checkpoint_root: Path,
) -> dict:
    case_ids = list(identity["case_ids"])
    trial_results = []
    all_transports = []
    for trial_index in range(1, int(identity["trial_count"]) + 1):
        baseline_results = [
            checkpoints[(trial_index, "baseline", case_id)]["result"]
            for case_id in case_ids
        ]
        final_results = [
            checkpoints[(trial_index, "adaptation", case_id)]["result"]
            for case_id in case_ids
        ]
        baseline = runner.runner._report("baseline", "live", baseline_results)
        final = runner.runner._report("final", "live", final_results)
        _assert_case_parity(baseline, final)
        calls = [
            copy.deepcopy(call)
            for unit_trial, phase, case_id in _unit_sequence(case_ids, 1)
            for call in checkpoints[(trial_index, phase, case_id)]["provider_ledger"]["calls"]
        ]
        requested = sorted({str(call["requested_model"]) for call in calls})
        returned = sorted({str(call["returned_model"]) for call in calls})
        if requested != [identity["live_contract"]["requested_model"]] or len(returned) != 1:
            raise SameModelContractError("assembled trial does not have one model identity")
        comparison = {
            "artifact_schema": "external-runtime-comparison-v1",
            "benchmark_id": BENCHMARK_ID,
            "created_at": _utc_now(),
            "mode": "live",
            "case_count": len(case_ids),
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
            "trial_index": trial_index,
            "provider_ledger": {
                "requested_models": requested,
                "returned_models": returned,
                "same_model_enforced": True,
                "usage": _provider_totals(calls),
                "calls": calls,
            },
        }
        trial_results.append(comparison)
        all_transports.extend(
            checkpoints[(trial_index, phase, case_id)]["transport"]
            for _unit_trial, phase, case_id in _unit_sequence(case_ids, 1)
        )

    baseline_rates = [
        float(item["baseline"]["metrics"]["coverage_adjusted_verified_recovery_rate"])
        for item in trial_results
    ]
    final_rates = [
        float(item["final"]["metrics"]["coverage_adjusted_verified_recovery_rate"])
        for item in trial_results
    ]
    attempt_files = sorted((checkpoint_root / "attempts").glob("*.json"))
    attempt_rows = [_read_json(path) for path in attempt_files]
    return {
        "artifact_schema": RUNTIME_SCHEMA,
        "benchmark_id": BENCHMARK_ID,
        "created_at": _utc_now(),
        "mode": "live",
        "trial_count": int(identity["trial_count"]),
        "contract": copy.deepcopy(identity["live_contract"]),
        "transport": _sum_transport(
            all_transports, identity["live_contract"]["transport_policy"]
        ),
        "aggregate": {
            "baseline_cavrr_mean": _mean(baseline_rates),
            "baseline_cavrr_stdev": _stdev(baseline_rates),
            "final_cavrr_mean": _mean(final_rates),
            "final_cavrr_stdev": _stdev(final_rates),
            "mean_absolute_improvement": round(
                _mean(final_rates) - _mean(baseline_rates), 6
            ),
        },
        "resumption": {
            "protocol": "case_atomic_checkpointing_v1",
            "checkpoint_count": len(checkpoints),
            "expected_checkpoint_count": len(case_ids) * len(PHASES) * int(identity["trial_count"]),
            "aborted_attempt_count": len(attempt_rows),
            "orphaned_successful_provider_calls": sum(
                int(item.get("successful_orphaned_calls") or 0) for item in attempt_rows
            ),
            "harness_sha256": identity["harness_sha256"],
            "private_labels_loaded": False,
        },
        "trials": trial_results,
    }


def _raw_payload(
    runtime: Mapping[str, Any],
    runtime_freeze: Mapping[str, Any],
    sut: Mapping[str, Any],
) -> dict:
    return {
        "artifact_schema": RAW_SCHEMA,
        "benchmark_id": BENCHMARK_ID,
        "created_at": _utc_now(),
        "mode": "live",
        "experiment": "comparison",
        "claim_eligible": True,
        "system_under_test_sha256": sut["system_under_test_sha256"],
        "cases_aggregate_sha256": runtime_freeze["cases_aggregate_sha256"],
        "case_ids": list(runtime_freeze["case_ids"]),
        "private_labels_loaded": False,
        "execution_protocol": {
            "name": "external-v2-case-atomic-resume-v1",
            "changes_system_under_test": False,
            "changes_model_prompts_or_verifier": False,
            "harness_sha256": _sha256(HARNESS_PATH),
        },
        "runtime": copy.deepcopy(dict(runtime)),
    }


def run_resumable_predictions(
    root: Path,
    output: Path,
    checkpoint_root: Path,
    max_units: Optional[int] = None,
) -> dict:
    """Execute unfinished cases, checkpoint atomically, then assemble raw evidence."""

    root = Path(root)
    output = Path(output)
    checkpoint_root = Path(checkpoint_root)
    if max_units is not None and max_units < 0:
        raise ExternalV2Error("max_units cannot be negative")
    if output.exists():
        return {
            "status": "complete",
            "output": str(output),
            "sha256": _sha256(output),
            "provider_calls_executed": 0,
            "private_labels_loaded": False,
        }

    runtime_freeze = validate_runtime_case_freeze(root)
    sut = validate_system_under_test(root)
    experiment = sut["experiment_contract"]
    if experiment.get("mode") != "live" or int(experiment.get("trial_count") or 0) < 3:
        raise ExternalV2Error("resumable execution requires the frozen LIVE comparison contract")
    config = _live_environment()
    policy = _transport_policy()
    if config["model"] != experiment["model"]:
        raise ExternalV2Error("LIVE model differs from the frozen SUT contract")
    public_contract = _public_live_contract(config, policy)
    identity = _identity(runtime_freeze, sut, public_contract)
    checkpoints = _load_all_checkpoints(checkpoint_root, identity)
    cases = load_external_v2_cases(root)
    case_lookup = {case["case_id"]: case for case in cases}

    with tempfile.TemporaryDirectory() as directory:
        runtime_root = Path(directory)
        (runtime_root / "cases.json").write_text(
            json.dumps({"benchmark_id": BENCHMARK_ID, "cases": cases}, sort_keys=True),
            encoding="utf-8",
        )
        runner = ExternalRuntimeRunner(runtime_root, benchmark_id=BENCHMARK_ID)
        completed_now = 0
        provider_calls_now = 0
        with _guard_provider_transport(policy) as transport:
            for trial_index, phase, case_id in _unit_sequence(
                identity["case_ids"], int(identity["trial_count"])
            ):
                key = (trial_index, phase, case_id)
                if key in checkpoints:
                    continue
                if max_units is not None and completed_now >= max_units:
                    break
                if _live_environment() != config or _transport_policy() != policy:
                    raise SameModelContractError("LIVE environment changed before resumable unit")
                runner.runner.cases = [case_lookup[case_id]]
                before = copy.deepcopy(transport)
                calls: list[dict] = []
                try:
                    with _capture_provider_calls() as calls:
                        if phase == "baseline":
                            result = runner.runner.run_baseline(
                                "live", "held_out"
                            )["results"][0]
                        elif phase == "investigator":
                            case = case_lookup[case_id]
                            original_sim = runner.runner.workload.run(case)
                            original = runner.runner.verifier.verify(case, original_sim)
                            investigation = runner.runner.investigator.investigate(
                                case, original, "live"
                            )
                            result = {
                                "case_id": case_id,
                                "original": {
                                    **original,
                                    "simulation": original_sim.to_dict(),
                                },
                                "investigator_trajectory": investigation,
                            }
                        else:
                            case = case_lookup[case_id]
                            investigation_checkpoint = checkpoints.get(
                                (trial_index, "investigator", case_id)
                            )
                            if investigation_checkpoint is None:
                                raise ExternalV2Error(
                                    "adaptation cannot run before its investigator checkpoint"
                                )
                            investigation_result = investigation_checkpoint["result"]
                            original = investigation_result["original"]
                            investigation = investigation_result[
                                "investigator_trajectory"
                            ]
                            adaptation = runner.runner.adaptation.propose(
                                case, investigation["output"], "live"
                            )
                            approved = transition_intervention(
                                adaptation["output"],
                                "approved",
                                reviewer_id="benchmark-reviewer",
                                note=(
                                    "Explicit simulated approval for deterministic "
                                    "held-out replay."
                                ),
                                simulated=True,
                            )
                            replay_sim = runner.runner.workload.run(case, approved)
                            replay = add_safety_regression(
                                original,
                                runner.runner.verifier.verify(case, replay_sim),
                            )
                            verified = is_verified_safe_recovery(original, replay)
                            result = {
                                "case_id": case_id,
                                "eligible": bool(case.get("eligible", True)),
                                "difficult": bool(case.get("difficult", False)),
                                "original": original,
                                "investigator_trajectory": investigation,
                                "adaptation_trajectory": adaptation,
                                "intervention": approved,
                                "replay": {
                                    **replay,
                                    "simulation": replay_sim.to_dict(),
                                },
                                "verified_safe_recovery": verified,
                                "learning_candidate": {
                                    "status": "candidate",
                                    "eligible_for_activation": verified,
                                    "source_intervention_id": approved[
                                        "intervention_id"
                                    ],
                                    "body": (
                                        "Reuse verified %s repair for matching "
                                        "invariant failures." % approved["operation"]
                                    ),
                                    "activation_note": (
                                        "Requires a separate explicit activation review."
                                        if verified
                                        else (
                                            "Rejected from promotion because replay did "
                                            "not pass all gates."
                                        )
                                    ),
                                },
                            }
                except Exception as exc:
                    delta = _transport_delta(before, transport)
                    attempt_path = _write_failed_attempt(
                        checkpoint_root,
                        identity,
                        trial_index,
                        phase,
                        case_id,
                        calls,
                        delta,
                        exc,
                    )
                    if isinstance(exc, RuntimeError) and _transient_failure_reason(exc):
                        raise ResumableExecutionPaused(
                            trial_index, phase, case_id, attempt_path, exc
                        ) from exc
                    raise ResumableExecutionFailed(
                        trial_index, phase, case_id, attempt_path, exc
                    ) from exc
                if _live_environment() != config or _transport_policy() != policy:
                    raise SameModelContractError("LIVE environment changed during resumable unit")
                delta = _transport_delta(before, transport)
                provider_calls_now += len(calls)
                payload = _checkpoint_payload(
                    identity,
                    trial_index,
                    phase,
                    case_id,
                    result,
                    calls,
                    delta,
                )
                path = _checkpoint_path(checkpoint_root, trial_index, phase, case_id)
                _atomic_write_new(path, payload)
                checkpoints[key] = _validate_checkpoint(
                    path, identity, trial_index, phase, case_id
                )
                completed_now += 1

        expected_count = len(identity["case_ids"]) * len(PHASES) * int(
            identity["trial_count"]
        )
        if len(checkpoints) != expected_count:
            return {
                "status": "checkpointed",
                "completed_now": completed_now,
                "completed_total": len(checkpoints),
                "remaining": expected_count - len(checkpoints),
                "provider_calls_executed": provider_calls_now,
                "checkpoint_root": str(checkpoint_root),
                "output_created": False,
                "private_labels_loaded": False,
            }

        runner.runner.cases = cases
        runtime = _assemble_runtime(runner, checkpoints, identity, checkpoint_root)
        # Recheck both public freezes immediately before immutable final persistence.
        final_runtime_freeze = validate_runtime_case_freeze(root)
        final_sut = validate_system_under_test(root)
        if final_runtime_freeze != runtime_freeze or final_sut != sut:
            raise ExternalV2Error("frozen benchmark or SUT changed during resumable execution")
        raw = _raw_payload(runtime, runtime_freeze, sut)
        _atomic_write_new(output, raw)
        return {
            "status": "raw_predictions_persisted",
            "output": str(output),
            "sha256": _sha256(output),
            "checkpoint_count": len(checkpoints),
            "completed_now": completed_now,
            "provider_calls_executed": provider_calls_now,
            "case_count": len(cases),
            "trial_count": int(identity["trial_count"]),
            "private_labels_loaded": False,
        }


class ResumableExecutionPaused(RuntimeError):
    def __init__(
        self,
        trial_index: int,
        phase: str,
        case_id: str,
        attempt_path: Path,
        cause: BaseException,
    ) -> None:
        self.trial_index = trial_index
        self.phase = phase
        self.case_id = case_id
        self.attempt_path = attempt_path
        self.cause = cause
        super().__init__(
            "execution paused at trial %d %s %s: %s"
            % (trial_index, phase, case_id, cause)
        )


class ResumableExecutionFailed(RuntimeError):
    def __init__(
        self,
        trial_index: int,
        phase: str,
        case_id: str,
        attempt_path: Path,
        cause: BaseException,
    ) -> None:
        self.trial_index = trial_index
        self.phase = phase
        self.case_id = case_id
        self.attempt_path = attempt_path
        self.cause = cause
        super().__init__(
            "execution failed at trial %d %s %s: %s"
            % (trial_index, phase, case_id, cause)
        )


def checkpoint_status(root: Path, output: Path, checkpoint_root: Path) -> dict:
    root = Path(root)
    output = Path(output)
    checkpoint_root = Path(checkpoint_root)
    runtime_freeze = validate_runtime_case_freeze(root)
    sut = validate_system_under_test(root)
    expected = (
        len(runtime_freeze["case_ids"])
        * len(PHASES)
        * int(sut["experiment_contract"]["trial_count"])
    )
    checkpoints = list(checkpoint_root.glob("trial-*/*/*.json"))
    attempts = list((checkpoint_root / "attempts").glob("*.json"))
    return {
        "status": "complete" if output.exists() else "incomplete",
        "completed_checkpoints": len(checkpoints),
        "expected_checkpoints": expected,
        "remaining_checkpoints": max(0, expected - len(checkpoints)),
        "aborted_attempts": len(attempts),
        "output": str(output),
        "output_exists": output.exists(),
        "output_sha256": _sha256(output) if output.exists() else None,
        "system_under_test_sha256": sut["system_under_test_sha256"],
        "cases_aggregate_sha256": runtime_freeze["cases_aggregate_sha256"],
        "private_labels_loaded": False,
    }


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Resume the frozen External-v2 LIVE comparison from atomic case checkpoints."
    )
    parser.add_argument("command", choices=("run", "status"), nargs="?", default="run")
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "evidence" / "external_validity" / "v2" / "raw_live_comparison.json"),
    )
    parser.add_argument("--checkpoint-dir")
    parser.add_argument("--max-units", type=int)
    args = parser.parse_args(argv)
    output = Path(args.output)
    checkpoint_root = Path(
        args.checkpoint_dir
        or output.parent / (output.stem + "_checkpoints")
    )
    if args.command == "status":
        payload = checkpoint_status(Path(args.root), output, checkpoint_root)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    try:
        payload = run_resumable_predictions(
            Path(args.root), output, checkpoint_root, max_units=args.max_units
        )
    except ResumableExecutionPaused as exc:
        payload = {
            "status": "paused_safe_to_resume",
            "trial_index": exc.trial_index,
            "phase": exc.phase,
            "case_id": exc.case_id,
            "attempt_journal": str(exc.attempt_path),
            "reason": str(exc.cause),
            "next_command": "rerun the identical command after provider capacity returns",
            "private_labels_loaded": False,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        raise SystemExit(75)
    except ResumableExecutionFailed as exc:
        payload = {
            "status": "failed_requires_investigation",
            "trial_index": exc.trial_index,
            "phase": exc.phase,
            "case_id": exc.case_id,
            "attempt_journal": str(exc.attempt_path),
            "reason": str(exc.cause),
            "private_labels_loaded": False,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        raise SystemExit(1)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
