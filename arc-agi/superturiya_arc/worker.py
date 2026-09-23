"""Disposable compute worker. Deliberately restricted Python, not a security sandbox.

Only JSON data crosses the boundary; no game object, filesystem API, imports,
network API, or credentials are exposed. Run untrusted deployments in an OS
sandbox as well. This worker is for model-authored computation in our notebook.
"""
from __future__ import annotations

import ast
import json
import math
import sys

SAFE_METHODS = {"append", "extend", "pop", "get", "items", "keys", "values", "copy", "count",
                "index", "sort", "reverse", "add", "discard", "remove", "update", "setdefault",
                "intersection", "union", "difference", "issubset", "split", "join", "strip"}
SAFE_BUILTINS = {name: getattr(__builtins__, name) if not isinstance(__builtins__, dict)
                 else __builtins__[name] for name in (
                     "abs", "all", "any", "bool", "dict", "enumerate", "float", "int", "len",
                     "list", "max", "min", "range", "reversed", "round", "set", "sorted", "str",
                     "sum", "tuple", "zip", "isinstance", "ValueError")}


def validate(source: str):
    tree = ast.parse(source)
    forbidden = (ast.Import, ast.ImportFrom, ast.ClassDef, ast.Global, ast.Nonlocal,
                 ast.AsyncFunctionDef, ast.Await, ast.With, ast.AsyncWith)
    for node in ast.walk(tree):
        if isinstance(node, forbidden):
            raise ValueError(f"unsupported syntax: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id.startswith("_"):
            raise ValueError("private identifiers are unavailable")
        if isinstance(node, ast.Attribute) and node.attr not in SAFE_METHODS:
            raise ValueError(f"method unavailable: {node.attr}")
    return tree


def main():
    # Limits apply before parsing/evaluating generated programs.
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
        resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
        if sys.platform == "linux":
            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024**2, 512 * 1024**2))
    except (ImportError, OSError, ValueError):
        pass
    try:
        payload = json.loads(sys.stdin.read(2_000_001))
        source = payload["source"]
        if not isinstance(source, str) or len(source) > 16000:
            raise ValueError("program too large")
        namespace = {"__builtins__": SAFE_BUILTINS, "sqrt": math.sqrt}
        exec(compile(validate(source), "<agent-program>", "exec"), namespace)
        entry = payload["entry"]
        if entry not in {"analyze", "predict"} or not callable(namespace.get(entry)):
            raise ValueError("missing analyze(data) or predict(grid, action)")
        values = [namespace[entry](*args) for args in payload["calls"]]
        result = json.dumps({"ok": True, "values": values}, allow_nan=False)
        if len(result) > 500000:
            raise ValueError("program output exceeds limit")
        sys.stdout.write(result)
    except Exception as exc:
        sys.stdout.write(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:300]}"}))


if __name__ == "__main__":
    main()
