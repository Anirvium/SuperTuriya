# Historical Primary LIVE Route: Groq Free Tier

> This preregistered primary route paused at 72/144 checkpoints because free
> daily capacity was exhausted before a complete artifact or score existed. It
> was not scored or combined with another model. The completed final evidence is
> the separately preregistered Qwen fallback documented in
> `external_v2_final_report.md`.

## Decision

Use Groq's OpenAI-compatible API with `openai/gpt-oss-120b` for the submitted
same-model LIVE experiment. Keep FROZEN mode as the credential-free,
deterministic reproduction path.

This choice does not make Groq a production dependency. It supplies one real
model experiment that tests whether the measured SuperTuriya advantage survives
outside the committed deterministic reasoning outputs.

The challenge materials and public event page do not identify a participant
compute allocation or API-credit redemption flow. OpenAI API access should also
not be treated as free by default: current accounts use prepaid billing unless
the account already has a credit grant. The experiment therefore targets a
published provider Free tier instead of depending on unconfirmed sponsorship.

## Why this is the final option

- No local model or GPU is required.
- Groq publishes Free-tier access for the selected model.
- The endpoint accepts the OpenAI-compatible Chat Completions and JSON-object
  contract already used by SuperTuriya.
- Baseline, Investigator, and Adaptation outputs use provider-enforced strict
  JSON schemas; mechanical lifecycle fields and frozen before-state hashes are
  bound locally before deterministic validation.
- The exact same endpoint, credential binding, requested model, case order,
  temperature, replay engine, and verifier are enforced for baseline and final.
- Provider model identity and provider-reported token usage are captured.
- Credentials and model response content are not written to evidence.
- Rate-limit pacing and transient retries are explicit and recorded.

Provider limits can change. Check the Groq Console limits page immediately
before the final run. The values below are deliberately conservative for the
currently published 30 requests-per-minute Free-tier limit.

## Configure zsh without saving the key in shell history

Create a Groq API key at <https://console.groq.com/keys>, then run:

```bash
cd /path/to/SuperTuriya
source .venv/bin/activate

export SUPERTURIYA_LLM_ENDPOINT='https://api.groq.com/openai/v1/chat/completions'
export SUPERTURIYA_LLM_MODEL='openai/gpt-oss-120b'
export SUPERTURIYA_LLM_MIN_INTERVAL_SECONDS='2.2'
export SUPERTURIYA_LLM_MAX_RETRIES='6'
export SUPERTURIYA_LLM_RETRY_BASE_SECONDS='5'

read -s "SUPERTURIYA_LLM_API_KEY?Paste Groq API key: "
export SUPERTURIYA_LLM_API_KEY
echo
```

Do not place the key in `.env`, a Markdown file, evidence JSON, terminal output,
screenshots, or the repository.

## Execute the evidence protocol

First validate the sealed benchmark and gold-label isolation:

```bash
python3 -m superturiya.external_validity validate
python3 -m superturiya.external_validity isolation
```

Make exactly one provider call to confirm authentication, JSON mode, returned
model identity, and usage metadata:

```bash
python3 -m superturiya.external_validity probe
```

Only after the probe succeeds, execute the LIVE ablation:

```bash
python3 -m superturiya.external_validity ablation --mode live
```

Then generate the complete bundle. `--include-live` performs the preregistered
three-trial comparison once and hashes all evidence, including the existing LIVE
ablation:

```bash
python3 -m superturiya.external_validity bundle --include-live
python3 -m unittest discover -s tests -v
```

Do not switch models after seeing results. If the run fails because of a
provider outage or exhausted quota, preserve the failure artifact, wait for the
published limit window, and rerun the same frozen protocol. Do not selectively
remove failed cases or incomplete trials.

## Expected artifacts

The run writes versioned evidence under `evidence/external_validity/v1/`:

- `live_probe.json`: redacted one-call compatibility proof;
- `live_comparison.json`: three complete baseline-versus-SuperTuriya trials;
- `ablation_live.json`: LIVE component ablation;
- `live_status.json`: configuration/completion status without the credential;
- `manifest.json`: artifact hashes, source revision, and dirty-state disclosure.

The comparison uses 36 successful model calls per trial: 12 direct-baseline
calls and 24 SuperTuriya calls (Investigator plus Adaptation). Three trials use
108 successful calls. The LIVE ablation uses another 36. Retry attempts are
recorded separately and never counted as successful agent calls.

## Submission claim boundary

Claim:

> On a sealed 12-case structural-transfer benchmark, SuperTuriya was compared
> with a direct baseline using the same external model under an enforced
> same-model contract. A deterministic verifier—not the model—decided recovery
> and safety.

Do not claim third-party validation, production generalization, physical quantum
computing, consciousness, or that Groq sponsored the project.
