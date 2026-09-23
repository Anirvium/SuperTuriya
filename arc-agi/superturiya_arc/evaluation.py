from __future__ import annotations

import json
import random
from pathlib import Path

from .artifacts import atomic_json
from .observation import digest


def create_split(game_ids, path: Path, seed=2026):
    if path.exists():
        raise ValueError("split already exists; refusing to overwrite a frozen partition")
    groups = {}
    for game_id in sorted(game_ids):
        groups.setdefault(game_id.split("-")[0], []).append(game_id)
    keys = sorted(groups)
    random.Random(seed).shuffle(keys)
    n = max(1, len(keys)//3)
    holdout = sorted(g for k in keys[:n] for g in groups[k])
    dev = sorted(g for k in keys[n:] for g in groups[k])
    if not dev:
        raise ValueError("at least two game families required")
    payload = {"schema": "superturiya-arc-agi-split-v1", "seed": seed,
               "development": dev, "holdout": holdout,
               "note": "Game IDs group versions, not semantically related game families. Review family overlap before research claims."}
    payload["sha256"] = digest(payload)
    atomic_json(path, payload)
    return payload


def load_split(path, partition):
    payload = json.loads(Path(path).read_text())
    signature = payload.pop("sha256")
    if digest(payload) != signature:
        raise ValueError("split hash mismatch")
    return payload[partition]


def game_scores(report):
    # One environment creation per run: multiple scorecard runs would be ambiguous.
    result = {}
    for entry in (report.get("scorecard") or {}).get("environments", []):
        runs = entry.get("runs", [])
        if len(runs) != 1:
            raise ValueError("expected exactly one scored run per environment")
        result[entry["id"]] = float(runs[0]["score"])
    return result


def compare(left_path, right_path, output=None):
    left, right = [json.loads(Path(p).read_text()) for p in (left_path, right_path)]
    if left["selected_games"] != right["selected_games"]:
        raise ValueError("game/version/order mismatch")
    for key in ("seed", "model", "max_actions", "game_seconds", "total_seconds", "max_model_calls",
                "max_tokens", "temperature", "vision", "enable_thinking", "max_context_tokens",
                "max_resets", "max_tool_rounds", "tool_seconds", "plan_length", "context_chars"):
        if left["config"][key] != right["config"][key]:
            raise ValueError(f"unmatched comparison config: {key}")
    if left["provenance"]["packages"] != right["provenance"]["packages"]:
        raise ValueError("runtime package mismatch")
    if left["mode"] != right["mode"]:
        raise ValueError("evaluation mode mismatch")
    if left["status"] != "complete" or right["status"] != "complete":
        raise ValueError("cannot claim paired improvement from incomplete runs")
    ls, rs = game_scores(left), game_scores(right)
    rows = []
    for game_id in left["selected_games"]:
        # Some SDK versions use short IDs in scorecard serialization.
        key = game_id if game_id in ls else game_id.split("-")[0]
        if key not in ls or key not in rs:
            raise ValueError(f"missing official score for {game_id}")
        rows.append({"game_id": game_id, "baseline": ls[key], "candidate": rs[key], "delta": rs[key]-ls[key]})
    diffs = [r["delta"] for r in rows]
    rng = random.Random(2026)
    means = sorted(sum(rng.choices(diffs, k=len(diffs)))/len(diffs) for _ in range(3000))
    result = {"schema": "superturiya-arc-agi-comparison-v1", "games": rows,
              "mean_score_delta": sum(diffs)/len(diffs), "paired_bootstrap_95": [means[75], means[2924]],
              "baseline_profile": left["config"]["profile"], "candidate_profile": right["config"]["profile"],
              "baseline_seconds": left["seconds"], "candidate_seconds": right["seconds"],
              "baseline_model_usage": left.get("model_usage"), "candidate_model_usage": right.get("model_usage"),
              "baseline_source": left["provenance"]["source_sha256"],
              "candidate_source": right["provenance"]["source_sha256"],
              "claim_boundary": "Local paired engineering comparison; not private Kaggle evidence. Small samples and related game families limit uncertainty estimates. Token use is reported separately, not forced equal."}
    if output:
        atomic_json(Path(output), result)
    return result
