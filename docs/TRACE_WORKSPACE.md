# Capture and inspect your own agent traces

Open `/traces.html` on the local Python operator. The repair playground links to
it through **Your traces**. This workspace accepts the native
`superturiya-trace-v1` JSON format; vendor-specific trace formats need an explicit
adapter. It does not execute uploaded content or run arbitrary code.

## Record a Python workflow

Run your workflow from the project checkout, or make this package available on
your Python path. The recorder uses the standard library and makes no network
calls. Wrap the operations you want to record:

```python
from superturiya.recorder import TraceRecorder

trace = TraceRecorder("my-agent", "Find catalog availability")
try:
    with trace.span("handle request", input={"item": "example"}):
        with trace.span("catalog.lookup", kind="tool", input={"item": "example"}) as span:
            result = {"available": True}  # Replace with your actual tool call.
            span.output(result)
finally:
    trace.export("output/my-agent-trace.json")
```

Inputs and outputs are captured only when explicitly supplied. The recorder
tracks nested spans, timing, completion status and exception type. It re-raises
exceptions and does not capture exception messages. Keep independent requests in
separate recorder instances. Export after the workflow has completed. The
recorder is an in-process aid, not a durable streaming collector; process crashes
before export can lose its in-memory spans.

Run `PYTHONPATH=. python3 examples/record_agent.py` for an illustrative local
failed-tool example. This example is not a customer workload or a benchmark of
agent quality.

## Review and save

1. Choose the JSON file in **Your traces**.
2. Inspect the preview, span details and full recording.
3. Remove anything private that the credential patterns did not catch.
4. Select **Save reviewed trace**.

Common authorization, token, password, API-key, cookie and credential fields are
masked before persistence. This is best-effort pattern matching, not a guarantee
of complete secret detection or personal-data removal. Unknown input fields are
discarded. The original unmasked upload is not retained by this importer.

Files go to the Python server you are connected to. The public marketing website
does not expose this import endpoint. For protected operator servers, bearer
tokens stay in tab memory and are sent in the Authorization header. Reloading
requires reconnecting. Use HTTPS and configured trusted origins before any
private remote deployment.

## Evidence and authority

An import is a single SQLite transaction. Source span IDs are namespaced through
new server IDs, so they cannot overwrite existing steps. Duplicate normalized,
masked content within one tenant returns its existing snapshot; another tenant
receives a separate snapshot. Imports are immutable through normal trace-write
routes. Their receipt includes the authenticated importing principal.

The workspace flags recorded failures, completed tool spans without captured
outputs, incomplete timing, and runs marked completed despite failed spans.
These checks do not establish causality or task correctness. A failed nested
operation can mark both the child and enclosing span failed; the displayed count
is a span count, not a count of independent root causes.

Imported recordings cannot currently run sandbox replay or activate policy.
That requires an executable adapter, an initial-state snapshot, modeled side
effects, a bounded repair surface, task-specific verifiers, and regression checks.
The existing synthetic playground remains the available end-to-end governed
repair demonstration.

Evidence exports check both normalized-content and inspection-report hashes.
Hashes are integrity comparisons, not signatures. Imports remain stored in your
configured database across restarts. The existing subject-erasure endpoint can
erase the `imported-traces` subject for the scoped tenant, including import
payloads. Audit event retention and backups are separate operational choices.

## API

- `POST /workspace/preview` with `{ "record": { ... } }`: validation and masked preview without persistence.
- `POST /workspace/import` with the same body: atomic save or existing-snapshot receipt.
- `GET /workspace/runs`: latest 100 imports in the bound tenant.
- `GET /workspace/runs/{run_id}`: integrity-checked document and inspection export.
- `GET /workspace/audit`: latest 100 tenant audit events.

Limits: 500 spans, 900 KB normalized import input, maximum nesting depth 20,
unique span identifiers and valid acyclic parent references. Recognized span
kinds are `step`, `tool`, `model`, `retrieval`, and `approval`; statuses are
`completed`, `failed`, `running`, and `unknown`. Timing fields use ISO timestamps
with explicit timezones.
