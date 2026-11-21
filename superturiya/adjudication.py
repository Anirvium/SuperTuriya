from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .adaptive import agent_case_view
from .evidence_integrity import sha256_json
from .external_v2 import DEFAULT_ROOT, load_external_v2_cases
from .models import JsonDict, clean_text, utc_now


LABELS = {"yes", "no", "unresolved"}


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _result_projection(result: Mapping[str, Any]) -> JsonDict:
    intervention = dict(result.get("intervention") or {})
    simulation = dict((result.get("replay") or {}).get("simulation") or {})
    return {
        "candidate_intervention": {
            key: intervention.get(key)
            for key in (
                "operation",
                "target_id",
                "after_value",
                "evidence_refs",
                "rationale",
                "risks",
                "verification_conditions",
            )
        },
        "replay_observation": {
            "state": simulation.get("state"),
            "steps": simulation.get("steps"),
            "initial_state_hash": simulation.get("initial_state_hash"),
            "task_hash": simulation.get("task_hash"),
            "fixture_hash": simulation.get("fixture_hash"),
            "frozen_policy_hash": simulation.get("frozen_policy_hash"),
            "config_diff": simulation.get("config_diff"),
        },
    }


def build_blind_adjudication_bundle(
    raw_path: Path,
    benchmark_root: Path = DEFAULT_ROOT,
    seed: str = "superturiya-v2-adjudication-v1",
) -> JsonDict:
    raw_path = Path(raw_path)
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    runtime = dict(raw.get("runtime") or {})
    trials = list(runtime.get("trials") or [])
    cases = load_external_v2_cases(Path(benchmark_root))
    case_by_id = {case["case_id"]: case for case in cases}
    if not trials:
        raise ValueError("raw prediction artifact contains no trials")

    key_entries: Dict[str, JsonDict] = {}
    packet_outcomes: Dict[str, List[JsonDict]] = defaultdict(list)
    for trial_index, trial in enumerate(trials, start=1):
        for arm in ("baseline", "final"):
            results = list((trial.get(arm) or {}).get("results") or [])
            for result in results:
                case_id = clean_text(result.get("case_id"))
                if case_id not in case_by_id:
                    raise ValueError("prediction references unknown case: %s" % case_id)
                digest = hashlib.sha256(
                    ("%s|%s|%d|%s" % (seed, case_id, trial_index, arm)).encode()
                ).hexdigest()[:12]
                alias = "outcome-%s" % digest
                key_entries[alias] = {
                    "case_id": case_id,
                    "trial_index": trial_index,
                    "arm": arm,
                    "automatic_task_completed": bool(
                        result.get("verified_safe_recovery")
                    ),
                }
                packet_outcomes[case_id].append(
                    {
                        "outcome_alias": alias,
                        **_result_projection(result),
                    }
                )

    packets = []
    for case_id in sorted(case_by_id):
        outcomes = sorted(
            packet_outcomes[case_id], key=lambda item: item["outcome_alias"]
        )
        packets.append(
            {
                "packet_id": "case-packet-%s" % case_id,
                "case": agent_case_view(case_by_id[case_id]),
                "outcomes": outcomes,
                "review_schema": {
                    "task_completed": "yes | no | unresolved",
                    "first_consequential_error": "step_id or null",
                    "partial_progress": "0.0 to 1.0",
                    "repair_surface_valid": "yes | no | unresolved",
                    "alternate_valid_path": "boolean",
                    "evidence_refs": "list of source references",
                    "note": "short evidence-backed rationale",
                },
            }
        )

    expected_outcomes = len(cases) * len(trials) * 2
    actual_outcomes = sum(len(packet["outcomes"]) for packet in packets)
    if actual_outcomes != expected_outcomes:
        raise ValueError(
            "adjudication bundle outcome count mismatch: %d != %d"
            % (actual_outcomes, expected_outcomes)
        )
    source_sha = _file_sha256(raw_path)
    review_bundle: JsonDict = {
        "schema": "superturiya-blind-adjudication-v1",
        "created_at": utc_now(),
        "source_raw_sha256": source_sha,
        "blind_to": ["arm", "trial", "automatic verdict", "private gold"],
        "case_packet_count": len(packets),
        "outcome_count": actual_outcomes,
        "minimum_independent_reviewers": 2,
        "disagreement_policy": "third reviewer tie-break",
        "packets": packets,
    }
    review_bundle["bundle_hash"] = sha256_json(review_bundle)
    private_key: JsonDict = {
        "schema": "superturiya-adjudication-key-v1",
        "source_raw_sha256": source_sha,
        "review_bundle_hash": review_bundle["bundle_hash"],
        "entries": key_entries,
    }
    private_key["key_hash"] = sha256_json(private_key)
    return {"review_bundle": review_bundle, "private_key": private_key}


def summarize_adjudications(
    labels: Sequence[Mapping[str, Any]], private_key: Mapping[str, Any]
) -> JsonDict:
    entries = dict(private_key.get("entries") or {})
    by_outcome: Dict[str, List[JsonDict]] = defaultdict(list)
    seen = set()
    for raw_label in labels:
        label = dict(raw_label)
        alias = clean_text(label.get("outcome_alias"))
        reviewer = clean_text(label.get("reviewer_id"))
        task_completed = clean_text(label.get("task_completed")).lower()
        if alias not in entries:
            raise ValueError("unknown outcome_alias: %s" % alias)
        if not reviewer:
            raise ValueError("reviewer_id is required")
        if task_completed not in LABELS:
            raise ValueError("task_completed must be yes, no, or unresolved")
        key = (alias, reviewer)
        if key in seen:
            raise ValueError("duplicate reviewer label for %s" % alias)
        seen.add(key)
        label["task_completed"] = task_completed
        by_outcome[alias].append(label)

    resolved = []
    pending = []
    for alias, reviews in sorted(by_outcome.items()):
        independent = {clean_text(item.get("reviewer_id")) for item in reviews}
        votes = [item["task_completed"] for item in reviews]
        yes = votes.count("yes")
        no = votes.count("no")
        if len(independent) < 2:
            pending.append({"outcome_alias": alias, "reason": "needs second reviewer"})
            continue
        if yes == no or (yes < 2 and no < 2):
            pending.append({"outcome_alias": alias, "reason": "needs tie-break reviewer"})
            continue
        human_completed = yes > no
        mapping = entries[alias]
        resolved.append(
            {
                "outcome_alias": alias,
                "case_id": mapping["case_id"],
                "trial_index": mapping["trial_index"],
                "arm": mapping["arm"],
                "automatic_task_completed": bool(
                    mapping["automatic_task_completed"]
                ),
                "human_task_completed": human_completed,
                "reviewer_count": len(independent),
            }
        )

    arm_metrics = {}
    for arm in ("baseline", "final"):
        rows = [item for item in resolved if item["arm"] == arm]
        tp = sum(
            item["automatic_task_completed"] and item["human_task_completed"]
            for item in rows
        )
        tn = sum(
            not item["automatic_task_completed"] and not item["human_task_completed"]
            for item in rows
        )
        fp = sum(
            item["automatic_task_completed"] and not item["human_task_completed"]
            for item in rows
        )
        fn = sum(
            not item["automatic_task_completed"] and item["human_task_completed"]
            for item in rows
        )
        arm_metrics[arm] = {
            "resolved_outcomes": len(rows),
            "corrected_completion_rate": round(
                sum(item["human_task_completed"] for item in rows) / max(1, len(rows)),
                4,
            ),
            "confusion_matrix": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        }
    summary: JsonDict = {
        "schema": "superturiya-adjudication-summary-v1",
        "resolved": resolved,
        "pending": pending,
        "arms": arm_metrics,
    }
    summary["summary_hash"] = sha256_json(summary)
    return summary


def _write_new(path: Path, payload: Mapping[str, Any]) -> None:
    if path.exists():
        raise ValueError("refusing to overwrite adjudication artifact: %s" % path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Build blinded External-v2 adjudication packets.")
    parser.add_argument("--raw", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--key-output", required=True)
    parser.add_argument("--benchmark-root", default=str(DEFAULT_ROOT))
    parser.add_argument("--seed", default="superturiya-v2-adjudication-v1")
    args = parser.parse_args(argv)
    built = build_blind_adjudication_bundle(
        Path(args.raw), Path(args.benchmark_root), args.seed
    )
    _write_new(Path(args.output), built["review_bundle"])
    _write_new(Path(args.key_output), built["private_key"])
    print(
        json.dumps(
            {
                "output": args.output,
                "key_output": args.key_output,
                "case_packet_count": built["review_bundle"]["case_packet_count"],
                "outcome_count": built["review_bundle"]["outcome_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
