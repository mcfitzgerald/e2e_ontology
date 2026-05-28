# Orchestrator Repo — Bootstrap Briefing

**Status:** Carry-over context to seed the new orchestrator repository (`plan_of_attack.md` Phase 2). Authored 2026-05-27. This document is a self-contained briefing for the first session in the new repo; it captures intent, decisions already made, what to inherit from the ontology repo, and the first concrete task.

This briefing does not get committed into the new repo verbatim — instead, its content seeds the new repo's `README.md`, `CONTRIBUTING.md`, `CLAUDE.md`, and `agent_system_design.md` (likely pulled in by reference rather than copied).

---

## 1. Project intent

The orchestrator repo hosts the **agent system that consumes the supply chain ontology** developed in `e2e_ontology`. The ontology is the source of truth for agent identity, coordination, and constraints. The orchestrator is the runtime that:

- Hosts **generic agents** (one ADK `LlmAgent` template, parameterized by role from the ontology).
- Routes **typed flows** between agents using deterministic lookups against the ontology.
- Evaluates **axioms** and **FSM guards** before any quantum advances (deterministically, never via an LLM).
- Persists **state** as an append-only event log + materialized views.
- Wires **specialist tools** (capacity, OTIF, lead-time) that agents call but do not implement.

The thesis is that one generic agent template plus the ontology suffices to coordinate a complex cross-domain supply chain demo (the promo whiplash narrative). No per-role code, no per-domain logic; identity flows from the ontology at runtime.

## 2. The thesis we are trying to prove

Four explicit claims, copied from `agent_system_design.md` §1:

1. **Coordination is generic.** One agent template, parameterized by role, suffices for routing, handoffs, query-response, and context assembly across every domain in the ontology.
2. **Identity is structural.** An agent knows what it is, what arrives at it, what it can emit, what gates it, and what it can ask of others — purely from the ontology.
3. **Agency survives structure.** Adding structure to the ontology (Playbooks, Tools, criteria) does not collapse the system into automation. Agency lives in resolution-under-evidence, not in workflow steps.
4. **The orchestrator is dumb in the right way.** It validates, routes, persists state, evaluates axioms, surfaces decisions — but it does not know domain semantics. The ontology is the only source of domain truth.

## 3. Authoritative reading order (from the ontology repo)

Read these in order before starting any orchestrator work. They live in the `e2e_ontology` repo and should be checked in as a git submodule or pulled in as a packaged dependency.

1. **`ontology_primer.md`** — how to read the ontology. Short. Prepend to every LLM prompt that consumes the ontology.
2. **`agent_system_design.md`** — design intent for the agent runtime. **The most important read.**
   - §1 Thesis
   - §2 The world-vs-policy design rule (durable)
   - §3 Where agency irreducibly lives (four classes of moment that must not be structured away)
   - §4 Orchestrator landscape — three layers people call "orchestrator," six recognizable patterns, where we sit, what we borrow, two-layer split, keep-it-boring philosophical note
   - §5 Architecture overview + ADK alignment notes
   - §6 New ontology constructs (Playbook + Tool) — note these are not yet in the ontology; Phase 5 of the plan
   - §7 Agent identity rendered from the ontology — the seven-tool kit
   - §8 Deterministic backbone (quantum validation, axiom eval, FSM guards)
   - §9 State and transactions
   - §10 Demo as proof point
   - §15 Consumer surfaces and MCP front door
3. **`plan_of_attack.md`** — phased plan with definitions-of-done. Phase 0 ✅ done; Phase 1 (Ontology Service in `e2e_ontology`) is the next deliverable; Phase 2 is the first work in this new repo.
4. **`demo_narrative.md`** — the promo whiplash narrative. The demo this system executes end-to-end.
5. **`initial_design_draft.md`** — authoritative for the ontology layer. Skim §3 (meta-model) and §11 (LLM-reasoning spike results) to understand what kind of artifact you're consuming.
6. **`CONTRIBUTING.md`** (ontology repo) — has the §2 world-vs-policy rule at the top, plus a "Notes for orchestrator-repo contributors" section with the §4.4 disciplines that travel.

## 4. Durable design rules that travel

These rules govern the orchestrator repo as much as the ontology repo. They should land verbatim in the orchestrator's own `CONTRIBUTING.md`:

### 4.1 The world-vs-policy rule (from `agent_system_design.md` §2)

> The ontology models the world and the action vocabulary. It never models the decision policy.

This governs ontology contributions; the orchestrator must refuse to consume any ontology field that smells like policy. If you find yourself wanting a `prefer:`, `priority_order:`, `fallback_chain:`, or `if X then Y` field in the ontology, the answer is "no — that's runtime."

### 4.2 The three borrowed disciplines (from `agent_system_design.md` §4.4)

Adopted from durable-execution and event-driven systems literature; they cost almost nothing now and a great deal to retrofit later:

1. **Idempotency keys on every flow firing.** Stable ID derived from `(source_role, target_role, quantum_id, sequence)`. Replaying the event log never double-fires downstream effects.
2. **Commands → events (CQRS / event sourcing).** Agents emit *commands* ("handoff this quantum"); the orchestrator validates and writes *events* ("handoff_executed") to the log; downstream effects are driven from events, not commands. Enables replay.
3. **Signals as the primitive for waits.** When a role is awaiting multiple query responses or a human decision, model it as "workflow waiting on signals," not "agent blocking on calls."

### 4.3 No LLM in the routing path

Routing is deterministic from the ontology. The orchestrator does **not** use ADK's `transfer_to_agent` or any LLM-driven dispatch primitive. If a future contributor reaches for `sub_agents` + LLM transfer for routing, redirect to the flow router.

### 4.4 No per-role code in the agent template

If adding a second or third role to the system requires editing the agent template, the abstraction is leaking. Revisit before pressing on. (This is also Phase 3's stop condition in `plan_of_attack.md`.)

## 5. Architectural commitments — already locked in

These are decided. Do not relitigate without significant new evidence.

### 5.1 Two-layer orchestrator with swappable durability backend

- **Application layer** (interesting code): flow router (lookup `target_role` from ontology), quantum validation, axiom evaluator, FSM tracker, decision-surface assembly, agent dispatch via ADK `Runner`.
- **Durability layer** (boring infra): event log writer, materialized views, signal/await primitives, idempotency checks, replay.

Interface (sketch):

```
append_event(kind, payload, idempotency_key)
await_signal(name, timeout)
read_state(view, key)
idempotency_check(key)
replay_from(checkpoint)
```

POC durability is JSONL + in-memory. Production durability is Temporal- or Restate-backed. The application layer does not change between the two — that's the contract.

### 5.2 Generic Agent = ADK `LlmAgent`

```python
Agent(role='demand_planning')
# = LlmAgent(
#     name='demand_planning',
#     instruction=render_prompt_from_ontology('demand_planning'),
#     tools=[handoff, query, emit_event, advance_fsm, call_tool,
#            read_ontology, surface_decision],
#   )
```

Constructor takes only the role name. Everything else is derived.

### 5.3 The fixed seven-tool kit (every role gets the same toolkit)

| Tool | Purpose |
|---|---|
| `read_ontology(query)` | Map lookup; the agent can introspect its environment at any time. |
| `emit_event(name, payload)` | Fire an event into the bus. |
| `handoff(flow, quantum)` | Fire an outgoing handoff flow. Orchestrator validates quantum + runs axioms before propagating. |
| `query(flow, query_quantum)` | Request-response over a `returns:` flow. Awaits typed response via signal. |
| `advance_fsm(quantum, trigger)` | Lifecycle transition. Orchestrator checks guard + follows `on_failure_route_to` on block. |
| `call_tool(name, input)` | Invoke a declared specialist tool. |
| `surface_decision(playbook, context, options)` | Request decision (autonomous OR human, per orchestrator's `human_involvement` policy). |

All seven are typed Python closures over the orchestrator. ADK auto-generates schemas from Python signatures, so `def handoff(flow: str, quantum: ProcurementRequest) -> HandoffResult` is fully typed end-to-end with no glue code.

### 5.4 Deterministic backbone — three things that must be code, never LLM

1. **Quantum validation** against its Pydantic class before transmission.
2. **Axiom evaluation** by the orchestrator via tool implementations; the agent sees only the result.
3. **FSM guards** evaluated by the same deterministic backbone; quantum advances only if the guard passes.

### 5.5 Boundary roles are stubs, not LLM agents

`customer_development`, `co_manufacturing`, `demand_sensing` — scripted YAML responders. No LLM behind boundary roles; that muddies the "external" semantic.

### 5.6 No ADK workflow primitives in the first cut

`SequentialAgent` and `ParallelAgent` exist but are not used. Fan-out is handled by the orchestrator (Scene 5's three query flows are three `query()` tool calls; orchestrator awaits all three). Revisit only if we find a pattern the orchestrator can't handle cleanly.

## 6. What lives where

| Concern | Ontology repo (`e2e_ontology`) | Orchestrator repo (new) |
|---|---|---|
| LinkML schemas (ontology + meta) | ✅ | — |
| `exploder.py` (validation, query, doc, scaffolding) | ✅ | — |
| Editor / visualizer | ✅ | — |
| Ontology Service (Phase 1 — Python module wrapping SchemaView, rendering role views) | ✅ | consumes |
| MCP server over the Ontology Service (Phase 7) | ✅ | — |
| World state fixture (`world_state.yaml`) | ✅ (the data) | loads it (the runtime) |
| Orchestrator (application + durability) | — | ✅ |
| Generic Agent (ADK `LlmAgent` template) | — | ✅ |
| Specialist tools (compute + reader implementations) | — | ✅ |
| World-state loader, clock, schedule materialized views | — | ✅ |
| Trace + replay UI (Phase 8) | — | ✅ |

Dependency direction: orchestrator depends on ontology repo. Never the other way.

## 7. Dependencies

Python runtime managed by `uv` (consistent with the ontology repo).

| Dependency | Purpose |
|---|---|
| `google-adk` (or current ADK package name; confirm via context7) | Agent runtime |
| `linkml-runtime` | SchemaView, instance validation (via the Ontology Service) |
| `pydantic` | Typed quanta, tool I/O, validation |
| `pyyaml` | Loading the ontology and world-state fixture |
| `pytest` | Test runner |
| `e2e_ontology` (this repo, as submodule or package) | Source of truth for the ontology |

Defer: Temporal/Restate Python SDKs — only when we move the durability layer off JSONL.

## 8. Initial repo structure (sketch)

```
e2e_orchestrator/
├── README.md
├── CLAUDE.md
├── CONTRIBUTING.md                    # carries §2 rule + §4.4 disciplines verbatim
├── pyproject.toml                     # uv-managed
├── ontology/                          # submodule or vendored: e2e_ontology
│
├── src/e2e_orchestrator/
│   ├── application/
│   │   ├── agent_factory.py           # Agent(role=...) constructor
│   │   ├── prompt_renderer.py         # consumes ontology Service; format adapters
│   │   ├── flow_router.py             # ontology lookup → target_role dispatch
│   │   ├── axiom_evaluator.py         # deterministic; tool-backed for world-state axioms
│   │   ├── fsm_tracker.py
│   │   ├── decision_surface.py        # Scene 5 context assembly
│   │   └── tools/
│   │       ├── agent_toolkit.py       # the seven tools (handoff, query, etc.)
│   │       └── specialist/            # capacity, otif, lead_time
│   │
│   ├── durability/
│   │   ├── event_log.py               # JSONL append-only
│   │   ├── materialized_views.py
│   │   ├── signals.py                 # await_signal primitive
│   │   ├── idempotency.py
│   │   └── interface.py               # the swappable contract
│   │
│   ├── world_state/
│   │   ├── loader.py                  # reads e2e_ontology/world_state.yaml
│   │   ├── clock.py                   # injectable today()
│   │   └── schedule.py                # production schedule queries
│   │
│   ├── boundary/
│   │   ├── customer_development.py    # scripted responder
│   │   ├── co_manufacturing.py
│   │   └── demand_sensing.py
│   │
│   └── runtime/
│       └── main.py                    # entry point; wires everything
│
├── tests/
│   ├── test_agent_factory.py
│   ├── test_flow_router.py
│   ├── test_axiom_evaluator.py
│   ├── test_event_log.py
│   ├── test_scene1_3_happy_path.py    # Phase 3
│   ├── test_scene4_axiom_recovery.py  # Phase 4
│   └── test_scene5_playbook.py        # Phase 5 (when ontology adds Playbook)
│
└── ui/                                # Phase 8 — frontend-design skill territory
```

Tweak freely; this is a sketch, not a constraint.

## 9. The first concrete task (Phase 2 DoD)

From `plan_of_attack.md` Phase 2:

> A `DemandAnomaly` quantum is injected at the boundary, dispatched to the `demand_planning` agent, the agent calls `handoff('submit_supply_request', SupplyRequest(...))`, the orchestrator validates the quantum, evaluates any axioms (none on this flow), appends to the event log, and routes to a stub `supply_planning`. The event log shows the full transaction with idempotency key. Agent reasoning visible in the trace.

Concretely, the minimum cuts to make this work:

1. **Ontology Service must exist in `e2e_ontology`** (Phase 1, which runs first). The orchestrator imports it.
2. **`Agent(role='demand_planning')` constructor** that renders an instruction from the Ontology Service and binds the seven tools.
3. **Flow router** that takes a flow name + quantum, validates the quantum's Pydantic class, runs any flow-level axioms (none on `raise_demand_anomaly` or `submit_supply_request`), looks up `target_role`, and dispatches.
4. **Stub `supply_planning`** — a scripted responder that accepts a `SupplyRequest` and acknowledges. (Real `supply_planning` agent lands in Phase 3.)
5. **Event log writer** that appends every meaningful runtime event to a JSONL file with idempotency keys.
6. **Boundary simulator for `demand_sensing`** — emits a `DemandAnomaly` quantum as the seed.
7. **Single command runner** that boots the orchestrator, instantiates the agent, fires the boundary event, and prints the trace.

Stop conditions per Phase 2 from `plan_of_attack.md`: if DoD doesn't hold within two working sessions, the contract between the Ontology Service and the Generic Agent is wrong — fix the contract before pressing forward.

## 10. Open questions to expect (already surfaced)

From `agent_system_design.md` §12 — not blockers for Phase 2 but worth knowing they're live:

- `expr:` vs `tool_ref:` on axioms. Trivial slot-level predicates stay as `expr:`; anything requiring world-state access gets a tool ref. Need to extend the axiom body schema in `scont_meta.yaml` when this bites (probably in Phase 4).
- Decision surface as a typed quantum (`DecisionSurface`). Probably worth modeling once Phase 5 needs human surfacing; defer until then.
- Playbook composition (multiple playbooks for the same role+event). Default to single playbook per (role, event) until the demo demands otherwise.
- Replay and determinism. With LLM stochasticity, runs aren't deterministic. ADK may provide a seed mode; confirm during Phase 2.

## 11. What we are not building (yet)

From `plan_of_attack.md`:

- No Temporal/Restate/Inngest in the POC. JSONL durability + signal primitives are the application-layer's only contract; backend swap is later.
- No bespoke specialist solvers beyond what's needed for axiom evaluation. Stubs are fine.
- No production-grade scaling, observability, or multi-tenant concerns.
- No embedded views in SAP/Excel/Slack. MCP is the substrate; embedded views are future.

## 12. First-session expected ritual

A fresh session in the new repo should:

1. Read this briefing.
2. Read `agent_system_design.md` and `plan_of_attack.md` from the ontology repo (linked via submodule or local path).
3. Confirm understanding by summarizing back: the thesis, the four claims, the §2 rule, the two-layer architecture, and what Phase 2 DoD looks like.
4. Confirm Phase 1 (Ontology Service) is in place in the ontology repo. If not, fall back to working on that first.
5. Then start Phase 2.
