# Focused Semantic Re-review: v2-008

## Scope

Review only the Person-A re-adjudication of `v2-008`. Do not run SuperTuriya,
inspect model outputs, calculate performance, or modify the supplied files.

The previous semantic review accepted the visible case, initial failure,
failure class, decisive invariant, difficulty designation, repair surfaces,
and visible/private boundary. It rejected only the second critical-step label.

Person A subsequently re-adjudicated that label:

- old `gold_critical_steps`: `["v2-008-s2", "v2-008-s5"]`;
- new `gold_critical_steps`: `["v2-008-s2", "v2-008-s4"]`.

Reason: `v2-008-s4` is the earliest visible point where the workflow
explicitly fails to attach `CAT-008` to the terminal record; `v2-008-s5` is
the downstream terminal manifestation.

## Required checks

Confirm that:

1. `v2-008-s2` remains the earliest critical step for premature fulfillment;
2. `v2-008-s4` is the earliest defensible critical step for the independent
   evidence-retention failure under the frozen protocol definition;
3. the change preserves the accepted failure class, decisive invariant,
   repair intent, difficult-case semantics, and visible/private boundary;
4. the documented Person-A change is the only semantic field change.

## Required return

Return:

- a stable reviewer ID;
- confirmation that the reviewer is different from Person A;
- `v2-008`: `PASS`, `CORRECTION REQUIRED`, or `REJECT` with a short reason;
- explicit acceptance or rejection of the Person-A critical-step correction;
- final verdict: `APPROVED FOR FREEZE` or `NOT APPROVED FOR FREEZE`.

Approval authorizes benchmark freeze only. It does not authorize prediction,
scoring, model/provider execution, prompt changes, or SUT changes.
