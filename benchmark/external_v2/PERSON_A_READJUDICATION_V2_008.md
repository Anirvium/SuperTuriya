# Person-A Re-adjudication: v2-008

Date: 30 August 2026

Source: Person A re-adjudication after the independent semantic review finding
for `v2-008`.

Authorized private-gold correction:

- case: `v2-008`;
- field: `gold_critical_steps`;
- old: `["v2-008-s2", "v2-008-s5"]`;
- new: `["v2-008-s2", "v2-008-s4"]`.

Reason: `v2-008-s4` is the earliest visible point where the workflow
explicitly fails to attach `CAT-008` to the terminal record. `v2-008-s5` is
the downstream terminal manifestation.

No other field in `gold_private/v2-008.json` was changed. No visible case,
other private-gold file, failure class, decisive invariant, difficulty flag,
expected repair surface, acceptable repair, canary, schema, verifier, prompt,
repair mapping, or SUT source was changed.

This re-adjudication requires focused independent semantic re-review before
benchmark freeze. It does not authorize freeze, prediction, scoring, or model
execution.

## Hash provenance

- pre-correction `gold_private/v2-008.json` SHA-256:
  `4fc4e119c4cf2c4fb50ba0b563925d7bfe1322f94386a445a137785b5162d5f1`;
- corrected `gold_private/v2-008.json` SHA-256:
  `4342216c9e2fd08f858c271acacb851d362c9a884d40ad2693c5a03f04c20ffb`;
- unchanged `cases/v2-008.json` SHA-256:
  `647493775d5758d354bdac8d865b7cc66ba38ceac40223d1fc022f297a82f1c5`;
- current visible-case aggregate SHA-256:
  `65355b5037671874294d488d5b4238a3695b140c2f3b73afdb50af4ea9cfa513`;
- current private-gold aggregate SHA-256:
  `2522231b0a680600b689648d08bed596c894d2ad68960013d05ac6d1666d9204`;
- current ordered 32-file content aggregate SHA-256:
  `f15a2edd5be82604a288ab0034e4eb5de803a16742096561189889c4e3d277f3`.

The earlier full replacement-review packet SHA-256
`0a919deba2b6dc0a153ef75146a74e3fbb119cd04c8f78e3a4ea411767fd469d`
contains the pre-re-adjudication `v2-008` gold and is superseded. It must not be
used for freeze approval.
