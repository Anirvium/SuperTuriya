"""Illustrative local workflow: run with PYTHONPATH=. python3 examples/record_agent.py."""
from superturiya.recorder import TraceRecorder

trace = TraceRecorder("example-assistant", "Look up an item and record a failed request")
try:
    with trace.span("request", input={"item": "example-item"}):
        with trace.span("catalog.lookup", kind="tool", input={"item": "example-item"}) as step:
            step.output({"available": True, "source": "local-example-catalog"})
        with trace.span("request.submit", kind="tool", input={"quantity": -2}):
            raise ValueError("quantity must be positive")
except ValueError:
    pass
print(trace.export("output/recorded-agent.json"))
