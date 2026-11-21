from __future__ import annotations

from typing import Any, Mapping

from .evidence_integrity import sha256_json
from .models import JsonDict, clean_text, new_id, utc_now


CHANNELS = (
    "training_time_exposure",
    "evaluation_time_retrieval",
    "scaffold_leakage",
)
CHANNEL_STATES = {"O", "P", "C", "?"}


def build_integrity_card(payload: Mapping[str, Any]) -> JsonDict:
    evaluation_id = clean_text(payload.get("evaluation_id"))
    assessor_id = clean_text(payload.get("assessor_id"))
    if not evaluation_id or not assessor_id:
        raise ValueError("evaluation_id and assessor_id are required")

    revisions = dict(payload.get("revisions") or {})
    revision_fields = ("model", "code", "dataset", "runner")
    missing_revisions = [
        field for field in revision_fields if not clean_text(revisions.get(field))
    ]
    if missing_revisions:
        raise ValueError(
            "integrity card revisions missing: %s" % ", ".join(missing_revisions)
        )

    raw_channels = dict(payload.get("channels") or {})
    channels: JsonDict = {}
    for channel in CHANNELS:
        raw = dict(raw_channels.get(channel) or {})
        state = clean_text(raw.get("state") or "?").upper()
        if state not in CHANNEL_STATES:
            raise ValueError("invalid integrity state for %s: %s" % (channel, state))
        channels[channel] = {
            "state": state,
            "observed_facts": [
                clean_text(item)
                for item in raw.get("observed_facts") or []
                if clean_text(item)
            ],
            "evidence_refs": [
                clean_text(item)
                for item in raw.get("evidence_refs") or []
                if clean_text(item)
            ],
            "missing_evidence": [
                clean_text(item)
                for item in raw.get("missing_evidence") or []
                if clean_text(item)
            ],
        }
        if state in {"O", "P", "?"} and not channels[channel]["missing_evidence"]:
            raise ValueError(
                "%s state %s requires explicit missing_evidence" % (channel, state)
            )
        if state == "C" and not channels[channel]["evidence_refs"]:
            raise ValueError("closed channel %s requires evidence_refs" % channel)

    incident = dict(payload.get("incident") or {})
    confirmed = bool(incident.get("confirmed", False))
    susceptibility = clean_text(incident.get("susceptibility") or "unknown")
    if susceptibility not in {"unknown", "low", "medium", "high"}:
        raise ValueError("incident susceptibility must be unknown, low, medium, or high")
    card: JsonDict = {
        "card_id": clean_text(payload.get("card_id") or new_id("integrity")),
        "evaluation_id": evaluation_id,
        "assessor_id": assessor_id,
        "assessed_at": clean_text(payload.get("assessed_at") or utc_now()),
        "revisions": {field: clean_text(revisions[field]) for field in revision_fields},
        "channels": channels,
        "incident": {
            "confirmed": confirmed,
            "susceptibility": susceptibility,
            "description": clean_text(incident.get("description")),
            "evidence_refs": [
                clean_text(item)
                for item in incident.get("evidence_refs") or []
                if clean_text(item)
            ],
        },
        "score_impact": payload.get("score_impact"),
        "aggregate_cleanliness_score": None,
    }
    if confirmed and not card["incident"]["evidence_refs"]:
        raise ValueError("confirmed incident requires evidence_refs")
    card["card_hash"] = sha256_json(card)
    return card
