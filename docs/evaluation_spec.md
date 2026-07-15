# SuperTuriya Evaluation Spec

Status: v0.1 scoring contract for POC, demo traces, and design partner validation.

Purpose: define the scoring logic behind utility, grounding, memory relevance, recovery, ambiguity, experience coherence, state gap, and policy acceptance.

## 1. Principles

SuperTuriya evaluates trajectories at two levels:

- function: whether the agent completed the task efficiently and safely
- experience state: whether the path was grounded, memory-consistent, recoverable, low-friction, and suitable for reuse

The product should not reward task completion alone. A completed trajectory can still be fragile if it relied on stale memory, unsupported assumptions, weak retrieval, or repeated recovery loops.

All v0.1 scores are normalized to `0.0` through `1.0`.

## 2. Current Utility Metrics

These formulas match the current implementation in `superturiya/intelligence.py`.

### 2.1 Goal Completion

```text
goal_completion = 0.96 if run completed else 0.28

if failure_steps and recovery_steps:
  goal_completion = max(goal_completion, 0.68)
```

Interpretation:

- completed run: high score
- failed run: low score
- failed but recovered path: partial credit because recovery behavior matters

### 2.2 Evidence Grounding

Evidence steps include steps with memory refs, tool/retrieval/memory kind, or explicit evidence text.

```text
observation_bonus = 0.08 if observations exist else 0.0

evidence_grounding = clamp(
  evidence_step_count / max(1, step_count) + observation_bonus
)

if no evidence_steps and observations exist:
  evidence_grounding = 0.42
```

Interpretation:

- high score means the path used observable evidence, retrieval, memory, or tool outputs
- low score means the agent likely reasoned without enough external support

### 2.3 Memory Relevance

```text
active_memory_bonus = 0.20 if active memories exist else 0.0
procedural_memory_bonus = 0.10 if procedural memory exists else 0.0

memory_relevance = clamp(
  (unique_memory_ref_count / max(1, min(5, step_count))) * 0.70
  + active_memory_bonus
  + procedural_memory_bonus
)
```

Interpretation:

- high score means memory was available and connected to the trajectory
- future versions should split this into `memory_presence`, `memory_usefulness`, and `memory_conflict`

### 2.4 Step Efficiency

```text
loop_penalty = max(0, step_count - 6) * 0.055
failure_penalty = failure_step_count * 0.09
step_efficiency = clamp(0.96 - loop_penalty - failure_penalty)
```

Interpretation:

- penalizes unnecessary loops and repeated failures
- does not yet distinguish useful exploration from wasteful looping

### 2.5 Policy Adherence

```text
policy_adherence = clamp(
  0.96
  - 0.18 * policy_violation_count
  - 0.05 * failure_step_count
)
```

Policy violations are currently detected from text signals such as `unsafe`, `violate`, or `ignored policy`.

### 2.6 Recovery Quality

```text
if failure_steps:
  recovery_quality = clamp((recovery_step_count / failure_step_count) * 0.72 + 0.12)
else:
  recovery_quality = 0.82 if step_count else 0.0
```

Interpretation:

- rewards trajectories that recover after failure
- gives healthy runs a stable baseline

## 3. Utility Score

```text
utility =
  0.24 * goal_completion
  + 0.20 * evidence_grounding
  + 0.16 * memory_relevance
  + 0.14 * step_efficiency
  + 0.14 * policy_adherence
  + 0.12 * recovery_quality
```

Weight logic:

| Metric | Weight | Why it matters |
| --- | ---: | --- |
| Goal completion | 0.24 | The agent still needs to finish the job. |
| Evidence grounding | 0.20 | Grounded paths are easier to trust and improve. |
| Memory relevance | 0.16 | Stateful agents need memory to be useful, not incidental. |
| Step efficiency | 0.14 | Long looping paths hide operational cost and instability. |
| Policy adherence | 0.14 | Unsafe or noncompliant paths cannot become reusable defaults. |
| Recovery quality | 0.12 | Durable agents must repair failures, not only avoid them. |

## 4. Root-Cause Scoring

Current root-cause hypotheses are deterministic:

- `missing_evidence` if evidence grounding is below `0.55`
- `weak_memory_routing` if memory relevance is below `0.45`
- `tool_failure` for failed steps unless text indicates another cause
- `memory_overgeneralisation` if failed text includes assumption or overgeneralization signals
- `stale_or_contradictory_memory` if failed text includes contradiction or stale-memory signals
- `inefficient_execution_path` if step efficiency is below `0.72`
- `empty_memory_substrate` if no active memory exists
- `healthy_trajectory` when evidence exists and no other cause is detected

Future versions should attach human root-cause agreement:

```text
root_cause_agreement = matched_human_labels / max(1, human_label_count)
```

## 5. Quantum-Inspired Interpretation Metrics

These formulas match the classical implementation in `superturiya/quantum_layer.py`. The language is quantum-inspired, not quantum computing.

### 5.1 Interpretation Probabilities

Each label receives evidence. Labels include:

- `retrieval_context_gap`
- `ambiguous_user_intent`
- `memory_conflict`
- `tool_selection_error`
- `weak_planning`
- `unsupported_assumption`
- `policy_or_safety_risk`
- `successful_recovery`
- `efficient_grounded_execution`

Probabilities are computed by softmax:

```text
scaled_score_i = evidence_score_i * 2.35
probability_i = exp(scaled_score_i - max_scaled_score) / sum(exp(scaled_score_j - max_scaled_score))
```

### 5.2 Ambiguity And Entropy

```text
entropy = -sum(probability_i * log(max(probability_i, 1e-12)))
normalized_entropy = entropy / log(label_count)
ambiguity_score = normalized_entropy
```

Ambiguity level:

```text
top_margin = top_probability - second_probability

if normalized_entropy >= 0.86 or top_margin < 0.08:
  ambiguity_level = "high"
elif normalized_entropy >= 0.70 or top_margin < 0.16:
  ambiguity_level = "medium_high"
elif normalized_entropy >= 0.48:
  ambiguity_level = "medium"
else:
  ambiguity_level = "low"
```

Interpretation:

- high ambiguity means multiple explanations remain plausible
- do not write durable memory or policy without more evidence when ambiguity is high

## 6. Experience Coherence

Experience coherence estimates whether the internal path condition is stable enough to trust or reuse.

```text
experience_coherence =
  0.22 * evidence_grounding
  + 0.18 * memory_relevance
  + 0.16 * recovery_quality
  + 0.14 * policy_adherence
  + 0.12 * step_efficiency
  + 0.08 * (1 - normalized_entropy)
  + 0.06 * (1 - failure_rate)
  + 0.04 * min(1, graph_density)
```

Interpretation:

- high utility and high coherence: strong reusable trajectory
- high utility and low coherence: completed but fragile
- low utility and high coherence: coherent reasoning path blocked by final execution
- low utility and low coherence: unstable path requiring diagnosis

## 7. Function-Experience Gap

Function score:

```text
function_score = utility
```

Fallback if utility is missing:

```text
function_score = mean(
  goal_completion,
  evidence_grounding,
  step_efficiency,
  policy_adherence,
  recovery_quality
)
```

Gap metrics:

```text
function_experience_gap = abs(function_score - experience_coherence)
hidden_friction_gap = clamp(function_score - experience_coherence)
unresolved_execution_gap = clamp(experience_coherence - function_score)
```

Product readout:

- `hidden_friction_gap`: the run succeeded externally but had internal path instability
- `unresolved_execution_gap`: the path was coherent but did not convert into task success

## 8. Attention-Memory Fidelity

```text
attention_memory_fidelity =
  (attention_repeats + 1) / (attention_repeats + latent_dimension_proxy)
```

Inputs:

- repeated memory references
- repeated entities
- feedback observations
- procedural memory support
- active relational couplings
- graph reinforcement

Interpretation:

- high fidelity: repeated evidence supports durable memory writeback
- low fidelity: collect more focused evidence before memory or policy updates

## 9. Policy Acceptance

Current state: policies can be synthesized, but human accept/reject/defer workflow is planned.

Planned scoring:

```text
policy_acceptance_rate =
  accepted_policy_candidates / max(1, proposed_policy_candidates)

weighted_policy_acceptance =
  sum(candidate_confidence * accepted_flag) / max(1, sum(candidate_confidence))

policy_writeback_precision =
  accepted_candidates_with_positive_before_after_delta / max(1, accepted_candidates)
```

Minimum acceptance fields:

- `policy_event_id`
- `operation`: `candidate`, `accept`, `reject`, or `defer`
- `evidence_refs`
- `reviewer_id`
- `review_status`
- `accepted_at` or `reviewed_at`

## 10. Design Partner Evaluation Loop

For each imported trace:

1. Compute utility and component metrics.
2. Compute interpretation probabilities and ambiguity.
3. Compute experience coherence and state gap.
4. Compare root-cause hypotheses to human root-cause labels.
5. Generate memory/policy writeback candidates.
6. Let human reviewer accept, reject, or defer candidates.
7. Re-run or compare an improved trace.
8. Measure utility delta, state gap reduction, and root-cause recurrence reduction.

The proof metric for funders:

```text
recurring_failure_reduction =
  (baseline_recurring_failures - post_writeback_recurring_failures)
  / max(1, baseline_recurring_failures)
```
