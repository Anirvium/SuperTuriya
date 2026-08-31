from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Optional

from .adaptive import AdaptiveEvaluationRunner, canonical_json
from .evaluation import EvaluationHarness, validate_benchmark
from .intelligence import SuperTuriyaEngine
from .store import SuperTuriyaStore
from .transfer import ShadowTransferEvaluator


DEFAULT_EVIDENCE_ROOT = Path(__file__).resolve().parent.parent / "evidence"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _print_summary(report: dict) -> None:
    if "baseline" in report and "final" in report:
        baseline = report["baseline"]["metrics"]
        final = report["final"]["metrics"]
        print("Baseline CAVRR: %.2f%% (%d/%d)" % (
            baseline["coverage_adjusted_verified_recovery_rate"] * 100,
            baseline["verified_safe_recoveries"],
            baseline["eligible_initial_failures"],
        ))
        print("Final CAVRR: %.2f%% (%d/%d)" % (
            final["coverage_adjusted_verified_recovery_rate"] * 100,
            final["verified_safe_recoveries"],
            final["eligible_initial_failures"],
        ))
        print("Absolute improvement: %.2f percentage points" % (
            report["improvement"]["absolute_vrr"] * 100
        ))
        print("Safety regression rate: %.2f%%" % (final["safety_regression_rate"] * 100))
        return
    print(canonical_json(report.get("metrics") or report))


def build_evidence_bundle(report: dict, root: Path) -> None:
    _write_json(root / "final_evaluation.json", report)
    _write_json(root / "baseline_evaluation.json", report["baseline"])
    _write_json(root / "superturiya_evaluation.json", report["final"])
    trajectories = root / "trajectories"
    for item in report["baseline"]["results"]:
        _write_json(
            trajectories / ("baseline_%s.json" % item["case_id"]),
            item["agent_trajectory"],
        )
    for item in report["final"]["results"]:
        _write_json(
            trajectories / ("investigator_%s.json" % item["case_id"]),
            item["investigator_trajectory"],
        )
        _write_json(
            trajectories / ("adaptation_%s.json" % item["case_id"]),
            item["adaptation_trajectory"],
        )
        _write_json(
            trajectories / ("replay_%s.json" % item["case_id"]),
            {
                "case_id": item["case_id"],
                "intervention": item["intervention"],
                "replay": item["replay"],
                "verified_safe_recovery": item["verified_safe_recovery"],
                "learning_candidate": item["learning_candidate"],
            },
        )
    matrix = EvaluationHarness().case_matrix(report)
    _write_json(root / "case_matrix.json", {"cases": matrix})
    _write_json(
        root / "engineering_evidence_report.json",
        {
            "evaluation_id": report["evaluation_id"],
            "created_at": report["created_at"],
            "positioning": "SuperTuriya turns failed agent trajectories into verified, governed procedural intelligence.",
            "demo_domain": {
                "name": "enterprise resource-request provisioning",
                "source": "curated synthetic deterministic fixtures",
                "production_generalization_claimed": False,
            },
            "benchmark_freeze": report["benchmark"],
            "resource_parity": report["resource_parity"],
            "aggregate_metrics": {
                "baseline": report["baseline"]["metrics"],
                "superturiya": report["final"]["metrics"],
                "improvement": report["improvement"],
            },
            "case_matrix": matrix,
            "replay_contract": {
                "initial_state_frozen": True,
                "task_frozen": True,
                "tool_fixtures_frozen": True,
                "policies_frozen_except_approved_intervention": True,
                "side_effects": "sandboxed",
                "different_valid_path_may_pass": True,
                "frozen_mode_reproduces_inference": False,
            },
            "governance": {
                "replay_path": "candidate -> human approval -> replay -> verifier",
                "activation_path": "verified candidate -> separate human activation -> active policy",
                "approval_overrides_verifier": False,
            },
            "test_command": "python3 -m unittest discover -s tests -v",
            "reproduction_command": "python3 -m superturiya.hackathon evaluate --mode frozen",
            "limitations": [
                "The benchmark is synthetic and does not establish production generalization.",
                "Cases, labels, and frozen reasoning rules were co-developed before the recorded freeze commit.",
                "FROZEN reproduces submitted outputs and deterministic scoring, not model inference.",
                "The primary benchmark does not claim cross-case policy transfer.",
            ],
        },
    )
    manifest = {
        "evaluation_id": report["evaluation_id"],
        "mode": report["mode"],
        "case_hash": report["benchmark"]["case_hash"],
        "label_hash": report["benchmark"]["label_hash"],
        "freeze_commit": report["benchmark"]["freeze_commit"],
        "metric_contract": report["metric_contract"],
        "files": sorted(str(path.relative_to(root)) for path in root.rglob("*.json")),
        "note": "FROZEN reproduces submitted outputs, deterministic verification, and scoring; it does not reproduce model inference.",
    }
    _write_json(root / "EVIDENCE_MANIFEST.json", manifest)


def main(argv: Optional[list] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run the SuperTuriya micro1 benchmark and evidence workflow."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate", help="Validate cases, hidden labels, and initial failures.")

    baseline = subparsers.add_parser("baseline", help="Run the direct raw-trace baseline.")
    baseline.add_argument("--mode", choices=["frozen", "live"], default="frozen")
    baseline.add_argument("--output", default=str(DEFAULT_EVIDENCE_ROOT / "baseline_evaluation.json"))

    evaluate = subparsers.add_parser("evaluate", help="Run baseline and final held-out evaluation.")
    evaluate.add_argument("--mode", choices=["frozen", "live"], default="frozen")
    evaluate.add_argument("--output", default=str(DEFAULT_EVIDENCE_ROOT))

    demo = subparsers.add_parser("demo", help="Prepare one case through the approval checkpoint.")
    demo.add_argument("--case", default="eval-006")
    demo.add_argument("--mode", choices=["frozen", "live"], default="frozen")
    demo.add_argument("--output", default="")

    shadow = subparsers.add_parser(
        "shadow-transfer",
        help="Activate one verified policy and test it on a separate showcase case.",
    )
    shadow.add_argument(
        "--output", default=str(DEFAULT_EVIDENCE_ROOT / "shadow_transfer.json")
    )

    args = parser.parse_args(argv)
    runner = AdaptiveEvaluationRunner()
    evaluator = EvaluationHarness(runtime=runner)
    if args.command == "validate":
        report = validate_benchmark()
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    if args.command == "baseline":
        report = runner.run_baseline(args.mode)
        output = Path(args.output)
        _write_json(output, report)
        _print_summary(report)
        print("Evidence: %s" % output)
        return
    if args.command == "evaluate":
        report = evaluator.compare(args.mode)
        output = Path(args.output)
        build_evidence_bundle(report, output)
        _print_summary(report)
        print("Evidence bundle: %s" % output)
        return
    if args.command == "demo":
        report = runner.case_demo(args.case, args.mode)
        output = Path(args.output) if args.output else DEFAULT_EVIDENCE_ROOT / (
            "demo_%s.json" % args.case
        )
        _write_json(output, report)
        print(json.dumps({
            "case_id": args.case,
            "critical_step": report["investigator_trajectory"]["output"]["critical_step"],
            "failure_class": report["investigator_trajectory"]["output"]["failure_class"],
            "operation": report["intervention"]["operation"],
            "approval_state": report["intervention"]["approval_state"],
            "evidence": str(output),
        }, indent=2))
        return
    if args.command == "shadow-transfer":
        with tempfile.TemporaryDirectory() as directory:
            store = SuperTuriyaStore(str(Path(directory) / "shadow.db"))
            try:
                engine = SuperTuriyaEngine(store)
                prepared = engine.prepare_hackathon_case(
                    {"tenant_id": "hackathon", "case_id": "eval-006", "mode": "frozen"}
                )
                intervention_id = prepared["stored_intervention"]["intervention_id"]
                engine.review_hackathon_intervention(
                    {
                        "tenant_id": "hackathon",
                        "intervention_id": intervention_id,
                        "decision": "approved",
                        "reviewer_id": "shadow-transfer-reviewer",
                        "note": "Approve the source repair for isolated replay.",
                        "mode": "frozen",
                    }
                )
                activated = engine.activate_hackathon_intervention(
                    {
                        "tenant_id": "hackathon",
                        "intervention_id": intervention_id,
                        "reviewer_id": "shadow-transfer-reviewer",
                        "note": "Activate only after verified source replay.",
                    }
                )
                report = ShadowTransferEvaluator().evaluate(
                    activated["procedural_policy"]
                )
            finally:
                store.close()
        output = Path(args.output)
        _write_json(output, report)
        print("Shadow case: %s" % report["case_id"])
        print("Verified safe transfer: %s" % report["verified_safe_transfer"])
        print("Evidence: %s" % output)


if __name__ == "__main__":
    main()
