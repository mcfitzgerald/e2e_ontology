# Agent System Design — Intent

**Status:** Draft. Captures the intent of an agentic system that consumes this ontology as its source of truth. Not an implementation spec — a north star for the work that follows in a separate orchestrator repo. Reflects discussion through 2026-05-27.

**Purpose:** Memorialize what we are trying to build on top of the ontology, why, and the design principles that keep the system agentic rather than automated. Sets up the next round of ontology additions (new meta-constructs) and the build sketch for a Google ADK-based mockup that scales to a production architecture.

**Reads with:**

- `initial_design_draft.md` — ontology design and meta-model (authoritative for the ontology layer).
- `demo_narrative.md` — the promo whiplash narrative this system will execute as its proof point.
- `ontology_primer.md` — how agents read the ontology.

---

## 1. Thesis

A small set of **generic agents**, each instantiated from a role declared in the ontology, can coordinate complex cross-domain supply chain work by reading the ontology as a live map. The agents do not embed domain knowledge in code. Their identity, their event surface, their handoffs, their queries, their gates, and their lifecycles are all *derived* from the ontology at runtime.

The ontology is the world model. The agents reason over it. The orchestrator binds it to execution.

This thesis is what we are trying to prove. If it holds, the architecture generalizes: new domain content (a new role, a new flow, a new constraint) lands as an ontology edit, not a code change. New agents come online by being instantiated against a new role declaration. The system gets richer by *authoring*, not engineering.

**What we are explicitly trying to demonstrate:**

1. **Coordination is generic.** One agent template, parameterized by role, suffices for routing, handoffs, query-response, and context assembly across every domain in the ontology.
2. **Identity is structural.** An agent knows what it is, what arrives at it, what it can emit, what gates it, and what it can ask of others — purely from the ontology.
3. **Agency survives structure.** Adding structure to the ontology (Playbooks, Tools, criteria) does not collapse the system into automation. Agency lives in resolution-under-evidence, not in workflow steps.
4. **The orchestrator is dumb in the right way.** It validates, routes, persists state, evaluates axioms, surfaces decisions — but it does not know domain semantics. The ontology is the only source of domain truth.

**What we are not trying to demonstrate:**

- Best-in-class planning math. Specialist solvers (capacity, OTIF, inventory) sit behind tools. The agent's job is to know when to call them and how to integrate their outputs. Not to be them.
- A general-purpose multi-agent framework. We are not building MAS infrastructure; we are using Google ADK to host a thin generic-agent runtime tightly coupled to the ontology.
- Replacement of human judgment. `human_involvement` is a first-class concept in the ontology; the demo deliberately shows escalation to a human as a structurally identical event to any other handoff.

---

## 2. The design rule that keeps us agentic

A meta-principle that governs every addition to the ontology and every behavior of the agent runtime:

> **The ontology models the world and the action vocabulary. It never models the decision policy.**
>
> *World model:* what exists, what can happen, what state things can be in, what actions are available, what counts as viable for each path.
>
> *Decision policy:* what to do, in what order, under what conditions, with what preferences, with what fallback chain.

World modeling stays in the ontology. Policy modeling stays at runtime, resolved by the agent against assembled context.

Without this rule, the ontology drifts into being a workflow definition language — at which point we have automation, not agentic coordination. With this rule, structural richness in the ontology *enables* agency by giving the agent better typed evidence to reason over, rather than substituting for the reasoning.

**Authoring test for any ontology field:** can it be answered without referring to a runtime instance, a preference, or a ranking? If yes, it's world model — eligible for the ontology. If no, it's policy — belongs at runtime.

Examples:

| Field | World or policy? | Verdict |
|---|---|---|
| `source_role`, `target_role`, `quantum` on a flow | World | In ontology |
| `severity: blocking` on an axiom | World (this constraint must hold) | In ontology |
| `is_boundary: true` on a role | World | In ontology |
| `selects_one_of: [shift_to_coman, ...]` on a Playbook | World (these are the available paths) | In ontology |
| Advisory axiom `viable_promo_renegotiation` | World (definition of viable) | In ontology |
| Hypothetical: `prefer: shift_to_coman` | Policy (ranking) | Out |
| Hypothetical: `if otif_penalty > X then prefer Y` | Policy (decision rule) | Out |
| Hypothetical: `fallback_chain: [A, B, C]` | Policy (retry order) | Out |

This rule belongs in `CONTRIBUTING.md` as a hard constraint on contributions. It is the most important durable design discipline this system depends on.

---

## 3. Where agency irreducibly lives

To know whether we are still agentic at any point in the architecture, we have to name where agency *must* live and protect those moments from being structured away.

Four classes of moment that are irreducibly LLM-doing-real-work:

1. **Trade-off resolution under heterogeneous evidence.** Multiple typed responses arrive (financial exposure, qualitative relationship risk, cost premium, lead time). No formula combines them into a single rank. The agent has to weigh and choose.
2. **Composition across playbooks.** Two conflicts arrive in overlapping windows on related SKUs. No single playbook covers "two-at-once." The agent must compose, recognizing coupling that the ontology does not pre-declare.
3. **Handling incomplete or contradictory evidence.** A query returns a partial answer; two responses imply different paths. The agent has to decide whether to press, accept, or escalate.
4. **Recognizing when no playbook applies.** A novel signal arrives. The agent has to reason from the primitives of the ontology — events, roles, flows, axioms — without scaffolding.

Each of these is something a sufficiently elaborate rule engine *could* attempt — and would fail at, because the trade-offs and ambiguities are not formalizable. They are why the system needs an LLM at all. The architecture must ensure these moments are reachable and supported, not optimized away by over-structuring.

If a future ontology addition would let the orchestrator handle case (1) deterministically, we should refuse it. The Playbook construct in §6 is designed to scaffold (1) without resolving it; review every Playbook field with this filter.

---

## 4. Where this sits in the orchestrator landscape

"Orchestrator" is one of the most overloaded terms in current agentic AI discourse. Practitioners use it for at least three distinct layers, and architecture arguments frequently slide past each other because the word is doing too much work. Naming the layers explicitly clarifies what we're building and what we're not.

### 4.1 The three layers people call "orchestrator"

| Layer | Job | Representative tooling |
|---|---|---|
| **Reasoning / agent-graph** | Decides which agent acts next, how state flows between them, how decisions branch | LangGraph, AutoGen, CrewAI, OpenAI Agents SDK, Google ADK |
| **Coordination / messaging** | Carries typed events between agents; handles fan-out, back-pressure, decoupling | Event bus: Kafka, Pulsar, NATS, Redis Streams |
| **Durable execution** | Guarantees long-running, multi-step work survives crashes, restarts, and external failures via retries + idempotency | Temporal, Restate, Inngest, Dapr Workflows |

A production architecture commonly contains all three. The framing worth memorizing (from the 2026 LangGraph-vs-Temporal comparisons): *"LangGraph checkpointing protects against application-level failures; Temporal protects against infrastructure-level failures."* Different layers, both legitimately called orchestration.

### 4.2 Recognizable architectural patterns in the field

Synthesized across Confluent's event-driven patterns piece, Microsoft's multi-agent reference architecture, and the recent comparative literature (Codebridge 2026, Augment Code 2026, Anubhav 2026), six patterns recur:

| Pattern | Mechanism | When it fits |
|---|---|---|
| **Hierarchical / supervisor** | LLM "manager" agent delegates via tool calls (e.g., `transfer_to_agent`) | Task decomposition where routing decisions need judgment |
| **Sequential pipeline** | Agents run in fixed order; state piped through | Predictable workflows (research → draft → review) |
| **Peer-to-peer conversational** | Agents debate via group chat; speaker-selection picks turns | Open-ended ideation, debate, group decision-making |
| **Event-driven / message bus** | Stateless agents subscribe to typed events; bus carries handoffs | Distributed, async, loosely-coupled domain agents |
| **Blackboard / shared workspace** | Agents read & write a shared structured state; orchestrator picks the next actor based on state changes | Cross-domain coordination over typed shared context |
| **Actor model** | Each agent is an actor with a mailbox; isolated state, message-passing, location-transparent | High-scale, fault-isolated, distributable systems |

Worth flagging: AutoGen v0.4, Akka/Pekko, Temporal, and Flink Stateful Functions are all converging on actor semantics — independent failure isolation, mailboxes, location transparency. That is the strongest field signal about where multi-agent systems are heading at scale.

### 4.3 Where our approach sits

Our orchestrator is **event-sourced orchestrator-worker with blackboard-style shared state, anchored to a declarative ontology.** Walking the comparison:

- **Reasoning layer.** Generic agents per role; ADK as the agent runtime. **Not** LangGraph-style graph-in-code — our graph is in *ontology data*, interpreted at runtime. Closer in spirit to BPMN/workflow engines than to LangGraph, but we explicitly refuse to encode policy (§2 design rule), which keeps us out of the BPMN trap.
- **Coordination layer.** In-process Python dispatch for the POC; equivalent to an in-memory message bus. Our "flow" abstraction is already shaped like a typed event — putting Kafka or NATS underneath later requires no reshaping of the agent layer.
- **Durable execution layer.** Append-only JSONL event log for the POC. Naive but event-sourced — which is the discipline that matters.
- **State model.** Closest to **blackboard** — world state and event log together form the shared structured workspace; agents read from materialized views; the orchestrator picks the next actor based on flow `target_role`.

We are explicitly **not** doing:

- **Hierarchical LLM-supervised routing.** Rejected — routing must be deterministic from the ontology (§7/§8). We will not use ADK's `transfer_to_agent` or any LLM-driven dispatch primitive.
- **LangGraph-in-code.** Our graph comes from ontology data; building a parallel graph in code would duplicate the source of truth.
- **Pure conversational peer-to-peer.** Our flows are typed handoffs, not chat turns. Type discipline matters more than emergent dialog.

### 4.4 What we borrow from the field

Three disciplines from durable execution and event-driven systems, adopted from day one because they cost almost nothing now and a great deal to retrofit later:

1. **Idempotency keys on every flow firing.** Every handoff/query carries a stable ID derived from `(source_role, target_role, quantum_id, sequence)`. Replaying the event log never double-fires downstream effects.
2. **Operations expressed as commands → events (CQRS / event sourcing).** Agents emit *commands* ("handoff this quantum"); the orchestrator validates and writes *events* ("handoff_executed") to the log; downstream effects are driven from events, not commands. Lets us replay scenarios from the log later.
3. **Signals as the primitive for waits.** When supply_planning is awaiting three query responses or a human decision, we model it as "workflow waiting on signals," not "agent blocking on calls." Temporal pioneered this; LangGraph adopted it (their `interrupt()` + `Command(resume=...)` pattern). Means the system survives a process restart mid-decision.

These three properties form the contract between the application layer and the durability layer (§4.5). If they hold, the durability backend is swappable.

### 4.5 Two-layer architecture, swappable durability backend

The orchestrator splits internally into two layers behind a small interface:

- **Application layer (the interesting code):** ontology service, agent factory, axiom evaluator, FSM tracker, flow router, decision-surface assembly. Domain-aware in the sense that it consumes ontology semantics; domain-agnostic in the sense that nothing about supply chains is hard-coded.
- **Durability layer (boring infrastructure):** event log writer, materialized views, signal/await primitives, idempotency checks, replay. Pure infrastructure.

Interface (sketch): `append_event(kind, payload, idempotency_key)`, `await_signal(name, timeout)`, `read_state(view, key)`, `idempotency_check(key)`, `replay_from(checkpoint)`.

For the POC, the durability layer is in-memory + JSONL. For production, it is Temporal- or Restate-backed (likely Temporal — more mature ecosystem at the time of this draft). The application layer does not change between the two. This is the answer to *"how does this scale to production?"* — swap the durability backend; the agent layer is untouched.

### 4.6 Philosophical note — keep the orchestrator boring

The novelty in this system is **not** in the orchestrator pattern. Event-sourced orchestrator-worker with declarative routing is fifteen-plus years old (BPMN engines, Airflow lineage, workflow systems). The novelty is in:

- **The ontology being the source of truth for agent identity and coordination**, with generic agents instantiated from it; and
- **The LLM resolving the irreducible judgment moments** that structure cannot — under a strict design rule (§2) that prevents structure from creeping into the judgment.

The orchestrator is plumbing. Keep it boring, well-trodden, well-documented. Borrow heavily from Temporal, LangGraph, AutoGen, and the event-driven literature. Reserve design originality for the ontology layer, where the actual bet lives.

---

## 5. Architecture overview

Five components, each with a clean ontology relationship.

```
┌─────────────────────────────────────────────────────────────┐
│                        ONTOLOGY                              │
│  (LinkML YAML — roles, events, flows, axioms, FSMs,         │
│   playbooks, tools, criteria — all as classes)              │
└─────────────────────────────────────────────────────────────┘
        ▲                  ▲                  ▲
        │ reads at         │ validates        │ renders
        │ runtime          │ quanta/axioms    │ prompts
        │                  │                  │
┌───────┴────────┐  ┌──────┴───────┐  ┌──────┴────────┐
│  Ontology      │  │ Orchestrator │  │ Generic Agent │
│  Service       │  │              │  │ (one per      │
│  (SchemaView   │  │ - validates  │  │  role,        │
│   wrapped as   │  │ - routes     │  │  parameterized│
│   queryable    │  │ - evaluates  │  │  by role name)│
│   API for      │  │   axioms     │  │               │
│   agents)      │  │ - persists   │  │ - reads role  │
│                │  │   state      │  │   identity    │
│                │  │ - surfaces   │  │ - calls tools │
│                │  │   decisions  │  │ - emits/      │
│                │  │              │  │   queries/    │
│                │  │              │  │   hands off   │
└────────────────┘  └──────┬───────┘  └──────┬────────┘
                           │                  │
                    ┌──────┴──────────────────┴────────┐
                    │     Specialist Tools             │
                    │  (deterministic services:        │
                    │   capacity solver, OTIF calc,    │
                    │   schedule reader, axiom evals)  │
                    │  declared in ontology, invoked   │
                    │  by agents via typed contracts)  │
                    └─────────────┬────────────────────┘
                                  │
                    ┌─────────────┴────────────────────┐
                    │      World State + Event Log     │
                    │  (mock for demo; real systems    │
                    │   of record in production)       │
                    └──────────────────────────────────┘
```

### Component responsibilities

**Ontology Service.** Wraps `exploder.py`'s SchemaView. Exposes a queryable API to agents and to the orchestrator: "what flows do I receive?", "what playbooks am I anchored to?", "what tools can I call?", "what's the FSM for this quantum?". Pure read API; the ontology is loaded once per process.

**Orchestrator.** Plain Python service — **not** an ADK `LlmAgent`. Internally split into an application layer (ontology consumption, axiom evaluator, FSM tracker, flow router, decision-surface assembly) and a durability layer (event log, materialized views, signal/await, idempotency); see §4.5 for the boundary. Validates every quantum against its Pydantic class before it moves. Evaluates axioms before any handoff (deterministically — never via the LLM). Persists the event log. Surfaces decisions to humans when `human_involvement` policy says to. Dispatches flows to the agent bound to the target role by invoking ADK's `Runner` per-invocation. Routing is deterministic from the ontology; the orchestrator does **not** use `transfer_to_agent` or any LLM-driven dispatch primitive.

**Generic Agent.** One ADK `LlmAgent` template, instantiated per role at boot. Constructor takes `name=role_name`, `instruction=render_prompt_from_ontology(role_name)`, and the fixed seven-tool kit (see §7). System prompt is *rendered* from the ontology's view of that role: identity, incoming flows, outgoing flows, playbooks anchored to it, tools it can call, criteria it can read, events it observes and emits. The LLM inside the agent does the reasoning that survives structuring (see §3). No per-role code, no per-domain logic, no hand-authored prompts.

**Specialist Tools.** Deterministic services with typed contracts. Declared in the ontology so roles can claim them and the agent runtime can wire them. Examples: `evaluate_axioms(flow, quantum) → AxiomResults`, `query_line_load(line, window) → LineLoad`, `calculate_otif_exposure(sku, retailer, delay_days) → OTIFExposure`. Tools are where planning math, system-of-record reads, and computational work live. The LLM never does math the tools can do.

**World State + Event Log.** For the demo, a mocked world (fixture data: SKUs, lines, retailers, suppliers, commitments) plus an append-only event log of every flow firing, FSM transition, tool call, and axiom evaluation. In production this is replaced by the enterprise's actual systems of record — but the contract is the same.

### ADK alignment notes

Findings from grounding the design against current Google ADK (2026):

- **Pydantic alignment is a free win.** ADK's tool schemas and `output_schema` both speak Pydantic. `scont_bodies.py` is Pydantic. A tool declared as `def handoff(flow: str, quantum: ProcurementRequest) -> HandoffResult` is fully typed end-to-end with no glue code.
- **`transfer_to_agent` is reserved and unused.** ADK supports LLM-driven sub-agent delegation. We do not use it; routing is deterministic from the ontology. A future contributor reaching for `sub_agents` + transfer should be redirected to the orchestrator's flow router.
- **ADK workflow primitives (`SequentialAgent`, `ParallelAgent`) are not used in the first cut.** Our orchestrator handles fan-out/parallelism directly (Scene 5's three query flows are three `query()` tool calls; the orchestrator awaits all three). Revisit only if we find a coordination pattern the orchestrator can't handle as cleanly.
- **Session state ≠ orchestrator state.** ADK `session.state` is short-lived per agent invocation. Durable state lives in the orchestrator's event log + materialized views. Do not lean on `session.state` for cross-invocation persistence.
- **Per-invocation overhead is worth measuring early.** Every flow hop is a fresh `Runner.run_async`. Scene 5 has ~10 hops with three parallel queries. If startup cost is meaningful, batched invocation or session reuse may be needed before the demo feels responsive.

---

## 6. New ontology constructs

Three meta-construct additions are needed before the agent system can be built without leaning on prose `llm_prompt_hint` for load-bearing semantics. Authored in `scont_meta.yaml`, regenerated into `scont_bodies.py`, validated by the exploder, consumed by the agent renderer.

### 6.1 Playbook

A named multi-flow choreography anchored to a `(role, trigger_event)` pair. Captures the patterns that are today smuggled into hints like "fans out three query flows in parallel and decides."

**Body shape (illustrative — not final spec):**

```yaml
resolve_capacity_conflict:
  instantiates: [scont:Playbook]
  annotations:
    scont:playbook: >-
      {
        "role": "supply_planning",
        "triggered_by": "capacity_conflict_detected",
        "input_quantum": "CapacityConflict",
        "context_assembly": [
          { "flow": "check_otif_exposure",      "required": true },
          { "flow": "check_promo_flexibility",  "required": true },
          { "flow": "check_coman_availability", "required": true }
        ],
        "synchronization": "wait_all",
        "decision": {
          "criteria_refs": ["viable_promo_renegotiation",
                            "viable_coman_shift",
                            "tolerable_otif_penalty"],
          "selects_one_of": ["shift_to_coman",
                             "request_promo_revision",
                             "re_request_production"]
        },
        "always_fires": [
          { "event": "capacity_resolved" },
          { "flow":  "plan_fulfillment" }
        ]
      }
```

A Playbook says: *here is the scaffold for handling this kind of situation — these are the queries you can/should fire, these are the criteria for assessing viability, these are the execution paths available.* It does not say which path to pick, in what order to prefer them, or what to do if a criterion is borderline. Those resolutions remain agentic per §3.

**Why Playbooks and not richer hints:** Playbooks are validatable (every flow ref resolves, every criterion exists, every execution path is a real flow). Playbooks are renderable (diagrams, agent prompt sections). Playbooks are versioned (diffs are meaningful). Hints are none of these.

**Authoring discipline (apply §2 rule):** every Playbook field is reviewed for world-vs-policy. `context_assembly` lists queries that *exist and are relevant* (world). `selects_one_of` lists paths that *are available* (world). Anything resembling priority, ordering, fallback, or conditional preference is rejected at authoring time and pushed to runtime.

### 6.2 Tool / Capability

A declared deterministic service the agent can invoke. Typed input, typed output. Declared in the ontology so that:
- Roles claim which tools they can call (capability surface).
- The agent renderer adds tool descriptions to the system prompt.
- The orchestrator wires the tool to its implementation at runtime.
- Specialist work (math, schedule reads, axiom evaluation) is named and inspectable, not opaque code.

**Body shape (illustrative):**

```yaml
calculate_otif_exposure:
  instantiates: [scont:Tool]
  annotations:
    scont:tool: >-
      {
        "description": "Compute financial penalty exposure given a SKU, retailer, and delay scenario.",
        "input_class":  "OTIFQuery",
        "output_class": "OTIFExposure",
        "implementation": "logistics.otif_solver.v1",
        "deterministic": true
      }
```

The implementation pointer is the only "binding" — and it's a name, not a binding. The orchestrator binds the name to a runtime callable at boot. The ontology stays generic.

Two tool categories worth distinguishing in body shape (probably an enum):

- **Compute tools.** Pure functions over typed input. (`calculate_otif_exposure`, `evaluate_axiom`.)
- **Reader tools.** Read from world state. (`query_line_load`, `query_commitments_in_window`.)

Both are deterministic. Writer tools — anything that mutates state — should be avoided as ontology citizens for now; mutations happen via flow execution, not arbitrary tool calls.

### 6.3 Decision criteria — as advisory axioms

We do not need a new meta-construct for criteria. They are already expressible as `severity: advisory` axioms with a `tool_ref` (when slot-level `expr:` isn't enough). The agent renderer treats advisory axioms attached to a flow or class as the named viability/exposure inputs to its decisions.

This is a usage discipline, not a schema change: use advisory axioms aggressively to name decision inputs, with `nl:` that reads as a viability statement.

```yaml
- name: viable_promo_renegotiation
  scope: class
  severity: advisory
  expr: "{quantum.commitment_status} != contractually_locked"
  nl: "Promo renegotiation is viable unless the commitment is contractually locked."
  references: { classes: ["TradePromotion"] }
```

### 6.4 What we are not adding

- **Pattern tags on flows** (`pattern: boundary_ingress | context_query | ...`) — nice to have, but rendering can infer most of this from `source_role.is_boundary`, presence of `returns:`, etc. Hold until we find a case the renderer can't infer.
- **Responsibility declarations on roles** — the role's `description` + the playbooks anchored to the role already encode this. Re-evaluate after we render a few agent prompts and see whether prose is sufficient.
- **Workflow / process meta-constructs beyond Playbook** — explicit non-goal. The moment we add "process steps" or "tasks with dependencies" we are building a workflow engine in YAML. Playbooks are deliberately scoped to *choreographies of declared flows*, not arbitrary procedures.

### 6.5 What `llm_prompt_hint` becomes

A narrative supplement, never load-bearing. After the additions above, the linter (or a contributing-guideline rule) should flag any hint containing "fan out," "always fires," "when X happens then Y," "wait for," "in parallel" — those phrases name patterns that should be playbooks, not prose. Once a playbook exists, the corresponding hint is demoted to commentary.

---

## 7. Agent identity rendered from the ontology

An agent is instantiated as `Agent(role="supply_planning")`. From that single parameter, its system prompt is rendered by querying the ontology service:

```
SystemPrompt(role) = render(
  primer.md,                                                  # how to read the ontology
  role.description,                                           # who I am
  incoming_flows(role)        + their quanta + return shapes, # what arrives at me
  outgoing_handoffs(role)     + axioms_I_must_satisfy,        # what I emit and what gates me
  outgoing_queries(role)      + return shapes,                # what I can ask of others
  events_observed(role) + events_emitted(role),               # my event surface
  fsms_governing_my_quanta,                                   # state I respect
  playbooks_anchored_to(role),                                # choreographies I run
  tools_available_to(role),                                   # deterministic services I call
  advisory_criteria(role),                                    # named viability inputs
  human_involvement(role)                                     # autonomy posture
)
```

The render is pure ontology traversal — no per-role code, no per-domain logic, no hand-authored prompts. Adding a role to the YAML brings an agent online. Renaming a role propagates without code changes. Renaming a flow propagates. Adding a new query to a role's surface propagates.

### The agent's tool kit (fixed across all roles)

| Tool | Purpose |
|---|---|
| `read_ontology(query)` | Map lookup; the agent can introspect its environment at any time. |
| `emit_event(name, payload)` | Fire an event into the bus. |
| `handoff(flow, quantum)` | Fire an outgoing handoff flow. Orchestrator validates quantum + runs axioms before propagating. |
| `query(flow, query_quantum)` | Request-response over a `returns:` flow. Awaits typed response. |
| `advance_fsm(quantum, trigger)` | Lifecycle transition. Orchestrator checks guard + follows `on_failure_route_to` on block. |
| `call_tool(name, input)` | Invoke a declared specialist tool. |
| `surface_decision(playbook, context, options)` | Request decision (autonomous OR human, per orchestrator's `human_involvement` policy). |

These seven tools, plus an LLM, plus the rendered prompt — that is the entire agent. Domain-specific behavior emerges from prompt + ontology + tool feedback. No domain code per role.

---

## 8. Deterministic backbone

Three things must be deterministic to make agency safe and the demo defensible.

1. **Quantum validation.** Every quantum is Pydantic-validated against its class before transmission. A malformed quantum never crosses a flow boundary. The agent cannot emit drift.

2. **Axiom evaluation.** Axioms are evaluated by the orchestrator via tool implementations, never by the LLM. The agent sees only the result: pass, or fail with a structured reason and a `on_failure_route_to` if blocking, or a viability map if advisory. The LLM does not get to "decide" whether the line has capacity.

3. **FSM guards.** When `advance_fsm` is invoked, the guard axiom is evaluated by the same deterministic backbone. The quantum advances only if the guard passes. Otherwise the orchestrator follows the recovery route.

These three give the architecture its safety floor. Within that floor, the LLM has freedom to reason and choose. The floor itself is non-negotiable code.

---

## 9. State and transactions

The orchestrator owns runtime state. The ontology owns structure. The two never blur.

### Event log (append-only)

Every meaningful runtime event is appended:

- Flow firings (with quantum, validated)
- FSM transitions (with trigger, guard result)
- Tool invocations (with input, output, latency)
- Axiom evaluations (with pass/fail, evidence)
- Decisions (with playbook, options, choice, who chose)
- Human surfacings (with context bundle, response)

The log is the system's source of truth at runtime. Materialized views (current quantum states, pending queries, line loads) are derived from it.

### World state

For the demo: a YAML fixture loaded at boot. Plants, lines, SKUs, retailers, commitments, suppliers, a baseline production schedule, a clock seed. Validated against the ontology's Pydantic models — the fixture is real data shaped by the real schema.

In production: replaced by the enterprise's systems of record. Reader tools wrap the integrations. The agent doesn't know the difference.

### Transactional discipline

A handoff is atomic from the orchestrator's perspective: validate quantum → evaluate axioms → append to log → notify target agent. Failure at any step = no append, no notification, route to recovery. This is the spine that makes the architecture defensible as "production-grade" rather than "demo-grade."

A clock is part of world state — `today()` is injectable, both for replay and so time-dependent axioms (lead time) aren't tied to wall time during demo runs.

---

## 10. Demo as proof point

The promo whiplash narrative in `demo_narrative.md` is the unit test for the architecture. Six scenes; each exercises a different part of the system.

| Scene | What it proves |
|---|---|
| 1. Promo enters | Boundary-role ingress; signal becomes typed quantum. |
| 2. Forecast revision | Routing inferred from ontology, not hardcoded. |
| 3. Network decision | Single role fans out across multiple downstream domains. |
| 4. Capacity conflict | Deterministic axiom evaluation; `on_failure_route_to` followed automatically. |
| 5. Context assembly | **Playbook execution.** Generic agent reads playbook, fires query flows, integrates responses, surfaces decision surface. The thesis turns on this scene. |
| 6. Resolution | Generic execution along declared flows; chosen path materially differs across runs (because LLM judgment differs), but flow set is structurally identical. |

**Scene 5 is the architecture's load-bearing demo moment.** If it works — generic agent, playbook-driven, deterministic tools for math, LLM for trade-off — the thesis holds. If it fails — agent goes off-script, hallucinates capacity, picks via fixed rule — we have to revisit.

**Visible proof for skeptics.** In the demo trace, the agent's first action in Scene 5 is literally `read_ontology(playbooks_anchored_to='supply_planning', trigger='capacity_conflict_detected')` returning the `resolve_capacity_conflict` playbook. That call is on the screen. No one can claim it was hardcoded.

**Determinism + agency, both visible.** Scene 4 should show the same `on_failure_route_to` taken every run. Scene 5 should show the same context assembly every run but a *potentially different resolution* across runs as the LLM reasons over the trade-offs. That contrast is the architecture in miniature.

---

## 11. Build sketch (separate repo)

Out of scope for this doc to spec, but the shape is:

- **Repo:** new, separate. Depends on this repo as a submodule or via packaged ontology export.
- **Runtime:** Google ADK as the agent host. Need a context7 pass to confirm current ADK shape for multi-agent dispatch, tool declaration, and event semantics before committing to interfaces.
- **Ontology Service:** Python module wrapping `exploder.py`'s SchemaView. Exposed to agents as tools (`read_ontology`).
- **Orchestrator:** Python service. Holds event log (start with append-only JSONL for the demo), runs validation/axiom/FSM backbone, dispatches.
- **Generic Agent class:** ADK agent template parameterized by role; renders prompt at boot from ontology service.
- **Specialist tools:** Python implementations of declared `scont:Tool` entries, wired to the orchestrator by name.
- **World state:** YAML fixture, loaded at boot.
- **UI:** Trace view + decision surface view. The frontend-design skill is the right tool here when we get to it.

---

## 12. Open questions

1. **Meta-construct aggressiveness.** Playbook + Tool look load-bearing and worth adding now. Pattern tags and responsibility declarations are deferrable. Default: ship Playbook + Tool, defer the rest, re-evaluate after rendering agent prompts for two or three roles.

2. **`expr:` vs `tool_ref` on axioms.** Today `expr:` strings are loose. For production: trivial slot-level predicates stay as `expr:`; anything requiring world-state access (schedules, lead times, calendars) gets a `tool_ref` field on the axiom, pointing at a declared compute tool. Need to extend the axiom body in `scont_meta.yaml`.

3. **Decision surface as a typed quantum.** When supply_planning concludes Scene 5 context assembly, the "decision surface" it has assembled is itself information — options, viabilities, exposures. Is it worth modeling as a typed class (`DecisionSurface` quantum) so that human surfacing and agent decision are operating on the same structured object? Probably yes; defer the modeling decision until we render one in code.

4. **Playbook composition.** What happens when two playbooks could fire for the same role+event? Single-trigger discipline (one playbook per role+event) is simpler but limiting. Multiple playbooks with disambiguation criteria is richer but risks creeping into policy. Default: single playbook per (role, event); revisit if the demo content demands it.

5. **Replay and determinism.** With LLM stochasticity in the agent, runs are not deterministic. Is that acceptable for the demo? Probably yes — different runs *should* pick different resolutions, that's the agency. But for debugging we likely want a "seed mode" that pins the LLM output. ADK may give this for free; confirm.

6. **Boundary role implementation.** Scripted responders vs. a single boundary simulator with a configuration knob. Default: scripted YAML responses keyed by quantum shape for the demo; one shared `boundary_simulator` module per boundary role. No LLM behind boundary roles — that muddies the "external" semantic.

7. **Mock data scope.** Need to fix the dimensions of the demo world: how many plants, lines, SKUs, retailers, suppliers, commitments. Right answer is "smallest world that lets the promo whiplash narrative run end-to-end with non-trivial trade-offs." Sketch: 2 plants, 2 lines each, 5 SKUs, 3 retailers, 2 standing promos, 8 commitments, 6 suppliers. Build the fixture, see what the narrative needs.

---

## 13. What this doc is not

- **Not an implementation spec.** Component shapes are sketches. The build doc lives in the separate orchestrator repo.
- **Not a replacement for `initial_design_draft.md`.** That doc remains authoritative for the ontology layer. This doc is the agent layer that consumes it.
- **Not a freeze.** The design rules in §2 and §4 are durable. The component breakdown in §5 is durable. Meta-construct shapes in §6 will refine through authoring. Open questions in §12 are open.

---

## 14. Next concrete steps

1. **Propagate the §2 design rule into `CONTRIBUTING.md`** as a hard constraint on ontology contributions. Also surface the §4.4 borrowed disciplines (idempotency, command→event, signals) as build-time guidance for the orchestrator repo.
2. **Author `Playbook` and `Tool` meta-constructs in `scont_meta.yaml`.** Regenerate `scont_bodies.py`. Update the primer.
3. **Convert Scene 5 to a Playbook** — `resolve_capacity_conflict` as the worked example. Demote the corresponding prose hints to commentary. This is the unit test for the §6 design.
4. **Sketch the world-state fixture** — minimum data to make the narrative run end-to-end.
5. **Then start the orchestrator repo** with the application-layer / durability-layer split (§4.5), the generic agent class (ADK `LlmAgent`), ontology service, and a single role rendered end-to-end. Build the durability layer as JSONL + in-memory for the POC; design the interface so it can later sit on top of Temporal.

For the phased execution plan with definitions-of-done and stop conditions, see `plan_of_attack.md`.

---

## 15. Consumer surfaces and the MCP front door

The ontology is being designed not just for the transactional agent system that consumes it as a coordination map, but as a **generic map of the supply chain** that multiple consumers should be able to navigate. Naming the consumers upfront prevents the design from accidentally optimizing for only one of them.

### 15.1 Framing: headless ontology, multiple surfaces

There is not one front door. There are several surfaces over the same data, each tuned to a consumer's tool of choice. The ontology is **headless** — the LinkML YAML + Pydantic models + SchemaView are the data substrate; consumer experiences are built as surfaces over the Ontology Service (§5).

### 15.2 Consumers and their needs

| Consumer | What they need | Natural entry point |
|---|---|---|
| **Transactional agent** | Role-scoped view; render my prompt; let me read connected elements | Ontology Service Python API |
| **Analysis agent** | Walk the graph, evaluate hypotheticals, identify impact — never moves a quantum | LLM + MCP server over the Ontology Service |
| **Knowledge worker (investigation)** | "Why did X happen?" Traverse from symptom backward through commitments, schedules, conflicts | Natural-language query against their LLM client backed by MCP |
| **Knowledge worker (onboarding)** | "What is supply_planning's job? What does a promo look like end-to-end?" | Role-centric overview rendered as prose; same render function that produces the agent's prompt |
| **Ontology author** | Add a new role / flow / playbook | Editor UI + `exploder.py` CLI |
| **Skeptic / stakeholder** | Visual proof this isn't vapor | Visual map (editor) + a worked scenario |

### 15.3 Surfaces we have and the one we don't

| Surface | Status | Serves |
|---|---|---|
| `exploder.py` CLI (`inspect`, `query`, `doc`) | Exists | Developers, advanced users |
| Generated `docs/` markdown | Exists | Anyone browsing (static) |
| Editor / visualizer | Shipped (Phase I.3) | Authors, visual explorers, stakeholder demos |
| Ontology Service (Python API) | Planned (`plan_of_attack.md` Phase 1) | Transactional agents, orchestrator |
| **MCP server over the Ontology Service** | **Missing — high leverage** | **Analysis agents, knowledge workers via their LLM client, IDE plugins** |
| Embedded views in business tools (SAP, Excel, Slack) | Far future | Real production knowledge workers |

### 15.4 Why MCP is the load-bearing missing surface

Wrapping the Ontology Service as an MCP server collapses what would otherwise be multiple build efforts into one substrate. The realization: **an analysis agent is not a separate runtime to build. It is an LLM with the ontology MCP server attached.** Same for knowledge workers — their front door is whichever LLM client they already use, plus MCP, plus the ontology.

Concretely, with MCP in place:

- A knowledge worker asks Claude "if Walmart's promo slips a week, who's affected?" — Claude traverses via MCP, returns a typed cited answer.
- An IDE plugin offers "go to ontology" — same protocol.
- A new hire onboarding asks "walk me through what supply_planning does day-to-day" — Claude renders the role's connected graph as prose.

The render function that produces the transactional agent's system prompt and the render function that produces the knowledge worker's onboarding doc are the **same function** — only the format adapter at the edge differs. Build the Ontology Service so this is true from day one: typed object output; format adapters (prompt-text / markdown / JSON) at the edge.

### 15.5 Ontology-side capabilities the front-door thesis depends on

Surface these so we feel the pain in the right order. None are urgent for Phase 1:

1. **Search over hints + descriptions.** Currently structural only. For MCP `search`, a simple inverted index over descriptions and hint text, optionally embedding-augmented. Cheap.
2. **Reverse-traversal / impact analysis.** "Given class X, what references it?" — a query over SchemaView, not new ontology content. Lives in the Ontology Service.
3. **Reified scenarios.** `demo_narrative.md` is prose. To let a knowledge worker "walk a scenario" via an LLM, scenarios want to be data — a sequence of flow firings with expected events. Could be a `scont:Scenario` construct or a separate `scenarios/` catalog. Defer until we feel the need.
4. **The "where am I" render.** Given a role/flow/quantum, return everything connected. This *is* the prompt-render function, retargeted at humans. Build once, format twice.

### 15.6 Tactical ordering

MCP comes after the first transactional-agent slice, not before. The Ontology Service should be exercised by one real consumer (the agent) before generalizing across protocols. Build the Service knowing MCP will sit on top; then add MCP as a thin adapter. This is Phase 7 in `plan_of_attack.md`.

### 15.7 What's beyond MCP

Production knowledge workers in CPG live in SAP, Excel, Slack, dashboards — not Claude. MCP is the right substrate for unlocking ontology navigation *now* (every LLM-augmented tool can speak it), but the long-term answer involves embedded views in real business tools. Not on the immediate roadmap; flagged so the path doesn't end at MCP.
