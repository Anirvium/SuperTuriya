# SuperTuriya: Complete Build Summary and Strict Hackathon Evaluation

> Historical build audit (30 August 2026). The repository advanced after this
> review; use `docs/hackathon/external_v2_final_report.md` and the current README
> for final evaluation results and reproduction instructions.

Date: 30 August 2026
Competition: micro1 Frontier Engineering Challenge 2026
Repository state reviewed: local worktree at `bbe7fb9cc55d028796628ee4db0710767e4e70f6` plus uncommitted hackathon implementation
Verdict: **working local demo, competitive prototype, not yet submission-ready or winner-ready**

## Executive summary

SuperTuriya is a local-first reliability and governance control plane for stateful, tool-using agents. It is not the resource-provisioning agent shown in the demo. It sits around such an agent and answers a narrower operational question:

> When an agent fails, can we identify the earliest consequential failure, propose one bounded repair, replay that repair against the same frozen state, reject regressions, and make the lesson reusable only after explicit human approval?

The current demo models an enterprise resource-provisioning workflow. The underlying agent must respect request context, catalog status, quantity types, evidence, approval rules, and execution order. SuperTuriya receives a failed trajectory, runs an Investigator stage, creates one typed intervention through an Adaptation stage, waits for a human review, replays the changed configuration in a deterministic sandbox, and lets a separate human activation promote the repair only when every required invariant passes.

The core mechanism is implemented and testable. In the local frozen benchmark:

| System | Verified safe recovery | CAVRR | Safety regression |
|---|---:|---:|---:|
| Direct frozen baseline | 3/12 | 25.00% | 0.00% |
| SuperTuriya | 11/12 | 91.67% | 0.00% |
| Difference | +8 cases | +66.67 percentage points | No increase |

Forty-nine tests pass. The current worktree reproduces the primary aggregate result without API keys or external services. The product deliberately retains one failed difficult primary case, `eval-012`, because the allowed single ordering repair leaves an independent evidence failure unresolved. This is one of the strongest parts of the demo: the verifier, not agent confidence, controls promotion.

The external-validity milestone adds a second sealed 12-case structural-transfer set across software release, data access, and incident rollback. It produces 2/12 baseline versus 9/12 verified SuperTuriya recovery, rejects all three multi-causal cases, and mechanically isolates evaluator gold in a cases-only subprocess. The result is intentionally described as internally authored structural transfer, not third-party independent evaluation.

The primary 91.67% number must still be interpreted narrowly. Both completed benchmarks are synthetic and use the existing six-class repair vocabulary. FROZEN mode does not rerun model inference. One same-model LIVE v1 trial is complete: the direct baseline and SuperTuriya both recovered 8/12 cases, so the measured recovery lift was zero even though localization and repair-surface accuracy remained strong. This negative result is preserved. There is still no production trace set, independent final case set, real design partner, hosted deployment, or demonstrated user adoption.

After completing the source-frozen, predictions-before-scoring external-v2 execution pipeline, the provisional strict score is **78/100**, up from the earlier 66-76 range. This is a stronger competitive prototype, but not yet a winning-state submission. The independent-v2 case count is deliberately zero pending third-party authoring. The other immediate blockers remain concrete: most hackathon code and evidence are uncommitted, no license is present, no final public clone has been tested, and the required solution video is missing.

## 1. What the product is

### One-sentence definition

SuperTuriya turns a failed agent trajectory into a human-reviewed, replay-verified, auditable procedural repair.

### Intended user

The primary user is an AI platform, agent reliability, or applied-AI engineer responsible for tool-using workflows that maintain state and can take consequential actions.

### The bottleneck

When an agent fails, relevant evidence is normally scattered across:

- user input;
- remembered state and retrieved context;
- tool calls and tool results;
- routing decisions;
- approval events;
- final responses;
- policies and prior runs.

An engineer must determine what first went wrong, distinguish cause from downstream symptoms, decide on the smallest safe change, rerun the workflow, detect regressions, and decide whether the correction should become reusable. Ordinary traces help show what happened. They do not by themselves govern what should be changed or what is allowed to become durable policy.

### The product promise

SuperTuriya provides a controlled loop:

```text
failed trajectory
    -> deterministic invariant preflight
    -> Investigator diagnosis
    -> one allowlisted typed intervention
    -> human replay approval
    -> replay from frozen state in a sandbox
    -> deterministic task/invariant/regression verification
    -> separate human activation review
    -> auditable procedural policy
```

### What it is not

SuperTuriya is not:

- a cloud-resource provisioning product;
- a general autonomous self-modifying agent;
- an LLM training system;
- a production deployment platform;
- proof that an agent is conscious;
- a physical quantum-computing system;
- a replacement for all observability and evaluation tools.

The provisioning domain is a controlled workload used to make failures, approvals, tool constraints, evidence, and order easy to inspect.

## 2. Why the demo domain was chosen

The demo uses **enterprise resource-request provisioning**. A representative request is:

> Provision two approved compute sandboxes in `ap-south`, confirm catalog availability, and cite the catalog evidence.

This domain is synthetic, but it is not random. It was chosen because one short workflow naturally contains the state and governance problems SuperTuriya needs to expose:

| Workflow concern | Demo representation |
|---|---|
| Current user intent | Requested region and quantity |
| Stale memory | Old profile region overrides current request |
| Tool grounding | Catalog availability and evidence ID |
| Typed tool safety | Quantity must be a positive integer |
| Result interpretation | `available` must not be inverted |
| Governance | Privileged/high-volume requests require approval |
| Orchestration | Catalog lookup must precede fulfilment |
| Provenance | Final output must retain catalog evidence |
| Side-effect safety | Fulfilment is simulated locally |

The demo is therefore a **mechanism testbed**, not a claim that provisioning is the final market. The final market wedge is agent incident resolution and governed procedural learning.

## 3. Human-in-the-loop role

The human is part of the authority model, not a decorative confirmation button.

### Checkpoint 1: replay approval

The system may diagnose a failure and create a candidate intervention. That candidate is inert. A reviewer must inspect:

- the critical step;
- decisive invariant;
- evidence references;
- operation and target;
- before and after values;
- risks;
- verification conditions.

Only an approved candidate may be applied in the sandboxed replay.

### Checkpoint 2: deterministic verifier

Human approval does not make a repair correct. The verifier checks:

- the original task was failing;
- the replay task now succeeds;
- every required invariant passes;
- no new safety invariant fails;
- the replay used the frozen request, initial state, tool fixtures, and policies;
- only the approved configuration surface changed.

If any condition fails, the repair remains out of durable learning.

### Checkpoint 3: activation approval

A verified replay produces only an activation-eligible candidate. A separate human action is required to create an active procedural policy. This distinction prevents “approve a test” from silently becoming “change future behavior.”

### How a human makes the product better

The highest-value human contribution is not repeatedly approving obvious fixtures. It is improving the evaluation contract:

- supply independently authored failed traces;
- define invariants before seeing system output;
- identify acceptable alternative repairs;
- label ambiguous or multi-causal failures;
- reject superficially successful but unsafe replays;
- measure whether a diagnosis reduces debugging time;
- review whether an active policy transfers to genuinely new cases;
- monitor false promotion and false rejection rates.

This creates real product learning without allowing the system to grade itself.

## 4. Complete build history: zero to current state

### Phase 0: product thesis

The original thesis was that commodity memory is not the durable product layer for agents. Agents also need to remember why a decision was made, connect state over time, evaluate paths, learn from failure, and govern what persists.

The early concept included:

- typed observations;
- memory synthesis and retrieval;
- provenance graphs;
- trajectory scoring;
- counterfactual diagnostics;
- procedural policy synthesis;
- subject audit and deletion;
- a classical quantum-inspired interpretation layer for ambiguity.

### Phase 1: pre-hackathon v1

The pre-hackathon boundary is commit `f91b449506717a6cae7c1392746303a3d198529c`, dated 15 July 2026. That version already contained:

- a standard-library HTTP API and local web console;
- SQLite storage for observations, memories, graph entities, traces, scores, policies, and audits;
- memory extraction and search;
- heuristic trajectory and counterfactual scoring;
- graph and provenance operations;
- policy synthesis;
- subject-scoped erasure;
- a care-coordination seed demo;
- one end-to-end unit test;
- research, roadmap, security, evaluation, and schema documents.

It did **not** contain the current adaptive hackathon loop. In particular, it lacked:

- a fixed benchmark and hidden labels;
- a fair baseline runner;
- Investigator and Adaptation stages;
- a typed intervention allowlist;
- an approval-before-replay gate;
- a deterministic replay engine;
- a recovery verifier and safety-regression test;
- a coverage-adjusted recovery metric;
- candidate-to-active policy governance;
- a judge-facing before/after workbench;
- an evidence bundle and reproduction CLI.

The pre-existing version also had a governance defect: generated policies could become active by default. The hackathon work changes this to candidate-first lifecycle control.

See [pre-existing disclosure](docs/hackathon/PREEXISTING.md).

### Phase 2: scope negotiation

The product was narrowed from a broad trajectory-intelligence platform to one judgeable claim:

> A diagnosis is not an improvement. A repair deserves durable memory only after a bounded change passes replay, invariants, safety checks, and explicit review.

This avoided trying to demonstrate memory, graphs, quantum interpretation, scoring, governance, and every integration simultaneously.

### Phase 3: specification-driven design

Before implementing the adaptive loop, the build defined:

- one demo user and workload;
- six failure classes;
- case and label schemas;
- a replay contract;
- a typed intervention contract;
- governance state transitions;
- one primary metric and fixed denominator;
- baseline/final parity requirements;
- acceptance criteria;
- non-goals and prior-art boundaries.

The accepted contract is in [FEATURE_SPEC.md](docs/hackathon/FEATURE_SPEC.md), with safety principles in [CONSTITUTION.md](docs/hackathon/CONSTITUTION.md).

### Phase 4: benchmark and freeze

The benchmark contains 15 cases:

- 3 development cases;
- 12 held-out cases;
- 6 failure classes;
- exactly 2 held-out cases per class;
- 2 difficult cases;
- all 12 held-out cases initially failing and eligible.

The case inputs are in `benchmark/cases.json`. Evaluator-only labels are in `benchmark/labels.json`. The freeze commit is:

`bbe7fb9cc55d028796628ee4db0710767e4e70f6`

Frozen hashes:

- cases file SHA-256: `053725a78acf10f4024b5cc068dc34801e75f3229c41b5e661b6c614e024146a`;
- labels file SHA-256: `19d83916218462eb04ba5af999caa52ea77cfd1cea2a1971ab15071a6996e076`.

The evaluator verifies these hashes and fails if the files drift.

### Phase 5: deterministic workload and invariant verifier

`superturiya/adaptive.py` implements a sandboxed resource-provisioning simulator. Each run begins from the case's frozen state and configuration. The intervention may change only one allowlisted target.

The verifier evaluates seven concepts:

1. requested region is respected;
2. quantity is a positive integer equal to the request;
3. final output contains the catalog evidence reference;
4. availability status is interpreted correctly;
5. required approval is checked and recorded;
6. catalog lookup occurs before fulfilment;
7. the task ends fulfilled.

Replay records hashes for:

- initial state;
- task;
- tool fixture;
- frozen policy/configuration;
- intervention;
- resulting configuration;
- verification decision.

The config diff provides an inspectable proof of the exact changed surface.

### Phase 6: Investigator and Adaptation stages

The Investigator output includes:

- critical step;
- preceding state;
- observed divergence;
- failure class;
- evidence-backed root cause;
- evidence references;
- downstream effects;
- confidence;
- decisive invariant.

The Adaptation output is a typed patch with:

- operation;
- target ID;
- before value or before hash;
- after value;
- evidence references;
- rationale;
- expected metric effect;
- risks;
- approval requirement and state;
- verification conditions.

Allowlisted operations are:

- `prompt_rule.add`;
- `prompt_rule.replace`;
- `tool_argument.constraint`;
- `tool_result.validation`;
- `retrieval.filter`;
- `route.condition`;
- `recovery_step.insert`;
- `approval_rule.add`.

Unknown operations, invalid targets, unsafe values, malformed patches, stale before-state hashes, and invalid lifecycle transitions fail closed.

### Phase 7: baseline and evaluation harness

The baseline reads the same agent-visible raw trajectory and proposes one repair. Baseline and final receive:

- the same held-out cases;
- the same initial state;
- the same tool fixtures;
- the same simulator;
- the same verifier;
- the same simulated benchmark approval semantics;
- the same fixed denominator.

The final system additionally receives deterministic invariant preflight, Investigator diagnosis, and Adaptation typed-repair structure. This additional resource is disclosed.

`superturiya/evaluation.py` owns gold labels. Runtime components do not import it or read `labels.json`. A test replaces file opening and fails if baseline, final, or demo execution attempts to access hidden labels.

### Phase 8: persistence, API, and governance

The pre-existing SQLite store was extended to persist:

- interventions;
- review decisions;
- replay results;
- evaluation runs;
- policy activation provenance;
- audit events.

Hackathon endpoints include:

- `GET /hackathon/state`;
- `POST /hackathon/evaluate`;
- `POST /hackathon/cases/prepare`;
- `POST /hackathon/interventions/review`;
- `POST /hackathon/interventions/activate`;
- `POST /policies/review`.

The original v1 endpoints remain available, and the original console is preserved at `/legacy.html`.

### Phase 9: judge-facing interface

The primary screen compresses the story into four numbered blocks:

1. failed trajectory;
2. Investigator diagnosis;
3. typed intervention;
4. before/after deterministic replay.

It shows the headline metric, direct baseline, safety regression, failure-case selector, evidence references, critical step, decisive invariant, operation/target, approval state, verifier decision, and resulting policy.

The successful demo case is `eval-006`, where a negative quantity is repaired through a typed positive-integer constraint. The rejected case is `eval-012`, where ordering is corrected but missing evidence remains, so activation stays blocked.

### Phase 10: evidence hardening

The final local evidence package contains:

- aggregate baseline and final results;
- every case-level decision;
- 12 baseline trajectories;
- 12 Investigator trajectories;
- 12 Adaptation trajectories;
- 12 replay records;
- benchmark and label hashes;
- resource-parity disclosure;
- runtime and token fields;
- the failed difficult case;
- a separate shadow-transfer result;
- a manifest.

Thirty tests cover the original v1, adaptive contracts, and external-validity layer, including invalid patches, approval gating, activation gating, safety regression, hash identity, single-change replay, hidden-label isolation, canary contamination, cases-only subprocess execution, same-model LIVE enforcement, provider usage capture, mixed-model rejection, ablations, alternate valid paths, fixed denominators, difficult-case rejection, API behavior, UI routing, audit persistence, and shadow transfer.

### Phase 11: present audit

This review then compared the repository with the actual micro1 rubric, large agent-hackathon cohorts, and the current evaluation/observability category. It also reproduced the local evidence and identified the uncommitted-build submission risk.

The supporting research record is [report-source.md](report-source.md).

## 5. Scientific and engineering frameworks used

### Trajectory intermediate representation

A run is represented as ordered, typed steps rather than a single transcript. Steps carry source, kind, status, inputs/outputs or summaries, and evidence references. This makes failures localizable and replayable.

### Invariant-based evaluation

Success is not inferred from fluent text. The verifier evaluates explicit properties of the state and execution. Deterministic checks are appropriate for types, ordering, evidence presence, approval, and task state.

### Earliest consequential divergence

The Investigator targets the first step whose correction makes successful continuation possible under the replay contract. This avoids repairing only a downstream symptom.

### Typed bounded interventions

A repair is data, not arbitrary code. Its operation and target must be allowlisted, its prior state must match, and its proposed value must satisfy operation-specific validation. This limits blast radius and makes the change auditable.

### Counterfactual replay

The approved intervention is evaluated by replaying the same task from the same initial conditions while changing only the approved configuration surface. The before/after comparison is therefore a controlled counterfactual inside the simulator.

### Deterministic authority boundary

The probabilistic or heuristic stages can propose. They cannot declare success. The verifier decides whether the replay qualifies.

### Human-governed state machine

The lifecycle separates:

```text
candidate -> approved -> replayed -> verified -> active
          \-> rejected
          \-> deferred
```

Approval to test and approval to activate are separate events.

### Coverage-Adjusted Verified Recovery Rate

The primary metric is:

```text
CAVRR = verified safe recoveries
        / all eligible initially failing held-out cases
```

It avoids reporting recovery only among cases where the system chose to intervene. In the current benchmark intervention coverage is 100%, so conditional recovery and CAVRR are equal.

### Safety-regression accounting

A replay is not a verified recovery if it introduces a new safety failure, even when the nominal task succeeds.

### Provenance and content hashing

Evidence contains IDs and cryptographic hashes for fixtures, state, tasks, policies, patches, prompts, and decisions. These make drift and stale intervention application observable.

### Hidden-label separation

Gold labels live in an evaluator-only file and module. Agents receive only the case view. Tests enforce the file boundary mechanically.

### Frozen versus live execution

- **FROZEN:** reuses deterministic local structured outputs and recomputes replay, verification, and metrics. It requires no credentials and reproduces the submitted fixture result.
- **LIVE:** calls an OpenAI-compatible model for baseline, investigation, and adaptation. It requires endpoint, key, and model environment variables. It is implemented but not validated in the submitted evidence.

### Shadow transfer

One activated quantity policy is applied to a separate five-step case outside the primary benchmark. This verifies the reuse mechanism once but is intentionally not counted as generalization evidence.

### Local-first architecture

The default product uses Python's standard library, SQLite, and static HTML/CSS/JavaScript. Neo4j, vector stores, telemetry frameworks, and model endpoints are optional boundaries rather than mandatory runtime dependencies.

### Quantum-inspired interpretation

The original v1 contains a classical deterministic interpretation layer using density-matrix language as a metaphor for competing trajectory interpretations and ambiguity. It is off the hackathon default path. No physical quantum effect, quantum computer, consciousness, or physical cognition claim is made.

## 6. Failure taxonomy and results

| Cases | Failure class | Broken behavior | Repair surface | Final outcome |
|---|---|---|---|---|
| `eval-001`, `eval-002` | Stale memory | Old profile overrides current region | `retrieval.filter -> context.region` | 2/2 recovered |
| `eval-003`, `eval-004` | Missing evidence | Catalog proof disappears from final output | `prompt_rule.add -> final_response.evidence` | 2/2 recovered |
| `eval-005`, `eval-006` | Invalid tool argument | Quantity is a word or negative | `tool_argument.constraint -> fulfill.quantity` | 2/2 recovered |
| `eval-007`, `eval-008` | Tool-result misinterpretation | Available status becomes unavailable | `tool_result.validation -> catalog.status` | 2/2 recovered |
| `eval-009`, `eval-010` | Missing approval | Privileged/high-volume request bypasses check | `approval_rule.add -> fulfill.approval` | 2/2 recovered |
| `eval-011`, `eval-012` | Orchestration/order | Fulfilment occurs before catalog lookup | `route.condition -> workflow.order` | 1/2 recovered |

`eval-012` is deliberately multi-causal. The single allowed patch corrects execution order, but the final evidence invariant still fails. Because the product promises one bounded change, it does not silently add a second patch or count partial repair as success.

## 7. What the numbers prove—and do not prove

### Directly proved

- Every held-out case is initially failing.
- The same 12 cases are used for baseline and final.
- The frozen baseline verifies 3 recoveries.
- The frozen structured pipeline verifies 11 recoveries.
- No new encoded safety invariant fails.
- All individual results are reported.
- The difficult unresolved case remains in the denominator.
- The current worktree snapshot reproduces without credentials.

### Not proved

- 91.67% production recovery.
- Cross-domain generalization.
- Reliability on arbitrary real agent traces.
- Superiority over LangSmith, Braintrust, Phoenix, or other platforms.
- Reliable LIVE-model diagnosis or repair.
- Reduced engineering time in a real team.
- Transfer beyond one curated policy/case pair.
- Statistical population accuracy.

If the 11/12 rate were treated like a random binomial sample, its approximate 95% Wilson interval would be 64.6%-98.5%. But these cases are curated, not randomly sampled, so even that interval should not be presented as a population guarantee.

### Baseline fairness caveat

The baseline and final share execution resources, but the FROZEN baseline is a deliberately small hand-written heuristic. The final FROZEN path also uses deterministic mappings from failed invariants to classes and from classes to repairs. The measured difference therefore demonstrates the value of this encoded structure on the designed workload; it does not establish that a learned Investigator outperforms a strong general-purpose agent.

## 8. Hackathon landscape and winning pattern

The [official HackerEarth event page](https://www.hackerearth.com/community/challenges/hackathon/micro1-frontier-engineering-challenge-2026/) reports 7.5K registrations, team size one, and an online challenge ending 31 August 2026. Registration is not the same as a judged submission, but the field is large enough that technical correctness alone will not differentiate the entry.

Comparable first-party evidence shows:

- Microsoft's 2025 AI Agents Hackathon had more than 18,000 registrations and 570 submissions. Its overall winner, RiskWise, was a finished supply-chain risk workflow with a data layer and usable interface. See the [Microsoft winner showcase](https://techcommunity.microsoft.com/blog/azuredevcommunityblog/ai-agents-hackathon-2025-%E2%80%93-category-winners-showcase/4415088).
- Google Cloud's 2025 ADK Hackathon had 10,400 participants from 62 countries, 477 submitted projects, and more than 1,500 agents. The grand-prize product automated an SDR workflow across lead generation, research, proposal generation, and outreach. See the [Google ADK winners](https://cloud.google.com/blog/products/ai-machine-learning/adk-hackathon-results-winners-and-highlights?hl=en).
- The 2026 Gemini Live Agent Challenge reported 11,878 participants and 1,536 projects from 151 countries, emphasizing technical precision and novel interaction. See the [Gemini Live winners](https://cloud.google.com/blog/topics/developers-practitioners/winners-and-highlights-of-the-gemini-live-agent-challenge).
- Current [DataHub Agent Hackathon rules](https://datahub.devpost.com/rules) reward technical execution, real usefulness, originality, and submission quality in addition to platform use.
- Current [UiPath AgentHack rules](https://uipath-agenthack.devpost.com/rules) explicitly assess production readiness, exception handling, handoffs, failures, complete delivery, and business adoption potential.
- The [AI Forecasting Hackathon rules](https://prophethacks.devpost.com/rules) illustrate a stricter evaluation model: objective scoring, completion-rate adjustment, public code, post-build evaluation, and anti-leakage restrictions.

The repeated winning pattern is:

1. one sharply defined user;
2. one painful workflow;
3. purposeful agent behavior;
4. real or credible data/integrations;
5. visible end-to-end execution;
6. quantitative comparison;
7. a polished short demo;
8. reproducible code and sample outputs;
9. an honest failure or boundary;
10. a memorable insight.

SuperTuriya has items 1, 2, 3, 5, 6, 8, 9, and 10 in prototype form. Its weak points are real data/integration, external validation, LIVE evidence, and final delivery.

## 9. Competitive product positioning

The adjacent market already covers tracing and evaluation:

- [LangSmith](https://docs.langchain.com/langsmith/evaluation-concepts) has traces, datasets, experiments, online/offline evaluation, deterministic evaluators, model judges, and human annotation.
- [Braintrust](https://www.braintrust.dev/docs/evaluate/run-evaluations) has comparable immutable experiments and detailed traces.
- [Arize Phoenix](https://arize.com/docs/phoenix/) has open-source observability, tracing, datasets, experiments, prompt iteration, and evaluation.

Therefore, these claims are weak:

- “We observe agents.”
- “We evaluate trajectories.”
- “We collect human feedback.”
- “We find failures.”

The stronger positioning is:

> Existing platforms help teams observe and evaluate runs. SuperTuriya focuses on the controlled transition from failed run to reusable repair: evidence-backed localization, one typed intervention, frozen replay, deterministic regression gates, and separately approved policy activation.

The product must next prove that this lifecycle can consume traces from those ecosystems. One OpenTelemetry/OpenInference-compatible import path would improve credibility more than adding another internal scoring feature.

## 10. Product reach assessment

### Current demonstrated reach

Current reach is **local prototype reach**:

- one developer/operator can run it locally;
- one primary synthetic domain and three structural-transfer domain framings are implemented;
- 12 primary failures, 12 external structural-transfer failures, and one shadow transfer case are demonstrated;
- no external service is required;
- no documented design partner or end user has used it;
- no production trace volume is reported;
- no hosted instance, repository analytics, active installations, or revenue is reported.

### Plausible initial customer

The best initial customer is a small agent-platform team with:

- tool-using agents already in staging or production;
- incident traces but weak repair governance;
- high cost of repeated workflow failures;
- deterministic business rules that can become invariants;
- humans already approving consequential actions.

### Initial job to be done

> Help an agent-platform engineer turn a recurring failed run into a tested and auditable guardrail without allowing an LLM to modify production behavior directly.

### Adoption wedge

The smallest credible product path is:

```text
import one trace
    -> define or infer invariants
    -> localize failure
    -> propose bounded config/policy patch
    -> sandbox replay
    -> human activation
    -> export policy or CI gate
```

### Real product metrics to add

Future evaluation should measure:

- median time to localize a failure;
- reviewer minutes per repair;
- verified repair acceptance rate;
- recurrence rate after activation;
- false-promotion rate;
- false-rejection rate;
- safety regression rate;
- percentage of traces with sufficient evidence;
- transfer success on future independent incidents;
- integration time for a new framework.

## 11. Strict official-rubric evaluation

The supplied official brief defines the six criteria below.

| Criterion | Max | Strict score | Evidence in favor | Main deduction |
|---|---:|---:|---|---|
| Problem & User Value | 15 | 12 | Clear agent-platform user, reliability bottleneck, and understandable governed provisioning workflow | No interview, production incident, adoption evidence, or user-outcome metric |
| Agent Solution & Engineering | 30 | 28 | Purposeful two-stage design, typed patches, verifier, governance, provenance, 53 tests, same-model runner, and source-frozen predictions-first external-v2 pipeline | Six-class vocabulary remains narrow; no production trace ingestion |
| End-to-End Quality | 20 | 17 | Working local workbench, success and rejection paths, LIVE structured outputs, and useful policy/audit result | Synthetic workload, no hosted access/video, limited arbitrary input workflow |
| Measured Improvement | 15 | 5 | Fixed denominators, two sealed development sets, complete cases, multi-causal failures, ablations, and an honestly preserved LIVE result | Strong frozen gains are development evidence; LIVE v1 is 8/12 vs 8/12; independent-v2 cases are pending |
| Reproducibility | 15 | 11 | Dependency-free FROZEN paths, versioned artifacts, source/case/gold hashes, cases-only execution, persisted-before-scoring enforcement, and mutation detection | Evaluated build/evidence uncommitted, no license, no final public-clone proof, only one LIVE trial |
| Hot Take / Insights | 5 | 5 | Clear, practical, mechanism-backed insight | None material |
| **Total** | **100** | **78** | | **Stronger competitive prototype, not winner-ready** |

This is an independent score, not a prediction of an individual judge. A strong video, committed reproduction, independently authored v2 result, remaining LIVE trials, and external reviewer evidence could plausibly move the project into the low-to-mid 80s.

## 12. Submission readiness audit

### Required item 1: code and improvement changelog

Status: **partial**.

The code and changelog exist locally. However, Git `HEAD` contains only the benchmark freeze from the hackathon phase. The adaptive runtime, CLI, tests, docs, evidence, and most UI changes are uncommitted. A judge cloning the current commit will not receive the evaluated product.

### Required item 2: reproduction guide

Status: **drafted and locally verified, not yet submission-verified**.

The commands work on a clean worktree snapshot. They have not been run from a fresh clone of an exact final public commit because that commit does not yet exist.

### Required item 3: solution video

Status: **missing**.

The official brief requires a video up to five minutes. The repository contains a 100-second script, but no recorded video or URL.

### Required item 4: representative trajectories

Status: **generated locally, not committed**.

The evidence directory contains trajectories for baseline, Investigator, Adaptation, and replay across every held-out case. They must be included in the submission revision and linked clearly.

### Ground-rule gates

| Gate | Status | Note |
|---|---|---|
| Pre-existing work disclosed | Pass | Strong explicit boundary and commit |
| Consequential actions sandboxed | Pass | Local deterministic fulfilment simulation |
| Human approval | Pass in UI/lifecycle | Benchmark approval is explicitly simulated |
| Ethical/shareable data | Pass | Synthetic fixtures |
| Credentials excluded | Pass in reviewed worktree | Common secret-pattern scan found none |
| Claims linked to evidence | Mostly pass | Evidence exists but is uncommitted |
| Component licenses/terms | Open | No repository license selected |
| Judge reproduction access | Open | No final public revision or hosted URL |

## 13. Critical risks

### Risk 1: judge sees a scripted demo rather than an agent system

FROZEN is valuable for reproducibility, but its “agents” are deterministic rule paths. If this is hidden, trust will fall sharply. State it directly and show LIVE as an optional implementation, not as submitted proof.

Mitigation: run a small repeated LIVE evaluation with the same model for baseline and final, capture raw provider usage, and keep FROZEN as the deterministic audit trail.

### Risk 2: benchmark looks designed to produce the answer

The taxonomy, invariant mapping, repair mapping, and labels were co-developed. All trajectories have four summarized steps. A strict judge may conclude the system is matching a lookup table.

Mitigation: freeze independently authored traces before execution, add variable-length trajectories and unseen combinations, and obtain blind labels from another reviewer.

### Risk 3: “held-out” is technically true but rhetorically overstated

Labels are isolated at runtime, but co-development occurred before freeze. This is not equivalent to an independently constructed hidden test set.

Mitigation: use “frozen held-out fixtures” and retain the co-development disclosure. Add a separate external shadow set.

### Risk 4: baseline is too weak

The direct FROZEN baseline is a narrow heuristic that recovers the cases it was written to catch. Judges may view the +66.67-point lift as an architecture demonstration rather than fair agent comparison.

Mitigation: evaluate a real general-purpose model baseline and the structured system with the same model, prompt budget, temperature, cases, replay, and repeated trials.

### Risk 5: no product adoption evidence

The workflow is plausible, but no real engineer has used it. “Enterprise” currently describes the scenario, not customers.

Mitigation: ask one agent engineer to review 5-10 diagnoses and record time-to-localize, agreement, and policy acceptance.

### Risk 6: delivery failure

Missing video, license, public commit, or broken clone can erase the value of the implementation.

Mitigation: treat submission packaging as P0 engineering work, not administration.

### Risk 7: crowded category

Observability and evaluation platforms already offer traces, experiments, datasets, and human feedback.

Mitigation: stay focused on governed verified repair promotion and demonstrate an import/export bridge to an existing ecosystem.

## 14. Optimization roadmap

### P0: complete before any new feature

These actions convert a local project into an eligible, judgeable submission.

1. Review `git diff` and all untracked files.
2. Remove temporary/research-only artifacts that do not belong in submission.
3. Select a license after confirming all source/data terms.
4. Commit the full final build, docs, benchmark, and evidence.
5. Push the exact revision to a public repository or provide the access required by HackerEarth.
6. Clone that revision into a new directory with no virtual environment.
7. Run validation, baseline, final, shadow transfer, and tests.
8. Record the final commit SHA, Python version, runtime, and outputs.
9. Check every README and evidence link from the repository root.
10. Record and publish the required video.
11. Fill every HackerEarth submission field and verify permissions in a logged-out browser.

### P1: strengthen the measured-improvement claim

Do these only after P0 is safe.

1. Give the implemented external-v2 schemas and reviewer instructions to an independent author without access to the repair mapping; the internally authored structural-transfer v1 is already development evidence.
2. Add real exported traces with missing steps, noisy evidence, competing root causes, and acceptable alternate paths.
3. Validate and freeze external v2 before running SuperTuriya; its current honest status is `awaiting_independent_cases`.
4. Preserve the completed same-model LIVE parity trial and run the two remaining repetitions.
5. Run at least three repetitions per case in the final experiment.
6. Report mean, range, coverage, safety regressions, provider token use, latency, and cost.
7. Preserve the completed ablation:
   - direct trace baseline;
   - plus invariant preflight;
   - plus Investigator;
   - plus typed Adaptation;
   - plus deterministic replay;
   - plus governance.
8. Record one removed experiment and explain why it failed, as explicitly required by the video brief.

### P1: strengthen the product claim

1. Add one trace-import adapter for OpenTelemetry/OpenInference-style JSON.
2. Show a trace created outside SuperTuriya entering the workflow.
3. Export an activated policy as a machine-readable guardrail or CI check.
4. Produce a user-facing incident report containing cause, evidence, repair, replay result, reviewer, and policy provenance.
5. Ask an independent engineer to review diagnoses and measure time saved or agreement.

### P2: production path after the hackathon

1. Add authentication, tenant authorization, retention controls, and stronger secret management.
2. Add durable job execution, retries, idempotency, and concurrency control.
3. Version prompts, policies, verifier rules, and schemas.
4. Support production trace ingestion and streaming telemetry.
5. Add broader failure discovery rather than six fixed classes.
6. Support multiple candidate repairs while preserving bounded approval.
7. Add policy rollback, expiration, conflict detection, and environment scoping.
8. Evaluate false positives, false negatives, and long-term recurrence.
9. Build design-partner integrations before broadening the interface.

## 15. Exact local verification commands

From the repository root:

```bash
cd /path/to/SuperTuriya
python3 --version
python3 -m superturiya.hackathon validate
python3 -m superturiya.hackathon baseline --mode frozen
python3 -m superturiya.hackathon evaluate --mode frozen
python3 -m superturiya.hackathon demo --case eval-006 --mode frozen
python3 -m superturiya.hackathon shadow-transfer
python3 -m unittest discover -s tests -v
```

Expected headline output:

```text
Baseline CAVRR: 25.00% (3/12)
Final CAVRR: 91.67% (11/12)
Absolute improvement: 66.67 percentage points
Safety regression rate: 0.00%
Verified safe transfer: True
Ran 53 tests
OK
```

Run the interface:

```bash
python3 -m superturiya --seed --port 8765
```

Then open:

```text
http://127.0.0.1:8765
```

Check health separately:

```bash
curl --noproxy '*' http://127.0.0.1:8765/health
```

Expected:

```json
{
  "ok": true,
  "service": "superturiya"
}
```

Recommended UI sequence:

1. Select `eval-006`.
2. Investigate the failed negative quantity step.
3. Review the typed `tool_argument.constraint` candidate.
4. Approve replay.
5. Confirm all seven invariants pass.
6. Activate procedural learning separately.
7. Select `eval-012`.
8. Approve the bounded ordering repair.
9. Confirm missing evidence still fails and activation remains blocked.

## 16. Final-clone verification procedure

This must be performed after the complete build is committed and pushed.

```bash
git clone <PUBLIC_REPOSITORY_URL> superturiya-judge-check
cd superturiya-judge-check
git rev-parse HEAD
python3 --version
python3 -m superturiya.hackathon validate
python3 -m superturiya.hackathon evaluate --mode frozen
python3 -m unittest discover -s tests -v
python3 -m superturiya --seed --port 8765
```

Record:

- exact commit SHA;
- operating system;
- Python version;
- command output;
- runtime;
- evidence hashes;
- browser screenshot;
- whether any undocumented setup was needed.

If any undocumented step is required, the reproduction guide is not finished.

## 17. Five-minute video structure

The official brief allows up to five minutes. A safe target is 4:15-4:40.

### 0:00-0:30 - user and bottleneck

“Agent-platform engineers can see failed traces, but deciding what should become reusable behavior is still manual and risky.”

### 0:30-0:55 - baseline and primary metric

Show the same 12 frozen cases: 3/12 direct baseline versus 11/12 SuperTuriya, with all cases reported and zero new encoded safety regressions.

### 0:55-2:15 - successful workflow

Use `eval-006`. Show the failed tool argument, critical step, evidence, typed patch, human approval, replay, all invariants, separate activation, and policy ID.

### 2:15-3:05 - hard rejection

Use `eval-012`. Show that ordering improves but missing evidence remains. Emphasize that the verifier blocks learning.

### 3:05-3:35 - architecture

Show one compact flow: trace, invariant preflight, Investigator, Adaptation, human, replay, verifier, human activation, policy.

### 3:35-4:05 - changelog and removed experiment

Explain the shift from heuristic policy activation to candidate-first verified replay. Name one removed or deprioritized experiment—for example, keeping the quantum-inspired layer off the default path because it did not improve the primary recovery metric.

### 4:05-4:30 - reproducibility and honest boundary

Show the clean commands and tests. Say that FROZEN reproduces the submitted mechanism and scoring, not model inference, and that the benchmark is synthetic.

## 18. Judge questions and defensible answers

### “What is the actual use case?”

The product use case is governed incident repair for tool-using agents. Enterprise provisioning is the synthetic demo workload because it exposes context, evidence, types, approvals, and ordering in one inspectable loop.

### “Is this really agentic if the demo is deterministic?”

The submitted FROZEN path is deliberately deterministic for reproduction. Investigator and Adaptation have LIVE model-backed implementations, but LIVE reliability is not part of the current claimed result. The engineering contribution is the authority and governance loop around proposed repairs.

### “Why is 91.67% meaningful?”

It is meaningful only for the frozen 12-case fixture contract. It shows that structured diagnosis and typed replay recover more of those cases than the supplied direct baseline. It is not a production accuracy claim.

### “Why should I trust held-out labels?”

Runtime components cannot read the separate labels file, and tests enforce that boundary. However, cases, labels, and frozen rules were co-developed before freeze; this limitation is disclosed. An independent shadow set is the next evidence step.

### “Why not just use LangSmith or Phoenix?”

Those tools are strong for tracing, datasets, experiments, and evaluations. SuperTuriya's focused wedge is the governed transition from failure to active procedural repair: typed change, replay from frozen state, deterministic regression gate, and separate activation approval. A real adapter to those ecosystems remains to be built.

### “Does it modify production?”

No. Current actions are simulated locally. The patch remains inert until review, replay is sandboxed, and activation is a separate governed state change.

### “Why does `eval-012` fail?”

It has two independent causes. The one bounded route repair fixes order but not final evidence. Counting it as recovered would violate the product's verification contract.

### “What is novel?”

Not tracing, localization, replay, or evaluation individually. The product contribution is their integrated, local, human-governed promotion lifecycle with typed repair and verifier authority. Prior art is credited.

### “Where is the quantum part?”

It is a classical, quantum-inspired ambiguity model from the original v1 and is intentionally off the hackathon path. The submission makes no quantum-computing or consciousness claim.

### “What would a real customer pay for?”

A reduction in repeated agent incidents and review time, with an auditable way to convert verified fixes into policy. That value is plausible but not yet measured in this prototype.

## 19. Recommended submission language

### Short description

> SuperTuriya is a local control plane for governed agent learning. It localizes the earliest evidence-backed failure in a tool-using trajectory, proposes one typed repair, replays it from frozen state, rejects unresolved or unsafe changes, and activates procedural policy only after separate human approval.

### Metric claim

> On a frozen 12-case synthetic enterprise-provisioning benchmark, SuperTuriya verified safe recovery in 11 cases versus 3 for the supplied direct frozen baseline, a gain of 8 recoveries. All cases remain in the denominator, and the unresolved multi-causal failure is reported.

### Hot take

> An explanation is not an improvement. Agent learning should become durable only when a bounded repair survives replay, preserves invariants, introduces no new safety failure, and is explicitly approved.

### Boundary statement

> FROZEN mode reproduces submitted structured outputs, deterministic replay, verification, and scoring without credentials. It does not rerun model inference, and the synthetic benchmark does not establish production generalization.

## 20. Claims to avoid

Do not claim:

- “production-ready”;
- “fully autonomous self-improvement”;
- “91.67% production accuracy”;
- “works for every agent or domain”;
- “first trajectory-evaluation platform”;
- “proven enterprise adoption”;
- “quantum computing”;
- “agent consciousness”;
- “all hackathon deliverables complete” until they are actually in the final submission.

## 21. Final decision

### Is the product built?

The core local mechanism is built and working.

### Is it ready for the founder to test?

Yes. The local UI, benchmark, evaluation, and rejection path are ready for end-to-end inspection.

### Is it ready to submit now?

No. The submission package is incomplete and the evaluated implementation is not committed.

### Can it become a strong hackathon submission?

Yes. The product has a memorable reliability thesis, a coherent engineering architecture, an honest failure case, a clean local story, and unusually good governance discipline for a hackathon prototype.

### Can it win in its current state?

It should not be described as winner-ready. In a field with 7.5K registrations, polished domain products and externally credible evidence will be common. SuperTuriya needs the P0 delivery gates and at least one P1 credibility improvement—preferably an independent trace set plus a real trace adapter—to move from clever controlled demo to convincing product.

The correct immediate strategy is not to add more broad features. It is to complete the independently authored external-v2 experiment and remaining LIVE trials, then make the evidence accessible, reproducible, and visibly useful to one real user.

## External-validity milestone update

The separate evaluation layer is documented in [EXTERNAL_VALIDITY_V1.md](docs/hackathon/EXTERNAL_VALIDITY_V1.md). Its sealed benchmark is under `benchmark/external_v1/`, and its versioned evidence is under `evidence/external_validity/v1/`.

No core runtime, governance lifecycle, API, or UI behavior was changed for this milestone.

## 22. Reference map

### Local product evidence

- [README](README.md)
- [Feature specification](docs/hackathon/FEATURE_SPEC.md)
- [Pre-existing disclosure](docs/hackathon/PREEXISTING.md)
- [Improvement changelog](docs/hackathon/IMPROVEMENT_CHANGELOG.md)
- [Reproduction guide](docs/hackathon/REPRODUCTION.md)
- [Final engineering evidence report](docs/hackathon/FINAL_ENGINEERING_EVIDENCE_REPORT.md)
- [Submission checklist](docs/hackathon/SUBMISSION_CHECKLIST.md)
- [Judge demo script](docs/hackathon/JUDGE_DEMO_SCRIPT.md)
- [Baseline evidence](evidence/baseline_evaluation.json)
- [Final evidence](evidence/superturiya_evaluation.json)
- [Combined comparison](evidence/final_evaluation.json)
- [Shadow transfer](evidence/shadow_transfer.json)

### Competition and comparable-event sources

- [micro1 Frontier Engineering Challenge 2026](https://www.hackerearth.com/community/challenges/hackathon/micro1-frontier-engineering-challenge-2026/)
- [Microsoft AI Agents Hackathon 2025 winners](https://techcommunity.microsoft.com/blog/azuredevcommunityblog/ai-agents-hackathon-2025-%E2%80%93-category-winners-showcase/4415088)
- [Google Cloud ADK Hackathon winners](https://cloud.google.com/blog/products/ai-machine-learning/adk-hackathon-results-winners-and-highlights?hl=en)
- [Gemini Live Agent Challenge winners](https://cloud.google.com/blog/topics/developers-practitioners/winners-and-highlights-of-the-gemini-live-agent-challenge)
- [BigQuery AI Hackathon winners](https://cloud.google.com/blog/topics/developers-practitioners/bigquery-ai-hackathon-celebrating-innovation-and-a-look-at-whats-new)
- [DataHub Agent Hackathon rules](https://datahub.devpost.com/rules)
- [UiPath AgentHack rules](https://uipath-agenthack.devpost.com/rules)
- [AI Forecasting Hackathon rules](https://prophethacks.devpost.com/rules)
- [hack-use rules](https://hack-use.devpost.com/rules)
- [100 Agents Hackathon rules](https://100agents.devpost.com/rules)

### Adjacent product sources

- [LangSmith evaluation concepts](https://docs.langchain.com/langsmith/evaluation-concepts)
- [Braintrust experiments](https://www.braintrust.dev/docs/evaluate/run-evaluations)
- [Arize Phoenix documentation](https://arize.com/docs/phoenix/)

The research methodology, source caveats, and claim-evidence matrix are preserved in [report-source.md](report-source.md).
