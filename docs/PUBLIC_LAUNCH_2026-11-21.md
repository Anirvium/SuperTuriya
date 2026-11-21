# SuperTuriya public launch — 21 November 2026

The public website and synthetic playground are ready for sharing. The reference
operator remains an early local product, not a validated production platform.

## Published surfaces

- Website: https://superturiya.piyushunt.chatgpt.site
- Playground: https://superturiya.piyushunt.chatgpt.site/demo/
- Guide: https://superturiya.piyushunt.chatgpt.site/docs/
- Social preview: https://superturiya.piyushunt.chatgpt.site/assets/social-preview.png

The public surface is buildless HTML, CSS, SVG and JavaScript, with no operator
API exposed. The twelve synthetic evidence records are exported from the Python
engine. Browser decisions are tab-local and do not change server policy. The
conversation form prepares a public GitHub issue for the visitor to review and
submit; it does not silently collect leads or send messages.

Release source: https://github.com/Anirvium/SuperTuriya/tree/launch/cosmic-workbench-2026-11-21

The public website source has its own Sites repository and hosting manifest.
The snapshot in this branch is inspectable source; ongoing Sites publication
must use the selected Site repository through the Sites workflow.

## Product experience

Blue and white surfaces, indigo navigation, an orbital visual, responsive
layouts, reduced-motion support, keyboard-accessible tabs, and explicit focus
management. The public and local workspaces share assets. Their runtime modes
are visibly distinguished.

The workbench supports all twelve cases, diagnosis, typed-patch inspection,
replay approval, checks, a separate activation-review dialog, revocation,
evidence export, repair-surface comparisons, and a session decision record.
The Python mode persists the existing server audit records and policies.

## Authority changes

- Authenticated servers require a fixed tenant and principal.
- Record references and caller-selected upsert identifiers are checked before
  reads/mutations; nested observation inputs are included.
- Reviewer identity is supplied by the authenticated server context, not the
  request's reviewer name.
- The generic policy-review endpoint cannot activate policies. Activation must
  use the governed intervention route.
- Activation requires actual human replay approval, a verified safe replay, and
  an unchanged approved intervention hash. Benchmark-simulated approvals do not
  qualify.
- Store-level policy activation also requires matching verified replay
  provenance and policy content.
- Active policies can be revoked; revocation is audited and removes them from
  active policy retrieval. This is local policy disabling, not rollback of an
  external production deployment.
- API mutations are serialized around ownership verification and handling in
  the single SQLite workspace, preventing concurrent duplicate transitions at
  the HTTP boundary.
- Non-loopback serving requires scoped bearer authentication. Authenticated
  requests are limited to 120/minute per client address. Sockets time out after
  15 seconds; the existing body/media limits and security headers remain.
- Unexpected browser origins are rejected. API-triggered live inference is
  disabled unless the operator explicitly sets `SUPERTURIYA_ALLOW_LIVE_API=1`.
- The browser token stays in tab memory and is not placed in URLs or browser
  persistent storage.

These are concrete improvements, not an assertion of complete tenant isolation,
enterprise authorization, or security certification. In-process Python/store
access remains a trusted boundary. A private HTTPS deployment needs explicit
trusted-origin configuration and infrastructure review.

## Verification

- 87 Python tests passed, including nine new launch governance tests.
- Primary benchmark validation, External-v2 frozen-data validation, and frozen
  system-under-test source hashes passed.
- Browser flows verified for all 12 recorded cases: 11 permit separate activation
  after passing replay; eval-012 stays blocked.
- Browser checks verified Python investigation, candidate comparison, replay,
  activation and revocation, plus the correctly blocked case.
- Desktop 1440px and mobile 390px layouts checked, with no horizontal overflow
  on the homepage, playground and guide.
- No uncaught JavaScript exceptions in the tested flows.
- All internal page/asset destinations, public evidence digest, and shared asset
  synchronization passed the static check.
- Public homepage, playground, guide, JSON evidence bundle and social image
  returned HTTP 200 without authentication.

The static host does not apply the supplied `_headers` file. Each HTML page
therefore also declares a restrictive content policy through a supported meta
tag. The Python operator server supplies its own HTTP security headers.

## Reproduction and maintenance

```bash
python3 -m unittest discover -s tests -q
make validate
make v2-verify
make v2-sut-verify
PYTHONPATH=. python3 scripts/check_public_site.py
```

To update the synthetic bundle, run `PYTHONPATH=. python3
scripts/export_public_demo.py`. It captures new export identifiers/timestamps;
expected case outcomes and verifier semantics stay fixed. The bundle includes
its own content digest and excludes prompt text. Run
`python3 scripts/sync_public_ui.py` after shared asset changes.

`scripts/visual_qa.cjs` uses an isolated installed headless Chrome profile on
macOS, a static preview on 8787 and a temporary Python server on 8766.
`scripts/deployed_qa.cjs` checks the public deployment and final local port 8765.
These scripts use synthetic state and require local network/process access.

## Remaining production milestones

- One real agent-framework integration and reproducible imported customer-like
  traces, with explicit permission and redaction.
- Snapshot fidelity and external side-effect isolation beyond the simulator.
- Multi-user authentication, roles, authorization lifecycle and security review.
- Policy versioning, deployment rollback, idempotent durable jobs, concurrency
  stress tests, monitoring, and tested backup/restore/retention behavior.
- Fresh development and independently evaluated holdout data for the newer
  repair selector; measured engineering-time value in a design-partner pilot.

The old frozen result remains 3/12 versus 11/12. External-v2 remains 8/16 versus
8/16. No new model-performance or production-safety claim is introduced.
