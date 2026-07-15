from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional


JsonDict = Dict[str, Any]


OBSERVATION_TYPES = {
    "message",
    "user_message",
    "assistant_message",
    "tool_call",
    "tool_result",
    "environment",
    "decision",
    "feedback",
    "policy_event",
    "memory_retrieval",
}

MEMORY_TYPES = {"episodic", "semantic", "profile", "procedural"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def json_dump(value: Any) -> str:
    return json.dumps(value if value is not None else {}, sort_keys=True, separators=(",", ":"))


def json_load(value: Any, default: Any = None) -> Any:
    if value is None or value == "":
        return {} if default is None else default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {} if default is None else default


def as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalized_key(value: str) -> str:
    cleaned = clean_text(value).lower()
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_")
    return cleaned or "unknown"


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def row_to_dict(row: Mapping[str, Any]) -> JsonDict:
    result: JsonDict = dict(row)
    for key in (
        "entities",
        "relations",
        "labels",
        "provenance",
        "derived_from",
        "graph_refs",
        "metadata",
        "memory_refs",
        "metrics",
        "root_cause_hypotheses",
        "derived_from_runs",
        "density_matrix",
        "latent_state",
        "interpretations",
        "relational_edges",
        "couplings",
        "learning_candidate",
        "full_report",
        "attrs",
    ):
        if key in result:
            result[key] = json_load(result[key], [] if key.endswith("s") else {})
    return result


@dataclass
class Observation:
    tenant_id: str
    subject_id: str
    content: str
    type: str = "message"
    source: str = "unknown"
    run_id: Optional[str] = None
    step_id: Optional[str] = None
    timestamp: str = field(default_factory=utc_now)
    observation_id: str = field(default_factory=lambda: new_id("obs"))
    entities: List[str] = field(default_factory=list)
    relations: List[JsonDict] = field(default_factory=list)
    labels: JsonDict = field(default_factory=dict)
    provenance: JsonDict = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "Observation":
        content = clean_text(payload.get("content"))
        if not content:
            raise ValueError("observation.content is required")

        observation_type = clean_text(payload.get("type") or "message")
        if observation_type not in OBSERVATION_TYPES:
            observation_type = "message"

        entities = [clean_text(item) for item in as_list(payload.get("entities")) if clean_text(item)]
        relations = [dict(item) for item in as_list(payload.get("relations")) if isinstance(item, dict)]

        return cls(
            tenant_id=clean_text(payload.get("tenant_id") or "default"),
            subject_id=clean_text(payload.get("subject_id") or "global"),
            observation_id=clean_text(payload.get("observation_id") or new_id("obs")),
            run_id=clean_text(payload.get("run_id")) or None,
            step_id=clean_text(payload.get("step_id")) or None,
            timestamp=clean_text(payload.get("timestamp") or utc_now()),
            type=observation_type,
            source=clean_text(payload.get("source") or "unknown"),
            content=content,
            entities=entities,
            relations=relations,
            labels=dict(payload.get("labels") or {}),
            provenance=dict(payload.get("provenance") or {}),
        )

    def to_record(self) -> JsonDict:
        return {
            "observation_id": self.observation_id,
            "tenant_id": self.tenant_id,
            "subject_id": self.subject_id,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "timestamp": self.timestamp,
            "type": self.type,
            "source": self.source,
            "content": self.content,
            "entities": json_dump(self.entities),
            "relations": json_dump(self.relations),
            "labels": json_dump(self.labels),
            "provenance": json_dump(self.provenance),
        }


def extract_capitalized_entities(text: str, max_entities: int = 6) -> List[str]:
    candidates = re.findall(r"\b[A-Z][a-zA-Z0-9_-]{2,}(?:\s+[A-Z][a-zA-Z0-9_-]{2,})?\b", text)
    ignored = {
        "The",
        "This",
        "That",
        "When",
        "User",
        "Agent",
        "Tool",
        "System",
        "Because",
    }
    result: List[str] = []
    for candidate in candidates:
        cleaned = clean_text(candidate)
        if cleaned in ignored or cleaned in result:
            continue
        result.append(cleaned)
        if len(result) >= max_entities:
            break
    return result


def token_set(text: str) -> set:
    stopwords = {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "into",
        "have",
        "has",
        "was",
        "were",
        "are",
        "but",
        "not",
        "you",
        "your",
        "user",
        "agent",
        "step",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]{3,}", text.lower())
        if token not in stopwords
    }


def mean(values: Iterable[float], default: float = 0.0) -> float:
    values = list(values)
    if not values:
        return default
    return sum(values) / len(values)
