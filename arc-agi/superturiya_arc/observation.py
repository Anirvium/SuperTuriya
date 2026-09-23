from __future__ import annotations

import hashlib
import json
from collections import Counter, deque
from dataclasses import dataclass
from typing import Any


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def grid_value(value: Any) -> list[list[int]]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if not isinstance(value, list) or not value or len(value) > 64:
        raise ValueError("grid height must be 1..64")
    width = len(value[0])
    if not 1 <= width <= 64:
        raise ValueError("grid width must be 1..64")
    if any(not isinstance(row, list) or len(row) != width for row in value):
        raise ValueError("grid must be rectangular")
    if any(type(c) is not int or not 0 <= c <= 15 for row in value for c in row):
        raise ValueError("grid colors must be integers in 0..15")
    return value


def encode_grid_rle(grid: list[list[int]]) -> list[str]:
    """Losslessly encode each grid row as color x run-length pairs.

    This keeps the complete visual state available to the model without sending a
    64-by-64 JSON array on every decision.  The accompanying image remains useful
    for quick visual interpretation; this representation is the exact data.
    """
    grid_value(grid)
    rows = []
    for row in grid:
        runs, color, count = [], row[0], 0
        for value in row:
            if value == color:
                count += 1
            else:
                runs.append(f"{color}x{count}")
                color, count = value, 1
        runs.append(f"{color}x{count}")
        rows.append(",".join(runs))
    return rows


def decode_grid_rle(rows: list[str], width: int) -> list[list[int]]:
    """Decode ``encode_grid_rle``; used in tests to protect its lossless contract."""
    decoded = []
    for row in rows:
        values = []
        for run in row.split(","):
            color, count = run.split("x", 1)
            values.extend([int(color)] * int(count))
        if len(values) != width:
            raise ValueError("RLE row width mismatch")
        decoded.append(values)
    return grid_value(decoded)


@dataclass(frozen=True)
class Action:
    id: int
    x: int | None = None
    y: int | None = None

    @classmethod
    def parse(cls, payload: dict, available: tuple[int, ...]):
        if not isinstance(payload, dict) or set(payload) - {"id", "x", "y"}:
            raise ValueError("action must contain only id and optional x,y")
        action = payload.get("id")
        if type(action) is not int or action not in available:
            raise ValueError("action is not currently available")
        if action == 6:
            x, y = payload.get("x"), payload.get("y")
            if type(x) is not int or type(y) is not int or not (0 <= x < 64 and 0 <= y < 64):
                raise ValueError("click requires integer coordinates in 0..63")
            return cls(action, x, y)
        if "x" in payload or "y" in payload:
            raise ValueError("only ACTION6 accepts coordinates")
        return cls(action)

    def to_dict(self):
        return {"id": self.id, **({"x": self.x, "y": self.y} if self.id == 6 else {})}

    @property
    def key(self):
        return f"{self.id}:{self.x}:{self.y}"


@dataclass(frozen=True)
class Observation:
    grid: list[list[int]]
    state: str
    level: int
    available: tuple[int, ...]

    @classmethod
    def from_frame(cls, frame):
        if frame is None:
            raise ValueError("environment returned no frame; do not retry an uncertain action")
        state = getattr(frame.state, "name", str(frame.state))
        frames = frame.frame
        grid = grid_value(frames[-1]) if len(frames) else []
        available = tuple(sorted({int(getattr(a, "value", a)) for a in frame.available_actions}))
        available = tuple(a for a in available if 1 <= a <= 7)
        return cls(grid, state, int(frame.levels_completed), available)

    @property
    def key(self):
        # Include level/legal actions: visually identical boards may have different states.
        return digest(self.to_dict())

    def to_dict(self):
        return {"grid": self.grid, "state": self.state, "level": self.level,
                "available_actions": list(self.available)}


def objects(grid: list[list[int]], limit: int = 80) -> list[dict]:
    """Connected components are candidates, not assumed game objects."""
    if not grid:
        return []
    height, width = len(grid), len(grid[0])
    counts = Counter(c for row in grid for c in row)
    background = counts.most_common(1)[0][0]
    visited = set()
    result = []
    for y in range(height):
        for x in range(width):
            if (x, y) in visited:
                continue
            color = grid[y][x]
            queue, pixels = deque([(x, y)]), []
            visited.add((x, y))
            while queue:
                cx, cy = queue.popleft()
                pixels.append((cx, cy))
                for nx, ny in ((cx-1, cy), (cx+1, cy), (cx, cy-1), (cx, cy+1)):
                    if (0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited
                            and grid[ny][nx] == color):
                        visited.add((nx, ny))
                        queue.append((nx, ny))
            if color == background:
                continue
            xs, ys = zip(*pixels)
            # Pick a real member nearest the centroid (bbox center may be empty).
            mx, my = sum(xs)/len(xs), sum(ys)/len(ys)
            center = min(pixels, key=lambda p: (p[0]-mx)**2 + (p[1]-my)**2)
            result.append({"color": color, "area": len(pixels), "point": list(center),
                           "bbox": [min(xs), min(ys), max(xs), max(ys)]})
    return sorted(result, key=lambda o: (o["area"], o["color"], o["point"]))[:limit]


def delta(before: list, after: list) -> dict:
    if not before or not after or len(before) != len(after) or len(before[0]) != len(after[0]):
        return {"shape_changed": True}
    changes = [[x, y, a, b] for y, (ra, rb) in enumerate(zip(before, after))
               for x, (a, b) in enumerate(zip(ra, rb)) if a != b]
    return {"changed_cells": len(changes), "sample": changes[:64]}
