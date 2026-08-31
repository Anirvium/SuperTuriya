const state = {
  tenant: "demo",
  subject: "user_42",
  activeRun: null,
  data: null,
  counterfactuals: [],
};

const byId = (id) => document.getElementById(id);

function svgText(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#039;",
  })[char]);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    method: options.method || "GET",
    headers: options.body ? { "content-type": "application/json" } : undefined,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || payload.detail || response.statusText);
  }
  return payload;
}

function toast(message) {
  const node = byId("toast");
  node.textContent = message;
  node.classList.add("visible");
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => node.classList.remove("visible"), 2600);
}

function scope() {
  state.tenant = byId("tenant").value.trim() || "demo";
  state.subject = byId("subject").value.trim() || "user_42";
  return { tenant_id: state.tenant, subject_id: state.subject };
}

async function refresh() {
  scope();
  state.data = await api(`/dashboard/state?tenant_id=${encodeURIComponent(state.tenant)}&subject_id=${encodeURIComponent(state.subject)}`);
  if (!state.activeRun && state.data.traces.length) {
    state.activeRun = state.data.traces[0].run_id;
  }
  render();
}

function render() {
  renderExecutiveStrip();
  renderCounts();
  renderRuns();
  renderScore();
  renderQuantumReport();
  renderExperienceState();
  renderGraph();
  renderMemories(state.data.memories || []);
  renderPolicies();
  renderAudit();
  renderCounterfactuals();
  byId("active-run").textContent = state.activeRun || "No active run";
}

function renderExecutiveStrip() {
  const counts = state.data.counts || {};
  const score = latestScore();
  byId("hero-utility").textContent = score ? Number(score.utility || 0).toFixed(2) : "0.00";
  byId("hero-status").textContent = state.activeRun
    ? `${state.activeRun} / ${score ? "scored" : "capturing"}`
    : "No trajectory selected";
  byId("hero-graph").textContent = `${counts.nodes || 0} nodes / ${counts.edges || 0} edges`;
  byId("hero-memory").textContent = `${counts.memories || 0} memories`;
  byId("hero-governance").textContent = `${counts.policies || 0} policies`;
}

function renderCounts() {
  const counts = state.data.counts || {};
  const order = ["observations", "memories", "interpretations", "edges", "traces", "steps", "scores", "policies"];
  byId("counts").innerHTML = order.map((key) => `
    <div class="metric">
      <strong>${counts[key] || 0}</strong>
      <span>${svgText(key)}</span>
    </div>
  `).join("");
}

function latestQuantumReport() {
  const report = state.data.latest_quantum_report || (state.data.quantum_reports || [])[0];
  if (!report) return null;
  return report.full_report || report;
}

function renderRuns() {
  const runs = state.data.traces || [];
  byId("runs").innerHTML = runs.length ? runs.map((run) => `
    <button class="item ${run.run_id === state.activeRun ? "success" : ""}" data-run="${svgText(run.run_id)}">
      <strong>${svgText(run.agent_id)} / ${svgText(run.status)}</strong>
      <p>${svgText(run.goal)}</p>
      <small>${svgText(run.run_id)}</small>
    </button>
  `).join("") : `<div class="item"><strong>No runs recorded</strong></div>`;

  byId("runs").querySelectorAll("[data-run]").forEach((node) => {
    node.addEventListener("click", () => {
      state.activeRun = node.dataset.run;
      render();
    });
  });
}

function latestScore() {
  if (!state.data.scores || !state.data.scores.length) return null;
  if (!state.activeRun) return state.data.scores[0];
  return state.data.scores.find((score) => score.run_id === state.activeRun) || state.data.scores[0];
}

function renderScore() {
  const score = latestScore();
  if (!score) {
    byId("utility-value").textContent = "0.00";
    byId("score-explanation").textContent = "No score loaded.";
    byId("metrics").innerHTML = "";
    return;
  }
  const metrics = score.metrics || {};
  byId("utility-value").textContent = Number(score.utility || 0).toFixed(2);
  byId("score-explanation").textContent = `${score.run_id} scored at ${score.created_at || "current"}.`;
  byId("metrics").innerHTML = Object.entries(metrics).map(([key, value]) => {
    const pct = Math.round(Number(value || 0) * 100);
    return `
      <div class="metric-bar">
        <div class="label"><span>${svgText(key.replaceAll("_", " "))}</span><span>${pct}%</span></div>
        <div class="bar"><span style="width:${pct}%"></span></div>
      </div>
    `;
  }).join("");
}

function renderMemories(memories) {
  const results = memories.slice(0, 18);
  byId("memory-results").innerHTML = results.length ? results.map((memory) => `
    <div class="item ${memory.memory_type === "procedural" ? "violet" : ""}">
      <strong>${svgText(memory.memory_type)} / ${Number(memory.confidence || 0).toFixed(2)}</strong>
      <p>${svgText(memory.text)}</p>
      <small>${svgText(memory.memory_id || "")}</small>
    </div>
  `).join("") : `<div class="item"><strong>No active memory</strong></div>`;
}

function renderPolicies() {
  const policies = state.data.policies || [];
  byId("policies").innerHTML = policies.length ? policies.map((policy) => `
    <div class="item warn">
      <strong>${svgText(policy.kind)} / ${svgText(policy.title)}</strong>
      <p>${svgText(policy.body)}</p>
      <small>${Number(policy.confidence || 0).toFixed(2)} confidence</small>
    </div>
  `).join("") : `<div class="item"><strong>No active policies</strong></div>`;
}

function renderQuantumReport() {
  const report = latestQuantumReport();
  if (!report) {
    byId("ambiguity-value").textContent = "0.00";
    byId("ambiguity-bar").style.width = "0%";
    byId("interpretations").innerHTML = `<div class="item"><strong>No interpretation report</strong></div>`;
    return;
  }
  const ambiguity = Number(report.ambiguity_score || report.normalized_entropy || 0);
  byId("ambiguity-value").textContent = ambiguity.toFixed(2);
  byId("ambiguity-bar").style.width = `${Math.round(ambiguity * 100)}%`;
  const entries = [
    ["Dominant", report.dominant_interpretation],
    ["Common", report.common_interpretation],
    ...(report.minor_interpretations || []).slice(0, 2).map((item) => ["Minor", item]),
  ].filter(([, item]) => item);
  byId("interpretations").innerHTML = entries.length ? entries.map(([role, item]) => `
    <div class="item ${role === "Dominant" ? "violet" : role === "Minor" ? "warn" : ""}">
      <strong>${svgText(role)} / ${svgText(item.label)} / ${Number(item.probability || 0).toFixed(2)}</strong>
      <p>${svgText((item.evidence || [])[0] || "No direct evidence")}</p>
      <small>${svgText(report.ambiguity_level || "unknown")} ambiguity</small>
    </div>
  `).join("") : `<div class="item"><strong>No interpretation report</strong></div>`;
}

function renderExperienceState() {
  const report = latestQuantumReport();
  const experience = report?.experience_state;
  if (!experience) {
    byId("experience-label").textContent = "No state";
    byId("function-score").textContent = "0.00";
    byId("experience-coherence").textContent = "0.00";
    byId("experience-gap").textContent = "0.00";
    byId("memory-fidelity").textContent = "0.00";
    byId("experience-readout").textContent = "Run an interpretation to load state.";
    byId("state-graph-summary").innerHTML = `<div class="item"><strong>No state graph yet</strong></div>`;
    return;
  }
  byId("experience-label").textContent = experience.state_label?.replaceAll("_", " ") || "state";
  byId("function-score").textContent = Number(experience.function_score || 0).toFixed(2);
  byId("experience-coherence").textContent = Number(experience.experience_coherence || 0).toFixed(2);
  byId("experience-gap").textContent = Number(experience.function_experience_gap || 0).toFixed(2);
  byId("memory-fidelity").textContent = Number(experience.attention_memory_fidelity?.fidelity || 0).toFixed(2);
  byId("experience-readout").textContent = experience.product_readout || "State loaded.";
  const graph = experience.state_transition_graph || {};
  const discovery = experience.graph_discovery || {};
  const motifs = discovery.motifs || [];
  const candidateEdges = discovery.candidate_edges || [];
  const rows = [
    {
      title: "State Graph",
      body: `${(graph.nodes || []).length} nodes / ${(graph.edges || []).length} edges`,
      meta: graph.readout || "transition graph",
      kind: "success",
    },
    ...motifs.slice(0, 2).map((motif) => ({
      title: motif.name,
      body: motif.action,
      meta: motif.trigger,
      kind: "warn",
    })),
    ...candidateEdges.slice(0, Math.max(0, 3 - motifs.length)).map((edge) => ({
      title: `${edge.from} -> ${edge.to}`,
      body: edge.type,
      meta: `${Number(edge.confidence || 0).toFixed(2)} confidence`,
      kind: "",
    })),
  ];
  byId("state-graph-summary").innerHTML = rows.length ? rows.map((row) => `
    <div class="item ${row.kind}">
      <strong>${svgText(row.title)}</strong>
      <p>${svgText(row.body)}</p>
      <small>${svgText(row.meta)}</small>
    </div>
  `).join("") : `<div class="item"><strong>No graph patterns discovered</strong></div>`;
}

async function quantumInterpret() {
  if (!state.activeRun) throw new Error("No active run");
  const result = await api("/trajectories/quantum-interpret", {
    method: "POST",
    body: { run_id: state.activeRun },
  });
  toast(`${result.dominant_interpretation.label} / ambiguity ${Number(result.ambiguity_score || 0).toFixed(2)}`);
  await refresh();
}

function renderAudit() {
  const audit = state.data.audit || [];
  byId("audit").innerHTML = audit.length ? audit.map((event) => `
    <div class="item ${event.action.includes("erase") ? "danger" : ""}">
      <strong>${svgText(event.action)}</strong>
      <small>${svgText(event.target_type)} ${svgText(event.target_id || "")} / ${svgText(event.created_at)}</small>
    </div>
  `).join("") : `<div class="item"><strong>No audit events</strong></div>`;
}

function renderCounterfactuals() {
  const list = state.counterfactuals || [];
  byId("counterfactual-list").innerHTML = list.length ? list.slice(0, 8).map((item) => {
    const kind = item.estimated_delta > 0.04 ? "danger" : item.estimated_delta < -0.04 ? "success" : "warn";
    return `
      <div class="item ${kind}">
        <strong>Step ${item.step_index}: ${svgText(item.kind)} (${item.estimated_delta})</strong>
        <p>${svgText(item.rationale)}</p>
        <small>${svgText(item.suggested_action)}</small>
      </div>
    `;
  }).join("") : `<div class="item"><strong>No counterfactual audit</strong></div>`;
}

function renderGraph() {
  const canvas = byId("graph");
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.max(640, Math.floor(rect.width * ratio));
  canvas.height = Math.max(330, Math.floor(rect.height * ratio));
  const ctx = canvas.getContext("2d");
  ctx.scale(ratio, ratio);

  const width = canvas.width / ratio;
  const height = canvas.height / ratio;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#f8fbff";
  ctx.fillRect(0, 0, width, height);

  drawGrid(ctx, width, height);
  const map = buildProvenanceMap();
  if (width < 760) {
    drawVerticalMap(ctx, width, height, map);
    renderMapInsights(map);
    return;
  }
  const lanes = [
    { key: "observations", label: "Observations", color: "#1677c7" },
    { key: "memories", label: "Memory", color: "#008f9c" },
    { key: "steps", label: "Trajectory", color: "#6f5bd6" },
    { key: "score", label: "Score", color: "#248a5b" },
    { key: "policies", label: "Policies", color: "#c87808" },
  ];
  const margin = 24;
  const laneGap = 14;
  const laneWidth = (width - margin * 2 - laneGap * (lanes.length - 1)) / lanes.length;
  const headerY = 24;
  const cardY = 72;
  const cardHeight = Math.max(72, Math.min(96, (height - 132) / 3));
  const lanePositions = {};

  lanes.forEach((lane, laneIndex) => {
    const x = margin + laneIndex * (laneWidth + laneGap);
    lanePositions[lane.key] = { x, width: laneWidth, color: lane.color };
    drawLaneHeader(ctx, x, headerY, laneWidth, lane.label, lane.color);
    const items = map[lane.key];
    items.slice(0, 3).forEach((item, itemIndex) => {
      const y = cardY + itemIndex * (cardHeight + 12);
      drawMapCard(ctx, x, y, laneWidth, cardHeight, item, lane.color);
    });
  });

  drawConnectors(ctx, lanePositions, cardY, cardHeight);
  renderMapInsights(map);
}

function drawVerticalMap(ctx, width, height, map) {
  const lanes = [
    { key: "observations", label: "Observations", color: "#1677c7" },
    { key: "memories", label: "Memory", color: "#008f9c" },
    { key: "steps", label: "Trajectory", color: "#6f5bd6" },
    { key: "score", label: "Score", color: "#248a5b" },
    { key: "policies", label: "Policies", color: "#c87808" },
  ];
  const margin = 18;
  const rowHeight = Math.max(82, (height - margin * 2 - 36) / lanes.length);
  lanes.forEach((lane, index) => {
    const y = margin + index * rowHeight;
    const item = map[lane.key][0] || { title: lane.label, body: "No signal", meta: "" };
    drawLaneHeader(ctx, margin, y, width - margin * 2, lane.label, lane.color);
    drawMapCard(ctx, margin, y + 42, width - margin * 2, Math.min(78, rowHeight - 50), item, lane.color);
    if (index < lanes.length - 1) {
      const centerX = width / 2;
      const startY = y + Math.min(78, rowHeight - 50) + 45;
      const endY = y + rowHeight - 4;
      ctx.strokeStyle = "rgba(0, 143, 156, 0.42)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(centerX, startY);
      ctx.lineTo(centerX, endY);
      ctx.stroke();
      ctx.fillStyle = "rgba(0, 143, 156, 0.74)";
      ctx.beginPath();
      ctx.moveTo(centerX, endY + 4);
      ctx.lineTo(centerX - 5, endY - 4);
      ctx.lineTo(centerX + 5, endY - 4);
      ctx.closePath();
      ctx.fill();
    }
  });
}

function buildProvenanceMap() {
  const observations = (state.data.observations || []).slice(0, 3).map((item) => ({
    title: item.source || item.type,
    body: item.content,
    meta: item.type,
  }));
  const memories = (state.data.memories || []).slice(0, 3).map((item) => ({
    title: item.memory_type,
    body: item.text,
    meta: `${Number(item.confidence || 0).toFixed(2)} confidence`,
  }));
  const activeRun = (state.data.traces || []).find((run) => run.run_id === state.activeRun) || (state.data.traces || [])[0];
  const steps = activeRun ? [
    { title: activeRun.agent_id, body: activeRun.goal, meta: activeRun.status },
    ...((latestScore()?.root_cause_hypotheses || []).slice(0, 2).map((cause) => ({
      title: cause.kind,
      body: cause.detail || cause.step_id,
      meta: `${Number(cause.confidence || 0).toFixed(2)} confidence`,
    }))),
  ] : [];
  const score = latestScore();
  const scoreItems = score ? [
    { title: "Utility", body: Number(score.utility || 0).toFixed(2), meta: score.run_id },
    { title: "Grounding", body: `${Math.round(Number(score.metrics?.evidence_grounding || 0) * 100)}% evidence`, meta: "metric" },
    { title: "Recovery", body: `${Math.round(Number(score.metrics?.recovery_quality || 0) * 100)}% recovery`, meta: "metric" },
  ] : [];
  const policies = (state.data.policies || []).slice(0, 3).map((item) => ({
    title: item.kind,
    body: item.title,
    meta: `${Number(item.confidence || 0).toFixed(2)} confidence`,
  }));
  return { observations, memories, steps, score: scoreItems, policies };
}

function drawGrid(ctx, width, height) {
  ctx.save();
  ctx.strokeStyle = "rgba(16, 24, 40, 0.05)";
  ctx.lineWidth = 1;
  for (let x = 0; x < width; x += 28) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }
  for (let y = 0; y < height; y += 28) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
  ctx.restore();
}

function drawLaneHeader(ctx, x, y, width, label, color) {
  roundRect(ctx, x, y, width, 34, 9);
  ctx.fillStyle = "rgba(255, 255, 255, 0.88)";
  ctx.fill();
  ctx.strokeStyle = "rgba(16, 24, 40, 0.08)";
  ctx.stroke();
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(x + 18, y + 17, 5, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#111827";
  ctx.font = "700 13px system-ui, sans-serif";
  ctx.fillText(label, x + 31, y + 22);
}

function drawMapCard(ctx, x, y, width, height, item, color) {
  roundRect(ctx, x, y, width, height, 12);
  ctx.fillStyle = "rgba(255, 255, 255, 0.93)";
  ctx.fill();
  ctx.strokeStyle = "rgba(16, 24, 40, 0.1)";
  ctx.stroke();
  ctx.fillStyle = color;
  roundRect(ctx, x, y, 5, height, 5);
  ctx.fill();
  ctx.fillStyle = "#111827";
  ctx.font = "700 12px system-ui, sans-serif";
  wrapText(ctx, item.title || "Item", x + 14, y + 20, width - 24, 14, 1);
  ctx.fillStyle = "#4b5563";
  ctx.font = "12px system-ui, sans-serif";
  wrapText(ctx, item.body || "", x + 14, y + 42, width - 24, 15, 2);
  ctx.fillStyle = "#657184";
  ctx.font = "700 10px system-ui, sans-serif";
  wrapText(ctx, item.meta || "", x + 14, y + height - 12, width - 24, 12, 1);
}

function drawConnectors(ctx, lanes, cardY, cardHeight) {
  const ordered = ["observations", "memories", "steps", "score", "policies"];
  ctx.save();
  ctx.lineWidth = 2;
  ordered.slice(0, -1).forEach((key, index) => {
    const from = lanes[key];
    const to = lanes[ordered[index + 1]];
    if (!from || !to) return;
    const y = cardY + cardHeight / 2;
    const startX = from.x + from.width + 4;
    const endX = to.x - 4;
    const midX = (startX + endX) / 2;
    ctx.strokeStyle = "rgba(0, 143, 156, 0.42)";
    ctx.beginPath();
    ctx.moveTo(startX, y);
    ctx.bezierCurveTo(midX, y, midX, y, endX, y);
    ctx.stroke();
    ctx.fillStyle = "rgba(0, 143, 156, 0.74)";
    ctx.beginPath();
    ctx.moveTo(endX, y);
    ctx.lineTo(endX - 7, y - 5);
    ctx.lineTo(endX - 7, y + 5);
    ctx.closePath();
    ctx.fill();
  });
  ctx.restore();
}

function wrapText(ctx, text, x, y, maxWidth, lineHeight, maxLines) {
  const words = String(text || "").split(/\s+/).filter(Boolean);
  let line = "";
  let lineCount = 0;
  for (const word of words) {
    const next = line ? `${line} ${word}` : word;
    if (ctx.measureText(next).width > maxWidth && line) {
      ctx.fillText(lineCount + 1 === maxLines ? `${line.slice(0, Math.max(0, line.length - 3))}...` : line, x, y);
      line = word;
      y += lineHeight;
      lineCount += 1;
      if (lineCount >= maxLines) return;
    } else {
      line = next;
    }
  }
  if (line && lineCount < maxLines) {
    ctx.fillText(line, x, y);
  }
}

function roundRect(ctx, x, y, width, height, radius) {
  const r = Math.min(radius, width / 2, height / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + width, y, x + width, y + height, r);
  ctx.arcTo(x + width, y + height, x, y + height, r);
  ctx.arcTo(x, y + height, x, y, r);
  ctx.arcTo(x, y, x + width, y, r);
  ctx.closePath();
}

function renderMapInsights(map) {
  const experience = latestQuantumReport()?.experience_state;
  const insights = [
    ["Source", map.observations[0]?.title || "none"],
    ["Memory Route", map.memories[0]?.title || "none"],
    ["State Gap", experience ? Number(experience.function_experience_gap || 0).toFixed(2) : "none"],
    ["Pattern", experience?.state_label?.replaceAll("_", " ") || map.steps[1]?.title || "healthy trajectory"],
  ];
  byId("map-insights").innerHTML = insights.map(([label, value]) => `
    <div class="map-insight">
      <span>${svgText(label)}</span>
      <strong>${svgText(value)}</strong>
    </div>
  `).join("");
}

async function startRun() {
  const payload = {
    ...scope(),
    agent_id: byId("agent-id").value.trim() || "planner_agent",
    goal: byId("run-goal").value.trim() || "Improve trajectory quality.",
  };
  const run = await api("/traces/start", { method: "POST", body: payload });
  state.activeRun = run.run_id;
  toast(`Started ${run.run_id}`);
  await refresh();
}

async function addStep() {
  if (!state.activeRun) {
    await startRun();
  }
  const payload = {
    run_id: state.activeRun,
    kind: byId("step-kind").value,
    source: byId("step-source").value.trim() || byId("agent-id").value.trim(),
    status: byId("step-status").value,
    input: byId("step-input").value,
    output: byId("step-output").value,
    capture_observation: true,
  };
  await api("/traces/step", { method: "POST", body: payload });
  toast("Step recorded");
  await refresh();
}

async function captureObservation() {
  const payload = {
    observations: [{
      ...scope(),
      run_id: state.activeRun,
      type: byId("obs-type").value,
      source: byId("obs-source").value.trim() || "operator",
      content: byId("obs-content").value.trim(),
    }],
  };
  await api("/observations", { method: "POST", body: payload });
  toast("Observation captured");
  await refresh();
}

async function extractMemory() {
  const payload = { ...scope(), run_id: state.activeRun, limit: 60 };
  const result = await api("/memories/extract", { method: "POST", body: payload });
  toast(`Stored ${result.stored.length} memories`);
  await refresh();
}

async function searchMemory() {
  const result = await api("/memories/search", {
    method: "POST",
    body: { ...scope(), query: byId("memory-query").value.trim(), limit: 12 },
  });
  renderMemories(result.results);
  toast(`${result.results.length} memories ranked`);
}

async function scoreRun() {
  if (!state.activeRun) throw new Error("No active run");
  const result = await api("/trajectories/score", { method: "POST", body: { run_id: state.activeRun } });
  toast(`Utility ${result.utility}`);
  await refresh();
}

async function runCounterfactuals() {
  if (!state.activeRun) throw new Error("No active run");
  const result = await api("/trajectories/counterfactuals", {
    method: "POST",
    body: { run_id: state.activeRun },
  });
  state.counterfactuals = result.counterfactuals || [];
  renderCounterfactuals();
  toast(`${state.counterfactuals.length} step effects estimated`);
}

async function synthPolicy() {
  const payload = state.activeRun ? { run_id: state.activeRun } : scope();
  const result = await api("/policies/synthesise", { method: "POST", body: payload });
  toast(`Stored ${result.stored.length} policies`);
  await refresh();
}

async function eraseSubject() {
  scope();
  if (!window.confirm(`Erase all local data for ${state.subject}?`)) return;
  const result = await api(`/subjects/${encodeURIComponent(state.subject)}?tenant_id=${encodeURIComponent(state.tenant)}`, {
    method: "DELETE",
  });
  state.activeRun = null;
  state.counterfactuals = [];
  toast(`Erased ${result.subject_id}`);
  await refresh();
}

function bind(id, event, handler) {
  byId(id).addEventListener(event, async () => {
    try {
      await handler();
    } catch (error) {
      toast(error.message);
      console.error(error);
    }
  });
}

bind("refresh", "click", refresh);
bind("start-run", "click", startRun);
bind("add-step", "click", addStep);
bind("capture-observation", "click", captureObservation);
bind("extract-memory", "click", extractMemory);
bind("search-memory", "click", searchMemory);
bind("score-run", "click", scoreRun);
bind("counterfactuals", "click", runCounterfactuals);
bind("quantum-interpret", "click", quantumInterpret);
bind("synth-policy", "click", synthPolicy);
bind("erase-subject", "click", eraseSubject);

window.addEventListener("resize", () => {
  if (state.data) renderGraph();
});

refresh().catch((error) => toast(error.message));
