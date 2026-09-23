# SuperTuriya ARC-AGI-3

This directory is the complete, isolated ARC-AGI-3 workspace. It does not import or
modify the existing `superturiya/` application. The older product keeps its own
runtime, tests, database, web UI, and root `Makefile`.

The competition workflow has one source of truth:

```text
arc-agi/superturiya_arc/*.py
        -> local tests and public-game runs
        -> generated self-contained dist/kaggle/submission.ipynb
        -> piyusha1234/notebook5326562b0c on Kaggle
        -> Save & Run All
        -> Submit to Competition only after validation
```

Do not edit the generated notebook. Change the Python source, test it, and rebuild.

## First Kaggle test

Run these commands from this directory:

```bash
make setup
make test
make cache
make local-smoke
```

Create a Kaggle API token at <https://www.kaggle.com/settings>, then save it locally
as one line in `arc-agi/.kaggle/access_token`. Never commit it or paste it into chat.

```bash
mkdir -p .kaggle
chmod 700 .kaggle
# Save the token in .kaggle/access_token, then:
chmod 600 .kaggle/access_token
make first-kaggle-test
make status
```

`make first-kaggle-test` updates the existing private notebook
<https://www.kaggle.com/code/piyusha1234/notebook5326562b0c>. It selects the RTX Pro
6000, disables internet, installs the official ARC wheels from the competition input,
verifies CUDA, checks the embedded source hashes, runs a sandbox self-test, and creates
the commit-mode `submission.parquet`. It does not load a language model.

When Kaggle reports `complete`, inspect the notebook logs. The required success lines
are listed in [the Kaggle runbook](docs/KAGGLE_RUNBOOK.md). Do not spend an official
submission on the smoke profile unless we specifically need to verify the hidden rerun.

## Model candidate

After the smoke version passes:

```bash
make kaggle-model
make status
```

The metadata automatically attaches:

- `foysalemonshanto/qwen3-8-27b-fp8-repacked-v1/pyTorch/hf-fp8/1`
- `driessmit1/arc3-vllm-h100-wheelhouse-v3`
- the `arc-prize-2026-arc-agi-3` competition input

The notebook discovers their mounted paths, installs vLLM offline, starts Qwen 3.8
27B FP8 on localhost, sends a schema-checked readiness prompt, and only then creates
the commit-mode output. During the competition rerun it waits for Kaggle's gateway,
opens exactly one scorecard, creates every environment once, plays games concurrently,
and lets the gateway create the real `submission.parquet`.

## Commands

| Command | Purpose |
|---|---|
| `make test` | Run contracts, solver, packaging, and runtime tests |
| `make cache` | Download and cache the selected public games |
| `make local-smoke` | Run and verify a short public-game integration test |
| `make build-smoke` | Generate the RTX pipeline validation notebook |
| `make build-model` | Generate the Qwen 3.8 competition notebook |
| `make build-repair` | Generate the repair ablation; not the default candidate |
| `make kaggle-public-memory` | Run the frozen eight-game public benchmark with memory |
| `make kaggle-public-repair` | Run the same benchmark with executable model repair |
| `make verify` | Recheck notebook hash, code cells, offline metadata, and inputs |
| `make push` | Upload the already-built `dist/kaggle` version |
| `make status` | Query Kaggle for the current notebook version status |
| `make pull-output` | Download outputs of the latest completed notebook version |

Every rebuild archives the previous generated directory under `dist/archive/`; it does
not silently overwrite the last artifact.

The public benchmark uses `cd82`, `ft09`, `ls20`, `r11l`, `s5i5`, `tu93`, `vc33`,
and `wa30` from the official competition input. It runs privately in notebook commit
mode, writes `arc-agi-run/report.json` plus hash-chained game journals, and still emits
the placeholder parquet required by Kaggle. These runs do not consume the daily
competition submission quota.

## Competition design

The default competition profile is intentionally smaller than the experimental repair
profile. It uses:

- Qwen 3.8 27B FP8 with raw grid plus image context;
- compact per-game notes and recent transition summaries;
- legal-action validation and coordinate validation before every real step;
- short action plans that are cancelled when an observation contradicts a prediction;
- bounded ephemeral Python for parsing, counting, search, and hypothesis checks;
- no-effect tracking and object-aware click exploration as failure fallbacks;
- eight concurrent games so vLLM can batch requests and use the RTX GPU effectively;
- one scorecard, one environment creation per game, offline inference, and a fixed
  global deadline with finalization reserve;
- append-only hash-chained journals and source/build hashes for diagnosis.

`repair-ablation.json` adds executable transition-model proposals and prospective
counterexample checks. It is excluded from the default candidate until paired public
game runs show a real score or efficiency gain.

This repository can make a submission reproducible and competitive in design. A win or
state-of-the-art result is established only by comparable Kaggle scores; it cannot be
guaranteed from architecture or local tests.

See [current status](STATUS.md), [Kaggle runbook](docs/KAGGLE_RUNBOOK.md), and the
[research strategy](docs/strategy.md).
