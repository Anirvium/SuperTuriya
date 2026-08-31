# SuperTuriya Hackathon Evaluation - Research Source

> Historical research record. Its readiness findings were accurate at the time
> of review but are superseded by the final External-v2 report and current
> repository state.

Date: 29 August 2026
Purpose: canonical research and evidence record supporting `summary.md`
Audience: founder, engineering reviewer, hackathon judge
Status: evidence-backed internal report; not submission copy

## 1. Research question

Evaluate SuperTuriya as if judging it for the micro1 Frontier Engineering Challenge 2026. Determine:

- the exact competition contract and deliverables;
- what comparable AI-agent hackathons reward;
- what winning products at large cohorts look like;
- how the current product compares with adjacent agent-evaluation platforms;
- whether the repository's claims reproduce;
- what prevents the project from being a winning submission;
- the shortest defensible path to a stronger score.

The request to research "every" similar hackathon cannot be satisfied literally because there is no complete public registry, private competitions are not indexed, and many events do not publish judging or winner details. The comparison set therefore uses public, first-party sources selected for relevance: agentic workflows, agent reliability, objective agent evaluation, end-to-end AI products, and competitions of similar or greater participation scale.

## 2. Method

### Source hierarchy

1. The supplied official micro1 challenge brief.
2. The [official HackerEarth event page](https://www.hackerearth.com/community/challenges/hackathon/micro1-frontier-engineering-challenge-2026/).
3. First-party organizer rules and winner showcases from Microsoft, Google Cloud, and Devpost-hosted competitions.
4. First-party product documentation for the adjacent agent-evaluation category.
5. The local repository, Git history, executable tests, benchmark artifacts, and generated evidence.
6. Clearly labeled inference where no direct source exists.

Secondary event listings, social posts, and community commentary were used for discovery only when they conflicted on prizes, dates, or ownership. Conflicting claims were excluded from the conclusions unless confirmed by a primary source.

### Repository checks performed

- Read the README, feature specification, pre-existing disclosure, changelog, reproduction guide, evidence report, submission checklist, and demo script.
- Inspected Git history, tracked files, uncommitted changes, package metadata, core runtime, evaluator, tests, API, and evidence bundle.
- Executed benchmark validation, frozen baseline/final evaluation, shadow transfer, and all unit tests.
- Copied the current worktree to a temporary clean environment with no project virtual environment or API credentials and reran evaluation and tests.
- Scanned for common committed credential patterns.
- Compared declared evidence with what is actually tracked by Git.

### Important interpretation rule

The report separates four different claims:

- **Mechanism claim:** the governed diagnosis-replay-promotion loop works on the supplied deterministic fixtures.
- **Benchmark claim:** it recovers 11 of 12 curated held-out failures versus 3 of 12 for the supplied frozen baseline.
- **Agent claim:** LIVE mode can call an OpenAI-compatible model, but no submitted LIVE evaluation establishes its reliability.
- **Product claim:** no production deployment, design-partner use, or broad generalization is currently established.

Only the first two are directly demonstrated.

## 3. Official micro1 competition contract

The event page reports an online, individual competition running from 28 August through 31 August 2026, with 7.5K registrations at the time of review. This makes it a highly competitive event even though registration count is not submission count. See the [official HackerEarth listing](https://www.hackerearth.com/community/challenges/hackathon/micro1-frontier-engineering-challenge-2026/).

The supplied official brief has SHA-256:

`be811a1d09ebedef2fc853544132b287924fd0f76d04301ea554b4c7e2d88fc4`

It defines this 100-point rubric:

| Official criterion | Points | Judge's essential question |
|---|---:|---|
| Problem & User Value | 15 | Is a clear user experiencing a meaningful bottleneck? |
| Agent Solution & Engineering | 30 | Are agent capabilities purposeful and technically sound? |
| End-to-End Quality | 20 | Is the execution realistic, self-contained, and professionally finished? |
| Measured Improvement | 15 | Is improvement demonstrated against a fair baseline and explained through a changelog? |
| Reproducibility | 15 | Can another person reproduce the main result from a clean environment? |
| Hot Take / Insights | 5 | Did a failure mode produce a practical lesson for reliable agent building? |
| Total | 100 | |

The brief recommends one user-centered primary metric, the same cases for baseline and final, complete results, at least ten cases when practical, and at least one challenging case.

The four required deliverables are:

1. Complete solution code plus an improvement changelog.
2. A clean-environment reproduction guide with exact commands, versions, expected output, runtime, and cost.
3. A solution video of up to five minutes showing the problem, baseline, one end-to-end run, comparison, changelog, biggest positive change, and one removed experiment.
4. Representative trajectories for every agent, including instructions, tool responses, feedback, retries, and human checkpoints.

Ground rules material to SuperTuriya include:

- disclose what existed before the competition and what was added;
- use all components under valid licenses and terms;
- sandbox consequential actions and require human approval;
- use a qualified human reviewer for decisions that may significantly affect someone;
- use legal, ethical, shareable information;
- exclude credentials and private information;
- connect every result claim to submitted evidence;
- provide judges enough access to reproduce the result.

## 4. Comparable event set

This set is representative rather than literally exhaustive.

| Event/cohort | Public reach | What its official source emphasizes | Relevance to SuperTuriya |
|---|---:|---|---|
| micro1 Frontier Engineering Challenge 2026 | 7.5K registrations | User value, purposeful agents, finished execution, fair improvement, reproduction, insight | Direct judging contract |
| Microsoft AI Agents Hackathon 2025 | 18K+ registrations; 570 submissions | Innovation, impact, usability, solution quality, category fit | Large agent cohort and winner patterns |
| Google Cloud ADK Hackathon 2025 | 10,400 participants; 62 countries; 477 projects; 1,500+ agents | Orchestrated multi-agent systems solving complete domain workflows | Large agent cohort and end-to-end ambition |
| Gemini Live Agent Challenge 2026 | 11,878 participants; 1,536 projects; 151 countries | Technical precision, novel interaction, multimodal operation | Current large-scale agent competition |
| BigQuery AI Hackathon 2025/announced 2026 | 5,350 entrants; 277 submissions | Real business problems, technical excellence, impact | Similar competitive scale |
| DataHub Agent Hackathon 2026 | Current rules, no winner cohort at review time | Meaningful platform use, robustness, originality, real usefulness, submission quality | Strong enterprise-agent rubric |
| UiPath AgentHack 2026 | Current rules, no winner cohort at review time | Business adoption, platform depth, production readiness, exceptions/handoffs/failures, complete delivery | Enterprise/governed agent comparison |
| AI Forecasting Hackathon 2026 | 115 participants listed | Objective benchmark, completion-adjusted scoring, public repository, anti-leakage/fair-play restrictions | Evaluation-integrity comparison |
| hack-use Computer-Use Agents Hackathon | 14 participants listed | Novelty 30%, real-world value 30%, technical depth 20%, demo 20% | Compact agent rubric |
| 100 Agents Hackathon 2025 | Public remote cohort | Equal weights for completeness, presentation, creativity, business viability | Product-readiness comparison |

Primary sources:

- [Microsoft AI Agents Hackathon 2025 winner showcase](https://techcommunity.microsoft.com/blog/azuredevcommunityblog/ai-agents-hackathon-2025-%E2%80%93-category-winners-showcase/4415088)
- [Google Cloud ADK Hackathon winners](https://cloud.google.com/blog/products/ai-machine-learning/adk-hackathon-results-winners-and-highlights?hl=en)
- [Gemini Live Agent Challenge winners](https://cloud.google.com/blog/topics/developers-practitioners/winners-and-highlights-of-the-gemini-live-agent-challenge)
- [BigQuery AI Hackathon winners](https://cloud.google.com/blog/topics/developers-practitioners/bigquery-ai-hackathon-celebrating-innovation-and-a-look-at-whats-new)
- [DataHub Agent Hackathon rules](https://datahub.devpost.com/rules)
- [UiPath AgentHack rules](https://uipath-agenthack.devpost.com/rules)
- [AI Forecasting Hackathon rules](https://prophethacks.devpost.com/rules)
- [hack-use rules](https://hack-use.devpost.com/rules)
- [100 Agents Hackathon rules](https://100agents.devpost.com/rules)

### Cohort-history limitation

No prior public cohort of the micro1 Frontier Engineering Challenge was discoverable from the official event source during this review. Public announcements describe this as the first global micro1 hackathon, but those announcements are not a reliable historical dataset. The evaluation therefore does not invent prior micro1 winners or use nonexistent cohort statistics.

## 5. What winning agent products repeatedly have in common

The following are synthesis, not organizer quotations.

### A. One concrete user and operational job

Large-cohort winners are typically domain systems, not broad slogans. Microsoft selected RiskWise, an end-to-end supply-chain risk analysis system. Google ADK selected SalesShortcut, an SDR workflow spanning research, proposals, and outreach. Other Google winners addressed energy operations, education, cloud sustainability, and validated physics workflows.

Implication: “trajectory intelligence for every agent” is too broad for the judging story. SuperTuriya should lead with one incident-resolution workflow for an agent-platform engineer.

### B. Visible end-to-end execution

Winning demos show an input, tool-using workflow, exception or evidence path, and useful final output. Architecture alone rarely establishes value. DataHub and UiPath rules explicitly reward robustness, actual end-to-end operation, production realism, and complete delivery.

Implication: the before/after UI is useful, but the demo must show where a failed trace comes from and what a platform engineer receives after activation.

### C. Technical choices tied to failure modes

Events reward deliberate state, tools, memory, verification, or orchestration—not component count. SuperTuriya's best engineering story is the separation of probabilistic diagnosis from deterministic authority, plus typed and human-governed promotion.

### D. Reproducibility and evidence are score multipliers

The micro1 brief gives reproducibility 15 points. DataHub asks for working access and sample outputs. Objective-evaluation competitions go further: the AI Forecasting Hackathon requires public code, completion-aware scoring, a post-build evaluation window, and bans evaluation leakage or harness manipulation.

Implication: hashes and complete artifacts are strong, but they must exist in the exact public commit the judge receives.

### E. Demo quality can decide close rankings

Several comparable rubrics devote 20-30% to demo/presentation or use demo quality as a tie-breaker. A missing video is not a small documentation defect; for micro1 it is a missing required deliverable.

### F. Product reach is demonstrated, not asserted

Winning entries show believable users, workflow data, integrations, or adoption pathways. SuperTuriya currently has no documented external user, production trace, hosted deployment, usage count, or design-partner result. Its current reach is a local proof of mechanism.

## 6. Adjacent product landscape

The category is not empty. Current first-party documentation shows:

- [LangSmith](https://docs.langchain.com/langsmith/evaluation-concepts) supports traces, datasets, offline/online evaluations, deterministic and model-based evaluators, human annotation queues, experiments, and trajectory evaluation.
- [Braintrust](https://www.braintrust.dev/docs/evaluate/run-evaluations) supports immutable experiment snapshots, comparable evaluations, local runs, and detailed traces.
- [Arize Phoenix](https://arize.com/docs/phoenix/) supports open-source observability, tracing, datasets, experiments, prompt iteration, and deterministic or model-based evaluation.

Therefore, “we trace and evaluate agents” is not differentiated. The defensible wedge is narrower:

> SuperTuriya converts a failed tool-using trajectory into one typed repair, replays it from frozen state, rejects unresolved or regressed cases, and allows durable policy activation only after explicit human approval.

This wedge is credible in the prototype. It is not yet proved as a general integration layer across agent frameworks.

## 7. Repository facts verified on 29 August 2026

### Git and delivery state

- `HEAD`: `bbe7fb9cc55d028796628ee4db0710767e4e70f6` - benchmark and hidden-label freeze.
- Pre-hackathon base commit: `f91b449506717a6cae7c1392746303a3d198529c` dated 15 July 2026.
- Current worktree: 8 modified tracked paths and 14 untracked top-level paths/groups.
- Only `benchmark/cases.json` and `benchmark/labels.json` from the hackathon build are present in `HEAD`.
- The adaptive runtime, evaluation CLI, hackathon docs, evidence, new tests, Makefile, and legacy UI assets are not tracked at `HEAD`.
- No repository license file is present.

This means the current local product runs, but no Git commit contains the product as evaluated. A judge cloning `HEAD` cannot reproduce the submitted claims.

### Runtime and evidence

- Python requirement: 3.9 or newer.
- Mandatory runtime dependencies: none.
- 20 unit tests pass.
- Benchmark validation passes for 3 development and 12 held-out cases.
- 56 evidence files exist locally; 55 are JSON.
- Frozen baseline: 3/12 verified safe recoveries, 25.00% CAVRR.
- Frozen final: 11/12, 91.67% CAVRR.
- Absolute difference: 8 recoveries and 66.67 percentage points.
- Safety regression rate: 0/12.
- One separate five-step shadow case verifies transfer of the quantity policy; it is correctly excluded from CAVRR.
- A clean temporary copy of the current worktree reproduced the aggregate metrics and 20 passing tests without credentials.

### What FROZEN actually means

In FROZEN mode, the baseline, Investigator, and Adaptation outputs are deterministic local logic recorded as submitted evidence. Model inference is not rerun. The Investigator maps failed invariants to one of six classes and selects a step by kind. Adaptation maps the class to a fixed typed repair surface. This is transparent and reproducible, but it is not evidence of model reasoning ability.

LIVE mode implements an OpenAI-compatible chat-completions request, but:

- no LIVE benchmark result is submitted;
- no test covers the external request/response path;
- provider token usage is not carried into the reported usage fields;
- no retry, output-repair, or rate-limit behavior is demonstrated;
- no claim of LIVE reproducibility is justified.

### Benchmark integrity

Strengths:

- cases and labels are separate and hashed;
- runtime code does not read `labels.json`;
- the denominator includes all 12 initially failing held-out cases;
- baseline and final share fixtures, replay, verifier, and approval semantics;
- the unresolved multi-causal case remains failed;
- case-level results are emitted.

Limitations:

- cases, labels, deterministic reasoning rules, and repair mappings were co-developed before the recorded freeze;
- all primary trajectories contain four summarized steps;
- there are only two held-out cases per class;
- the baseline is a deliberately small frozen heuristic, not a demonstrated general-purpose agent;
- the final frozen path has direct access to deterministic invariant failures;
- 100% localization and classification occur on the taxonomy the system itself encodes;
- no independent or production-derived test set exists;
- a single curated shadow case does not establish transfer.

The 91.67% number is valid for this fixture contract. It must not be presented as production accuracy, cross-domain recovery, or broad agent reliability.

## 8. Claim-evidence-gap matrix

| Claim | Supporting evidence | Confidence | Gap |
|---|---|---|---|
| The governed mechanism works locally | UI flow, replay records, store/API lifecycle, 30 tests | High | No production integration |
| An unapproved patch cannot replay | Negative tests and runtime validation | High | Only local simulator |
| A failed replay cannot activate learning | `eval-012`, tests, UI state | High | Only encoded invariants |
| Final beats baseline on the benchmark | Complete 12-case reports; same replay/verifier | High for this benchmark | Baseline and benchmark are co-designed |
| Labels are mechanically isolated at runtime | Separate file/module, guarded-open test | High | Co-development before freeze remains |
| The result reproduces without credentials | Clean worktree snapshot rerun | High for FROZEN | No committed final revision yet |
| Investigator and Adaptation are agents | LIVE code path exists; frozen trajectories use agent-shaped interfaces | Medium-low | Submitted path is deterministic, no LIVE evidence |
| Policies transfer to new failures | One shadow case | Low | One curated case, same repair class |
| Product solves a real enterprise need | Plausible problem and competitive category | Medium-low | No design partner or real trace |
| Product is winner-ready | Strong mechanism and story | Low today | Missing video, license, public final commit, external evidence |

## 9. Strict official-rubric score

| Criterion | Max | Score | Reason |
|---|---:|---:|---|
| Problem & User Value | 15 | 9 | User and bottleneck are clear, but no user discovery, real incident, or value measurement exists. |
| Agent Solution & Engineering | 30 | 21 | Strong typed lifecycle, verifier, provenance, and tests; submitted default is deterministic rule mapping, LIVE is unvalidated, and no real framework adapter exists. |
| End-to-End Quality | 20 | 12 | Local UI demonstrates accepted and rejected paths; workload is synthetic, no arbitrary trace ingestion is shown in the judge flow, and video/public access are missing. |
| Measured Improvement | 15 | 9 | Complete same-case results and an honest failure are good; small co-designed benchmark and weak frozen baseline limit inference. |
| Reproducibility | 15 | 10 | Clean worktree snapshot reproduces with no credentials; the evaluated product is not committed, no license exists, and no clean public-clone proof exists. |
| Hot Take / Insights | 5 | 5 | “Explanation is not improvement; only verified, approved repair becomes memory” is specific and supported. |
| **Total** | **100** | **66** | Competitive prototype, below winner-ready threshold. |

The score is an independent audit, not an official micro1 score. A plausible ceiling after the prioritized fixes is approximately 82-86, depending on the quality of external evaluation and the video.

## 10. Current verdict

### Technical demo readiness

Yes. The local successful and rejected flows work, tests pass, and evidence regenerates.

### Submission readiness

No. Required or practical gates remain open:

- final code/evidence is not in a commit;
- no solution video exists;
- no license has been selected;
- no public repository or judge-access URL is recorded;
- no evaluation has been rerun from the exact final public commit;
- product-value evidence is synthetic only;
- LIVE agent behavior is not validated.

### Winner readiness

Not yet. The engineering thesis is good enough to compete, but the evidence currently proves a curated mechanism rather than a broadly useful agent-reliability product.

## 11. Highest-return optimization order

### P0 - eligibility and judge access

1. Review and commit the complete worktree.
2. Select a compatible repository license and document third-party terms.
3. Push a public submission repository.
4. Run evaluation and tests from a fresh clone of the exact commit; record commit SHA and output.
5. Record a sub-five-minute video meeting every official content requirement.
6. Verify every submitted trajectory and evidence link exists in that commit.
7. Preserve and prominently disclose the pre-hackathon boundary.

### P1 - measured-improvement credibility

1. Freeze a new, independent shadow set before running it.
2. Add varied, longer traces from an actual open-source tool-using agent or independently authored fixtures.
3. Run the same model in LIVE mode for baseline and final, with repeated trials and provider usage/cost captured correctly.
4. Add an ablation table that isolates invariant preflight, Investigator, typed Adaptation, deterministic verification, and governance.
5. Add at least one real trace adapter, preferably OpenTelemetry/OpenInference JSON, so judges can see adoption potential.
6. Measure a user outcome such as debugging time, recurrence prevention, or reviewer effort—not only recovery on synthetic cases.

### P2 - product reach and polish

1. Obtain one agent-platform engineer's review of several trace diagnoses.
2. Show export of an approved rule into a real agent configuration or CI gate while keeping execution sandboxed.
3. Add a one-command smoke script and CI workflow.
4. Make the UI explain FROZEN versus LIVE without relying on verbal caveats.
5. Package an example incident report and audit export as user-facing output.

## 12. Recommended claim language

Use:

> On a frozen 12-case synthetic provisioning benchmark, SuperTuriya's structured diagnosis and typed replay pipeline verified safe recovery in 11 cases, compared with 3 for the supplied direct frozen baseline. The benchmark demonstrates the governance mechanism; it does not establish production generalization.

Do not use:

- “91.67% accurate in production.”
- “Autonomously self-improves any agent.”
- “Proven across domains.”
- “The first agent evaluation platform.”
- “Quantum intelligence” as a physical or computational claim.

## 13. Research gaps

- The dynamic HackerEarth page did not expose all rule-tab content to static extraction; the supplied official brief is the authoritative rubric source used here.
- No full public list of all similar hackathons exists.
- No prior official micro1 cohort dataset was found.
- Registration totals do not equal submissions or judged entries.
- No external repository URL, deployment, video, analytics, user interview, or design-partner trace was available to evaluate.
- No LIVE model credentials or provider were supplied; LIVE behavior was reviewed statically only.

These gaps are preserved rather than filled with assumptions.

## 14. Post-report external-validity addendum

After this research report was completed, a separate external-validity layer was added without changing the core architecture or UI.

- A sealed 12-case structural-transfer benchmark covers software release, data access, and incident rollback with five-to-seven-step traces.
- Its internally authored status and lack of third-party blindness are embedded in the freeze manifest.
- Runtime predictions execute in a cases-only subprocess before evaluator gold is loaded.
- Unique canaries, file-open guards, static source checks, and byte/content hashes enforce mechanical isolation.
- Frozen result: 2/12 direct baseline versus 9/12 verified SuperTuriya recovery, with all three multi-causal cases rejected.
- Ablation result: preflight alone 0/12; structured task completion without the full verifier 11/12; full verified and governed result 9/12.
- The same-model LIVE runner is implemented and contract-tested against a local compatible server, including provider usage capture and mixed-model rejection.
- A real-provider LIVE experiment remains blocked because endpoint, key, and model configuration are absent.
- The full suite now contains 30 passing tests.

The provisional rubric estimate rises from 66 to 71. This is not treated as third-party validation or production generalization.
