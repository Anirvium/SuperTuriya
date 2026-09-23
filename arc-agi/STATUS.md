# ARC-AGI-3 release status

Updated: 23 September 2026.

## Kaggle evidence

- **Version 2 — smoke passed.** Kaggle allocated an NVIDIA RTX PRO 6000 (95 GiB),
  installed the official ARC runtime, verified the embedded source bundle, and wrote
  a valid placeholder `submission.parquet`.
- **Version 3 — model startup failed before inference.** The model was attached under
  Kaggle's nested model mount, while the notebook only searched direct input children.
  No competition submission was made.
- **Version 4 — model commit passed.** Nested model and dataset mounts are resolved
  recursively; Kaggle loaded Qwen 3.8 27B FP8 with vLLM 0.19.0, passed the local
  model readiness probe, and wrote a valid Apache Parquet output. Model loading used
  28.51 GiB; the measured KV cache supports the configured eight concurrent games.
- **Official submissions — none.** There is no leaderboard score yet.

## Ready locally

- The ARC work is isolated under `arc-agi/`; root SuperTuriya entry points are unchanged.
- Kaggle-parity `arc-agi==0.9.8` and `arcengine==0.9.3` contracts are used locally.
- Observations expose only frames, state, completed levels, and available actions.
- Actions and click coordinates are validated before the environment is called.
- Model endpoints are restricted to credential-free loopback HTTP.
- Model-authored Python runs in a disposable process with syntax, time, memory, input,
  and output limits. It is a compute boundary, not a security sandbox.
- The runtime supports bounded concurrent games, one scorecard, and one environment
  creation per selected game.
- Run reports are written atomically and journals are hash chained.
- The notebook is generated from exact source bytes, works with internet disabled,
  targets `NvidiaRtxPro6000`, and points to
  `piyusha1234/notebook5326562b0c`.
- The model release pins a public Apache-2.0 Qwen 3.8 27B FP8 Kaggle model and an
  offline vLLM wheelhouse dataset.

## External gates

These remaining facts require an official Kaggle competition rerun and cannot be
certified by commit-mode execution:

1. The competition gateway completes a hidden rerun and emits the real parquet file.
2. The candidate establishes a leaderboard baseline for measured ablations.

The hardware, packaging, offline dependency, model-load, and inference gates have
passed. The hidden gateway and score require an official submission.

## Evidence labels

- **Local tests passed** means source contracts and simulated runtime behavior passed.
- **Kaggle commit passed** means the notebook ran on Kaggle and produced the placeholder
  output; it is not a competition score.
- **Competition rerun passed** means Kaggle executed the hidden gateway run.
- **Competitive** or **state of the art** requires a comparable leaderboard result.
