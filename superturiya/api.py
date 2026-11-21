from __future__ import annotations

import argparse
import hmac
import json
import mimetypes
import os
import threading
import time
from collections import deque
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence
from urllib.parse import parse_qs, unquote, urlparse

from .explainability import live_explainability_state
from .intelligence import SuperTuriyaEngine
from .sample_data import seed_demo
from .store import SuperTuriyaStore
from .trace_workspace import export_trace, import_trace, inspect_trace, normalize


class ApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


class SuperTuriyaHandler(BaseHTTPRequestHandler):
    engine: SuperTuriyaEngine
    static_root: Path
    api_token: Optional[str] = None
    scoped_principal_id: Optional[str] = None
    scoped_tenant_id: Optional[str] = None
    allowed_origins: Sequence[str] = ()
    max_body_bytes: int = 1_048_576
    rate_lock = threading.Lock()
    request_times: Dict[str, Any] = {}

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(15)

    server_version = "SuperTuriya/0.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._cors_headers()
        self._security_headers(api=True)
        self.end_headers()

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self._send_json({"ok": True, "service": "superturiya"})
                return
            if parsed.path == "/session":
                self._authenticate()
                self._send_json({"authenticated": True, "tenant_id": self.scoped_tenant_id or "hackathon", "principal_id": self.scoped_principal_id or "local-operator", "local_mode": not bool(self.api_token)})
                return
            if parsed.path.startswith("/workspace/"):
                self._authenticate()
                tenant = self.scoped_tenant_id or "hackathon"
                if parsed.path == "/workspace/runs":
                    with self.engine.store._lock:
                        rows = self.engine.store._connection.execute(
                            "SELECT t.*,i.content_hash,i.report FROM traces t JOIN trace_imports i ON t.run_id=i.run_id WHERE t.tenant_id=? ORDER BY i.created_at DESC LIMIT 100",
                            (tenant,),
                        ).fetchall()
                    runs = []
                    for row in rows:
                        item = dict(row)
                        item["metadata"] = json.loads(item["metadata"])
                        item["report"] = json.loads(item["report"])
                        runs.append(item)
                    self._send_json({"runs": runs, "limit": 100})
                    return
                if parsed.path.startswith("/workspace/runs/"):
                    identifier = unquote(parsed.path.removeprefix("/workspace/runs/"))
                    self._send_json(export_trace(self.engine.store, identifier, tenant))
                    return
                if parsed.path == "/workspace/audit":
                    self._send_json({"events": self.engine.store.list_audit(tenant, limit=100)})
                    return
                raise ApiError(HTTPStatus.NOT_FOUND, "unknown workspace endpoint")
            if parsed.path.startswith(("/dashboard/", "/hackathon/", "/traces/", "/evidence/", "/integrity/")):
                self._authenticate()
            if parsed.path == "/dashboard/state":
                query = parse_qs(parsed.query)
                tenant_id = self.scoped_tenant_id or query.get("tenant_id", ["demo"])[0]
                subject_id = query.get("subject_id", [None])[0] or None
                self._send_json(self.engine.dashboard_state(tenant_id, subject_id))
                return
            if parsed.path == "/hackathon/state":
                query = parse_qs(parsed.query)
                tenant_id = self.scoped_tenant_id or query.get("tenant_id", ["hackathon"])[0]
                self._send_json(self.engine.hackathon_state({"tenant_id": tenant_id}))
                return
            if parsed.path == "/hackathon/external-validity":
                self._send_json(live_explainability_state())
                return
            if parsed.path.startswith("/traces/"):
                run_id = unquote(parsed.path.split("/", 2)[2])
                trace = self.engine.store.get_trace(run_id)
                self._require_tenant(trace["run"])
                self._send_json(trace)
                return
            if parsed.path.startswith("/evidence/records/"):
                parts = parsed.path.strip("/").split("/")
                if len(parts) not in {3, 4}:
                    raise ApiError(HTTPStatus.NOT_FOUND, "unknown evidence endpoint")
                record_id = unquote(parts[2])
                if len(parts) == 4 and parts[3] == "raw":
                    record = self.engine.store.get_evidence_record(record_id)
                    self._require_tenant(record)
                    self._send_json(
                        {
                            "record_id": record_id,
                            "raw_sha256": record["raw_sha256"],
                            "raw_payload": record["raw_payload"],
                        },
                        extra_headers={
                            "content-disposition": 'attachment; filename="%s.raw.json"'
                            % record_id.replace('"', ""),
                        },
                    )
                    return
                if len(parts) == 3:
                    self._require_tenant(
                        self.engine.store.get_evidence_record(record_id)
                    )
                    self._send_json(self.engine.evidence_projection(record_id))
                    return
                raise ApiError(HTTPStatus.NOT_FOUND, "unknown evidence endpoint")
            if parsed.path == "/integrity/cards":
                query = parse_qs(parsed.query)
                tenant_id = self.scoped_tenant_id or query.get("tenant_id", ["default"])[0]
                evaluation_id = query.get("evaluation_id", [None])[0]
                self._send_json(
                    {
                        "cards": self.engine.store.list_integrity_cards(
                            tenant_id, evaluation_id
                        )
                    }
                )
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
            self._authenticate()
            payload = self._scope_payload(self._read_json())
            self._authorize_payload(payload)
            if payload.get("mode") == "live" and os.environ.get("SUPERTURIYA_ALLOW_LIVE_API") != "1":
                raise ApiError(HTTPStatus.FORBIDDEN, "live model calls require explicit server configuration")
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
                "/hackathon/repair-guided": self.engine.repair_guided_case,
                "/hackathon/repair-oracle": self.engine.repair_oracle_ceiling,
                "/evidence/records": self.engine.ingest_evidence,
                "/integrity/cards": self.engine.create_integrity_card,
                "/oversight/graph": self.engine.oversight_graph,
            }
            handler = routes.get(parsed.path)
            if not handler:
                if parsed.path == "/workspace/preview":
                    document = normalize(payload.get("record"))
                    self._send_json({"record": document, "report": inspect_trace(document)})
                    return
                if parsed.path == "/workspace/import":
                    payload["tenant_id"] = self.scoped_tenant_id or "hackathon"
                    payload["principal_id"] = self.scoped_principal_id or "local-operator"
                    self._send_json(import_trace(self.engine.store, payload))
                    return
                raise ApiError(HTTPStatus.NOT_FOUND, f"unknown endpoint: {parsed.path}")
            # Serialize authorization and mutations across this SQLite workspace.
            # This prevents duplicate concurrent lifecycle transitions.
            with self.engine.store._lock:
                self._authorize_payload(payload)
                result = handler(payload)
            self._send_json(result)
        except Exception as exc:
            self._handle_exception(exc)

    def do_DELETE(self) -> None:
        try:
            parsed = urlparse(self.path)
            self._authenticate()
            if not parsed.path.startswith("/subjects/"):
                raise ApiError(HTTPStatus.NOT_FOUND, f"unknown endpoint: {parsed.path}")
            subject_id = unquote(parsed.path.split("/", 2)[2])
            query = parse_qs(parsed.query)
            tenant_id = self.scoped_tenant_id or query.get("tenant_id", ["default"])[0]
            self._send_json(self.engine.forget_subject(tenant_id, subject_id))
        except Exception as exc:
            self._handle_exception(exc)

    def _read_json(self) -> Dict[str, Any]:
        try:
            length = int(self.headers.get("content-length", "0") or 0)
        except ValueError as exc:
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid content-length") from exc
        if length < 0:
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid content-length")
        if length > self.max_body_bytes:
            raise ApiError(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "request body exceeds %d bytes" % self.max_body_bytes,
            )
        if length == 0:
            return {}
        content_type = self.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise ApiError(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "content-type must be application/json")
        raw = self.rfile.read(length).decode("utf-8")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ApiError(HTTPStatus.BAD_REQUEST, f"invalid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ApiError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
        return parsed

    def _send_json(
        self,
        payload: Any,
        status: int = HTTPStatus.OK,
        head_only: bool = False,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self._cors_headers()
        self._security_headers(api=True)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
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
        self._security_headers(api=False)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    def _cors_headers(self) -> None:
        origin = clean_origin(self.headers.get("origin"))
        if origin and origin in set(self.allowed_origins):
            self.send_header("access-control-allow-origin", origin)
            self.send_header("vary", "Origin")
            self.send_header("access-control-allow-methods", "GET, POST, DELETE, OPTIONS")
            self.send_header("access-control-allow-headers", "authorization, content-type")

    def _security_headers(self, api: bool) -> None:
        self.send_header(
            "content-security-policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        )
        self.send_header("x-content-type-options", "nosniff")
        self.send_header("referrer-policy", "no-referrer")
        self.send_header("permissions-policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("cross-origin-opener-policy", "same-origin")
        self.send_header("cache-control", "no-store" if api else "no-cache")

    def _authenticate(self) -> None:
        origin = self.headers.get("origin")
        expected_origin = "http://" + self.headers.get("host", "")
        if origin and origin != expected_origin and origin not in self.allowed_origins:
            raise ApiError(HTTPStatus.FORBIDDEN, "origin is not allowed")
        if self.api_token:
            now = time.monotonic()
            key = self.client_address[0]
            with self.rate_lock:
                times = self.request_times.setdefault(key, deque())
                while times and times[0] < now - 60:
                    times.popleft()
                if len(times) >= 120:
                    raise ApiError(HTTPStatus.TOO_MANY_REQUESTS, "request limit reached; try again shortly")
                times.append(now)
        if not self.api_token:
            return
        header = self.headers.get("authorization", "")
        expected = "Bearer %s" % self.api_token
        if not hmac.compare_digest(header, expected):
            raise ApiError(HTTPStatus.UNAUTHORIZED, "valid bearer token required")

    def _scope_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        def bind(value: Any) -> Any:
            if isinstance(value, list):
                return [bind(item) for item in value]
            if not isinstance(value, dict):
                return value
            result = {key: (item if key in {"record", "metadata", "input", "output", "provenance"} else bind(item)) for key, item in value.items()}
            if self.scoped_tenant_id and "tenant_id" in result:
                result["tenant_id"] = self.scoped_tenant_id
            if self.scoped_principal_id:
                for key in ("principal_id", "reviewer_id"):
                    if key in result:
                        result[key] = self.scoped_principal_id
            return result
        scoped = bind(payload)
        if self.scoped_tenant_id:
            scoped["tenant_id"] = self.scoped_tenant_id
        if self.scoped_principal_id:
            scoped["principal_id"] = self.scoped_principal_id
            scoped["reviewer_id"] = self.scoped_principal_id
        return scoped

    def _authorize_payload(self, payload: Dict[str, Any]) -> None:
        """Check ownership for references AND caller-selected upsert identifiers."""
        if not self.scoped_tenant_id:
            return
        fields = {
            "run_id": ("traces", "run_id"),
            "policy_id": ("policies", "policy_id"),
            "intervention_id": ("interventions", "intervention_id"),
            "step_id": ("trace_steps", "step_id"),
            "parent_step_id": ("trace_steps", "step_id"),
            "observation_id": ("observations", "observation_id"),
            "memory_id": ("memories", "memory_id"),
            "record_id": ("evidence_records", "record_id"),
        }
        def visit(value: Any) -> None:
            if isinstance(value, list):
                for item in value:
                    visit(item)
            elif isinstance(value, dict):
                for key, item in value.items():
                    if key in fields and item:
                        table, column = fields[key]
                        owner = self.engine.store.record_owner(table, column, str(item))
                        if owner and owner != self.scoped_tenant_id:
                            raise ApiError(HTTPStatus.FORBIDDEN, "record is outside authenticated tenant scope")
                    elif key in {"observation_ids", "memory_refs"} and isinstance(item, list):
                        field = "observation_id" if key == "observation_ids" else "memory_id"
                        for identifier in item:
                            visit({field: identifier})
                    # Raw evidence is inert content, not an authorization request.
                    if key not in {"record", "metadata", "input", "output", "provenance"}:
                        visit(item)
        visit(payload)

    def _require_tenant(self, record: Mapping[str, Any]) -> None:
        record_tenant = str(record.get("tenant_id") or "").strip()
        if self.scoped_tenant_id and record_tenant != self.scoped_tenant_id:
            raise ApiError(HTTPStatus.FORBIDDEN, "record is outside authenticated tenant scope")

    def _handle_exception(self, exc: Exception) -> None:
        # A navigating/closing browser can reset a response mid-write. Sending a
        # second error response on that socket only produces another exception.
        if isinstance(exc, (BrokenPipeError, ConnectionResetError, TimeoutError)):
            return
        if isinstance(exc, ApiError):
            self._send_json({"error": exc.message}, exc.status)
            return
        if isinstance(exc, KeyError):
            self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
            return
        if isinstance(exc, ValueError):
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self._send_json({"error": "internal_error"}, HTTPStatus.INTERNAL_SERVER_ERROR)


def clean_origin(value: Any) -> str:
    origin = str(value or "").strip()
    if not origin or "\r" in origin or "\n" in origin:
        return ""
    return origin


def build_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    db_path: str = "var/superturiya.db",
    seed: bool = False,
    static_root: Optional[str] = None,
    api_token: Optional[str] = None,
    principal_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    allowed_origins: Optional[Sequence[str]] = None,
    max_body_bytes: int = 1_048_576,
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
    Handler.api_token = api_token if api_token is not None else os.environ.get("SUPERTURIYA_API_TOKEN")
    Handler.scoped_principal_id = principal_id or os.environ.get("SUPERTURIYA_API_PRINCIPAL")
    Handler.scoped_tenant_id = tenant_id or os.environ.get("SUPERTURIYA_API_TENANT")
    if Handler.api_token and not (Handler.scoped_principal_id and Handler.scoped_tenant_id):
        store.close()
        raise ValueError("authenticated servers require both principal and tenant scope")
    if host not in {"127.0.0.1", "localhost", "::1"} and not Handler.api_token:
        store.close()
        raise ValueError("non-loopback servers require scoped API authentication")
    Handler.rate_lock = threading.Lock()
    Handler.request_times = {}
    if allowed_origins is None:
        raw_origins = os.environ.get("SUPERTURIYA_ALLOWED_ORIGINS", "")
        Handler.allowed_origins = tuple(
            origin.strip() for origin in raw_origins.split(",") if origin.strip()
        )
    else:
        Handler.allowed_origins = tuple(allowed_origins)
    if max_body_bytes <= 0:
        raise ValueError("max_body_bytes must be positive")
    Handler.max_body_bytes = int(max_body_bytes)
    return ThreadingHTTPServer((host, port), Handler)


def main(argv: Optional[list] = None) -> None:
    parser = argparse.ArgumentParser(description="Run the SuperTuriya local product server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", default="var/superturiya.db")
    parser.add_argument("--seed", action="store_true")
    parser.add_argument("--principal", default=None)
    parser.add_argument("--tenant", default=None)
    parser.add_argument("--allowed-origin", action="append", default=None)
    parser.add_argument("--max-body-bytes", type=int, default=1_048_576)
    args = parser.parse_args(argv)

    server = build_server(
        args.host,
        args.port,
        args.db,
        args.seed,
        principal_id=args.principal,
        tenant_id=args.tenant,
        allowed_origins=args.allowed_origin,
        max_body_bytes=args.max_body_bytes,
    )
    url = f"http://{args.host}:{args.port}"
    print(f"SuperTuriya running at {url}")
    print(
        "API bearer authentication: %s"
        % ("enabled" if server.RequestHandlerClass.api_token else "disabled (local mode)")
    )
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSuperTuriya stopped.")


if __name__ == "__main__":
    main()
