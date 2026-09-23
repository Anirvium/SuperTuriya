from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .artifacts import atomic_json


def diagnose_game(path: Path) -> dict:
    kinds = Counter()
    sources = Counter()
    observation_hashes = []
    note_hashes = set()
    last_end = None
    with path.open() as stream:
        for line in stream:
            event = json.loads(line)
            kind = event["kind"]
            kinds[kind] += 1
            if kind == "action":
                sources[event.get("source", "unknown")] += 1
            elif kind == "observation":
                observation_hashes.append(event["hash"])
            elif kind == "plan":
                note_hashes.add(event.get("notes", ""))
            elif kind == "game_end":
                last_end = event
    if last_end is None:
        raise ValueError(f"journal has no game_end: {path}")
    decisions = sum(sources.values())
    unchanged = sum(a == b for a, b in zip(observation_hashes, observation_hashes[1:]))
    transitions = max(0, len(observation_hashes)-1)
    model_failures = kinds["model_error"] + kinds["schema_error"]
    fallback = sum(value for key, value in sources.items() if key.startswith("fallback"))
    signals = []
    if last_end.get("stop_reason") in {"error", "time_limit", "global_time_limit"}:
        signals.append("runtime")
    if decisions and (model_failures/decisions >= 0.15 or fallback/decisions >= 0.25):
        signals.append("model_interface")
    if transitions and unchanged/transitions >= 0.35:
        signals.append("exploration")
    if kinds["prediction_mismatches"] or kinds["counterexample"] >= 3:
        signals.append("planning_or_world_model")
    if kinds["plan"] >= 4 and len(note_hashes) <= max(1, kinds["plan"]//4):
        signals.append("memory_stagnation")
    if last_end.get("levels_completed", 0) == 0 and not signals:
        signals.append("reasoning_or_goal_inference")
    return {
        "journal": path.name,
        "levels_completed": last_end.get("levels_completed", 0),
        "actions": last_end.get("actions", decisions),
        "stop_reason": last_end.get("stop_reason"),
        "event_counts": dict(kinds),
        "action_sources": dict(sources),
        "unchanged_transition_rate": unchanged/transitions if transitions else 0.0,
        "distinct_note_states": len(note_hashes),
        "signals": signals,
    }


def diagnose_run(directory: Path, output: Path | None = None) -> dict:
    report = json.loads((directory/"report.json").read_text())
    games = []
    signal_counts = Counter()
    for game in report["games"]:
        if not game.get("journal"):
            item = {
                "journal": None,
                "levels_completed": game.get("levels_completed", 0),
                "actions": game.get("actions", 0),
                "stop_reason": game.get("stop_reason"),
                "signals": ["missing_journal"],
            }
        else:
            item = diagnose_game(directory/game["journal"])
        item["game_id"] = game["game_id"]
        games.append(item)
        signal_counts.update(item["signals"])
    result = {
        "schema": "superturiya-arc-agi-diagnostics-v1",
        "profile": report["config"]["profile"],
        "score": (report.get("scorecard") or {}).get("score"),
        "games": games,
        "signal_counts": dict(signal_counts),
        "interpretation": (
            "Signals are deterministic triage heuristics from observable journals. "
            "They prioritize replay review and do not prove a causal failure mechanism."
        ),
    }
    if output:
        atomic_json(output, result)
    return result
