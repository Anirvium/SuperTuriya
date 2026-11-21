"""Versioned, inert trace import. Imported spans never authorize execution."""
from __future__ import annotations

import copy
import json
import re
from datetime import datetime
from typing import Any, Mapping

from .adaptive import content_hash
from .models import new_id, utc_now

SCHEMA = "superturiya-trace-v1"
SECRET_KEY = re.compile(r"(?:^|[._-])(authorization|api[_-]?key|access[_-]?token|refresh[_-]?token|token|password|secret|cookie|set.cookie|client[_-]?secret|credentials?)$", re.I)
BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
ASSIGNMENT = re.compile(r"(?i)\b(api[_-]?key|access[_-]?token|password|client[_-]?secret)\s*[:=]\s*[^\s,;\"'}]+")


def redact(value: Any, depth: int = 0) -> Any:
    if depth > 20:
        raise ValueError("trace nesting exceeds 20 levels")
    if isinstance(value, dict):
        return {str(k): "[REDACTED]" if SECRET_KEY.search(str(k)) else redact(v, depth + 1) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, depth + 1) for v in value]
    if isinstance(value, str):
        return ASSIGNMENT.sub(lambda m: m.group(1) + "=[REDACTED]", BEARER.sub("Bearer [REDACTED]", value))
    if value is None or isinstance(value, (bool, int, float)):
        return value
    raise ValueError("trace values must be JSON-compatible")


def text(value: Any, name: str, maximum: int = 4000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError("%s must be nonempty text of at most %d characters" % (name, maximum))
    return value.strip()


def normalize(record: Mapping[str, Any]) -> dict:
    if not isinstance(record, dict) or record.get("schema") != SCHEMA:
        raise ValueError("record.schema must be " + SCHEMA)
    # Reject non-finite JSON and unreasonable inputs even outside the HTTP API.
    try:
        encoded = json.dumps(record, allow_nan=False)
    except (ValueError, TypeError, RecursionError) as exc:
        raise ValueError("trace must contain finite, JSON-compatible values") from exc
    if len(encoded.encode()) > 900_000:
        raise ValueError("trace exceeds the 900 KB import limit")
    spans = record.get("spans")
    if not isinstance(spans, list) or not 1 <= len(spans) <= 500:
        raise ValueError("trace requires between 1 and 500 spans")
    result = {"schema": SCHEMA, "agent": text(record.get("agent"), "agent", 200),
              "goal": text(record.get("goal"), "goal"), "status": record.get("status", "unknown"), "spans": []}
    if not isinstance(result["status"], str) or result["status"] not in {"completed", "failed", "running", "unknown"}:
        raise ValueError("unsupported trace status")
    identifiers = set()
    for i, span in enumerate(spans):
        if not isinstance(span, dict):
            raise ValueError("each span must be an object")
        identifier = text(span.get("span_id"), "span_id", 200)
        if not re.fullmatch(r"[A-Za-z0-9._:-]+", identifier):
            raise ValueError("span_id must use letters, numbers, dots, colons, dashes or underscores")
        if identifier in identifiers:
            raise ValueError("duplicate span_id")
        identifiers.add(identifier)
        status = span.get("status", "unknown")
        kind = span.get("kind", "step")
        if not isinstance(status, str) or not isinstance(kind, str) or status not in {"completed", "failed", "running", "unknown"} or kind not in {"step", "tool", "model", "retrieval", "approval"}:
            raise ValueError("unsupported span status or kind")
        item = {"span_id": identifier, "parent_span_id": span.get("parent_span_id") or None,
                "name": text(span.get("name"), "span.name", 200), "status": status, "kind": kind,
                "input": span.get("input"), "output": span.get("output"), "attributes": span.get("attributes", {})}
        if not isinstance(item["attributes"], dict):
            raise ValueError("span attributes must be an object")
        for key in ("started_at", "ended_at"):
            if span.get(key) is not None:
                item[key] = text(span[key], key, 80)
                try:
                    timestamp = datetime.fromisoformat(item[key].replace("Z", "+00:00"))
                    if timestamp.utcoffset() is None:
                        raise ValueError("timezone required")
                except ValueError as exc:
                    raise ValueError(key + " must be an ISO timestamp with timezone") from exc
        if item.get("started_at") and item.get("ended_at"):
            if datetime.fromisoformat(item["ended_at"].replace("Z", "+00:00")) < datetime.fromisoformat(item["started_at"].replace("Z", "+00:00")):
                raise ValueError("span ends before it starts")
        result["spans"].append(item)
    parents = {s["span_id"]: s["parent_span_id"] for s in result["spans"]}
    for identifier, parent in parents.items():
        if parent is not None and (not isinstance(parent, str) or parent not in identifiers):
            raise ValueError("parent span does not exist")
        visited = {identifier}
        while parent is not None:
            if parent in visited:
                raise ValueError("span hierarchy contains a cycle")
            visited.add(parent)
            parent = parents[parent]
    return redact(result)


def inspect_trace(document: Mapping[str, Any]) -> dict:
    findings = []
    spans = document["spans"]
    for s in spans:
        if s["status"] == "failed":
            findings.append({"code": "recorded_failure", "severity": "attention", "span_id": s["span_id"], "message": "This span was recorded as failed. Inspect its input, output and upstream dependencies."})
        if s["status"] == "completed" and s["kind"] == "tool" and s["output"] is None:
            findings.append({"code": "missing_tool_output", "severity": "review", "span_id": s["span_id"], "message": "A completed tool span has no recorded output. Capture it to make the evidence inspectable."})
        if not s.get("started_at") or not s.get("ended_at"):
            findings.append({"code": "incomplete_timing", "severity": "review", "span_id": s["span_id"], "message": "Timing is incomplete; execution duration and ordering cannot be established for this span."})
    if document["status"] == "completed" and any(s["status"] == "failed" for s in spans):
        findings.append({"code": "completion_with_failure", "severity": "review", "span_id": None, "message": "The run is marked completed and contains a failed span. Check whether a recorded recovery explains the outcome."})
    report = {"schema": "superturiya-trace-inspection-v1", "span_count": len(spans),
              "failed_span_count": sum(s["status"] == "failed" for s in spans), "findings": findings,
              "replay_available": False, "activation_available": False,
              "boundary": "Recorded trace inspection only. Findings are evidence checks, not a verified root cause. An executable replay adapter and task-specific verifier are required before any repair or activation."}
    report["report_hash"] = content_hash(report)
    return report


def import_trace(store: Any, payload: Mapping[str, Any]) -> dict:
    document = normalize(payload.get("record"))
    digest = content_hash(document)
    tenant = text(payload.get("tenant_id", "hackathon"), "tenant_id", 200)
    principal = text(payload.get("principal_id", "local-operator"), "principal_id", 200)
    now = utc_now()
    run_id = new_id("import")
    report = inspect_trace(document)
    # One transaction: a failed import leaves neither a partial trace nor a receipt.
    with store._lock, store._connection:
        existing = store._connection.execute("SELECT run_id FROM trace_imports WHERE tenant_id=? AND content_hash=?", (tenant, digest)).fetchone()
        if existing:
            return {"run_id": existing[0], "content_hash": digest, "duplicate": True, "report": report}
        store._connection.execute("INSERT INTO traces (run_id,tenant_id,subject_id,agent_id,goal,started_at,ended_at,status,metadata) VALUES (?,?,?,?,?,?,?,?,?)",
            (run_id, tenant, "imported-traces", document["agent"], document["goal"], now, now, document["status"], json.dumps({"imported": True, "content_hash": digest, "replay_available": False})))
        ids = {s["span_id"]: new_id("span") for s in document["spans"]}
        for i, s in enumerate(document["spans"], 1):
            store._connection.execute("INSERT INTO trace_steps (step_id,run_id,tenant_id,subject_id,parent_step_id,step_index,kind,source,input,output,status,started_at,ended_at,memory_refs,tool_call_id,metadata) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (ids[s["span_id"]], run_id, tenant, "imported-traces", ids.get(s["parent_span_id"]), i, s["kind"], s["name"], json.dumps(s["input"]), json.dumps(s["output"]), s["status"], s.get("started_at", now), s.get("ended_at"), "[]", None, json.dumps({"source_span_id": s["span_id"], "attributes": s["attributes"]})))
        store._connection.execute("INSERT INTO trace_imports (run_id,tenant_id,content_hash,document,report,created_at) VALUES (?,?,?,?,?,?)", (run_id, tenant, digest, json.dumps(document), json.dumps(report), now))
        store._connection.execute("INSERT INTO audit_events (event_id,tenant_id,subject_id,action,target_type,target_id,created_at,metadata) VALUES (?,?,?,?,?,?,?,?)",
            (new_id("aud"), tenant, "imported-traces", "trace.import", "trace", run_id, now, json.dumps({"principal_id": principal, "content_hash": digest, "redaction": "best-effort credential patterns; user review required"})))
    return {"run_id": run_id, "content_hash": digest, "duplicate": False, "report": report}


def export_trace(store: Any, run_id: str, tenant_id: str) -> dict:
    with store._lock:
        row = store._connection.execute("SELECT * FROM trace_imports WHERE run_id=? AND tenant_id=?", (run_id, tenant_id)).fetchone()
        if row is None:
            raise KeyError("imported trace not found")
        document, report = json.loads(row["document"]), json.loads(row["report"])
    if content_hash(document) != row["content_hash"]:
        raise ValueError("stored trace integrity check failed")
    actual_report_hash = content_hash({k: v for k, v in report.items() if k != "report_hash"})
    if actual_report_hash != report["report_hash"]:
        raise ValueError("stored inspection integrity check failed")
    return {"schema": "superturiya-trace-export-v1", "run_id": run_id, "created_at": row["created_at"], "content_hash": row["content_hash"], "record": copy.deepcopy(document), "report": report, "integrity_verified": True}
