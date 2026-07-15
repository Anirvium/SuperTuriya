# Research To Product Translation

The PDF frames SuperTuriya as a Trajectory Intelligence platform, not a generic memory API.

## Product Thesis

Memory is necessary but increasingly commoditized. The defensible layer is the system that converts observations, tool calls, retrieved memories, graph structure, provenance, and execution traces into measurable reasoning quality and reusable improvement.

## Implemented V1 Modules

1. Observation Capture: typed observation ingestion with entities, relations, labels, and provenance.
2. Memory Synthesis: deterministic episodic, semantic, profile, and procedural memory extraction.
3. Graph Intelligence: subject-scoped nodes, temporal relations, co-occurrence edges, and provenance.
4. Trajectory Evaluation: goal completion, evidence grounding, memory relevance, step efficiency, policy adherence, recovery quality, and utility.
5. Optimization Loop: policy synthesis from low-scoring or successful trajectories.
6. Governance Layer: subject-scoped erasure across observations, memories, graph, traces, scores, policies, and audit events.
7. Quantum-Inspired Relational Interpretation: dominant/common/minor trajectory interpretations, entropy-based ambiguity, contextual measurement lenses, coupling signals, and learning candidates.
8. Experience-State Analysis: function score, experience coherence, function-experience gap, hidden friction, attention-memory fidelity, and state-transition graph discovery.

## Deliberate V1 Choices

- SQLite is the durable control plane for a runnable local product.
- Lexical hybrid ranking stands in for Qdrant until vector infrastructure is attached.
- Graph tables stand in for Neo4j while preserving node, edge, temporal, and provenance semantics.
- Trace records mirror OpenTelemetry span ideas without requiring an collector.
- Deterministic extractors make tests stable; model-backed extractors can be plugged in later.
- The quantum-inspired layer uses classical probability and graph features. It must not be marketed as quantum computing or evidence that human/agent cognition is physically quantum.
- The experience-state layer is ontic-inspired only as a product model. It separates observable function from inferred path condition, helping identify trajectories that technically completed but remained fragile, ambiguous, or poorly grounded.
