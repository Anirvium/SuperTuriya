# ARC-AGI-3 release status

Updated: 23 September 2026.

## Kaggle evidence

- **Version 2 — smoke passed.** Kaggle allocated an NVIDIA RTX PRO 6000 (95 GiB),
  installed the official ARC runtime, verified the embedded source bundle, and wrote
  a valid placeholder `submission.parquet`.
- **Version 3 — model startup failed before inference.** The model was attached under
  Kaggle's nested model mount, while the notebook only searched direct input children.
  No competition submission was made.
- **Version 4 — running.** Nested model and dataset mounts are now resolved recursively;
  the regression is covered by the local test suite. This run is the current full
  Qwen 3.8 27B FP8 candidate.
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

These remaining facts require a real Kaggle execution and cannot be certified locally:

1. The current Kaggle image and attached wheelhouse start vLLM successfully.
2. The mounted model loads and the Qwen readiness probe passes.
3. The competition gateway completes a hidden rerun and emits the real parquet file.
4. The candidate establishes a leaderboard baseline for measured ablations.

The first hardware and packaging gate has passed. The live model run exercises the
next two startup gates. The hidden gateway and score require an official submission.

## Evidence labels

- **Local tests passed** means source contracts and simulated runtime behavior passed.
- **Kaggle commit passed** means the notebook ran on Kaggle and produced the placeholder
  output; it is not a competition score.
- **Competition rerun passed** means Kaggle executed the hidden gateway run.
- **Competitive** or **state of the art** requires a comparable leaderboard result.
