from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .observation import digest, grid_value


class ProgramExecutor:
    def __init__(self, seconds=2, max_chars=12000):
        self.seconds = seconds
        self.max_chars = max_chars

    def run(self, source: str, entry: str, calls: list, timeout: float | None = None):
        if not isinstance(source, str) or len(source) > self.max_chars:
            return {"ok": False, "error": "program size exceeds budget"}
        body = json.dumps({"source": source, "entry": entry, "calls": calls})
        if len(body) > 2_000_000:
            return {"ok": False, "error": "program inputs exceed budget"}
        seconds = min(self.seconds, timeout) if timeout is not None else self.seconds
        if seconds <= 0:
            return {"ok": False, "error": "program deadline exhausted"}
        try:
            with tempfile.TemporaryDirectory(prefix="superturiya-compute-") as cwd:
                result = subprocess.run(
                    [sys.executable, "-I", str(Path(__file__).with_name("worker.py"))],
                    input=body, capture_output=True, text=True, timeout=seconds,
                    cwd=cwd, env={"PATH": os.defpath, "PYTHONHASHSEED": "0"},
                )
            if result.returncode != 0:
                return {"ok": False, "error": f"worker stopped: {result.returncode}"}
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "program timed out"}
        except (OSError, ValueError):
            return {"ok": False, "error": "program execution failed"}


@dataclass
class Rule:
    source: str
    revision: str
    support: int
    prospective_passes: int = 0
    status: str = "provisional"


class WorldModel:
    """A falsifiable transition program, scoped to one game/level.

    Historical consistency is not a proof. Two correct, nontrivial future
    predictions are required for prospective acceptance; contradictions revoke it.
    """
    def __init__(self, executor: ProgramExecutor, min_examples=4):
        self.executor = executor
        self.min_examples = min_examples
        self.rule: Rule | None = None
        self.rejections = 0
        self.revocations = 0

    def propose(self, source: str, transitions: list[dict], timeout=None):
        if len(transitions) < self.min_examples:
            return {"accepted": False, "reason": "insufficient observed transitions"}
        changed = sum(t["before"] != t["after"] for t in transitions)
        if changed < 2:
            return {"accepted": False, "reason": "need two nontrivial transitions"}
        # All retained transitions are regressions; they are not independent holdout data.
        result = self.executor.run(source, "predict", [[t["before"], t["action"]] for t in transitions], timeout)
        if not result["ok"]:
            self.rejections += 1
            return {"accepted": False, "reason": result["error"]}
        outputs = result["values"]
        mismatches = [i for i, (value, transition) in enumerate(zip(outputs, transitions))
                      if value != transition["after"]]
        if mismatches or len(outputs) != len(transitions):
            self.rejections += 1
            return {"accepted": False, "reason": "recorded-transition regression",
                    "mismatch_indices": mismatches[:16], "examples": len(transitions)}
        revision = digest(source)
        if self.rule and self.rule.revision == revision:
            return {"accepted": True, "status": self.rule.status, "revision": revision}
        self.rule = Rule(source, revision, len(transitions))
        return {"accepted": True, "status": "provisional", "revision": revision,
                "examples": len(transitions)}

    def predict(self, grid, action, timeout=None):
        if not self.rule:
            return None
        result = self.executor.run(self.rule.source, "predict", [[grid, action]], timeout)
        if not result["ok"]:
            self.rule = None
            return None
        try:
            return grid_value(result["values"][0])
        except (IndexError, ValueError):
            self.rule = None
            return None

    def observe(self, before, predicted, actual):
        if predicted is None or self.rule is None:
            return None
        revision = self.rule.revision
        if predicted != actual:
            self.rule = None
            self.revocations += 1
            return {"revision": revision, "status": "revoked", "reason": "future prediction contradicted"}
        if before != actual:
            self.rule.prospective_passes += 1
            if self.rule.prospective_passes >= 2:
                self.rule.status = "accepted_on_observed_evidence"
        return {"revision": revision, "status": self.rule.status,
                "prospective_passes": self.rule.prospective_passes}
