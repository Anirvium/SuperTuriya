# SuperTuriya Product Workflow

This document explains what has been built so far, from step zero to a usable v1.

## 0. Product Intent

SuperTuriya is a Trajectory Intelligence platform for intelligent agents.

The product does not compete with a memory database, vector store, graph database, tracing tool, or evaluation script as a single commodity component. It sits above them as the intelligence layer that turns agent activity into durable improvement.

The core claim is:

> An intelligent agent should not only remember facts. It should understand the path by which it acted, where the path was coherent or fragile, what graph patterns explain the path, and which lessons should be written back into memory or policy.

## 1. What The System Ingests

SuperTuriya starts with raw operational signals:

- user messages
- assistant or agent decisions
- tool calls and tool results
- environment events
- feedback
- policy events
- manually supplied entities and relations
- trace steps with inputs, outputs, status, and memory references

These are captured through:

- `POST /observations`
- `POST /traces/start`
- `POST /traces/step`

The local dashboard exposes the same flow through the Trace, Step, and Observation panels.

## 2. Observation Layer

File: `superturiya/intelligence.py`

The observation layer normalizes incoming evidence into typed records. Each observation has:

- tenant and subject scope
- source
- type
- content
- entities
- relations
- labels
- provenance
- optional run and step IDs

Capitalized entities are inferred when explicit entities are not enough. Explicit relations and entity co-occurrence are converted into graph edges.

This is the base truth substrate of the product.

## 3. Memory Layer

File: `superturiya/intelligence.py`

The memory layer converts observations into deterministic memory candidates:

- episodic memory: what happened
- semantic memory: recurring facts and relations
- profile memory: user needs or preferences
- procedural memory: reusable lessons and recovery strategies

Memory extraction runs through:

- `POST /memories/extract`
- `POST /memories/search`

The current implementation is deterministic for testability. A model-backed extractor or vector database can be attached later without changing the product contract.

## 4. Graph Layer

Files: `superturiya/store.py`, `superturiya/intelligence.py`

The graph layer stores:

- subject-scoped nodes
- typed edges
- confidence
- temporal validity
- provenance through source observations

The graph is currently stored in SQLite, but its shape deliberately maps to graph infrastructure such as Neo4j.

The graph is used for:

- entity recurrence
- relation memory
- provenance display
- interpretation support
- experience-state graph discovery

## 5. Trace Layer

File: `superturiya/store.py`

Each agent run is stored as a trace:

- run ID
- tenant
- subject
- agent ID
- goal
- status
- metadata

Each trace step records:

- step index
- kind
- source
- input
- output
- status
- memory references
- optional tool call ID
- optional parent step ID

This gives SuperTuriya a full operational path rather than a final answer only.

## 6. Trajectory Scoring

File: `superturiya/intelligence.py`

The scoring layer evaluates the run across six dimensions:

- goal completion
- evidence grounding
- memory relevance
- step efficiency
- policy adherence
- recovery quality

These are combined into a utility score.

The engine also emits root-cause hypotheses such as:

- missing evidence
- weak memory routing
- tool failure
- stale or contradictory memory
- inefficient execution path
- healthy trajectory

Endpoint:

- `POST /trajectories/score`

## 7. Counterfactual Diagnostics

File: `superturiya/intelligence.py`

The counterfactual layer estimates how each step affected the trajectory. It asks:

- Did the step add evidence?
- Did it use memory?
- Did it introduce failure risk?
- Did it recover the path?
- Should it be kept, replaced, or promoted as procedural memory?

Endpoint:

- `POST /trajectories/counterfactuals`

## 8. Quantum-Inspired Interpretation

File: `superturiya/quantum_layer.py`

This layer is classical and deterministic. It uses quantum-inspired language as a mathematical metaphor for uncertainty and contextual interpretation.

It computes:

- latent trajectory state vector
- diagonal density-matrix approximation over interpretation hypotheses
- entropy and ambiguity level
- contextual measurement lenses
- dominant, common, and minor interpretations
- relational couplings
- learning candidate
- self-improvement recommendation

Interpretation labels include:

- retrieval context gap
- ambiguous user intent
- memory conflict
- tool selection error
- weak planning
- unsupported assumption
- policy or safety risk
- successful recovery
- efficient grounded execution

Endpoint:

- `POST /trajectories/quantum-interpret`

## 9. Experience-State Layer

File: `superturiya/quantum_layer.py`

This is the new layer inspired by the function-versus-experience finding from the D'Ariano/Faggin paper.

It does not claim the agent is conscious. It creates an ontic-inspired classical proxy for the inferred path condition of the trajectory.

It computes:

- function score: how well the run performed externally
- experience coherence: how stable, grounded, memory-aware, efficient, policy-aligned, and recoverable the path was
- function-experience gap: mismatch between external function and inferred path coherence
- hidden friction gap: high function score but lower coherence
- unresolved execution gap: coherent path but lower final success
- attention-memory fidelity: whether repeated evidence supports durable memory writeback
- state label: integrated flow, completed but fragile, coherent but unresolved, interpretively uncertain, turbulent path, or developing state

The attention-memory fidelity metric uses:

```text
(attention_repeats + 1) / (attention_repeats + latent_dimension_proxy)
```

This is an inspired product metric, not a physical quantum claim.

## 10. State Transition Graph Discovery

File: `superturiya/quantum_layer.py`

The experience-state layer emits a state transition graph. It links:

- initial latent path state
- observations
- memory recalls
- trace steps
- inferred after-step states
- score state
- relational interpretation edges

It also proposes graph-discovery candidates such as:

- memory recall stabilizes experience coherence
- weak evidence grounding widens the function-experience gap
- external success masks latent path friction
- focused attention repetition improves memory write fidelity
- retrieval quality couples with unsupported assumptions

This is the beginning of better graph discovery: the graph is no longer just a provenance diagram, it becomes a theory of how path state changes.

## 11. Policy Synthesis

File: `superturiya/intelligence.py`

Policies are synthesized from trajectory scores and root causes.

Examples:

- require evidence-linked final claims
- retrieve hybrid memory before planning
- stop low-novelty loops
- recover explicitly after failures
- resolve stale or contradictory memory
- promote high-utility trajectory patterns

Endpoint:

- `POST /policies/synthesise`

## 12. Governance

File: `superturiya/store.py`

The governance layer provides:

- audit events
- subject-scoped deletion
- local-first storage
- tenant and subject boundaries

Endpoint:

- `DELETE /subjects/{id}?tenant_id=demo`

## 13. Dashboard

Files: `web/index.html`, `web/app.js`, `web/styles.css`

The dashboard provides:

- executive strip for utility, graph, memory, and governance status
- trace creation
- step recording
- observation capture
- trajectory scoring
- simplified provenance map
- counterfactual audit
- interpretation panel
- experience-state panel
- memory search
- policy synthesis
- subject erasure

The new Experience State panel shows:

- function score
- coherence
- gap
- memory fidelity
- state label
- product readout
- state graph and discovered motifs

## 14. Storage

File: `superturiya/store.py`

The v1 storage engine is SQLite. It contains tables for:

- observations
- memories
- graph nodes
- graph edges
- traces
- trace steps
- trajectory scores
- quantum trajectory reports
- policies
- audit events

The report table stores the full structured interpretation report, so new analytical layers can be added without migrations.

## 15. Current Boundaries

The current version is intentionally local-first and dependency-light.

Implemented:

- local API
- local dashboard
- deterministic memory extraction
- SQLite graph and provenance store
- trajectory scoring
- counterfactuals
- quantum-inspired interpretation
- experience-state analysis
- state-transition graph discovery
- policy synthesis
- subject erasure

Integration boundaries:

- Neo4j for production graph storage
- Qdrant or another vector DB for embedding retrieval
- LangMem or equivalent for model-backed memory workflows
- OpenTelemetry for distributed traces
- model-based extraction, ranking, and evaluation

## 16. Scientific Positioning

SuperTuriya uses quantum-inspired and ontic-inspired concepts as product architecture:

- mixed state means uncertainty over interpretations
- contextual measurement means interpreting the same trace through different evaluation lenses
- entropy means ambiguity
- coupling means feature interaction
- experience state means inferred path condition
- attention-memory fidelity means repeated evidence improves writeback confidence

The system does not claim:

- physical quantum computation
- agent consciousness
- proof of quantum cognition
- direct measurement of subjective experience

The product claim is narrower and stronger:

> SuperTuriya makes agent trajectories state-aware, explainable, improvable, and governable.

