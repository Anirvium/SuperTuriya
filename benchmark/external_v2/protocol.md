# Independent External-Validity Protocol v2

## Purpose

This benchmark is the final credibility test for SuperTuriya within the frozen
cloud-operations simulator. External v1 is
development evidence because the system was tuned after its results were seen.
V2 must therefore be authored and adjudicated independently after the
system-under-test is frozen.

## Order of operations

1. Freeze the exact SuperTuriya source, prompts, typed operations, verifier,
   provider, model, temperature, and trial count with `sut-freeze`.
2. Give the independent author exactly the sanitized ZIP described under
   **Author packet contents**. Do not give them system prompts, repair mappings,
   prior cases, or model outputs.
3. Author 12-16 opaque cases across at least three frozen cloud-operations
   scenario families, including at least three genuinely difficult or
   multi-causal cases. Do not describe this as unrelated-domain transfer.
4. Store visible cases in `cases/` and labels in `gold_private/`.
5. Run `validate`; have a different named reviewer inspect the package.
6. Run `freeze` once. Any later byte change requires a new benchmark namespace.
7. Run the cases-only prediction stage. It verifies only public case hashes and
   must persist raw predictions before evaluator-only scoring begins.
8. Run scoring as a separate command. Only this later stage may open private
   labels. It rejects raw output containing any private canary.
9. Execute the same model, temperature, cases, trial count, replay simulator,
   and deterministic verifier for the direct baseline and SuperTuriya.
10. Preserve all successes, failures, schema errors, provider errors, runtime,
   token usage, case-level decisions, and aggregate metrics.
11. Do not tune prompts, repair mappings, verifier logic, or case eligibility
   after the first final run. A defect discovered after freeze must be disclosed
   and addressed in a future namespace.

## Primary measure

Coverage-Adjusted Verified Recovery Rate (CAVRR): verified safe recoveries
divided by all accepted, mechanically validated, initially failing cases. The
author does not provide an eligibility field and cannot change the denominator.
Report numerator, denominator,
absolute percentage-point difference, safety regression rate, critical-step
accuracy, failure-class accuracy, repair-surface accuracy, latency, and usage.

## Model-visible projection

All direct-baseline, Investigator, and Adaptation prompts receive the same case
projection:

- `case_id`;
- `goal`;
- current-request fields from `initial_state`, excluding `faulty_quantity_arg`
  and `faulty_order`;
- fixed tool descriptions;
- `trajectory`.

`expected_state`, raw tool fixtures, workflow configuration, scenario/difficulty
metadata, private labels, acceptable repairs, adjudication notes, and canaries
are excluded. The Investigator additionally receives only projected failed-
invariant records containing `invariant_id`, `passed`, and `evidence_refs` from
the frozen verifier. Verifier `expected` and `actual` values remain excluded.
Adaptation additionally receives the Investigator's own structured output.
Neither receives private adjudication data.

## Uncertainty

Every trial uses the same cases, so case-trial observations are not treated as
independent. Report every case's baseline and final outcomes for every trial,
aggregate repeated outcomes within each case, and compute a paired nonparametric
bootstrap interval over cases for the mean CAVRR difference. The implementation
uses 10,000 case resamples, a frozen seed, and a 95% percentile interval. Report
the interval as a small-sample descriptive uncertainty estimate, not a population
guarantee.

## Claim rule

No independent-improvement claim is allowed until a frozen v2 run beats the
same-model direct baseline on CAVRR without a safety regression. Statistical
uncertainty and the small benchmark size must remain visible.

## Author packet contents

The sanitized ZIP contains exactly:

- `README.md`;
- `case.schema.json`;
- `gold.schema.json`;
- `failure_taxonomy.v1.json`;
- `protocol.md`;
- `reviewer_instructions.md`;
- `templates/case.template.json`;
- `templates/gold.template.json`;
- `PACKET_MANIFEST.json` containing hashes of every other member and explicit
  statements that prompts, model outputs, and credentials are absent.

## Executable commands

Before sending the author packet:

```bash
make v2-sut-freeze
make v2-sut-verify
make v2-author-packet
```

After independently authored files arrive:

```bash
make v2-validate
make v2-freeze AUTHOR_ID='<author>' REVIEWER_ID='<different-reviewer>'
make v2-verify
make v2-predict OUTPUT='evidence/external_validity/v2/raw_live_comparison.json'
make v2-score \
  RAW='evidence/external_validity/v2/raw_live_comparison.json' \
  OUTPUT='evidence/external_validity/v2/scored_live_comparison.json'
make v2-evidence-manifest EVIDENCE_ROOT='evidence/external_validity/v2'
```
