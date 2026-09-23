# Third-party runtime inputs

The generated notebook contains SuperTuriya ARC source and references these external
Kaggle inputs. Their code and weights are not copied into this repository.

| Input | Pinned reference | Purpose |
|---|---|---|
| ARC-AGI-3 competition | `arc-prize-2026-arc-agi-3` | Official SDK wheels, framework data, and gateway |
| Qwen 3.8 27B FP8 repack | `foysalemonshanto/qwen3-8-27b-fp8-repacked-v1/pyTorch/hf-fp8/1` | Offline local vision-language model; listed as Apache-2.0 |
| ARC3 vLLM wheelhouse | `driessmit1/arc3-vllm-h100-wheelhouse-v3` | Offline Linux/CUDA inference dependencies |

Protocol reference: ARC Prize's
[ARC-AGI-3 Kaggle Starter](https://github.com/arcprize/ARC-AGI-3-Kaggle-Starter),
commit `eeb1535404f321d280a8f9194bbc1d7aca5f05fc`, reviewed on 16 September
2026. The generated notebook uses the organizer's commit-versus-rerun protocol but does
not vendor that repository.

Before a public prize release, recheck the competition's current publication and license
terms and include the licenses shipped with every attached model and dataset.
