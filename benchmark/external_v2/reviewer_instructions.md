# Independent Author and Reviewer Instructions

## What the author receives

- the visible-case and private-gold schemas;
- the versioned failure-class taxonomy;
- this instruction file;
- the typed-operation allowlist;
- a description of CAVRR and the deterministic replay requirement.

The author must not receive model prompts, frozen outputs, rule mappings, or
case-specific suggestions from the SuperTuriya implementer.

## Authoring requirements

- Create 12-16 opaque IDs (`v2-001`, `v2-002`, ...).
- Cover at least three frozen cloud-operations scenario families. Do not label
  the result as cross-domain external validity.
- Include at least three difficult or multi-causal trajectories.
- Make each trajectory understandable from its visible evidence alone.
- Specify one or more defensible critical steps and acceptable bounded repairs
  privately; do not leak them into the visible file or ID.
- Use synthetic data and sandboxed side effects only.
- Do not add credentials, personal data, copyrighted private corpora, or
  private chain-of-thought.
- Preserve the canonical simulator fields defined by `case.schema.json` while
  changing scenario language, trajectory structure, tool evidence, and failure
  combinations. The validator rejects files that cannot be executed.
- Give every private label a unique `V2_GOLD_CANARY_*` value.
- Return visible case files and private labels separately. Do not place private
  labels in the model-runtime package.

## Reviewer checklist

- [ ] Author and reviewer are different people.
- [ ] No case supplies an eligibility field; all accepted initially failing
  cases enter the denominator mechanically.
- [ ] IDs and file names reveal no class or expected answer.
- [ ] Visible trajectories contain no gold fields or canaries.
- [ ] Gold critical steps exist in the corresponding trajectory.
- [ ] Expected and acceptable repairs use allowlisted typed operations.
- [ ] Difficult-case assignments are justified before results; eligibility is
  derived mechanically and is not author-controlled.
- [ ] All cases are initially failing under the frozen verifier contract.
- [ ] The package validates before it is frozen.
- [ ] Every private operation/target resolves to a real mutable surface in its
  corresponding visible case.
- [ ] The model-projection audit reports no verifier-only or private fields.
- [ ] The author/reviewer identities and freeze hashes are recorded.

Freeze command:

```bash
python3 -m superturiya.external_v2 freeze \
  --author-id '<independent-author>' \
  --reviewer-id '<independent-reviewer>'
```
