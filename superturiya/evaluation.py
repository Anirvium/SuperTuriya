from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Mapping, Optional

from .adaptive import (
    BENCHMARK_ROOT,
    FAILURE_CLASSES,
    AdaptiveEvaluationRunner,
    DeterministicVerifier,
    DeterministicWorkload,
    content_hash,
    load_cases,
)
from .models import JsonDict, new_id, utc_now


BENCHMARK_FREEZE_COMMIT = "bbe7fb9cc55d028796628ee4db0710767e4e70f6"
CASES_FILE_SHA256 = "053725a78acf10f4024b5cc068dc34801e75f3229c41b5e661b6c614e024146a"
LABELS_FILE_SHA256 = "19d83916218462eb04ba5af999caa52ea77cfd1cea2a1971ab15071a6996e076"


def _read_json(path: Path) -> JsonDict:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("expected JSON object: %s" % path)
    return data


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_gold_labels(root: Optional[Path] = None) -> Dict[str, JsonDict]:
    """Evaluator-only gold loader. Runtime agents and replay never import this module."""

    base = Path(root or BENCHMARK_ROOT)
    document = _read_json(base / "labels.json")
    return {str(key): dict(value) for key, value in document.get("labels", {}).items()}


def validate_benchmark(root: Optional[Path] = None) -> JsonDict:
    base = Path(root or BENCHMARK_ROOT)
    cases = load_cases(base)
    labels = load_gold_labels(base)
    errors: List[str] = []
    ids = [case.get("case_id") for case in cases]
    if len(ids) != len(set(ids)):
        errors.append("case IDs must be unique")
    development = [case for case in cases if case.get("split") == "development"]
    held_out = [case for case in cases if case.get("split") == "held_out"]
    if len(development) != 3:
        errors.append("expected 3 development cases, got %d" % len(development))
    if len(held_out) != 12:
        errors.append("expected 12 held-out cases, got %d" % len(held_out))
    if set(ids) != set(labels):
        errors.append("case and label IDs do not match")
    verifier = DeterministicVerifier()
    workload = DeterministicWorkload()
    class_counts = {name: 0 for name in FAILURE_CLASSES}
    required_case = {
        "case_id",
        "split",
        "goal",
        "initial_state",
        "tool_fixtures",
        "workflow_config",
        "trajectory",
        "expected_state",
    }
    required_label = {
        "gold_critical_steps",
        "gold_failure_class",
        "decisive_invariant",
        "expected_repair_surface",
        "acceptable_alternative_repairs",
    }
    for case in cases:
        missing_case = sorted(required_case - set(case))
        if missing_case:
            errors.append("%s missing %s" % (case.get("case_id", "unknown"), missing_case))
            continue
        if any(key.startswith("gold_") for key in case):
            errors.append("%s leaks gold labels" % case.get("case_id"))
        label = labels.get(str(case.get("case_id")), {})
        missing_label = sorted(required_label - set(label))
        if missing_label:
            errors.append("%s label missing %s" % (case.get("case_id"), missing_label))
        failure_class = label.get("gold_failure_class")
        if failure_class in class_counts and case.get("split") == "held_out":
            class_counts[failure_class] += 1
        initial_verdict = verifier.verify(case, workload.run(case))
        if initial_verdict["task_success"]:
            errors.append("%s is not initially failing" % case.get("case_id"))
    if set(class_counts.values()) != {2}:
        errors.append("held-out classes must have exactly two cases each: %s" % class_counts)

    cases_file_hash = _file_hash(base / "cases.json")
    labels_file_hash = _file_hash(base / "labels.json")
    if root is None:
        if cases_file_hash != CASES_FILE_SHA256:
            errors.append("cases.json differs from frozen byte hash")
        if labels_file_hash != LABELS_FILE_SHA256:
            errors.append("labels.json differs from frozen byte hash")
    if errors:
        raise ValueError("benchmark validation failed:\n- " + "\n- ".join(errors))
    return {
        "valid": True,
        "case_count": len(cases),
        "development_count": len(development),
        "held_out_count": len(held_out),
        "failure_class_counts": class_counts,
        "case_hash": content_hash(cases),
        "label_hash": content_hash(labels),
        "cases_file_sha256": cases_file_hash,
        "labels_file_sha256": labels_file_hash,
        "freeze_commit": BENCHMARK_FREEZE_COMMIT if root is None else None,
        "labels_exposed_to_agents": False,
        "gold_loader_module": "superturiya.evaluation",
        "runtime_module": "superturiya.adaptive",
    }


class EvaluationHarness:
    """Own hidden labels and score completed runtime outputs after execution."""

    def __init__(
        self,
        root: Optional[Path] = None,
        runtime: Optional[AdaptiveEvaluationRunner] = None,
    ) -> None:
        self.root = Path(root or BENCHMARK_ROOT)
        self.runtime = runtime or AdaptiveEvaluationRunner(self.root)
        self.labels = load_gold_labels(self.root)

    def run_baseline(self, mode: str = "frozen", split: str = "held_out") -> JsonDict:
        return self.runtime.run_baseline(mode, split)

    def run_final(self, mode: str = "frozen", split: str = "held_out") -> JsonDict:
        report = self.runtime.run_final(mode, split)
        eligible = [item for item in report["results"] if item.get("eligible")]
        for item in report["results"]:
            label = self.labels[item["case_id"]]
            diagnosis = item["investigator_trajectory"]["output"]
            item["localization_correct"] = (
                diagnosis["critical_step"] in label["gold_critical_steps"]
            )
            item["failure_class_correct"] = (
                diagnosis["failure_class"] == label["gold_failure_class"]
            )
        report["metrics"]["critical_step_localization_accuracy"] = round(
            sum(bool(item.get("localization_correct")) for item in eligible)
            / max(1, len(eligible)),
            4,
        )
        report["metrics"]["failure_class_accuracy"] = round(
            sum(bool(item.get("failure_class_correct")) for item in eligible)
            / max(1, len(eligible)),
            4,
        )
        report["evidence_hash"] = content_hash(report["results"])
        return report

    def compare(self, mode: str = "frozen") -> JsonDict:
        baseline = self.run_baseline(mode=mode, split="held_out")
        final = self.run_final(mode=mode, split="held_out")
        baseline_rate = baseline["metrics"]["coverage_adjusted_verified_recovery_rate"]
        final_rate = final["metrics"]["coverage_adjusted_verified_recovery_rate"]
        return {
            "evaluation_id": new_id("eval"),
            "created_at": utc_now(),
            "mode": mode,
            "benchmark": validate_benchmark(self.root if self.root != BENCHMARK_ROOT else None),
            "metric_contract": {
                "primary": "coverage_adjusted_verified_recovery_rate",
                "formula": "verified_safe_recoveries / all_eligible_initially_failing_held_out_cases",
                "frozen_before_evaluation": True,
            },
            "resource_parity": {
                "same_cases": True,
                "same_initial_state": True,
                "same_tool_fixtures": True,
                "same_replay_engine": True,
                "same_verifier": True,
                "same_approval_semantics": True,
                "baseline_input": "raw agent-visible trajectory",
                "superturiya_additional_resources": [
                    "deterministic invariant preflight",
                    "Investigator Agent structured diagnosis",
                    "Adaptation Agent typed repair",
                ],
                "live_model_provider_parity": "same environment-configured endpoint and model",
            },
            "baseline": baseline,
            "final": final,
            "improvement": {
                "absolute_vrr": round(final_rate - baseline_rate, 4),
                "relative_vrr": (
                    None
                    if baseline_rate == 0
                    else round((final_rate - baseline_rate) / baseline_rate, 4)
                ),
                "additional_verified_recoveries": final["metrics"][
                    "verified_safe_recoveries"
                ]
                - baseline["metrics"]["verified_safe_recoveries"],
            },
        }

    def case_matrix(self, report: Mapping[str, Any]) -> List[JsonDict]:
        baseline = {item["case_id"]: item for item in report["baseline"]["results"]}
        final = {item["case_id"]: item for item in report["final"]["results"]}
        matrix = []
        for case in self.runtime.cases:
            if case.get("split") != "held_out":
                continue
            case_id = case["case_id"]
            label = self.labels[case_id]
            matrix.append(
                {
                    "case_id": case_id,
                    "failure_class": label["gold_failure_class"],
                    "trajectory_length": len(case["trajectory"]),
                    "decisive_invariant": label["decisive_invariant"],
                    "expected_repair_surface": label["expected_repair_surface"],
                    "baseline_recovered": baseline[case_id]["verified_safe_recovery"],
                    "superturiya_recovered": final[case_id]["verified_safe_recovery"],
                    "verifier_result": (
                        "verified_safe_recovery"
                        if final[case_id]["verified_safe_recovery"]
                        else "rejected"
                    ),
                    "difficult": bool(case.get("difficult", False)),
                }
            )
        return matrix
