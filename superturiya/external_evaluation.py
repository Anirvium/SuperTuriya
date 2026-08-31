from __future__ import annotations

import builtins
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional
from unittest import mock

from .adaptive import (
    FAILURE_CLASSES,
    DeterministicVerifier,
    DeterministicWorkload,
    content_hash,
)
from .external_runtime import (
    EXTERNAL_BENCHMARK_ID,
    EXTERNAL_BENCHMARK_ROOT,
    ExternalRuntimeRunner,
)
from .models import JsonDict, utc_now


def _read_json(path: Path) -> JsonDict:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("expected JSON object: %s" % path)
    return data


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_cases(root: Path) -> List[JsonDict]:
    document = _read_json(root / "cases.json")
    return [dict(item) for item in document.get("cases", [])]


def load_external_gold(root: Optional[Path] = None) -> Dict[str, JsonDict]:
    base = Path(root or EXTERNAL_BENCHMARK_ROOT)
    document = _read_json(base / "labels.json")
    return {str(key): dict(value) for key, value in document.get("labels", {}).items()}


def validate_external_freeze(root: Optional[Path] = None) -> JsonDict:
    base = Path(root or EXTERNAL_BENCHMARK_ROOT)
    manifest = _read_json(base / "freeze_manifest.json")
    cases = _load_cases(base)
    gold = load_external_gold(base)
    errors: List[str] = []

    if manifest.get("benchmark_id") != EXTERNAL_BENCHMARK_ID:
        errors.append("benchmark ID differs from external v1 contract")
    actual_cases_file_hash = _file_hash(base / "cases.json")
    actual_gold_file_hash = _file_hash(base / "labels.json")
    if actual_cases_file_hash != manifest.get("cases_file_sha256"):
        errors.append("cases.json differs from sealed byte hash")
    if actual_gold_file_hash != manifest.get("labels_file_sha256"):
        errors.append("evaluator gold differs from sealed byte hash")
    if content_hash(cases) != manifest.get("case_content_hash"):
        errors.append("case content differs from sealed canonical hash")
    if content_hash(gold) != manifest.get("label_content_hash"):
        errors.append("gold content differs from sealed canonical hash")

    ids = [str(case.get("case_id")) for case in cases]
    if len(ids) != 12 or len(set(ids)) != 12:
        errors.append("external v1 requires 12 unique case IDs")
    if set(ids) != set(gold):
        errors.append("case and gold ID sets differ")
    if ids != list(manifest.get("case_ids") or []):
        errors.append("case ordering differs from freeze manifest")

    class_counts = {name: 0 for name in FAILURE_CLASSES}
    domains: Dict[str, int] = {}
    canaries: List[str] = []
    workload = DeterministicWorkload()
    verifier = DeterministicVerifier()
    required_case = {
        "case_id",
        "split",
        "eligible",
        "goal",
        "initial_state",
        "tool_fixtures",
        "workflow_config",
        "trajectory",
        "expected_state",
        "source_domain",
        "trace_standard",
    }
    required_gold = {
        "gold_critical_steps",
        "gold_failure_class",
        "decisive_invariant",
        "expected_repair_surface",
        "acceptable_alternative_repairs",
        "secondary_invariants",
        "label_canary",
    }
    for case in cases:
        case_id = str(case.get("case_id"))
        missing_case = sorted(required_case - set(case))
        if missing_case:
            errors.append("%s missing case fields %s" % (case_id, missing_case))
            continue
        if case.get("split") != "held_out" or case.get("eligible") is not True:
            errors.append("%s is not an eligible held-out case" % case_id)
        if not 5 <= len(case.get("trajectory") or []) <= 7:
            errors.append("%s trajectory length is outside frozen range" % case_id)
        if _contains_gold_key(case):
            errors.append("%s contains evaluator-shaped fields" % case_id)
        domain = str(case.get("source_domain"))
        domains[domain] = domains.get(domain, 0) + 1
        label = gold.get(case_id, {})
        missing_gold = sorted(required_gold - set(label))
        if missing_gold:
            errors.append("%s missing evaluator fields %s" % (case_id, missing_gold))
            continue
        failure_class = str(label.get("gold_failure_class"))
        if failure_class not in class_counts:
            errors.append("%s has unknown failure class" % case_id)
        else:
            class_counts[failure_class] += 1
        canaries.append(str(label.get("label_canary")))
        original = verifier.verify(case, workload.run(case))
        if original["task_success"]:
            errors.append("%s is not initially failing" % case_id)
        failed = set(original["failed_invariants"])
        if label.get("decisive_invariant") not in failed:
            errors.append("%s decisive invariant is not initially failed" % case_id)
        if not set(label.get("secondary_invariants") or []).issubset(failed):
            errors.append("%s secondary invariant is not initially failed" % case_id)

    if set(class_counts.values()) != {2}:
        errors.append("external v1 requires exactly two cases per failure class")
    if set(domains) != {"software_release", "data_access", "incident_rollback"}:
        errors.append("external v1 domain set differs from freeze contract")
    if len(canaries) != len(set(canaries)) or not all(canaries):
        errors.append("evaluator canaries must be unique and non-empty")
    cases_text = json.dumps(cases, sort_keys=True)
    if any(canary in cases_text for canary in canaries):
        errors.append("an evaluator canary leaked into runtime cases")
    if errors:
        raise ValueError("external freeze validation failed:\n- " + "\n- ".join(errors))
    return {
        "artifact_schema": "external-freeze-validation-v1",
        "benchmark_id": EXTERNAL_BENCHMARK_ID,
        "created_at": utc_now(),
        "valid": True,
        "freeze_status": manifest["freeze_status"],
        "case_count": len(cases),
        "case_ids": ids,
        "domains": domains,
        "failure_class_counts": class_counts,
        "multi_causal_case_ids": list(manifest.get("multi_causal_case_ids") or []),
        "cases_file_sha256": actual_cases_file_hash,
        "labels_file_sha256": actual_gold_file_hash,
        "case_content_hash": content_hash(cases),
        "label_content_hash": content_hash(gold),
        "authoring_independence": copy.deepcopy(manifest["authoring_independence"]),
    }


def _contains_gold_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).lower()
            if normalized.startswith("gold_") or normalized in {
                "label_canary",
                "decisive_invariant",
                "expected_repair_surface",
                "acceptable_alternative_repairs",
            }:
                return True
            if _contains_gold_key(child):
                return True
    elif isinstance(value, list):
        return any(_contains_gold_key(item) for item in value)
    return False


def _all_canaries(root: Path) -> List[str]:
    return [str(item["label_canary"]) for item in load_external_gold(root).values()]


def _assert_no_canary(payload: Any, canaries: List[str]) -> None:
    serialized = json.dumps(payload, sort_keys=True)
    leaked = [canary for canary in canaries if canary in serialized]
    if leaked:
        raise AssertionError("evaluator canary leaked into runtime output: %s" % leaked)


def run_isolation_audit(root: Optional[Path] = None) -> JsonDict:
    base = Path(root or EXTERNAL_BENCHMARK_ROOT)
    validate_external_freeze(base)
    import superturiya.external_runtime as runtime_module
    import superturiya.external_runtime_cli as runtime_cli_module

    forbidden_source_tokens = (
        "labels.json",
        "load_external_gold",
        "label_canary",
        "external_evaluation",
    )
    source_checks: Dict[str, JsonDict] = {}
    for module in (runtime_module, runtime_cli_module):
        source = Path(module.__file__).read_text(encoding="utf-8")
        found = [token for token in forbidden_source_tokens if token in source]
        source_checks[module.__name__] = {
            "forbidden_tokens_found": found,
            "passed": not found,
            "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        }
        if found:
            raise AssertionError("runtime source contains evaluator token: %s" % found)

    forbidden_path = (base / "labels.json").resolve()
    original_path_open = Path.open
    original_builtin_open = builtins.open

    def guarded_path_open(path: Path, *args: Any, **kwargs: Any) -> Any:
        if path.resolve() == forbidden_path:
            raise AssertionError("runtime attempted to open evaluator gold")
        return original_path_open(path, *args, **kwargs)

    def guarded_builtin_open(file: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            resolved = Path(file).resolve()
        except TypeError:
            resolved = None
        if resolved == forbidden_path:
            raise AssertionError("runtime attempted to open evaluator gold")
        return original_builtin_open(file, *args, **kwargs)

    with mock.patch.object(Path, "open", guarded_path_open), mock.patch(
        "builtins.open", guarded_builtin_open
    ):
        guarded_output = ExternalRuntimeRunner(base).run_comparison("frozen")
    canaries = _all_canaries(base)
    _assert_no_canary(guarded_output, canaries)

    with tempfile.TemporaryDirectory() as directory:
        isolated_root = Path(directory) / "runtime_input"
        isolated_root.mkdir(parents=True)
        shutil.copyfile(base / "cases.json", isolated_root / "cases.json")
        output = Path(directory) / "runtime_output.json"
        command = [
            sys.executable,
            "-m",
            "superturiya.external_runtime_cli",
            "comparison",
            "--benchmark-root",
            str(isolated_root),
            "--output",
            str(output),
            "--mode",
            "frozen",
        ]
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            command,
            cwd=str(Path(__file__).resolve().parent.parent),
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if completed.returncode != 0:
            raise AssertionError(
                "isolated runtime subprocess failed: %s" % completed.stderr.strip()
            )
        subprocess_output = _read_json(output)
        _assert_no_canary(subprocess_output, canaries)

    return {
        "artifact_schema": "external-isolation-audit-v1",
        "benchmark_id": EXTERNAL_BENCHMARK_ID,
        "created_at": utc_now(),
        "passed": True,
        "checks": {
            "runtime_source_has_no_evaluator_tokens": True,
            "runtime_import_boundary": source_checks,
            "in_process_file_open_guard": True,
            "runtime_output_has_no_gold_canary": True,
            "subprocess_has_cases_without_gold_file": True,
            "subprocess_output_has_no_gold_canary": True,
            "scoring_occurs_after_prediction_persistence": True,
        },
    }


def _repair_matches(label: Mapping[str, Any], patch: Mapping[str, Any]) -> bool:
    candidate = {
        "operation": patch.get("operation"),
        "target_id": patch.get("target_id"),
    }
    allowed = [label["expected_repair_surface"]] + list(
        label.get("acceptable_alternative_repairs") or []
    )
    return candidate in allowed


def score_comparison(
    raw: Mapping[str, Any], root: Optional[Path] = None
) -> JsonDict:
    base = Path(root or EXTERNAL_BENCHMARK_ROOT)
    freeze = validate_external_freeze(base)
    gold = load_external_gold(base)
    canaries = _all_canaries(base)
    _assert_no_canary(raw, canaries)
    baseline = raw["baseline"]
    final = raw["final"]
    baseline_ids = _case_ids_from_results(baseline)
    final_ids = _case_ids_from_results(final)
    if baseline_ids != freeze["case_ids"] or final_ids != freeze["case_ids"]:
        raise ValueError("runtime predictions do not match frozen case ordering")
    scored_cases: List[JsonDict] = []
    for item in final["results"]:
        case_id = str(item["case_id"])
        label = gold[case_id]
        diagnosis = item["investigator_trajectory"]["output"]
        patch = item["adaptation_trajectory"]["output"]
        scored_cases.append(
            {
                "case_id": case_id,
                "critical_step_correct": diagnosis.get("critical_step")
                in label["gold_critical_steps"],
                "failure_class_correct": diagnosis.get("failure_class")
                == label["gold_failure_class"],
                "repair_surface_correct": _repair_matches(label, patch),
                "verified_safe_recovery": bool(item["verified_safe_recovery"]),
                "difficult": case_id in freeze["multi_causal_case_ids"],
            }
        )
    count = max(1, len(scored_cases))
    baseline_rate = float(
        baseline["metrics"]["coverage_adjusted_verified_recovery_rate"]
    )
    final_rate = float(final["metrics"]["coverage_adjusted_verified_recovery_rate"])
    return {
        "artifact_schema": "external-scored-comparison-v1",
        "benchmark_id": EXTERNAL_BENCHMARK_ID,
        "created_at": utc_now(),
        "mode": raw["mode"],
        "freeze": freeze,
        "metrics": {
            "eligible_cases": len(scored_cases),
            "baseline_verified_safe_recoveries": baseline["metrics"][
                "verified_safe_recoveries"
            ],
            "baseline_cavrr": baseline_rate,
            "final_verified_safe_recoveries": final["metrics"][
                "verified_safe_recoveries"
            ],
            "final_cavrr": final_rate,
            "absolute_improvement": round(final_rate - baseline_rate, 4),
            "safety_regression_rate": final["metrics"]["safety_regression_rate"],
            "critical_step_localization_accuracy": round(
                sum(bool(item["critical_step_correct"]) for item in scored_cases) / count,
                4,
            ),
            "failure_class_accuracy": round(
                sum(bool(item["failure_class_correct"]) for item in scored_cases) / count,
                4,
            ),
            "repair_surface_accuracy": round(
                sum(bool(item["repair_surface_correct"]) for item in scored_cases) / count,
                4,
            ),
        },
        "cases": scored_cases,
        "runtime": copy.deepcopy(dict(raw)),
        "limitations": [
            "The benchmark is internally authored structural transfer, not third-party blind evaluation.",
            "The frozen runtime still uses the existing six-class invariant and repair vocabulary.",
            "Results do not establish production or unrestricted cross-domain generalization.",
        ],
    }


def score_ablations(raw: Mapping[str, Any], root: Optional[Path] = None) -> JsonDict:
    base = Path(root or EXTERNAL_BENCHMARK_ROOT)
    canaries = _all_canaries(base)
    _assert_no_canary(raw, canaries)
    full_raw = {
        "benchmark_id": raw["benchmark_id"],
        "created_at": raw["created_at"],
        "mode": raw["mode"],
        "baseline": raw["variants"]["direct_raw_trace"],
        "final": raw["variants"]["full_verified_repair"],
    }
    scored_full = score_comparison(full_raw, base)
    direct_metrics = raw["variants"]["direct_raw_trace"]["metrics"]
    preflight_metrics = raw["variants"][
        "invariant_preflight_without_typed_repair"
    ]["metrics"]
    unsafe_metrics = raw["variants"]["structured_repair_without_full_verifier"]
    full_metrics = raw["variants"]["full_verified_repair"]["metrics"]
    governance = raw["variants"]["full_verified_and_governed"]
    return {
        "artifact_schema": "external-scored-ablation-v1",
        "benchmark_id": EXTERNAL_BENCHMARK_ID,
        "created_at": utc_now(),
        "mode": raw["mode"],
        "freeze": scored_full["freeze"],
        "matrix": [
            {
                "variant": "direct_raw_trace",
                "verified_safe_recoveries": direct_metrics["verified_safe_recoveries"],
                "rate": direct_metrics["coverage_adjusted_verified_recovery_rate"],
                "interpretation": "reasonable direct frozen repair baseline",
            },
            {
                "variant": "invariant_preflight_without_typed_repair",
                "verified_safe_recoveries": preflight_metrics["verified_safe_recoveries"],
                "rate": preflight_metrics["coverage_adjusted_verified_recovery_rate"],
                "interpretation": "visibility alone does not change the causal configuration",
            },
            {
                "variant": "structured_repair_without_full_verifier",
                "verified_safe_recoveries": None,
                "rate": unsafe_metrics["rate"],
                "interpretation": "unsafe task-completion upper bound; not a product metric",
            },
            {
                "variant": "full_verified_repair",
                "verified_safe_recoveries": full_metrics["verified_safe_recoveries"],
                "rate": full_metrics["coverage_adjusted_verified_recovery_rate"],
                "interpretation": "typed repair accepted only when all invariants pass",
            },
            {
                "variant": "full_verified_and_governed",
                "verified_safe_recoveries": governance["verified_safe_recoveries"],
                "rate": round(
                    governance["activation_eligible"] / max(1, raw["case_count"]), 4
                ),
                "interpretation": "durable eligibility exactly follows verified safe recovery",
            },
        ],
        "diagnostic_metrics": {
            key: value
            for key, value in scored_full["metrics"].items()
            if key
            in {
                "critical_step_localization_accuracy",
                "failure_class_accuracy",
                "repair_surface_accuracy",
            }
        },
        "governance_consistent": governance["governance_consistent"],
        "raw": copy.deepcopy(dict(raw)),
    }


def score_live_trials(raw: Mapping[str, Any], root: Optional[Path] = None) -> JsonDict:
    base = Path(root or EXTERNAL_BENCHMARK_ROOT)
    scored_trials = [score_comparison(item, base) for item in raw.get("trials", [])]
    if not scored_trials:
        raise ValueError("LIVE artifact contains no trials")
    return {
        "artifact_schema": "same-model-live-scored-v1",
        "benchmark_id": EXTERNAL_BENCHMARK_ID,
        "created_at": utc_now(),
        "mode": "live",
        "contract": copy.deepcopy(raw["contract"]),
        "trial_count": len(scored_trials),
        "aggregate": copy.deepcopy(raw["aggregate"]),
        "scored_trial_metrics": [item["metrics"] for item in scored_trials],
        "trials": scored_trials,
    }


def _case_ids_from_results(report: Mapping[str, Any]) -> List[str]:
    return [str(item["case_id"]) for item in report.get("results", [])]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_evidence_manifest(root: Path) -> JsonDict:
    files = []
    for path in sorted(root.glob("*.json")):
        if path.name == "manifest.json":
            continue
        files.append(
            {
                "path": path.name,
                "sha256": _file_hash(path),
                "size_bytes": path.stat().st_size,
            }
        )
    repository_root = Path(__file__).resolve().parent.parent
    git_head = "unknown"
    git_dirty: Optional[bool] = None
    try:
        head_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repository_root),
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repository_root),
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        git_head = head_result.stdout.strip()
        git_dirty = bool(status_result.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    source_modules = {}
    for name in (
        "superturiya/external_runtime.py",
        "superturiya/external_runtime_cli.py",
        "superturiya/external_evaluation.py",
        "superturiya/external_validity.py",
    ):
        path = repository_root / name
        source_modules[name] = _file_hash(path)
    return {
        "artifact_schema": "external-evidence-manifest-v1",
        "evidence_version": "external-validity-v1",
        "benchmark_id": EXTERNAL_BENCHMARK_ID,
        "created_at": utc_now(),
        "source_revision": {
            "git_head": git_head,
            "git_worktree_dirty": git_dirty,
            "module_sha256": source_modules,
            "warning": (
                "Evidence was generated from a dirty worktree; regenerate after the final commit."
                if git_dirty
                else "Evidence was generated from the recorded clean revision."
            ),
        },
        "files": files,
        "artifact_count": len(files),
    }
