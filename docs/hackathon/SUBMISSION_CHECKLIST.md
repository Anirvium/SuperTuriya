# Submission Checklist

## Repository-ready

- [x] Accepted short specification contains all eight mandatory amendments.
- [x] Pre-hackathon boundary and governance defect are recorded.
- [x] 3 development + 12 held-out cases validate; labels are separate and hashed.
- [x] Direct baseline and final use the same fixtures, replay, verifier, and fixed denominator.
- [x] Complete per-case evidence and aggregate metrics are committed.
- [x] Unknown operations and unapproved replay fail closed.
- [x] Candidate → approved → active is enforced and audited.
- [x] Original v1 APIs and console remain available at `/legacy.html`.
- [x] Fifty-eight automated tests pass; FROZEN regeneration matches benchmark hashes, case decisions, and metrics.
- [x] One explicitly non-benchmark shadow case demonstrates reuse of an activated procedural policy.
- [x] Secret-pattern scan reports no committed credential material.
- [x] LIVE runner has a redacted provider probe, same-model enforcement, Free-tier pacing, and bounded transient retries.

## External submission actions

- [x] Add the MIT repository license.
- [x] Push the reviewed implementation and evidence to the public submission repository.
- [x] Prepare the judge flow in `JUDGE_DEMO_SCRIPT.md`.
- [x] Provide the credential-free local run command in README and `REPRODUCTION.md`.
- [ ] Confirm team details, repository URL, demo URL/video, and written fields in HackerEarth.
- [x] Re-run the full suite and frozen integrity checks from a clean public clone: 58/58 tests, External-v2 frozen and valid.
- [x] Supply the provider key at runtime and preserve the first same-model LIVE comparison, including its zero-lift result.
- [x] Preserve the capacity-limited primary External-v2 attempt without mixing models or producing a partial score.
- [x] Preregister and complete the separate Qwen fallback: three trials, 144/144 calls, raw predictions before scoring, and a content-addressed manifest.
- [x] Receive, mechanically validate, semantically review, correct, freeze, and execute 16 blinded/adversarial External-v2 cases.
- [x] Freeze and verify the v2 system-under-test source/experiment contract.
- [ ] Record and upload the solution video of no more than five minutes.
- [ ] Verify every submitted link and publish the final HackerEarth form.

Optional LIVE credentials are not required for judging or FROZEN reproduction and must not be committed.
