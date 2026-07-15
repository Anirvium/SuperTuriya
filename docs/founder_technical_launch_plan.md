# SuperTuriya: Product Launch, Demo Readiness, and Technical Execution Plan

Date: 2026-07-03

Audience: Founder, product owner, early engineering team, design partners, and technical advisors.

Purpose: This is the founder operating plan for taking SuperTuriya from the current repository into a demo-ready, design-partner-ready, and investor-ready product.

## 0. Founder Decision

Proceed.

SuperTuriya has a strong company thesis and a credible working POC. The product should now be pushed toward a narrow, proof-driven launch:

> SuperTuriya must become the best way to replay, understand, and improve failed AI agent trajectories.

The next milestone is not "build every enterprise feature."

The next milestone is:

> Real trace import + replay + before/after improvement demo.

Everything in this document supports that milestone.

## 1. Current Product Status Audit

### 1.1 What Is Already Built

The repository already contains a working local-first product skeleton.

Code and product surface:

- `superturiya/api.py`: standard-library HTTP API and static web server.
- `superturiya/store.py`: SQLite-backed control plane and provenance ledger.
- `superturiya/intelligence.py`: core engine for observations, memory, graph, traces, scoring, counterfactuals, policies, and dashboard state.
- `superturiya/quantum_layer.py`: quantum-inspired interpretation layer and experience-state analysis.
- `superturiya/sample_data.py`: seeded local demo scenario.
- `web/index.html`, `web/app.js`, `web/styles.css`: browser dashboard.
- `tests/test_superturiya.py`: end-to-end unit flow for observation -> memory -> trace -> score -> interpretation -> policies -> erasure.

Implemented capabilities:

- local server startup
- dashboard state endpoint
- health endpoint
- static dashboard serving
- typed observation capture
- entity extraction and co-occurrence relation generation
- memory extraction across episodic, semantic, profile, and procedural memory
- memory search
- subject-scoped graph nodes and edges
- trace and trace-step recording
- automatic observation capture from trace steps
- trajectory scoring
- root-cause hypotheses
- counterfactual step diagnostics
- quantum-inspired interpretation
- experience-state metrics
- state-transition graph payload in interpretation report
- policy synthesis
- subject-scoped deletion
- audit trail
- seed demo data
- founder docs, company roadmap, pitch-deck blueprint, product workflow docs

Current local API surface:

- `GET /health`
- `GET /dashboard/state`
- `GET /traces/{run_id}`
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

Current docs:

- `README.md`
- `docs/product_workflow.md`
- `docs/research_to_product.md`
- `docs/company_roadmap.md`
- `docs/pitch_deck_blueprint.md`
- `docs/founder_technical_launch_plan.md`

### 1.2 What Is Partially Built

These are real, but not yet production/demo-complete:

- Dashboard: good for POC, but not yet a polished investor/demo product.
- Provenance map: simplified and useful, but not yet a full replay or state-transition view.
- Experience-state layer: computed and surfaced, but needs stronger visual explanation.
- Policy synthesis: generates policies, but lacks accept/reject review queue.
- Demo data: one strong seeded scenario, but not the required 10-scenario demo set.
- Tests: one good end-to-end unit flow, but not enough coverage for launch readiness.
- API: works locally, but no auth, rate limits, request size limits, OpenAPI docs, or production hardening.
- Storage: SQLite is fine for local POC, but production needs Postgres or managed storage path.
- External integrations: integration boundaries are planned, but no LangGraph/OpenAI Agents SDK/OpenTelemetry import yet.
- Documentation: strong founder docs, but needs an API guide, demo guide, security guide, and deployment guide.

### 1.3 What Is Missing

Critical missing items before external design partners:

- JSON trace import endpoint.
- One real agent framework adapter.
- Replay view.
- Before/after trajectory comparison.
- Policy and procedural memory review queue.
- API key or workspace auth.
- Staging deployment.
- Dockerfile and `.env.example`.
- Public or private landing page.
- Demo video.
- Sanitized demo dataset.
- Security/privacy baseline.
- Design partner onboarding pack.

Critical missing items before investor/funder push:

- live staging URL or recorded product demo
- clear use-case wedge
- 3-5 design partner conversations
- at least one real or realistic trace case study
- measurable before/after improvement
- founder/company email
- pitch deck
- one-page memo
- technical architecture diagram
- product screenshots

### 1.4 What Needs Validation Before External Showings

Validate these before showing to funders or serious design partners:

- The seeded demo runs from a clean database.
- The README command starts the product successfully.
- The dashboard has no broken controls in the planned demo path.
- `Analyze` produces interpretation and experience-state output.
- Scoring and policy synthesis work on the seeded trace.
- Erasure works for the demo subject.
- Graph/provenance view is understandable to a non-author.
- The product story can be communicated in under 3 minutes.
- The demo does not require explaining quantum theory.
- The product can explain a failed trajectory better than raw logs.

## 2. Technical Readiness Checklist

### 2.1 Backend Requirements

Current state:

- Local HTTP server exists.
- Business logic is in `SuperTuriyaEngine`.
- Storage is in `SuperTuriyaStore`.
- Endpoints are manually routed.

Required next:

- Add `POST /integrations/traces/import`.
- Add a health endpoint with version/build info.
- Add request size limit.
- Add structured logging.
- Add API errors with stable error codes.
- Add API examples under `docs/api_examples.md`.
- Add OpenAPI-like documentation, even if manually authored.
- Add service config via environment variables.

Acceptance criteria:

- Any JSON trace can be imported and converted into a scored SuperTuriya run.
- API responses are predictable enough for SDK wrappers.
- A founder can demonstrate the product without touching code.

### 2.2 Frontend / Dashboard Requirements

Current state:

- Dashboard is functional and visually strong for POC.
- It supports trace creation, step recording, observation capture, scoring, counterfactuals, interpretation, experience state, memory, policies, governance, and a simplified provenance map.

Required next:

- Add trace import UI.
- Add replay mode.
- Add before/after comparison mode.
- Add state-transition graph panel.
- Add policy/memory review queue.
- Add loading states and error states.
- Add empty states for every panel.
- Add product screenshot-ready demo layout.

Acceptance criteria:

- A demo can be run entirely from the dashboard.
- The product value is visible within 60 seconds.
- The state graph is readable, not dense.

### 2.3 Database Requirements

Current state:

- SQLite tables cover observations, memories, graph nodes, graph edges, traces, trace steps, scores, quantum trajectory reports, policies, and audit events.

Required next:

- Add schema versioning.
- Add migration script or migration notes.
- Add Postgres-compatible schema plan.
- Add backup/restore guide.
- Add retention configuration.
- Add explicit indexes for common dashboard and import queries.

Acceptance criteria:

- Local SQLite remains the demo mode.
- Postgres becomes the design-partner staging path.
- Data deletion is clear and testable.

### 2.4 Trace Ingestion Requirements

Current state:

- Manual trace start/step endpoints exist.
- No batch trace import exists.

Required next:

- Use `docs/canonical_trace_schema_v0_1.md` as the canonical SuperTuriya trace import schema.
- Add JSON import endpoint.
- Add imported trace validation.
- Add import result summary.
- Add sample files under `examples/traces/`.
- Add one framework adapter.

Priority:

1. Generic JSON trace import.
2. LangGraph import.
3. OpenAI Agents SDK import.
4. OpenTelemetry/OpenInference import.
5. CrewAI or AutoGen import.

Acceptance criteria:

- A single JSON file can produce observations, trace steps, score, interpretation, and policy candidates.
- The importer can validate required/optional trace, step, memory, tool, retrieval, policy, model metadata, latency, token, cost, and error fields.

### 2.5 Memory And Provenance Graph Requirements

Current state:

- Deterministic memory extraction exists.
- Graph nodes/edges exist.
- Provenance references exist.

Required next:

- Store memory influence per step more explicitly.
- Add memory conflict labels.
- Add graph edge evidence preview.
- Add state-transition graph visualization.
- Add graph export.
- Define future Neo4j mapping.

Acceptance criteria:

- Demo can show which memory helped, misled, or conflicted.
- Graph view supports explanation, not decoration.

### 2.6 Evaluation And Scoring Requirements

Current state:

- Utility score covers goal completion, evidence grounding, memory relevance, step efficiency, policy adherence, and recovery quality.
- Root-cause hypotheses exist.
- Counterfactual diagnostics exist.

Required next:

- Add expected outcome support.
- Add manual evaluator labels.
- Add human-reviewed root-cause correctness field.
- Add before/after improvement metrics.
- Add score trend across similar runs.
- Keep `docs/evaluation_spec.md` updated as the scoring contract for utility, grounding, memory relevance, recovery, ambiguity, experience coherence, state gap, and policy acceptance.

Acceptance criteria:

- SuperTuriya can show improvement, not only diagnosis.
- Every investor or design partner metric maps to a documented formula or planned scoring rule.

### 2.7 Policy / Memory Writeback Requirements

Current state:

- Policies can be synthesized and stored.
- Procedural memory extraction exists.

Required next:

- Add candidate queue.
- Add accept/reject/defer states.
- Add accepted-by and accepted-at metadata.
- Add link from accepted update to evidence.
- Add diff view for policy writeback.

Acceptance criteria:

- Design partners trust recommendations because humans approve them first.

### 2.8 Authentication, Workspace, And User Management Requirements

Current state:

- No auth.
- Tenant/subject fields exist as logical scopes.

Required next:

- Add `workspace_id` or formalize tenant as workspace.
- Add API keys for ingestion.
- Add admin UI password or simple auth gate for staging.
- Add API-key-to-workspace mapping.
- Add key rotation.
- Add no-public-write rule for hosted deployment.

Acceptance criteria:

- One design partner cannot access another design partner's data.

### 2.9 Logging, Monitoring, And Error Handling Requirements

Current state:

- HTTP server suppresses default logs.
- Error responses exist but are simple.

Required next:

- Add structured request logs.
- Add audit log for imports, scoring, policy acceptance, deletion.
- Add frontend error toasts for all failed calls.
- Add uptime check.
- Add server-side exception log.
- Add lightweight product analytics.

Acceptance criteria:

- Founder can diagnose demo/staging failures quickly.

## 3. Repository Hardening Plan

### 3.1 Folder Structure Improvements

Recommended target:

```text
superturiya/
  api.py
  intelligence.py
  integrations/
    __init__.py
    trace_import.py
    langgraph.py
    openai_agents.py
  models.py
  quantum_layer.py
  sample_data.py
  store.py
examples/
  traces/
    completed_but_fragile.json
    memory_conflict.json
    tool_failure_recovery.json
docs/
  api_examples.md
  canonical_trace_schema_v0_1.md
  competitive_differentiation.md
  deployment.md
  demo_script.md
  design_partner_trace_request.md
  evaluation_spec.md
  security_baseline.md
  founder_technical_launch_plan.md
tests/
  test_superturiya.py
  test_trace_import.py
web/
  index.html
  app.js
  styles.css
```

### 3.2 README Updates

Already fixed:

- README now opens `http://127.0.0.1:8765` to match the run command.
- README now uses `python3 -m unittest discover -s tests` for verification.

Still needed:

- Add demo walkthrough.
- Add troubleshooting section.
- Add example API calls.
- Add "what is implemented vs planned" section.
- Add screenshots once available.

### 3.3 Setup Instructions

Required:

- Python version note.
- Clean install instructions.
- Run with seed instructions.
- Run tests instructions.
- Reset demo database instructions.
- Optional Docker instructions once Dockerfile exists.

### 3.4 Environment Variable Management

Add `.env.example` with:

```text
SUPERTURIYA_HOST=127.0.0.1
SUPERTURIYA_PORT=8765
SUPERTURIYA_DB=var/superturiya.db
SUPERTURIYA_ENV=local
SUPERTURIYA_REQUIRE_API_KEY=false
SUPERTURIYA_ADMIN_PASSWORD=
SUPERTURIYA_MAX_REQUEST_BYTES=1048576
```

### 3.5 Dependency Cleanup

Current product has no mandatory external runtime dependencies. Keep that advantage for local demo.

Required:

- Do not commit `.venv`, `.codex_deps`, or local databases.
- Keep `.gitignore` current.
- Add optional dependency groups later for `dev`, `server`, and `integrations`.

### 3.6 Test Coverage

Current:

- One end-to-end flow test.

Required:

- trace import test
- score edge-case test
- memory conflict test
- erasure test across all tables
- dashboard state test
- API route smoke test
- policy synthesis test
- experience-state report test

Acceptance criteria:

- `python3 -m unittest discover -s tests` passes from a clean checkout.

### 3.7 Seed / Demo Data

Current:

- one seeded healthcare-safe demo.

Required:

- 10 demo scenarios.
- At least one coding-agent scenario.
- At least one research-agent scenario.
- At least one support-agent scenario.
- At least one enterprise-workflow scenario.

### 3.8 Local Development Workflow

Add a small developer workflow:

```bash
python3 -m superturiya --seed --port 8765
python3 -m unittest discover -s tests
```

Optional later:

```bash
make demo
make test
make reset-demo
make docker-run
```

### 3.9 Deployment Scripts

Required:

- Dockerfile.
- docker-compose for local demo.
- deployment guide for one platform.
- health check.
- env var guide.

### 3.10 CI/CD Requirements

Minimum:

- run unit tests
- run Python compile check
- check formatting later
- prevent committing local DB files

CI can be GitHub Actions once repo is on GitHub.

## 4. Demo Readiness Plan

### 4.1 First Demo Scenario

Use this first:

> A stateful research or coding agent completes a task, but it uses weak evidence and stale memory. SuperTuriya detects the hidden fragility, identifies the root cause, and recommends a policy/memory update that improves the next run.

This is better than starting with healthcare because it avoids regulated-industry anxiety during early investor demos.

Recommended first external demo domain:

- coding agent failure
- research agent failure
- enterprise workflow agent failure

Keep healthcare/finance as future high-value regulated use cases.

### 4.2 Sample Agent Trajectory

Trace:

1. User asks agent to update a repo or research a topic.
2. Agent retrieves old memory or weak context.
3. Agent calls a tool.
4. Tool output is incomplete or ambiguous.
5. Agent makes unsupported assumption.
6. Agent completes the task but misses a test or citation.
7. SuperTuriya scores weak grounding and state gap.
8. SuperTuriya recommends "verify retrieved memory against fresh evidence before final output."
9. Improved run uses verification and scores higher.

### 4.3 Failure Case To Demonstrate

Best first failure:

> Completed but fragile.

Why:

- It is more subtle than a simple crash.
- It proves the value of trajectory intelligence.
- It lets you explain function score vs experience coherence.

### 4.4 Before / After Improvement Loop

Before:

- function score acceptable
- experience coherence low
- high function-experience gap
- root cause: weak evidence grounding or memory conflict

After:

- better evidence grounding
- lower ambiguity
- lower state gap
- accepted policy or memory update

### 4.5 Required Dashboard Screens

Before serious demos:

- trace import
- run replay
- trajectory score
- root-cause explanation
- interpretation
- experience state
- simplified state-transition graph
- policy/memory review queue
- before/after comparison
- export report

### 4.6 Metrics To Show

In demo:

- utility score
- evidence grounding
- memory relevance
- recovery quality
- ambiguity score
- function score
- experience coherence
- function-experience gap
- accepted policy/memory update
- before/after improvement delta

### 4.7 Demo Story

Investor/design partner message:

> Existing tools show spans and final evals. SuperTuriya explains the whole trajectory and closes the loop from failure to improvement.

## 5. Data And Evidence Requirements

### 5.1 Synthetic Traces To Create

Create 10 traces:

1. retrieval context gap
2. ambiguous user intent
3. memory conflict
4. tool selection error
5. weak planning loop
6. unsupported assumption
7. policy/safety risk
8. successful recovery
9. efficient grounded execution
10. completed but fragile

### 5.2 Real Traces To Collect

Collect sanitized traces from:

- coding agents
- research agents
- customer support agents
- internal workflow agents

For each trace, collect:

- framework used
- user goal
- steps
- tool calls
- tool outputs
- retrieval events
- memory events
- final response/action
- human rating
- known root cause if available

### 5.3 Metadata Required

Minimum metadata:

- `trace_id`
- `tenant_id`
- `subject_id`
- `agent_id`
- `framework`
- `goal`
- `started_at`
- `ended_at`
- `status`
- `step_index`
- `step_kind`
- `source`
- `input`
- `output`
- `tool_call_id`
- `memory_refs`
- `retrieval_refs`
- `labels`
- `expected_outcome`
- `human_eval`

### 5.4 Evaluation Labels

Add labels:

- final success
- evidence grounding
- memory relevance
- policy adherence
- tool correctness
- planning quality
- recovery quality
- repeated failure type
- human root cause
- accepted improvement

### 5.5 Dataset Structure

Recommended:

```text
examples/traces/
  synthetic/
  sanitized/
  before_after/
```

Each scenario should have:

- `trace.json`
- `expected_report.json`
- `notes.md`
- optional `after_trace.json`

## 6. Infrastructure And Deployment Requirements

### 6.1 Recommended Cloud Options

For first staging:

- Render
- Fly.io
- Railway
- Google Cloud Run
- AWS App Runner

Best first choice:

> Use the simplest platform where you can deploy quickly with HTTPS, env vars, logs, and persistent database.

### 6.2 Local-First Deployment

Keep local-first mode as a differentiator.

Local mode should support:

- no required external services
- seeded demo
- local SQLite
- static dashboard
- import local JSON traces

### 6.3 Hosted SaaS Path

For design partners:

- hosted backend
- hosted dashboard
- project/workspace auth
- API ingestion keys
- Postgres
- object storage for exports
- basic analytics
- HTTPS

### 6.4 Database Choices

Now:

- SQLite for POC.

Next:

- Postgres for hosted design partner product.

Later:

- Neo4j for advanced graph workloads.
- Qdrant/pgvector for vector retrieval if needed.

### 6.5 Vector Database Requirements

Do not add a vector database until trace import and replay are working.

When needed:

- memory semantic search
- similar trajectory retrieval
- failure-pattern clustering
- policy recommendation retrieval

Initial choices:

- pgvector
- Qdrant

### 6.6 Graph Database Requirements

Do not migrate graph storage too early.

First prove:

- graph edges improve diagnosis
- state-transition motifs matter
- customers care about graph-backed provenance

Then evaluate:

- Neo4j Aura
- Postgres graph tables
- hybrid Postgres + Neo4j

### 6.7 Storage Requirements

Need storage for:

- exported reports
- trace import files
- screenshots
- demo videos

Use:

- S3
- GCS
- Azure Blob

### 6.8 Observability Stack

For SuperTuriya itself:

- structured logs
- request logs
- error logs
- uptime monitor
- product analytics
- import success/failure metrics

Later:

- OpenTelemetry instrumentation for SuperTuriya backend.

### 6.9 Security And Governance

Minimum before design partners:

- API key ingestion
- workspace isolation
- HTTPS
- request size limit
- no secrets in logs
- deletion endpoint documented
- privacy policy
- terms of use
- data retention policy
- "do not send sensitive production data" warning during alpha
- `docs/security_baseline.md` reviewed and shared in design partner onboarding when appropriate

Do not claim SOC 2/HIPAA/GDPR readiness until reviewed properly.

## 7. Domain, Brand, And Product Surface

### 7.1 SuperTuriya.ai

`SuperTuriya.ai` is a good domain choice if available.

Why:

- memorable
- distinctive
- AI-native
- aligned with the product's "higher-order intelligence" theme

Risks:

- some people may not know how to spell it
- "Turiya" may need a one-line explanation
- domain availability can change quickly

Recommended:

- buy `superturiya.ai` if available
- also secure `superturiya.com` or `superturiya.io` if affordable
- reserve GitHub org and LinkedIn company page

### 7.2 Brand Assets Required

Minimum:

- logo
- favicon
- color system
- typography
- dashboard screenshots
- architecture diagram
- 1-line and 2-line descriptions
- founder headshot/bio
- demo video thumbnail

### 7.3 Landing Page Structure

Page sections:

1. Hero:
   > Trajectory Intelligence for state-aware AI agents.
2. Problem:
   > Agent failures are path failures.
3. Solution:
   > Connect traces, memory, graph, state, evaluation, and policy writeback.
4. Product demo video.
5. Use cases.
6. Architecture.
7. Design partner CTA.
8. Contact.

Primary CTA:

> Join the design partner program

### 7.4 Product Messaging

Use:

> SuperTuriya helps AI teams replay, understand, and improve failed agent trajectories.

Avoid leading with:

- quantum
- consciousness
- metaphysics
- "human era" language

Use deeper research only after the buyer understands the practical pain.

### 7.5 Demo Video Requirements

Create two videos:

- 2-3 minute investor/design partner demo
- 7-10 minute technical demo

The 2-3 minute demo must show:

- failed or fragile trajectory
- SuperTuriya diagnosis
- state gap
- policy/memory recommendation
- before/after improvement

### 7.6 Investor Deck Alignment

Use `docs/pitch_deck_blueprint.md` as source.
Use `docs/competitive_differentiation.md` for the category and competitor slide.

Deck spine:

- title
- inflection
- problem
- bottlenecks
- solution
- workflow
- demo
- use cases
- architecture
- differentiation
- GTM
- roadmap
- ask

### 7.7 Design Partner Onboarding Material

Prepare:

- one-page product memo
- demo video
- trace data request using `docs/design_partner_trace_request.md`
- privacy note
- design partner agreement draft
- onboarding checklist
- expected weekly feedback cadence

## 8. Fundraising And Design Partner Readiness

### 8.1 Before Contacting Design Partners

Need:

- staging or local demo video
- trace import schema from `docs/canonical_trace_schema_v0_1.md`
- privacy statement
- security baseline from `docs/security_baseline.md`
- design partner trace request from `docs/design_partner_trace_request.md`
- sample reports
- clear ask: "give us 20-100 sanitized traces"
- expected outcome: "we will identify repeated trajectory failures"

### 8.2 Before Contacting Investors

Need:

- pitch deck
- demo video
- landing page
- product screenshots
- founder story
- 30/60/90 day plan
- design partner pipeline
- one concrete case study if possible

### 8.3 Metrics To Track

Product metrics:

- traces ingested
- failed traces analyzed
- recurring patterns detected
- accepted policy/memory updates
- before/after utility delta
- state gap reduction
- root-cause agreement with human reviewers

Business metrics:

- design partner conversations
- active design partners
- weekly active projects
- pilots requested
- LOIs
- paid pilots

### 8.4 Proof Points To Create

Strong proof point:

> SuperTuriya reduced repeated agent failures by X% across Y traces.

Early proof point:

> In 20 sanitized traces, SuperTuriya identified 6 repeated failure patterns and generated 4 accepted policy updates.

### 8.5 Technical Credibility Assets

Prepare:

- architecture diagram
- API examples
- trace schema
- sample trajectory report
- security baseline
- benchmark memo
- state-transition graph example
- competitive differentiation memo

### 8.6 Competitive Differentiation

Use `docs/competitive_differentiation.md` as the source for investor, design partner, and deck positioning.

The direct claim:

> SuperTuriya is not trying to be another generic LLM tracing tool. It is the trajectory intelligence layer for state-aware agents.

SuperTuriya should explicitly compare against LangSmith, Braintrust, Phoenix, Langfuse, and OpenTelemetry/OpenInference.

Win on:

- memory-aware provenance
- state-transition scoring
- function-experience gap
- policy/memory writeback
- graph-backed pattern discovery
- before/after trajectory improvement

Do not overclaim:

- enterprise compliance
- broad framework coverage
- generic observability superiority
- physical quantum computing

The funder proof metric remains:

> Reduce recurring agent trajectory failures after approved memory or policy writeback.

## 9. 30-Day Execution Plan

### Week 1: Demo Foundation

Technical:

- create `examples/traces/`
- use the canonical trace import schema
- implement `POST /integrations/traces/import`
- add 3 synthetic traces
- update README demo workflow

Product:

- freeze demo story
- choose first demo domain: coding or research agent
- define before/after metrics

Founder/GTM:

- check and buy domain if available
- create design partner target list
- draft landing page copy

Acceptance criteria:

- one JSON trace can be imported and scored end-to-end

### Week 2: Replay And Comparison

Technical:

- build replay screen
- build before/after comparison payload
- add comparison UI
- improve state graph display

Product:

- create 10 scenario outlines
- create demo script
- capture first screenshots

Founder/GTM:

- write one-page memo
- contact 5 friendly technical reviewers

Acceptance criteria:

- demo shows a failed run and improved run side by side

### Week 3: Integration And Staging

Technical:

- add LangGraph or OpenAI Agents SDK adapter
- add Dockerfile
- add `.env.example`
- add API key ingestion gate
- deploy staging

Product:

- polish dashboard demo route
- add policy/memory candidate review queue skeleton

Founder/GTM:

- record first 3-minute demo video
- start 15 customer discovery conversations

Acceptance criteria:

- staging URL works with seeded demo

### Week 4: Design Partner Package

Technical:

- add exportable markdown report
- add trace import examples
- add test coverage for trace import

Product:

- finish 10 demo traces
- finalize landing page
- finalize pitch deck draft

Founder/GTM:

- invite 3-5 design partners
- apply for startup credits
- prepare accelerator application drafts

Acceptance criteria:

- founder can run demo, send deck, send video, and ask for traces

## 10. 60-Day And 90-Day Roadmap

### Day 60 Target

Product:

- trace import stable
- replay/comparison working
- state graph usable
- policy/memory review queue functional
- landing page live
- demo video live

Technical:

- one framework adapter
- staging deployment
- API key ingestion
- 20+ tests or meaningful focused coverage
- deployment guide

GTM:

- 3 design partners in active discussion or testing
- 50+ traces collected or synthetically modeled
- first case study draft

### Day 90 Target

Product:

- 100+ traces analyzed
- recurring failure pattern dashboard
- exportable reports
- accepted policy/memory update workflow

Technical:

- hosted design partner environment
- basic workspace isolation
- privacy/security docs
- backup/restore plan

GTM:

- 3+ design partners
- 1 paid pilot or LOI target
- investor deck complete
- before/after improvement metric

### Ready For Paid Pilots

Need:

- security baseline
- private workspace
- import adapter
- support process
- weekly report
- deletion/export controls
- clear pilot scope

### Ready For Investor Conversations

Need:

- live demo or video
- clear category narrative
- one specific ICP
- design partner evidence
- proof metric or strong qualitative case study

## 11. External Programs And Launch Support

Use these after domain, website, and demo are ready:

- YC application: https://www.ycombinator.com/apply
- AWS Startups / Activate: https://aws.amazon.com/startups/
- Google for Startups Cloud Program: https://cloud.google.com/startup
- Microsoft for Startups: https://www.microsoft.com/en-us/startups
- NVIDIA Inception: https://www.nvidia.com/en-us/startups/
- Neo4j Startup Program: https://neo4j.com/startup-program/

Practical sequencing:

1. Buy domain and create landing page.
2. Record demo.
3. Apply for cloud/startup credits.
4. Start design partner outreach.
5. Apply to accelerators when product proof is stronger.

## 12. Risk Register

### 12.1 Technical Risks

Risk: Product remains a local demo.

Mitigation:

- add Dockerfile
- deploy staging
- add API key ingestion
- add trace import

Risk: Graph becomes too complex to understand.

Mitigation:

- keep graph visual simple
- show only top state transitions and motifs
- use graph as explanation, not decoration

Risk: Scoring feels arbitrary.

Mitigation:

- expose evidence behind each metric
- add human labels
- compare before/after runs
- validate with design partners

### 12.2 Product Risks

Risk: Users see it as another observability dashboard.

Mitigation:

- lead with replay -> root cause -> writeback
- show improvement loop
- avoid generic traces-only positioning

Risk: Too much quantum/philosophical framing.

Mitigation:

- keep research framing in docs
- pitch agent reliability and trajectory intelligence

### 12.3 Market Risks

Risk: Existing observability platforms copy features.

Mitigation:

- focus on memory-aware provenance and policy writeback
- build dataset and workflow moat
- integrate with existing trace sources

Risk: Teams are not ready to pay.

Mitigation:

- target teams already running agents in production
- measure debugging time saved
- measure repeated failures reduced

### 12.4 Fundraising Risks

Risk: Investors think it is too early.

Mitigation:

- show working product
- show design partners
- show trace count
- show before/after improvement

Risk: Category is unclear.

Mitigation:

- use "Trajectory Intelligence for state-aware AI agents"
- explain as layer above traces, memory, evals, and policies

### 12.5 Execution Risks

Risk: Solo founder scope overload.

Mitigation:

- focus on one integration
- one demo story
- one ICP
- one proof metric

Risk: Spending too much before validation.

Mitigation:

- use startup credits
- avoid enterprise compliance spend
- use contractors only for focused deliverables

## 13. Final Founder Action Checklist

### Immediate Actions Today

- Choose first demo domain: coding agent or research agent.
- Confirm whether `SuperTuriya.ai` is available.
- Create 10 trace scenario names.
- Choose first integration: LangGraph or OpenAI Agents SDK.
- Draft design partner target list.

### Before Buying The Domain

- Check spelling and pronunciation risk.
- Search for obvious trademark conflicts.
- Check `.ai`, `.com`, `.io`.
- Decide official capitalization: SuperTuriya.

### Before Launching The Landing Page

- Have product one-liner.
- Have 3 screenshots or demo video.
- Have design partner CTA.
- Have privacy/contact page.
- Have founder/company email.

### Before Recording The Demo

- Seed database from clean state.
- Verify dashboard flow.
- Verify scoring and analysis.
- Verify experience-state output.
- Prepare backup screenshots.
- Write the 2-3 minute script.

### Before Pitching Investors

- Have deck.
- Have demo video.
- Have live or local demo.
- Have exact ICP.
- Have design partner pipeline.
- Have 30/60/90 plan.
- Have clear funding ask.

### Before Onboarding Design Partners

- Have data request template.
- Have privacy note.
- Have API key or private ingestion path.
- Have deletion/export policy.
- Have weekly feedback cadence.
- Have support contact.

## 14. Final Reassurance

The product direction is coherent and worth continuing.

The strongest part is not the quantum-inspired layer alone. The strongest part is the full closed loop:

> trace -> memory -> graph -> score -> state -> root cause -> policy/memory writeback -> improved next run

That is the company.

Keep the next build focused:

> Import real traces, replay failures, compare before/after improvement, and win design partners.
