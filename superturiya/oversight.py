from __future__ import annotations

from typing import Any, Mapping

from .evidence_integrity import sha256_json
from .models import JsonDict, clean_text, utc_now


CONSEQUENTIAL_KINDS = {"decision", "tool", "tool_call", "action", "route", "memory"}


def build_evidence_grounded_behavior_graph(trace: Mapping[str, Any]) -> JsonDict:
    run = dict(trace.get("run") or {})
    steps = list(trace.get("steps") or [])
    run_id = clean_text(run.get("run_id"))
    if not run_id:
        raise ValueError("trace.run.run_id is required")

    evidence_units = []
    behaviors = []
    decisions = []
    edges = []
    prior_behavior_id = None
    for step in steps:
        step_id = clean_text(step.get("step_id"))
        if not step_id:
            continue
        full_unit_id = "evidence:%s:step" % step_id
        full_unit = {
            "evidence_unit_id": full_unit_id,
            "source_id": step_id,
            "source_hash": sha256_json(dict(step)),
            "raw_ref": "trace_step:%s" % step_id,
            "field": "full_step",
        }
        evidence_units.append(full_unit)
        demand_refs = []
        response_refs = []
        if clean_text(step.get("input")):
            input_id = "evidence:%s:input" % step_id
            evidence_units.append(
                {
                    "evidence_unit_id": input_id,
                    "source_id": step_id,
                    "source_hash": sha256_json(step.get("input")),
                    "raw_ref": "trace_step:%s#input" % step_id,
                    "field": "input",
                }
            )
            demand_refs.append(input_id)
        if clean_text(step.get("output")):
            output_id = "evidence:%s:output" % step_id
            evidence_units.append(
                {
                    "evidence_unit_id": output_id,
                    "source_id": step_id,
                    "source_hash": sha256_json(step.get("output")),
                    "raw_ref": "trace_step:%s#output" % step_id,
                    "field": "output",
                }
            )
            response_refs.append(output_id)

        behavior_id = "behavior:%s" % step_id
        behavior = {
            "behavior_id": behavior_id,
            "scope_id": "scope:%s" % run_id,
            "kind": clean_text(step.get("kind") or "unknown"),
            "source": clean_text(step.get("source") or "unknown"),
            "status": clean_text(step.get("status") or "unknown"),
            "demand_refs": demand_refs,
            "action_refs": [full_unit_id],
            "response_refs": response_refs,
        }
        behaviors.append(behavior)
        if prior_behavior_id:
            edges.append(
                {
                    "from": prior_behavior_id,
                    "to": behavior_id,
                    "type": "PRECEDES",
                    "evidence_refs": [full_unit_id],
                }
            )
        prior_behavior_id = behavior_id

        consequential = behavior["kind"] in CONSEQUENTIAL_KINDS or behavior["status"] in {
            "failed",
            "error",
            "timeout",
        }
        if consequential:
            decisions.append(
                {
                    "decision_id": "consequence:%s" % step_id,
                    "behavior_id": behavior_id,
                    "decision": "%s by %s" % (behavior["kind"], behavior["source"]),
                    "impact": clean_text(step.get("output") or step.get("status") or "unknown"),
                    "verification_question": (
                        "Does the cited raw step justify this action and its consequence?"
                    ),
                    "evidence_refs": [full_unit_id, *response_refs],
                    "criticality": (
                        "high"
                        if behavior["status"] in {"failed", "error", "timeout"}
                        else "review"
                    ),
                }
            )

    graph: JsonDict = {
        "graph_version": "evidence-grounded-behavior-graph-v1",
        "created_at": utc_now(),
        "run_id": run_id,
        "raw_trace_preserved": True,
        "scopes": [
            {
                "scope_id": "scope:%s" % run_id,
                "goal": clean_text(run.get("goal")),
                "agent_id": clean_text(run.get("agent_id")),
                "evidence_refs": [
                    item["evidence_unit_id"]
                    for item in evidence_units
                    if item["field"] == "full_step"
                ],
            }
        ],
        "evidence_units": evidence_units,
        "behaviors": behaviors,
        "edges": edges,
        "consequential_decisions": decisions,
    }
    graph["graph_hash"] = sha256_json(graph)
    return graph
