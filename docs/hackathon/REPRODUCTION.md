# Reproduction Guide

Status: verified from the public submission commit on 31 August 2026 using
Python 3.12.10 on macOS. The project contract requires Python 3.9 or newer.

## Requirements

- Python 3.9 or newer.
- No mandatory external service, GPU, or API key for FROZEN mode.

## Demo domain

The benchmark models an enterprise resource-provisioning agent that must combine tenant context, regional catalog availability, quantity constraints, approval policy, evidence references, and correct tool order. It is a curated deterministic workload for evaluating the governance loop, not production-derived traffic.

## One-command paths

```bash
make validate
make evaluate
make test
make run
```

## Exact commands

```bash
python3 -m superturiya.hackathon validate
python3 -m superturiya.hackathon baseline --mode frozen
python3 -m superturiya.hackathon evaluate --mode frozen
python3 -m superturiya.hackathon demo --case eval-006 --mode frozen
```

FROZEN reuses committed reasoning outputs and recomputes deterministic replay verification and aggregate metrics. It does not reproduce model inference.

Expected evaluation summary:

```text
Baseline CAVRR: 25.00% (3/12)
Final CAVRR: 91.67% (11/12)
Absolute improvement: 66.67 percentage points
Safety regression rate: 0.00%
```

Expected tests: **58 passing tests**. They cover frozen benchmark hashes,
mechanical hidden-label isolation, baseline/final parity, malformed and stale
patch rejection, approval and activation gates, safety regressions, frozen-state
and fixture identity, single-change replay, alternate valid paths, fixed metrics,
difficult-case rejection, one non-benchmark shadow transfer, provider identity,
strict-schema probing, resumable execution, fallback preregistration, safe
explainability, API/static UI routing, audit persistence, the pre-existing full
trajectory loop, and the External-v2 source freeze, projection boundary,
taxonomy, repair targets, cases-only runtime, canary rejection,
predictions-before-scoring contract, paired uncertainty, and author packet.

## Frozen External-v2 verification

```bash
make v2-verify
make v2-sut-verify
```

Expected benchmark verification:

- status `frozen` and `valid: true`;
- 16 cases and 16 eligible, initially failing cases;
- four cloud-operations scenario families and five difficult cases;
- no hidden fields in the model-visible projection;
- valid frozen file hashes.

Expected SUT verification: status `frozen`, valid source hashes, and system hash
`b49f961ae86aedd2cbdf85ada2209fbb97307ffa3e76d29e4fcae636e024ee9e`.

These commands validate the already-frozen benchmark and SUT without invoking a
model or opening private gold for a new comparison.

Optional bounded transfer proof:

```bash
python3 -m superturiya.hackathon shadow-transfer
```

Expected: `Verified safe transfer: True`. This one curated shadow case is excluded from CAVRR and does not establish production generalization.

## Evidence outputs

`python3 -m superturiya.hackathon evaluate --mode frozen` writes:

- `evidence/final_evaluation.json`: comparison, metric contract, benchmark hashes, and complete results;
- `evidence/baseline_evaluation.json`: complete baseline results;
- `evidence/superturiya_evaluation.json`: complete final results;
- `evidence/trajectories/`: per-case baseline, Investigator, Adaptation, and replay records;
- `evidence/EVIDENCE_MANIFEST.json`: file list plus benchmark and label hashes.

Runtime IDs, timestamps, and measured local latency may differ between executions. Case/label hashes, denominators, verification decisions, and aggregate recovery metrics must match.

## Judge UI

```bash
python3 -m superturiya --seed --port 8765
```

Open `http://127.0.0.1:8765`. The seed step persists the FROZEN held-out evaluation if the local database does not already contain one. The recommended successful case is `eval-006`; the recommended verifier-rejection case is `eval-012`.

## External-v2 recorded experiment

The committed final experiment is a three-trial, same-model comparison over 16
cases. The primary run paused at 72/144 checkpoints when free daily capacity was
exhausted, before a complete artifact or score existed. A capacity-driven Qwen
3.8 27B fallback was preregistered before any fallback output was observed. It
completed all 144 calls and used 160,658 provider tokens, with about 50 minutes
of enforced pacing and no paid cost incurred.

Committed result: direct baseline **8/16 (50.00%)**, SuperTuriya **8/16
(50.00%)**, absolute improvement **0.00 percentage points**, and safety
regression **0.00%**. The result was identical across all three trials.

Inspect the result without provider credentials:

```bash
python3 -m json.tool evidence/external_validity/v2/scored_live_comparison_qwen_fallback.json
python3 -m json.tool evidence/external_validity/v2/manifest.json
```

See `external_v2_final_report.md` for the claim boundary and interpretation.

## Optional new LIVE execution

LIVE configuration will use environment variables and must never be committed:

- `SUPERTURIYA_LLM_ENDPOINT`
- `SUPERTURIYA_LLM_API_KEY`
- `SUPERTURIYA_LLM_MODEL`

LIVE mode records endpoint/model metadata, temperature, hashes, usage, latency,
and transport behavior. It requires an explicitly configured compatible service
and is not necessary to reproduce the committed deterministic demo, tests,
benchmark integrity, or scored evidence. Do not rerun or rescore the frozen
competition experiment as part of ordinary judge reproduction.
