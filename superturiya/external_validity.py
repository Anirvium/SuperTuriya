from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Optional

from .external_evaluation import (
    build_evidence_manifest,
    run_isolation_audit,
    score_ablations,
    score_comparison,
    score_live_trials,
    validate_external_freeze,
    write_json,
)
from .external_runtime import ExternalRuntimeRunner, SameModelContractError
from .models import utc_now


DEFAULT_EVIDENCE_ROOT = (
    Path(__file__).resolve().parent.parent / "evidence" / "external_validity" / "v1"
)


def _print(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _archive_existing(path: Path) -> Optional[Path]:
    """Preserve an immutable content-addressed copy before replacing LIVE evidence."""

    if not path.exists():
        return None
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()[:16]
    history = path.parent / "history"
    history.mkdir(parents=True, exist_ok=True)
    archived = history / ("%s_%s%s" % (path.stem, digest, path.suffix))
    if not archived.exists():
        archived.write_bytes(raw)
    return archived


def _live_status() -> dict:
    required = (
        "SUPERTURIYA_LLM_ENDPOINT",
        "SUPERTURIYA_LLM_API_KEY",
        "SUPERTURIYA_LLM_MODEL",
    )
    missing = [key for key in required if not os.environ.get(key)]
    return {
        "artifact_schema": "same-model-live-status-v1",
        "created_at": utc_now(),
        "status": "blocked_missing_configuration" if missing else "ready",
        "missing_environment_variables": missing,
        "credential_values_recorded": False,
        "required_trial_count": 3,
        "command": "python3 -m superturiya.external_validity live --trials 3",
    }


def main(argv: Optional[list] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Build versioned external-validity evidence without changing core behavior."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate")
    subparsers.add_parser("isolation")
    subparsers.add_parser("frozen")
    subparsers.add_parser("probe")
    live = subparsers.add_parser("live")
    live.add_argument("--trials", type=int, default=3)
    ablation = subparsers.add_parser("ablation")
    ablation.add_argument("--mode", choices=["frozen", "live"], default="frozen")
    bundle = subparsers.add_parser("bundle")
    bundle.add_argument("--include-live", action="store_true")
    parser.add_argument("--output-root", default=str(DEFAULT_EVIDENCE_ROOT))
    args = parser.parse_args(argv)
    output_root = Path(args.output_root)

    if args.command == "validate":
        payload = validate_external_freeze()
        write_json(output_root / "freeze_validation.json", payload)
        _print(payload)
        return
    if args.command == "isolation":
        payload = run_isolation_audit()
        write_json(output_root / "isolation_audit.json", payload)
        _print(payload)
        return
    if args.command == "frozen":
        payload = score_comparison(ExternalRuntimeRunner().run_comparison("frozen"))
        write_json(output_root / "frozen_comparison.json", payload)
        _print(payload["metrics"])
        return
    if args.command == "probe":
        status = _live_status()
        write_json(output_root / "live_status.json", status)
        if status["status"] != "ready":
            _print(status)
            raise SystemExit(2)
        try:
            payload = ExternalRuntimeRunner().probe_live_provider()
        except (SameModelContractError, RuntimeError, ValueError) as exc:
            failure = {**status, "status": "probe_failed", "error": str(exc)}
            write_json(output_root / "live_status.json", failure)
            raise
        write_json(output_root / "live_probe.json", payload)
        write_json(output_root / "live_status.json", {**status, "status": "probe_complete"})
        _print(
            {
                "status": payload["status"],
                "returned_model": payload["returned_model"],
                "json_object_received": payload["json_object_received"],
                "usage": payload["usage"],
            }
        )
        return
    if args.command == "ablation":
        try:
            payload = score_ablations(ExternalRuntimeRunner().run_ablations(args.mode))
        except (SameModelContractError, RuntimeError, ValueError) as exc:
            if args.mode == "live":
                write_json(
                    output_root / "live_status.json",
                    {**_live_status(), "status": "ablation_failed", "error": str(exc)},
                )
            raise
        write_json(output_root / ("ablation_%s.json" % args.mode), payload)
        _print({"matrix": payload["matrix"]})
        return
    if args.command == "live":
        status = _live_status()
        write_json(output_root / "live_status.json", status)
        if status["status"] != "ready":
            _print(status)
            raise SystemExit(2)
        try:
            payload = score_live_trials(
                ExternalRuntimeRunner().run_same_model_live(args.trials)
            )
        except (SameModelContractError, RuntimeError, ValueError) as exc:
            failure = {**status, "status": "experiment_failed", "error": str(exc)}
            write_json(output_root / "live_status.json", failure)
            raise
        live_path = output_root / "live_comparison.json"
        _archive_existing(live_path)
        write_json(live_path, payload)
        write_json(output_root / "live_status.json", {**status, "status": "complete"})
        _print(payload["aggregate"])
        return
    if args.command == "bundle":
        freeze = validate_external_freeze()
        isolation = run_isolation_audit()
        frozen = score_comparison(ExternalRuntimeRunner().run_comparison("frozen"))
        ablations = score_ablations(ExternalRuntimeRunner().run_ablations("frozen"))
        write_json(output_root / "freeze_validation.json", freeze)
        write_json(output_root / "isolation_audit.json", isolation)
        write_json(output_root / "frozen_comparison.json", frozen)
        write_json(output_root / "ablation_frozen.json", ablations)
        status = _live_status()
        write_json(output_root / "live_status.json", status)
        if args.include_live:
            if status["status"] != "ready":
                _print(status)
                raise SystemExit(2)
            try:
                live_payload = score_live_trials(
                    ExternalRuntimeRunner().run_same_model_live(3)
                )
            except (SameModelContractError, RuntimeError, ValueError) as exc:
                failure = {
                    **status,
                    "status": "experiment_failed",
                    "error": str(exc),
                }
                write_json(output_root / "live_status.json", failure)
                raise
            live_path = output_root / "live_comparison.json"
            _archive_existing(live_path)
            write_json(live_path, live_payload)
            write_json(output_root / "live_status.json", {**status, "status": "complete"})
        manifest = build_evidence_manifest(output_root)
        write_json(output_root / "manifest.json", manifest)
        _print(
            {
                "benchmark_id": freeze["benchmark_id"],
                "frozen_metrics": frozen["metrics"],
                "isolation_passed": isolation["passed"],
                "live_status": status["status"],
                "evidence_root": str(output_root),
            }
        )


if __name__ == "__main__":
    main()
