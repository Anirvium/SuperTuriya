# Trace workspace and deployment upgrade — 21 November 2026

This upgrade adds a path from an explicitly recorded Python workflow to a saved,
inspectable trace. It does not turn imported logs into an executable replay or
establish a new agent-quality result.

## Delivered

- Local **Your traces** workspace with file preview, reviewed save, persistent
  history, search, span hierarchy references, recorded status and evidence checks.
- A dependency-free Python recorder for explicitly supplied spans, inputs and
  outputs, nested relationships, timestamps and exception types.
- Versioned native trace schema, 500-span/900 KB limits, timing validation,
  duplicate/cycle checks, fresh server identifiers and tenant-bound imports.
- Best-effort credential masking before storage, inert hostile-text rendering,
  immutable imported snapshots and atomic import/audit transactions.
- Tenant-scoped audit viewer and integrity-checked evidence export.
- SQLite online backup, digest manifest verification, restore to a fresh path,
  and refusal to overwrite existing backup/restore destinations.
- Non-root Docker/Compose deployment definitions with explicit authentication,
  persistent data, loopback publishing, and operational instructions.
- Portable static website export with optional custom-origin rewriting, leaving
  the current live site untouched while an owned domain is selected.

## Executed verification

- 100 Python tests passed, including 13 additional trace-workspace and operations
  tests beyond the earlier 87-test release.
- Browser checks passed at 1440px desktop and 390px mobile widths, with no
  horizontal overflow or uncaught JavaScript exceptions in the tested flows.
- File-format preview, reviewed import, persistence across reloads, duplicate
  detection, saved-run search, audit viewing and operator navigation passed.
- Hostile HTML stayed inert and a synthetic authorization value did not appear
  in the rendered saved trace.
- Tests cover malformed imports, acyclic hierarchy validation, atomic rollback,
  concurrent duplicate requests, tenant isolation, server-bound actor identity,
  immutable writes, tamper detection, subject erasure and restart persistence.
- Backup/restore preserved an imported trace's verified integrity. Existing
  destinations and mismatched backup digests were rejected.
- The public-site static check and portable ZIP origin-rewriting check passed.
- Primary benchmark validation, External-v2 frozen artifact validation and frozen
  system-under-test hash verification passed without changing frozen evidence.

Browser artifacts are generated under `output/workspace-upgrade`. The ready
static website archive is `output/superturiya-website-portable.zip`.

## Boundaries and remaining work

Docker was not installed in the development environment. The container image
build, startup, volume ownership and restart smoke test remain unexecuted.

The new recorder can wrap a real Python workflow, but this upgrade used
illustrative local execution and synthetic browser/security fixtures. It did not
run a customer pilot or independently evaluate recovery on new traces.

Next production gates are an executable real-agent replay adapter, faithful
initial-state capture, explicit external-side-effect isolation, task verifiers,
multi-user identity/roles, independent security review, deployment rollback,
monitoring and a fresh independent evaluation. The current operator remains one
bound tenant/principal per authenticated server.

The public marketing site remains on its current host. A purchased domain still
needs DNS and HTTPS configuration on the chosen host. No domain was purchased or
changed by this upgrade.

See [the trace guide](TRACE_WORKSPACE.md) and
[deployment and domain instructions](DEPLOYMENT.md).
