# SuperTuriya

SuperTuriya is a local-first Trajectory Intelligence platform for state-aware agents. It turns agent runs into typed observations, memory, provenance graph structure, trajectory scores, counterfactual diagnostics, experience-state analysis, procedural policies, and governance actions.

The research brief in `Trajectory Intelligence.pdf` argues that the durable product layer is above commodity memory: agents need to remember, justify, improve, and govern decisions over time. This repository implements that thesis as a working v1.

## Product Definition

SuperTuriya is the command layer between raw agent execution and durable agent improvement.

It answers:

- What did the agent observe?
- What memory should be extracted or recalled?
- Which graph relations explain the path?
- Did the trajectory succeed functionally?
- Did the path remain coherent, grounded, and recoverable?
- Which hidden patterns should become reusable policy or memory?
- Which subject data can be audited or erased?

## Run

```bash
python3 -m superturiya --seed --port 8765
```

Then open:

```text
http://127.0.0.1:8765
```

## API Surface

- `POST /observations`
- `POST /memories/extract`
- `POST /memories/search`
- `POST /graphs/upsert`
- `POST /traces/start`
- `POST /traces/step`
- `POST /trajectories/score`
- `POST /trajectories/counterfactuals`
- `POST /trajectories/quantum-interpret`
- `POST /policies/synthesise`
- `DELETE /subjects/{id}?tenant_id=demo`

## Verify

```bash
python3 -m unittest discover -s tests
```

## Architecture

- `superturiya/store.py`: SQLite control plane and provenance ledger.
- `superturiya/intelligence.py`: observation normalization, memory synthesis, graph induction, scoring, counterfactuals, and policy synthesis.
- `superturiya/quantum_layer.py`: quantum-inspired relational trajectory interpretation, ambiguity entropy, contextual measurement lenses, experience-state analysis, state-transition graph discovery, and learning candidates.
- `superturiya/api.py`: standard-library HTTP API and static app server.
- `web/`: operational dashboard for ingest, search, graph, scores, policies, and governance.
- `docs/product_workflow.md`: structural zero-to-one walkthrough of the product and loop.
- `docs/company_roadmap.md`: startup path, ICP, milestones, fundraising readiness, and next build priorities.
- `docs/pitch_deck_blueprint.md`: slide-by-slide investor deck structure and context for ChatGPT Canvas, Figma, Canva, or PowerPoint.
- `docs/founder_technical_launch_plan.md`: founder-focused technical launch plan, demo readiness checklist, resource plan, domain/brand prerequisites, and funding prep.
- `docs/canonical_trace_schema_v0_1.md`: canonical trace contract for steps, memory, tools, retrieval, policy events, usage, cost, latency, and errors.
- `docs/competitive_differentiation.md`: direct positioning against LangSmith, Braintrust, Phoenix, Langfuse, and OpenTelemetry/OpenInference.
- `docs/evaluation_spec.md`: utility, grounding, memory relevance, recovery, ambiguity, experience coherence, state-gap, and policy acceptance scoring logic.
- `docs/security_baseline.md`: PII redaction, secret masking, API key handling, tenant isolation, deletion, retention, and audit behavior.
- `docs/design_partner_trace_request.md`: ready-to-send request template for sanitized traces, labels, framework context, and debugging workflow.

This version has no mandatory external runtime dependencies. Neo4j, Qdrant, LangMem, and OpenTelemetry are represented as explicit integration boundaries rather than required services, so the product can be run and tested immediately.

## Intelligence Loop

1. Observe: capture messages, tool outputs, feedback, policy events, and environment signals.
2. Synthesize: convert observations into episodic, semantic, profile, and procedural memory.
3. Connect: build subject-scoped graph nodes and temporal/provenance edges.
4. Trace: record every agent step with inputs, outputs, status, source, and memory refs.
5. Score: compute utility from completion, grounding, memory relevance, efficiency, policy adherence, and recovery.
6. Interpret: estimate dominant/common/minor trajectory interpretations and ambiguity entropy.
7. Experience State: compare function score with inferred path coherence, memory fidelity, and graph-discovered state transitions.
8. Improve: synthesize reusable policies and procedural memory from failures and successful patterns.
9. Govern: audit actions and erase subject-scoped data when required.

## Scientific Positioning

The interpretation layer is quantum-inspired, not quantum computing. It uses density-matrix language as an explainable mathematical metaphor for uncertainty over competing trajectory interpretations. The v1 implementation is classical and deterministic: it computes a normalized latent vector, a diagonal mixed-state distribution over interpretation labels, contextual measurement lenses, entropy-based ambiguity, graph-derived coupling, experience-state coherence, attention-memory fidelity, and self-improvement recommendations.

The experience-state layer is ontic-inspired only as a product model: it distinguishes external function from inferred internal path condition. It does not claim the agent is conscious or that the product uses physical quantum cognition.
