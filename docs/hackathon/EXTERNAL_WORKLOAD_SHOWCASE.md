# External Workload Showcase Contract

Status: optional interoperability evidence; excluded from the primary benchmark.

## Decision

A sanitized trace exported by a separately built, multi-agent workflow is useful
because it can demonstrate that SuperTuriya is not coupled to the competition's
resource-provisioning simulator. The external workload should contain realistic
tool calls, retrieved evidence, policy gates, approval states, escalation,
memory recall, and human handoff.

It must not replace the primary governed learning story or the independently
authored external benchmark. Its only claim is interoperability.

Required label:

> External Workload Showcase - excluded from the primary benchmark.

## Thin adapter boundary

The adapter may consume one sanitized exported run or a list of canonical trace
spans. It must not import or start the source application.

| Exported field | SuperTuriya canonical field |
| --- | --- |
| `run_id` | `run_id` and source provenance |
| `step_id` | `step_id` |
| `parent_step_id` | parent/provenance reference |
| `agent_name` | `source` |
| `input_summary` / `output_summary` | safe step summary |
| safe `decision_summary` | optional structured decision summary |
| `tools_used` | tool references |
| `evidence_ids` | `evidence_refs` |
| `latency_ms` | latency metadata |
| `tokens_in` / `tokens_out` | usage metadata |
| `model_name` | model metadata |
| `confidence` | confidence metadata |
| `risk_flags` | risk metadata |
| `approval_state` | governance metadata |
| `timestamp` | event timestamp |

The adapter must preserve original IDs, reject private-reasoning markers and
credential-like material, tolerate missing optional fields, and never mutate
the source fixture.

## Evidence contract

The exported fixture must record:

- immutable source commit or content-addressed snapshot;
- export timestamp and source run ID;
- synthetic-data and sanitization statements;
- applicable code and data rights;
- adapter version and output hash;
- explicit exclusion from the primary benchmark.

## Claim boundaries

Allowed:

- SuperTuriya can ingest a sanitized trace from a separately built multi-agent
  system.
- The adapter preserves tool, evidence, risk, approval, usage, and provenance
  fields.
- SuperTuriya can produce its structured decision record over the imported
  trajectory.

Not allowed:

- The showcase proves independent benchmark superiority.
- A code license automatically grants rights to an external knowledge corpus.
- The fixture represents production customers, production connectors, or
  verified production outcomes unless separately proven.
- SuperTuriya exposes private chain-of-thought or weakens source policy.

## Go/no-go gates

Implement the adapter only after:

1. the independent external benchmark protocol is frozen;
2. the owner supplies one permitted, synthetic exported run;
3. the source state is committed or content-addressed;
4. the export passes sanitization and contains no raw private documents;
5. the showcase remains optional for judge reproduction.
