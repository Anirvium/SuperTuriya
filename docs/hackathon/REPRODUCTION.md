# Reproduction Guide

Status: verified on 29 August 2026 using Python 3.12.10 on macOS. The project contract requires Python 3.9 or newer.

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

Expected tests: 53 passing tests. They cover frozen benchmark hashes, mechanical hidden-label isolation, baseline/final parity, malformed and stale patch rejection, approval and activation gates, safety regressions, frozen-state and fixture identity, single-change replay, alternate valid paths, fixed metrics, difficult-case rejection, one non-benchmark shadow transfer, LIVE provider identity, strict-schema probing, deterministic LIVE intervention binding, complete Investigator schema prompting, governance-versus-repair prompt separation, append-preserved LIVE evidence, safe explainability projection, explainability API routing, terminology controls, rate-limit retry behavior, transport-guarded ablation, API/static UI routing, audit persistence, the pre-existing full trajectory loop, and the independent-v2 source-freeze, strict visible projection, frozen taxonomy, repair-surface resolution, cases-only runtime, canary, predictions-before-scoring, case-level paired uncertainty, and author-packet controls.

## Independent external-v2 gate

```bash
python3 -m superturiya.external_v2 status
```

Expected before independent authoring: `awaiting_independent_cases`, 0 visible
cases, 0 private-gold files, and `ready_to_freeze: false`. This is a required
honest blocker, not a failed product test. After an independent author supplies
12-16 cases and a different reviewer checks them:

```bash
python3 -m superturiya.external_v2 validate
make v2-freeze AUTHOR_ID='<author>' REVIEWER_ID='<reviewer>'
python3 -m superturiya.external_v2 verify
```

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

## Optional LIVE mode

LIVE configuration will use environment variables and must never be committed:

- `SUPERTURIYA_LLM_ENDPOINT`
- `SUPERTURIYA_LLM_API_KEY`
- `SUPERTURIYA_LLM_MODEL`

LIVE mode records the endpoint/model metadata, temperature, hashes, usage, latency, and estimated cost returned by the provider. LIVE results are not the submitted reproducibility claim and require an explicitly configured compatible service.

The final competition path uses Groq Free Tier and `openai/gpt-oss-120b`, with a one-call probe plus recorded pacing and retry controls. Use the exact commands and claim boundaries in [GROQ_LIVE_EVIDENCE.md](GROQ_LIVE_EVIDENCE.md).
