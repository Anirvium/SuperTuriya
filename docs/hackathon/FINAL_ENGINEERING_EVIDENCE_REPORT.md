# Final Engineering Evidence Report

Status: core evidence-hardening gates passed on 29 August 2026. One shadow-transfer proof is included separately from the primary benchmark.

## Product and demo domain

SuperTuriya turns failed agent trajectories into verified, governed procedural intelligence. The controlled demo models an enterprise resource-provisioning agent that must combine tenant context, regional catalog availability, quantity constraints, approval policy, evidence references, and correct execution order.

The workload is curated and deterministic. It is not production-derived and does not establish production generalization.

## Frozen benchmark

- Freeze commit: `bbe7fb9cc55d028796628ee4db0710767e4e70f6`
- Cases file SHA-256: `053725a78acf10f4024b5cc068dc34801e75f3229c41b5e661b6c614e024146a`
- Labels file SHA-256: `19d83916218462eb04ba5af999caa52ea77cfd1cea2a1971ab15071a6996e076`
- 3 development cases; 12 eligible, initially failing held-out cases.
- Six failure classes, exactly two held-out cases each.
- `eval-012` remains the rejected multi-causal case; no 12/12 tuning was performed.

See `BENCHMARK_FREEZE.md` for the co-development disclosure.

## Gold-label isolation audit

- Runtime cases are loaded by `superturiya.adaptive.load_cases` from `cases.json` only.
- Baseline, Investigator, Adaptation, deterministic workload, and replay live in `superturiya.adaptive` and do not import the evaluator or reference `labels.json`.
- Hidden labels are loaded only by `superturiya.evaluation.EvaluationHarness` after runtime outputs are complete.
- A test replaces `Path.open` with a guard that fails if any runtime baseline/final/demo execution attempts to open `labels.json`.
- Validation records both byte hashes and fails closed on post-freeze file changes.

## Resource and baseline fairness

Both systems use identical held-out case IDs, initial-state hashes, task hashes, deterministic fixtures, frozen policy hashes, replay engine, verifier, and simulated approval semantics. In LIVE mode they resolve the same environment-configured endpoint and model.

The additional resources received by SuperTuriya are disclosed rather than hidden: deterministic invariant preflight, Investigator structured diagnosis, and Adaptation typed repair. The baseline receives the raw agent-visible trajectory and proposes one direct typed repair in one reasoning stage.

## Aggregate evaluation

| Metric | Baseline | SuperTuriya |
|---|---:|---:|
| Eligible initially failing cases | 12 | 12 |
| Interventions attempted | 12 | 12 |
| Intervention coverage | 100.00% | 100.00% |
| Verified safe recoveries | 3 | 11 |
| Coverage-Adjusted Verified Recovery Rate | 25.00% | 91.67% |
| Conditional recovery rate | 25.00% | 91.67% |
| Safety regression rate | 0.00% | 0.00% |
| Task success after replay | 25.00% | 91.67% |
| Critical-step localization accuracy | — | 100.00% |
| Failure-class accuracy | — | 100.00% |
| FROZEN token accounting | 1,368 | 2,872 |
| Estimated model cost | $0.00 | $0.00 |

Median runtime is machine-run-specific and remains in `evidence/final_evaluation.json`; timestamps and local latency may change while decisions, hashes, denominators, and aggregate rates must reproduce.

## Case matrix

| Case | Failure class | Steps | Decisive invariant | Expected repair | Baseline | SuperTuriya | Verifier |
|---|---|---:|---|---|---:|---:|---|
| eval-001 | stale memory | 4 | `state.region_matches_request` | `retrieval.filter → context.region` | No | Yes | Verified |
| eval-002 | stale memory | 4 | `state.region_matches_request` | `retrieval.filter → context.region` | No | Yes | Verified |
| eval-003 | missing evidence | 4 | `evidence.final_has_catalog_ref` | `prompt_rule.add → final_response.evidence` | Yes | Yes | Verified |
| eval-004 | missing evidence | 4 | `evidence.final_has_catalog_ref` | `prompt_rule.add → final_response.evidence` | Yes | Yes | Verified |
| eval-005 | invalid tool argument | 4 | `tool.quantity_is_positive_integer` | `tool_argument.constraint → fulfill.quantity` | Yes | Yes | Verified |
| eval-006 | invalid tool argument | 4 | `tool.quantity_is_positive_integer` | `tool_argument.constraint → fulfill.quantity` | No | Yes | Verified |
| eval-007 | tool-output misinterpretation | 4 | `tool.available_status_respected` | `tool_result.validation → catalog.status` | No | Yes | Verified |
| eval-008 | tool-output misinterpretation | 4 | `tool.available_status_respected` | `tool_result.validation → catalog.status` | No | Yes | Verified |
| eval-009 | missing approval | 4 | `policy.approval_checked_when_required` | `approval_rule.add → fulfill.approval` | No | Yes | Verified |
| eval-010 | missing approval | 4 | `policy.approval_checked_when_required` | `approval_rule.add → fulfill.approval` | No | Yes | Verified |
| eval-011 | orchestration error | 4 | `workflow.catalog_before_fulfill` | `route.condition → workflow.order` | No | Yes | Verified |
| eval-012 | orchestration + evidence | 4 | `workflow.catalog_before_fulfill` | `route.condition → workflow.order` | No | No | Rejected |

The classes are distinct at the violated-invariant and repair-operation layers, although all frozen trajectories contain four summarized steps. `eval-012` is multi-causal: ordering is repaired but missing evidence remains.

## Replay and governance contracts

Replay records initial-state, task, fixture, frozen-policy, resulting-config, intervention, and verification hashes. Patch application rejects stale `before_value` or `before_hash`. The recorded `config_diff` proves only the approved target changes.

Governance paths remain separate:

```text
candidate → human replay approval → replay → verifier
verified candidate → separate human activation → active policy
```

Approval does not activate. Failed replay cannot activate. A synthetic new safety regression cannot count as recovery. A different valid path may pass when task success and all invariants hold.

Representative accepted replay: `evidence/trajectories/replay_eval-006.json`.

Representative rejected replay: `evidence/trajectories/replay_eval-012.json`.

## Separate shadow-transfer proof

After the verified `eval-006` quantity intervention becomes an active procedural policy, `shadow-transfer-001` applies that policy to a new five-step build-worker provisioning trace. The original shadow run fails with quantity `0`; the policy-matched replay changes only `quantity_constraint`, passes all invariants, and records a verified safe transfer in `evidence/shadow_transfer.json`.

This showcase is excluded from the 12-case benchmark, CAVRR, and localization metrics. One curated transfer case demonstrates policy reuse mechanics but does not establish broad or production generalization.

## Verification

Forty-nine tests pass, covering original v1 behavior plus benchmark hashes, label isolation, case parity, patch validation, before-state matching, approval gating, activation gating, safety regression, frozen-state hashes, deterministic fixtures, one-change replay, alternate valid paths, CAVRR denominator, committed decisions, shadow transfer, strict-schema LIVE provider probing, deterministic LIVE intervention binding, rate-limit retry behavior, transport-guarded ablation, independent-v2 source/case freeze, cases-only execution, persisted-before-scoring enforcement, canary rejection, author-packet controls, API, and UI routing.

```bash
python3 -m superturiya.hackathon validate
python3 -m superturiya.hackathon evaluate --mode frozen
python3 -m superturiya.hackathon shadow-transfer
python3 -m unittest discover -s tests -v
```

## Pre-existing versus hackathon-added

Pre-existing at `f91b449506717a6cae7c1392746303a3d198529c`: HTTP/static app, SQLite trace/memory/graph/score/policy/audit substrate, heuristic counterfactuals, quantum-inspired interpretation, seed demo, and one unit test.

Hackathon-added: frozen benchmark and labels, baseline, Investigator, Adaptation, typed patch allowlist, deterministic simulator/verifier, before-state enforcement, replay provenance, CAVRR, intervention/replay/evaluation persistence, two-stage governance, judge UI, CLI, 52+ evidence artifacts, and adversarial contract tests.
