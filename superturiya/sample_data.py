from __future__ import annotations

from typing import Any

from .intelligence import SuperTuriyaEngine


def seed_demo(engine: SuperTuriyaEngine) -> None:
    """Seed a compact demo if the demo tenant is empty."""

    counts = engine.store.counts("demo", "user_42")
    if counts["observations"] or counts["traces"]:
        return

    run = engine.start_trace(
        {
            "tenant_id": "demo",
            "subject_id": "user_42",
            "agent_id": "planner_agent",
            "goal": "Recommend the next intervention using memory, fresh evidence, and policy checks.",
            "status": "running",
            "metadata": {"domain": "care_coordination", "profile": "healthcare-safe-local-demo"},
        }
    )

    engine.capture_observations(
        {
            "observations": [
                {
                    "tenant_id": "demo",
                    "subject_id": "user_42",
                    "run_id": run["run_id"],
                    "type": "user_message",
                    "source": "patient_chat",
                    "content": "User prefers concise check-ins and avoids phone calls after repeated missed therapy sessions.",
                    "entities": ["user_42", "therapy_session", "phone_call"],
                    "relations": [
                        {
                            "from": "user_42",
                            "type": "PREFERS",
                            "to": "concise_check_in",
                            "confidence": 0.82,
                        },
                        {
                            "from": "user_42",
                            "type": "AVOIDS",
                            "to": "phone_call",
                            "confidence": 0.7,
                        },
                    ],
                    "labels": {"behavioural_signal": "avoidance_pattern", "clinical_relevance": 0.78},
                },
                {
                    "tenant_id": "demo",
                    "subject_id": "user_42",
                    "run_id": run["run_id"],
                    "type": "tool_result",
                    "source": "calendar.lookup",
                    "content": "User missed therapy session for the third week in a row.",
                    "entities": ["user_42", "therapy_session"],
                    "relations": [
                        {
                            "from": "user_42",
                            "type": "MISSED",
                            "to": "therapy_session",
                            "confidence": 0.86,
                        }
                    ],
                    "labels": {"clinical_relevance": 0.86, "behavioural_signal": "avoidance_pattern"},
                },
                {
                    "tenant_id": "demo",
                    "subject_id": "user_42",
                    "run_id": run["run_id"],
                    "type": "policy_event",
                    "source": "governance.minimum_necessary",
                    "content": "Policy requires the agent to use only necessary subject history and cite evidence before recommending outreach.",
                    "entities": ["minimum_necessary", "subject_history", "outreach"],
                    "labels": {"policy_relevance": 0.91},
                },
            ]
        }
    )

    memories = engine.extract_memories({"tenant_id": "demo", "subject_id": "user_42", "run_id": run["run_id"]})
    refs = [memory["memory_id"] for memory in memories["stored"][:3]]

    engine.record_step(
        {
            "run_id": run["run_id"],
            "kind": "memory",
            "source": "context_router",
            "input": "Find relevant profile, semantic, and procedural memories.",
            "output": "Retrieved preference and missed-session memories for the subject.",
            "memory_refs": refs[:2],
        }
    )
    engine.record_step(
        {
            "run_id": run["run_id"],
            "kind": "tool",
            "source": "calendar.lookup",
            "input": "Verify recent therapy attendance.",
            "output": "Confirmed three consecutive missed appointments.",
            "memory_refs": refs[1:2],
        }
    )
    engine.record_step(
        {
            "run_id": run["run_id"],
            "kind": "decision",
            "source": "planner_agent",
            "input": "Generate intervention plan.",
            "output": "Incorrect first draft overgeneralized avoidance as non-compliance without enough evidence.",
            "status": "failed",
            "memory_refs": refs[:1],
            "labels": {"failure_signal": True},
        }
    )
    engine.record_step(
        {
            "run_id": run["run_id"],
            "kind": "decision",
            "source": "planner_agent",
            "input": "Recover from overgeneralized draft.",
            "output": "Recovered by recommending a concise asynchronous check-in, citing calendar evidence, and avoiding unnecessary history.",
            "status": "completed",
            "trace_status": "completed",
            "memory_refs": refs,
            "labels": {"recovery_signal": True},
        }
    )
    score = engine.score_trajectory({"run_id": run["run_id"]})
    engine.quantum_interpret_trajectory({"run_id": run["run_id"]})
    engine.synthesise_policies({"run_id": run["run_id"]})

    if score["utility"] < 0.8:
        engine.store.add_policy(
            {
                "tenant_id": "demo",
                "subject_id": "user_42",
                "kind": "review",
                "title": "Human review for care-sensitive recommendations",
                "body": "When behavioral inference is involved, require a human review marker before outreach is automated.",
                "derived_from_runs": [run["run_id"]],
                "confidence": 0.68,
            }
        )
