from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Config:
    profile: str = "repair"
    seed: int = 2026
    max_actions: int = 800
    max_resets: int = 5
    game_seconds: float = 600
    total_seconds: float = 28800
    reserve_seconds: float = 120
    max_model_calls: int = 160
    model: str = ""
    endpoint: str = "http://127.0.0.1:8000/v1"
    request_seconds: float = 90
    max_tokens: int = 2048
    temperature: float = 0.2
    top_p: float = 0.95
    top_k: int = 20
    context_chars: int = 28000
    recent_transitions: int = 8
    max_tool_rounds: int = 2
    tool_seconds: float = 2
    max_program_chars: int = 12000
    min_rule_examples: int = 4
    plan_length: int = 4
    vision: bool = False
    enable_thinking: bool | None = None
    max_context_tokens: int = 32768
    max_parallel_games: int = 1

    def __post_init__(self):
        if self.profile not in {"random", "explore", "reactive", "memory", "repair"}:
            raise ValueError("unknown profile")
        positive = ("max_actions", "game_seconds", "total_seconds", "request_seconds",
                    "max_model_calls", "max_tokens", "context_chars", "recent_transitions",
                    "tool_seconds", "max_program_chars", "min_rule_examples", "plan_length",
                    "max_context_tokens", "top_p", "top_k", "max_parallel_games")
        for key in positive:
            value = getattr(self, key)
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{key} must be finite and positive")
        for key in ("seed", "max_actions", "max_resets", "max_model_calls", "max_tokens",
                    "context_chars", "recent_transitions", "max_tool_rounds", "max_program_chars",
                    "min_rule_examples", "plan_length", "max_context_tokens", "top_k",
                    "max_parallel_games"):
            if type(getattr(self, key)) is not int:
                raise ValueError(f"{key} must be an integer")
        if self.max_resets < 0 or not 0 <= self.max_tool_rounds <= 8:
            raise ValueError("invalid reset/tool limits")
        if self.context_chars < 6000 or self.min_rule_examples < 4 or self.plan_length > 8:
            raise ValueError("context >=6000, rule examples >=4, plan length <=8 required")
        if not math.isfinite(self.reserve_seconds) or not 0 <= self.reserve_seconds < self.total_seconds:
            raise ValueError("reserve must be below total runtime")
        if not math.isfinite(self.temperature) or not 0 <= self.temperature <= 2:
            raise ValueError("invalid temperature")
        if not math.isfinite(self.top_p) or not 0 < self.top_p <= 1:
            raise ValueError("top_p must be in (0, 1]")
        if self.max_parallel_games > 32:
            raise ValueError("max_parallel_games must be <= 32")
        if type(self.vision) is not bool or (self.enable_thinking is not None and type(self.enable_thinking) is not bool):
            raise ValueError("vision/enable_thinking must be booleans")
        if self.max_tokens >= self.max_context_tokens:
            raise ValueError("generation budget must be below context length")
        endpoint = urlsplit(self.endpoint)
        if (endpoint.scheme != "http" or endpoint.hostname not in {"127.0.0.1", "localhost", "::1"}
                or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment):
            raise ValueError("inference endpoint must be credential-free loopback HTTP")

    @classmethod
    def load(cls, path: str | Path):
        payload = json.loads(Path(path).read_text())
        if not isinstance(payload, dict):
            raise ValueError("configuration must be an object")
        unknown = set(payload) - {f.name for f in fields(cls)}
        if unknown:
            raise ValueError(f"unknown config fields: {sorted(unknown)}")
        return cls(**payload)

    def to_dict(self):
        return asdict(self)
