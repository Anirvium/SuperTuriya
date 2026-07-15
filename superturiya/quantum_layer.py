from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .models import JsonDict, clamp, clean_text, mean, token_set, utc_now


INTERPRETATION_LABELS = [
    "retrieval_context_gap",
    "ambiguous_user_intent",
    "memory_conflict",
    "tool_selection_error",
    "weak_planning",
    "unsupported_assumption",
    "policy_or_safety_risk",
    "successful_recovery",
    "efficient_grounded_execution",
]

CONTEXT_LENSES = {
    "factuality": {
        "retrieval_context_gap": 1.15,
        "unsupported_assumption": 1.25,
        "efficient_grounded_execution": 0.8,
    },
    "tool_use": {
        "tool_selection_error": 1.35,
        "tool_failure": 1.2,
        "successful_recovery": 0.95,
    },
    "retrieval_quality": {
        "retrieval_context_gap": 1.45,
        "memory_conflict": 1.1,
    },
    "safety": {
        "policy_or_safety_risk": 1.55,
        "unsupported_assumption": 1.05,
    },
    "planning_quality": {
        "weak_planning": 1.35,
        "successful_recovery": 1.05,
        "efficient_grounded_execution": 1.15,
    },
    "memory_consistency": {
        "memory_conflict": 1.5,
        "retrieval_context_gap": 1.05,
    },
    "ambiguity_resolution": {
        "ambiguous_user_intent": 1.4,
        "weak_planning": 1.1,
        "successful_recovery": 0.9,
    },
}


class QuantumInspiredTrajectoryAnalyzer:
    """Density-matrix-inspired interpretation layer for trajectory ambiguity.

    The implementation is intentionally classical and explainable. It borrows
    the language of mixed states, contextual measurement, and entropy to model
    uncertainty over competing trajectory interpretations.
    """

    def analyze(
        self,
        trace: Mapping[str, Any],
        observations: Sequence[JsonDict],
        memories: Sequence[JsonDict],
        graph: Mapping[str, Sequence[JsonDict]],
        score: Mapping[str, Any],
        historical_reports: Sequence[JsonDict],
    ) -> JsonDict:
        run = trace["run"]
        steps = trace["steps"]
        metrics = score.get("metrics") or {}
        root_causes = score.get("root_cause_hypotheses") or []
        features = self._features(run, steps, observations, memories, graph, metrics, root_causes)
        amplitudes = self._latent_state(features)
        label_evidence = self._interpretation_evidence(
            steps, observations, memories, graph, metrics, root_causes, features
        )
        probabilities = self._measurement_probabilities(label_evidence)
        density_matrix = self._diagonal_density(probabilities)
        entropy, normalized_entropy = self._entropy(probabilities)
        ambiguity_level = self._ambiguity_level(normalized_entropy, probabilities)
        context_measurements = self._context_measurements(label_evidence)
        dominant, common, minor = self._interpretation_roles(
            probabilities, label_evidence, historical_reports
        )
        relational_edges = self._relational_edges(label_evidence, graph, root_causes)
        couplings = self._couplings(steps, observations, memories, graph)
        experience_state = self._experience_state(
            run,
            steps,
            observations,
            memories,
            graph,
            score,
            features,
            probabilities,
            normalized_entropy,
            relational_edges,
            couplings,
        )
        attribution = self._attribution(score, dominant, relational_edges)
        learning_candidate = self._learning_candidate(dominant, common, normalized_entropy, metrics)
        recommendation = self._recommendation(learning_candidate, dominant, normalized_entropy)

        report = {
            "report_id": "",
            "trajectory_id": run["run_id"],
            "run_id": run["run_id"],
            "tenant_id": run["tenant_id"],
            "subject_id": run["subject_id"],
            "created_at": utc_now(),
            "trajectory_state_summary": self._summary(run, steps, observations, memories, score),
            "latent_state": {
                "basis": [
                    "trace",
                    "tool",
                    "memory",
                    "retrieval",
                    "feedback",
                    "graph",
                    "score",
                    "recovery",
                ],
                "amplitudes": amplitudes,
                "note": "Low-rank classical fusion vector; not a physical quantum state.",
            },
            "density_matrix": {
                "basis": INTERPRETATION_LABELS,
                "matrix": density_matrix,
                "trace": round(sum(row[index] for index, row in enumerate(density_matrix)), 6),
                "note": "Diagonal mixed-state approximation over interpretation hypotheses.",
            },
            "dominant_interpretation": dominant,
            "common_interpretation": common,
            "minor_interpretations": minor,
            "trajectory_entropy": round(entropy, 6),
            "normalized_entropy": round(normalized_entropy, 6),
            "ambiguity_score": round(normalized_entropy, 6),
            "ambiguity_level": ambiguity_level,
            "contextual_measurements": context_measurements,
            "relational_edges": relational_edges,
            "relational_couplings": couplings,
            "experience_state": experience_state,
            "failure_success_attribution": attribution,
            "learning_candidate": learning_candidate,
            "self_improvement_recommendation": recommendation,
            "scientific_positioning": (
                "Quantum-inspired classical analysis. The system models uncertainty over "
                "trajectory interpretations; it does not claim quantum computation or physical "
                "quantum cognition."
            ),
        }
        return report

    def _features(
        self,
        run: Mapping[str, Any],
        steps: Sequence[JsonDict],
        observations: Sequence[JsonDict],
        memories: Sequence[JsonDict],
        graph: Mapping[str, Sequence[JsonDict]],
        metrics: Mapping[str, float],
        root_causes: Sequence[JsonDict],
    ) -> JsonDict:
        text = self._trajectory_text(run, steps, observations, memories)
        tokens = token_set(text)
        failure_steps = [step for step in steps if step.get("status") in {"failed", "error", "timeout"}]
        recovery_hits = self._term_count(text, {"recover", "recovered", "fallback", "retry", "resolved"})
        tool_steps = [step for step in steps if step.get("kind") == "tool"]
        memory_steps = [step for step in steps if step.get("memory_refs")]
        feedback_observations = [item for item in observations if item.get("type") == "feedback"]
        contradiction_hits = self._term_count(text, {"contradiction", "conflict", "stale", "inconsistent"})
        assumption_hits = self._term_count(text, {"assumption", "unsupported", "hallucination", "overgeneral"})
        ambiguity_hits = self._term_count(
            text, {"ambiguous", "underspecified", "unclear", "missing", "constraints", "clarify"}
        )
        safety_hits = self._term_count(text, {"unsafe", "policy", "violate", "privacy", "phi"})
        graph_edges = graph.get("edges") or []
        graph_nodes = graph.get("nodes") or []
        graph_density = len(graph_edges) / max(1, len(graph_nodes) * max(1, len(graph_nodes) - 1))
        return {
            "step_count": len(steps),
            "failure_rate": len(failure_steps) / max(1, len(steps)),
            "recovery_signal": clamp(recovery_hits / 2),
            "tool_usage": len(tool_steps) / max(1, len(steps)),
            "memory_usage": len(memory_steps) / max(1, len(steps)),
            "feedback_signal": clamp(len(feedback_observations) / 2),
            "contradiction_signal": clamp(contradiction_hits / 2),
            "assumption_signal": clamp(assumption_hits / 2),
            "ambiguity_signal": clamp(ambiguity_hits / 3),
            "safety_signal": clamp(safety_hits / 3),
            "graph_density": clamp(graph_density * 8),
            "root_cause_count": len(root_causes),
            "token_diversity": clamp(len(tokens) / 140),
            "goal_completion": float(metrics.get("goal_completion", 0.0)),
            "evidence_grounding": float(metrics.get("evidence_grounding", 0.0)),
            "memory_relevance": float(metrics.get("memory_relevance", 0.0)),
            "step_efficiency": float(metrics.get("step_efficiency", 0.0)),
            "policy_adherence": float(metrics.get("policy_adherence", 0.0)),
            "recovery_quality": float(metrics.get("recovery_quality", 0.0)),
        }

    def _experience_state(
        self,
        run: Mapping[str, Any],
        steps: Sequence[JsonDict],
        observations: Sequence[JsonDict],
        memories: Sequence[JsonDict],
        graph: Mapping[str, Sequence[JsonDict]],
        score: Mapping[str, Any],
        features: Mapping[str, float],
        probabilities: Mapping[str, float],
        normalized_entropy: float,
        relational_edges: Sequence[JsonDict],
        couplings: Sequence[JsonDict],
    ) -> JsonDict:
        metrics = score.get("metrics") or {}
        function_score = self._function_score(metrics, score)
        experience_coherence = self._experience_coherence(metrics, features, normalized_entropy)
        function_experience_gap = clamp(abs(function_score - experience_coherence))
        hidden_friction_gap = clamp(function_score - experience_coherence)
        unresolved_execution_gap = clamp(experience_coherence - function_score)
        attention_memory = self._attention_memory_fidelity(
            steps, observations, memories, graph, features, couplings
        )
        transition_graph = self._state_transition_graph(
            run, steps, observations, memories, score, relational_edges
        )
        graph_discovery = self._experience_graph_discovery(
            metrics,
            features,
            probabilities,
            couplings,
            attention_memory,
            hidden_friction_gap,
            unresolved_execution_gap,
        )
        transition_drivers = self._transition_drivers(
            metrics, features, normalized_entropy, couplings
        )

        return {
            "positioning": (
                "Ontic-inspired classical proxy for trajectory state. It models the inferred "
                "agent/user path condition from traces, memory, graph evidence, and feedback; "
                "it is not a claim of consciousness or physical quantum state."
            ),
            "state_label": self._experience_state_label(
                function_score,
                experience_coherence,
                hidden_friction_gap,
                unresolved_execution_gap,
                normalized_entropy,
            ),
            "function_score": round(function_score, 6),
            "experience_coherence": round(experience_coherence, 6),
            "function_experience_gap": round(function_experience_gap, 6),
            "hidden_friction_gap": round(hidden_friction_gap, 6),
            "unresolved_execution_gap": round(unresolved_execution_gap, 6),
            "attention_memory_fidelity": attention_memory,
            "transition_drivers": transition_drivers,
            "state_transition_graph": transition_graph,
            "graph_discovery": graph_discovery,
            "product_readout": self._experience_readout(
                function_score,
                experience_coherence,
                hidden_friction_gap,
                unresolved_execution_gap,
                attention_memory,
            ),
        }

    def _function_score(self, metrics: Mapping[str, float], score: Mapping[str, Any]) -> float:
        utility = score.get("utility")
        if isinstance(utility, (int, float)):
            return clamp(float(utility))
        return clamp(
            mean(
                [
                    float(metrics.get("goal_completion", 0.0)),
                    float(metrics.get("evidence_grounding", 0.0)),
                    float(metrics.get("step_efficiency", 0.0)),
                    float(metrics.get("policy_adherence", 0.0)),
                    float(metrics.get("recovery_quality", 0.0)),
                ]
            )
        )

    def _experience_coherence(
        self,
        metrics: Mapping[str, float],
        features: Mapping[str, float],
        normalized_entropy: float,
    ) -> float:
        return clamp(
            0.22 * float(metrics.get("evidence_grounding", 0.0))
            + 0.18 * float(metrics.get("memory_relevance", 0.0))
            + 0.16 * float(metrics.get("recovery_quality", 0.0))
            + 0.14 * float(metrics.get("policy_adherence", 0.0))
            + 0.12 * float(metrics.get("step_efficiency", 0.0))
            + 0.08 * (1 - normalized_entropy)
            + 0.06 * (1 - float(features.get("failure_rate", 0.0)))
            + 0.04 * min(1.0, float(features.get("graph_density", 0.0)))
        )

    def _attention_memory_fidelity(
        self,
        steps: Sequence[JsonDict],
        observations: Sequence[JsonDict],
        memories: Sequence[JsonDict],
        graph: Mapping[str, Sequence[JsonDict]],
        features: Mapping[str, float],
        couplings: Sequence[JsonDict],
    ) -> JsonDict:
        memory_ref_counts: Counter = Counter(
            ref for step in steps for ref in (step.get("memory_refs") or [])
        )
        repeated_memory_refs = sum(
            count - 1 for count in memory_ref_counts.values() if count > 1
        )
        entity_counts: Counter = Counter(
            clean_text(entity).lower()
            for observation in observations
            for entity in (observation.get("entities") or [])
            if clean_text(entity)
        )
        repeated_entities = sum(count - 1 for count in entity_counts.values() if count > 1)
        feedback_repeats = len([item for item in observations if item.get("type") == "feedback"])
        procedural_support = len(
            [item for item in memories if item.get("memory_type") == "procedural"]
        )
        active_couplings = len(
            [item for item in couplings if float(item.get("coupling", 0.0)) > 0]
        )
        graph_reinforcement = min(3, len(graph.get("edges") or []) // 2)
        attention_repeats = max(
            1,
            repeated_memory_refs
            + repeated_entities
            + feedback_repeats
            + min(3, procedural_support)
            + active_couplings
            + graph_reinforcement,
        )
        latent_dimension_proxy = int(
            round(
                clamp(
                    2
                    + float(features.get("token_diversity", 0.0)) * 6
                    + float(features.get("root_cause_count", 0.0)) * 0.5
                    + active_couplings * 0.75,
                    lower=2,
                    upper=12,
                )
            )
        )
        fidelity = clamp((attention_repeats + 1) / (attention_repeats + latent_dimension_proxy))
        if fidelity >= 0.72:
            interpretation = "attention is repeatedly reinforcing memory write quality"
        elif fidelity >= 0.48:
            interpretation = "memory write quality is usable but still context-fragile"
        else:
            interpretation = "memory write quality is weak; collect repeated focused evidence"
        return {
            "attention_repeats": attention_repeats,
            "latent_dimension_proxy": latent_dimension_proxy,
            "fidelity": round(fidelity, 6),
            "interpretation": interpretation,
            "formula": "(attention_repeats + 1) / (attention_repeats + latent_dimension_proxy)",
        }

    def _state_transition_graph(
        self,
        run: Mapping[str, Any],
        steps: Sequence[JsonDict],
        observations: Sequence[JsonDict],
        memories: Sequence[JsonDict],
        score: Mapping[str, Any],
        relational_edges: Sequence[JsonDict],
    ) -> JsonDict:
        nodes: List[JsonDict] = [
            {
                "id": "state:start",
                "kind": "latent_state",
                "label": "Initial path state",
                "salience": 0.5,
            }
        ]
        edges: List[JsonDict] = []
        previous_state = "state:start"
        for index, step in enumerate(steps[:8]):
            step_id = clean_text(step.get("step_id") or f"step:{index + 1}")
            state_id = f"state:after_{index + 1}"
            step_status = clean_text(step.get("status") or "unknown")
            salience = 0.42
            if step_status in {"failed", "error", "timeout"}:
                salience = 0.86
            elif step.get("memory_refs"):
                salience = 0.68
            elif step_status in {"completed", "succeeded", "success"}:
                salience = 0.58
            nodes.append(
                {
                    "id": step_id,
                    "kind": clean_text(step.get("kind") or "step"),
                    "label": clean_text(step.get("source") or step.get("kind") or "step"),
                    "status": step_status,
                    "salience": round(salience, 4),
                }
            )
            nodes.append(
                {
                    "id": state_id,
                    "kind": "latent_state",
                    "label": f"State after step {index + 1}",
                    "salience": round(salience, 4),
                }
            )
            edges.extend(
                [
                    {
                        "from": previous_state,
                        "type": "evolves_through",
                        "to": step_id,
                        "confidence": round(salience, 4),
                    },
                    {
                        "from": step_id,
                        "type": "updates_state",
                        "to": state_id,
                        "confidence": round(salience, 4),
                    },
                ]
            )
            for ref in (step.get("memory_refs") or [])[:3]:
                memory_node = f"memory:{ref}"
                nodes.append(
                    {
                        "id": memory_node,
                        "kind": "memory_ref",
                        "label": ref,
                        "salience": 0.64,
                    }
                )
                edges.append(
                    {
                        "from": memory_node,
                        "type": "recalls_into",
                        "to": step_id,
                        "confidence": 0.66,
                    }
                )
            previous_state = state_id

        score_state = "state:scored"
        nodes.append(
            {
                "id": score_state,
                "kind": "evaluation",
                "label": "Scored path state",
                "salience": round(float(score.get("utility", 0.0)), 4),
            }
        )
        edges.append(
            {
                "from": previous_state,
                "type": "evaluated_as",
                "to": score_state,
                "confidence": round(float(score.get("utility", 0.0)), 4),
            }
        )

        for observation in observations[:4]:
            obs_id = clean_text(
                observation.get("observation_id")
                or observation.get("source")
                or "observation"
            )
            obs_label = clean_text(
                observation.get("source") or observation.get("type") or "observation"
            )
            nodes.append(
                {
                    "id": obs_id,
                    "kind": clean_text(observation.get("type") or "observation"),
                    "label": obs_label,
                    "salience": 0.56,
                }
            )
            anchor_target = (
                "state:start" if not observation.get("step_id") else observation.get("step_id")
            )
            edges.append(
                {
                    "from": obs_id,
                    "type": "anchors",
                    "to": anchor_target,
                    "confidence": 0.58,
                }
            )

        seen = set()
        unique_nodes = []
        for node in nodes:
            node_id = node["id"]
            if node_id in seen:
                continue
            seen.add(node_id)
            unique_nodes.append(node)

        return {
            "run_id": run.get("run_id"),
            "nodes": unique_nodes[:30],
            "edges": [*edges, *list(relational_edges[:6])][:42],
            "readout": (
                "State transition graph linking observations, memory recalls, trajectory "
                "steps, evaluation, and inferred state changes."
            ),
        }

    def _experience_graph_discovery(
        self,
        metrics: Mapping[str, float],
        features: Mapping[str, float],
        probabilities: Mapping[str, float],
        couplings: Sequence[JsonDict],
        attention_memory: Mapping[str, Any],
        hidden_friction_gap: float,
        unresolved_execution_gap: float,
    ) -> JsonDict:
        candidate_edges: List[JsonDict] = []
        motifs: List[JsonDict] = []
        if metrics.get("memory_relevance", 0.0) >= 0.55:
            candidate_edges.append(
                {
                    "from": "memory_recall",
                    "type": "stabilizes",
                    "to": "experience_coherence",
                    "confidence": round(float(metrics.get("memory_relevance", 0.0)), 4),
                }
            )
        if metrics.get("evidence_grounding", 0.0) < 0.7:
            candidate_edges.append(
                {
                    "from": "weak_evidence_grounding",
                    "type": "widens",
                    "to": "function_experience_gap",
                    "confidence": round(1 - float(metrics.get("evidence_grounding", 0.0)), 4),
                }
            )
        if hidden_friction_gap > 0.12:
            candidate_edges.append(
                {
                    "from": "external_success",
                    "type": "masks",
                    "to": "latent_path_friction",
                    "confidence": round(hidden_friction_gap, 4),
                }
            )
            motifs.append(
                {
                    "name": "completed_but_fragile",
                    "trigger": "function score exceeds experience coherence",
                    "action": (
                        "inspect recovery, evidence grounding, and memory routing before "
                        "promoting the path"
                    ),
                }
            )
        if unresolved_execution_gap > 0.12:
            candidate_edges.append(
                {
                    "from": "coherent_reasoning_path",
                    "type": "failed_to_convert_into",
                    "to": "task_completion",
                    "confidence": round(unresolved_execution_gap, 4),
                }
            )
        if attention_memory.get("fidelity", 0.0) >= 0.55:
            candidate_edges.append(
                {
                    "from": "focused_attention_repetition",
                    "type": "improves",
                    "to": "memory_write_fidelity",
                    "confidence": round(float(attention_memory.get("fidelity", 0.0)), 4),
                }
            )
            motifs.append(
                {
                    "name": "attention_reinforced_memory",
                    "trigger": "repeated memory/entity/feedback evidence",
                    "action": "promote stable lessons into procedural memory",
                }
            )
        for coupling in couplings[:3]:
            if float(coupling.get("coupling", 0.0)) <= 0:
                continue
            candidate_edges.append(
                {
                    "from": coupling["left"],
                    "type": "couples_with",
                    "to": coupling["right"],
                    "confidence": round(float(coupling.get("coupling", 0.0)), 4),
                }
            )
        top_label = max(probabilities, key=probabilities.get)
        if top_label not in {"successful_recovery", "efficient_grounded_execution"}:
            motifs.append(
                {
                    "name": top_label,
                    "trigger": "dominant interpretation remained unresolved",
                    "action": "collect one more observation or memory edge before policy writeback",
                }
            )
        return {
            "candidate_edges": candidate_edges[:8],
            "motifs": motifs[:5],
            "method": (
                "classical graph discovery over trace state, memory recall, evidence "
                "grounding, couplings, and function-experience mismatch"
            ),
        }

    def _transition_drivers(
        self,
        metrics: Mapping[str, float],
        features: Mapping[str, float],
        normalized_entropy: float,
        couplings: Sequence[JsonDict],
    ) -> List[JsonDict]:
        raw = [
            (
                "evidence_grounding",
                float(metrics.get("evidence_grounding", 0.0)),
                "grounds the state in observed evidence",
            ),
            (
                "memory_relevance",
                float(metrics.get("memory_relevance", 0.0)),
                "routes prior context into the path",
            ),
            (
                "recovery_quality",
                float(metrics.get("recovery_quality", 0.0)),
                "repairs instability after failure",
            ),
            (
                "step_efficiency",
                float(metrics.get("step_efficiency", 0.0)),
                "limits unnecessary loop depth",
            ),
            ("ambiguity_pressure", normalized_entropy, "keeps multiple interpretations open"),
            (
                "failure_pressure",
                float(features.get("failure_rate", 0.0)),
                "destabilizes trajectory continuity",
            ),
        ]
        for coupling in couplings[:2]:
            raw.append(
                (
                    f"{coupling['left']}__{coupling['right']}",
                    float(coupling.get("coupling", 0.0)),
                    coupling.get("interpretation", "coupling signal"),
                )
            )
        ranked = sorted(raw, key=lambda item: item[1], reverse=True)
        return [
            {"name": name, "strength": round(clamp(value), 6), "effect": effect}
            for name, value, effect in ranked[:6]
        ]

    def _experience_state_label(
        self,
        function_score: float,
        experience_coherence: float,
        hidden_friction_gap: float,
        unresolved_execution_gap: float,
        normalized_entropy: float,
    ) -> str:
        if function_score >= 0.72 and experience_coherence >= 0.68 and normalized_entropy < 0.82:
            return "integrated_flow"
        if hidden_friction_gap >= 0.16:
            return "completed_but_fragile"
        if unresolved_execution_gap >= 0.16:
            return "coherent_but_unresolved"
        if normalized_entropy >= 0.84:
            return "interpretively_uncertain"
        if experience_coherence < 0.44:
            return "turbulent_path"
        return "developing_state"

    def _experience_readout(
        self,
        function_score: float,
        experience_coherence: float,
        hidden_friction_gap: float,
        unresolved_execution_gap: float,
        attention_memory: Mapping[str, Any],
    ) -> str:
        if hidden_friction_gap >= 0.16:
            return (
                "The trajectory functioned better than it felt internally: promote only after "
                "checking grounding, recovery, and memory routing."
            )
        if unresolved_execution_gap >= 0.16:
            return (
                "The reasoning path was coherent but did not fully convert into task success; "
                "inspect final action selection and tool execution."
            )
        if function_score >= 0.72 and experience_coherence >= 0.68:
            return (
                "Function and experience are aligned; this is a strong candidate for reusable "
                "strategy memory."
            )
        if attention_memory.get("fidelity", 0.0) < 0.45:
            return "Collect repeated focused evidence before writing durable memory or policy."
        return "The path is usable but should retain ambiguity watchlist signals."

    def _latent_state(self, features: Mapping[str, float]) -> List[float]:
        raw = [
            0.2 + features["token_diversity"],
            0.2 + features["tool_usage"],
            0.2 + features["memory_usage"],
            0.2 + (1 - features["evidence_grounding"]),
            0.2 + features["feedback_signal"],
            0.2 + features["graph_density"],
            0.2 + mean(
                [
                    features["goal_completion"],
                    features["evidence_grounding"],
                    features["step_efficiency"],
                    features["policy_adherence"],
                ]
            ),
            0.2 + features["recovery_quality"],
        ]
        norm = math.sqrt(sum(value * value for value in raw)) or 1.0
        return [round(value / norm, 6) for value in raw]

    def _interpretation_evidence(
        self,
        steps: Sequence[JsonDict],
        observations: Sequence[JsonDict],
        memories: Sequence[JsonDict],
        graph: Mapping[str, Sequence[JsonDict]],
        metrics: Mapping[str, float],
        root_causes: Sequence[JsonDict],
        features: Mapping[str, float],
    ) -> Dict[str, JsonDict]:
        cause_text = " ".join(clean_text(cause.get("kind")) for cause in root_causes)
        text = self._trajectory_text({}, steps, observations, memories) + " " + cause_text
        evidence: Dict[str, JsonDict] = {
            label: {"score": 0.08, "evidence": []} for label in INTERPRETATION_LABELS
        }

        self._add_signal(
            evidence,
            "retrieval_context_gap",
            0.65 * (1 - features["evidence_grounding"]) + 0.35 * (1 - features["memory_relevance"]),
            "low evidence grounding or weak memory relevance",
        )
        self._add_signal(
            evidence,
            "ambiguous_user_intent",
            0.65 * features["ambiguity_signal"] + 0.25 * (1 - features["goal_completion"]),
            "ambiguous or underspecified request signals",
        )
        self._add_signal(
            evidence,
            "memory_conflict",
            0.68 * features["contradiction_signal"] + 0.18 * (1 - features["memory_relevance"]),
            "conflict, stale memory, or contradiction signals",
        )
        self._add_signal(
            evidence,
            "tool_selection_error",
            0.52 * features["failure_rate"] + 0.24 * features["tool_usage"] * (1 - features["goal_completion"]),
            "tool-related failure or insufficient verification",
        )
        self._add_signal(
            evidence,
            "weak_planning",
            0.62 * (1 - features["step_efficiency"]) + 0.28 * features["failure_rate"],
            "inefficient execution path or repeated failure",
        )
        self._add_signal(
            evidence,
            "unsupported_assumption",
            0.72 * features["assumption_signal"] + 0.28 * (1 - features["evidence_grounding"]),
            "unsupported assumption, hallucination, or overgeneralization signal",
        )
        self._add_signal(
            evidence,
            "policy_or_safety_risk",
            0.68 * features["safety_signal"] + 0.34 * (1 - features["policy_adherence"]),
            "policy, safety, or privacy pressure detected",
        )
        self._add_signal(
            evidence,
            "successful_recovery",
            0.66 * features["recovery_quality"] + 0.22 * features["recovery_signal"],
            "trajectory recovered from a failure or uncertainty signal",
        )
        self._add_signal(
            evidence,
            "efficient_grounded_execution",
            mean(
                [
                    metrics.get("goal_completion", 0.0),
                    metrics.get("evidence_grounding", 0.0),
                    metrics.get("step_efficiency", 0.0),
                    metrics.get("policy_adherence", 0.0),
                ]
            ),
            "high goal completion, grounding, efficiency, and policy adherence",
        )

        for cause in root_causes:
            kind = clean_text(cause.get("kind"))
            if kind in {"memory_overgeneralisation", "stale_or_contradictory_memory"}:
                self._add_signal(evidence, "memory_conflict", 0.28, clean_text(cause.get("detail")))
                self._add_signal(evidence, "unsupported_assumption", 0.2, clean_text(cause.get("detail")))
            if kind in {"missing_evidence", "weak_memory_routing"}:
                self._add_signal(evidence, "retrieval_context_gap", 0.3, clean_text(cause.get("detail")))
            if kind == "healthy_trajectory":
                self._add_signal(evidence, "efficient_grounded_execution", 0.28, clean_text(cause.get("detail")))

        if re.search(r"\b(skip|skipped|wrong tool|tool error|tool failed)\b", text):
            self._add_signal(evidence, "tool_selection_error", 0.3, "tool selection or tool execution concern")
        return evidence

    def _measurement_probabilities(self, label_evidence: Mapping[str, JsonDict]) -> Dict[str, float]:
        scores = [float(label_evidence[label]["score"]) for label in INTERPRETATION_LABELS]
        return self._softmax(scores)

    def _diagonal_density(self, probabilities: Mapping[str, float]) -> List[List[float]]:
        matrix: List[List[float]] = []
        for row_label in INTERPRETATION_LABELS:
            row = []
            for column_label in INTERPRETATION_LABELS:
                row.append(round(probabilities[row_label] if row_label == column_label else 0.0, 6))
            matrix.append(row)
        return matrix

    def _entropy(self, probabilities: Mapping[str, float]) -> Tuple[float, float]:
        entropy = -sum(p * math.log(max(p, 1e-12)) for p in probabilities.values())
        max_entropy = math.log(len(probabilities))
        return entropy, entropy / max_entropy if max_entropy else 0.0

    def _ambiguity_level(self, normalized_entropy: float, probabilities: Mapping[str, float]) -> str:
        ordered = sorted(probabilities.values(), reverse=True)
        margin = ordered[0] - ordered[1] if len(ordered) > 1 else ordered[0]
        if normalized_entropy >= 0.86 or margin < 0.08:
            return "high"
        if normalized_entropy >= 0.7 or margin < 0.16:
            return "medium_high"
        if normalized_entropy >= 0.48:
            return "medium"
        return "low"

    def _context_measurements(self, label_evidence: Mapping[str, JsonDict]) -> JsonDict:
        output: JsonDict = {}
        for lens, weights in CONTEXT_LENSES.items():
            weighted = []
            for label in INTERPRETATION_LABELS:
                weighted.append(float(label_evidence[label]["score"]) * float(weights.get(label, 1.0)))
            probabilities = self._softmax(weighted)
            top_label = max(probabilities, key=probabilities.get)
            output[lens] = {
                "top_interpretation": top_label,
                "probability": round(probabilities[top_label], 6),
                "distribution": {label: round(probabilities[label], 6) for label in INTERPRETATION_LABELS},
            }
        return output

    def _interpretation_roles(
        self,
        probabilities: Mapping[str, float],
        label_evidence: Mapping[str, JsonDict],
        historical_reports: Sequence[JsonDict],
    ) -> Tuple[JsonDict, JsonDict, List[JsonDict]]:
        ranked = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)
        dominant_label = ranked[0][0]
        dominant = self._interpretation_payload(dominant_label, probabilities, label_evidence, "dominant")

        historical_labels = []
        for report in historical_reports:
            full = report.get("full_report") or report
            for key in ("dominant_interpretation", "common_interpretation"):
                label = (full.get(key) or {}).get("label")
                if label:
                    historical_labels.append(label)
        common_label = None
        if historical_labels:
            counts = Counter(historical_labels)
            common_label = counts.most_common(1)[0][0]
        if not common_label or common_label == dominant_label:
            common_label = ranked[1][0] if len(ranked) > 1 else dominant_label
        common = self._interpretation_payload(common_label, probabilities, label_evidence, "common")
        common["recurrence_basis"] = "historical_reports" if historical_labels else "current_distribution"

        minor = [
            self._interpretation_payload(label, probabilities, label_evidence, "minor")
            for label, probability in ranked[2:]
            if probability >= 0.04
        ][:3]
        return dominant, common, minor

    def _interpretation_payload(
        self,
        label: str,
        probabilities: Mapping[str, float],
        label_evidence: Mapping[str, JsonDict],
        role: str,
    ) -> JsonDict:
        raw_evidence = label_evidence[label].get("evidence") or []
        return {
            "label": label,
            "role": role,
            "probability": round(probabilities[label], 6),
            "evidence": raw_evidence[:4] or ["weak prior; no strong direct signal"],
        }

    def _relational_edges(
        self,
        label_evidence: Mapping[str, JsonDict],
        graph: Mapping[str, Sequence[JsonDict]],
        root_causes: Sequence[JsonDict],
    ) -> List[JsonDict]:
        edges: List[JsonDict] = []
        if label_evidence["ambiguous_user_intent"]["score"] > 0.2:
            edges.append(
                {
                    "from": "ambiguous_intent",
                    "type": "caused_by",
                    "to": "missing_constraints",
                    "confidence": round(label_evidence["ambiguous_user_intent"]["score"], 4),
                }
            )
        if label_evidence["retrieval_context_gap"]["score"] > 0.2:
            edges.append(
                {
                    "from": "retrieval_gap",
                    "type": "supports",
                    "to": "unsupported_answer_risk",
                    "confidence": round(label_evidence["retrieval_context_gap"]["score"], 4),
                }
            )
        if label_evidence["memory_conflict"]["score"] > 0.2:
            edges.append(
                {
                    "from": "memory_conflict",
                    "type": "weak_signal_for",
                    "to": "personalization_error",
                    "confidence": round(label_evidence["memory_conflict"]["score"], 4),
                }
            )
        for cause in root_causes[:3]:
            if cause.get("step_id"):
                edges.append(
                    {
                        "from": clean_text(cause.get("kind")) or "root_cause",
                        "type": "localized_at",
                        "to": cause["step_id"],
                        "confidence": round(float(cause.get("confidence", 0.6)), 4),
                    }
                )
        for edge in (graph.get("edges") or [])[:4]:
            edges.append(
                {
                    "from": edge.get("from_node"),
                    "type": clean_text(edge.get("relation_type")).lower(),
                    "to": edge.get("to_node"),
                    "confidence": round(float(edge.get("confidence") or 0.5), 4),
                }
            )
        return edges[:10]

    def _couplings(
        self,
        steps: Sequence[JsonDict],
        observations: Sequence[JsonDict],
        memories: Sequence[JsonDict],
        graph: Mapping[str, Sequence[JsonDict]],
    ) -> List[JsonDict]:
        text = self._trajectory_text({}, steps, observations, memories)
        pairs = [
            (
                "retrieval_quality",
                "unsupported_assumption",
                {"retrieval", "memory", "document", "context"},
                {"unsupported", "assumption", "hallucination", "overgeneral"},
            ),
            (
                "ambiguous_intent",
                "tool_selection_error",
                {"ambiguous", "unclear", "missing", "constraints"},
                {"tool", "skipped", "wrong", "failed"},
            ),
            (
                "memory_conflict",
                "personalization_error",
                {"memory", "preference", "stale", "contradiction", "conflict"},
                {"personalization", "preference", "user", "subject"},
            ),
            (
                "tool_failure",
                "fallback_quality",
                {"tool", "failed", "timeout", "error"},
                {"recover", "fallback", "retry", "resolved"},
            ),
        ]
        output = []
        for left, right, left_terms, right_terms in pairs:
            left_signal = clamp(self._term_count(text, left_terms) / 3)
            right_signal = clamp(self._term_count(text, right_terms) / 3)
            joint_signal = clamp(self._joint_window_count(text, left_terms, right_terms) / 2)
            coupling = self._mutual_information_proxy(left_signal, right_signal, joint_signal)
            output.append(
                {
                    "left": left,
                    "right": right,
                    "coupling": round(coupling, 6),
                    "interpretation": self._coupling_interpretation(left, right, coupling),
                }
            )
        graph_relation_signal = clamp(len(graph.get("edges") or []) / max(1, len(graph.get("nodes") or [])))
        if graph_relation_signal:
            output.append(
                {
                    "left": "graph_relations",
                    "right": "trajectory_interpretation",
                    "coupling": round(graph_relation_signal, 6),
                    "interpretation": "Graph structure is contributing to interpretation strength.",
                }
            )
        return sorted(output, key=lambda item: item["coupling"], reverse=True)[:5]

    def _attribution(
        self,
        score: Mapping[str, Any],
        dominant: Mapping[str, Any],
        relational_edges: Sequence[JsonDict],
    ) -> JsonDict:
        metrics = score.get("metrics") or {}
        positive = []
        negative = []
        if metrics.get("evidence_grounding", 0) >= 0.75:
            positive.append("evidence grounding supported trajectory quality")
        else:
            negative.append("weak evidence grounding left the interpretation underdetermined")
        if metrics.get("recovery_quality", 0) >= 0.7:
            positive.append("recovery behavior improved final trajectory quality")
        elif metrics.get("recovery_quality", 0) < 0.5:
            negative.append("low recovery quality increased failure risk")
        if dominant["label"] not in {"successful_recovery", "efficient_grounded_execution"}:
            negative.append(f"dominant uncertainty driver: {dominant['label']}")
        else:
            positive.append(f"dominant success pattern: {dominant['label']}")
        return {
            "positive_factors": positive,
            "negative_factors": negative,
            "key_edges": list(relational_edges[:3]),
        }

    def _learning_candidate(
        self,
        dominant: Mapping[str, Any],
        common: Mapping[str, Any],
        normalized_entropy: float,
        metrics: Mapping[str, float],
    ) -> JsonDict:
        label = dominant["label"]
        mapping = {
            "retrieval_context_gap": ("retrieval_policy", "force verification when retrieved evidence confidence is below threshold"),
            "ambiguous_user_intent": ("prompt_policy", "ask clarifying questions when constraints remain underspecified"),
            "memory_conflict": ("memory_policy", "suppress stale or contradictory memory until reconciled by fresh evidence"),
            "tool_selection_error": ("tool_routing", "route through the verification tool before final answers in similar contexts"),
            "weak_planning": ("planning_policy", "limit low-novelty loops and require explicit plan checkpoints"),
            "unsupported_assumption": ("evaluator_logic", "penalize unsupported assumptions and require cited evidence spans"),
            "policy_or_safety_risk": ("guardrail", "escalate safety or privacy-sensitive trajectories for review"),
            "successful_recovery": ("procedural_memory", "promote the recovery strategy into reusable procedural memory"),
            "efficient_grounded_execution": ("strategy_memory", "reuse this evidence-first trajectory pattern"),
        }
        update_type, recommendation = mapping.get(label, ("trajectory_policy", "review this trajectory pattern"))
        priority = "high" if normalized_entropy > 0.74 or metrics.get("goal_completion", 1.0) < 0.6 else "medium"
        if label in {"successful_recovery", "efficient_grounded_execution"} and normalized_entropy < 0.72:
            priority = "medium"
        return {
            "update_type": update_type,
            "priority": priority,
            "recommendation": recommendation,
            "common_pattern": common["label"],
        }

    def _recommendation(
        self,
        learning_candidate: Mapping[str, Any],
        dominant: Mapping[str, Any],
        normalized_entropy: float,
    ) -> str:
        if dominant["label"] in {"successful_recovery", "efficient_grounded_execution"}:
            return (
                f"Promote the {dominant['label']} pattern, but preserve minor interpretations "
                "as watchlist signals for future evaluation."
            )
        if normalized_entropy >= 0.82:
            return (
                f"Hold multiple interpretations open for {dominant['label']} and collect one more "
                "evidence source before writing a permanent policy."
            )
        return (
            f"Write a {learning_candidate['update_type']} update: "
            f"{learning_candidate['recommendation']}."
        )

    def _summary(
        self,
        run: Mapping[str, Any],
        steps: Sequence[JsonDict],
        observations: Sequence[JsonDict],
        memories: Sequence[JsonDict],
        score: Mapping[str, Any],
    ) -> str:
        return (
            f"{run.get('agent_id')} executed {len(steps)} steps for '{run.get('goal')}'. "
            f"The run has {len(observations)} observations, {len(memories)} active memories, "
            f"and utility {float(score.get('utility', 0.0)):.2f}."
        )

    def _trajectory_text(
        self,
        run: Mapping[str, Any],
        steps: Sequence[JsonDict],
        observations: Sequence[JsonDict],
        memories: Sequence[JsonDict],
    ) -> str:
        parts = [clean_text(run.get("goal"))]
        for step in steps:
            parts.extend([step.get("kind"), step.get("status"), step.get("input"), step.get("output")])
        for observation in observations:
            parts.extend([observation.get("type"), observation.get("source"), observation.get("content")])
        for memory in memories[:40]:
            parts.extend([memory.get("memory_type"), memory.get("text")])
        return " ".join(clean_text(part) for part in parts if clean_text(part)).lower()

    def _add_signal(self, evidence: Dict[str, JsonDict], label: str, score: float, reason: str) -> None:
        if label not in evidence:
            return
        evidence[label]["score"] = float(evidence[label]["score"]) + max(0.0, score)
        if reason:
            cleaned = clean_text(reason)
            if cleaned and cleaned not in evidence[label]["evidence"]:
                evidence[label]["evidence"].append(cleaned[:180])

    def _softmax(self, scores: Sequence[float]) -> Dict[str, float]:
        temperature = 2.35
        scaled = [score * temperature for score in scores]
        max_score = max(scaled) if scaled else 0.0
        exps = [math.exp(score - max_score) for score in scaled]
        total = sum(exps) or 1.0
        return {label: exps[index] / total for index, label in enumerate(INTERPRETATION_LABELS)}

    def _term_count(self, text: str, terms: set) -> int:
        lowered = text.lower()
        return sum(1 for term in terms if term in lowered)

    def _joint_window_count(self, text: str, left_terms: set, right_terms: set) -> int:
        tokens = re.findall(r"[a-z0-9_]+", text.lower())
        count = 0
        for index, token in enumerate(tokens):
            if token not in left_terms:
                continue
            window = set(tokens[index + 1 : index + 8])
            if window & right_terms:
                count += 1
        return count

    def _mutual_information_proxy(self, left: float, right: float, joint: float) -> float:
        if not left or not right or not joint:
            return 0.0
        expected = max(1e-6, left * right)
        return clamp(joint * math.log(1 + joint / expected) / math.log(3))

    def _coupling_interpretation(self, left: str, right: str, coupling: float) -> str:
        if coupling >= 0.7:
            strength = "Strong"
        elif coupling >= 0.35:
            strength = "Moderate"
        elif coupling > 0:
            strength = "Weak"
        else:
            strength = "No"
        return f"{strength} interaction between {left} and {right}."
