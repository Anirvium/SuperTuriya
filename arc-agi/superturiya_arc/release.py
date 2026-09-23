from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from .artifacts import verify_journal


def verify_run(directory: Path):
    report = json.loads((directory/"report.json").read_text())
    if report["status"] != "complete":
        raise ValueError("run is not complete")
    checked = {}
    for game in report["games"]:
        if "journal" not in game:
            checked[game["game_id"]] = {"skipped": game["stop_reason"]}
            continue
        path = directory/game["journal"]
        if path.parent.resolve() != directory.resolve():
            raise ValueError("invalid journal path")
        result = verify_journal(path)
        if result != {"events": game["journal_events"], "tip": game["journal_tip"]}:
            raise ValueError(f"journal was truncated or replaced: {path.name}")
        checked[game["game_id"]] = result
    return checked


def verify_build(directory: Path):
    manifest = json.loads((directory/"build-manifest.json").read_text())
    notebook = directory/"submission.ipynb"
    if hashlib.sha256(notebook.read_bytes()).hexdigest() != manifest["notebook_sha256"]:
        raise ValueError("notebook changed after build")
    metadata = json.loads((directory/"kernel-metadata.json").read_text())
    if metadata["enable_internet"] or metadata["competition_sources"] != ["arc-prize-2026-arc-agi-3"]:
        raise ValueError("invalid competition metadata")
    if not re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_-]+", metadata["id"]):
        raise ValueError("invalid notebook ID")
    expected_machine = {
        "cpu": "", "t4": "NvidiaTeslaT4", "p100": "NvidiaTeslaP100",
        "rtx6000": "NvidiaRtxPro6000",
    }[manifest["settings"]["accelerator"]]
    if metadata.get("machine_shape", "") != expected_machine:
        raise ValueError("Kaggle accelerator metadata does not match the build")
    uses_model = manifest["settings"]["uses_model"]
    if uses_model and (not metadata["model_sources"] or not metadata["dataset_sources"]):
        raise ValueError("model build is missing offline Kaggle inputs")
    notebook_data = json.loads(notebook.read_text())
    for entry in notebook_data["cells"]:
        if entry["cell_type"] == "code":
            compile(entry["source"], "notebook", "exec")
    return {"id": metadata["id"], "profile": manifest["config"]["profile"],
            "machine_shape": metadata.get("machine_shape", ""),
            "internet": False, "visibility": "private" if metadata["is_private"] else "public",
            "status": "source_bundle_verified", "kaggle_execution_verified": False}


def push(directory: Path):
    """Explicit CLI action: upload a private notebook, not an official submission."""
    status = verify_build(directory)
    metadata = json.loads((directory/"kernel-metadata.json").read_text())
    if not metadata["is_private"]:
        raise ValueError("this command only uploads private drafts; publish reviewed artifacts in Kaggle")
    env = os.environ.copy()
    token = Path(".kaggle/access_token")
    if token.exists():
        env["KAGGLE_API_TOKEN"] = token.read_text().strip()
    # Credentials remain in the child environment, never interpolated into a shell command.
    command = [sys.executable, "-m", "kaggle", "kernels", "push", "-p", str(directory)]
    if metadata.get("machine_shape"):
        command += ["--accelerator", metadata["machine_shape"]]
    subprocess.run(command, env=env, check=True)
    return status
