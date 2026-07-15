# SuperTuriya Security Baseline

Status: minimum security baseline for POC, demo, and design partner conversations.

Important: this document is a product security plan, not a compliance certification. SuperTuriya should not claim SOC 2, HIPAA, GDPR, or enterprise compliance readiness until formal controls, legal review, and audits exist.

## 1. Security Goals

SuperTuriya will ingest sensitive agent traces. A trace may include user content, prompts, retrieved documents, tool arguments, tool outputs, source code, API responses, customer identifiers, errors, costs, and model metadata.

The baseline goals:

- prevent secrets from entering storage
- redact personal data where possible
- isolate tenants/workspaces
- keep audit trails for sensitive actions
- support deletion and export
- make design partner data handling explicit
- avoid public write access in hosted demos

## 2. Data Classification

Classify incoming data before storage:

| Class | Examples | Handling |
| --- | --- | --- |
| Public | demo traces, synthetic traces, docs | Safe to show in demos. |
| Internal | product logs, test traces, founder notes | Keep inside workspace. |
| Partner confidential | sanitized design partner traces, failed runs, successful runs | Store per tenant, restrict access, do not share externally. |
| Restricted | API keys, tokens, passwords, private keys, raw customer PII, PHI, payment data | Do not store unless specifically approved and protected. |

Default rule:

> Design partners should send sanitized traces only. SuperTuriya should not request production secrets, raw credentials, PHI, payment data, or unnecessary PII.

## 3. PII Redaction

Before traces are stored or used in demos:

- redact emails
- redact phone numbers
- redact access tokens and API keys
- redact passwords
- redact private keys
- redact session cookies
- redact customer names when not required
- hash or pseudonymize `user_id`
- replace real IDs with stable aliases such as `user_001`, `account_001`, `repo_001`

Recommended redaction markers:

```text
[REDACTED_EMAIL]
[REDACTED_PHONE]
[REDACTED_SECRET]
[REDACTED_TOKEN]
[REDACTED_PRIVATE_KEY]
[REDACTED_CUSTOMER]
```

Importer requirement:

- reject traces containing high-confidence secrets
- warn on possible PII
- keep a redaction summary in import results

## 4. API Key Handling

For hosted staging:

- require API keys for ingestion endpoints
- map each key to one tenant/workspace
- store only hashed API keys
- show key prefix only, never full key after creation
- support key rotation
- support key revocation
- separate demo keys from design partner keys

Never:

- commit API keys to the repository
- store keys in frontend code
- include keys in screenshots or demo videos
- log full authorization headers

Recommended environment variables:

```text
SUPERTURIYA_ENV=staging
SUPERTURIYA_DATABASE_URL=...
SUPERTURIYA_API_KEY_HASH=...
SUPERTURIYA_ADMIN_PASSWORD_HASH=...
```

## 5. Secret Masking

Mask secrets in:

- request logs
- import errors
- stack traces
- tool arguments
- tool results
- frontend payload previews
- exported reports

Minimum secret patterns:

- `sk-...` style model keys
- GitHub tokens
- bearer tokens
- JWTs
- AWS access keys
- private key blocks
- OAuth client secrets
- database URLs with credentials

## 6. Tenant Isolation

Current POC:

- `tenant_id` and `subject_id` are logical scopes
- no full authentication exists yet

Before design partner hosting:

- require authenticated workspace access
- restrict every read/write/delete by tenant/workspace
- map API keys to one tenant
- prevent tenant ID override from client payloads when authenticated
- include tenant ID in audit logs
- test cross-tenant access denial

Acceptance criterion:

> A design partner cannot read, modify, export, or delete another design partner's traces.

## 7. Deletion Guarantees

Minimum deletion behavior:

- delete observations by subject
- delete memories by subject
- delete graph nodes and edges by subject
- delete traces and steps by subject
- delete scores and reports by subject
- write an audit event for deletion

For hosted product:

- document deletion SLA
- include backup deletion window
- support workspace-level export before deletion
- provide deletion confirmation with timestamp and actor

POC wording:

> SuperTuriya supports subject-scoped erasure in the local control plane. Hosted deletion guarantees will require backup, retention, and audit implementation before production launch.

## 8. Retention Policy

Recommended defaults:

| Data | Default retention |
| --- | --- |
| Synthetic demo traces | Indefinite |
| Local POC traces | User-controlled |
| Design partner sanitized traces | 90 days unless extended in writing |
| Import logs | 30 days |
| Security audit logs | 1 year for hosted staging |
| Deleted subject backups | Remove from active system immediately, purge from backups within documented window |

Every design partner should know:

- what data is collected
- how long it is stored
- who can access it
- how deletion works
- whether data may be used in demos or case studies

## 9. Audit Trail Behavior

Audit events should be recorded for:

- trace import
- failed import
- trajectory scoring
- report generation
- policy candidate creation
- policy accept/reject/defer
- memory write/update/delete
- API key creation/revocation
- subject deletion
- export
- login/admin access for hosted product

Minimum audit fields:

- `audit_event_id`
- `tenant_id`
- `actor_id`
- `action`
- `resource_type`
- `resource_id`
- `timestamp`
- `result`: `success` or `failure`
- `metadata`

## 10. Design Partner Trace Handling

Before accepting real traces:

- send the design partner trace request template
- require sanitized payloads
- confirm no secrets or regulated data are included
- assign a tenant/workspace
- agree on retention duration
- agree on whether outputs can be used anonymously in fundraising or case studies
- define a deletion contact

Do not:

- accept raw production logs without review
- mix partner traces into public demo data
- publish screenshots containing partner content
- train external models on partner traces without written permission

## 11. Demo And Staging Minimums

Minimum before external demo:

- admin gate or private URL
- seeded synthetic demo data
- no public write endpoint
- no real secrets in seed data
- clear local-vs-hosted disclaimer

Minimum before design partner staging:

- HTTPS
- API ingestion key
- workspace isolation
- structured logs with secret masking
- subject deletion endpoint
- backup plan
- retention note
- security contact email

## 12. Incident Response

Minimum incident process:

1. Stop new imports if data exposure is suspected.
2. Identify affected tenant, traces, and time window.
3. Preserve audit logs.
4. Rotate affected API keys.
5. Delete exposed data if requested.
6. Notify affected partner with facts, impact, and mitigation.
7. Add regression tests or controls.

Founder note:

> In early-stage mode, speed matters, but trust compounds. Treat every trace as if it contains sensitive operational memory.
