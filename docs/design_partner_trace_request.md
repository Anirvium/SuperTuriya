# SuperTuriya Design Partner Trace Request Template

Status: ready-to-send template for early design partners.

Purpose: collect sanitized agent traces that help validate SuperTuriya's trajectory intelligence, memory-aware provenance, state scoring, and policy/memory writeback workflow.

## 1. Short Email Template

Subject: Request for sanitized agent traces for SuperTuriya design partner analysis

Hi [Name],

Thank you for exploring SuperTuriya with us.

We are validating a trajectory intelligence layer for state-aware AI agents. The goal is to help teams understand why agent runs succeed, fail, recover, or become fragile by connecting traces, memory, retrieval, tool calls, graph provenance, evaluation, and policy/memory writeback.

Could you share a small sanitized trace package from your agent system?

Ideal package:

- 10-30 failed or fragile runs
- 5-10 successful runs
- framework used
- current debugging workflow
- human root-cause labels where available
- any before/after examples where you changed prompts, tools, memory, retrieval, or policies

Please do not include secrets, credentials, raw customer PII, PHI, payment data, private keys, access tokens, or confidential customer names. Stable aliases are perfect.

In return, we will produce a trajectory intelligence report showing repeated failure patterns, memory/retrieval/tool-state issues, function-experience gaps, and candidate policy or memory improvements.

Best,
[Founder Name]

## 2. What To Send

Minimum useful package:

- 5 failed traces
- 5 successful traces
- one short description of your agent workflow
- one short description of your current debugging process

Strong package:

- 20-100 sanitized traces
- failed, successful, recovered, and ambiguous runs
- human labels for known root causes
- examples of memory/retrieval/tool events
- cost, latency, token usage if available
- expected outcome or task rubric
- before/after traces after an attempted fix

## 3. Required Trace Fields

Use `docs/canonical_trace_schema_v0_1.md` when possible.

Required:

- `trace_id`
- `tenant_id`
- `subject_id`
- `agent_id`
- `goal`
- `started_at`
- `status`
- ordered `steps`

Required per step:

- `step_id`
- `step_index`
- `kind`
- `source`
- `status`

Strongly recommended:

- step input and output
- model metadata
- tool calls
- retrieval events
- memory events
- policy events
- errors
- latency
- token usage
- cost
- human evaluation
- root-cause labels

## 4. Failed Run Request

For failed or fragile runs, please include:

- final failure state
- error message or failure observation
- tool that failed, if any
- whether the agent recovered
- whether the final answer looked correct but was not trustworthy
- whether stale or missing memory contributed
- whether retrieval was missing, irrelevant, or contradictory
- whether the issue was policy/safety/compliance related
- human root-cause label

Suggested labels:

- `missing_evidence`
- `weak_memory_routing`
- `stale_memory`
- `memory_conflict`
- `tool_failure`
- `tool_selection_error`
- `retrieval_context_gap`
- `unsupported_assumption`
- `weak_planning`
- `policy_violation`
- `ambiguous_user_intent`
- `good_reasoning_bad_execution`
- `completed_but_fragile`

## 5. Successful Run Request

For successful runs, please include:

- why the run was considered successful
- whether the agent used memory
- whether the agent used retrieval
- whether tool calls were necessary
- whether a human reviewed the output
- whether this run should become a reusable strategy

SuperTuriya needs successful runs because the product learns stable patterns, not only failures.

## 6. Framework And System Context

Please answer:

- Which framework do you use? LangGraph, OpenAI Agents SDK, CrewAI, AutoGen, custom, or other?
- Which model providers and models are used?
- Do you use vector search, graph search, SQL, web search, tools, code execution, or browser automation?
- Do you use long-term memory?
- How are memory writes approved or rejected today?
- How are policy/guardrail changes managed today?
- What observability tools do you already use?

## 7. Current Debugging Workflow

Please describe:

- how a failed run is noticed
- who reviews it
- what logs/traces are inspected
- how root cause is decided
- how fixes are made
- how you verify the fix
- where debugging feels slow or unclear

This helps SuperTuriya compare its workflow to your current baseline.

## 8. Sanitization Rules

Remove or replace:

- names
- emails
- phone numbers
- addresses
- account IDs
- customer names
- API keys
- access tokens
- passwords
- private keys
- session cookies
- production URLs if sensitive
- proprietary document text if not approved

Use stable aliases:

```text
customer_001
user_001
repo_001
ticket_001
document_001
tool_001
```

Do not send:

- raw secrets
- PHI
- payment data
- private keys
- access tokens
- regulated personal data unless a legal agreement exists

## 9. Preferred Package Structure

```text
partner_trace_package/
  README.md
  system_context.md
  debugging_workflow.md
  traces/
    failed/
      trace_001.json
      trace_002.json
    successful/
      trace_101.json
    before_after/
      before_trace_201.json
      after_trace_201.json
  labels/
    root_cause_labels.csv
  notes/
    reviewer_notes.md
```

## 10. Human Label CSV

Recommended columns:

```csv
trace_id,success,human_score,primary_root_cause,secondary_root_cause,recovery_observed,should_write_policy,should_write_memory,notes
```

Example:

```csv
trace_001,false,0.32,stale_memory,retrieval_context_gap,true,true,true,"Agent trusted old migration note before checking current docs."
```

## 11. Analysis We Will Return

SuperTuriya will return:

- utility score
- grounding score
- memory relevance score
- recovery score
- ambiguity score
- experience coherence
- function-experience gap
- root-cause hypotheses
- state-transition graph summary
- recurring failure patterns
- candidate memory updates
- candidate policy updates
- before/after improvement opportunities

## 12. Permission And Case Study

Please choose one:

```text
[ ] Internal analysis only. Do not use our traces or results externally.
[ ] You may use anonymized aggregate findings in fundraising conversations.
[ ] You may use anonymized screenshots after our written approval.
[ ] You may use our company name as a design partner after written approval.
[ ] We are open to a public case study after successful validation.
```

Retention preference:

```text
[ ] Delete after analysis.
[ ] Retain for 30 days.
[ ] Retain for 90 days.
[ ] Retain until the pilot ends.
```

Design partner contact:

```text
Company:
Technical contact:
Security/legal contact:
Preferred deletion contact:
Preferred communication channel:
```
