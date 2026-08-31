# Judge Demo Script (100 seconds)

## 0–15s — Problem and hot take

“Agent debugging tools can explain a failure, but explanation is not improvement. SuperTuriya is a local control plane that allows durable learning only when one bounded repair survives replay, preserves invariants, introduces no safety regression, and receives explicit approval.”

Keep the hero and CAVRR card visible. Credit AgentRx for localization/invariant reasoning and DoVer for intervention/re-execution; position SuperTuriya as the governed promotion lifecycle.

## 15–30s — Measured improvement

Point to the fixed held-out result: direct raw-trace baseline 3/12 (25.00%) versus SuperTuriya 11/12 (91.67%), an absolute gain of 66.67 percentage points, with 0.00% safety regression. State that all 12 initially failing cases remain in the denominator.

## 30–70s — Successful governed repair

1. Select `eval-006` and click **Investigate case**.
2. Show the highlighted critical step, decisive quantity invariant, evidence reference, and typed `tool_argument.constraint` patch.
3. Emphasize that the patch is still `candidate` and has not executed.
4. Click **Approve & replay from frozen state**. Show all invariants passing and “Verified safe recovery.”
5. Emphasize that approval still did not create learning.
6. Click **Activate procedural learning**. Show the active policy ID and audit-backed promotion.

## 70–88s — Verifier authority / honest failure

Select `eval-012 · difficult`, investigate, and approve replay. The one bounded ordering repair leaves the independent missing-evidence failure unresolved. The verifier rejects recovery and keeps activation disabled. Say: “Agent confidence cannot overrule deterministic evidence.”

## 88–100s — Reproducibility close

Show `make evaluate` and `make test`, or the committed `evidence/` directory. Close with: “FROZEN reproduces the submitted outputs, replay, verification, and scores without credentials; it does not pretend to reproduce model inference.”

Do not lead with the quantum-inspired v1 layer. Do not claim autonomous self-modification, production deployment, or novelty for localization/replay themselves.
