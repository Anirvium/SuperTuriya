# External-v2 Qwen fallback

This separately preregistered experiment exists because the primary frozen
model exhausted its free daily capacity before producing a complete raw
artifact on submission day.

It does not replace or complete the primary model contract. The existing 72
primary-model checkpoints remain untouched. Results from this run must be
reported as a separate same-Qwen baseline-versus-SuperTuriya comparison.

The following remain identical to the primary experiment:

- frozen 16-case benchmark and order;
- three trials and temperature zero;
- Baseline, Investigator, and Adaptation prompts;
- typed repair logic, approval, replay, and deterministic verifier;
- cases-only prediction followed by separately authorized private scoring.

The only experimental change is the preregistered model identity. The selection
was made for documented free-tier capacity before any fallback-model output or
performance was observed. The immutable contract is
`evidence/external_validity/v2/qwen_fallback_contract.json`.

Run `make v2-qwen-validate`, export the exact preregistered endpoint and model,
then run `make v2-qwen-probe` followed by `make v2-qwen-predict-resume`.
