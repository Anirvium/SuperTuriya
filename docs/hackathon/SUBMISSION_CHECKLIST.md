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
- [x] Fifty-three automated tests pass; FROZEN regeneration matches benchmark hashes, case decisions, and metrics.
- [x] One explicitly non-benchmark shadow case demonstrates reuse of an activated procedural policy.
- [x] Secret-pattern scan reports no committed credential material.
- [x] LIVE runner has a redacted provider probe, same-model enforcement, Free-tier pacing, and bounded transient retries.

## External submission actions

- [ ] Choose and add a repository license; this is a founder/legal decision and was not inferred.
- [ ] Push the reviewed changes to the public submission repository.
- [ ] Record the 100-second judge flow in `JUDGE_DEMO_SCRIPT.md`.
- [ ] Deploy or provide the local run command accepted by the challenge submission form.
- [ ] Confirm team details, repository URL, demo URL/video, and written fields in HackerEarth.
- [ ] Re-run `make evaluate && make test` from the exact submitted commit and record its SHA.
- [x] Supply the provider key at runtime and preserve the first same-model LIVE comparison, including its zero-lift result.
- [ ] Complete two more same-model LIVE trials plus the LIVE ablation, then regenerate the evidence manifest without overwriting prior trials.
- [ ] Receive, validate, review, freeze, and execute the 12-16 independently authored external-v2 cases.
- [x] Freeze the v2 system-under-test source/experiment contract and generate the independent-author handoff packet.

Optional LIVE credentials are not required for judging or FROZEN reproduction and must not be committed.
