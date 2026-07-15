from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .models import JsonDict, Observation, clean_text, json_dump, json_load, new_id, normalized_key, row_to_dict, utc_now


class SuperTuriyaStore:
    """SQLite-backed control plane, trace ledger, and local graph store."""

    def __init__(self, db_path: str = "var/superturiya.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self.initialize()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def initialize(self) -> None:
        with self._lock:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS observations (
                    observation_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    run_id TEXT,
                    step_id TEXT,
                    timestamp TEXT NOT NULL,
                    type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    content TEXT NOT NULL,
                    entities TEXT NOT NULL,
                    relations TEXT NOT NULL,
                    labels TEXT NOT NULL,
                    provenance TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    text TEXT NOT NULL,
                    derived_from TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT,
                    graph_refs TEXT NOT NULL,
                    vector_ref TEXT NOT NULL,
                    metadata TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS graph_nodes (
                    node_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    label TEXT NOT NULL,
                    attrs TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS graph_edges (
                    edge_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    from_node TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    to_node TEXT NOT NULL,
                    valid_at TEXT NOT NULL,
                    invalid_at TEXT,
                    confidence REAL NOT NULL,
                    derived_from TEXT NOT NULL,
                    attrs TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS traces (
                    run_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    status TEXT NOT NULL,
                    metadata TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS trace_steps (
                    step_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    parent_step_id TEXT,
                    step_index INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    source TEXT NOT NULL,
                    input TEXT NOT NULL,
                    output TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    memory_refs TEXT NOT NULL,
                    tool_call_id TEXT,
                    metadata TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS trajectory_scores (
                    score_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    utility REAL NOT NULL,
                    metrics TEXT NOT NULL,
                    root_cause_hypotheses TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS quantum_trajectory_reports (
                    report_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    dominant_label TEXT NOT NULL,
                    common_label TEXT NOT NULL,
                    entropy REAL NOT NULL,
                    ambiguity_level TEXT NOT NULL,
                    density_matrix TEXT NOT NULL,
                    latent_state TEXT NOT NULL,
                    interpretations TEXT NOT NULL,
                    relational_edges TEXT NOT NULL,
                    couplings TEXT NOT NULL,
                    learning_candidate TEXT NOT NULL,
                    recommendation TEXT NOT NULL,
                    full_report TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS policies (
                    policy_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    subject_id TEXT,
                    kind TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    derived_from_runs TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    subject_id TEXT,
                    action TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_id TEXT,
                    created_at TEXT NOT NULL,
                    metadata TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_observations_scope
                    ON observations (tenant_id, subject_id, timestamp);
                CREATE INDEX IF NOT EXISTS idx_observations_run
                    ON observations (run_id, step_id);
                CREATE INDEX IF NOT EXISTS idx_memories_scope
                    ON memories (tenant_id, subject_id, memory_type, status);
                CREATE INDEX IF NOT EXISTS idx_graph_edges_scope
                    ON graph_edges (tenant_id, subject_id, relation_type);
                CREATE INDEX IF NOT EXISTS idx_trace_steps_run
                    ON trace_steps (run_id, step_index);
                CREATE INDEX IF NOT EXISTS idx_scores_run
                    ON trajectory_scores (run_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_quantum_reports_scope
                    ON quantum_trajectory_reports (tenant_id, subject_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_quantum_reports_run
                    ON quantum_trajectory_reports (run_id, created_at);
                """
            )
            self._connection.commit()

    def add_audit(
        self,
        tenant_id: str,
        action: str,
        target_type: str,
        target_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> JsonDict:
        event = {
            "event_id": new_id("aud"),
            "tenant_id": tenant_id,
            "subject_id": subject_id,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "created_at": utc_now(),
            "metadata": json_dump(dict(metadata or {})),
        }
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO audit_events
                (event_id, tenant_id, subject_id, action, target_type, target_id, created_at, metadata)
                VALUES
                (:event_id, :tenant_id, :subject_id, :action, :target_type, :target_id, :created_at, :metadata)
                """,
                event,
            )
            self._connection.commit()
        return {**event, "metadata": json_load(event["metadata"])}

    def add_observations(self, payloads: Sequence[Mapping[str, Any]]) -> List[JsonDict]:
        observations = [Observation.from_payload(payload) for payload in payloads]
        records = [observation.to_record() for observation in observations]
        with self._lock:
            self._connection.executemany(
                """
                INSERT OR REPLACE INTO observations
                (observation_id, tenant_id, subject_id, run_id, step_id, timestamp, type, source,
                 content, entities, relations, labels, provenance)
                VALUES
                (:observation_id, :tenant_id, :subject_id, :run_id, :step_id, :timestamp, :type,
                 :source, :content, :entities, :relations, :labels, :provenance)
                """,
                records,
            )
            self._connection.commit()
        for observation in observations:
            self.add_audit(
                observation.tenant_id,
                "observation.capture",
                "observation",
                observation.observation_id,
                observation.subject_id,
                {"type": observation.type, "source": observation.source},
            )
        return [self.get_observation(record["observation_id"]) for record in records]

    def get_observation(self, observation_id: str) -> JsonDict:
        row = self._connection.execute(
            "SELECT * FROM observations WHERE observation_id = ?",
            (observation_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"observation not found: {observation_id}")
        return row_to_dict(row)

    def list_observations(
        self,
        tenant_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        run_id: Optional[str] = None,
        observation_ids: Optional[Sequence[str]] = None,
        limit: int = 100,
        ascending: bool = False,
    ) -> List[JsonDict]:
        clauses: List[str] = []
        params: List[Any] = []
        if tenant_id:
            clauses.append("tenant_id = ?")
            params.append(tenant_id)
        if subject_id:
            clauses.append("subject_id = ?")
            params.append(subject_id)
        if run_id:
            clauses.append("run_id = ?")
            params.append(run_id)
        if observation_ids:
            placeholders = ",".join("?" for _ in observation_ids)
            clauses.append(f"observation_id IN ({placeholders})")
            params.extend(observation_ids)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        order = "ASC" if ascending else "DESC"
        params.append(limit)
        rows = self._connection.execute(
            f"SELECT * FROM observations {where} ORDER BY timestamp {order} LIMIT ?",
            params,
        ).fetchall()
        return [row_to_dict(row) for row in rows]

    def add_memory(self, payload: Mapping[str, Any]) -> JsonDict:
        now = utc_now()
        memory_id = clean_text(payload.get("memory_id") or new_id("mem"))
        record = {
            "memory_id": memory_id,
            "tenant_id": clean_text(payload.get("tenant_id") or "default"),
            "subject_id": clean_text(payload.get("subject_id") or "global"),
            "memory_type": clean_text(payload.get("memory_type") or "episodic"),
            "text": clean_text(payload.get("text")),
            "derived_from": json_dump(payload.get("derived_from") or []),
            "confidence": float(payload.get("confidence", 0.65)),
            "status": clean_text(payload.get("status") or "active"),
            "created_at": clean_text(payload.get("created_at") or now),
            "updated_at": clean_text(payload.get("updated_at") or now),
            "expires_at": clean_text(payload.get("expires_at")) or None,
            "graph_refs": json_dump(payload.get("graph_refs") or []),
            "vector_ref": clean_text(payload.get("vector_ref") or f"local:memories/{memory_id}"),
            "metadata": json_dump(payload.get("metadata") or {}),
        }
        if not record["text"]:
            raise ValueError("memory.text is required")
        with self._lock:
            self._connection.execute(
                """
                INSERT OR REPLACE INTO memories
                (memory_id, tenant_id, subject_id, memory_type, text, derived_from, confidence,
                 status, created_at, updated_at, expires_at, graph_refs, vector_ref, metadata)
                VALUES
                (:memory_id, :tenant_id, :subject_id, :memory_type, :text, :derived_from,
                 :confidence, :status, :created_at, :updated_at, :expires_at, :graph_refs,
                 :vector_ref, :metadata)
                """,
                record,
            )
            self._connection.commit()
        self.add_audit(
            record["tenant_id"],
            "memory.write",
            "memory",
            memory_id,
            record["subject_id"],
            {"memory_type": record["memory_type"], "confidence": record["confidence"]},
        )
        return self.get_memory(memory_id)

    def get_memory(self, memory_id: str) -> JsonDict:
        row = self._connection.execute("SELECT * FROM memories WHERE memory_id = ?", (memory_id,)).fetchone()
        if row is None:
            raise KeyError(f"memory not found: {memory_id}")
        return row_to_dict(row)

    def list_memories(
        self,
        tenant_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        memory_types: Optional[Sequence[str]] = None,
        status: str = "active",
        limit: int = 200,
    ) -> List[JsonDict]:
        clauses: List[str] = []
        params: List[Any] = []
        if tenant_id:
            clauses.append("tenant_id = ?")
            params.append(tenant_id)
        if subject_id:
            clauses.append("subject_id = ?")
            params.append(subject_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if memory_types:
            placeholders = ",".join("?" for _ in memory_types)
            clauses.append(f"memory_type IN ({placeholders})")
            params.extend(memory_types)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        rows = self._connection.execute(
            f"SELECT * FROM memories {where} ORDER BY updated_at DESC LIMIT ?",
            params,
        ).fetchall()
        return [row_to_dict(row) for row in rows]

    def upsert_graph(
        self,
        tenant_id: str,
        subject_id: str,
        entities: Sequence[str],
        relations: Sequence[Mapping[str, Any]],
        derived_from: Optional[Sequence[str]] = None,
    ) -> JsonDict:
        now = utc_now()
        created_nodes = 0
        created_edges = 0
        derived = list(derived_from or [])

        def node_id_for(label: str) -> str:
            return f"node:{tenant_id}:{subject_id}:{normalized_key(label)}"

        with self._lock:
            for label in entities:
                label = clean_text(label)
                if not label:
                    continue
                node_id = node_id_for(label)
                existing = self._connection.execute(
                    "SELECT node_id FROM graph_nodes WHERE node_id = ?",
                    (node_id,),
                ).fetchone()
                if existing:
                    self._connection.execute(
                        "UPDATE graph_nodes SET last_seen_at = ? WHERE node_id = ?",
                        (now, node_id),
                    )
                else:
                    self._connection.execute(
                        """
                        INSERT INTO graph_nodes
                        (node_id, tenant_id, subject_id, kind, label, attrs, first_seen_at, last_seen_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            node_id,
                            tenant_id,
                            subject_id,
                            "entity",
                            label,
                            json_dump({"normalized": normalized_key(label)}),
                            now,
                            now,
                        ),
                    )
                    created_nodes += 1

            for relation in relations:
                from_label = clean_text(relation.get("from"))
                to_label = clean_text(relation.get("to"))
                relation_type = clean_text(relation.get("type") or relation.get("relation_type") or "RELATED_TO")
                if not from_label or not to_label:
                    continue
                for label in (from_label, to_label):
                    node_id = node_id_for(label)
                    existing = self._connection.execute(
                        "SELECT node_id FROM graph_nodes WHERE node_id = ?",
                        (node_id,),
                    ).fetchone()
                    if not existing:
                        self._connection.execute(
                            """
                            INSERT INTO graph_nodes
                            (node_id, tenant_id, subject_id, kind, label, attrs, first_seen_at, last_seen_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                node_id,
                                tenant_id,
                                subject_id,
                                "entity",
                                label,
                                json_dump({"normalized": normalized_key(label)}),
                                now,
                                now,
                            ),
                        )
                        created_nodes += 1
                edge_id = (
                    f"edge:{tenant_id}:{subject_id}:{normalized_key(from_label)}:"
                    f"{normalized_key(relation_type)}:{normalized_key(to_label)}"
                )
                record = {
                    "edge_id": edge_id,
                    "tenant_id": tenant_id,
                    "subject_id": subject_id,
                    "from_node": node_id_for(from_label),
                    "relation_type": relation_type.upper(),
                    "to_node": node_id_for(to_label),
                    "valid_at": clean_text(relation.get("valid_at") or now),
                    "invalid_at": clean_text(relation.get("invalid_at")) or None,
                    "confidence": float(relation.get("confidence", 0.62)),
                    "derived_from": json_dump(relation.get("derived_from") or derived),
                    "attrs": json_dump({k: v for k, v in relation.items() if k not in {"from", "to", "type"}}),
                }
                existing_edge = self._connection.execute(
                    "SELECT edge_id FROM graph_edges WHERE edge_id = ?",
                    (edge_id,),
                ).fetchone()
                if existing_edge:
                    self._connection.execute(
                        """
                        UPDATE graph_edges
                        SET valid_at = :valid_at, invalid_at = :invalid_at, confidence = :confidence,
                            derived_from = :derived_from, attrs = :attrs
                        WHERE edge_id = :edge_id
                        """,
                        record,
                    )
                else:
                    self._connection.execute(
                        """
                        INSERT INTO graph_edges
                        (edge_id, tenant_id, subject_id, from_node, relation_type, to_node,
                         valid_at, invalid_at, confidence, derived_from, attrs)
                        VALUES
                        (:edge_id, :tenant_id, :subject_id, :from_node, :relation_type, :to_node,
                         :valid_at, :invalid_at, :confidence, :derived_from, :attrs)
                        """,
                        record,
                    )
                    created_edges += 1
            self._connection.commit()
        if created_nodes or created_edges:
            self.add_audit(
                tenant_id,
                "graph.upsert",
                "graph",
                subject_id=subject_id,
                metadata={"nodes": created_nodes, "edges": created_edges},
            )
        return {"nodes_created": created_nodes, "edges_created": created_edges}

    def list_graph(
        self, tenant_id: Optional[str] = None, subject_id: Optional[str] = None, limit: int = 200
    ) -> JsonDict:
        clauses: List[str] = []
        params: List[Any] = []
        if tenant_id:
            clauses.append("tenant_id = ?")
            params.append(tenant_id)
        if subject_id:
            clauses.append("subject_id = ?")
            params.append(subject_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows_nodes = self._connection.execute(
            f"SELECT * FROM graph_nodes {where} ORDER BY last_seen_at DESC LIMIT ?",
            [*params, limit],
        ).fetchall()
        rows_edges = self._connection.execute(
            f"SELECT * FROM graph_edges {where} ORDER BY valid_at DESC LIMIT ?",
            [*params, limit],
        ).fetchall()
        return {
            "nodes": [row_to_dict(row) for row in rows_nodes],
            "edges": [row_to_dict(row) for row in rows_edges],
        }

    def start_trace(self, payload: Mapping[str, Any]) -> JsonDict:
        now = utc_now()
        record = {
            "run_id": clean_text(payload.get("run_id") or new_id("run")),
            "tenant_id": clean_text(payload.get("tenant_id") or "default"),
            "subject_id": clean_text(payload.get("subject_id") or "global"),
            "agent_id": clean_text(payload.get("agent_id") or "agent"),
            "goal": clean_text(payload.get("goal") or "Unspecified goal"),
            "started_at": clean_text(payload.get("started_at") or now),
            "ended_at": clean_text(payload.get("ended_at")) or None,
            "status": clean_text(payload.get("status") or "running"),
            "metadata": json_dump(payload.get("metadata") or {}),
        }
        with self._lock:
            self._connection.execute(
                """
                INSERT OR REPLACE INTO traces
                (run_id, tenant_id, subject_id, agent_id, goal, started_at, ended_at, status, metadata)
                VALUES
                (:run_id, :tenant_id, :subject_id, :agent_id, :goal, :started_at, :ended_at,
                 :status, :metadata)
                """,
                record,
            )
            self._connection.commit()
        self.add_audit(
            record["tenant_id"],
            "trace.start",
            "trace",
            record["run_id"],
            record["subject_id"],
            {"agent_id": record["agent_id"]},
        )
        return self.get_trace(record["run_id"])["run"]

    def add_trace_step(self, payload: Mapping[str, Any]) -> JsonDict:
        run_id = clean_text(payload.get("run_id"))
        if not run_id:
            raise ValueError("step.run_id is required")
        run = self.get_trace(run_id)["run"]
        with self._lock:
            next_index = self._connection.execute(
                "SELECT COALESCE(MAX(step_index), 0) + 1 FROM trace_steps WHERE run_id = ?",
                (run_id,),
            ).fetchone()[0]
            record = {
                "step_id": clean_text(payload.get("step_id") or new_id("step")),
                "run_id": run_id,
                "tenant_id": run["tenant_id"],
                "subject_id": run["subject_id"],
                "parent_step_id": clean_text(payload.get("parent_step_id")) or None,
                "step_index": int(payload.get("step_index") or next_index),
                "kind": clean_text(payload.get("kind") or "decision"),
                "source": clean_text(payload.get("source") or run["agent_id"]),
                "input": clean_text(payload.get("input")),
                "output": clean_text(payload.get("output")),
                "status": clean_text(payload.get("status") or "completed"),
                "started_at": clean_text(payload.get("started_at") or utc_now()),
                "ended_at": clean_text(payload.get("ended_at")) or None,
                "memory_refs": json_dump(payload.get("memory_refs") or []),
                "tool_call_id": clean_text(payload.get("tool_call_id")) or None,
                "metadata": json_dump(payload.get("metadata") or {}),
            }
            self._connection.execute(
                """
                INSERT OR REPLACE INTO trace_steps
                (step_id, run_id, tenant_id, subject_id, parent_step_id, step_index, kind, source,
                 input, output, status, started_at, ended_at, memory_refs, tool_call_id, metadata)
                VALUES
                (:step_id, :run_id, :tenant_id, :subject_id, :parent_step_id, :step_index, :kind,
                 :source, :input, :output, :status, :started_at, :ended_at, :memory_refs,
                 :tool_call_id, :metadata)
                """,
                record,
            )
            if payload.get("trace_status"):
                self._connection.execute(
                    "UPDATE traces SET status = ?, ended_at = COALESCE(ended_at, ?) WHERE run_id = ?",
                    (clean_text(payload.get("trace_status")), utc_now(), run_id),
                )
            self._connection.commit()
        self.add_audit(
            record["tenant_id"],
            "trace.step",
            "trace_step",
            record["step_id"],
            record["subject_id"],
            {"run_id": run_id, "kind": record["kind"], "status": record["status"]},
        )
        return self.get_step(record["step_id"])

    def get_step(self, step_id: str) -> JsonDict:
        row = self._connection.execute("SELECT * FROM trace_steps WHERE step_id = ?", (step_id,)).fetchone()
        if row is None:
            raise KeyError(f"step not found: {step_id}")
        return row_to_dict(row)

    def get_trace(self, run_id: str) -> JsonDict:
        run = self._connection.execute("SELECT * FROM traces WHERE run_id = ?", (run_id,)).fetchone()
        if run is None:
            raise KeyError(f"trace not found: {run_id}")
        steps = self._connection.execute(
            "SELECT * FROM trace_steps WHERE run_id = ? ORDER BY step_index ASC",
            (run_id,),
        ).fetchall()
        scores = self._connection.execute(
            "SELECT * FROM trajectory_scores WHERE run_id = ? ORDER BY created_at DESC",
            (run_id,),
        ).fetchall()
        return {
            "run": row_to_dict(run),
            "steps": [row_to_dict(row) for row in steps],
            "scores": [row_to_dict(row) for row in scores],
        }

    def list_traces(
        self, tenant_id: Optional[str] = None, subject_id: Optional[str] = None, limit: int = 50
    ) -> List[JsonDict]:
        clauses: List[str] = []
        params: List[Any] = []
        if tenant_id:
            clauses.append("tenant_id = ?")
            params.append(tenant_id)
        if subject_id:
            clauses.append("subject_id = ?")
            params.append(subject_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._connection.execute(
            f"SELECT * FROM traces {where} ORDER BY started_at DESC LIMIT ?",
            [*params, limit],
        ).fetchall()
        return [row_to_dict(row) for row in rows]

    def save_score(
        self,
        run_id: str,
        tenant_id: str,
        subject_id: str,
        utility: float,
        metrics: Mapping[str, Any],
        root_causes: Sequence[Mapping[str, Any]],
    ) -> JsonDict:
        record = {
            "score_id": new_id("score"),
            "run_id": run_id,
            "tenant_id": tenant_id,
            "subject_id": subject_id,
            "utility": float(utility),
            "metrics": json_dump(dict(metrics)),
            "root_cause_hypotheses": json_dump(list(root_causes)),
            "created_at": utc_now(),
        }
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO trajectory_scores
                (score_id, run_id, tenant_id, subject_id, utility, metrics,
                 root_cause_hypotheses, created_at)
                VALUES
                (:score_id, :run_id, :tenant_id, :subject_id, :utility, :metrics,
                 :root_cause_hypotheses, :created_at)
                """,
                record,
            )
            self._connection.commit()
        self.add_audit(
            tenant_id,
            "trajectory.score",
            "trajectory_score",
            record["score_id"],
            subject_id,
            {"run_id": run_id, "utility": utility},
        )
        return row_to_dict(record)

    def save_quantum_report(self, report: Mapping[str, Any]) -> JsonDict:
        report_id = clean_text(report.get("report_id") or new_id("qtraj"))
        dominant = dict(report.get("dominant_interpretation") or {})
        common = dict(report.get("common_interpretation") or {})
        record = {
            "report_id": report_id,
            "run_id": clean_text(report.get("run_id") or report.get("trajectory_id")),
            "tenant_id": clean_text(report.get("tenant_id") or "default"),
            "subject_id": clean_text(report.get("subject_id") or "global"),
            "dominant_label": clean_text(dominant.get("label") or "unknown"),
            "common_label": clean_text(common.get("label") or "unknown"),
            "entropy": float(report.get("trajectory_entropy", 0.0)),
            "ambiguity_level": clean_text(report.get("ambiguity_level") or "unknown"),
            "density_matrix": json_dump(report.get("density_matrix") or {}),
            "latent_state": json_dump(report.get("latent_state") or {}),
            "interpretations": json_dump(
                {
                    "dominant_interpretation": dominant,
                    "common_interpretation": common,
                    "minor_interpretations": report.get("minor_interpretations") or [],
                    "contextual_measurements": report.get("contextual_measurements") or {},
                }
            ),
            "relational_edges": json_dump(report.get("relational_edges") or []),
            "couplings": json_dump(report.get("relational_couplings") or []),
            "learning_candidate": json_dump(report.get("learning_candidate") or {}),
            "recommendation": clean_text(report.get("self_improvement_recommendation")),
            "full_report": json_dump({**dict(report), "report_id": report_id}),
            "created_at": clean_text(report.get("created_at") or utc_now()),
        }
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO quantum_trajectory_reports
                (report_id, run_id, tenant_id, subject_id, dominant_label, common_label,
                 entropy, ambiguity_level, density_matrix, latent_state, interpretations,
                 relational_edges, couplings, learning_candidate, recommendation,
                 full_report, created_at)
                VALUES
                (:report_id, :run_id, :tenant_id, :subject_id, :dominant_label, :common_label,
                 :entropy, :ambiguity_level, :density_matrix, :latent_state, :interpretations,
                 :relational_edges, :couplings, :learning_candidate, :recommendation,
                 :full_report, :created_at)
                """,
                record,
            )
            self._connection.commit()
        self.add_audit(
            record["tenant_id"],
            "trajectory.quantum_interpret",
            "quantum_trajectory_report",
            report_id,
            record["subject_id"],
            {
                "run_id": record["run_id"],
                "dominant_label": record["dominant_label"],
                "ambiguity_level": record["ambiguity_level"],
            },
        )
        return self.get_quantum_report(report_id)

    def get_quantum_report(self, report_id: str) -> JsonDict:
        row = self._connection.execute(
            "SELECT * FROM quantum_trajectory_reports WHERE report_id = ?",
            (report_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"quantum trajectory report not found: {report_id}")
        return row_to_dict(row)

    def list_quantum_reports(
        self,
        tenant_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        run_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[JsonDict]:
        clauses: List[str] = []
        params: List[Any] = []
        if tenant_id:
            clauses.append("tenant_id = ?")
            params.append(tenant_id)
        if subject_id:
            clauses.append("subject_id = ?")
            params.append(subject_id)
        if run_id:
            clauses.append("run_id = ?")
            params.append(run_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._connection.execute(
            f"SELECT * FROM quantum_trajectory_reports {where} ORDER BY created_at DESC LIMIT ?",
            [*params, limit],
        ).fetchall()
        return [row_to_dict(row) for row in rows]

    def add_policy(self, payload: Mapping[str, Any]) -> JsonDict:
        now = utc_now()
        record = {
            "policy_id": clean_text(payload.get("policy_id") or new_id("pol")),
            "tenant_id": clean_text(payload.get("tenant_id") or "default"),
            "subject_id": clean_text(payload.get("subject_id")) or None,
            "kind": clean_text(payload.get("kind") or "routing"),
            "title": clean_text(payload.get("title") or "Untitled policy"),
            "body": clean_text(payload.get("body")),
            "derived_from_runs": json_dump(payload.get("derived_from_runs") or []),
            "confidence": float(payload.get("confidence", 0.7)),
            "status": clean_text(payload.get("status") or "active"),
            "created_at": clean_text(payload.get("created_at") or now),
            "updated_at": clean_text(payload.get("updated_at") or now),
        }
        if not record["body"]:
            raise ValueError("policy.body is required")
        with self._lock:
            self._connection.execute(
                """
                INSERT OR REPLACE INTO policies
                (policy_id, tenant_id, subject_id, kind, title, body, derived_from_runs,
                 confidence, status, created_at, updated_at)
                VALUES
                (:policy_id, :tenant_id, :subject_id, :kind, :title, :body, :derived_from_runs,
                 :confidence, :status, :created_at, :updated_at)
                """,
                record,
            )
            self._connection.commit()
        self.add_audit(
            record["tenant_id"],
            "policy.write",
            "policy",
            record["policy_id"],
            record["subject_id"],
            {"kind": record["kind"]},
        )
        return self.get_policy(record["policy_id"])

    def get_policy(self, policy_id: str) -> JsonDict:
        row = self._connection.execute("SELECT * FROM policies WHERE policy_id = ?", (policy_id,)).fetchone()
        if row is None:
            raise KeyError(f"policy not found: {policy_id}")
        return row_to_dict(row)

    def list_policies(
        self, tenant_id: Optional[str] = None, subject_id: Optional[str] = None, limit: int = 100
    ) -> List[JsonDict]:
        clauses: List[str] = ["status = ?"]
        params: List[Any] = ["active"]
        if tenant_id:
            clauses.append("tenant_id = ?")
            params.append(tenant_id)
        if subject_id:
            clauses.append("(subject_id = ? OR subject_id IS NULL)")
            params.append(subject_id)
        where = f"WHERE {' AND '.join(clauses)}"
        rows = self._connection.execute(
            f"SELECT * FROM policies {where} ORDER BY updated_at DESC LIMIT ?",
            [*params, limit],
        ).fetchall()
        return [row_to_dict(row) for row in rows]

    def list_scores(
        self, tenant_id: Optional[str] = None, subject_id: Optional[str] = None, limit: int = 50
    ) -> List[JsonDict]:
        clauses: List[str] = []
        params: List[Any] = []
        if tenant_id:
            clauses.append("tenant_id = ?")
            params.append(tenant_id)
        if subject_id:
            clauses.append("subject_id = ?")
            params.append(subject_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._connection.execute(
            f"SELECT * FROM trajectory_scores {where} ORDER BY created_at DESC LIMIT ?",
            [*params, limit],
        ).fetchall()
        return [row_to_dict(row) for row in rows]

    def list_audit(
        self, tenant_id: Optional[str] = None, subject_id: Optional[str] = None, limit: int = 50
    ) -> List[JsonDict]:
        clauses: List[str] = []
        params: List[Any] = []
        if tenant_id:
            clauses.append("tenant_id = ?")
            params.append(tenant_id)
        if subject_id:
            clauses.append("(subject_id = ? OR subject_id IS NULL)")
            params.append(subject_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._connection.execute(
            f"SELECT * FROM audit_events {where} ORDER BY created_at DESC LIMIT ?",
            [*params, limit],
        ).fetchall()
        return [row_to_dict(row) for row in rows]

    def counts(self, tenant_id: Optional[str] = None, subject_id: Optional[str] = None) -> JsonDict:
        result: JsonDict = {}
        tables = {
            "observations": "observations",
            "memories": "memories",
            "nodes": "graph_nodes",
            "edges": "graph_edges",
            "traces": "traces",
            "steps": "trace_steps",
            "scores": "trajectory_scores",
            "interpretations": "quantum_trajectory_reports",
            "policies": "policies",
        }
        for key, table in tables.items():
            clauses: List[str] = []
            params: List[Any] = []
            if tenant_id:
                clauses.append("tenant_id = ?")
                params.append(tenant_id)
            if subject_id:
                clauses.append("subject_id = ?")
                params.append(subject_id)
            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            row = self._connection.execute(f"SELECT COUNT(*) FROM {table} {where}", params).fetchone()
            result[key] = int(row[0])
        return result

    def delete_subject(self, tenant_id: str, subject_id: str) -> JsonDict:
        tables = [
            "observations",
            "memories",
            "graph_edges",
            "graph_nodes",
            "trace_steps",
            "trajectory_scores",
            "quantum_trajectory_reports",
            "traces",
            "policies",
        ]
        deleted: Dict[str, int] = {}
        with self._lock:
            for table in tables:
                cursor = self._connection.execute(
                    f"DELETE FROM {table} WHERE tenant_id = ? AND subject_id = ?",
                    (tenant_id, subject_id),
                )
                deleted[table] = cursor.rowcount
            self._connection.commit()
        self.add_audit(
            tenant_id,
            "subject.erase",
            "subject",
            subject_id,
            subject_id,
            {"deleted": deleted},
        )
        return {"tenant_id": tenant_id, "subject_id": subject_id, "deleted": deleted}

    def dashboard_state(self, tenant_id: str = "demo", subject_id: Optional[str] = None) -> JsonDict:
        return {
            "counts": self.counts(tenant_id, subject_id),
            "traces": self.list_traces(tenant_id, subject_id, limit=20),
            "observations": self.list_observations(tenant_id, subject_id, limit=30),
            "memories": self.list_memories(tenant_id, subject_id, limit=50),
            "graph": self.list_graph(tenant_id, subject_id, limit=120),
            "scores": self.list_scores(tenant_id, subject_id, limit=20),
            "quantum_reports": self.list_quantum_reports(tenant_id, subject_id, limit=12),
            "policies": self.list_policies(tenant_id, subject_id, limit=30),
            "audit": self.list_audit(tenant_id, subject_id, limit=20),
        }
