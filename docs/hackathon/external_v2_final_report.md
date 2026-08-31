# SuperTuriya External-v2 Evaluation — Short Report

## Objective

Test whether SuperTuriya improves recovery from failed agent trajectories under a
strict, externally authored and frozen evaluation—not merely whether the product
works on its demonstration cases.

## What we did

1. Froze the SuperTuriya system under test, including prompts, repair logic,
   replay behavior, verifier semantics, model-visible projections, and a
   three-trial same-model comparison contract.
2. Imported and mechanically validated 16 blinded/adversarial held-out cases
   across four cloud-operations scenario families. Visible cases and private gold
   remained separated.
3. Completed semantic review, corrected one adjudicated private critical-step
   label, and froze the benchmark with content hashes.
4. Began the primary GPT-OSS evaluation. Its free daily capacity was exhausted
   after 72 of 144 calls, before any complete raw artifact or score existed.
5. Added a call-atomic resumable execution layer outside the frozen SUT. It
   preserves every completed call while leaving cases, prompts, agents, repair
   logic, verifier, and scoring unchanged.
6. Before observing any fallback-model output, preregistered Qwen 3.8 27B as a
   separate capacity-driven fallback experiment. It did not replace the primary
   model contract.
7. Executed 144 calls: three trials over the same 16 cases for both the direct
   baseline and SuperTuriya. Raw predictions were persisted before private gold
   was opened for scoring.
8. Generated a scored artifact and content-addressed evidence manifest.

## Results

| Measure | Result |
|---|---:|
| Direct baseline CAVRR | 50.00% (8/16) |
| SuperTuriya CAVRR | 50.00% (8/16) |
| Absolute improvement | 0.00 percentage points |
| Paired 95% interval | [0.00, 0.00] |
| Critical-step localization accuracy | 100.00% |
| Decisive-invariant accuracy | 81.25% |
| Failure-class accuracy | 62.50% |
| Mean repair-surface accuracy | 41.67% |
| Safety-regression rate | 0.00% |

The result was identical across all three trials. The run used 160,658 provider
tokens, completed all 144 calls without retries or aborted attempts, and recorded
no credential values or private-label leakage.

## Evaluation

The experiment validates SuperTuriya's strongest current capabilities:

- deterministic and auditable evaluation;
- perfect localization of the accepted critical-step label set;
- strong decisive-invariant diagnosis;
- typed, approval-gated interventions;
- immutable replay and scoring evidence;
- zero observed safety regression.

It does **not** establish that the current Adaptation stage improves verified
recovery over a strong direct-model baseline. Both systems recovered the same
eight cases. Repair-surface selection is the clearest remaining technical
bottleneck.

## Submission-safe conclusion

SuperTuriya should be presented as a governed trajectory-intelligence and
verification layer that makes agent failures localizable, repairs typed and
reviewable, and learning auditable. The deterministic demo result may be shown as
product behavior, while this External-v2 result must be reported separately as
an honest external evaluation with zero measured recovery lift.

This negative result strengthens the credibility of the evidence process: the
benchmark was frozen, fallback selection was preregistered for capacity rather
than performance, raw predictions preceded private scoring, and no post-freeze
tuning or model-shopping was used.

## Evidence

- `evidence/external_validity/v2/qwen_fallback_contract.json`
- `evidence/external_validity/v2/raw_live_comparison_qwen_fallback.json`
- `evidence/external_validity/v2/scored_live_comparison_qwen_fallback.json`
- `evidence/external_validity/v2/manifest.json`
