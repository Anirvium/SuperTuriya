from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path


def atomic_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)


def source_manifest():
    root = Path(__file__).parent
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.glob("*.py"))}


def provenance():
    packages = {}
    for name in ("arc-agi", "arcengine", "vllm", "torch", "transformers"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            pass
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL,
                                         text=True, timeout=2).strip()
    except (OSError, subprocess.SubprocessError):
        commit = None
    return {"created_at": datetime.now(timezone.utc).isoformat(), "python": sys.version,
            "platform": platform.platform(), "packages": packages, "git_commit": commit,
            "source_sha256": source_manifest()}


class Journal:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = path.open("x", buffering=1)
        self.sequence = 0
        self.previous = "0" * 64

    def write(self, kind: str, **payload):
        item = {"seq": self.sequence, "previous": self.previous, "kind": kind, **payload}
        encoded = json.dumps(item, sort_keys=True, separators=(",", ":"), allow_nan=False)
        self.previous = hashlib.sha256(encoded.encode()).hexdigest()
        self.stream.write(json.dumps({**item, "sha256": self.previous}, sort_keys=True) + "\n")
        self.sequence += 1

    def close(self):
        self.stream.flush()
        self.stream.close()


def verify_journal(path: Path):
    previous = "0" * 64
    count = 0
    with path.open() as stream:
        for sequence, line in enumerate(stream):
            item = json.loads(line)
            given = item.pop("sha256")
            encoded = json.dumps(item, sort_keys=True, separators=(",", ":"), allow_nan=False)
            if (item["seq"] != sequence or item["previous"] != previous
                    or hashlib.sha256(encoded.encode()).hexdigest() != given):
                raise ValueError(f"journal integrity failure at line {sequence + 1}")
            previous = given
            count += 1
    return {"events": count, "tip": previous}
