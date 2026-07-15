# SuperTuriya Company Roadmap

This is the practical path from current POC to a fundable company.

## Executive Verdict

SuperTuriya should proceed, but the company must start with a narrow wedge.

The broad vision is:

> Trajectory Intelligence for state-aware, self-improving AI agents.

The first market wedge should be:

> Debug, evaluate, and improve production AI agents from trace to memory to policy.

Do not lead with quantum-inspired language in the investor pitch. Keep it as research depth.
Lead with agent reliability, observability, optimization, and governance.

## Current Score

- Product thesis: 85 / 100
- Current built product: 62 / 100
- VC fundability today without pilots: 35-45 / 100
- VC fundability after strong POC and design partners: 72-78 / 100
- VC fundability after paid pilots with measurable ROI: 82+ / 100

## Why This Can Become A Company

The agent observability market is real. Teams building agents need more than logs:

- they need to see what happened
- why it happened
- which memory influenced the decision
- where the agent path became fragile
- whether the task succeeded for the right reason
- how to turn failure into policy, memory, or guardrails

Existing observability and eval platforms prove demand, but SuperTuriya's wedge is trajectory intelligence:

- memory-aware tracing
- graph-backed provenance
- function-experience gap
- state-transition graph discovery
- policy and memory writeback
- governance for subject-scoped agent memory

## Category Positioning

SuperTuriya should not be positioned as another LLM dashboard.

Position as:

> The trajectory intelligence layer for agentic systems.

One-line description:

> SuperTuriya helps AI teams trace, understand, and improve agent behavior by connecting execution paths, memory, provenance, evaluation, and policy writeback.

Sharper enterprise version:

> SuperTuriya turns messy agent runs into auditable trajectories, root-cause insights, and reusable improvement policies.

## Ideal Customer Profile

Start with teams that already have agent pain.

Best first ICP:

1. AI engineering teams building coding agents, research agents, or internal workflow agents.
2. Enterprise AI platform teams deploying multi-step LLM workflows.
3. Regulated teams where memory, provenance, and audit matter.
4. AI-native startups running agents in production.

Avoid at first:

- generic chatbot builders
- consumers
- teams without production traces
- buyers who only want prompt management

## Beachhead Use Case

The first killer workflow should be:

> Replay a failed agent run, identify why it failed, and generate the policy or memory update that prevents recurrence.

The demo should show:

1. Agent run starts.
2. Tool call or memory retrieval goes wrong.
3. SuperTuriya captures trace, observations, memory refs, graph edges.
4. System scores utility and root causes.
5. Experience-state layer shows hidden fragility or state gap.
6. State graph shows where memory/evidence/tool behavior shifted the path.
7. System writes a policy or procedural memory.
8. Same run or similar run improves.

This is the wedge investors and customers can understand.

## Product Milestones

### Phase 1: POC To Demo-Grade Product

Target: 2-4 weeks.

Build:

- LangGraph or OpenAI Agents SDK ingestion adapter
- JSON trace import endpoint
- trace replay view
- before/after trajectory comparison
- clearer root-cause panel
- exportable trajectory report
- demo dataset with 10 realistic agent failures

Success bar:

- anyone can run a demo in under 5 minutes
- product explains a failed trajectory better than raw logs
- product produces a useful policy or memory update

### Phase 2: Design Partner Product

Target: 4-8 weeks.

Build:

- hosted or simple Docker deployment
- auth-light workspace model
- project-level trace ingestion keys
- OpenTelemetry/OpenInference-compatible import path
- agent framework SDK wrappers
- evaluator plugin interface
- dataset of recurring trajectory failures
- dashboard for repeated failure patterns

Success bar:

- 3-5 design partners using it on real traces
- at least 100 real agent runs ingested
- 3 concrete case studies where SuperTuriya found a failure pattern

### Phase 3: Paid Pilot

Target: 8-16 weeks.

Build:

- team accounts
- role-based access basics
- retention controls
- PII/subject deletion workflows
- alerting on high-risk trajectory patterns
- integration with Slack/Jira/GitHub
- policy writeback review queue

Success bar:

- 2-3 paid pilots
- clear ROI metric
- customer quote
- repeat usage every week

### Phase 4: Seed-Ready Company

Target: 4-6 months.

Needed:

- 5-10 design partners
- 2-5 paid customers
- clear wedge with repeatable pain
- demo that creates urgency in under 3 minutes
- credible technical moat
- founder narrative
- investor deck
- one benchmark or report on agent trajectory failures

## What To Build Next

Priority order:

1. Trace import standardization.
2. Agent framework adapters.
3. Failure replay and before/after comparison.
4. State-transition graph visualization.
5. Policy/memory writeback review queue.
6. Integration with GitHub issues or coding-agent logs.
7. Hosted deployment path.

Do not build first:

- generic vector database UI
- broad workflow automation
- too many graph visualizations
- heavy quantum branding
- enterprise compliance before design partners

## Technical Moat

The moat cannot be "we store traces." Many companies can do that.

The moat should become:

- proprietary taxonomy of agent trajectory failure modes
- memory-aware provenance graph
- state-transition scoring
- function-experience gap metric
- policy/memory writeback loop
- dataset of real-world agent trajectories
- integration depth with agent frameworks
- workflow that improves agents, not just observes them

## Investor Narrative

Problem:

AI agents are moving from demos to production, but teams cannot reliably understand why they fail, what memory affected them, or how to prevent repeat failures.

Current tools:

Tracing tools show what happened. Eval tools score outputs. Memory systems store context. But teams still lack a trajectory-level intelligence layer that connects trace, memory, graph, state, root cause, and improvement.

Solution:

SuperTuriya turns agent runs into auditable trajectories and converts failures into durable memory, policies, and optimization loops.

Why now:

Agent adoption is accelerating. More autonomy creates more failures, more audit risk, and more need for process-level observability.

Why us:

We are building from a deeper trajectory-intelligence thesis: agents need memory, provenance, state awareness, and self-improvement loops as one system.

## Fundraising Strategy

Do not raise from cold pitch alone.

Best path:

1. Build demo-grade POC.
2. Get 3-5 design partners.
3. Publish a sharp technical memo: "The Agent Trajectory Failure Report."
4. Show before/after improvements.
5. Raise pre-seed or seed from AI infra, devtools, and enterprise AI investors.

Possible check size:

- angel/pre-seed: $250k-$1.5M
- seed with pilots: $2M-$6M
- strong seed with revenue and famous design partners: $6M-$10M+

## 30-Day Plan

Week 1:

- define ICP and exact demo story
- build trace import adapter
- create 10 realistic demo traces
- simplify investor-facing wording

Week 2:

- build failure replay
- add before/after comparison
- improve UI around root cause and state gap
- create pitch narrative

Week 3:

- integrate one real agent framework
- onboard first design partner candidate
- run product on real traces
- collect feedback

Week 4:

- publish demo video
- create landing page
- write technical memo
- start 30 customer discovery calls

## 90-Day Plan

Days 1-30:

- demo-grade product
- one framework integration
- first public narrative

Days 31-60:

- 3 design partners
- real traces
- measurable before/after improvement

Days 61-90:

- 1-2 paid pilots
- investor deck
- technical report
- fundraising conversations

## Key Metrics

Track:

- traces ingested
- repeat failed patterns detected
- root-cause accuracy from human review
- policy/memory updates accepted
- recurring failures reduced
- time saved in debugging
- agent success-rate improvement
- weekly active projects

The strongest fundraising metric:

> SuperTuriya reduced repeated agent failures by X% across Y real production traces.

## Naming And Branding

Keep the company name SuperTuriya if it feels meaningful and distinctive.

Investor-facing category:

- Trajectory Intelligence
- Agent Observability and Optimization
- Agent Reliability Platform

Avoid leading with:

- quantum consciousness
- human era transformation
- philosophical framing

Use the deep research as credibility after the buyer understands the practical pain.

## Immediate Next Build

The next engineering milestone should be:

> Import real agent traces and replay failure-to-improvement loops.

Concretely:

- `POST /integrations/langgraph/import`
- `POST /integrations/openai-agents/import`
- replay screen
- before/after score comparison
- accepted policy/memory update queue
- exported PDF/markdown trajectory report

This turns SuperTuriya from impressive POC into a product customers can test on their own runs.

