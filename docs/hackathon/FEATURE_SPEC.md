# Feature Spec: Verified Adaptive Improvement

Status: Accepted for implementation on 29 August 2026.

## Product statement

SuperTuriya is a local-first, provenance-aware, human-governed adaptive intelligence control plane. It promotes an intervention into durable procedural intelligence only after evidence-backed diagnosis, a typed bounded repair, replay success, invariant preservation, regression checks, and explicit approval.

## Prior art and differentiation

AgentRx covers trajectory IR, invariant checking, auditable evidence, critical-failure localization, and failure classification. DoVer covers targeted intervention, re-execution, and outcome-oriented recovery measurement. SuperTuriya does not claim those operations individually as novel.

The product contribution is the governed end-to-end control plane: provenance-grounded diagnosis, typed repair, explicit review, deterministic regression-gated replay, and lifecycle-controlled promotion into reusable procedural intelligence in one local workflow.

## User and problem

Primary user: AI and agent-platform engineers operating stateful, tool-using workflows.

Problem: failure evidence is fragmented across state, memory, tools, policy events, and downstream outputs. Engineers need to find the earliest consequential divergence, see supporting evidence, test the smallest bounded change against the same initial state, reject regressions, and preserve only approved lessons.

## Scope

- One deterministic enterprise resource-request provisioning workload. It remains synthetic and domain-neutral at the implementation layer; the demo maps catalog, approval, region, quantity, evidence, and fulfilment operations to internal resource provisioning.
- 3 development cases and 12 held-out evaluation cases.
- Six failure classes: stale/conflicting memory, missing evidence, invalid tool argument, tool-output misinterpretation, missing approval, and orchestration/order failure.
- Investigator Agent and Adaptation Agent.
- One deterministic verifier and one primary judge-facing screen.
- LIVE and FROZEN reasoning modes.

## Non-goals

- Production deployment, automatic code mutation, model training, broad framework integration, enterprise auth, GPU infrastructure, mandatory cloud services, or automatic activation of learning.
- Quantum-inspired interpretation on the default path.
- Any external reference workload as the product ontology or primary benchmark.

## Canonical case and ground-truth contract

Every case includes `case_id`, `split`, `goal`, frozen `initial_state`, deterministic `tool_fixtures`, frozen `workflow_config`, raw `trajectory`, expected final state, required invariants, and eligibility.

Labels are stored separately from agent-visible input and include:

- `gold_critical_steps` (one or more acceptable steps);
- `gold_failure_class`;
- `decisive_invariant`;
- `expected_repair_surface`;
- `acceptable_alternative_repairs`;
- optional `adjudication_notes`.

Critical step: the earliest step whose faithful correction makes successful continuation possible under this replay contract. Genuinely multi-causal cases may specify multiple acceptable steps.

## Replay contract

- Replay starts from the frozen initial case state.
- Task input, tool fixtures, and policies are frozen except for the one approved intervention under test.
- Tools and side effects are deterministic, local, and simulated.
- A different valid path passes when task success and all invariants pass.
- Evidence records mode, provider, model, temperature, prompt/config hashes, intervention hash, tokens, latency, and estimated cost.
- LIVE invokes a configured OpenAI-compatible model endpoint.
- FROZEN reuses committed structured outputs. It reproduces submitted evidence and scoring, not model inference.

## Typed intervention contract

Allowed operations only:

- `prompt_rule.add`
- `prompt_rule.replace`
- `tool_argument.constraint`
- `tool_result.validation`
- `retrieval.filter`
- `route.condition`
- `recovery_step.insert`
- `approval_rule.add`

Required fields: `intervention_id`, `operation`, `target_id`, `before_value` or `before_hash`, `after_value`, `evidence_refs`, `rationale`, `expected_metric_effect`, `risks`, `requires_approval`, `approval_state`, and `verification_conditions`. Unknown operations or invalid lifecycle transitions are rejected.

## Governance contract

Lifecycle: `candidate -> approved -> active`, with `candidate -> rejected` or `candidate -> deferred` alternatives. Review requires `reviewer_id`, timestamp, decision, and note. Approval never implies activation. Replay may test an approved intervention; only a verified safe replay may be activated or promoted into procedural memory.

## Metric contract

Primary:

`Coverage-Adjusted Verified Recovery Rate = verified safe recoveries / all eligible initially failing held-out cases`

Also report intervention coverage, conditional recovery, safety regression rate, task success after replay, critical-step localization accuracy, failure-class accuracy, median runtime, tokens, and estimated cost. Denominators and case-level results are always emitted. This definition is frozen before held-out evaluation.

## Functional requirements

- FR-001: Load and validate 3 development plus 12 held-out cases without exposing labels to agents.
- FR-002: Deterministically evaluate task success and all case invariants.
- FR-003: Run a fair direct-LLM baseline over raw trajectory input and the same replay verifier.
- FR-004: Produce structured Investigator output with critical step, failure class, root cause, evidence references, and confidence.
- FR-005: Produce and validate one typed bounded Adaptation patch.
- FR-006: Persist explicit review decisions and enforce the intervention lifecycle.
- FR-007: Replay only approved interventions from frozen initial state.
- FR-008: Reject safety regressions and promote only verified safe recoveries.
- FR-009: Store per-agent representative trajectories, costs, latency, hashes, and complete case results.
- FR-010: Provide FROZEN reproduction and optional LIVE inference.
- FR-011: Present one before/after judge view with diagnosis, evidence, intervention, approval, replay, metrics, and changelog.

## Acceptance criteria

- AC-001: All 15 cases validate; exactly 3 are development and 12 held-out.
- AC-002: Unknown patch operations and unapproved replay attempts fail closed.
- AC-003: Generated policies/interventions default to candidate and cannot skip lifecycle states.
- AC-004: Baseline and final use identical held-out inputs and the same verifier.
- AC-005: Evaluation emits all case results and every required metric with fixed denominators.
- AC-006: FROZEN evaluation runs without credentials from a clean Python environment.
- AC-007: Tests cover schemas, verifier, baseline, agents, lifecycle, replay, metrics, APIs, and the original v1 flow.
- AC-008: README, changelog, reproduction guide, and UI claims match stored evidence.

## Rubric traceability

- Problem/User Value: user and problem sections; single end-to-end workflow.
- Agent Solution/Engineering: FR-004 through FR-008; purposeful two-agent boundary and deterministic verifier.
- End-to-End Quality: FR-011 and complete approved replay path.
- Measured Improvement: metric contract, FR-003, FR-009.
- Reproducibility: replay contract, FR-010, AC-006.
- Hot Take: a diagnosis is not an improvement; only an approved bounded intervention that survives replay without regression deserves durable memory.

## Revised architecture

`case -> trace IR -> invariant preflight -> Investigator -> typed Adaptation patch -> explicit review -> deterministic replay -> verifier -> comparison -> governed learning candidate`

Existing SQLite, trace, graph, audit, API, and static-app layers remain. Benchmark fixtures and labels are file-backed; interventions, reviews, replay evidence, and evaluation runs are persisted.

## Build-gate resolution

All eight requested amendments are reflected above: credited prior art, revised metric, label contract, replay contract, typed patches, compressed SDD, candidate-first governance, and frozen scope.

Unresolved but bounded assumptions:

- No live model credentials are available in-repository. FROZEN is mandatory; LIVE remains optional.
- No permitted, independently exported workload fixture was supplied, so the optional showcase adapter is excluded.
- Automated tests use an explicit `benchmark-reviewer` event marked simulated; the live UI requires a user click and reviewer name.

First executable milestone: fixed case schema + deterministic verifier + direct baseline. Frontend work follows the full backend loop.
