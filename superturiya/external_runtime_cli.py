from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from .external_runtime import ExternalRuntimeRunner


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: Optional[list] = None) -> None:
    parser = argparse.ArgumentParser(description="Run sealed external runtime predictions.")
    parser.add_argument("command", choices=["comparison", "ablation"])
    parser.add_argument("--benchmark-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=["frozen", "live"], default="frozen")
    args = parser.parse_args(argv)

    runner = ExternalRuntimeRunner(Path(args.benchmark_root))
    if args.command == "comparison":
        payload = runner.run_comparison(args.mode)
    else:
        payload = runner.run_ablations(args.mode)
    _write(Path(args.output), payload)


if __name__ == "__main__":
    main()
