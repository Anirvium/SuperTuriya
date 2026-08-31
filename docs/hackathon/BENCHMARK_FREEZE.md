# Benchmark Freeze Record

The micro1 benchmark was frozen before the evidence-hardening phase. No case, held-out label, Investigator rule, Adaptation mapping, replay rule, or verifier rule may now be changed to improve held-out outcomes.

- Freeze commit: `bbe7fb9cc55d028796628ee4db0710767e4e70f6`
- `benchmark/cases.json` byte SHA-256: `053725a78acf10f4024b5cc068dc34801e75f3229c41b5e661b6c614e024146a`
- `benchmark/labels.json` byte SHA-256: `19d83916218462eb04ba5af999caa52ea77cfd1cea2a1971ab15071a6996e076`
- Canonical case-content hash: `1ce1700ecc3eb21cf1fa28442131ceceb8bf694093ba98297ddfc3ee6879f05b`
- Canonical label-content hash: `31e1666b99360f12fbbbe9cd786e1975ac05988b7c171e9579170af99976c890`

`python3 -m superturiya.hackathon validate` fails if either frozen file’s byte hash changes.

## Integrity disclosure

The cases, labels, and FROZEN deterministic reasoning rules were co-developed during the initial hackathon implementation before this freeze. The held-out split is isolated from runtime agents and evaluation inputs, but it is not an externally authored or previously unseen production dataset. No post-freeze tuning is permitted. Results demonstrate controlled control-plane mechanics and must not be represented as production generalization.
