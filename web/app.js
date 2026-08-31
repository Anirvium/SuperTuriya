const $ = (id) => document.getElementById(id);
const state = { data: null, external: null, demo: null, interventionId: null, replay: null };

// Keep the product workflow ahead of supporting research evidence in the judge flow.
const externalProof = $("external-proof");
const recordedEvidence = $("live-evidence");
if (externalProof && recordedEvidence) externalProof.after(recordedEvidence);

function percent(value) {
  return `${((Number(value) || 0) * 100).toFixed(2)}%`;
}

function compactNumber(value) {
  const number = Number(value) || 0;
  return new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(number);
}

function toast(message, error = false) {
  const node = $("toast");
  node.textContent = message;
  node.className = `toast show${error ? " error" : ""}`;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { node.className = "toast"; }, 3600);
}

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "content-type": "application/json" }, ...options });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `Request failed (${response.status})`);
  return payload;
}

function setBusy(button, busy, label) {
  button.disabled = busy;
  button.dataset.label = button.dataset.label || button.textContent;
  button.textContent = busy ? label : button.dataset.label;
  document.body.classList.toggle("loading", busy);
}

function renderMetrics(report) {
  if (!report) return;
  const baseline = report.baseline.metrics;
  const final = report.final.metrics;
  const primary = final.coverage_adjusted_verified_recovery_rate;
  $("final-score").textContent = percent(primary);
  $("final-score").title = `${final.verified_safe_recoveries} verified safe recoveries / ${final.eligible_initial_failures} eligible held-out failures`;
  $("score-count").textContent = `${final.verified_safe_recoveries} / ${final.eligible_initial_failures}`;
  $("baseline-score").textContent = percent(baseline.coverage_adjusted_verified_recovery_rate);
  $("score-lift").textContent = `+${(report.improvement.absolute_vrr * 100).toFixed(2)} pp`;
  $("safety-rate").textContent = percent(final.safety_regression_rate);
  $("final-bar").style.width = percent(primary);
  $("baseline-marker").style.left = percent(baseline.coverage_adjusted_verified_recovery_rate);
  $("mode-label").textContent = `DEMO · ${report.mode.toLowerCase()} replay`;
}

function renderExternalCase() {
  const item = state.external?.cases?.find((candidate) => candidate.case_id === $("live-case-select").value);
  if (!item) return;
  const diagnosis = item.investigator;
  const adaptation = item.adaptation;
  const verifier = item.verifier;
  $("live-case-badge").textContent = `${item.difficult ? "Difficult · multi-causal" : "Single-causal"} · recorded`;
  $("live-failure-class").textContent = String(diagnosis.failure_class || "Unclassified").replaceAll("_", " ");
  $("live-critical-step").textContent = diagnosis.critical_step || "—";
  $("live-decisive-invariant").textContent = diagnosis.decisive_invariant || "—";
  $("live-root-cause").textContent = diagnosis.root_cause || "No structured root cause returned.";
  $("live-evidence-refs").innerHTML = (diagnosis.evidence_refs || []).map((ref) => `<span class="evidence-chip">${escapeHtml(ref)}</span>`).join("");
  $("live-operation").textContent = adaptation.operation || "—";
  $("live-target").textContent = adaptation.target_id || "—";
  $("live-rationale").textContent = adaptation.rationale || "No rationale returned.";
  $("live-risks").innerHTML = (adaptation.risks || []).map((risk) => `<li>${escapeHtml(risk)}</li>`).join("") || "<li>No risks returned.</li>";
  $("live-verdict").textContent = verifier.verified_safe_recovery ? "Verified safe recovery" : "Promotion blocked";
  $("live-verdict").className = verifier.verified_safe_recovery ? "passed" : "rejected";
  const failed = verifier.failed_after_replay || [];
  $("live-failed-after").textContent = verifier.verified_safe_recovery
    ? `All invariants passed · safety regression ${verifier.safety_regression ? "detected" : "0%"}.`
    : `Replay still failed: ${failed.join(" · ") || "verification gate"}. The model cannot promote this repair.`;
}

function renderExternalEvidence(payload) {
  state.external = payload;
  if (payload.status !== "available") {
    $("live-status-pill").textContent = "Recorded evidence unavailable";
    $("live-disclosure").textContent = payload.message || "No completed experiment artifact was found.";
    return;
  }
  const provider = payload.provider;
  const aggregate = payload.aggregate;
  const metrics = payload.metrics;
  $("live-status-pill").textContent = `${payload.evidence_class} evidence · recorded run`;
  $("live-status-pill").className = "evidence-status ready";
  $("live-model").textContent = provider.display_name || provider.model || "Unknown model";
  $("live-provider").textContent = provider.name || "OpenAI-compatible provider";
  $("live-temperature").textContent = provider.temperature ?? "—";
  $("live-calls").textContent = provider.call_count ?? "—";
  $("live-tokens").textContent = compactNumber(provider.total_tokens);
  $("live-credentials").textContent = provider.credential_recorded ? "Yes" : "No";
  $("live-baseline").textContent = percent(aggregate.baseline_cavrr_mean);
  $("live-final").textContent = percent(aggregate.final_cavrr_mean);
  const lift = Number(aggregate.mean_absolute_improvement || 0) * 100;
  $("live-lift").textContent = `${lift > 0 ? "+" : ""}${lift.toFixed(2)} pp · ${payload.headline}`;
  $("live-class-accuracy").textContent = percent(metrics.failure_class_accuracy);
  $("live-critical-accuracy").textContent = percent(metrics.critical_step_localization_accuracy);
  $("live-repair-accuracy").textContent = percent(metrics.repair_surface_accuracy);
  $("live-disclosure").textContent = `${payload.disclosure} ${payload.history_count} earlier LIVE artifact${payload.history_count === 1 ? " is" : "s are"} preserved.`;
  const select = $("live-case-select");
  select.innerHTML = "";
  payload.cases.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.case_id;
    option.textContent = `${item.case_id} — ${item.investigator.failure_class.replaceAll("_", " ")}${item.difficult ? " · difficult" : ""}`;
    select.append(option);
  });
  select.value = payload.cases[0]?.case_id || "";
  renderExternalCase();
}

async function loadExternalEvidence() {
  try {
    renderExternalEvidence(await api("/hackathon/external-validity"));
  } catch (error) {
    $("live-status-pill").textContent = "Evidence load failed";
    $("live-disclosure").textContent = error.message;
  }
}

function renderCases(cases) {
  const select = $("case-select");
  select.innerHTML = "";
  cases.filter((item) => item.split === "held_out").forEach((item) => {
    const option = document.createElement("option");
    option.value = item.case_id;
    option.textContent = `${item.case_id} — ${item.title}${item.difficult ? " · difficult" : ""}`;
    select.append(option);
  });
  select.value = "eval-006";
  updateCaseSummary();
}

function updateCaseSummary() {
  const selected = state.data?.cases.find((item) => item.case_id === $("case-select").value);
  if (!selected) return;
  $("case-goal").textContent = selected.goal;
  $("case-class").textContent = selected.difficult ? "Difficult · multi-causal" : "Hidden failure class";
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
}

function renderTimeline(steps, criticalStep) {
  const root = $("timeline");
  root.innerHTML = "";
  steps.forEach((step) => {
    const item = document.createElement("div");
    item.className = `timeline-step${step.step_id === criticalStep ? " critical" : ""}`;
    const refs = step.evidence_refs?.length ? ` · ${step.evidence_refs.join(", ")}` : "";
    item.innerHTML = `<span class="node">${String(step.index).padStart(2, "0")}</span><div><strong>${escapeHtml(step.source)} · ${escapeHtml(step.kind)}</strong><p>${escapeHtml(step.summary)}</p><small>${escapeHtml(step.step_id + refs)}</small></div>`;
    root.append(item);
  });
}

function renderPrepared(payload) {
  state.demo = payload;
  state.interventionId = payload.stored_intervention.intervention_id;
  state.replay = null;
  const diagnosis = payload.investigator_trajectory.output;
  const patch = payload.intervention;
  renderTimeline(payload.case.trajectory, diagnosis.critical_step);
  $("original-status").textContent = "Failed invariants";
  $("case-class").textContent = diagnosis.failure_class.replaceAll("_", " ");
  $("critical-step").textContent = diagnosis.critical_step;
  $("decisive-invariant").textContent = diagnosis.decisive_invariant;
  $("root-cause").textContent = diagnosis.root_cause;
  $("confidence").textContent = `${Math.round(diagnosis.confidence * 100)}% confidence`;
  $("evidence-refs").innerHTML = diagnosis.evidence_refs.map((ref) => `<span class="evidence-chip">${escapeHtml(ref)}</span>`).join("");
  $("patch-operation").textContent = patch.operation;
  $("patch-target").textContent = patch.target_id;
  $("patch-after").textContent = typeof patch.after_value === "string" ? patch.after_value : JSON.stringify(patch.after_value);
  $("patch-rationale").textContent = patch.rationale;
  $("approval-state").textContent = patch.approval_state;
  $("approval-state").className = `status ${patch.approval_state}`;
  $("before-verdict").textContent = "Failed verification";
  $("before-detail").textContent = payload.original.failed_invariants.join(" · ");
  $("after-verdict").textContent = "Pending replay";
  $("after-detail").textContent = "The patch is stored as a candidate; no replay or learning has occurred.";
  $("after-verdict").parentElement.className = "verdict after";
  $("promotion-icon").textContent = "○";
  $("promotion-icon").className = "promotion-icon";
  $("promotion-title").textContent = "Learning is gated";
  $("promotion-copy").textContent = "A candidate cannot become durable policy until replay passes every invariant.";
  $("approve-replay").dataset.label = "Approve & replay from frozen state";
  $("approve-replay").textContent = "Approve & replay from frozen state";
  $("approve-replay").disabled = false;
  $("activate-learning").dataset.label = "Activate procedural learning";
  $("activate-learning").textContent = "Activate procedural learning";
  $("activate-learning").disabled = true;
}

function renderReplay(payload) {
  state.replay = payload.replay;
  const replay = payload.replay.replay;
  const verified = payload.replay.verified_safe_recovery;
  $("approval-state").textContent = "approved";
  $("approval-state").className = "status approved";
  $("approve-replay").textContent = verified ? "Replay verified" : "Replay rejected";
  $("approve-replay").disabled = true;
  $("after-verdict").textContent = verified ? "Verified safe recovery" : "Rejected by verifier";
  $("after-detail").textContent = verified ? `All ${replay.invariants.length} invariants pass · no new safety regression · ${replay.verification_hash.slice(0, 12)}…` : `Failed: ${replay.failed_invariants.join(" · ") || "verification gate"}. No learning promotion allowed.`;
  $("after-verdict").parentElement.className = `verdict after ${verified ? "passed" : "rejected"}`;
  $("promotion-icon").textContent = verified ? "✓" : "×";
  $("promotion-icon").className = `promotion-icon${verified ? " ready" : ""}`;
  $("promotion-title").textContent = verified ? "Eligible for explicit activation" : "Learning candidate rejected";
  $("promotion-copy").textContent = verified ? "Replay recovered the task with every invariant intact. A second review may now activate procedural learning." : "The verifier found an unresolved or regressed invariant. The patch stays out of durable policy.";
  $("activate-learning").disabled = !verified;
}

async function loadState() {
  try {
    state.data = await api("/hackathon/state");
    renderCases(state.data.cases);
    renderMetrics(state.data.latest_evaluation);
    $("benchmark-hash").textContent = `cases ${state.data.benchmark.case_hash.slice(0, 10)}… · labels ${state.data.benchmark.label_hash.slice(0, 10)}…`;
  } catch (error) { toast(error.message, true); }
}

$("case-select").addEventListener("change", updateCaseSummary);
$("live-case-select").addEventListener("change", renderExternalCase);

$("prepare-case").addEventListener("click", async () => {
  const button = $("prepare-case");
  try {
    setBusy(button, true, "Investigating…");
    const payload = await api("/hackathon/cases/prepare", { method: "POST", body: JSON.stringify({ tenant_id: "hackathon", case_id: $("case-select").value, mode: "frozen" }) });
    renderPrepared(payload);
    toast("Investigator localized the failure and proposed one typed candidate patch.");
  } catch (error) { toast(error.message, true); }
  finally { setBusy(button, false); }
});

$("approve-replay").addEventListener("click", async () => {
  const button = $("approve-replay");
  try {
    setBusy(button, true, "Replaying frozen state…");
    const payload = await api("/hackathon/interventions/review", { method: "POST", body: JSON.stringify({ tenant_id: "hackathon", intervention_id: state.interventionId, decision: "approved", reviewer_id: "demo-judge", note: "Explicit UI approval after evidence review.", mode: "frozen" }) });
    renderReplay(payload);
    toast(payload.replay.verified_safe_recovery ? "Verified safe recovery. Learning remains gated." : "Replay rejected the patch; promotion remains blocked.");
  } catch (error) { toast(error.message, true); }
  finally { document.body.classList.remove("loading"); }
});

$("activate-learning").addEventListener("click", async () => {
  const button = $("activate-learning");
  try {
    setBusy(button, true, "Activating…");
    const payload = await api("/hackathon/interventions/activate", { method: "POST", body: JSON.stringify({ tenant_id: "hackathon", intervention_id: state.interventionId, reviewer_id: "demo-judge", note: "Explicitly promote verified replay to durable procedural policy." }) });
    $("approval-state").textContent = "active";
    $("approval-state").className = "status active";
    $("promotion-title").textContent = "Procedural learning active";
    $("promotion-copy").textContent = `${payload.procedural_policy.title} · auditable policy ${payload.procedural_policy.policy_id}`;
    button.textContent = "Learning activated";
    button.disabled = true;
    toast("Verified repair promoted to active procedural policy with an audit trail.");
  } catch (error) { toast(error.message, true); setBusy(button, false); }
  finally { document.body.classList.remove("loading"); }
});

$("run-evaluation").addEventListener("click", async () => {
  const button = $("run-evaluation");
  try {
    setBusy(button, true, "Running 12 cases…");
    const report = await api("/hackathon/evaluate", { method: "POST", body: JSON.stringify({ tenant_id: "hackathon", mode: "frozen" }) });
    renderMetrics(report);
    toast(`Evaluation complete: ${report.final.metrics.verified_safe_recoveries}/12 verified safe recoveries.`);
  } catch (error) { toast(error.message, true); }
  finally { setBusy(button, false); }
});

loadState();
loadExternalEvidence();
