# External-Validity Evaluation v1

Status: frozen benchmark, isolation audit, frozen comparison, frozen ablation,
and one real-provider LIVE comparison complete. LIVE produced baseline/final
parity and v1 is classified as development evidence.

## Objective

This layer does not change the core SuperTuriya architecture. It tests whether the existing diagnosis, typed intervention, replay, verification, and governance mechanism transfers to new trace wording, domains, step sequences, and multi-causal failures.

The milestone is evidence hardening, not capability expansion.

## Benchmark identity

- ID: `superturiya-external-structural-transfer-v1`
- Root: `benchmark/external_v1/`
- Split: 12 held-out cases only.
- Domains: software release, data access, and incident rollback.
- Trajectory lengths: five to seven steps.
- Failure classes: six, exactly two cases per class.
- Multi-causal cases: `xval-002`, `xval-006`, and `xval-012`.

Frozen hashes:

- `cases.json`: `5a4331157a7334a9ceae37ac4738292ed3aa617f30a156a3324af8f7a48438b6`
- `labels.json`: `4deb121ce6f55e08a83aecc7456b156943ba95e7b284c1980b921fd5041807cc`
- canonical case content: `8ccd3b63f15f8518aa005aa3d8f3f62edc3b5ff5256ca86741215d89da61be4c`
- canonical gold content: `06cd1389a11f3366fd719894076eecf29fa1a8d7ac04397f24047af71107f3a7`

Any byte change requires a new `external_v2` namespace. Post-freeze tuning of v1 is prohibited.

## Independence statement

This set is structurally independent from the primary benchmark:

- new case IDs;
- new user wording;
- new source tool names;
- three new domain framings;
- longer and varied step sequences;
- three multi-causal combinations.

It is not third-party independent. It was internally authored with knowledge of SuperTuriya's existing six-class invariant and repair vocabulary. This limitation is embedded in the freeze manifest and scored artifacts. It must remain in judge-facing claims.

The benchmark is therefore evidence of structural transfer, not unrestricted cross-domain generalization.

## Freeze sequence

1. Cases and evaluator gold were authored.
2. The existing verifier confirmed every case was initially failing.
3. No external baseline or SuperTuriya prediction was generated.
4. Byte and canonical hashes were recorded in `freeze_manifest.json`.
5. Only then were the external runner, isolation checks, scoring, and ablations implemented.

## Mechanical gold isolation

Runtime and scoring are separate modules and stages:

```text
cases-only runtime process
    -> persisted raw baseline/final predictions
    -> evaluator process loads gold
    -> scoring and evidence artifact
```

The isolation audit enforces:

- runtime source contains no evaluator module import, gold filename, gold loader, or canary symbol;
- runtime succeeds while `Path.open` and `builtins.open` reject gold access;
- every label has a unique canary that must not occur in cases, prompts, or runtime output;
- a subprocess runs from a temporary benchmark directory containing only `cases.json`;
- scoring begins only after the subprocess output exists;
- cases and gold must match the sealed hashes and ID ordering.

Run:

```bash
python3 -m superturiya.external_validity validate
python3 -m superturiya.external_validity isolation
```

## Frozen result

```text
Direct frozen baseline: 2/12 = 16.67% CAVRR
SuperTuriya frozen:      9/12 = 75.00% CAVRR
Absolute improvement:   7 recoveries = 58.33 percentage points
Safety regression:      0.00%
```

All three multi-causal cases are rejected because a single typed repair leaves another invariant unresolved.

Diagnostic scores are 12/12 for critical step, failure class, and repair surface. These remain taxonomy-aligned metrics; they do not prove unconstrained diagnosis.

## Ablation contract

The ablation harness uses the same cases, initial states, replay engine, approval semantics, and verifier where applicable.

| Variant | Result | Interpretation |
|---|---:|---|
| Direct raw trajectory | 2/12 verified | Direct frozen repair baseline |
| Invariant preflight without typed repair | 0/12 verified | Visibility alone does not change configuration |
| Structured repair without full verifier | 11/12 task completion | Unsafe upper bound; ignores unresolved invariants |
| Full verified repair | 9/12 verified | Full invariant gate rejects two superficially completed cases plus one still-failed case |
| Full verified and governed | 9/12 activation-eligible | Durable eligibility exactly matches verified recovery |

The 11/12 row must never be reported as verified recovery. Its purpose is to show that task completion overstates safe improvement.

Run:

```bash
python3 -m superturiya.external_validity ablation --mode frozen
```

## Same-model LIVE protocol

Required environment variables:

- `SUPERTURIYA_LLM_ENDPOINT`
- `SUPERTURIYA_LLM_API_KEY`
- `SUPERTURIYA_LLM_MODEL`

Optional transport controls used for constrained Free tiers:

- `SUPERTURIYA_LLM_MIN_INTERVAL_SECONDS`
- `SUPERTURIYA_LLM_MAX_RETRIES`
- `SUPERTURIYA_LLM_RETRY_BASE_SECONDS`

Run:

```bash
python3 -m superturiya.external_validity probe
python3 -m superturiya.external_validity live --trials 3
python3 -m superturiya.external_validity ablation --mode live
```

The runner enforces:

- one unchanged endpoint, credential binding, and requested model for baseline and final;
- identical cases and order;
- identical original verifier results;
- temperature 0 for every request;
- exactly one returned provider model identity;
- provider-reported prompt, completion, and total token capture;
- three complete trials;
- explicit pacing and bounded retries only for 429, timeout, and transient 5xx failures;
- retry attempts, reasons, and delays recorded separately from successful calls;
- scoring only after each runtime comparison is complete.

No credential value or model response content is written to evidence. Only the endpoint hash, requested model, presence flag, provider-returned model identity, usage, prompt hashes, and public transport/retry metadata are stored.

The contract is tested with a local OpenAI-compatible fake server. The test proves same-model enforcement, provider usage capture, scoring, and failure on mixed provider model identities. It is not a substitute for a real-provider experiment.

The selected competition route is Groq Free Tier with `openai/gpt-oss-120b`. Follow `GROQ_LIVE_EVIDENCE.md`. Until a participant supplies the runtime API key and completes the experiment, `evidence/external_validity/v1/live_status.json` records the missing-configuration state honestly.

## Evidence artifacts

Generate all credential-free artifacts:

```bash
python3 -m superturiya.external_validity bundle
```

Outputs:

- `freeze_validation.json`
- `isolation_audit.json`
- `frozen_comparison.json`
- `ablation_frozen.json`
- `live_status.json`
- `manifest.json`

The manifest records each artifact's byte hash and size, the current Git revision and dirty-state flag, and hashes of the four external-validity source modules. Evidence generated before the final commit carries an explicit dirty-worktree warning. A completed real-provider run additionally creates `live_comparison.json`.

## Tests

`tests/test_external_validity.py` covers:

- sealed hashes and disclosures;
- post-freeze mutation rejection;
- canary contamination rejection;
- guarded in-process and cases-only subprocess isolation;
- fixed frozen metrics and difficult-case rejection;
- ablation separation;
- same-model LIVE enforcement through a local compatible server;
- one-call provider probing and transient 429 retry behavior;
- rate-limit protection for LIVE comparison and LIVE ablation;
- mixed provider identity rejection;
- provider usage capture;
- artifact manifest hashing;
- unchanged primary benchmark metrics.

## Remaining credibility gates

Two gates cannot be manufactured by this repository:

1. A real same-model provider run with repeated trials.
2. A truly third-party-authored or blind-adjudicated benchmark extension.

Until both exist, claim structural transfer and mechanical isolation—not independent production validation.
