# SuperTuriya

SuperTuriya governs durable learning for stateful, tool-using agents. It turns a failed trajectory into an evidence-backed diagnosis, one typed bounded intervention, a deterministic replay from frozen state, and—only after verification plus explicit review—an active procedural policy.

This micro1 Frontier Engineering Challenge build is local-first, credential-free in FROZEN mode, and implemented with the Python standard library and SQLite.

## Exact demo use case

The controlled workload is **enterprise resource-request provisioning**. A tool-using agent receives a request such as “provision two approved compute sandboxes in `ap-south`, confirm catalog availability, and cite the evidence record.” It must read tenant context, interpret region and quantity, validate the resource catalog, obtain approval when required, call the provisioning tool, and return an evidence-linked result.

SuperTuriya is not the provisioning agent. It is the reliability and governance control plane around that agent: it diagnoses a failed run, proposes one bounded repair, tests the repair against the same frozen request, and controls whether the verified repair becomes reusable procedural policy.

The benchmark is deliberately synthetic and deterministic—not sampled from production—and is used to prove control-plane mechanics under inspectable conditions. Regions, quantities, approvals, and tool outputs are curated fixtures covering six structurally distinct failure classes. The measured result is therefore a controlled benchmark result, not a claim of production generalization.

## Controlled development result

Primary metric: **Coverage-Adjusted Verified Recovery Rate (CAVRR)**.

| System | Verified safe recoveries | CAVRR | Safety regression rate |
|---|---:|---:|---:|
| Direct raw-trajectory baseline | 3 / 12 | 25.00% | 0.00% |
| SuperTuriya Investigator + Adaptation | 11 / 12 | 91.67% | 0.00% |
| Absolute improvement | +8 | +66.67 percentage points | — |

All 12 held-out cases are initially failing and eligible. The benchmark contains two held-out cases for each of six failure classes. The unrecovered difficult case is retained and reported: its one proposed repair fixes only one of two independent causes, so verification rejects promotion.

This 91.67% result is controlled development evidence, not the final independent
claim. System prompts were revised after inspecting development results. A
same-model LIVE v1 run subsequently produced parity—8/12 for the direct baseline
and 8/12 for SuperTuriya—while retaining stronger diagnosis/localization scores.
That negative result is preserved rather than hidden.

FROZEN reproduces committed structured reasoning outputs, deterministic replay, verification, and scoring. It does **not** reproduce model inference. Optional LIVE mode uses a configured OpenAI-compatible endpoint.

## Run the judge demo

```bash
python3 -m superturiya --seed --port 8765
```

Open `http://127.0.0.1:8765`, then follow the numbered screen:

1. Investigate `eval-006` to localize the invalid tool argument.
2. Inspect the evidence and allowlisted typed intervention.
3. Explicitly approve the patch and replay from frozen state.
4. Activate procedural learning in a separate governance action.

Try `eval-012 · difficult` to demonstrate safe rejection: the replay does not pass every invariant, so activation stays disabled.

## Reproduce the evidence

```bash
python3 -m superturiya.hackathon validate
python3 -m superturiya.hackathon baseline --mode frozen
python3 -m superturiya.hackathon evaluate --mode frozen
python3 -m superturiya.hackathon demo --case eval-006 --mode frozen
python3 -m superturiya.hackathon shadow-transfer
python3 -m unittest discover -s tests -v
```

Equivalent shortcuts are available through `make validate`, `make evaluate`, `make shadow-transfer`, `make test`, and `make run`.

Committed evidence is under `evidence/`: complete baseline and final reports, all case-level results, representative Investigator and Adaptation trajectories, replay records, hashes, usage, runtime, and the metric contract. See [reproduction instructions](docs/hackathon/REPRODUCTION.md) and the [evidence manifest](docs/hackathon/EVIDENCE_MANIFEST.md).

## External-validity evaluation

A separate sealed structural-transfer benchmark now tests the same mechanism on 12 new five-to-seven-step traces across software release, data access, and incident rollback. It is independent from the primary benchmark's case IDs, wording, and step sequences, but it was internally authored with knowledge of the six repair surfaces. It is not presented as third-party blind evaluation.

```bash
python3 -m superturiya.external_validity validate
python3 -m superturiya.external_validity isolation
python3 -m superturiya.external_validity frozen
python3 -m superturiya.external_validity ablation --mode frozen
python3 -m superturiya.external_validity bundle
```

Frozen structural-transfer result: direct baseline **2/12 (16.67%)** versus SuperTuriya **9/12 (75.00%)**, an absolute gain of seven verified recoveries, with 0.00% safety regression. All three deliberately multi-causal cases remain rejected.

The same-model LIVE runner requires `SUPERTURIYA_LLM_ENDPOINT`, `SUPERTURIYA_LLM_API_KEY`, and `SUPERTURIYA_LLM_MODEL`, runs baseline and final against the same environment and model for three trials, captures provider-reported usage, and fails closed if provider model identities differ.

The final competition provider route uses the GPT-OSS-120B reasoning model (`openai/gpt-oss-120b`) served through the Groq Free Tier. GPT-OSS performs the direct-baseline repair proposal and the structured Investigator and Adaptation judgments; it does not execute tools, verify replay, approve itself, or activate learning. A one-call probe, configurable pacing, bounded transient retries, and a redacted transport ledger make the full experiment executable within published Free-tier constraints without changing the core architecture. Follow the [exact Groq LIVE evidence procedure](docs/hackathon/GROQ_LIVE_EVIDENCE.md); never commit the API key.

See [external validity protocol](docs/hackathon/EXTERNAL_VALIDITY_V1.md), the sealed [benchmark contract](benchmark/external_v1/README.md), and versioned artifacts under `evidence/external_validity/v1/`.

The final evidence gate is the independently authored external-v2 benchmark
covering multiple cloud-operations scenario families over the same frozen
region/quantity/catalog/approval/order simulator. It is not claimed as
unrelated-domain external validity.
Its case/gold schemas, separate private-gold boundary, author/reviewer protocol,
minimum-size check, one-time hash freeze, and mutation detection are implemented.
No final cases have been invented inside this repository; status remains
`awaiting_independent_cases` until a third party supplies and a separate reviewer
checks 12-16 opaque cases.

```bash
python3 -m superturiya.external_v2 status
python3 -m superturiya.external_v2 validate  # after independent cases arrive
```

The complete v2 path is executable as separate `sut-freeze`, `author-packet`,
`validate`, `freeze`, `predict`, `score`, and `evidence-manifest` stages. Raw
predictions are persisted before private labels can be opened by scoring.

See [external-v2 protocol](benchmark/external_v2/protocol.md) and the
[reviewer instructions](benchmark/external_v2/reviewer_instructions.md).

For submission delivery, use the [100-second judge script](docs/hackathon/JUDGE_DEMO_SCRIPT.md) and [submission checklist](docs/hackathon/SUBMISSION_CHECKLIST.md).

## What is engineered

```text
frozen case
  → deterministic invariant preflight
  → Investigator Agent (critical step + evidence-backed failure class)
  → Adaptation Agent (one allowlisted typed patch)
  → explicit approval
  → deterministic replay from the same initial state
  → task + invariant + safety-regression verification
  → separate activation review
  → active procedural policy with audit provenance
```

The agent does not grade itself. The deterministic verifier is the authority. Unknown operations fail closed, candidates cannot replay, approval does not imply activation, and an intervention cannot become durable learning without a verified safe replay.

## Benchmark contract

- One deterministic enterprise resource-provisioning workload.
- 3 development cases and 12 held-out cases.
- Six failure classes: stale memory, missing evidence, invalid tool argument, tool-output misinterpretation, missing approval, and orchestration/order error.
- Cases and frozen inputs: `benchmark/cases.json`.
- Hidden evaluation labels: `benchmark/labels.json`; excluded from agent-visible case input.
- Fixed denominator: all 12 eligible, initially failing held-out cases.
- Same fixtures, verifier, replay semantics, and approval event for baseline and final systems.

## API

Hackathon workflow:

- `GET /hackathon/state`
- `POST /hackathon/evaluate`
- `POST /hackathon/cases/prepare`
- `POST /hackathon/interventions/review`
- `POST /hackathon/interventions/activate`
- `POST /policies/review`

The pre-existing trajectory-intelligence substrate remains available:

- `POST /observations`
- `POST /memories/extract`
- `POST /memories/search`
- `POST /graphs/upsert`
- `POST /traces/start`
- `POST /traces/step`
- `POST /trajectories/score`
- `POST /trajectories/counterfactuals`
- `POST /trajectories/quantum-interpret`
- `POST /policies/synthesise`
- `DELETE /subjects/{id}?tenant_id=demo`

## Repository map

- `superturiya/adaptive.py`: benchmark loading, hidden agent view, workload, verifier, agents, typed interventions, replay, and metrics.
- `superturiya/hackathon.py`: validation, baseline, evaluation, demo, and evidence-bundle CLI.
- `superturiya/store.py`: SQLite provenance ledger for interventions, replay results, evaluations, policies, and audit.
- `superturiya/intelligence.py`: governed application service plus the original trace/memory/graph intelligence loop.
- `superturiya/api.py`: standard-library HTTP and static-app server.
- `web/`: single judge-facing before/after workbench plus `/legacy.html` for the preserved original v1 console.
- `benchmark/`: frozen cases and separate ground-truth labels.
- `benchmark/external_v2/`: independent-case schemas, private-gold boundary, reviewer protocol, and freeze manifest.
- `tests/`: original v1 regression plus adaptive benchmark and governance tests.
- `docs/hackathon/`: compressed spec-driven-development package, prior-art statement, changelog, and reproduction guide.

## Prior art and differentiation

AgentRx is credited for trajectory IR, invariant checking, auditable evidence, localization, and failure classification. DoVer is credited for targeted intervention, re-execution, and recovery measurement. SuperTuriya does not claim those operations individually as novel.

The product contribution is their governed lifecycle in one local control plane: provenance-grounded diagnosis, strict typed repair, human review, deterministic regression-gated replay, and promotion into reusable procedural intelligence only after a verified safe recovery.

See [PREEXISTING.md](docs/hackathon/PREEXISTING.md) for the frozen pre-hackathon boundary and [FEATURE_SPEC.md](docs/hackathon/FEATURE_SPEC.md) for the accepted scope and contracts.

## Scientific positioning

The original v1 also contains a quantum-inspired interpretation layer. It is classical and deterministic and is not on the default hackathon path. Density-matrix language is used only as an explainable metaphor for uncertainty over competing trajectory interpretations. SuperTuriya does not claim quantum computing, physical quantum cognition, or agent consciousness.

## License

SuperTuriya is available under the [MIT License](LICENSE).
