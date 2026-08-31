from __future__ import annotations

import argparse
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, unquote, urlparse

from .explainability import live_explainability_state
from .intelligence import SuperTuriyaEngine
from .sample_data import seed_demo
from .store import SuperTuriyaStore


class ApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


class SuperTuriyaHandler(BaseHTTPRequestHandler):
    engine: SuperTuriyaEngine
    static_root: Path

    server_version = "SuperTuriya/0.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self._send_json({"ok": True, "service": "superturiya"})
                return
            if parsed.path == "/dashboard/state":
                query = parse_qs(parsed.query)
                tenant_id = query.get("tenant_id", ["demo"])[0]
                subject_id = query.get("subject_id", [None])[0] or None
                self._send_json(self.engine.dashboard_state(tenant_id, subject_id))
                return
            if parsed.path == "/hackathon/state":
                query = parse_qs(parsed.query)
                tenant_id = query.get("tenant_id", ["hackathon"])[0]
                self._send_json(self.engine.hackathon_state({"tenant_id": tenant_id}))
                return
            if parsed.path == "/hackathon/external-validity":
                self._send_json(live_explainability_state())
                return
            if parsed.path.startswith("/traces/"):
                run_id = unquote(parsed.path.split("/", 2)[2])
                self._send_json(self.engine.store.get_trace(run_id))
                return
            self._serve_static(parsed.path)
        except Exception as exc:
            self._handle_exception(exc)

    def do_HEAD(self) -> None:
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self._send_json({"ok": True, "service": "superturiya"}, head_only=True)
                return
            self._serve_static(parsed.path, head_only=True)
        except Exception as exc:
            self._handle_exception(exc)

    def do_POST(self) -> None:
        try:
            parsed = urlparse(self.path)
            payload = self._read_json()
            routes = {
                "/observations": self.engine.capture_observations,
                "/memories/extract": self.engine.extract_memories,
                "/memories/search": self.engine.search_memories,
                "/graphs/upsert": self.engine.upsert_graph,
                "/traces/start": self.engine.start_trace,
                "/traces/step": self.engine.record_step,
                "/trajectories/score": self.engine.score_trajectory,
                "/trajectories/counterfactuals": self.engine.counterfactuals,
                "/trajectories/quantum-interpret": self.engine.quantum_interpret_trajectory,
                "/trajectories/interpret": self.engine.quantum_interpret_trajectory,
                "/policies/synthesise": self.engine.synthesise_policies,
                "/policies/synthesize": self.engine.synthesise_policies,
                "/policies/review": self.engine.review_policy,
                "/hackathon/evaluate": self.engine.run_hackathon_evaluation,
                "/hackathon/cases/prepare": self.engine.prepare_hackathon_case,
                "/hackathon/interventions/review": self.engine.review_hackathon_intervention,
                "/hackathon/interventions/activate": self.engine.activate_hackathon_intervention,
            }
            handler = routes.get(parsed.path)
            if not handler:
                raise ApiError(HTTPStatus.NOT_FOUND, f"unknown endpoint: {parsed.path}")
            self._send_json(handler(payload))
        except Exception as exc:
            self._handle_exception(exc)

    def do_DELETE(self) -> None:
        try:
            parsed = urlparse(self.path)
            if not parsed.path.startswith("/subjects/"):
                raise ApiError(HTTPStatus.NOT_FOUND, f"unknown endpoint: {parsed.path}")
            subject_id = unquote(parsed.path.split("/", 2)[2])
            query = parse_qs(parsed.query)
            tenant_id = query.get("tenant_id", ["default"])[0]
            self._send_json(self.engine.forget_subject(tenant_id, subject_id))
        except Exception as exc:
            self._handle_exception(exc)

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("content-length", "0") or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ApiError(HTTPStatus.BAD_REQUEST, f"invalid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ApiError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
        return parsed

    def _send_json(self, payload: Any, status: int = HTTPStatus.OK, head_only: bool = False) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self._cors_headers()
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    def _serve_static(self, path: str, head_only: bool = False) -> None:
        if path in {"", "/"}:
            target = self.static_root / "index.html"
        else:
            target = (self.static_root / path.lstrip("/")).resolve()
            if self.static_root.resolve() not in target.parents and target != self.static_root.resolve():
                raise ApiError(HTTPStatus.FORBIDDEN, "static path outside web root")
        if not target.exists() or not target.is_file():
            raise ApiError(HTTPStatus.NOT_FOUND, f"not found: {path}")
        body = target.read_bytes()
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self._cors_headers()
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    def _cors_headers(self) -> None:
        self.send_header("access-control-allow-origin", "*")
        self.send_header("access-control-allow-methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("access-control-allow-headers", "content-type")

    def _handle_exception(self, exc: Exception) -> None:
        if isinstance(exc, ApiError):
            self._send_json({"error": exc.message}, exc.status)
            return
        if isinstance(exc, KeyError):
            self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
            return
        if isinstance(exc, ValueError):
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self._send_json({"error": "internal_error", "detail": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)


def build_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    db_path: str = "var/superturiya.db",
    seed: bool = False,
    static_root: Optional[str] = None,
) -> ThreadingHTTPServer:
    store = SuperTuriyaStore(db_path)
    engine = SuperTuriyaEngine(store)
    if seed:
        seed_demo(engine)
        if not store.list_evaluation_runs("hackathon", limit=1):
            engine.run_hackathon_evaluation({"mode": "frozen", "tenant_id": "hackathon"})

    root = Path(static_root or Path(__file__).resolve().parent.parent / "web").resolve()

    class Handler(SuperTuriyaHandler):
        pass

    Handler.engine = engine
    Handler.static_root = root
    return ThreadingHTTPServer((host, port), Handler)


def main(argv: Optional[list] = None) -> None:
    parser = argparse.ArgumentParser(description="Run the SuperTuriya local product server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", default="var/superturiya.db")
    parser.add_argument("--seed", action="store_true")
    args = parser.parse_args(argv)

    server = build_server(args.host, args.port, args.db, args.seed)
    url = f"http://{args.host}:{args.port}"
    print(f"SuperTuriya running at {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSuperTuriya stopped.")


if __name__ == "__main__":
    main()
