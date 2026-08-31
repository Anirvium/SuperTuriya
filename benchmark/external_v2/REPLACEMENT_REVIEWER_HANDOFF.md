# External-v2 Replacement Reviewer Handoff

## Role

You are the replacement independent semantic reviewer for a 16-case,
AI-authored blinded/adversarial benchmark. Person A authored the original
benchmark from a sanitized packet. A prior proposed reviewer was rejected; no
approval from that reviewer is being relied upon.

You are not being asked to run SuperTuriya, predict model behavior, optimize
cases, score a model, or approve a competition claim. Review only the supplied
benchmark semantics against the frozen protocol, schemas, taxonomy, and typed
operation language.

## Independence boundary

You must be different from Person A. Perform the review without SuperTuriya
system prompts, previous benchmark outputs, v1 evidence, v2 predictions, or
performance results. Do not request those materials.

The original files required 37 purely mechanical private-gold `target_id`
normalizations after import. Read `MECHANICAL_CORRECTIONS.md` and explicitly
state whether those substitutions preserve the authored repair intent. No
visible case or semantic label was changed during that normalization.

## Required case-by-case adjudication

For each `v2-001` through `v2-016`, record pass/fail and a short reason for:

1. the visible trajectory is understandable and initially represents a real
   failure within the frozen cloud-operations simulator;
2. the frozen failure class naturally describes the failure rather than being
   forced by the taxonomy;
3. every gold critical step is defensible under the protocol's earliest-
   consequential-divergence definition;
4. the decisive invariant matches the selected failure class;
5. expected and acceptable repair surfaces preserve the author's described
   intent and are semantically appropriate, not merely schema-valid;
6. difficult and multi-causal designations are justified;
7. the case does not contain an answer hint, identity leakage, private data,
   credential, or unsafe real-world side effect.

Pay special attention to multi-causal cases. A single bounded repair need not
repair an unrelated second cause, but the adjudication and acceptable critical
steps must make that limitation explicit.

## Required return

Return:

- reviewer identity or stable reviewer ID;
- confirmation that the reviewer is different from Person A;
- one row per case with `PASS`, `CORRECTION REQUIRED`, or `REJECT`;
- explicit acceptance or rejection of the documented mechanical target-ID
  normalizations;
- all proposed corrections without editing the supplied files silently;
- one final verdict: `APPROVED FOR FREEZE` or `NOT APPROVED FOR FREEZE`.

Approval is permission to freeze only. It does not authorize prediction,
private scoring, prompt changes, repair-mapping changes, or any model/provider
call.
