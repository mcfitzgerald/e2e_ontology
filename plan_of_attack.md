# Plan of Attack — Ontology + Agent System Build

**Status:** Active plan. Memorialized 2026-05-27 after the orchestrator-landscape (§4) and consumer-surfaces (§15) design work in `agent_system_design.md`. Supersedes the ad-hoc "next concrete steps" in §14 of that doc.

**Reads with:**

- `initial_design_draft.md` — ontology design and meta-model.
- `agent_system_design.md` — agent system architecture and design philosophy (the *what* and *why*).
- `demo_narrative.md` — the promo whiplash narrative this system will execute as its proof point.
- This doc — the *when* and *in what order*.

**Format.** Phased milestones with explicit definition-of-done (DoD) per phase. Phases are sequenced because each unlocks the next; within a phase, items may parallelize. Phase 7 (MCP) and Phase 8 (UI) can run in parallel with later transactional-agent phases.

---

## Phase 0 — Foundations (this repo)

Purpose: lock the design discipline in writing before any new code lands.

### 0.1 Propagate the design rules into `CONTRIBUTING.md`

- Land the §2 world-model / decision-policy rule as a hard contribution constraint.
- Land the §4.4 borrowed disciplines (idempotency keys, command→event / CQRS, signals for waits) as build-time guidance for the orchestrator repo when it spins up.

**DoD:** A new contributor PR-ing a `prefer:` or `priority_order:` field on a flow or playbook would get caught by the contribution guidelines.

### 0.2 Sketch the world-state fixture dimensions

- ~2 plants × 2 lines each, ~5 SKUs, ~3 retailers, ~2 standing promos, ~8 retailer commitments, ~6 suppliers.
- Author as a YAML fixture in this repo; validate against ontology Pydantic models.
- Decide the clock-seed strategy (`today()` = integer day-of-year, injectable).

**DoD:** A `world_state.yaml` exists, parses cleanly via the existing ontology Pydantic models, and lets the demo scenarios resolve their data references (SKUs, retailers, lines).

---

## Phase 1 — Ontology Service + prompt renderer (this repo, branch)

Purpose: prove the contract that the ontology can render a coherent role view *without any agent infrastructure*.

### 1.1 Ontology Service Python module

- New module `ontology_service/` in this repo.
- Wraps `exploder.py`'s `SchemaView` with a queryable API.
- Initial methods: `get_role(name)`, `incoming_flows(role)`, `outgoing_handoffs(role)`, `outgoing_queries(role)`, `events_observed(role)`, `events_emitted(role)`, `fsms_for_role(role)`, `playbooks_anchored_to(role)`, `tools_for_role(role)`, `advisory_criteria_for(role)`, `human_involvement(role)`, `axioms_on_flow(flow)`.
- Read-only; ontology loaded once at boot.

### 1.2 Format-agnostic role-view render

- `render_role_view(role_name) → RoleView` returns a typed Pydantic object.
- Format adapters at the edge: `as_agent_prompt(view)`, `as_markdown(view)`, `as_json(view)`.
- One render function, multiple consumers (agent prompt today; knowledge-worker doc and MCP response later).

### 1.3 Tests

- Render `demand_planning` → eyeball + snapshot test.
- Render `supply_planning` → eyeball (most complex; multiple incoming/outgoing/query flows; `human_involvement: conditional`).
- Snapshot tests for stability across ontology changes.

**DoD:** `render_role_view('demand_planning').as_agent_prompt()` produces a deterministic, readable, complete agent system prompt from the current ontology. Same call works for `supply_planning`. No agent code yet — this is pure rendering.

---

## Phase 2 — First transactional agent (new orchestrator repo)

Purpose: smallest possible vertical slice. End-to-end round trip for a single role.

### 2.1 New repo `e2e-orchestrator` (or similar)

- Depends on the ontology repo (submodule or packaged release).
- Python project, ADK as primary dependency.
- Inherits the §4.4 disciplines from this repo's `CONTRIBUTING.md`.

### 2.2 Orchestrator scaffold with two-layer split (per §4.5)

- **Application layer:** flow router (lookup `target_role` from ontology), quantum validation, agent dispatch via ADK `Runner`.
- **Durability layer:** append-only JSONL event log, in-memory materialized views, signal/await primitives, idempotency keys.
- Interface boundary: `append_event(kind, payload, idempotency_key)`, `await_signal(name, timeout)`, `read_state(view, key)`, `idempotency_check(key)`, `replay_from(checkpoint)`.

### 2.3 Generic Agent template (ADK `LlmAgent`)

- `Agent(role='demand_planning')` constructor.
- Instruction rendered from Ontology Service.
- Tool kit (per §7): `read_ontology`, `emit_event`, `handoff`, `query`, `advance_fsm`, `call_tool`, `surface_decision`.

### 2.4 World state loaded from fixture

- Loads the Phase 0.2 YAML into a queryable in-memory store.

### 2.5 Stub the rest

- All non-`demand_planning` roles backed by scripted responders for now.

**DoD:** A `DemandAnomaly` quantum is injected at the boundary, dispatched to the `demand_planning` agent, the agent calls `handoff('submit_supply_request', SupplyRequest(...))`, the orchestrator validates the quantum, evaluates any axioms (none on this flow), appends to the event log, and routes to a stub `supply_planning`. The event log shows the full transaction with idempotency key. Agent reasoning visible in the trace.

---

## Phase 3 — Multi-role happy path (Scenes 1-3)

Purpose: prove the generic-agent thesis on more than one role. Get the promo whiplash narrative's happy path through Scenes 1-3.

### 3.1 Add `supply_planning` agent

- Same template, different role parameter. **No code change to the template.** If a code change is required to support a second role, the template is wrong — revisit.

### 3.2 Add `production_planning` agent

- Same template again.

### 3.3 Wire the boundary simulator for `customer_development`

- Scripted YAML responder for the boundary role per §12.6.
- Emits `promo_plan_aligned` event with a `TradePromotion` payload.

### 3.4 Execute Scenes 1-3 end-to-end

- `promo_plan_aligned` → `submit_promo_plan` → `forecast_revised` → `submit_supply_request` → `production_assigned` → `request_production`.
- Three real LLM agents acting; deterministic routing throughout; no axiom failures yet.

**DoD:** Single-command run starts the full happy path. The trace shows three role agents acting, **no domain-specific code per role**, and all routing decisions traceable to ontology lookups (visible in the agent tool-call traces).

---

## Phase 4 — Deterministic backbone (axioms + FSM)

Purpose: prove Scene 4 (Mode 1 — hard gate). Add the safety floor under the agent layer.

### 4.1 Axiom evaluator

- Slot-level `expr:` evaluator (Python-subset expression with `{slot.path}` references).
- Tool-backed evaluator stub for axioms needing world-state access (`line_capacity_not_exceeded` requires summing scheduled units on a line for a window).
- Returns structured `AxiomResult` with pass/fail + evidence + `on_failure_route_to` if blocking.

### 4.2 FSM tracker

- Per-quantum FSM state held in the orchestrator's materialized views.
- Guard enforcement: `advance_fsm` invokes the same evaluator on the guard axiom; on block, follows `on_failure_route_to`.

### 4.3 Execute Scene 4

- Inject a `ProductionRequest` whose volume exceeds line capacity.
- `line_capacity_not_exceeded` fires; orchestrator follows `on_failure_route_to: escalate_capacity_conflict` automatically.
- `production_planning` agent never sees the option to "decide capacity passes" — the floor is in code, not the LLM.

**DoD:** Blocking axiom triggers the recovery flow without LLM involvement in the routing. The same code path handles `respect_lead_time` and `line_capacity_not_exceeded`. The trace shows the deterministic evaluation outcome as a non-LLM event.

---

## Phase 5 — Playbook + Scene 5 (the load-bearing demo moment)

Purpose: validate the thesis. Cross-domain context assembly via a Playbook-driven agent, with LLM judgment irreducibly present.

### 5.1 Author Playbook + Tool meta-constructs in `scont_meta.yaml`

- Bodies per §6.1 (Playbook) and §6.2 (Tool) of `agent_system_design.md`.
- Regenerate `scont_bodies.py` via `exploder.py regen-bodies`.
- Update `ontology_primer.md` to teach LLMs how to read the new constructs.

### 5.2 Convert Scene 5 to a Playbook

- Author `resolve_capacity_conflict` Playbook anchored to (`supply_planning`, `capacity_conflict_detected`).
- Apply the §2 design rule at authoring: only world-modeling fields; no policy.
- Demote the corresponding `llm_prompt_hint` content to commentary.

### 5.3 Implement query flow fan-out in the orchestrator

- `query()` tool fires a typed query to a target role; awaits typed response via signals.
- Parallel fan-out: three queries in flight, supply_planning waits for all (signals from §4.4).

### 5.4 Implement decision-surface assembly

- After query responses arrive, supply_planning agent assembles a `DecisionSurface` (typed; per §12.3 — model as a quantum if it earns its keep).
- Agent picks a resolution flow.

### 5.5 Execute Scene 5

- Capacity conflict lands; supply_planning's first action visible in the trace: `read_ontology(playbooks_anchored_to='supply_planning', trigger='capacity_conflict_detected')` returns `resolve_capacity_conflict`.
- Three queries fire in parallel; three typed responses arrive; supply_planning's LLM weighs the trade-off; one resolution flow selected.

**DoD:** Across two runs with different LLM seeds, supply_planning fires the **same three query flows** (deterministic context assembly) but may pick **different resolutions** (irreducible agency). The contrast is visible in the trace. Skeptics can see the ontology lookup in the trace and confirm no hardcoded routing.

---

## Phase 6 — Resolution and full demo (Scene 6)

Purpose: end-to-end promo whiplash narrative running from a single seed signal.

### 6.1 Implement the three resolution paths

- `shift_to_coman` (external boundary handoff).
- `re_request_production` (internal re-entry with revised quantum).
- `request_promo_revision` (skeletal, boundary).
- Stub boundary responders for `co_manufacturing` and `customer_development`.

### 6.2 `plan_fulfillment` and convergence to happy path

- The "always fires on capacity_resolved" flow per the playbook.
- Demonstrate the system re-converges after the conflict resolution.

### 6.3 Trace + replay

- Trace viewer renders the event log into a readable narrative.
- Replay capability: given a seed signal + same LLM seed, the run reproduces. ADK may give this for free per §12.5; confirm.

**DoD:** A single command runs the full promo whiplash narrative end-to-end. The trace tells the story. The narrative document and the trace agree.

---

## Phase 7 — MCP front door (this repo, can start after Phase 1)

Purpose: open the ontology to analysis agents and knowledge workers via every LLM client that speaks MCP.

### 7.1 MCP server module

- New module `mcp_server/` in this repo.
- Wraps the Ontology Service from Phase 1.
- Tools: `read_role`, `read_flow`, `read_quantum`, `read_playbook`, `traverse(from, direction)`, `search(query)`, `impact_analysis(element)`, `walk_scenario(name)`.
- Resources: ontology source, generated docs, narrative.
- Prompts: canonical traversal patterns ("show me everything about role X").

### 7.2 Format adapters

- All MCP responses use the format-agnostic Ontology Service (markdown for human consumption; JSON for tool chains).

### 7.3 Reverse-traversal index

- Build the impact-analysis primitive (§15.5 #2): "given class X, what references it?"
- This is a query over SchemaView, not new ontology content.

### 7.4 Test with Claude Desktop or equivalent

- Connect the server; ask exploratory questions; verify answers cite real ontology elements.

**DoD:** A knowledge worker asks Claude "if Walmart's promo slips a week, who's affected?" — Claude traverses via MCP and gives a typed, cited answer that resolves to real ontology elements. The same answer is reproducible across LLM clients.

---

## Phase 8 (parallel) — Demo UI

Purpose: make the demo land for non-technical stakeholders. Parallels Phases 5-6.

### 8.1 Trace view

- Streaming view of the event log as a scenario runs.
- Highlight ontology lookups, axiom evaluations, decision moments, FSM transitions.

### 8.2 Decision surface view

- Visual presentation of the assembled options + criteria at Scene 5's decision moment.
- Optional button to act as the human decider (for the demo, not production HITL — that's an orchestrator concern).

### 8.3 Use `frontend-design` skill

- Distinctive, production-grade output per `CLAUDE.md` tooling conventions.

**DoD:** A 5-minute video of the demo. Trace visible; agent reasoning legible; decision surface clear; resolution executed; happy path re-converges.

---

## Phase dependency graph

```
Phase 0 (foundations, this repo)
  └─→ Phase 1 (ontology service in this repo)
        ├─→ Phase 2 (first agent in new repo)
        │     └─→ Phase 3 (multi-role happy path)
        │           └─→ Phase 4 (axioms + FSM)
        │                 └─→ Phase 5 (playbook + Scene 5)
        │                       └─→ Phase 6 (resolution + full demo)
        │                             └─→ Phase 8 (UI; parallels 5-6 in practice)
        └─→ Phase 7 (MCP front door; independent of orchestrator)
```

Phase 7 (MCP) can begin any time after Phase 1 — it depends only on the Ontology Service. Phase 8 (UI) parallels Phase 6 closely.

---

## What this plan deliberately does NOT include

- **No commitment to Temporal/Restate/Inngest in the POC.** The durability layer is JSONL until we need otherwise. The application-layer interface (§4.5) is the contract that lets us swap later.
- **No commitment to scaling beyond demo throughput.** Per-invocation ADK overhead is worth measuring (§5 ADK alignment notes), but not optimizing for at POC scale.
- **No commitment to embedded views in business tools (SAP/Excel/Slack).** MCP is the substrate; embedded views are a future build.
- **No new meta-constructs beyond Playbook + Tool in Phase 5.** Pattern tags, responsibility declarations, decision-surface-as-construct — all deferred until we feel the pain.
- **No bespoke specialist solvers** (capacity, OTIF, lead-time) beyond what's needed for axiom evaluation. The point is coordination-generic; specialist quality comes later.

---

## Stop conditions — when to pause and rethink

Trip wires that indicate the design needs revisiting, not more code:

1. **Phase 2 DoD doesn't hold within two working sessions.** Means the contract between the Ontology Service and the Generic Agent is wrong; fix the contract before pressing forward.
2. **Phase 3 requires per-role code in the generic agent template.** Means the template is leaky; the abstraction needs revisiting before adding role 4.
3. **Phase 4 axiom evaluator turns into a small language implementation.** Means `expr:` was the wrong abstraction; pivot to `tool_ref` per §12.2 of the design doc.
4. **Phase 5 Scene 5 doesn't show different resolutions across runs.** Means we've structured the agency away; revisit the Playbook authoring against the §2 design rule.
5. **Phase 7 MCP doesn't deliver a clean knowledge-worker experience on the first non-trivial query.** Means the Ontology Service shape is wrong; refactor before adding more tools.

---

## Cadence and visibility

- **Per-phase commit.** Each phase lands as one or more PRs into its respective repo. Phase DoD is the PR description's "definition of done" checklist.
- **CHANGELOG entries.** Per the existing repo conventions, every phase appends a session-by-session entry to `CHANGELOG.md`.
- **Open questions tracked in `agent_system_design.md §12`.** As we feel the pain of deferred decisions, items move from §12 into a phase's scope.
- **Memory writes.** When a phase reveals a durable lesson (a design choice that worked or didn't), it goes into the auto-memory layer for future sessions.
