# SuperTuriya: ARC Prize 2026 assessment and execution plan

Research date: 16 September 2026. This document records the pre-implementation audit and experimental strategy. The isolated solver and Kaggle pipeline were implemented afterward; see [current status](../STATUS.md). It remains a research plan rather than evidence of state-of-the-art performance.

Recommendation: ARC-AGI-3 as the primary engineering target, Paper Prize as a paired research submission, and ARC-AGI-2 as a conditional secondary experiment.

**We have a useful evaluation and repair foundation, but no demonstrated ARC capability. The immediate objective is a valid offline submission and evidence that one specific SuperTuriya mechanism improves a strong baseline under the same resource limits.**

## Competition selection

| Track | Deliverable | Fit and recommendation |
|---|---|---|
| ARC-AGI-3 | Autonomous agent for unfamiliar interactive environments | Best fit for trajectory diagnosis and adaptation. Primary investment. |
| ARC-AGI-2 | Exact output grids inferred from example pairs | Requires a new grid solver. Add only after ARC-AGI-3 is stable, or with a separate experienced owner. |
| Paper Prize | Research writeup tied to an actual ARC-AGI-2 or ARC-AGI-3 submission | Enter alongside the primary solver. A credible method and ablations can matter without a winning leaderboard score. |

The official pools are $850,000, $700,000, and $450,000 respectively. The paper rubric covers accuracy, universality, progress, theory, completeness, and novelty. A low score does not automatically make a paper ineligible; it still weakens its accuracy assessment. [ARC-AGI-3](https://arcprize.org/competitions/2026/arc-agi-3), [ARC-AGI-2](https://arcprize.org/competitions/2026/arc-agi-2), [Paper Prize](https://arcprize.org/competitions/2026/paper).

The competition archive also lists 2024, 2025, and the ARC-AGI-3 developer preview. Those are historical references, not additional current entry targets. [Competition archive](https://arcprize.org/competitions).

Registration for a Kaggle account is not acceptance of a particular competition's rules. Check the joined state separately for the solver track and the Paper Track. Participation feasibility is clear at the project level; personal prize eligibility cannot be certified without the entrant's age, residency, affiliations, and accepted track-specific terms. ARC-AGI-2's retrieved rules specify five-person teams, one submission per day, and up to two final selections. Do not assume these quotas apply to the other tracks. [ARC-AGI-2 rules](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/rules).

## Published requirements and unresolved contradictions

| Subject | Findings | Working decision |
|---|---|---|
| Runtime | Kaggle publishes 9 hours for ARC-AGI-3 and 12 hours for ARC-AGI-2, CPU or GPU | Measure model loading, inference, search, and output finalization within one total budget. |
| Hardware | ARC-AGI-3 lists RTX 6000 access; ARC-AGI-2 lists L4×4, 96 GB aggregate GPU memory | Confirm actual allocation and model fit before choosing weights. Aggregate memory is not one contiguous GPU allocation. |
| Network | Evaluation has internet disabled; public external data/models are allowed | Package weights, tokenizer, dependencies, and assets ahead of execution. |
| ARC-AGI-2 output | `submission.json`, two attempts per test input | Validate every task ID and preserve test-input order. |
| ARC-AGI-3 output | Framework generates the submission artifact | Use the official starter/gateway rather than inventing a file contract. |

Sources: [Kaggle ARC-AGI-3 overview](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/overview/upgraded-accelerators), [Kaggle ARC-AGI-2 overview](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/overview).

**Do not silently reconcile these source conflicts:**

- ARC's overview says papers are due November 8; Kaggle's Paper Track says November 9. Set our internal submission date to November 7.
- ARC lists ARC-AGI-3 milestone awards as $25K/$10K/$2.5K; Kaggle lists $25K/$7.5K/$5K. Both total $37.5K per milestone.
- ARC describes first-eligible threshold awards; Kaggle describes distributions among qualifying top teams for the ARC-AGI-3 $700K and ARC-AGI-2 $150K pools. ARC-AGI-2's $275K writeup award is called Grand Prize on the overview and Innovation Prize in its rules.
- ARC's umbrella page requests CC0/MIT-0-style licensing for entrant-authored work; retrieved ARC-AGI-2 rules contain CC BY 4.0 winner-license language. The current repository is MIT, which is not MIT-0. Prepare a dependency/ownership inventory and obtain organizer clarification before deciding the competition release license. Do not assume an MIT repository alone settles eligibility or relicense other contributors' work unilaterally.

Sources: [ARC umbrella requirements](https://arcprize.org/competitions/2026), the three official track pages above, the Kaggle solver overviews/rules above, and [Kaggle Paper Track](https://www.kaggle.com/competitions/arc-prize-2026-paper-track/overview/abstract). No organizer message was sent during this review.

## What the current repository actually provides

Audit basis: current working tree, including pre-existing uncommitted changes; latest commit `938eb33`. Existing files were not modified for this assessment. `python3 -m unittest discover -s tests -q` passed all 58 tests on 16 September. This verifies existing mechanics, not ARC readiness.

| Existing asset | Evidence | Reuse and limitation |
|---|---|---|
| Typed diagnosis and repair | `superturiya/adaptive.py`: InvestigatorAgent, AdaptationAgent, intervention validation | Reuse contracts and evidence references. Provisioning-specific failure classes and patch targets must be replaced for ARC. |
| Replay and verification | DeterministicWorkload, DeterministicVerifier | Reuse testing discipline. These implement a known cloud simulator, not inferred game physics. |
| Provenance and policy lifecycle | `store.py`, `intelligence.py` | Reuse audit records and versioning; adapt policy acceptance to autonomous competition execution. |
| Separated predictions and labels | `external_v2.py`, `external_runtime.py`, benchmark manifests | Strong foundation for held-out evaluation and contamination controls. |
| Resumable experiments | `external_v2_resumable.py` | Reuse atomic checkpoints and call accounting. Development resumption must not imply hidden-game restart privileges. |
| Memory and graph features | `models.py`, `intelligence.py`, `evaluation.py` | Candidate support for compact working memory; no evidence yet that these improve ARC. |
| Policy transfer demo | `transfer.py` | One curated quantity-repair scenario; not general skill induction. |
| Classical uncertainty analysis | `quantum_layer.py` | Heuristic probability/entropy analysis. No quantum computing and no demonstrated ARC advantage. |
| UI, evidence reports, test suite | `web/`, `evidence/`, `tests/` | Useful for inspecting experiments and explaining results. Not the competition's scoring target. |

The final External-v2 report records 8/16 recoveries for both the direct baseline and SuperTuriya, zero recovery lift, 100% critical-step localization, and 41.67% mean repair-surface accuracy. This indicates a repair-selection bottleneck; it does not identify why the micro1 judges rejected the entry. There is no judge feedback in the reviewed material establishing that causal explanation. [Local final report](hackathon/external_v2_final_report.md).

The development 91.67% recovery result is not an ARC score. Frozen-mode outputs are committed reasoning artifacts, not fresh local model inference. The live provider supports an OpenAI-compatible endpoint but the repository does not supply a bundled offline model runtime. A local endpoint could reuse part of that transport contract; external API inference cannot power the Kaggle entry.

At the time of this audit, the repository lacked ARC adapters, grid/game perception, an ARC solver, learned transition models, an autonomous exploration policy, local model packaging, competition scoring integration, and valid ARC submission evidence. The implementation that followed addresses the engineering items under `arc-agi/`; Kaggle execution and score evidence remain external gates. [Starter documentation](https://docs.arcprize.org/arc-prize-2026).

## What recent research changes about the plan

1. **Start with a capable simple baseline.** July's milestone winner, The Duck, used a local Qwen 3.6 27B FP8 model and Python execution. The organizer reports that extra hand-built tools hurt that entry, and another finalist's best profile disabled extra machinery. This is direct reason to demand ablation evidence for our additions. [Milestone analysis](https://arcprize.org/blog/arc-prize-2026-milestone-1).
2. **Treat context preservation as a serious baseline.** PRO-LONG already studies programmatic access to structured interaction history. Logging and retrieval alone are not our novelty. Reproduce an appropriate local-model version before claiming our repair mechanism is the cause of improvement. [PRO-LONG paper](https://arxiv.org/pdf/2607.20064).
3. **Do not claim concept memory as new.** ArcMemo already investigates reusable abstract reasoning memories. Our proposed contribution must isolate when accepting, rejecting, or invalidating a learned rule helps. [ArcMemo](https://arxiv.org/abs/2509.04439).
4. **Program refinement is established prior art.** The 2025 analysis highlights iterative program refinement and test-time adaptation; NVARC won that year's private ARC-AGI-2 evaluation at 24.03%. That is a historical reference, not today's winning threshold. [2025 results](https://arcprize.org/blog/arc-prize-2025-results-analysis).
5. **Architecture names are not evidence.** ARC's HRM analysis attributes important gains to refinement and augmentation rather than the headline hierarchical architecture. Test mechanisms, data, and compute separately. [HRM analysis](https://arcprize.org/blog/hrm-analysis).
6. **The frontier has moved.** ARC's September 3 analysis reports Astra at 62.7% with the Standard harness and 99.9% with a Provider Adapter on semi-private ARC-AGI-3. These are different evaluation conditions from an offline Kaggle entry; they are not a Kaggle prize-winning score we can copy. The useful observation is compact executable world modeling and effective state retention. [September analysis](https://arcprize.org/blog/astra).

The verified benchmark, community leaderboard, and Kaggle leaderboard are distinct comparison settings. ARC's separate verification policy can permit APIs; that does not override the competition's offline restrictions. Current live Kaggle score rows were not obtainable in this session, so no current rank or winning-score forecast is asserted. [Testing policy](https://arcprize.org/policy), [Leaderboard explanation](https://arcprize.org/leaderboard).

## Proposed system: SuperTuriya ARC

Research hypothesis: **counterexample-guided repair of executable world models can reduce wasted actions and increase held-out game scores at fixed compute, beyond a coding agent with equally capable memory.** This is a hypothesis, not an established novelty or performance claim.

The loop is:

`observe → propose rules → predict → act → compare → localize contradiction → repair → test → plan`

Build incrementally:

1. **Observation adapter.** Preserve raw grids, legal actions, frame changes, level state, object candidates, and an append-only action log. Keep multiple representations available; segmentation is a hypothesis and can be wrong.
2. **Local coding baseline.** A locally runnable, license-compatible model can inspect state, write bounded Python helpers, and issue legal actions. Evaluate a strong available quantized model against a smaller faster alternative on actual assigned hardware. Do not select purely by parameter count.
3. **Executable world model.** Represent candidate transitions, object interactions, inferred goals, preconditions, and confidence. Distinguish uncertain observations from inferred rules. Retain contradictory evidence instead of explaining it away.
4. **Targeted repair.** When prediction and observation disagree, localize the mismatch to perception, state tracking, a transition rule, a precondition, or the goal hypothesis. Search a small budgeted set of revisions instead of repeatedly regenerating everything.
5. **Evidence checks.** Run revised rules against recorded transitions and reserved transitions not used to generate the revision. Penalize regressions and unsupported complexity. Passing recorded checks means consistency with evidence, not proof about unseen states.
6. **Exploration and planning.** Prefer actions that distinguish plausible models or advance a supported goal. Use internal search over the inferred simulator when it predicts reliably; switch back to short plans and observation when confidence drops.
7. **Scoped procedural memory.** Store learned rules with their preconditions, supporting transitions, counterexamples, and version. Start with memory inside one environment. Cross-environment persistence is a separate experiment subject to the actual evaluation protocol.
8. **Compute controller.** Allocate model calls and search by uncertainty, progress, time remaining, and observed benefit. Reserve time for the remaining games and output closure. Calls to a large model on every action may consume the run before hard levels are reached.

Important boundary: Competition Mode allows only one creation of each environment, one scorecard, and level resets rather than unrestricted game resets. It withholds inflight scorecards. Our replay runs over recorded data or our own inferred simulator; it must not inspect hidden engine state/source or query free alternative futures from the real game. [Competition Mode](https://docs.arcprize.org/toolkit/competition_mode).

The existing enterprise product's human approvals should remain intact. A separate competition package needs automatic, predefined acceptance checks inside the sandbox. Human review belongs to experiment/release decisions, not individual evaluation moves.

The score rewards action efficiency as well as completion: a completed level at twice the human action count receives a raw squared-ratio score of 0.25. Later levels carry greater weights, with caps applied by the official scorer. Use the official scorer rather than our provisioning recovery metric. Real exploratory actions cost score; internal planning costs wall-clock time. [Scoring methodology](https://docs.arcprize.org/methodology).

## Conditional ARC-AGI-2 extension

If the primary track is stable, adapt the repair engine to Python grid transformations. Propose several programs; execute each on all provided demonstration pairs; identify mismatches; repair; rank by fit, simplicity, and appropriately validated consistency checks; emit two diverse outputs per test input. Fitting examples does not prove generalization. Never let held-out test outputs enter proposal generation.

Compare against a competent reproduced public solver and a no-repair program-synthesis baseline. Add test-time training or an ensemble only if the gain survives the runtime budget. Do not train a new foundation model or build two full solver stacks in parallel as a solo founder. [ARC-AGI guide](https://arcprize.org/guide/1).

## Experimental contract

Freeze a development partition and a separate holdout before tuning. Separate ARC-AGI-3 game families, not just adjacent levels of the same game. A family we inspect during error analysis becomes development data. For ARC-AGI-2, hold out entire tasks. Preserve model/data provenance and distinguish pretraining exposure from genuinely unseen evaluation.

| Experiment | Purpose |
|---|---|
| B0: official random starter | Validate integration only; not the scientific comparison. |
| B1: strong local coding agent | Establish a competitive same-model reference. |
| B2: B1 plus structured searchable memory | Control for context-management gains. |
| B3: B2 plus executable model and planner | Control for world-modeling gains. |
| T1: B3 plus evidence-tested targeted repair | Test the central SuperTuriya contribution. |
| T2: T1 plus adaptive compute | Determine whether the controller improves the score/time tradeoff. |

Use identical model weights, game versions, resource ceilings, and comparable seeds. For a mechanism comparison, equalize model-call/token budgets as well as total time; for an engineering comparison, report score under the same time/hardware cap. Give the baseline additional useful reasoning where necessary rather than letting our method quietly buy more compute.

Report official score, full-game and level completion, all-game action totals, runtime, peak memory, model calls/tokens, invalid actions, resets, timeouts, and pre/post-repair transition accuracy. Keep unfinished games in the denominator. Use at least three local repeated runs for finalists where feasible, paired game-level uncertainty, and explicit small-sample limitations. Individual actions are not independent test samples.

Suggested go/no-go criterion, set before experiments: retain a feature only if paired holdout score improves without exceeding limits, or the feature materially lowers compute while maintaining score. Require gains across more than one game family before calling them general. A positive result on a single public game is a debugging signal.

## Calendar and execution gates

There are 14 calendar days to September 30 and 47 to November 2 from this research date.

| Date | Target and evidence required |
|---|---|
| September 16–18 | Confirm joined tracks and runtime; isolate Python 3.12 environment; freeze source/data versions; run official starter locally and produce first valid Kaggle entry. |
| September 19–22 | Reproduce strong local coding baseline, measure model loading and per-action latency, establish clean evaluation splits and raw logs. |
| September 23–26 | Add only targeted repair and evidence checks; run B1/B2/B3/T1 comparisons; identify whether perception or inference speed is the actual bottleneck. |
| September 27–29 | Freeze the strongest measured variant; complete clean offline rerun; prepare public notebook, dependency notices, and method description. |
| September 30 | ARC-AGI-3 milestone 2. Submit and publish eligible artifacts before the cutoff; do not delay the first valid entry until this date. |
| October 1–11 | Strengthen held-out generalization, simulator repair, and context handling. Drop additions with no measured gain. |
| October 12–18 | Final ablations and a second model if feasible. ARC-AGI-2 extension only with spare capacity and a stable primary submission. |
| October 19–25 | Full offline rehearsals, runtime buffer, failure handling, final team configuration. |
| October 26 | Solver entry/team-merger deadlines published by Kaggle. |
| October 27–30 | Freeze candidate artifacts; finish result tables and select submissions under each track's rules. |
| November 2 | Solver submission deadline. Aim to finish by October 30. |
| November 3–7 | Finalize and submit paper; verify linked public notebook and submission ID. |
| November 8/9 | Conflicting published paper deadlines; use the earlier date as our outer planning bound. |
| December 4 | Announced results date. |

Kaggle's retrieved solver timelines specify 23:59 UTC unless otherwise stated. September 30 then corresponds to October 1 at 05:29 IST; October 26 to October 27 at 05:29 IST; November 2 to November 3 at 05:29 IST. Kaggle's November 9 paper date corresponds to November 10 at 05:29 IST. Do not transfer that time assumption to ARC's conflicting November 8 date without confirmation. Sources: official Kaggle overviews cited above.

Planning assumption while founder constraints are unknown: one full-time builder and access to Kaggle competition GPUs. Suggested effort split is 70% primary solver, 20% evaluation/reproducibility/paper, 10% secondary-track feasibility. With only evenings or no usable GPU allocation, reduce to one solver track plus a focused paper. A CPU starter can prove integration, but is not evidence that a CPU-only entry is competitive.

Before buying compute, measure one end-to-end baseline. Budget using `model loading + sum(game execution) + artifact finalization`, with a proposed 20% runtime buffer. Reserve compute for paired evaluations and final rehearsals before expensive tuning. No paid compute was provisioned in this review.

## Paper and product outcome

Working paper title: “Counterexample-Guided Repair of Executable World Models for Action-Efficient Adaptation.” Novelty needs a deeper related-work comparison; the title is a proposed research direction.

The Kaggle Paper Track requires a submitted Writeup, a cover image, and an attached public notebook; its published Writeup limit is 1,500 words. Record the actual solver submission ID. A saved draft is not submitted. A public PDF can be linked through the project-link mechanism. Plan a concise writeup plus reproducible code and results rather than spending time on presentation polish before measured gains exist. [Paper submission instructions](https://www.kaggle.com/competitions/arc-prize-2026-paper-track/overview/abstract).

The reusable product outcome is an API that accepts observations, predictions, and failures, proposes bounded model revisions, checks them against evidence, and records whether they improve decisions. ARC is the stress test; a subsequent real agent workload must establish product value. Winning the prize cannot be guaranteed. State-of-the-art status requires a comparable verified result, not a proposed architecture.

## Coverage and remaining checks

Reviewed the 2026 umbrella and three track pages, indexed Kaggle overviews, retrievable ARC-AGI-2 rules, relevant SDK/scoring/action/competition documentation, competition archive, research guide, testing policy, July winners, September frontier analysis, 2025 results, HRM analysis, developer-preview material, and primary related-work sources. This is a targeted deep review, not a claim to have read every historical blog, notebook, or discussion.

Direct Kaggle page opens often returned empty content; indexed official Kaggle text supplied several key details. The in-app browser had no available connection. The ARC-AGI-3 and Paper Track complete rule bodies and live leaderboard rows remain unverified. One linked OpenReview paper was blocked by browser verification. Recheck deadlines, publication/license wording, quotas, model restrictions, and current score standings in the signed-in competition interface before the first release. None of these gaps justifies postponing the local baseline.

First concrete milestone: **a reproducible offline ARC-AGI-3 baseline, one valid Kaggle submission, and a frozen experiment comparing it with targeted repair.**
