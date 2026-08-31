"""Pre-registered, separate-model fallback execution for External-v2.

The fallback preserves the frozen SUT source hash and benchmark. It overlays
only the model identity used by the execution contract, and delegates all
case-atomic work to the already-tested resumable harness. It must be reported
as a separate same-model comparison, never as completion of the primary model
contract.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Optional
from unittest import mock

from . import external_v2_resumable as resumable
from .external_runtime import ExternalRuntimeRunner, _live_environment
from .external_v2 import (
    DEFAULT_ROOT,
    ExternalV2Error,
    validate_runtime_case_freeze,
    validate_system_under_test,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTRACT = (
    PROJECT_ROOT
    / "evidence"
    / "external_validity"
    / "v2"
    / "qwen_fallback_contract.json"
)
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "evidence"
    / "external_validity"
    / "v2"
    / "raw_live_comparison_qwen_fallback.json"
)
CONTRACT_SCHEMA = "superturiya-external-v2-fallback-execution-contract-v1"
EXPECTED_MODEL = "qwen/qwen3.8-27b"


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExternalV2Error("cannot read fallback contract %s: %s" % (path, exc)) from exc
    if not isinstance(value, dict):
        raise ExternalV2Error("fallback contract must be a JSON object")
    return value


def validate_fallback_contract(
    path: Path = DEFAULT_CONTRACT,
    root: Path = DEFAULT_ROOT,
    require_live_environment: bool = False,
) -> dict:
    contract = _read_json(Path(path))
    if contract.get("artifact_schema") != CONTRACT_SCHEMA:
        raise ExternalV2Error("unknown fallback execution contract schema")
    recorded_hash = contract.get("contract_sha256")
    sealed = {key: copy.deepcopy(value) for key, value in contract.items() if key != "contract_sha256"}
    if recorded_hash != _canonical_hash(sealed):
        raise ExternalV2Error("fallback execution contract hash mismatch")
    if contract.get("execution_wrapper_sha256") != _sha256_file(Path(__file__)):
        raise ExternalV2Error("fallback execution wrapper differs from preregistration")
    if contract.get("resumable_harness_sha256") != _sha256_file(
        resumable.HARNESS_PATH
    ):
        raise ExternalV2Error("resumable harness differs from fallback preregistration")
    experiment = contract.get("experiment") or {}
    if experiment.get("model") != EXPECTED_MODEL:
        raise ExternalV2Error("fallback contract model is not the preregistered model")
    if experiment.get("mode") != "live" or experiment.get("temperature") != 0.0:
        raise ExternalV2Error("fallback contract must remain LIVE at temperature zero")
    if int(experiment.get("trial_count") or 0) != 3:
        raise ExternalV2Error("fallback contract must retain three trials")
    required_true = (
        "baseline_and_final_same_cases",
        "baseline_and_final_same_model",
        "baseline_and_final_same_replay_and_verifier",
    )
    if not all(experiment.get(field) is True for field in required_true):
        raise ExternalV2Error("fallback resource-parity contract is incomplete")
    if experiment.get("prompt_or_rule_tuning_after_freeze") is not False:
        raise ExternalV2Error("fallback contract permits post-freeze tuning")
    boundary = contract.get("claim_boundary") or {}
    if boundary.get("primary_frozen_gpt_experiment_replaced") is not False:
        raise ExternalV2Error("fallback must not replace the primary frozen experiment")
    if contract.get("private_labels_accessed_for_selection") is not False:
        raise ExternalV2Error("fallback selection cannot use private labels")
    if contract.get("provider_performance_observed_for_fallback_model") is not False:
        raise ExternalV2Error("fallback must be preregistered before observing its outputs")

    runtime_freeze = validate_runtime_case_freeze(Path(root))
    sut = validate_system_under_test(Path(root))
    if contract.get("system_under_test_sha256") != sut["system_under_test_sha256"]:
        raise ExternalV2Error("fallback contract references another frozen SUT")
    if contract.get("cases_aggregate_sha256") != runtime_freeze["cases_aggregate_sha256"]:
        raise ExternalV2Error("fallback contract references other visible cases")
    if require_live_environment:
        environment = _live_environment()
        if environment["model"] != experiment["model"]:
            raise ExternalV2Error("LIVE model differs from fallback execution contract")
        if _sha256_text(environment["endpoint"]) != contract.get("endpoint_sha256"):
            raise ExternalV2Error("LIVE endpoint differs from fallback execution contract")
    return contract


def _overlay_sut(base: Mapping[str, Any], contract: Mapping[str, Any]) -> dict:
    overlay = copy.deepcopy(dict(base))
    overlay["experiment_contract"]["model"] = contract["experiment"]["model"]
    overlay["experiment_contract"]["temperature"] = contract["experiment"]["temperature"]
    overlay["experiment_contract"]["trial_count"] = contract["experiment"]["trial_count"]
    return overlay


def _ensure_contract_sentinel(checkpoint_root: Path, contract: Mapping[str, Any]) -> Path:
    sentinel = checkpoint_root / "FALLBACK_EXECUTION_CONTRACT.json"
    if sentinel.exists():
        if _read_json(sentinel) != contract:
            raise ExternalV2Error("fallback checkpoint namespace has another contract")
    else:
        resumable._atomic_write_new(sentinel, contract)
    return sentinel


def run_fallback_predictions(
    root: Path,
    output: Path,
    checkpoint_root: Path,
    contract_path: Path = DEFAULT_CONTRACT,
    max_units: Optional[int] = None,
) -> dict:
    contract = validate_fallback_contract(
        Path(contract_path), Path(root), require_live_environment=True
    )
    base_sut = validate_system_under_test(Path(root))
    overlay = _overlay_sut(base_sut, contract)
    _ensure_contract_sentinel(Path(checkpoint_root), contract)

    def overlay_validator(_root: Path = DEFAULT_ROOT) -> dict:
        current = validate_system_under_test(Path(_root))
        if current != base_sut:
            raise ExternalV2Error("frozen SUT changed during fallback execution")
        return copy.deepcopy(overlay)

    with mock.patch.object(
        resumable, "validate_system_under_test", overlay_validator
    ):
        result = resumable.run_resumable_predictions(
            Path(root),
            Path(output),
            Path(checkpoint_root),
            max_units=max_units,
        )
    return {
        **result,
        "fallback_contract": str(contract_path),
        "fallback_contract_sha256": contract["contract_sha256"],
        "claim_boundary": "separate_same-model_fallback_experiment",
    }


def fallback_status(
    root: Path,
    output: Path,
    checkpoint_root: Path,
    contract_path: Path = DEFAULT_CONTRACT,
) -> dict:
    contract = validate_fallback_contract(Path(contract_path), Path(root))
    status = resumable.checkpoint_status(Path(root), Path(output), Path(checkpoint_root))
    return {
        **status,
        "fallback_contract": str(contract_path),
        "fallback_contract_sha256": contract["contract_sha256"],
        "model": contract["experiment"]["model"],
        "claim_boundary": "separate_same-model_fallback_experiment",
    }


def probe_fallback_provider(
    root: Path,
    contract_path: Path = DEFAULT_CONTRACT,
) -> dict:
    contract = validate_fallback_contract(
        Path(contract_path), Path(root), require_live_environment=True
    )
    probe = ExternalRuntimeRunner().probe_live_provider()
    returned = str(probe.get("returned_model") or "")
    if returned != contract["experiment"]["model"]:
        raise ExternalV2Error("fallback provider returned another model identity")
    return {
        "status": "ready",
        "fallback_contract_sha256": contract["contract_sha256"],
        "claim_boundary": "separate_same-model_fallback_experiment",
        "probe": probe,
        "private_labels_loaded": False,
    }


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run the preregistered External-v2 Qwen fallback experiment."
    )
    parser.add_argument("command", choices=("validate", "probe", "run", "status"))
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--checkpoint-dir")
    parser.add_argument("--max-units", type=int)
    args = parser.parse_args(argv)
    root = Path(args.root)
    contract_path = Path(args.contract)
    output = Path(args.output)
    checkpoint_root = Path(
        args.checkpoint_dir
        or output.parent / (output.stem + "_checkpoints")
    )
    if args.command == "validate":
        contract = validate_fallback_contract(contract_path, root)
        payload = {
            "status": "valid_preregistered_fallback",
            "contract": str(contract_path),
            "contract_sha256": contract["contract_sha256"],
            "model": contract["experiment"]["model"],
        }
    elif args.command == "probe":
        payload = probe_fallback_provider(root, contract_path)
    elif args.command == "status":
        payload = fallback_status(root, output, checkpoint_root, contract_path)
    else:
        try:
            payload = run_fallback_predictions(
                root,
                output,
                checkpoint_root,
                contract_path,
                max_units=args.max_units,
            )
        except resumable.ResumableExecutionPaused as exc:
            payload = {
                "status": "paused_safe_to_resume",
                "trial_index": exc.trial_index,
                "phase": exc.phase,
                "case_id": exc.case_id,
                "attempt_journal": str(exc.attempt_path),
                "reason": str(exc.cause),
                "private_labels_loaded": False,
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
            raise SystemExit(75)
        except resumable.ResumableExecutionFailed as exc:
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
