# External-v2 resumable execution protocol

This execution-only protocol handles provider quota interruption without changing
the frozen External-v2 system under test or benchmark.

## Boundary

- The frozen model, temperature, prompts, agents, repair logic, replay engine,
  verifier, case order, trial count, and scoring stage remain unchanged.
- Runtime case loading opens only `benchmark/external_v2/cases/` and public
  manifests. It never imports or opens `gold_private/`.
- Execution order remains baseline cases 001–016, then final cases 001–016,
  repeated for trials 1–3.
- Every completed model call is written as a new immutable JSON checkpoint
  using an atomic, no-overwrite same-directory publish.
- A checkpoint is accepted on resume only when its SUT hash, case aggregate,
  model/endpoint contract, transport policy, trial index, phase, case ID, provider
  ledger, and harness hash match.
- Interrupted units are not treated as predictions. A metadata-only attempt
  journal records their location, error, transport counters, and any successful
  calls whose outputs were discarded.
- The standard raw prediction artifact is created only after all 144 checkpoints
  exist: 16 cases × 3 calls × 3 trials. Private scoring remains a later stage.

This protocol changes persistence granularity only. Results should disclose that
execution was resumed across provider-capacity windows when attempt journals are
present.

## Commands

With the frozen provider variables and API key exported:

```bash
make v2-verify
make v2-sut-verify
make v2-predict-resume \
  OUTPUT='evidence/external_validity/v2/raw_live_comparison.json'
```

If the command reports `paused_safe_to_resume`, wait until provider capacity is
available and run the identical command again. Inspect progress without invoking
the provider:

```bash
make v2-predict-resume-status \
  OUTPUT='evidence/external_validity/v2/raw_live_comparison.json'
```

Do not run scoring until status is `complete` and the raw output exists.
