#!/usr/bin/env python3
"""Build one reviewable Kaggle release directory and archive the previous one."""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from superturiya_arc.config import Config
from superturiya_arc.notebook import build
from superturiya_arc.release import verify_build


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
TARGET = DIST / "kaggle"
MODEL_SOURCE = "foysalemonshanto/qwen3-8-27b-fp8-repacked-v1/pyTorch/hf-fp8/1"
WHEEL_SOURCE = "driessmit1/arc3-vllm-h100-wheelhouse-v3"
PUBLIC_GAMES = ("cd82", "ft09", "ls20", "r11l", "s5i5", "tu93", "vc33", "wa30")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        choices=["smoke", "competition", "repair", "public-memory", "public-repair"],
        required=True,
    )
    args = parser.parse_args()

    config_name = {
        "smoke": "smoke.json",
        "competition": "competition.json",
        "repair": "repair-ablation.json",
        "public-memory": "competition.json",
        "public-repair": "repair-ablation.json",
    }[args.profile]
    config = Config.load(ROOT / "configs" / config_name)
    DIST.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".kaggle-build-", dir=DIST))
    candidate = temporary / "kaggle"
    kwargs = {}
    if args.profile != "smoke":
        kwargs = {
            "model_path": "auto:qwen3-8-27b-fp8-repacked-v1",
            "model_sources": [MODEL_SOURCE],
            "wheel_path": "auto:arc3-vllm-h100-wheelhouse-v3",
            "dataset_sources": [WHEEL_SOURCE],
        }
    if args.profile.startswith("public-"):
        kwargs["validation_games"] = PUBLIC_GAMES
    try:
        build(
            config,
            candidate,
            username="piyusha1234",
            accelerator="rtx6000",
            kernel_slug="notebook5326562b0c",
            title="notebook5326562b0c",
            **kwargs,
        )
        verified = verify_build(candidate)
        if TARGET.exists():
            archive = DIST / "archive"
            archive.mkdir(exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            destination = archive / f"kaggle-{stamp}"
            suffix = 1
            while destination.exists():
                suffix += 1
                destination = archive / f"kaggle-{stamp}-{suffix}"
            TARGET.rename(destination)
        candidate.rename(TARGET)
        temporary.rmdir()
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    print(json.dumps({"profile": args.profile, "directory": str(TARGET), **verified}, indent=2))


if __name__ == "__main__":
    main()
