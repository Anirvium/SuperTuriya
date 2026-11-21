"""Opt-in recording for arbitrary Python agent workflows; no network calls."""
from __future__ import annotations

import copy
import json
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import new_id
from .trace_workspace import SCHEMA, normalize, redact


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class RecordedSpan:
    def __init__(self, data: dict) -> None:
        self.data = data

    def output(self, value: Any) -> None:
        self.data["output"] = redact(copy.deepcopy(value))


class TraceRecorder:
    """Capture only explicitly supplied fields. Exception values are excluded."""
    def __init__(self, agent: str, goal: str) -> None:
        self.agent, self.goal = agent, goal
        self._spans: list = []
        self._lock = threading.RLock()
        self._parent: ContextVar = ContextVar("trace_parent_" + new_id("rec"), default=None)

    @contextmanager
    def span(self, name: str, kind: str = "step", input: Any = None, attributes: Any = None):
        data = {"span_id": new_id("span"), "parent_span_id": self._parent.get(), "name": name,
                "kind": kind, "status": "running", "input": redact(copy.deepcopy(input)), "output": None,
                "started_at": timestamp(), "attributes": redact(copy.deepcopy(attributes or {}))}
        with self._lock:
            if len(self._spans) >= 500:
                raise ValueError("recorder supports at most 500 spans per trace")
            self._spans.append(data)
        token = self._parent.set(data["span_id"])
        try:
            yield RecordedSpan(data)
            data["status"] = "completed"
        except BaseException as exc:
            data["status"] = "failed"
            data["attributes"]["exception_type"] = type(exc).__name__
            raise
        finally:
            data["ended_at"] = timestamp()
            self._parent.reset(token)

    def document(self, status: str = None) -> dict:
        with self._lock:
            spans = copy.deepcopy(self._spans)
        if status is None:
            status = "running" if any(s["status"] == "running" for s in spans) else "failed" if any(s["status"] == "failed" for s in spans) else "completed"
        return normalize({"schema": SCHEMA, "agent": self.agent, "goal": self.goal, "status": status, "spans": spans})

    def export(self, path: str, status: str = None) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(self.document(status), indent=2), encoding="utf-8")
        return destination
