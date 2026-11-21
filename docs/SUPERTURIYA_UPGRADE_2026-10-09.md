# SuperTuriya upgrade — 9 October 2026

This upgrade is a post-External-v2 layer. It does not rewrite the frozen v2
benchmark, raw predictions, private labels, scored evidence, or the three
source files covered by the v2 system-under-test manifest.

## Implemented capabilities

### Replay-guided repair selection

`POST /hackathon/repair-guided` maps the Investigator's decisive invariant to
only repair surfaces with declared causal effects, runs ephemeral frozen
replays, recommends a verified one-patch recovery, and abstains when no such
repair exists. A recommendation remains a candidate and still requires human
approval.

`POST /hackathon/repair-oracle` reports the declared one-patch ceiling. On the
committed primary held-out benchmark the ceiling is 11/12; the multi-causal
case remains unrecoverable by design.

### Governed memory exposure

`POST /memories/search` now requires subject scope and evaluates each ranked
memory across scope, policy, and lifecycle axes. Decisions are `yes`, `no`, or
`unresolved`. Only `yes` memories enter returned prompt context; all decisions
are recorded in the audit ledger with candidate, retrieved, exposed, withheld,
and admissible-but-not-exposed identifiers.

Memory metadata includes owner, namespace, allowed purposes, authorization
state/reference, policy version, lifecycle state, and validity window.

### Dual evidence records and hostile-display controls

`POST /evidence/records` preserves an append-only raw JSON record and produces
a separately hashed plain-text display projection. Hidden Unicode direction
and zero-width controls are made visible in the projection.

- `GET /evidence/records/{record_id}` returns only the projection and integrity
  result.
- `GET /evidence/records/{record_id}/raw` returns the separately downloadable
  raw record.

The HTTP boundary now adds a restrictive CSP, no-sniff, no-referrer,
permissions, frame, cache, and opener policies; removes wildcard CORS; rejects
unsupported media types and oversized bodies; and supports bearer-bound tenant
and principal scope.

Set production-local authentication through environment variables:

```bash
export SUPERTURIYA_API_TOKEN='replace-with-a-secret'
export SUPERTURIYA_API_PRINCIPAL='operator-id'
export SUPERTURIYA_API_TENANT='tenant-id'
export SUPERTURIYA_ALLOWED_ORIGINS='https://trusted.example'
python3 -m superturiya --host 127.0.0.1 --port 8765
```

### Evaluation integrity cards

`POST /integrity/cards` stores separately evidenced `O`, `P`, `C`, or `?`
states for training-time exposure, evaluation-time retrieval, and scaffold
leakage. Susceptibility, confirmed incidents, and score impact remain separate;
there is intentionally no aggregate cleanliness score.

### Evidence-grounded behavior graph

`POST /oversight/graph` creates a deterministic sidecar graph over a stored
trace. It contains evidence units, demand/action/response behaviors, typed
edges, task scope, and consequential-decision review questions. Every unit
retains a hash and raw trace reference; the original trace is never replaced.

### Blinded External-v2 adjudication

Create 16 case packets covering all 96 arm-by-trial outcomes:

```bash
make v2-adjudication-packet \
  RAW=evidence/external_validity/v2/raw_live_comparison_qwen_fallback.json \
  OUTPUT=output/v2-adjudication-review.json \
  KEY_OUTPUT=output/v2-adjudication-private-key.json
```

The review artifact contains no arm, trial, automatic verdict, or private gold.
The private key supports later unblinding, automatic-versus-human confusion
matrices, corrected completion rates, two independent reviewers, and a third
reviewer for disagreements.

## Validation commands

```bash
python3 -m unittest discover -s tests -v
make v2-verify
make v2-sut-verify
```

The new mechanisms establish engineering capability. They do not constitute a
new external performance claim until a preregistered, independently scored
post-v2 evaluation is completed.
