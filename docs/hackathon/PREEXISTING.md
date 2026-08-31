# Pre-Hackathon State

Frozen on 29 August 2026 before adaptive-loop implementation.

- Starting commit: `f91b449506717a6cae7c1392746303a3d198529c`
- Commit subject: `Initial SuperTuriya implementation`
- Commit date: 15 July 2026

## Present before the micro1 build

- Standard-library HTTP server and local dashboard.
- SQLite observations, memories, provenance graph, traces, trace steps, scores, policies, audit events, and subject deletion.
- Heuristic trajectory scoring, root-cause hypotheses, counterfactual estimates, memory extraction/search, policy synthesis, and quantum-inspired interpretation.
- One seeded care-coordination demonstration and one end-to-end unit test.
- Product, evaluation, security, roadmap, and canonical trace documentation.

## Important limitations at the freeze

- No fixed benchmark, held-out split, baseline runner, Investigator Agent, Adaptation Agent, typed intervention, approval checkpoint, replay engine, deterministic recovery verifier, coverage-adjusted recovery metric, or improvement evidence bundle.
- No representative saved trajectories for reasoning agents.
- No clean-environment baseline/evaluation commands.
- Existing `synthesise_policies` wrote generated policies through `add_policy`, whose default status was `active`. Human accept/reject/defer was documented as future work but not implemented. This behavior violates the new governance contract and must be changed without hiding its pre-existing origin.
- Existing utility and counterfactual scores are heuristic signals, not benchmark ground truth.
- The existing quantum-inspired layer is classical, deterministic, and off the hackathon default path unless an ablation proves value.

## Reuse boundary

Existing storage, trace capture, graph, audit, API, and static-app infrastructure may be extended. Existing functionality must not be removed merely to simplify the hackathon path.

No permitted external-workload source, license, immutable snapshot, or exported
trajectory was supplied. No external product code or claims are included in the
primary build.
