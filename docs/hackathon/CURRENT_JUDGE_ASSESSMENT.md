# Current Judge Assessment

> Historical pre-External-v2 assessment. See `external_v2_final_report.md` for
> the completed frozen evaluation and current claim boundary.

Date: 30 August 2026
Assessment posture: strict, evidence-weighted, and submission-aware
Verdict: strong competitive prototype; not yet ready for a final winning claim

## Score now: 78/100

This uses the official six-part rubric supplied with the challenge brief.

| Criterion | Max | Score | Evidence | Deduction |
| --- | ---: | ---: | --- | --- |
| Problem and User Value | 15 | 12 | Clear AI-platform user; costly failure-to-learning bottleneck; understandable resource-provisioning demonstration | No user interview, design-partner outcome, or measured time saved |
| Agent Solution and Engineering | 30 | 28 | Purposeful Investigator/Adaptation separation; strict typed operations; frozen-state replay; deterministic verifier; human lifecycle; provenance; same-model LIVE runner; source-frozen predictions-first external-v2 pipeline | Current six-class repair vocabulary remains narrow; no production trace ingestion |
| End-to-End Quality | 20 | 17 | Working local workbench; successful recovery and safe-rejection paths; inspectable LIVE structured outputs; durable policy/audit result; original console preserved | Synthetic workload; no hosted judge URL; final visual/video QA incomplete |
| Measured Improvement | 15 | 5 | Complete development case results, fixed denominators, two sealed synthetic sets, ablations, and an honestly preserved LIVE trial | The strongest +66.67-point claim is development evidence; same-model LIVE v1 is 8/12 vs 8/12; independent v2 has no cases yet |
| Reproducibility | 15 | 11 | Credential-free FROZEN run, standard-library runtime, source/case/gold hashes, predictions-before-scoring enforcement, evidence manifests, isolation audits, 53 passing tests | Evaluated implementation is uncommitted; no license; no public final-clone proof; only one LIVE trial |
| Hot Take and Insights | 5 | 5 | Strong mechanism-backed position: a model proposal is not durable learning until verifier and human governance accept it | No material deduction |
| **Total** | **100** | **78** | | |

The increase from the prior 66-71 range comes from a materially clearer UI,
structured LIVE explainability, provider-contract hardening, preserved negative
evidence, and the external-v2 isolation/freeze implementation. The score does
not exceed 80 because the final independent measured-improvement claim is still
absent.

## Evidence hierarchy

1. **Mechanism proof:** primary FROZEN development benchmark, 3/12 to 11/12,
   with one retained verifier rejection and 0 safety regression.
2. **Structural transfer development evidence:** external v1 FROZEN, 2/12 to
   9/12 across three domains, also 0 safety regression.
3. **Same-model LIVE development evidence:** one trial, direct baseline 8/12
   and SuperTuriya 8/12. Diagnosis remained strong (100% failure-class and
   91.67% critical-step/repair-surface accuracy), but recovery lift was zero.
4. **Final independent evidence:** not yet available. External-v2 infrastructure
   is complete; case count is deliberately zero pending independent authoring.

Only levels 1-3 may be demonstrated today. Level 4 is required before claiming
independent superiority.

## What was implemented in this phase

- Removed all reference-product identity from code and documentation and added
  a repository-wide terminology regression test.
- Retained only a generic, sanitized external-workload adapter contract; it is
  explicitly excluded from benchmark claims.
- Added visible-case and private-gold JSON schemas under `benchmark/external_v2/`.
- Narrowed the external-v2 claim to cloud-operations scenario families and
  froze a versioned six-class taxonomy before independent authoring.
- Defined and tested the exact model-visible case/invariant projections;
  verifier-only expected values, private labels, repairs, and canaries are
  excluded from actual outbound model payloads.
- Made author schemas fail closed on undeclared fields, derived denominator
  eligibility mechanically, and required every private repair target to
  resolve to an actual mutable case surface.
- Added an agent-visible loader that operates when private gold is completely
  absent.
- Added opaque-ID, gold-field/canary leakage, file parity, critical-step,
  allowlisted repair, and minimum-size validation.
- Added different-author/reviewer enforcement, one-time freeze, per-file and
  aggregate SHA-256 hashes, and post-freeze mutation detection.
- Added reviewer instructions, protocol, CLI, Make targets, and independent
  author handoff ZIP.
- Froze the exact SUT source and three-trial LIVE contract under hash
  `b49f961ae86a...`.
- Added cases-only prediction, raw-artifact persistence, evaluator-only scoring,
  private-canary rejection, ablation scoring, case-level paired bootstrap
  uncertainty, and evidence-manifest stages.
- Regenerated the sanitized author packet under SHA-256
  `89f778d3b1e7...` with an exact nine-member manifest.
- Full regression result: 53/53 passing.

## Submission readiness: 64%

| Area | Status | Readiness |
| --- | --- | ---: |
| Core product and demo loop | Complete and locally verified | 95% |
| Automated tests and FROZEN reproduction | Complete | 95% |
| Explainability and claim boundaries | Complete for current evidence | 90% |
| Independent measured evidence | Complete executable pipeline; cases/results missing | 40% |
| Repository packaging | Uncommitted implementation; license and public-clone proof missing | 35% |
| Submission media and form | Five-minute video and final form fields missing | 10% |

This percentage is not the rubric score. It represents how much of the final
submission workflow is actually complete.

## P0 next actions

1. Freeze the system-under-test commit. Do not tune prompts after external-v2
   authoring begins.
2. Ask an independent author to create 12-16 opaque v2 cases using only the
   supplied schemas and instructions. Ask a different person to review them.
3. Validate and freeze v2, then run the same model, temperature, cases, trial
   count, replay, and verifier for baseline and SuperTuriya. Preserve errors and
   all case-level results.
4. Complete the remaining two LIVE repetitions and cumulative LIVE ablation.
   A zero or negative result must remain visible.
5. Have one real agent engineer inspect 5-10 diagnoses; record agreement,
   repair acceptance, and time-to-localize. This directly strengthens user
   value even if benchmark lift remains modest.
6. Then choose a license, review and commit all changes, push the public repo,
   clone it fresh, run the full reproduction, and record the exact commit SHA.
7. Record a sub-five-minute video showing: problem, architecture, LIVE model
   role, one success, one verifier rejection, evidence hierarchy, measured
   result, and reproduction command.

## Submission threshold

Do not submit while the repository clone does not contain the evaluated code or
the video is absent. A credible minimum is: committed public clone, license,
fresh-clone pass, complete trajectories, video, and honest current evidence.
The winning-state target adds a frozen independent-v2 lift or, if lift remains
zero, a compelling diagnosis/governance value result from an external reviewer.
