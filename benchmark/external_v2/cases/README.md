# Agent-visible external-v2 cases

An independent author places 12-16 files named `v2-NNN.json` here. These are
the only benchmark files available to the baseline, Investigator, and
Adaptation agents. Do not include failure labels, decisive invariants, expected
repair surfaces, adjudication notes, or canary strings.

Validate with:

```bash
python3 -m superturiya.external_v2 validate
```

The schema intentionally preserves the frozen deterministic cloud-operations
simulator contract while allowing independently authored scenario language,
longer trajectories, evidence patterns, and multi-causal combinations. It does
not support claims of transfer to unrelated domains.
