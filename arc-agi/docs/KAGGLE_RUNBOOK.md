# Kaggle runbook

This is the only release path for `piyusha1234/notebook5326562b0c`.

## 1. Local gate

From `SuperTuriya/arc-agi`:

```bash
make setup
make test
make cache
make local-smoke
```

Do not upload a candidate when tests fail or the public-game runner reports an incomplete
run.

## 2. Save the Kaggle credential locally

Create a token at <https://www.kaggle.com/settings>. Store it as one line at:

```text
SuperTuriya/arc-agi/.kaggle/access_token
```

The directory is ignored by Git. Do not put the token in source code, a notebook cell,
terminal output, or a message.

## 3. Prove the RTX pipeline

```bash
make first-kaggle-test
make status
```

This builds and pushes `configs/smoke.json`. Wait until the status is `complete`, then
open <https://www.kaggle.com/code/piyusha1234/notebook5326562b0c> and inspect the latest
version. It must show all of the following:

```text
GPU: NVIDIA RTX PRO 6000 ...
Official ARC runtime installed from competition inputs.
Embedded SuperTuriya ARC source verified (... files).
Kaggle commit-mode validation passed; placeholder submission created.
```

The output must contain `submission.parquet`. This version proves packaging and hardware;
it is not the model candidate.

## 4. Prove the model pipeline

```bash
make kaggle-model
make status
```

The generated metadata attaches the model and wheelhouse automatically. In addition to
the smoke messages, the latest version must show:

```text
vLLM: ...
Model path: /kaggle/input/...
Local model readiness probe passed.
```

If the run fails, use the notebook log and `model-server.log`. Fix source locally and
rebuild. Do not edit the generated notebook on Kaggle.

## 5. Spend an official submission deliberately

Only after the model commit completes:

1. Open the latest successful version on Kaggle.
2. Click **Submit to Competition**.
3. Select `submission.parquet` if Kaggle asks for an output file.
4. Wait for the competition rerun and leaderboard result.
5. Record the notebook version, profile, build manifest hash, score, runtime, and failure
   notes before changing the candidate.

The CLI upload does not spend one of the daily competition submissions. Clicking
**Submit to Competition** does.

## 6. Pull evidence

```bash
make pull-output
```

Outputs are downloaded under `results/`. Keep the build manifest with every recorded
score so later comparisons refer to exact source and configuration.

## Recovery rules

- A Kaggle infrastructure failure does not justify changing solver logic.
- A CUDA or vLLM startup failure is fixed in packaging before agent tuning.
- An invalid model response is repaired before any environment action; ambiguous real
  actions are never retried.
- Complex repair features are promoted only after paired runs beat the memory profile
  under the same model, games, runtime, and token limits.
