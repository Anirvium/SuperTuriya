from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .models import (
    JsonDict,
    clamp,
    clean_text,
    extract_capitalized_entities,
    mean,
    token_set,
    utc_now,
)
from .quantum_layer import QuantumInspiredTrajectoryAnalyzer
from .store import SuperTuriyaStore


FAILURE_TERMS = {
    "error",
    "failed",
    "failure",
    "timeout",
    "missing",
    "incorrect",
    "contradiction",
    "hallucination",
    "overgeneral",
    "unsafe",
    "stale",
}

RECOVERY_TERMS = {"recover", "fallback", "retry", "corrected", "resolved", "repair", "mitigated"}

PREFERENCE_TERMS = {"prefer", "prefers", "preference", "likes", "requires", "needs", "avoid"}

PROCEDURAL_TERMS = {
    "when",
    "always",
    "never",
    "should",
    "strategy",
    "lesson",
    "policy",
    "guardrail",
    "recovery",
}


class SuperTuriyaEngine:
    """Research-backed trajectory intelligence engine."""

    def __init__(self, store: SuperTuriyaStore) -> None:
        self.store = store
        self.quantum_analyzer = QuantumInspiredTrajectoryAnalyzer()

    def capture_observations(self, payload: Mapping[str, Any]) -> JsonDict:
        raw = payload.get("observations", payload)
        if isinstance(raw, Mapping):
            observations_payload = [raw]
        elif isinstance(raw, list):
            observations_payload = raw
        else:
            raise ValueError("observations must be an object or list")

        enriched = []
        graph_summary = {"nodes_created": 0, "edges_created": 0}
        for item in observations_payload:
            item = dict(item)
            content = clean_text(item.get("content"))
            explicit_entities = [clean_text(entity) for entity in item.get("entities", []) if clean_text(entity)]
            inferred_entities = extract_capitalized_entities(content)
            item["entities"] = list(dict.fromkeys([*explicit_entities, *inferred_entities]))
            enriched.append(item)

        observations = self.store.add_observations(enriched)
        for observation in observations:
            relations = list(observation.get("relations") or [])
            entities = observation.get("entities") or []
            relations.extend(self._cooccurrence_relations(entities, observation["observation_id"]))
            summary = self.store.upsert_graph(
                observation["tenant_id"],
                observation["subject_id"],
                entities,
                relations,
                derived_from=[observation["observation_id"]],
            )
            graph_summary["nodes_created"] += summary["nodes_created"]
            graph_summary["edges_created"] += summary["edges_created"]

        return {"observations": observations, "graph": graph_summary}

    def extract_memories(self, payload: Mapping[str, Any]) -> JsonDict:
        tenant_id = clean_text(payload.get("tenant_id") or "default")
        subject_id = clean_text(payload.get("subject_id"))
        dry_run = bool(payload.get("dry_run", False))
        limit = int(payload.get("limit") or 40)

        observations = self._observations_for_payload(payload, tenant_id, subject_id, limit)
        candidates = self._memory_candidates(observations)
        existing = self.store.list_memories(
            tenant_id=tenant_id,
            subject_id=subject_id or None,
            limit=500,
        )
        existing_keys = {self._memory_key(memory["memory_type"], memory["text"]) for memory in existing}

        unique_candidates = []
        for candidate in candidates:
            key = self._memory_key(candidate["memory_type"], candidate["text"])
            if key in existing_keys:
                continue
            existing_keys.add(key)
            unique_candidates.append(candidate)

        stored = []
        if not dry_run:
            for candidate in unique_candidates:
                stored.append(self.store.add_memory(candidate))

        return {
            "source_observation_count": len(observations),
            "candidate_count": len(unique_candidates),
            "candidates": unique_candidates,
            "stored": stored,
        }

    def search_memories(self, payload: Mapping[str, Any]) -> JsonDict:
        tenant_id = clean_text(payload.get("tenant_id") or "default")
        subject_id = clean_text(payload.get("subject_id")) or None
        query = clean_text(payload.get("query"))
        memory_types = payload.get("memory_types") or payload.get("types")
        limit = int(payload.get("limit") or 8)
        memories = self.store.list_memories(tenant_id, subject_id, memory_types, limit=500)
        query_tokens = token_set(query)

        ranked = []
        for memory in memories:
            memory_tokens = token_set(memory["text"])
            overlap = len(query_tokens & memory_tokens)
            union = max(1, len(query_tokens | memory_tokens))
            lexical = overlap / union
            phrase = 0.15 if query and query.lower() in memory["text"].lower() else 0.0
            confidence = float(memory.get("confidence") or 0.5) * 0.25
            type_boost = self._type_boost(memory["memory_type"], query_tokens)
            score = clamp((lexical * 0.7) + phrase + confidence + type_boost)
            if score > 0.08 or not query:
                ranked.append(
                    {
                        **memory,
                        "rank_score": round(score, 4),
                        "routing_reason": self._routing_reason(memory, overlap, type_boost),
                    }
                )
        ranked.sort(key=lambda item: item["rank_score"], reverse=True)
        return {
            "query": query,
            "results": ranked[:limit],
            "context": "\n".join(f"- {item['text']}" for item in ranked[:limit]),
        }

    def upsert_graph(self, payload: Mapping[str, Any]) -> JsonDict:
        tenant_id = clean_text(payload.get("tenant_id") or "default")
        subject_id = clean_text(payload.get("subject_id") or "global")
        return self.store.upsert_graph(
            tenant_id,
            subject_id,
            payload.get("entities") or [],
            payload.get("relations") or [],
            payload.get("derived_from") or [],
        )

    def start_trace(self, payload: Mapping[str, Any]) -> JsonDict:
        return self.store.start_trace(payload)

    def record_step(self, payload: Mapping[str, Any]) -> JsonDict:
        step = self.store.add_trace_step(payload)
        if payload.get("capture_observation", True) and (step.get("input") or step.get("output")):
            content = step.get("output") or step.get("input")
            labels = dict(payload.get("labels") or {})
            if step["status"] in {"failed", "error"}:
                labels["failure_signal"] = True
            observation = {
                "tenant_id": step["tenant_id"],
                "subject_id": step["subject_id"],
                "run_id": step["run_id"],
                "step_id": step["step_id"],
                "type": "tool_result" if step["kind"] == "tool" else "decision",
                "source": step["source"],
                "content": content,
                "entities": payload.get("entities") or [],
                "relations": payload.get("relations") or [],
                "labels": labels,
                "provenance": {
                    "parent_step_id": step.get("parent_step_id"),
                    "tool_call_id": step.get("tool_call_id"),
                    "memory_refs": step.get("memory_refs") or [],
                },
            }
            self.capture_observations({"observations": [observation]})
        return step

    def score_trajectory(self, payload: Mapping[str, Any]) -> JsonDict:
        run_id = clean_text(payload.get("run_id"))
        if not run_id:
            raise ValueError("run_id is required")
        trace = self.store.get_trace(run_id)
        run = trace["run"]
        steps = trace["steps"]
        observations = self.store.list_observations(
            tenant_id=run["tenant_id"],
            subject_id=run["subject_id"],
            run_id=run_id,
            limit=300,
            ascending=True,
        )
        memories = self.store.list_memories(run["tenant_id"], run["subject_id"], limit=300)
        metrics, root_causes, explanation = self._score(run, steps, observations, memories)
        utility = self._utility(metrics)
        stored = None
        if not payload.get("dry_run", False):
            stored = self.store.save_score(
                run_id,
                run["tenant_id"],
                run["subject_id"],
                utility,
                metrics,
                root_causes,
            )
        return {
            "run_id": run_id,
            "utility": utility,
            "metrics": metrics,
            "root_cause_hypotheses": root_causes,
            "explanation": explanation,
            "stored": stored,
        }

    def counterfactuals(self, payload: Mapping[str, Any]) -> JsonDict:
        run_id = clean_text(payload.get("run_id"))
        if not run_id:
            raise ValueError("run_id is required")
        trace = self.store.get_trace(run_id)
        run = trace["run"]
        observations = self.store.list_observations(
            tenant_id=run["tenant_id"],
            subject_id=run["subject_id"],
            run_id=run_id,
            limit=300,
            ascending=True,
        )
        memories = self.store.list_memories(run["tenant_id"], run["subject_id"], limit=300)
        base_metrics, _, _ = self._score(run, trace["steps"], observations, memories)
        baseline = self._utility(base_metrics)
        analyses = []
        for step in trace["steps"]:
            delta, rationale, action = self._counterfactual_delta(step, base_metrics)
            analyses.append(
                {
                    "step_id": step["step_id"],
                    "step_index": step["step_index"],
                    "kind": step["kind"],
                    "status": step["status"],
                    "baseline_utility": baseline,
                    "estimated_utility_without_step": round(clamp(baseline + delta), 4),
                    "estimated_delta": round(delta, 4),
                    "rationale": rationale,
                    "suggested_action": action,
                }
            )
        analyses.sort(key=lambda item: abs(item["estimated_delta"]), reverse=True)
        return {"run_id": run_id, "baseline_utility": baseline, "counterfactuals": analyses}

    def quantum_interpret_trajectory(self, payload: Mapping[str, Any]) -> JsonDict:
        run_id = clean_text(payload.get("run_id"))
        if not run_id:
            raise ValueError("run_id is required")
        trace = self.store.get_trace(run_id)
        run = trace["run"]
        observations = self.store.list_observations(
            tenant_id=run["tenant_id"],
            subject_id=run["subject_id"],
            run_id=run_id,
            limit=300,
            ascending=True,
        )
        memories = self.store.list_memories(run["tenant_id"], run["subject_id"], limit=300)
        graph = self.store.list_graph(run["tenant_id"], run["subject_id"], limit=300)
        if trace["scores"]:
            score = trace["scores"][0]
        else:
            score = self.score_trajectory({"run_id": run_id, "dry_run": True})
        historical_reports = self.store.list_quantum_reports(
            tenant_id=run["tenant_id"],
            subject_id=run["subject_id"],
            limit=40,
        )
        report = self.quantum_analyzer.analyze(
            trace=trace,
            observations=observations,
            memories=memories,
            graph=graph,
            score=score,
            historical_reports=historical_reports,
        )
        if payload.get("dry_run", False):
            return report
        stored = self.store.save_quantum_report(report)
        full_report = stored.get("full_report") or report
        return {**full_report, "stored": stored}

    def synthesise_policies(self, payload: Mapping[str, Any]) -> JsonDict:
        run_id = clean_text(payload.get("run_id"))
        tenant_id = clean_text(payload.get("tenant_id") or "default")
        subject_id = clean_text(payload.get("subject_id")) or None

        if run_id:
            score = self.score_trajectory({"run_id": run_id, "dry_run": True})
            tenant_id = self.store.get_trace(run_id)["run"]["tenant_id"]
            subject_id = self.store.get_trace(run_id)["run"]["subject_id"]
            candidates = self._policy_candidates_from_score(run_id, score)
        else:
            scores = self.store.list_scores(tenant_id, subject_id, limit=5)
            candidates = []
            for item in scores:
                score = {
                    "run_id": item["run_id"],
                    "utility": item["utility"],
                    "metrics": item["metrics"],
                    "root_cause_hypotheses": item["root_cause_hypotheses"],
                }
                candidates.extend(self._policy_candidates_from_score(item["run_id"], score))

        existing = {
            (policy["kind"].lower(), policy["title"].lower())
            for policy in self.store.list_policies(tenant_id, subject_id, limit=200)
        }
        stored = []
        for candidate in candidates:
            key = (candidate["kind"].lower(), candidate["title"].lower())
            if key in existing:
                continue
            existing.add(key)
            candidate["tenant_id"] = tenant_id
            candidate["subject_id"] = subject_id
            stored.append(self.store.add_policy(candidate))
        return {"candidate_count": len(candidates), "stored": stored}

    def forget_subject(self, tenant_id: str, subject_id: str) -> JsonDict:
        return self.store.delete_subject(tenant_id, subject_id)

    def dashboard_state(self, tenant_id: str = "demo", subject_id: Optional[str] = None) -> JsonDict:
        state = self.store.dashboard_state(tenant_id, subject_id)
        latest_score = state["scores"][0] if state["scores"] else None
        state["latest_score"] = latest_score
        state["latest_quantum_report"] = state["quantum_reports"][0] if state["quantum_reports"] else None
        state["system"] = {
            "name": "SuperTuriya",
            "thesis": "Trajectory Intelligence for auditable, self-improving agents",
            "time": utc_now(),
        }
        return state

    def _observations_for_payload(
        self,
        payload: Mapping[str, Any],
        tenant_id: str,
        subject_id: str,
        limit: int,
    ) -> List[JsonDict]:
        if payload.get("observations"):
            captured = self.capture_observations(
                {"observations": payload["observations"], "tenant_id": tenant_id, "subject_id": subject_id}
            )
            return captured["observations"]
        if payload.get("observation_ids"):
            return self.store.list_observations(
                tenant_id=tenant_id,
                subject_id=subject_id or None,
                observation_ids=payload["observation_ids"],
                limit=limit,
                ascending=True,
            )
        if payload.get("run_id"):
            return self.store.list_observations(
                tenant_id=tenant_id,
                subject_id=subject_id or None,
                run_id=payload["run_id"],
                limit=limit,
                ascending=True,
            )
        return self.store.list_observations(
            tenant_id=tenant_id,
            subject_id=subject_id or None,
            limit=limit,
            ascending=True,
        )

    def _memory_candidates(self, observations: Sequence[JsonDict]) -> List[JsonDict]:
        candidates: List[JsonDict] = []
        relation_counter: Counter = Counter()
        observations_by_subject: Dict[Tuple[str, str], List[JsonDict]] = defaultdict(list)
        for observation in observations:
            observations_by_subject[(observation["tenant_id"], observation["subject_id"])].append(observation)
            for relation in observation.get("relations") or []:
                relation_counter[
                    (
                        observation["tenant_id"],
                        observation["subject_id"],
                        clean_text(relation.get("from")),
                        clean_text(relation.get("type") or relation.get("relation_type")),
                        clean_text(relation.get("to")),
                    )
                ] += 1

        for (tenant_id, subject_id), scoped_observations in observations_by_subject.items():
            for observation in scoped_observations:
                text = observation["content"]
                labels = observation.get("labels") or {}
                confidence = self._observation_confidence(observation)
                graph_refs = self._graph_refs(observation)
                candidates.append(
                    {
                        "tenant_id": tenant_id,
                        "subject_id": subject_id,
                        "memory_type": "episodic",
                        "text": f"{observation['source']} observed: {text}",
                        "derived_from": [observation["observation_id"]],
                        "confidence": round(confidence, 3),
                        "graph_refs": graph_refs,
                        "metadata": {
                            "observation_type": observation["type"],
                            "labels": labels,
                            "synthesis": "episodic_observation",
                        },
                    }
                )
                preference = self._preference_memory(text)
                if preference:
                    candidates.append(
                        {
                            "tenant_id": tenant_id,
                            "subject_id": subject_id,
                            "memory_type": "profile",
                            "text": preference,
                            "derived_from": [observation["observation_id"]],
                            "confidence": round(min(0.9, confidence + 0.08), 3),
                            "graph_refs": graph_refs,
                            "metadata": {"synthesis": "profile_preference"},
                        }
                    )
                procedural = self._procedural_memory(text, labels)
                if procedural:
                    candidates.append(
                        {
                            "tenant_id": tenant_id,
                            "subject_id": subject_id,
                            "memory_type": "procedural",
                            "text": procedural,
                            "derived_from": [observation["observation_id"]],
                            "confidence": round(min(0.88, confidence + 0.06), 3),
                            "graph_refs": graph_refs,
                            "metadata": {"synthesis": "procedural_lesson"},
                        }
                    )

            entity_mentions = Counter()
            for observation in scoped_observations:
                for entity in observation.get("entities") or []:
                    entity_mentions[entity] += 1
            for entity, count in entity_mentions.items():
                if count >= 2:
                    related = [
                        item["observation_id"]
                        for item in scoped_observations
                        if entity in (item.get("entities") or [])
                    ]
                    candidates.append(
                        {
                            "tenant_id": tenant_id,
                            "subject_id": subject_id,
                            "memory_type": "semantic",
                            "text": f"{entity} is a recurring entity across {count} observations.",
                            "derived_from": related[:8],
                            "confidence": round(clamp(0.55 + 0.08 * count, upper=0.86), 3),
                            "graph_refs": [f"node:{entity}"],
                            "metadata": {"synthesis": "recurring_entity"},
                        }
                    )

        for (tenant_id, subject_id, from_entity, relation_type, to_entity), count in relation_counter.items():
            if count >= 1 and from_entity and to_entity:
                candidates.append(
                    {
                        "tenant_id": tenant_id,
                        "subject_id": subject_id,
                        "memory_type": "semantic",
                        "text": f"{from_entity} {relation_type.lower() or 'relates to'} {to_entity}.",
                        "derived_from": [],
                        "confidence": round(clamp(0.6 + 0.08 * count, upper=0.9), 3),
                        "graph_refs": [f"node:{from_entity}", f"node:{to_entity}"],
                        "metadata": {"synthesis": "explicit_relation", "support_count": count},
                    }
                )

        candidates.sort(key=lambda item: (item["memory_type"] != "procedural", -item["confidence"]))
        return candidates

    def _score(
        self,
        run: Mapping[str, Any],
        steps: Sequence[JsonDict],
        observations: Sequence[JsonDict],
        memories: Sequence[JsonDict],
    ) -> Tuple[JsonDict, List[JsonDict], str]:
        step_count = len(steps)
        failure_steps = [step for step in steps if self._is_failure(step)]
        recovery_steps = [step for step in steps if self._has_any(step, RECOVERY_TERMS)]
        evidence_steps = [
            step
            for step in steps
            if step.get("memory_refs")
            or step["kind"] in {"tool", "retrieval", "memory"}
            or "evidence" in f"{step.get('input')} {step.get('output')}".lower()
        ]
        memory_refs = {
            ref
            for step in steps
            for ref in (step.get("memory_refs") or [])
        }
        policy_violations = [
            step
            for step in steps
            if any(term in f"{step.get('input')} {step.get('output')}".lower() for term in ["unsafe", "violate", "ignored policy"])
        ]

        completed = run.get("status") in {"completed", "succeeded", "success"}
        if not completed and steps:
            completed = steps[-1].get("status") in {"completed", "succeeded", "success"} and not failure_steps

        goal_completion = 0.96 if completed else 0.28
        if failure_steps and recovery_steps:
            goal_completion = max(goal_completion, 0.68)

        evidence_grounding = clamp((len(evidence_steps) / max(1, step_count)) + (0.08 if observations else 0.0))
        if not evidence_steps and observations:
            evidence_grounding = 0.42

        memory_relevance = clamp(
            (len(memory_refs) / max(1, min(5, step_count))) * 0.7
            + (0.2 if memories else 0.0)
            + (0.1 if any(memory.get("memory_type") == "procedural" for memory in memories) else 0.0)
        )

        loop_penalty = max(0, step_count - 6) * 0.055
        failure_penalty = len(failure_steps) * 0.09
        step_efficiency = clamp(0.96 - loop_penalty - failure_penalty)

        policy_adherence = clamp(0.96 - (0.18 * len(policy_violations)) - (0.05 * len(failure_steps)))

        if failure_steps:
            recovery_quality = clamp((len(recovery_steps) / len(failure_steps)) * 0.72 + 0.12)
        else:
            recovery_quality = 0.82 if step_count else 0.0

        metrics = {
            "goal_completion": round(goal_completion, 4),
            "evidence_grounding": round(evidence_grounding, 4),
            "memory_relevance": round(memory_relevance, 4),
            "step_efficiency": round(step_efficiency, 4),
            "policy_adherence": round(policy_adherence, 4),
            "recovery_quality": round(recovery_quality, 4),
        }
        root_causes = self._root_causes(metrics, steps, failure_steps, evidence_steps, memories)
        explanation = (
            f"Scored {step_count} steps, {len(observations)} observations, "
            f"{len(memories)} active memories, {len(failure_steps)} failure signals."
        )
        return metrics, root_causes, explanation

    def _root_causes(
        self,
        metrics: Mapping[str, float],
        steps: Sequence[JsonDict],
        failure_steps: Sequence[JsonDict],
        evidence_steps: Sequence[JsonDict],
        memories: Sequence[JsonDict],
    ) -> List[JsonDict]:
        causes: List[JsonDict] = []
        if metrics["evidence_grounding"] < 0.55:
            causes.append(
                {
                    "kind": "missing_evidence",
                    "step_id": steps[-1]["step_id"] if steps else None,
                    "confidence": 0.76,
                    "detail": "Few steps carried memory references, tool evidence, or explicit evidence claims.",
                }
            )
        if metrics["memory_relevance"] < 0.45:
            causes.append(
                {
                    "kind": "weak_memory_routing",
                    "step_id": steps[0]["step_id"] if steps else None,
                    "confidence": 0.72,
                    "detail": "Trajectory did not use enough retrieved memory for the task context.",
                }
            )
        for step in failure_steps[:3]:
            text = f"{step.get('input')} {step.get('output')}".lower()
            kind = "tool_failure"
            if "overgeneral" in text or "assumption" in text:
                kind = "memory_overgeneralisation"
            if "contradiction" in text or "stale" in text:
                kind = "stale_or_contradictory_memory"
            causes.append(
                {
                    "kind": kind,
                    "step_id": step["step_id"],
                    "confidence": 0.69,
                    "detail": clean_text(step.get("output") or step.get("input"))[:180],
                }
            )
        if metrics["step_efficiency"] < 0.72:
            causes.append(
                {
                    "kind": "inefficient_execution_path",
                    "step_id": steps[-1]["step_id"] if steps else None,
                    "confidence": 0.64,
                    "detail": "Step count or repeated failures reduced path efficiency.",
                }
            )
        if not memories:
            causes.append(
                {
                    "kind": "empty_memory_substrate",
                    "step_id": None,
                    "confidence": 0.62,
                    "detail": "No active memory was available for retrieval or reflection.",
                }
            )
        if not causes and evidence_steps:
            causes.append(
                {
                    "kind": "healthy_trajectory",
                    "step_id": evidence_steps[-1]["step_id"],
                    "confidence": 0.71,
                    "detail": "Trajectory shows adequate evidence use, policy adherence, and recovery posture.",
                }
            )
        return causes

    def _utility(self, metrics: Mapping[str, float]) -> float:
        weights = {
            "goal_completion": 0.24,
            "evidence_grounding": 0.2,
            "memory_relevance": 0.16,
            "step_efficiency": 0.14,
            "policy_adherence": 0.14,
            "recovery_quality": 0.12,
        }
        return round(sum(metrics[key] * weight for key, weight in weights.items()), 4)

    def _policy_candidates_from_score(self, run_id: str, score: Mapping[str, Any]) -> List[JsonDict]:
        metrics = score.get("metrics") or {}
        causes = score.get("root_cause_hypotheses") or []
        candidates: List[JsonDict] = []
        if metrics.get("evidence_grounding", 1.0) < 0.7:
            candidates.append(
                self._policy(
                    "guardrail",
                    "Evidence-linked final claims",
                    "Before finalizing a recommendation, require at least one memory, tool result, or observation reference to be attached to the deciding step.",
                    run_id,
                    0.78,
                )
            )
        if metrics.get("memory_relevance", 1.0) < 0.65:
            candidates.append(
                self._policy(
                    "routing",
                    "Hybrid memory retrieval before planning",
                    "For subject-specific tasks, retrieve profile, semantic, and procedural memory before the first planning step, then record the selected memory refs on the trace.",
                    run_id,
                    0.74,
                )
            )
        if metrics.get("step_efficiency", 1.0) < 0.76:
            candidates.append(
                self._policy(
                    "efficiency",
                    "Stop low-novelty loops",
                    "After two consecutive steps that add no new evidence, switch to a summarizing decision step or ask for missing information.",
                    run_id,
                    0.7,
                )
            )
        if metrics.get("recovery_quality", 1.0) < 0.55:
            candidates.append(
                self._policy(
                    "recovery",
                    "Explicit fallback after failure",
                    "When a tool or memory edge fails, capture the failure as an observation, use an alternate evidence source, and mark the recovery step in the trace.",
                    run_id,
                    0.76,
                )
            )
        for cause in causes:
            if cause.get("kind") == "memory_overgeneralisation":
                candidates.append(
                    self._policy(
                        "memory_governance",
                        "Guard against overgeneralized memory",
                        "Treat broad behavioral memories as hypotheses until supported by at least two recent observations or an explicit user confirmation.",
                        run_id,
                        0.73,
                    )
                )
            if cause.get("kind") == "stale_or_contradictory_memory":
                candidates.append(
                    self._policy(
                        "memory_governance",
                        "Resolve stale or contradictory memory",
                        "When retrieved memory contradicts fresh evidence, create a temporal graph update and suppress the older memory until reviewed.",
                        run_id,
                        0.75,
                    )
                )
        if metrics and mean(metrics.values()) > 0.82:
            candidates.append(
                self._policy(
                    "strategy",
                    "Promote high-utility trajectory pattern",
                    "Reuse this run pattern for similar tasks: retrieve subject memory, collect fresh tool evidence, then score policy adherence before final output.",
                    run_id,
                    0.69,
                )
            )
        return candidates

    def _policy(self, kind: str, title: str, body: str, run_id: str, confidence: float) -> JsonDict:
        return {
            "kind": kind,
            "title": title,
            "body": body,
            "derived_from_runs": [run_id],
            "confidence": confidence,
        }

    def _cooccurrence_relations(self, entities: Sequence[str], observation_id: str) -> List[JsonDict]:
        relations: List[JsonDict] = []
        clean_entities = [clean_text(entity) for entity in entities if clean_text(entity)]
        for index, entity in enumerate(clean_entities):
            for other in clean_entities[index + 1 : index + 3]:
                relations.append(
                    {
                        "from": entity,
                        "type": "CO_OCCURS_WITH",
                        "to": other,
                        "confidence": 0.45,
                        "derived_from": [observation_id],
                    }
                )
        return relations

    def _memory_key(self, memory_type: str, text: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
        return f"{memory_type}:{normalized[:220]}"

    def _observation_confidence(self, observation: Mapping[str, Any]) -> float:
        labels = observation.get("labels") or {}
        numeric_labels = [float(value) for value in labels.values() if isinstance(value, (int, float))]
        label_confidence = mean(numeric_labels, default=0.62)
        type_boost = 0.08 if observation.get("type") in {"tool_result", "feedback"} else 0.0
        relation_boost = 0.04 if observation.get("relations") else 0.0
        return clamp(label_confidence + type_boost + relation_boost, upper=0.92)

    def _graph_refs(self, observation: Mapping[str, Any]) -> List[str]:
        return [f"node:{entity}" for entity in observation.get("entities") or []]

    def _preference_memory(self, text: str) -> Optional[str]:
        lowered = text.lower()
        if not any(term in lowered for term in PREFERENCE_TERMS):
            return None
        return f"Subject preference or need: {text}"

    def _procedural_memory(self, text: str, labels: Mapping[str, Any]) -> Optional[str]:
        lowered = text.lower()
        if labels.get("failure_signal") or labels.get("recovery_signal"):
            return f"Trajectory lesson: when this pattern appears, account for it explicitly - {text}"
        if any(term in lowered for term in PROCEDURAL_TERMS):
            return f"Reusable procedure: {text}"
        return None

    def _type_boost(self, memory_type: str, query_tokens: set) -> float:
        if memory_type == "procedural" and query_tokens & {"how", "strategy", "policy", "recover"}:
            return 0.12
        if memory_type == "profile" and query_tokens & {"prefer", "needs", "user", "subject"}:
            return 0.1
        if memory_type == "semantic" and query_tokens & {"what", "why", "relation", "fact"}:
            return 0.08
        return 0.0

    def _routing_reason(self, memory: Mapping[str, Any], overlap: int, type_boost: float) -> str:
        reasons = []
        if overlap:
            reasons.append(f"{overlap} query terms matched")
        if type_boost:
            reasons.append(f"{memory['memory_type']} memory matched route intent")
        if memory.get("graph_refs"):
            reasons.append("graph references available")
        return "; ".join(reasons) or "recent active memory"

    def _is_failure(self, step: Mapping[str, Any]) -> bool:
        if step.get("status") in {"failed", "error", "timeout"}:
            return True
        if step.get("status") in {"completed", "succeeded", "success"} and self._has_any(step, RECOVERY_TERMS):
            return False
        return self._has_any(step, FAILURE_TERMS)

    def _has_any(self, step: Mapping[str, Any], terms: set) -> bool:
        text = f"{step.get('kind')} {step.get('input')} {step.get('output')} {step.get('metadata')}".lower()
        return any(term in text for term in terms)

    def _counterfactual_delta(self, step: Mapping[str, Any], metrics: Mapping[str, float]) -> Tuple[float, str, str]:
        text = f"{step.get('input')} {step.get('output')}".lower()
        delta = 0.0
        rationale_parts = []
        action = "keep"
        if self._is_failure(step):
            delta += 0.08 + (0.08 * (1 - metrics.get("recovery_quality", 0.5)))
            rationale_parts.append("step carries a failure signal")
            action = "replace or add recovery guardrail"
        if step.get("memory_refs"):
            delta -= 0.07
            rationale_parts.append("step used retrieved memory")
            action = "retain but verify memory provenance" if action == "keep" else action
        if step.get("kind") in {"tool", "retrieval", "memory"}:
            delta -= 0.05
            rationale_parts.append("step added evidence")
        if any(term in text for term in RECOVERY_TERMS):
            delta -= 0.08
            rationale_parts.append("step appears to recover the trajectory")
            action = "promote as procedural memory"
        if "unsafe" in text or "violate" in text:
            delta += 0.11
            rationale_parts.append("step may violate policy")
            action = "block or require review"
        if not rationale_parts:
            delta += 0.01 if metrics.get("step_efficiency", 1.0) < 0.75 else -0.01
            rationale_parts.append("low estimated causal effect")
        return (
            round(delta, 4),
            "; ".join(rationale_parts),
            action,
        )
