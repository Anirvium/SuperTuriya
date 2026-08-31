# SuperTuriya Final Video and Presentation Guide

Use this guide with `output/presentation/superturiya_hackathon_final.pptx`.
The deck contains eight slides and matching speaker notes. The target recording
length is **4 minutes 50 seconds**, leaving ten seconds of safety below the
five-minute limit.

## The one sentence judges should remember

> SuperTuriya turns a failed agent trajectory into one evidence-backed repair,
> proves it through frozen replay, and lets a human decide whether verified
> learning becomes durable policy.

## Recording setup

Before recording:

1. Start the local product with `python3 -m superturiya --seed --port 8765`.
2. Open `http://127.0.0.1:8765` and confirm `eval-006` and `eval-012` load.
3. Open the presentation in full-screen presenter mode.
4. Keep one browser tab for the product and one terminal window ready, but do
   not expose an API key, environment variables, private messages, or unrelated
   browser tabs.
5. Record at 1080p, use a quiet microphone, disable notifications, and enlarge
   the browser to at least 125% if text is difficult to read.
6. Perform one untimed rehearsal, then one timed rehearsal. Aim for 4:40-4:50.

## Final run of show and exact narration

### 0:00-0:22 — Slide 1: the hot take

Show slide 1.

> An agent can propose a repair. It cannot decide that it has learned. Teams can
> already inspect failed agent runs, but a plausible model suggestion should not
> silently become memory, routing, or policy. SuperTuriya creates that missing
> authority boundary: the model proposes, deterministic code verifies, and a
> human governs.

### 0:22-0:50 — Slide 2: user, problem, and value

Show slide 2.

> The intended users are platform and reliability teams operating stateful,
> tool-using agents. Their bottleneck is not a lack of logs. It is converting a
> failure into a safe, reusable improvement. Without a controlled writeback
> loop, the agent either repeats the failure or learns the wrong lesson. Our
> demonstration uses simulated enterprise resource provisioning so
> consequential actions remain sandboxed.

### 0:50-1:15 — Slide 3: purposeful agent architecture

Show slide 3.

> SuperTuriya gives five components bounded roles. The trajectory is frozen.
> Investigator localizes the earliest consequential step. Adaptation proposes
> one allowlisted typed repair. A deterministic verifier replays from the same
> state. The human approves replay and separately activates policy. The agents
> cannot execute tools, grade themselves, approve themselves, or activate
> learning.

### 1:15-2:28 — Slide 4 and live product: successful governed repair

Briefly show slide 4, then switch to the product UI and select `eval-006`.

> Here the user requested quantity two, but the fulfilment tool received
> negative two. I click Investigate. SuperTuriya identifies step s3, the
> positive-integer invariant, and the supporting catalog evidence. Adaptation
> proposes one typed operation: constrain `fulfill.quantity` to the requested
> positive integer.

Point at the intervention status before approval.

> This is still only a candidate. It has not executed and cannot activate
> itself.

Click **Approve and replay from frozen state**. Point at the before/after result.

> After my approval, replay begins from the identical frozen state. All seven
> invariants pass and no safety regression appears. Approval still did not create
> learning.

Click **Activate procedural learning** and point at the policy ID/audit result.

> I make a second human decision to activate the verified repair. The result is
> an auditable procedural policy rather than an invisible prompt mutation.

### 2:28-2:58 — Slide 5 and live product: difficult rejection

Show slide 5, then select `eval-012` in the UI and replay its proposed repair.

> A trustworthy system must also refuse incomplete learning. This difficult
> case has two causes. The ordering repair correctly moves catalog lookup before
> fulfilment, but the final action still omits catalog evidence. Replay therefore
> fails an invariant and policy activation remains blocked. Agent confidence
> cannot overrule evidence.

### 2:58-3:28 — Slide 6: improvement changelog

Show slide 6.

> We began with a direct raw-trajectory baseline that recovered three of twelve
> controlled development cases. Structured diagnosis helped, but the decisive
> change was separating proposal from authority through typed repair, approval,
> frozen replay, verification, and activation. The controlled result reached
> eleven of twelve with zero safety regression. We also removed an internally
> authored transfer benchmark from the final validation claim because it knew
> our repair vocabulary and produced no live recovery lift.

### 3:28-4:25 — Slide 7: honest final evaluation

Show slide 7. Pause briefly on the equal recovery bars.

> For the final evidence gate, we froze the system first and used sixteen
> blinded and adversarial cases across four cloud-operations scenario families.
> They were authored by an AI Person A from a sanitized packet and reviewed
> before execution; we do not call them independently human-authored.
>
> Across three trials, the direct baseline and SuperTuriya both recovered eight
> of sixteen, so measured recovery lift was zero. We preserved that result and
> did not tune after freeze. SuperTuriya localized accepted critical steps at one
> hundred percent and decisive invariants at eighty-one point two five percent,
> with zero safety regression. Exact repair-surface accuracy was forty-one point
> six seven percent. That is the next engineering bottleneck.

### 4:25-4:50 — Slide 8: reproducibility and close

Show slide 8.

> Judges can reproduce the credential-free product from the public repository.
> A clean clone passes all fifty-eight tests, and all sixteen frozen cases verify
> with valid hashes. Provider inference is optional and is not disguised as
> deterministic reproduction. Our practical insight is simple: reliable agent
> learning is an authority-design problem, not only a prompting problem. The
> model proposes. Code verifies. A human governs.

Stop recording here. Do not add a long thank-you screen.

## What to show on screen

The final video should contain these visible proofs:

- the intended user and bottleneck;
- the five bounded roles;
- one complete `eval-006` execution from failure to activated policy;
- the rejected `eval-012` replay;
- the improvement changelog, including the removed experiment;
- the External-v2 zero-lift result and diagnostic metrics;
- the clean-clone test and frozen-hash counts.

Do not spend recording time scrolling through source code. The repository is the
reproducibility artifact; the video should make the product and evidence easy to
understand.

## Claim boundaries

Safe, exact claims:

- Controlled development evidence: baseline `3/12` versus SuperTuriya `11/12`.
- Final External-v2 evidence: baseline `8/16` versus SuperTuriya `8/16`.
- External-v2 critical-step localization: `100.00%`.
- External-v2 decisive-invariant accuracy: `81.25%`.
- External-v2 mean repair-surface accuracy: `41.67%`.
- External-v2 safety regression: `0.00%`.
- External-v2 cases were AI-authored, blinded/adversarial, separately reviewed,
  and frozen before model execution.
- The final scope is four cloud-operations scenario families, not unrelated
  multi-domain validation.
- The public, credential-free path reproduces deterministic behavior, evidence,
  tests, and hashes; it does not reproduce provider inference.

Do not claim:

- that 91.67% is the final external-validation score;
- independently human-authored External-v2 cases;
- production deployment or production traffic;
- broad cross-domain generalization;
- autonomous self-modification;
- that the reasoning model verifies, approves, or activates its own repair;
- consciousness, quantum computing, or physical quantum cognition;
- sponsorship or endorsement by a model or inference provider.

## Recommended submission copy

### Project title

**SuperTuriya — Governed Learning for Stateful AI Agents**

### One-line description

SuperTuriya turns failed agent trajectories into evidence-backed, typed repairs
that must survive frozen replay, deterministic verification, and explicit human
approval before becoming durable policy.

### Short description

Stateful, tool-using agents can fail because of memory, evidence, tool arguments,
approvals, interpretation, or execution order. SuperTuriya freezes the failed
trajectory, uses bounded Investigator and Adaptation agents to diagnose it and
propose one typed repair, then replays the candidate through a deterministic
verifier. A human approves replay and separately controls policy activation.
The repository includes a credential-free local demo, 58 automated tests,
complete trajectories, reproducible evidence, an improvement changelog, and a
frozen blinded/adversarial evaluation that honestly preserves a zero-lift result
and identifies repair-surface selection as the next bottleneck.

### Hot take

**A model suggestion is not agent learning until independent verification and a
human authority accept it.**

## Final upload checklist

- [ ] Video duration is no longer than five minutes.
- [ ] Audio is clear and the UI text is readable at normal playback size.
- [ ] No API key, terminal secret, private notification, or unrelated tab appears.
- [ ] `eval-006` reaches verified activation.
- [ ] `eval-012` remains rejected.
- [ ] Development and External-v2 metrics are presented separately.
- [ ] The removed experiment is mentioned.
- [ ] The public repository link opens in a signed-out browser.
- [ ] The video link opens without requesting access.
- [ ] HackerEarth title, description, repository, and video fields match this guide.
- [ ] Watch the uploaded video once from beginning to end before submitting.
