from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, List, Mapping, Optional

from .models import JsonDict, clean_text, utc_now


DECISIONS = {"yes", "no", "unresolved"}
INTENTS = {"current", "historical"}


def _as_strings(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [clean_text(value)] if clean_text(value) else []
    if isinstance(value, (list, tuple, set)):
        return [clean_text(item) for item in value if clean_text(item)]
    return []


def _parse_time(value: Any) -> Optional[datetime]:
    text = clean_text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class MemoryUseContext:
    tenant_id: str
    subject_id: str
    principal_id: str
    purpose: str
    intent: str
    policy_version: str
    workflow_state: str
    evaluated_at: str

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "MemoryUseContext":
        tenant_id = clean_text(payload.get("tenant_id") or "default")
        subject_id = clean_text(payload.get("subject_id"))
        if not subject_id:
            raise ValueError("subject_id is required for governed memory retrieval")
        principal_id = clean_text(payload.get("principal_id") or subject_id)
        purpose = clean_text(payload.get("purpose") or "assist_subject")
        policy_version = clean_text(payload.get("policy_version") or "v1")
        intent = clean_text(payload.get("intent") or "current").lower()
        if intent not in INTENTS:
            raise ValueError("memory intent must be current or historical")
        if not principal_id or not purpose or not policy_version:
            raise ValueError("principal_id, purpose, and policy_version are required")
        evaluated_at = clean_text(payload.get("evaluated_at") or utc_now())
        if _parse_time(evaluated_at) is None:
            raise ValueError("evaluated_at must be an ISO-8601 timestamp")
        return cls(
            tenant_id=tenant_id,
            subject_id=subject_id,
            principal_id=principal_id,
            purpose=purpose,
            intent=intent,
            policy_version=policy_version,
            workflow_state=clean_text(payload.get("workflow_state") or "unspecified"),
            evaluated_at=evaluated_at,
        )

    def to_dict(self) -> JsonDict:
        return {
            "tenant_id": self.tenant_id,
            "subject_id": self.subject_id,
            "principal_id": self.principal_id,
            "purpose": self.purpose,
            "intent": self.intent,
            "policy_version": self.policy_version,
            "workflow_state": self.workflow_state,
            "evaluated_at": self.evaluated_at,
        }


def _axis(decision: str, reasons: List[str]) -> JsonDict:
    if decision not in DECISIONS:
        raise ValueError("invalid memory admissibility decision: %s" % decision)
    return {"decision": decision, "reasons": reasons}


def _conjunction(axes: Mapping[str, Mapping[str, Any]]) -> str:
    decisions = [clean_text(axis.get("decision")) for axis in axes.values()]
    if "no" in decisions:
        return "no"
    if "unresolved" in decisions:
        return "unresolved"
    return "yes"


def evaluate_memory_admissibility(
    memory: Mapping[str, Any], context: MemoryUseContext
) -> JsonDict:
    metadata = dict(memory.get("metadata") or {})

    scope_reasons: List[str] = []
    scope_decision = "yes"
    if clean_text(memory.get("tenant_id")) != context.tenant_id:
        scope_decision = "no"
        scope_reasons.append("tenant mismatch")
    if clean_text(memory.get("subject_id")) != context.subject_id:
        scope_decision = "no"
        scope_reasons.append("subject mismatch")
    owner = clean_text(metadata.get("owner_principal_id") or memory.get("subject_id"))
    shared = set(_as_strings(metadata.get("shared_with_principals")))
    if context.principal_id != owner and context.principal_id not in shared:
        scope_decision = "no"
        scope_reasons.append("principal is neither owner nor explicitly shared")
    if not scope_reasons:
        scope_reasons.append("tenant, subject, and principal scope match")

    policy_reasons: List[str] = []
    authorization_state = clean_text(metadata.get("authorization_state") or "yes").lower()
    if authorization_state not in DECISIONS:
        authorization_state = "unresolved"
        policy_reasons.append("authorization state is invalid")
    policy_decision = authorization_state
    allowed_purposes = _as_strings(
        metadata.get("allowed_purposes", ["assist_subject"])
    )
    if not allowed_purposes:
        policy_decision = "unresolved"
        policy_reasons.append("allowed purposes are missing")
    elif context.purpose not in allowed_purposes and "*" not in allowed_purposes:
        policy_decision = "no"
        policy_reasons.append("purpose is not authorized")
    memory_policy = clean_text(metadata.get("policy_version") or "v1")
    if not memory_policy:
        if policy_decision != "no":
            policy_decision = "unresolved"
        policy_reasons.append("memory policy version is missing")
    elif memory_policy != context.policy_version:
        policy_decision = "no"
        policy_reasons.append("policy version mismatch")
    if not policy_reasons:
        policy_reasons.append("authorization, purpose, and policy version match")

    lifecycle_reasons: List[str] = []
    lifecycle_decision = "yes"
    state = clean_text(metadata.get("lifecycle_state") or "current").lower()
    if clean_text(memory.get("status") or "active").lower() != "active":
        lifecycle_decision = "no"
        lifecycle_reasons.append("memory record is not active")
    if state in {"forgotten", "quarantined", "revoked"}:
        lifecycle_decision = "no"
        lifecycle_reasons.append("lifecycle state forbids use")
    elif state == "superseded" and context.intent == "current":
        lifecycle_decision = "no"
        lifecycle_reasons.append("superseded memory is inadmissible for current intent")
    elif state not in {"current", "superseded", "historical"}:
        lifecycle_decision = "unresolved"
        lifecycle_reasons.append("lifecycle state is unknown")

    evaluated_at = _parse_time(context.evaluated_at)
    valid_from_raw = metadata.get("valid_from") or memory.get("created_at")
    valid_to_raw = metadata.get("valid_to") or memory.get("expires_at")
    valid_from = _parse_time(valid_from_raw)
    valid_to = _parse_time(valid_to_raw)
    if valid_from_raw and valid_from is None:
        lifecycle_decision = "unresolved"
        lifecycle_reasons.append("valid_from is malformed")
    elif valid_from and evaluated_at and evaluated_at < valid_from:
        lifecycle_decision = "no"
        lifecycle_reasons.append("memory is not yet valid")
    if valid_to_raw and valid_to is None:
        lifecycle_decision = "unresolved"
        lifecycle_reasons.append("valid_to is malformed")
    elif valid_to and evaluated_at and evaluated_at > valid_to:
        lifecycle_decision = "no"
        lifecycle_reasons.append("memory validity has expired")
    if not lifecycle_reasons:
        lifecycle_reasons.append("lifecycle and validity window permit use")

    axes = {
        "scope": _axis(scope_decision, scope_reasons),
        "policy": _axis(policy_decision, policy_reasons),
        "lifecycle": _axis(lifecycle_decision, lifecycle_reasons),
    }
    decision = _conjunction(axes)
    return {
        "memory_id": memory["memory_id"],
        "decision": decision,
        "axes": axes,
        "fail_closed": decision != "yes",
    }
