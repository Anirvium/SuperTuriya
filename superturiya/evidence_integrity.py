from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Any, Mapping, Optional, Sequence

from .models import JsonDict, clean_text, new_id


RENDERER_VERSION = "plain-text-projection-v1"
DEFAULT_DISPLAY_FIELDS = (
    "content",
    "input",
    "output",
    "summary",
    "root_cause",
    "rationale",
    "note",
    "evidence_refs",
)

HIDDEN_CODEPOINTS = {
    0x061C,
    0x200B,
    0x200C,
    0x200D,
    0x200E,
    0x200F,
    0x202A,
    0x202B,
    0x202C,
    0x202D,
    0x202E,
    0x2060,
    0x2061,
    0x2062,
    0x2063,
    0x2064,
    0x2066,
    0x2067,
    0x2068,
    0x2069,
    0xFEFF,
}


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def reveal_hidden_unicode(value: Any) -> Any:
    if isinstance(value, str):
        parts = []
        for character in value:
            codepoint = ord(character)
            category = unicodedata.category(character)
            hidden = codepoint in HIDDEN_CODEPOINTS or (
                category == "Cc" and character not in {"\n", "\r", "\t"}
            )
            if hidden:
                name = unicodedata.name(character, "CONTROL")
                parts.append("⟦U+%04X %s⟧" % (codepoint, name))
            else:
                parts.append(character)
        return "".join(parts)
    if isinstance(value, list):
        return [reveal_hidden_unicode(item) for item in value]
    if isinstance(value, tuple):
        return [reveal_hidden_unicode(item) for item in value]
    if isinstance(value, Mapping):
        return {
            clean_text(key): reveal_hidden_unicode(nested)
            for key, nested in value.items()
        }
    return value


def build_evidence_projection(
    raw_record: Mapping[str, Any],
    record_id: Optional[str] = None,
    display_fields: Optional[Sequence[str]] = None,
) -> JsonDict:
    raw = dict(raw_record)
    fields = [
        clean_text(field)
        for field in (display_fields or DEFAULT_DISPLAY_FIELDS)
        if clean_text(field)
    ]
    fields = list(dict.fromkeys(fields))
    display = {
        field: reveal_hidden_unicode(raw[field])
        for field in fields
        if field in raw
    }
    projection: JsonDict = {
        "record_id": clean_text(record_id or raw.get("record_id") or new_id("evidence")),
        "raw_sha256": sha256_json(raw),
        "renderer_version": RENDERER_VERSION,
        "display_fields": fields,
        "display": display,
    }
    projection["projection_sha256"] = sha256_json(projection)
    return projection


def verify_evidence_projection(
    raw_record: Mapping[str, Any], projection: Mapping[str, Any]
) -> JsonDict:
    expected_raw = sha256_json(dict(raw_record))
    without_hash = {
        key: value for key, value in dict(projection).items() if key != "projection_sha256"
    }
    expected_projection = sha256_json(without_hash)
    raw_matches = clean_text(projection.get("raw_sha256")) == expected_raw
    projection_matches = (
        clean_text(projection.get("projection_sha256")) == expected_projection
    )
    renderer_supported = (
        clean_text(projection.get("renderer_version")) == RENDERER_VERSION
    )
    return {
        "verified": raw_matches and projection_matches and renderer_supported,
        "raw_hash_matches": raw_matches,
        "projection_hash_matches": projection_matches,
        "renderer_supported": renderer_supported,
        "expected_raw_sha256": expected_raw,
        "expected_projection_sha256": expected_projection,
    }
