# SuperTuriya Canonical Trace Schema v0.1

Status: draft for POC, design partners, and integration adapters.

Purpose: define the canonical payload SuperTuriya should ingest from agent frameworks, logs, OpenTelemetry/OpenInference traces, coding agents, research agents, support agents, and enterprise workflow agents.

## 1. Design Goals

The schema must support:

- multi-step agent trajectories
- model calls
- tool calls
- retrieval events
- memory events
- policy events
- human feedback
- latency, token, and cost accounting
- error states
- before/after comparison
- root-cause labeling
- memory-aware provenance
- state-transition scoring
- policy/memory writeback

The schema should be stable enough for design partners, but flexible enough to map from LangGraph, OpenAI Agents SDK, CrewAI, AutoGen, OpenTelemetry, OpenInference, LangSmith exports, Phoenix traces, Braintrust logs, and custom JSON.

## 2. Top-Level Trace Object

Required fields:

| Field | Type | Description |
| --- | --- | --- |
| `schema_version` | string | Must be `superturiya.trace.v0.1`. |
| `trace_id` | string | External trace ID from source system. |
| `tenant_id` | string | Workspace/customer scope. |
| `subject_id` | string | Subject, user, task, repo, customer, or workflow scope. |
| `agent_id` | string | Agent or application name. |
| `goal` | string | Goal given to the agent. |
| `started_at` | string | ISO-8601 timestamp. |
| `status` | string | One of `running`, `completed`, `failed`, `cancelled`, `timeout`. |
| `steps` | array | Ordered trajectory steps. |

Optional fields:

| Field | Type | Description |
| --- | --- | --- |
| `ended_at` | string | ISO-8601 timestamp. |
| `framework` | string | `langgraph`, `openai_agents`, `crewai`, `autogen`, `custom`, etc. |
| `environment` | string | `local`, `staging`, `production`, `eval`, `demo`. |
| `session_id` | string | Conversation/session ID if available. |
| `user_id` | string | Hashed or pseudonymous user identifier. |
| `run_group_id` | string | Group for before/after or experiment comparisons. |
| `parent_trace_id` | string | Parent trace for nested/child trajectories. |
| `expected_outcome` | object | Ground truth, success criteria, or target behavior. |
| `final_output` | object/string | Final result emitted by the agent. |
| `human_evaluation` | object | Human labels or review summary. |
| `metadata` | object | Custom framework/application metadata. |

## 3. Status Enums

Trace status:

- `running`
- `completed`
- `failed`
- `cancelled`
- `timeout`

Step status:

- `pending`
- `running`
- `completed`
- `failed`
- `skipped`
- `cancelled`
- `timeout`

Error severity:

- `info`
- `warning`
- `error`
- `critical`

## 4. Step Object

Required fields:

| Field | Type | Description |
| --- | --- | --- |
| `step_id` | string | Stable ID within the trace. |
| `step_index` | integer | Zero- or one-based order; importer should normalize to ordered sequence. |
| `kind` | string | Step type. |
| `source` | string | Agent, model, tool, router, evaluator, user, system, etc. |
| `status` | string | Step status enum. |

Recommended fields:

| Field | Type | Description |
| --- | --- | --- |
| `input` | string/object | Input to the step. |
| `output` | string/object | Output from the step. |
| `started_at` | string | ISO-8601 timestamp. |
| `ended_at` | string | ISO-8601 timestamp. |
| `duration_ms` | number | Step latency. |
| `parent_step_id` | string | Parent step for nested workflows. |
| `model_call` | object | Model metadata and token/cost usage. |
| `tool_call` | object | Tool invocation details. |
| `retrieval_event` | object | Retrieval details. |
| `memory_events` | array | Memory read/write/update/delete events. |
| `policy_events` | array | Policy checks or writeback candidates. |
| `error` | object | Error details if failed/timeout. |
| `labels` | object | Evaluation labels. |
| `metadata` | object | Custom metadata. |

Step `kind` values:

- `user_message`
- `assistant_message`
- `planning`
- `reasoning`
- `model`
- `tool`
- `retrieval`
- `memory`
- `decision`
- `evaluation`
- `policy`
- `feedback`
- `system`
- `handoff`
- `other`

## 5. Model Metadata Object

Required when a step includes a model call:

| Field | Type | Description |
| --- | --- | --- |
| `provider` | string | `openai`, `anthropic`, `google`, `mistral`, `local`, etc. |
| `model` | string | Model name. |

Optional:

| Field | Type | Description |
| --- | --- | --- |
| `temperature` | number | Sampling temperature. |
| `top_p` | number | Sampling parameter. |
| `max_output_tokens` | integer | Requested max output. |
| `prompt_tokens` | integer | Prompt/input token count. |
| `completion_tokens` | integer | Completion/output token count. |
| `total_tokens` | integer | Total token count. |
| `cached_tokens` | integer | Cached tokens if available. |
| `reasoning_tokens` | integer | Reasoning tokens if available. |
| `cost_usd` | number | Estimated cost in USD. |
| `latency_ms` | number | Model latency. |
| `request_id` | string | Provider request ID if available. |
| `finish_reason` | string | Stop reason. |

## 6. Tool Call Object

Required:

| Field | Type | Description |
| --- | --- | --- |
| `tool_call_id` | string | Tool call ID. |
| `tool_name` | string | Tool/function/service name. |
| `status` | string | Step status enum. |

Optional:

| Field | Type | Description |
| --- | --- | --- |
| `arguments` | object/string | Tool inputs. |
| `result` | object/string | Tool result. |
| `latency_ms` | number | Tool latency. |
| `retries` | integer | Retry count. |
| `external_request_id` | string | External service request ID. |
| `error` | object | Error details. |
| `side_effects` | array | Files changed, tickets created, emails sent, etc. |

## 7. Retrieval Event Object

Required:

| Field | Type | Description |
| --- | --- | --- |
| `retrieval_id` | string | Retrieval event ID. |
| `query` | string | Retrieval query. |
| `source` | string | Vector store, search engine, graph store, database, etc. |

Optional:

| Field | Type | Description |
| --- | --- | --- |
| `top_k` | integer | Requested result count. |
| `results` | array | Retrieval results. |
| `latency_ms` | number | Retrieval latency. |
| `embedding_model` | string | Embedding model. |
| `score_threshold` | number | Threshold used. |
| `filters` | object | Retrieval filters. |
| `error` | object | Error details. |

Retrieval result object:

| Field | Type | Description |
| --- | --- | --- |
| `document_id` | string | Source document/chunk ID. |
| `content` | string | Retrieved text or summary. |
| `score` | number | Retrieval score. |
| `rank` | integer | Rank order. |
| `source_uri` | string | Optional source URL/path. |
| `metadata` | object | Custom metadata. |

## 8. Memory Event Object

Required:

| Field | Type | Description |
| --- | --- | --- |
| `memory_event_id` | string | Memory event ID. |
| `operation` | string | `read`, `write`, `update`, `delete`, `suppress`, `promote`. |
| `memory_type` | string | `episodic`, `semantic`, `profile`, `procedural`, `policy`, `other`. |

Optional:

| Field | Type | Description |
| --- | --- | --- |
| `memory_id` | string | Existing memory ID. |
| `text` | string | Memory content. |
| `confidence` | number | 0-1 confidence. |
| `derived_from` | array | Observation/step IDs. |
| `graph_refs` | array | Related graph node/edge refs. |
| `conflict_with` | array | Memory IDs or refs in conflict. |
| `decision` | string | `used`, `ignored`, `suppressed`, `candidate`, `accepted`, `rejected`. |
| `metadata` | object | Custom metadata. |

## 9. Policy Event Object

Required:

| Field | Type | Description |
| --- | --- | --- |
| `policy_event_id` | string | Policy event ID. |
| `operation` | string | `check`, `violation`, `candidate`, `accept`, `reject`, `defer`. |
| `policy_kind` | string | `guardrail`, `routing`, `memory_governance`, `recovery`, `strategy`, etc. |

Optional:

| Field | Type | Description |
| --- | --- | --- |
| `policy_id` | string | Existing policy ID. |
| `title` | string | Policy title. |
| `body` | string | Policy body. |
| `confidence` | number | 0-1 confidence. |
| `evidence_refs` | array | Trace/step/observation refs. |
| `review_status` | string | `pending`, `accepted`, `rejected`, `deferred`. |
| `reviewer_id` | string | Human/system reviewer. |
| `metadata` | object | Custom metadata. |

## 10. Error Object

Required when status is failed/timeout:

| Field | Type | Description |
| --- | --- | --- |
| `type` | string | Error class/category. |
| `message` | string | Human-readable message. |

Optional:

| Field | Type | Description |
| --- | --- | --- |
| `code` | string | Stable error code. |
| `severity` | string | `info`, `warning`, `error`, `critical`. |
| `retryable` | boolean | Whether retry is safe. |
| `stack` | string | Sanitized stack trace. |
| `raw` | object/string | Sanitized raw error. |

## 11. Human Evaluation Object

Optional but strongly recommended for design partners.

| Field | Type | Description |
| --- | --- | --- |
| `success` | boolean | Human judgment of final success. |
| `score` | number | 0-1 overall human score. |
| `root_cause_labels` | array | Human root-cause labels. |
| `failure_mode` | string | Primary failure type. |
| `notes` | string | Reviewer notes. |
| `reviewer_id` | string | Reviewer ID. |
| `reviewed_at` | string | ISO-8601 timestamp. |

## 12. Cost And Latency Aggregates

Top-level optional aggregate:

```json
{
  "usage": {
    "total_latency_ms": 24500,
    "model_latency_ms": 18300,
    "tool_latency_ms": 4100,
    "retrieval_latency_ms": 2100,
    "prompt_tokens": 8120,
    "completion_tokens": 1420,
    "total_tokens": 9540,
    "cost_usd": 0.1842
  }
}
```

## 13. Minimal Example

```json
{
  "schema_version": "superturiya.trace.v0.1",
  "trace_id": "trace_001",
  "tenant_id": "demo",
  "subject_id": "repo_fix_001",
  "agent_id": "coding_agent",
  "framework": "custom",
  "environment": "demo",
  "goal": "Fix failing test after dependency update.",
  "started_at": "2026-07-03T08:00:00Z",
  "ended_at": "2026-07-03T08:02:10Z",
  "status": "completed",
  "steps": [
    {
      "step_id": "step_001",
      "step_index": 1,
      "kind": "retrieval",
      "source": "memory_router",
      "status": "completed",
      "input": "Find previous dependency migration notes.",
      "output": "Retrieved stale migration memory.",
      "started_at": "2026-07-03T08:00:04Z",
      "ended_at": "2026-07-03T08:00:07Z",
      "duration_ms": 3000,
      "memory_events": [
        {
          "memory_event_id": "memevt_001",
          "operation": "read",
          "memory_type": "procedural",
          "memory_id": "mem_old_migration",
          "text": "Use legacy import path for package X.",
          "confidence": 0.62,
          "decision": "used"
        }
      ]
    },
    {
      "step_id": "step_002",
      "step_index": 2,
      "kind": "tool",
      "source": "pytest",
      "status": "failed",
      "input": "Run unit tests.",
      "output": "ImportError in package X.",
      "tool_call": {
        "tool_call_id": "tool_001",
        "tool_name": "pytest",
        "status": "failed",
        "arguments": {"path": "tests/"},
        "result": "ImportError: cannot import legacy path",
        "latency_ms": 8200,
        "error": {
          "type": "ImportError",
          "message": "Legacy import path no longer exists.",
          "severity": "error",
          "retryable": false
        }
      }
    }
  ],
  "human_evaluation": {
    "success": false,
    "score": 0.35,
    "root_cause_labels": ["stale_memory", "weak_verification"],
    "failure_mode": "memory_conflict",
    "notes": "Agent trusted old memory without checking current docs."
  }
}
```

## 14. Importer Rules

Importers must:

- preserve external IDs in metadata
- normalize step order
- sanitize secrets before storage
- create observations from meaningful step inputs/outputs
- attach memory/tool/retrieval/policy refs to steps
- compute or preserve latency, token, and cost fields
- store raw source payload only if privacy policy allows it
- report skipped/invalid records clearly

## 15. Versioning Rules

- v0.1 is allowed to change during POC.
- Breaking changes after design partner onboarding should create v0.2.
- Importers should reject unknown future major versions and warn on unknown minor fields.

