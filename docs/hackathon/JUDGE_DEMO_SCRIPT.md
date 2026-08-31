# Judge Video Script (4 minutes 45 seconds)

## 0:00-0:30 - User, problem, and hot take

Show the workbench hero.

“Teams operating stateful, tool-using agents can inspect failures, but a diagnosis
does not safely become durable learning. SuperTuriya is a local reliability and
governance control plane. It localizes the earliest consequential failure,
proposes one bounded repair, replays from frozen state, rejects regressions, and
promotes a procedural policy only after explicit human approval.”

“Our hot take: a model suggestion is not agent learning until independent
verification and human governance accept it.”

## 0:30-0:55 - Baseline and controlled development result

Show the metric card and case list.

“The direct raw-trajectory baseline and SuperTuriya use the same 12 initially
failing cases, approval event, fixtures, replay, verifier, and denominator. The
controlled development result is 3/12 versus 11/12 verified safe recoveries,
25.00% versus 91.67% CAVRR, with zero safety regression. This is synthetic
development evidence, not a production-accuracy claim.”

## 0:55-2:25 - One complete governed repair

Select `eval-006`.

1. Show the failed trajectory: the request asks for quantity `2`, but
   `fulfill.simulate` receives `-2`.
2. Click **Investigate case**. Show the critical step, decisive positive-integer
   invariant, evidence reference, and confidence.
3. Show the Adaptation output: one allowlisted
   `tool_argument.constraint` targeting `fulfill.quantity`.
4. Emphasize that the candidate has not executed and cannot activate itself.
5. Click **Approve & replay from frozen state**. Show the single configuration
   change, successful tool sequence, all seven invariants passing, and zero new
   safety failures.
6. Explain that approval still did not create learning.
7. Click **Activate procedural learning** and show the policy ID and audit trail.

“The Investigator and Adaptation agents propose structured judgments. They do
not execute tools, grade the replay, approve themselves, or activate policy. The
deterministic verifier and human reviewer hold that authority.”

## 2:25-2:55 - Honest difficult failure

Select `eval-012`, investigate, approve, and replay.

“This case has two independent causes. The bounded ordering repair fixes catalog
sequencing but leaves final evidence unresolved. The verifier rejects recovery
and activation remains blocked. Agent confidence cannot overrule evidence.”

## 2:55-3:35 - Improvement changelog and biggest contribution

Show `IMPROVEMENT_CHANGELOG.md`.

Briefly walk through direct baseline, structured diagnosis, typed repair,
approval-gated replay, shadow transfer, and blinded External-v2 evaluation.

“The most important change was separating proposal from authority: a repair must
survive frozen replay, every invariant, safety-regression checks, and a separate
human activation decision. That turned a plausible model answer into auditable
procedural learning.”

## 3:35-3:55 - Removed experiment

Show the changelog’s “Removed from final validation claim” row.

“We initially considered the internally authored structural-transfer v1
benchmark as final evidence. Its same-model live run produced zero recovery lift,
and the cases were authored with knowledge of our repair vocabulary. We removed
it from the final validation claim and built the blinded External-v2 protocol
instead.”

## 3:55-4:30 - External-v2 and honest final comparison

Show `external_v2_final_report.md` and the scored evidence artifact.

“We then froze the SUT and evaluated 16 blinded/adversarial cases authored by an
AI Person A from a sanitized packet and separately reviewed before model
execution. We do not call them independently human-authored. The primary model
hit free-tier capacity before a complete artifact existed, so before observing
fallback output we preregistered a separate same-model Qwen experiment.”

“Across three trials, both the direct baseline and SuperTuriya recovered 8/16:
50.00% versus 50.00%, with zero safety regression. SuperTuriya achieved 100%
critical-step localization and 81.25% decisive-invariant accuracy, but repair
surface selection was only 41.67%. We preserved the zero-lift result and did not
tune after freeze.”

## 4:30-4:45 - Reproducibility close

Show the terminal and repository.

```bash
make evaluate
make test
make v2-verify
make v2-sut-verify
```

“A clean public clone passes 58 tests. The credential-free path reproduces the
demo, replay, verification, scores, hashes, and committed evidence. Provider
inference is optional and is not disguised as deterministic reproduction.”

Do not claim production deployment, broad cross-domain validity, autonomous
self-modification, or novelty for localization and replay individually.
