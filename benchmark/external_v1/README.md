# External Structural-Transfer Benchmark v1

This directory is sealed evidence input for the external-validity milestone.

It contains 12 held-out fixtures across software release, data access, and incident rollback workflows. The traces use new IDs, wording, source tools, domains, and five-to-seven-step sequences. Three cases contain a second independent failure so a single repair should be rejected by the full verifier.

## Independence disclosure

The set is independent from the primary benchmark's case text and sequences, but it was internally authored with knowledge of SuperTuriya's failure surfaces. It is therefore a structural-transfer benchmark, not a third-party blind evaluation. This wording is part of the evidence contract and must not be weakened in submission copy.

## Freeze rule

`freeze_manifest.json` records byte and canonical content hashes. Any change to `cases.json` or `labels.json` must create `external_v2`; it must never silently update v1.

The external runner was not implemented and no baseline/final output was generated before these hashes were recorded. The existing deterministic verifier was used only to confirm that every fixture began as an eligible failure.

## Visibility

- `cases.json`: runtime-visible inputs.
- `labels.json`: evaluator-only gold data with unique leakage canaries.
- `freeze_manifest.json`: immutable benchmark identity and authoring disclosure.

The runtime stage must succeed in a process that never opens `labels.json`. Scoring happens only after raw predictions have been persisted.
