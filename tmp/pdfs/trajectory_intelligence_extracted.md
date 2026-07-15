# Extracted text: Trajectory Intelligence.pdf

Pages: 18



--- PAGE 1 ---

Trajectory Intelligence
Executive Summary
The context behind this report is straightforward: Supermemory demonstrated that investors will fund
AI memory infrastructure when it looks like a reusable platform rather than a one-off application.
TechCrunch reported that Supermemory raised a $2.6 million seed round led by Susa Ventures, with
participation from Jeff Dean and other senior AI operators, while Supermemory’s own docs and repo
position it as a long-term and short-term memory and context stack for AI agents, including memory
extraction, user profiles, multimodal ingestion, connectors, and hybrid retrieval. 1
The deeper conclusion from the literature is that memory alone is becoming table stakes. Recent
surveys describe agent memory as a full write–manage–read lifecycle and decompose systems into
representation, extraction, retrieval/routing, and maintenance modules. At the same time, newer work
has moved beyond “can the agent recall facts?” toward “can the system explain, evaluate, improve, and
debug its own trajectories?” That shift is visible in recent memory surveys, provenance surveys,
trajectory-aware evaluation papers, and failure-attribution work. 2
Based on your previously described Mind Matters stack, you already have a strong substrate for this
category: LangMem for extraction and long-term learning primitives, SQLAlchemy for typed durable
persistence, Neo4j for relationship-heavy graph memory and traversal, and Qdrant for filterable vector
retrieval and hybrid ranking. Those components map closely to the leading patterns in LangMem,
graph-memory systems, and hybrid vector/graph infrastructure. 3
The strategic judgement is therefore: build the company around Trajectory Intelligence, not around
memory APIs alone. The defensible layer is the one that turns observations, memory, graph structure,
provenance, and execution traces into measurable reasoning quality, auditability, counterfactual
diagnostics, and continuous agent improvement. That layer is far less commoditised than “store and
retrieve user facts,” and current literature repeatedly identifies it as a frontier rather than a solved
problem. 4
The Publication-Ready Article
Trajectory Intelligence is the next logical layer above AI memory. Memory systems solve an important
but incomplete problem: they let agents retain facts, preferences, and prior interactions across
sessions. Trajectory Intelligence goes further. It treats every agent run as a structured object made of
observations, tool calls, state transitions, retrieved memories, intermediate claims, environmental
feedback, and final outcomes. The product’s job is not merely to remember the past, but to explain why
the agent acted as it did, determine what evidence or memory influenced the decision, identify where
the trajectory failed or recovered, and convert those lessons into better future behaviour. That framing
is increasingly aligned with the research frontier, which now emphasises process-level accountability,
evidence tracing, trajectory-aware evaluation, and failure attribution rather than outcome-only
accuracy. 5
Why does this matter now? Because memory infrastructure is maturing quickly. Supermemory positions
itself as a full context stack with memory extraction, user profiles, multimodal ingestion, connectors,
1


--- PAGE 2 ---

and semantic understanding graphs. Letta operationalises stateful agents through memory blocks,
message persistence, and archival vector memory. Mem0 focuses on scalable long-term memory with
extraction, consolidation, and graph-enhanced memory. Zep and Graphiti push temporal knowledge
graphs with provenance and historical validity windows. In other words, the market is already filling in
the lower layer. What remains comparatively open is the upper layer that scores, diagnoses, and
improves trajectories across single-agent and multi-agent systems. 6
A Trajectory Intelligence product would serve teams deploying agents in settings where traceability,
reproducibility, safety, and longitudinal optimisation matter more than raw novelty. Healthcare
copilots need to show which observations and historical states influenced a recommendation. Coding
agents need to explain which retrieved prior fix or tool result changed the repair plan. Customer-
support agents need consistent preference memory plus auditable decision history. Research agents
need trajectory-aware quality metrics rather than only answer correctness. Multi-agent systems need
provenance, localisation of failure, replay budgeting, and credit assignment across collaborating roles.
Recent benchmarks and surveys make clear that these are not edge cases; they are becoming the
default hard problems for production agents. 7
The core components of such a product are now visible. It needs a persistent memory substrate that
supports episodic, semantic, and procedural memory; a graph layer for relationships, temporal
updates, and provenance; a vector layer for retrieval under scale; an observation model that converts
raw interactions into typed events; a trace ledger that records every step of execution; a scoring engine
that measures utility, grounding, and efficiency across trajectories; and a reflection layer that can write
back reusable strategies, guardrails, and preference updates. This is not a speculative stack. It is a
synthesis of what recent systems have independently shown: graph memory improves structure and
temporal reasoning, selective memory reduces latency and token cost, observation-centric memory can
preserve cacheability, and trajectory-derived learning can improve future task performance. 8
The product spec therefore becomes clear. Build an infrastructure service that sits between the agent
runtime and the model. It ingests messages, tool results, environment observations, and user feedback;
extracts memory candidates and graph updates; stores evidence and provenance; retrieves context at
runtime; scores each execution path; and periodically distils successful and failed trajectories into
reusable policies. In a strong implementation, memory is no longer just “what happened before.” It
becomes the substrate from which the system learns how to reason better next time. That is the
difference between a memory product and a Trajectory Intelligence platform. 9
State of the Art Review
The literature has consolidated around a few strong ideas. First, modern agent memory is no longer
treated as “long chat history”; recent surveys model it as a write–manage–read loop with explicit
maintenance and lifecycle governance, while a newer data-management study decomposes systems
into storage/representation, extraction, retrieval/routing, and maintenance. Second, graph-based
memory has become a major 2025–2026 direction because it can encode relations, temporality, and
provenance more explicitly than flat vector stores. Third, the frontier is rapidly shifting from recall
quality alone toward process supervision: trajectory-aware evaluation, evidence tracing, failure
attribution, and self-improving memory generated from execution traces. 10
Benchmarking has become more nuanced for the same reason. LoCoMo stresses very long multi-
session dialogue with temporal and causal dynamics; LongMemEval measures extraction, multi-session
reasoning, temporal reasoning, knowledge updates, and abstention; ConvoMem expands statistical
coverage to 75,336 QA pairs; MemoryAgentBench evaluates accurate retrieval, test-time learning,
2


--- PAGE 3 ---

long-range understanding, and selective forgetting; BEAM pushes long-term memory out to multi-
domain dialogues up to 10 million tokens; and STATE-Bench asks whether agents truly improve with
experience on realistic enterprise tasks. The implication for product design is important: there is no
single SOTA number that settles architecture quality across all workloads. 11
What the strongest systems are converging on is also clearer than it was a year ago. MemGPT/Letta
popularised memory tiers and OS-style paging. Mem0 made selective extraction and consolidation a
practical production story. Zep/Graphiti showed that temporal context graphs can win on enterprise-
style memory workloads. A-Mem, Hindsight, and GAM all argue that structure and memory evolution
matter more than naive top-k recall. Mastra’s observational memory shows that some of the best
current results come from treating observations as stable compressed state rather than constantly re-
querying unaudited long context. And several 2026 papers explicitly pull trajectory analysis into
memory learning itself. 12
Annotated bibliography of the most decision-relevant recent papers
MemGPT: Towards LLMs as Operating Systems — Charles Packer et al., 2023. This is the foundational
systems paper for modern agent memory. It reframes LLM memory limits as an OS-style virtual
memory problem, with tiered storage and paging between context and external memory. The paper
also introduced the Deep Memory Retrieval task, which became an early benchmark for conversational
consistency. Methods: memory tiers, interrupts, external recall. Datasets and metrics: document
analysis task and DMR consistency. Primary sources: 13
Evaluating Very Long-Term Conversational Memory of LLM Agents — Adyasha Maharana et al.,
2024. This paper introduced LoCoMo, one of the most important benchmarks in the space. It builds very
long conversations, averaging about 300 turns and roughly 9K tokens across up to 35 sessions, and
evaluates question answering, event summarisation, and multimodal dialogue generation. The paper is
especially useful because it highlights that long context and vanilla RAG still lag human performance on
long-range temporal and causal understanding. Methods: benchmark construction from personas and
temporal event graphs. Datasets and metrics: LoCoMo QA, summarisation, multimodal generation.
Primary sources: 14
LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory — Di Wu et al.,
2024. LongMemEval is the most useful benchmark if the product target is persistent assistant memory
rather than generic long-context QA. It evaluates five core abilities: information extraction, multi-
session reasoning, temporal reasoning, knowledge updates, and abstention. That makes it especially
relevant for user-profile memory and continuity across conversations. Methods: attribute-controlled,
timestamped chat-history construction. Datasets and metrics: 500 questions over multi-session chat
histories; category-wise memory accuracy. Primary sources: 15
Zep: A Temporal Knowledge Graph Architecture for Agent Memory — Preston Rasmussen et al.,
2025. Zep is one of the clearest papers showing why temporal graphs matter in production-like settings.
It couples a managed memory layer with Graphiti, a graph engine that tracks changing facts over time
and preserves provenance. In the paper, Zep beats MemGPT on DMR and reports substantial gains on
LongMemEval along with major latency reductions, which makes it one of the strongest references for
graph-first memory infrastructure. Methods: temporal knowledge graph, validity windows, provenance,
hybrid retrieval. Datasets and metrics: DMR and LongMemEval; 94.8 vs 93.4 on DMR and accuracy gains
up to 18.5 with large latency reductions. Primary sources: 16
3


--- PAGE 4 ---

Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory — Prateek Chhikara
et al., 2025. Mem0 is the most production-minded paper in the group. It argues for dynamic extraction,
consolidation, and retrieval of salient memory and reports strong performance on LoCoMo, including
major reductions in p95 latency and token cost relative to full-context baselines. The graph-memory
variant adds a smaller extra gain, which is useful evidence that graph structure helps but often on top
of a good selective-memory core rather than instead of it. Methods: selective memory extraction,
consolidation, graph-memory extension. Datasets and metrics: LoCoMo; 26% relative improvement in
LLM-as-a-judge over OpenAI baseline, ~2% further gain with graph memory, 91% lower p95 latency and
>90% token savings versus full context. Primary sources: 17
In Prospect and Retrospect: Reflective Memory Management for Long-Term Personalized
Dialogue Agents — Zhen Tan et al., ACL 2025. RMM is important because it attacks two real production
pathologies: rigid summarisation granularity and rigid retrieval. Its “prospective reflection” decomposes
conversation into topic memory for future use, while “retrospective reflection” refines retrieval online
using attribution signals emitted during generation. The paper reports more than 10% accuracy
improvement over a no-memory baseline on LongMemEval and more than 5% over strong baselines
across MSC and LongMemEval. Methods: topic-based memory decomposition plus online retrieval
refinement with RL. Datasets and metrics: MSC and LongMemEval; retrieval and response-generation
improvements. Primary sources: 18
A-MEM: Agentic Memory for LLM Agents — Wujiang Xu et al., 2025. A-MEM is one of the most
relevant papers for “memory evolution.” Instead of treating stored items as static fragments, it uses
Zettelkasten-inspired notes with attributes, dynamic linking, and memory updates triggered by new
experiences, so old memory can change when new evidence arrives. The evaluation emphasises long-
term conversational data from LoCoMo across six foundation models and argues that dynamic linking
plus memory evolution creates more organised memory representations than baseline memory stores.
Methods: structured notes, dynamic link generation, memory evolution. Datasets and metrics: LoCoMo-
based long-term conversations; six foundation models and six metrics, plus embedding-structure
analysis. Primary sources: 19
AriGraph: Learning Knowledge Graph World Models with Episodic Memory for LLM Agents — Petr
Anokhin et al., IJCAI 2025. AriGraph is the strongest bridge between graph memory and agent planning.
It integrates semantic and episodic memory inside a memory graph and uses that structure during
exploration and action in partially observable environments. The paper reports strong gains over full
history, summarisation, RAG, Reflexion, Simulacra, and RL baselines in TextWorld and NetHack, while
also staying competitive on multi-hop QA. Methods: semantic triplets, episodic vertices/edges, planning
plus ReAct-based action selection. Datasets and metrics: TextWorld, NetHack, multi-hop QA. Primary
sources: 20
Hindsight is 20/20: Building Agent Memory that Retains, Recalls, and Reflects — Chris Latimer et
al., 2025. Hindsight is one of the strongest recent architectural papers because it formalises memory as
four logical networks: world facts, agent experiences, synthesised summaries, and evolving beliefs. That
separation better supports explainability than monolithic memory stores because the system can
distinguish evidence from inference. The paper reports very strong LongMemEval and LoCoMo results,
including 83.6% with an open 20B model and 91.4% on LongMemEval at larger scale. Methods: four-
network structured memory with retain/recall/reflect operations. Datasets and metrics: LongMemEval
and LoCoMo. Primary sources: 21
ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory — Samira Ouyang et al., ICLR
2026 poster. ReasoningBank matters because it stores reasoning derived from both successful and
failed trajectories rather than only storing recalled facts. Google Research reports that it improves
4


--- PAGE 5 ---

success rates on WebArena and SWE-Bench-Verified while reducing unnecessary execution steps, which
directly supports the product thesis that the moat is in trajectory-derived learning rather than plain
recall. Methods: reasoning-memory distillation from success and failure trajectories; test-time scaling
with memory. Datasets and metrics: WebArena and SWE-Bench-Verified; higher success and fewer
execution steps. Primary sources: 22
Trajectory-Informed Memory Generation for Self-Improving Agent Systems — Gaodan Fang et al.,
2026. This paper is the closest academic match to the product concept in this report. It explicitly extracts
learnings from execution trajectories, attributes which decisions caused failures or recoveries, and
stores strategy, recovery, and optimisation tips for future retrieval. On AppWorld it reports up to 14.3
percentage-point gains overall and 28.5 points on complex tasks, which is a direct signal that trajectory
memory can materially improve downstream agent quality. Methods: trajectory intelligence extractor,
decision attribution, contextual learning generator, adaptive retrieval. Datasets and metrics: AppWorld;
scenario goal completion improvements. Primary sources: 23
Towards Autonomous Memory Agents — Xinle Wu et al., 2026. U-Mem is important because it turns
memory from a passive store into an active learner. Instead of only writing whatever happened to
appear in the conversation, it uses a cost-aware knowledge extraction cascade and semantic-aware
Thompson sampling to decide when to seek more evidence and how to balance exploration versus
exploitation. That directly informs any product ambition around active memory curation and
autonomous knowledge growth. Methods: cost-aware extraction cascade, semantic-aware Thompson
sampling. Datasets and metrics: HotpotQA and AIME25; reported gains of 14.6 points and 7.33 points
respectively. Primary sources: 24
TRACE: Trajectory-Aware Comprehensive Evaluation for Deep Research Agents — Yanyu Chen et al.,
2026. TRACE is not a memory paper, but it is crucial for product design because it codifies what process-
level evaluation should look like when outcome-only scores are misleading. Its hierarchical trajectory
utility function incorporates efficiency and evidence grounding rather than only final answer accuracy.
That gives a direct template for one of the most defensible parts of a Trajectory Intelligence product:
the evaluation layer. Methods: hierarchical trajectory utility, scaffolded capability assessment. Datasets
and metrics: DeepResearch-Bench with controllable complexity. Primary sources: 25
Comparative Landscape
The table below compares the systems most relevant to a founder or CTO deciding whether to build
“memory infrastructure” or a higher-order “trajectory intelligence” platform. Where capabilities are
marketing-claimed rather than independently reproduced, the table treats them as source-reported,
not universally established facts.
5


--- PAGE 6 ---

Primary
Memory types Retrieval Online Trajectory Explainability / Production Source /
System storage Graph support Multimodality License
supported method learning analysis provenance readiness link
model
Moderate;
graph
Managed Yes, semantic Context
Short-term + Yes: text, relationships
memory understanding fetch from Yes, updates/ Limited
long-term conversations, exposed, but
Supermemory graph + graph and learned contradictions/ publicly High MIT repo 26
user memory, files, images, full trace/
semantic relationship graph + forgetfulness documented
profiles, RAG videos provenance
index types search
model not
central in docs
In-context Tool-based Moderate;
memory Stateful semantic clear
blocks + agent store Limited native Mostly text/ archival Yes, through separation of
Letta /
archival vector + vector DB graph doc oriented search + agent tools Limited blocks, High Apache-2.0 27
MemGPT
memory + archival emphasis in docs pinned and edits passages,
message memory memory messages,
history blocks runs/steps
User/session/ Moderate;
agent Selective Mostly text- structured
Partial / Extract–
memory; memory centric in memory, but
Mem0 optional graph consolidate– Yes Limited High Apache-2.0 28
graph- store, graph paper and trajectory
memory retrieve
memory extension repo explanation is
variant not core
High for
Temporal Text + Hybrid Strong
Long-term Zep, Zep
knowledge structured/ semantic + Yes, provenance
temporal medium- managed;
Zep / Graphiti graph with Strong unstructured keyword + incremental Limited and temporal 29
context high for Graphiti
provenance enterprise graph graph updates validity
memory Graphiti Apache-2.0
episodes data traversal windows
OSS
Moderate;
Long-term Works with
Search tools useful for
memory + any store; Mostly text/ Partial, via
Storage- + procedural Medium-
LangMem behaviour/ native conversation Yes, strongly behaviour MIT 30
agnostic background memory and high
prompt LangGraph primitives optimisation
consolidator behaviour
optimisation integration
refinement
Self-hosted Graph
Persistent Stronger than
graph + Yes, repo reasoning +
long-term Yes, feedback/ average; OTEL
vector + claims vector
Cognee memory + Strong context Partial collector and Medium Apache-2.0 31
relational/ multimodal search +
knowledge learning audit traits
provenance support ontology
graph mentioned
layers grounding
6


--- PAGE 7 ---

Primary
Memory types Retrieval Online Trajectory Explainability / Production Source /
System storage Graph support Multimodality License
supported method learning analysis provenance readiness link
model
Moderate;
Attribute-
Long-term structure
rich notes + Similarity + Yes, explicit
conversational Yes, dynamic more Research /
A-Mem embeddings Text-focused structured memory Limited MIT 19
memory with links transparent early OSS
via linking evolution
evolving notes than plain
ChromaDB
vector stores
Good
Semantic Partial
Semantic + Knowledge- Yes, structural Unspecified
Text search + through
AriGraph episodic graph world Strong environment- explainability Research in cited 20
environments episodic planning/
memory model driven updates inside graph source
search action loops
world model
Stronger than
Structured Partial to
Facts, Retain– average
multi- Implicit strong;
experiences, Text-focused recall–reflect because Medium-
Hindsight network structured Yes reflection MIT 32
summaries, in sources over typed evidence and high
memory network over
beliefs networks belief are
bank trajectories
separated
Stable Limited
Observations In-context
context directly, but Moderate;
Mastra + raw Text/tool observations Unspecified
window with No graph-first observation very Medium-
Observational messages + results in rather than Yes in cited 33
observer/ model model is reproducible high
Memory reflected current docs heavy source
reflector trace- context state
observations retrieval
compression adjacent
Moderate to
Reasoning
Memory strong,
memory from No graph-first Memory- Unspecified
bank of because
ReasoningBank successful and emphasis in Unspecified aware test- Yes, core idea Strong Research in cited 22
reasoning stored units
failed cited sources time scaling source
items are reasoning
trajectories
patterns
Against that landscape, Mind Matters as you described it is already closer to the frontier than to
commodity memory tooling. LangMem gives you memory extraction and behaviour-optimisation
primitives; SQLAlchemy gives you a durable typed control plane; Neo4j is structurally well-suited for
relationship-heavy, traversal-heavy, and increasingly vector-aware memory; and Qdrant is built for
filterable HNSW indexing and hybrid retrieval. That combination is already consistent with the best
graph/vector memory patterns in the current literature. 34
What is still missing, relative to the strongest research angle, is not basic memory. It is the trajectory
layer: typed observations, provenance graphs, execution spans, policy learning from traces,
counterfactual diagnostics, and multi-agent credit assignment. Those are precisely the places where the
literature is active and where product competition is still thinner. 35
7


--- PAGE 8 ---

Reference Architectures
The three reference designs below synthesise how the field is converging. The first is the memory-
infrastructure pattern visible in Supermemory, Mem0, Letta, and Zep/Graphiti. The second adds the
trajectory layer that newer provenance, evaluation, and self-improvement papers motivate. The third
maps those ideas onto the hybrid stack you described for Mind Matters. 36
Apps and agents
Ingestion and extraction
Memory normaliser
Document and connector
Episodic store Semantic store User profile store
index
Retrieval and routing layer
Context assembly
LLM / agent runtime
Writes back new memory
candidates
8


--- PAGE 9 ---

Agent runtime
Typed trace capture
Execution provenance
graph
Trajectory evaluator
Counterfactual analysis Failure attribution
Observation extractor Policy sy a n n t d he s s tr is ategy Guardrails and alerts
Episodic memory Semantic memory Procedural memory
Context router
Prompt / tool context
Conversations, tools,
external events
LangMem extraction and
OpenTelemetry trace
background memory
spans
management
SQLAlchemy control plane Neo4j relationship and Trace store and
Qdrant vector memory
/ typed records behaviour graph provenance ledger
Memory governance and Graph traversal / temporal Trajectory scoring and
Semantic retrieval
lifecycle / relationship retrieval debugging
Policy updates, prompts,
Context builder
agent feedback
Mind Matters agents
Neo4j’s current platform supports expressive graph querying, traversal, and vector indexes, while
Qdrant is explicitly optimised for combining vector similarity with payload filters and hybrid dense/
sparse fusion. That makes the pairing technically sound for a hybrid memory-and-trajectory stack:
Qdrant for semantic recall under latency constraints, Neo4j for path-dependent reasoning, temporal
relation updates, and provenance-heavy queries. 37
9


--- PAGE 10 ---

Product Blueprint
The most defensible version of this product is not “a memory API” and not “an agent framework.” It is a
system-of-intelligence layer that sits between agent runtimes and storage engines. Its job is to
convert raw execution into durable memory, typed observations, causal/provenance structure, and
optimisation signals. That framing aligns with where current research is heading: memory systems
increasingly need lifecycle governance, adaptive retrieval, evaluation beyond final correctness, and
structured trace analysis. 38
Moat-weighted component importance
10%
25%
10%
Trace provenance and auditability [25]
Observation ontology [20]
Trajectory evaluation metrics [20]
Memory evolution and governance [15]
15%
Graph and causal induction [10]
Retrieval and routing [10]
20%
20%
Core product modules
A usable v1 should expose six modules:
1. Observation Capture — ingest messages, tool calls, tool outputs, user signals, environment
observations, and model-internal decision metadata where available.
2. Memory Synthesis — derive episodic memory, semantic facts, preferences, and procedural
lessons from observations and traces.
3. Graph Intelligence — maintain temporal and relational structure, contradictions, staleness
windows, provenance edges, and entity evolution.
4. Trajectory Evaluation — score runs for grounding, efficiency, recovery behaviour, policy
adherence, and memory utility.
5. Optimisation Loop — write back successful strategies, anti-patterns, recovery hints, and routing
policies.
6. Governance Layer — manage deletion, forgetting, access control, retention, PHI scoping, and
tenant isolation. This module is not optional in healthcare or enterprise settings. 39
API surface
A realistic API surface would look like this:
• POST /observations — write one or more typed observations.
10


--- PAGE 11 ---

• POST /memories/extract — extract memory candidates from an observation batch or a
trace.
• POST /memories/search — retrieve episodic, semantic, profile, and procedural memory with
hybrid routing.
• POST /graphs/upsert — apply entity, relation, temporal, and provenance updates.
• POST /traces/start and POST /traces/step — record run-level and step-level spans.
• POST /trajectories/score — compute trajectory metrics for one run or an evaluation set.
• POST /trajectories/counterfactuals — evaluate “what if this step/tool/memory were
removed or changed?”
• POST /policies/synthesise — convert labelled or scored trajectories into procedural
memory or routing updates.
• DELETE /subjects/{id} — execute right-to-erasure / forgetting workflow across all stores.
These endpoints mirror where the field has landed: memory platforms already expose write/search/
update semantics, while the emerging opportunity is the layer above them that understands traces,
provenance, and optimisation. 40
Illustrative data schema
{
"observation_id": "obs_01",
"tenant_id": "tenant_a",
"subject_id": "user_42",
"run_id": "run_992",
"step_id": "step_07",
"timestamp": "2026-07-01T10:30:00+05:30",
"type": "tool_result",
"source": "calendar.lookup",
"content": "User missed therapy session for the third week in a row",
"entities": ["user_42", "therapy_session"],
"relations": [
{"from": "user_42", "type": "MISSED", "to": "therapy_session",
"valid_at": "2026-07-01"}
],
"labels": {
"clinical_relevance": 0.86,
"behavioural_signal": "avoidance_pattern"
},
"provenance": {
"parent_step_id": "step_06",
"tool_call_id": "tool_88"
}
}
{
"memory_id": "mem_5001",
"subject_id": "user_42",
"memory_type": "semantic",
"text": "User shows recurring avoidance patterns around weekly therapy
11


--- PAGE 12 ---

sessions",
"derived_from": ["obs_01", "obs_443", "obs_781"],
"confidence": 0.78,
"status": "active",
"expires_at": null,
"graph_refs": ["node:user_42", "node:therapy_session",
"edge:avoidance_pattern"],
"vector_ref": "qdrant:memories/5001"
}
{
"run_id": "run_992",
"agent_id": "planner_agent",
"trajectory_score": {
"goal_completion": 0.0,
"evidence_grounding": 0.91,
"memory_relevance": 0.82,
"step_efficiency": 0.61,
"policy_adherence": 0.95,
"recovery_quality": 0.34
},
"root_cause_hypotheses": [
{
"step_id": "step_05",
"kind": "memory_overgeneralisation",
"confidence": 0.73
}
]
}
Evaluation metrics
A serious product in this category needs two metric families.
The first is memory quality: retrieval precision/recall, temporal consistency, contradiction resolution
accuracy, staleness detection rate, profile consistency, and selective-forgetting correctness. These are
motivated by LongMemEval, MemoryAgentBench, RMM, and the latest system-level memory studies.
41
The second is trajectory quality: evidence grounding, tool-call validity, path efficiency, recovery rate
after error, counterfactual sensitivity, branch localisation accuracy, and minimum-guidance utility.
TRACE, the provenance survey, CTA, zero-replay debugging, and related failure-attribution work all point
toward these as product-grade metrics, not merely research niceties. 42
A practical internal scorecard should therefore include:
• Memory Usefulness Score = retrieval relevance × downstream answer lift.
• Trajectory Utility Score = goal completion + grounding + efficiency + recovery quality.
12


--- PAGE 13 ---

• Attribution Quality Score = whether the system correctly localised the high-effect step or
memory edge.
• Governance Score = deletion completeness, stale-memory suppression, PHI-minimisation
compliance.
That is materially more defensible than any leaderboard that reports only final answer accuracy. 43
Offline and online learning loops
The online loop should capture traces, write observations, retrieve context, and optionally synthesize
procedural hints in near-real time. The offline loop should replay or analyse traces in batches, train
retrieval/routing policies, generate anti-pattern libraries, refine the observation ontology, and
recalibrate trajectory scorers. This split matches both practical systems work and recent research: online
memory must stay fast, while deeper reflection, policy learning, and attribution can run asynchronously
under cost control. 44
Privacy, compliance, and safety
For any healthcare-adjacent version of this product, the compliance baseline is demanding. In the US,
the HIPAA Security Rule requires administrative, physical, and technical safeguards for ePHI, and HHS
explicitly frames business associates as directly responsible for safeguarding protected health
information under specific provisions. The HIPAA Privacy Rule and “minimum necessary” standard also
require that use and disclosure be limited to what is necessary for the intended purpose. 45
For European and UK-style privacy regimes, Article 5 principles require lawfulness, transparency, data
minimisation, and storage limitation, while Article 17 creates a right to erasure. For a memory platform,
that means memory lifecycle design is itself a compliance feature: you need subject-scoped deletion,
retention windows, stale-memory invalidation, and provenance strong enough to prove where personal
data lives and what was derived from it. 46
Operationally, treat provenance and tracing as compliance infrastructure, not only debugging
infrastructure. OpenTelemetry’s semantic conventions and trace model provide a sane baseline for
standardised execution spans and attributes. In practice, that means every tool call, retrieval, graph
update, evaluation pass, and policy write-back should be traceable at the span level with consistent
metadata. 47
Scalability and cost
Exact budget is unspecified, so the estimates below are architecture-level rather than vendor-quoted.
Scale tier Estimated scope Likely bottleneck Recommended pattern
Keep writes synchronous only for
Up to ~1M
LLM extraction and critical memories; batch graph
MVP memory items;
reflection cost consolidation; small Neo4j + Qdrant +
single region
Postgres footprint
Separate hot-path retrieval from
~1M–50M Retrieval routing and
offline maintenance; shard vector
Growth memory items; background
store before graph store; cache
multiple tenants maintenance
profile summaries
13


--- PAGE 14 ---

Scale tier Estimated scope Likely bottleneck Recommended pattern
Event-sourced trace ledger,
Provenance volume,
50M+ items; strict asynchronous compaction, entity-
Enterprise graph maintenance,
audit/compliance level retention policies, dedicated
deletion workflows
compliance pipeline
That sizing logic is supported by the overall direction of the literature even if the exact thresholds are
design estimates. Selective memory systems such as Mem0 report major token and latency savings
relative to full-context baselines, while observational-memory designs explicitly target stable, cacheable
context windows. In other words, the main economic battle is typically won or lost in what you choose to
retrieve and reprocess, not in raw storage alone. 48
Roadmap
Product roadmap from MVP to enterprise
Month1 Month2 Month3 Month4 Month6 Month9 Month12
Canonical Episodic/semantic Trajectoryscorerv1 Policysynthesis Counterfactual Domainontologies Enterpriselaunch
observation memoryextraction from traceauditing andcausal
schema successful/failed induction
Run/step traces Fullevaluationsuite
Hybridretrievaland dashboards Multi-agent
Tracecapturewith contextbuilder provenancegraph Healthcare-safe
OpenTelemetry Internalbenchmark Re m co e v m er o y r - y tip deploymentprofile ev C id o e m n p c l e ia p n a c c e ks
Deletionand harness Enterpriseauthand
Qdrant+Neo4j+ retentioncontrols tenancy SLAand
SQLAlchemy Routing-policy governance
baseline learning controls
Moat and Implementation Plan
The moat in this category is not the existence of memory. Too many competent teams can now
assemble memory from vector stores, graph stores, and LLM summarisation. The moat is the
structured intelligence that turns traces into repeatable improvement. Recent papers and surveys
repeatedly identify the hardest open problems as maintenance, dynamic updates, process-level
accountability, trajectory attribution, and experience utilisation rather than storage alone. 49
The most promising IP opportunities are these:
Opportunity Why it matters Evidence from literature
Most systems still rely on loosely
Graph-memory surveys and
typed facts or summaries. A domain-
systems like Cognee, Graphiti, and
Observation quality ontology for observations,
AriGraph all show the importance
ontology behaviours, intent, risk, and
of structure, but none has become
outcomes becomes a reusable asset
the universal ontology layer. 50
across products and models.
14


--- PAGE 15 ---

Opportunity Why it matters Evidence from literature
A proprietary but well-validated
Trajectory TRACE explicitly argues that
scoring stack can become the control
evaluation outcome-only scores create a
plane for agent quality, procurement,
metrics “high-score illusion.” 51
and governance.
This is one of the strongest moats
Counterfactual because it explains why a trace failed CTA and zero-replay debugging
trace analysis and which policy or memory should directly target this gap. 52
change.
Updating old memories when new A-Mem and Hindsight push in this
Memory evolution
evidence arrives is still immature and direction, but there is no dominant
algorithms
inconsistent across systems. standard. 53
Multi-agent systems will fail noisily AEL finds credit assignment to be a
Multi-agent credit unless someone can attribute gains major open challenge, and multi-
assignment and failures across roles, tools, and agent attribution papers reinforce
branches. that point. 54
If the product can infer not only
Emerging work around causal
Causal graph relations but causal pathways from
graphs, provenance, and graph-
induction from longitudinal observations, it moves
based memory suggests this is
observations from memory into reasoning
valuable but underdeveloped. 55
infrastructure.
That leads to a sharper company thesis: build the operating layer that lets agents remember,
justify, improve, and govern their own decisions over time. Supermemory-like memory
infrastructure can be one component of that stack, but the actual company moat lies above it. The
strongest wedge is not “best recall”; it is “best auditable improvement loop.” 56
Prioritised implementation plan
Phase Milestone Success criterion Open-source to reuse
OpenTelemetry semantic
Canonical Every run can be
conventions, SQLAlchemy,
Foundation observation and reconstructed as typed
existing agent runtime hooks
trace schema spans and events
57
Episodic + Stable retrieval lift on
LangMem, Qdrant, Neo4j,
Memory core semantic + profile LongMemEval/
benchmark repos 58
memory ConvoMem-style tasks
Temporal + Correct contradiction Neo4j, Graphiti patterns,
Graph
provenance handling and temporal LoCoMo/LongMemEval
intelligence
graph retrieval harnesses 59
Utility, Rankings correlate with
Trajectory TRACE-style metrics, provenance
grounding, human review and
scoring survey patterns 60
recovery metrics failure localisation
15


--- PAGE 16 ---

Phase Milestone Success criterion Open-source to reuse
ReasoningBank ideas, trajectory-
Repeated-task
Learning Policy synthesis informed memory generation,
improvement without
loop from traces RMM-style retrieval refinement
manual prompt tuning
61
Deletion, HIPAA/GDPR-aligned
Enterprise HHS guidance, GDPR principles,
retention, audit, data lifecycle and
hardening OpenTelemetry tracing 62
tenancy evidence packs
Team design
A credible first team for this company is small but specialised:
• Founding CTO / product architect — owns observation ontology, storage abstractions, and
evaluation strategy.
• Applied AI engineer — memory extraction, prompt/reflection systems, benchmark harnesses.
• Graph/data systems engineer — Neo4j/Qdrant/Postgres design, provenance graph, deletion/
retention flows.
• Agent evaluation engineer — trajectory scorer, counterfactual tools, dashboards, benchmark
automation.
• Security/compliance engineer or fractional lead — HIPAA/GDPR controls, audit trails, threat
modelling, BAAs where relevant.
That team mix follows directly from the shape of the problem. The hard part is not one clever prompt; it
is the integration of storage design, runtime instrumentation, evaluation science, and governance. 63
Final strategic conclusion
Based on the research and market signals, the strongest product to build is a hybrid memory +
trajectory intelligence platform. The memory portion is necessary but insufficient. Your existing Mind
Matters-style architecture already covers much of the lower layer. The part that can become proprietary,
valuable, and hard to copy is the system that turns longitudinal observations and execution traces into
provable reasoning quality, failure attribution, policy optimisation, and multi-agent governance. That is
where the literature is moving, where benchmarks are evolving, and where the commercial moat still
looks real. 64
1 A 19-year-old nabs backing from Google execs for his AI ...
https://techcrunch.com/2025/10/06/a-19-year-old-nabs-backing-from-google-execs-for-his-ai-memory-startup-
supermemory/?utm_source=chatgpt.com
2 9 10 Memory for Autonomous LLM Agents: Mechanisms ...
https://arxiv.org/html/2603.07670v1?utm_source=chatgpt.com
3 30 34 58 GitHub - langchain-ai/langmem · GitHub
https://github.com/langchain-ai/langmem
4 38 49 63 64 Are We Ready For An Agent-Native Memory System?
https://arxiv.org/abs/2606.24775?utm_source=chatgpt.com
5 [2606.04990] From Agent Traces to Trust: A Survey of ...
https://arxiv.org/abs/2606.04990?utm_source=chatgpt.com
16


--- PAGE 17 ---

6 26 36 56 Overview — What is Supermemory? - supermemory | Memory API for the AI era
https://supermemory.ai/docs/intro
7 Summary of the HIPAA Security Rule
https://www.hhs.gov/hipaa/for-professionals/security/laws-regulations/index.html?utm_source=chatgpt.com
8 16 29 Zep: A Temporal Knowledge Graph Architecture for Agent Memory
https://arxiv.org/abs/2501.13956?utm_source=chatgpt.com
11 14 Evaluating Very Long-Term Conversational Memory of LLM Agents
https://arxiv.org/abs/2402.17753?utm_source=chatgpt.com
12 13 MemGPT: Towards LLMs as Operating Systems
https://arxiv.org/abs/2310.08560?utm_source=chatgpt.com
15 41 LongMemEval: Benchmarking Chat Assistants on Long- ...
https://arxiv.org/abs/2410.10813?utm_source=chatgpt.com
17 28 44 48 Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory
https://arxiv.org/abs/2504.19413?utm_source=chatgpt.com
18 aclanthology.org
https://aclanthology.org/2025.acl-long.413.pdf
19 53 A-MEM: Agentic Memory for LLM Agents
https://arxiv.org/pdf/2502.12110
20 AriGraph: Learning Knowledge Graph World Models with Episodic Memory for LLM Agents
https://www.ijcai.org/proceedings/2025/0002.pdf
21 32 Hindsight is 20/20: Building Agent Memory that Retains, Recalls, and Reflects
https://arxiv.org/abs/2512.12818?utm_source=chatgpt.com
22 Scaling Agent Self-Evolving with Reasoning Memory
https://openreview.net/forum?id=jL7fwchScm&utm_source=chatgpt.com
23 35 39 Trajectory-Informed Memory Generation for Self-Improving Agent Systems
https://arxiv.org/abs/2603.10600?utm_source=chatgpt.com
24 Towards Autonomous Memory Agents
https://arxiv.org/abs/2602.22406?utm_source=chatgpt.com
25 42 43 51 60 TRACE: Trajectory-Aware Comprehensive Evaluation for Deep Research Agents
https://arxiv.org/abs/2602.21230?utm_source=chatgpt.com
27 40 Archival memory | Letta Docs
https://docs.letta.com/guides/core-concepts/memory/archival-memory/
31 GitHub - topoteretes/cognee: Cognee is the open-source AI memory platform for agents. Give your
AI agents persistent long-term memory across sessions with a self-hosted knowledge graph engine. ·
GitHub
https://github.com/topoteretes/cognee
33 Announcing Observational Memory | Mastra Blog
https://mastra.ai/blog/observational-memory
37 Vector indexes - Cypher Manual
https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/?utm_source=chatgpt.com
45 62 The Security Rule
https://www.hhs.gov/hipaa/for-professionals/security/index.html?utm_source=chatgpt.com
17


--- PAGE 18 ---

46 Art. 5 GDPR – Principles relating to processing of personal ...
https://gdpr-info.eu/art-5-gdpr/?utm_source=chatgpt.com
47 Trace semantic conventions
https://opentelemetry.io/docs/specs/semconv/general/trace/?utm_source=chatgpt.com
50 Graph-based Agent Memory: Taxonomy, Techniques, and Applications
https://arxiv.org/abs/2602.05665?utm_source=chatgpt.com
52 Counterfactual Trace Auditing of LLM Agent Skills
https://arxiv.org/abs/2605.11946?utm_source=chatgpt.com
54 AEL: Agent Evolving Learning for Open-Ended Environments
https://arxiv.org/abs/2604.21725?utm_source=chatgpt.com
55 CausalTrace: A Neurosymbolic Causal Analysis Agent for ...
https://arxiv.org/html/2510.12033v1?utm_source=chatgpt.com
57 OpenTelemetry semantic conventions 1.42.0
https://opentelemetry.io/docs/specs/semconv/?utm_source=chatgpt.com
59 GitHub - getzep/graphiti: Build Real-Time Knowledge Graphs for AI Agents · GitHub
https://github.com/getzep/graphiti
61 ReasoningBank: Enabling agents to learn from experience
https://research.google/blog/reasoningbank-enabling-agents-to-learn-from-experience/?utm_source=chatgpt.com
18