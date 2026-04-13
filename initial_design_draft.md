# Initial Design Draft — Supply Chain Ontology POC

**Status:** POC foundation in place and validated. Format choice (LinkML) validated. Extension pattern refined against `pcg.yaml` and **proven empirically** — the de-risking spike (§10) passed all three LLM-reasoning questions cleanly on first run, with the LLM exhibiting deeper cross-reference traversal than required (see §11). Ontology, exploder, and primer all exist and work end-to-end. Meta-model extended (session 3) with boundary roles (§3.1), query-flow clarification (§3.3), human-involvement pattern (§3.7), and two reasoning modes (§4). Demo scenario chosen: promo whiplash (see `demo_narrative.md`, linked from §7).
**Purpose:** Memorialize the brainstorming session's conclusions, record what we learned from the spike, and capture forward-looking concerns so we can resume with shared context and avoid re-litigating settled points.

---

## 1. Purpose and scope

A simple, extensible ontology of the supply chain that sits in an **agent orchestration layer** and provides the core **structural and process context** agents need to navigate the domain. The ontology is consumed by agents as context; it does not itself orchestrate.

**Hard constraints:**

- Simple but complete and functional enough for a demonstration that sells the idea
- Not OWL — avoid formal description logics, but retain a similar feature set at a lighter weight
- Easy to extend, compose, and nest
- Declarations trivially recastable as a graph schema (e.g. Neo4j) without targeting a graph data architecture — the ontology can be used "virtually" in LLM context alone
- Generic in tone — no binding to a specific orchestrator framework or runtime
- Authoritative for metrics **now**, designed for future coexistence with dbt semantic layer when the enterprise scales it out

**Non-goals (explicit):**

- Not a capability manifest. The ontology describes concepts, including actions as declared affordances with pre/post conditions — but it does **not** bind actions to tools or APIs. That is the orchestrator's job.
- Not a runtime dependency on dbt semantic layer. The ontology must be *compatible* with dbt's model, not reliant on it being deployed.
- Not a virtual twin over a specific database. Unlike `pcg.yaml` (which models SQL tables), this ontology is abstract-conceptual; it describes the supply chain and how an agent navigates it, not a mapping to physical storage.

---

## 2. Layer model

```
Structural  — what exists (types, taxonomy, relations)
Logical     — what must be true (constraints, axioms, invariants)
Kinetic     — what changes (state, flow, actions, events)
Metric      — what we measure

+ Context   — cross-cutting annotation dimension (scope, lifecycle, provenance, LLM hints)
+ Domain    — composition mode (base ontology + extension packs)
```

Four layers plus two cross-cutting concerns. Collapsed from an earlier seven-layer draft: Structural and Graph merged (LinkML unifies them natively via `is_a` + slots); Context pulled out as cross-cutting because it applies to every element in every layer; Domain recast as a composition mode because domain concerns shape the ontology from the start rather than sitting "above" it.

**Kinetic is where the ontology comes alive** — it's where most supply chain ontologies fail to earn their keep. The Logical layer provides truth semantics (invariants); the Kinetic layer provides change semantics (state transitions, flow occurrences, actions).

---

## 3. First-class constructs

Beyond classes, slots, and enums (which LinkML already gives us), the ontology introduces the following first-class constructs. **All are realized as LinkML classes** — there are no top-level `flows:` / `events:` / `axioms:` blocks. Composition is class-centric: everything is a class, everything that needs dispatch carries an `instantiates:` tag, and extension semantics live in annotations. See §6 for the implementation mechanism, the JSON-in-string convention, and the exploder tool that consumes it.

### 3.1 Role

A logical actor that entities can fulfill. `demand_planning`, `procurement`, `inbound_dock`. Flows bind to roles, not concrete entity types, so handoffs are reusable across any entity that can play a given role. Roles are the abstraction that lets the orchestrator reason about handoffs without hardcoded point-to-point routing.

**Boundary roles.** Some roles represent *external* participants — functions outside the supply chain that send signals in or receive signals out. Commercial/trade (source of promo commitments), co-manufacturers (recipients of volume shifts), regulatory bodies, finance. The ontology declares boundary roles as thin shells — a description and `llm_prompt_hint` are usually enough — so flows that cross the SC boundary can name them as source or target. The ontology does not model boundary roles' internals; that is outside its scope. This pattern is how external signals enter the ontology's reasoning surface without forcing us to model the external function, and it generalizes to any cross-boundary signal source (customer orders from sales, cost targets from finance, regulatory changes from legal). A role is marked as a boundary role via an `is_boundary: true` field in its `scont:role` annotation body.

### 3.2 Event

A first-class happening the ontology can observe or trigger on. `demand_anomaly_detected`, `procurement_infeasible`, `shipment_dispatched`. Events are the glue between flows — one flow's completion can be the event that triggers another. They also represent external signals entering the system.

### 3.3 Flow — the primary orchestration surface

A **flow** is a typed, directed, stateful handoff between roles, carrying a **quantum** (a payload object with its own lifecycle).

**This is the single most important design decision in the session.** The agent orchestrator consumes flows to answer "who hands off to whom, with what payload, under what conditions." No capability manifest is required — the orchestrator reads flows from the ontology and binds them to its own execution substrate.

#### Flow shape (conceptual)

```yaml
Flow:                         # abstract parent
  kind: information | material | cash   # concrete subtypes below
  source: Role
  target: Role
  quantum: <class>            # the typed payload that moves
  trigger: <event>            # what causes an occurrence
  lifecycle:
    quantum_state: <FSM>       # the quantum's business state machine
    occurrence_state: <FSM>    # the flow instance's execution state
    coupling: linked | independent   # default: linked
  invariants: [<axiom>]       # flow-scoped axioms (see §4)
  dependencies: [<flow>]      # other flows that must precede
```

This is the *conceptual* shape. The LinkML realization — a class tagged `instantiates: [scont:InformationFlow]` with a JSON-in-string `scont:flow` annotation carrying the body — is in §6.1.

#### Three concrete subtypes

| Subtype | Conservation | Reversibility | Notable future slots |
|---|---|---|---|
| `InformationFlow` | not conserved (copyable) | editable until committed | freshness, authority, versioning |
| `MaterialFlow` | mass-conserved minus loss | physical, hard to reverse | lot tracking, chain of custody, handling conditions |
| `CashFlow` | value-conserved, directional | settlement-final | currency, fx rate, reversal windows |

Subtypes chosen over a flat `Flow` class with conditional slots because the kind-specific semantics will grow over time and would otherwise pollute the common interface.

**Service flow** is the canonical next addition and the sanity-check target for the abstract parent shape — if adding Service would force a refactor, the parent is factored wrong. Service is out of POC scope but the interface must not preclude it.

#### Quantum state vs. flow-occurrence state

Two distinct FSMs, defaulted to collapsed:

- **Quantum state** = business state of the thing that flows (`ProcurementRequest` is `draft | submitted | approved | ...`). Intrinsic to the object.
- **Flow-occurrence state** = execution state of a specific running flow instance (`pending | in_progress | completed | failed | cancelled | retrying`). Meta-level.

Usually they move in lockstep. But they can diverge (retries, orchestrator-initiated pauses, multi-occurrence flows touching one quantum). Modeled separately so the distinction survives, collapsed by default via `coupling: linked` so POC declarations stay small. Flip to `coupling: independent` when a flow needs its own occurrence FSM.

#### Flow distinguished from relation

- A **relation** like `supplies(Supplier, SKU)` describes *capability* — static structure.
- A **flow** like `submit_procurement_request` describes *occurrence* — a stateful, temporal event with a payload.

Enforcement is schematic: a flow **must** have a quantum, a trigger, and a direction. If you can't name those, you have a relation, not a flow. The exploder catches this trivially.

#### Query flows vs handoff flows — declared via `returns:`

Some flows transfer responsibility from source to target (a *handoff*: procurement hands a PO off to supplier_management). Others are request-response: an agent asks another role a question and *retains* responsibility (supply_planning asks logistics_planning for an OTIF exposure calculation and uses the answer in its own decision). We revisited this after the early POC made clear that agent teams in a separate repo will read the ontology cold, where a prose-only signal ("the hint tells you it's a query") is not robust enough.

**Decision: the flow body carries an optional `returns: <ClassName>` field.** Presence → query flow, and the response shape is the named class. Absence → handoff flow. This is an explicit, machine-validatable schema signal: the exploder resolves `returns:` to a declared class and errors if it does not. The `returns:` field is defined in `scont_meta.yaml` (`FlowBody`) and surfaced on `ResolvedFlow.body.returns`. Query flows are still modeled as `InformationFlow` at the LinkML level — the distinction is purely a field on the flow body, not a subclass or a new tag.

The `llm_prompt_hint` on a query flow still documents *how* the response flows (synchronous, timeout, retries) because that is agent execution semantics and remains the orchestrator's concern. The schema declares *what* the response is; the hint describes *how* to use it. Both stay in scope.

The earlier draft's "non-decision" (hint is the only signal) is superseded by this decision.

### 3.4 Axiom

A statement that must be true, scoped to a class or a flow (the two forms of Logical layer attachment — a class invariant describes what the thing must *be*; a flow invariant describes what a handoff must *respect*). Axioms live as annotations on the class or flow they apply to, not in a separate top-level block. See §4 for notation and §6.1 for the class-centric realization.

### 3.5 Metric

Measurement definitions. For now, ontology-native (`source: local`). Shaped to be promotable to dbt semantic layer without a rewrite (see §5).

### 3.6 Context (cross-cutting annotation)

Every element — class, slot, flow, event, axiom, metric — can carry:

- **Scope**: business unit, region, tenant, environment
- **Temporal validity**: `valid_from` / `valid_to`
- **Status**: `draft | proposed | approved | deprecated`
- **Provenance**: author (human or agent ID), source commit, rationale
- **Confidence**: human-authored vs. agent-proposed with a score
- **`llm_prompt_hint`**: a per-element hint written specifically to guide LLM navigation of *that element* — its quirks, join patterns, traversal semantics, gotchas, common misreadings to avoid. Adopted from the `pcg.yaml` convention, where it is load-bearing for LLM reasoning over the ontology. Every concept the LLM might have to reason about should carry one.

This is the substrate for future self-healing (agents propose diffs as `status: proposed` with full provenance) and for change management more broadly. Context is cross-cutting rather than a layer because it applies everywhere and would duplicate if modeled as a layer.

### 3.7 Human involvement — where humans enter the agent loop

The ontology declares which roles and situations may require human input; the orchestrator decides when and how. This hybrid split was chosen after weighing framework conventions against workflow-specification conventions.

- Agent frameworks (LangGraph, CrewAI, AutoGen, Google ADK) uniformly treat human-in-the-loop as a runtime/framework-level concern (interrupts, `human_input=True`, `UserProxyAgent`, callback hooks). Domain models don't participate.
- Workflow specification standards (BPMN `UserTask`, CMMN discretionary tasks, DMN decision tables) make the locus of human involvement a first-class element of the process definition — the *where* is domain knowledge; only the *how* (assignment, UI, notification, SLA) is runtime.
- The human-agent teaming literature (Sheridan, Parasuraman on Levels of Automation) argues explicitly against runtime-only autonomy boundaries: if the system decides at runtime when to involve humans based on confidence scores alone, boundaries become unpredictable and erode trust. The envelope of permissible autonomy should be declared at design time.

For this ontology, the workflow-specification side wins. Execs need to know in advance which decisions the system makes autonomously versus which surface to a human. That is design-time domain knowledge — ontology content — not runtime policy.

**The split:**

- **Ontology declares (domain truth):**
  - Which roles may require a human actor — via a `human_involvement: required | conditional | autonomous` field in the `scont:role` annotation body.
  - What context an agent should assemble before surfacing a decision — expressed through *query flows* connecting the role to affected domains (see §3.3).
  - What resolution flows are available — the options the human or agent chooses between.

- **Orchestrator owns (execution semantics):**
  - How to reach the human (UI, Slack, email, Teams).
  - Autonomy thresholds (financial exposure > $X → always escalate; below $Y with a single clear path → resolve autonomously).
  - SLA timers, timeout policies, escalation ladders.
  - Confidence-based fallbacks.

Structurally, escalation to a human is identical to any other flow routing. The ontology does not care whether a role is played by an agent or a human — it declares a role, flows connect roles, and the orchestrator binds roles to actors at runtime. This preserves the ontology's neutrality toward orchestration specifics and mirrors BPMN's `UserTask` pattern: the declaration lives in the process definition; task assignment and notification are the engine's concern.

The annotation is deliberately minimal for POC — one enum field on the role body. Richer shapes (explicit escalation criteria, decision-surface templates) can be added when a real orchestrator's needs inform them. The behavioral richness lives in the role's `llm_prompt_hint`, which describes how the agent-in-role should assemble context and present a decision surface when escalation is indicated.

---

## 4. Axiom notation — hybrid `expr:` + `nl:`, two tiers

**Decision: dual-form axioms in two tiers.** Tier 1 uses native LinkML features where possible; Tier 2 uses annotation-carried axioms for anything the native layer can't express.

### Tier 1 — native LinkML `rules:` for simple class-level invariants

LinkML already supports preconditions/postconditions on classes via the `rules:` block, with `slot_conditions`, `equals_string`, `pattern`, `any_of`, `all_of`, `minimum_value`, `maximum_value`, and related constraints. Simple class-level invariants ("if species=horse then colour must be in RedGreen") drop into this block natively, get validated by LinkML's own validator, and get compiled to Pydantic `@validator` decorators by LinkML's Pydantic generator. Zero extension work, maximum tooling leverage.

### Tier 2 — annotation-carried axioms for flow-scoped and complex invariants

Anything the native `rules:` block can't express cleanly — flow-scoped invariants, cross-entity path traversal, invariants that need to reference metrics or other flows, invariants best read in natural language — lives as a JSON-in-string annotation on the class or flow it applies to. The body of a single axiom looks like:

```json
{
  "name": "respect_lead_time",
  "scope": "flow",
  "expr": "{quantum.required_by} >= today() + {quantum.supplier.lead_time}",
  "nl":   "A procurement request's required-by date must not fall inside its supplier's lead time.",
  "severity": "blocking",
  "message":  "Required-by date is inside supplier lead time",
  "references": {
    "metrics": ["supplier.lead_time"]
  }
}
```

- **`expr:`** — uses LinkML's native **`equals_expression` syntax** (a Python-subset expression language already built into LinkML, used for slot inference). Slot names in curly braces, evaluates to `None` on missing values, Python-like operators/comparisons. **No custom parser required** — we reuse LinkML's existing expression machinery.
- **`nl:`** — natural-language statement. Always present. Read by LLM-based validators and by agents as context. Handles cases the deterministic evaluator can't cover. Graceful degradation when the ontology schema evolves underneath an axiom.

See §6.1 for how a list of axiom bodies attaches to a class or flow (via a JSON-in-folded-string annotation).

### Why this shape

- Transpilation to SQL/Cypher is **not** a hard requirement — LLMs handle that at runtime, and there's an existing working POC for LLM-validated LinkML ontologies over data fields.
- `equals_expression` is **already the Python-subset expression language** we would have had to build from scratch. Zero custom parser/evaluator work.
- Two-tier keeps simple invariants in pure native LinkML (full validator + Pydantic compilation) while routing flow-scoped and complex axioms through the annotation form.
- `nl:` is the form that survives schema refactors — it degrades gracefully where `expr:` breaks.
- Python-native matters; CEL was considered and rejected (alien to Python devs, mediocre embedding ergonomics).

### Two reasoning modes — how agents consume axioms

Axioms and their surrounding flows support two distinct reasoning modes. Both use the same ontology surface; what differs is the agent's behavior.

**Mode 1 — Hard gates.** A blocking axiom fires, its `on_failure_route_to` declares the recovery flow, and the agent follows that route without judgment. `respect_lead_time` is the canonical example: a required-by date inside supplier lead time is unambiguously infeasible, and the routing to `replan_on_infeasible_request` is predetermined. No cross-domain context is needed — the axiom body has everything. Deterministic, autonomous.

**Mode 2 — Context assembly for judgment calls.** Some conflicts have no predetermined resolution. A line capacity conflict during a promo surge could resolve via co-manufacturer shift, promo renegotiation, accepting OTIF penalties, or reducing promo volume — and the right answer depends on cross-domain context (OTIF exposure at the affected retailer, co-man availability, promo commitment status). Here the ontology does not declare *the* resolution. It declares *what context an agent needs to gather and from whom* — expressed through query flows (§3.3) from the mediating role (typically a supply/netops role) to each affected domain. The consuming agent reads the connected flows, queries each domain, assembles quantified trade-offs using declared metrics, and then either resolves autonomously (when the orchestrator's autonomy policy permits) or presents the decision surface to a human (§3.7). The LLM provides judgment; the ontology provides the information architecture for the decision.

Both modes are first-class. The POC demo (§7) exercises both: a `line_capacity_not_exceeded` axiom as a hard gate, followed by context assembly at `supply_planning` to resolve the trade-off. The axiom still fires deterministically; what happens next is where the two modes diverge.

The practical implication for ontology authoring: axioms that point to a single unambiguous recovery declare `on_failure_route_to`. Axioms that open into a judgment space — typically when multiple functions are affected — route to a mediating role whose `human_involvement` annotation and `llm_prompt_hint` describe the context-assembly pattern.

---

## 5. Metrics and dbt semantic layer alignment

**Current reality:** dbt semantic layer is a future enterprise target, not currently deployed at scale. The ontology is the **authoritative metric source for now**.

**Design discipline:** shape metrics so that future promotion to dbt is a translation, not a rewrite. Borrow MetricFlow's vocabulary (`measure | dimension | metric`, native aggregations, time grains, entities).

```yaml
metrics:
  supplier_lead_time:
    source: local              # local | dbt
    kind: measure              # MetricFlow-compatible
    entity: Supplier           # maps to dbt semantic model on promotion
    aggregation: avg
    time_grain: day
    unit: days
    definition: "Average elapsed days from PO acknowledgment to shipment dispatch"
    promotion_target: dbt      # flags as a candidate for upstream migration
```

Classes can carry `dbt_semantic_model:` alignment annotations. A lint rule validates that class keys and shared dimensions agree with the referenced dbt semantic model. This is a pre-commit/CI check, not a runtime dependency.

**Escape hatch:** when a metric eventually moves upstream, it flips to `source: dbt, ref: {semantic_model: X, metric: Y}`. The ontology holds the *context* (which flow uses it, which axioms reference it); dbt holds the *definition*. At POC time this path exists in the schema but isn't exercised.

---

## 6. Implementation mechanism in LinkML

All of §3's first-class constructs are additions layered on vanilla LinkML. We follow the convention proven in `pcg.yaml`: lightweight `instantiates:` tags as type discriminators, complex structured content stored as JSON-in-folded-string annotations, and a Python-side exploder that parses and validates the extension shapes.

### 6.1 The extension pattern — four principles

1. **Class-centric.** Everything is a LinkML class. No top-level `flows:` / `events:` / `axioms:` blocks. Roles are classes. Events are classes. Concrete flows are classes. State machines are classes. Composition happens through LinkML's existing `imports:` and `is_a` mechanisms.

2. **`instantiates:` is a type discriminator, not a shape constraint.** Its role is to tell downstream tooling (the exploder, the validator, the LLM prompter) what *kind* of thing a class is so they can dispatch to the right handler. It is **not** used for LinkML 1.6+ enforced metaclass-extension shape constraints — we don't lean on enforcement that LinkML's validator doesn't yet implement. Real shape validation lives in the Python exploder (§6.6).

3. **Plain entities skip `instantiates:`.** A class with no `instantiates:` is by default a plain structural entity (`Supplier`, `SKU`, `ProcurementRequest`). Only meta-typed constructs (Role / Event / Flow / StateMachine / standalone Axiom) carry the tag. This keeps the schema clean — the majority of classes in any supply chain ontology are entities, and spamming `instantiates: [scont:Entity]` on every one is ceremony without value. The exploder's rule: *if `instantiates:` is present, dispatch on the tag; if absent, treat as a plain structural entity.*

4. **Complex structured content lives in JSON-in-folded-string annotations.** Simple scalars stay flat YAML (`scont:domain: procurement`, `scont:subdomain: sourcing`). Structured bodies — flow config, state machines, axiom lists, action lists, metric lists — are stored as JSON strings via YAML's `>-` folded-block scalar. From LinkML's perspective they're opaque strings (zero round-trip risk, no nested-annotation edge cases); the exploder parses the JSON at access time; the LLM parses the JSON natively when the whole schema is consumed as context.

#### Worked example

Here's what a concrete flow and its supporting elements look like end-to-end:

```yaml
# core.yaml — lightweight documentation shells for the tags
classes:
  Role:
    description: >-
      A logical actor that entities can fulfill. Flows bind source and target
      to roles so handoffs are reusable across any entity playing that role.

  Event:
    description: >-
      A first-class happening the ontology can observe or trigger on.

  Flow:
    abstract: true
    description: >-
      A directed, stateful handoff between roles carrying a typed quantum.

  InformationFlow:
    is_a: Flow
    description: >-
      A flow whose quantum is not conserved (copyable); freshness and authority
      are the relevant invariants.

  MaterialFlow:
    is_a: Flow
    description: >-
      A flow whose quantum is physical and mass-conserving minus loss.

  CashFlow:
    is_a: Flow
    description: >-
      A flow whose quantum is value-conserving, directional, and settlement-final.

  StateMachine:
    description: >-
      A finite state machine: states, transitions, initial, terminal.

# supply_chain_demo.yaml — the instantiation
imports:
  - linkml:types
  - core

classes:

  # A plain entity — no instantiates, no ceremony
  ProcurementRequest:
    description: "The quantum carried by the demand→procurement flow"
    slots:
      - triggering_signal
      - sku
      - quantity
      - urgency
      - required_by
      - status

  # A role
  demand_planning:
    instantiates: [scont:Role]
    annotations:
      scont:role: >-
        {
          "description": "Forecasts demand, detects anomalies, revises plans",
          "llm_prompt_hint": "This role owns demand-side signals; it emits ProcurementRequest quanta to procurement when anomalies are detected."
        }

  # An event
  demand_anomaly_detected:
    instantiates: [scont:Event]
    annotations:
      scont:event: >-
        {
          "description": "A statistically significant departure from forecast for a SKU",
          "observed_by": "demand_planning",
          "llm_prompt_hint": "Fires when demand signal deviates materially from forecast; triggers submit_procurement_request."
        }

  # A state machine
  RequestLifecycle:
    instantiates: [scont:StateMachine]
    annotations:
      scont:state_machine: >-
        {
          "states": ["draft", "submitted", "approved", "rejected", "expired"],
          "transitions": [
            {"from": "draft",     "to": "submitted", "trigger": "submit",   "guard": null},
            {"from": "submitted", "to": "approved",  "trigger": "approve",  "guard": "respect_lead_time"},
            {"from": "submitted", "to": "rejected",  "trigger": "reject",   "guard": null}
          ],
          "initial":  "draft",
          "terminal": ["approved", "rejected", "expired"]
        }

  # A flow — the primary orchestration surface
  submit_procurement_request:
    instantiates: [scont:InformationFlow]
    annotations:
      scont:flow: >-
        {
          "source_role":   "demand_planning",
          "target_role":   "procurement",
          "quantum":       "ProcurementRequest",
          "trigger_event": "demand_anomaly_detected",
          "lifecycle_ref": "RequestLifecycle"
        }
      scont:axioms: >-
        [
          {
            "name": "respect_lead_time",
            "scope": "flow",
            "expr": "{quantum.required_by} >= today() + {quantum.supplier.lead_time}",
            "nl":   "A procurement request's required-by date must not fall inside its supplier's lead time.",
            "severity": "blocking",
            "message":  "Required-by date is inside supplier lead time",
            "references": {"metrics": ["supplier.lead_time"]}
          }
        ]
      scont:llm_prompt_hint: >-
        Happy-path information flow from demand planning to procurement. Fires on
        demand_anomaly_detected. Blocking axiom respect_lead_time routes to
        replan_on_infeasible_request on failure.
```

Notice:

- `ProcurementRequest` is a plain entity — no `instantiates:`, just real LinkML slots. It generates a normal Pydantic class.
- `demand_planning`, `demand_anomaly_detected`, `RequestLifecycle`, and `submit_procurement_request` each carry `instantiates:` tags pointing at core meta-classes. Their semantic content is in JSON-in-folded-string annotations whose shape the exploder knows.
- Flow subtyping is resolved through `core.yaml`'s `is_a` hierarchy (`InformationFlow is_a Flow`), so the exploder can ask "is this some kind of Flow?" by walking ancestors instead of enumerating subtypes.
- No top-level `flows:` / `events:` / `axioms:` blocks. Everything is class-centric.
- Every meta-typed class carries a `llm_prompt_hint` either inline in its body or as a top-level `scont:llm_prompt_hint` annotation.

### 6.2 Runtime: LinkML Pydantic generator + exploder

LinkML's Pydantic generator compiles `classes` (with slots, inheritance, rules) to Pydantic `BaseModel` classes. For our purposes:

- **Plain entities** (no `instantiates:`, real slots) generate full Pydantic classes with field constraints and validators. Instance-data validation is direct: `ProcurementRequest(**data)`.
- **Meta-typed classes** (with `instantiates:` and JSON-in-string annotations) generate thinner Pydantic classes — the JSON strings become string attributes. The **exploder** parses those strings into typed structured objects (Flow, Role, Event, StateMachine, Axiom) at read time.

```
LinkML YAML  →  Pydantic models (build time)  →  validate entity instance data (runtime)
             →  Exploder parses JSON-in-string annotations
                                              →  structured Flow / Role / Event / StateMachine / Axiom objects
             →  LLM evaluates `nl:` axioms at runtime
             →  LLM consumes whole schema (or exploder's resolved JSON view) as context for reasoning
```

Python-native requirement satisfied. The existing LLM-validation POC slots directly into the `nl:` evaluation and whole-schema-reasoning sides.

### 6.3 Load-bearing concerns — status after pcg evidence

The earlier draft flagged four failure modes for the `instantiates` + annotation pattern. Reviewing `pcg.yaml` — a 3020-line virtual-twin ontology using exactly this pattern and demonstrably working with the existing LLM-validation POC — resolves most of them:

| Concern | Status |
|---|---|
| **Nested structured annotations** | ✅ Resolved. The JSON-in-folded-string convention sidesteps LinkML's annotation round-trip entirely. `pcg.yaml` uses this for state machines, axioms, actions, measures, metrics, and flow configs. |
| **Validation enforcement gap** | ✅ Sidestepped. Nothing structural is expressed to LinkML beyond opaque strings, so there is nothing for LinkML to fail to enforce. All validation lives in the Python exploder, which we were going to own anyway. |
| **Pydantic generator round-trip** | ✅ Non-issue for semantics. The generator sees a string attribute and does nothing weird with it. Semantic consumption is via the exploder, not via generated Pydantic fields. |
| **LLM validator compatibility** | ✅ Empirically proven. `pcg.yaml` uses this pattern with the user's existing LLM stack and it works well. |

One narrower concern remains: does this pattern work *as well* for abstract orchestration concepts (roles, flows, axioms as handoff gates) as it does for the virtual-twin-over-SQL content `pcg.yaml` demonstrates? That is what the focused spike in §10 validates.

### 6.4 Fallback — dual declaration

No longer load-bearing. If some unexpected failure surfaces during the §10 spike, the dual-declaration fallback (express extension structure through real LinkML slots rather than annotations) remains available. We are not designing around it, and we do not expect to need it.

### 6.5 The exploder — an explicit POC deliverable

The exploder is a small Python module that reads the LinkML YAML, walks classes, dispatches on `instantiates:` tags, parses the JSON-in-folded-string annotations, and produces three outputs:

1. **A structured object model.** Pydantic (or dataclass) representations of `Role` / `Event` / `Flow` / `StateMachine` / `Axiom`, with typed fields and resolved cross-references. This is the programmatic surface for any Python-side consumer — validators, generators, the orchestrator's ontology-reader, the demo's test harness.

2. **A resolved JSON view.** A flat, fully-expanded alternative form of the ontology (no JSON-in-string nesting, no `instantiates:` indirection, cross-references inlined where useful). Used as an alternative LLM context format if the raw YAML proves awkward for the LLM in our specific use case. Gives us an experimental knob to pull without changing the authoring format.

3. **A shape validator.** Checks each tagged class's annotations against the expected extension shape. Raises on missing required fields, type mismatches, and dangling references (a flow whose `source_role` doesn't resolve to a declared Role, a trigger that points at an undeclared Event, an FSM `lifecycle_ref` that doesn't resolve, an axiom body referencing a metric that doesn't exist, etc.). This is the Python-side closure of what LinkML's own validator doesn't yet enforce.

**Rough scope:** ~150 lines of Python for the first cut (parser + object model + basic validator). The resolved JSON view adds maybe another 50 lines. The validator grows as the schema grows.

**Why we build it now, not later:** it's the Python-side interface to the ontology, and it will exist one way or another — either written deliberately as a small, focused module, or accreted as scattered helpers across wherever the ontology gets consumed. Deliberate is cheaper.

---

## 7. Demonstration scope

**Authoritative content plan:** [`demo_narrative.md`](./demo_narrative.md). This section captures the meta-level criteria the demo must satisfy; the narrative specifies the concrete roles, flows, axioms, entities, and story beats. The two documents have different scopes — this design draft specifies the ontology's language and mechanism; the narrative specifies the content we're writing with it.

### Meta-level criteria the demo must satisfy

- **Cross-domain.** The demo must exercise agents navigating at least three supply chain functions (demand, supply/netops, manufacturing, procurement, logistics, customer service) plus at least one boundary role. A single-domain relay does not demonstrate the ontology's value.
- **Both reasoning modes.** The demo must exercise both hard-gate axioms (§4 / Mode 1) and context-assembly flows with a mediating role (§4 / Mode 2), so the ontology's full reasoning surface is visible.
- **Both autonomy levels.** The demo must exercise autonomous resolution (agent follows `on_failure_route_to` without human input) and assisted resolution (agent assembles context, surfaces decision to a human). §3.7 is the mechanism.
- **Realistic for the target vertical.** The POC targets CPG oral/personal/home care (model: P&G, Colgate). The narrative is grounded in that vertical's actual coordination failures so it lands with execs who know these pains.
- **Live execution.** Agents running against this ontology must be able to complete the scenario end-to-end. The orchestrator and agents are a separate build; this ontology is their source of truth. That raises the precision bar: every role, flow, axiom, and `llm_prompt_hint` must be accurate enough that an agent reading it cold makes correct routing decisions.

### Chosen scenario — promo whiplash

A retailer BOGO commitment (Walmart, Product A) enters the supply chain via S&OP alignment from a `customer_development` boundary role. Demand planning revises the forecast and hands off to supply/netops, which assigns production to a specific plant and line. Manufacturing detects that the promo volume collides with a standing commitment for Product B on the same line — total demand at 120% of capacity — and a `line_capacity_not_exceeded` axiom fires (hard gate). Supply/netops receives the escalation and assembles cross-domain context via query flows: OTIF exposure at Target from `logistics_planning`, promo flexibility from `customer_development`, co-manufacturer availability from a `co_manufacturing` boundary role. The assembled decision surface is either resolved autonomously or surfaced to a human planner depending on the orchestrator's autonomy policy; in the scripted demo path the resolution is a co-manufacturer shift for Product B, freeing the internal line for the promo volume while preserving Target's OTIF commitment.

Spans five SC functions plus two boundary roles. Exercises both reasoning modes and both autonomy levels. Full beat-by-beat and content inventory in `demo_narrative.md`.

**Executive framing:** "A promo commitment hit a capacity wall. Within minutes, agents across five functions assembled the full cross-domain impact — OTIF exposure at Target, co-manufacturer availability, promo flexibility with Walmart — with quantified trade-offs. A human planner saw the complete picture and made the call. No one built a dashboard for this scenario. The ontology declared the domains, the constraints, and the information the decision-maker needs; the agents navigated it. That's what an autonomous supply chain looks like — not replacing human judgment, but making sure every decision has complete, cross-functional context in minutes instead of days."

---

## 8. What's tabled (intentionally)

- **Proposal protocol for self-healing / meta-ontology build rules.** Revisit once a working ontology exists. The hook point is the Context annotation dimension — every element already carries `status`, `provenance`, `confidence`, which is the metadata a future proposal protocol needs. We are not painting ourselves into a corner as long as Context stays cross-cutting and extensible.
- **Live dbt semantic layer resolver.** Future, when dbt is deployed at scale. For now, alignment is design-time only.
- **Additional flow kinds beyond info/material/cash.** Service is the canonical next addition and the parent-shape sanity check. Out of POC scope.
- **Action semantics beyond declaration.** Actions are declared as affordances with pre/post conditions; binding to actual tools is orchestrator-side, out of scope.
- **Navigation tools / graph-query backends.** Neo4j + Cypher and dedicated navigation tools are scale answers. The POC works with whole-schema context consumption; we revisit if scale or coherence issues appear.

---

## 9. Open points — closed by POC

All original open points from the pre-spike draft are now resolved. This section is kept as a historical record of what had to land before we could commit to the pattern. Forward-looking work is in §13.

1. ~~**Run the focused spike in §10.**~~ ✅ Done — all three LLM-reasoning questions passed on first run. See §11.
2. ~~**Concrete annotation shapes**~~ ✅ Done — shapes for `scont:role`, `scont:event`, `scont:flow`, `scont:state_machine`, `scont:axioms` are documented as prose on the meta-classes in `core.yaml` and enforced by the exploder's cross-reference validator.
3. ~~**FSM representation — confirm shape.**~~ ✅ Done — `RequestLifecycle` in `supply_chain_demo.yaml` demonstrates the `{states, transitions: [{from, to, trigger, guard}], initial, terminal}` shape and the exploder validates its internal consistency.
4. ~~**Axiom unification.**~~ ✅ Done — a single axiom body shape with `scope: "class" | "flow"` is in use. Tier-1 native `rules:` and Tier-2 annotation-carried axioms coexist without conflict.
5. ~~**File layout.**~~ ✅ Done — three files at repo root: `core.yaml`, `supply_chain_demo.yaml`, `exploder.py`. Plus the primer (`ontology_primer.md`) that emerged as a fourth deliverable once we saw how much scaffolding the LLM needed.

---

## 10. De-risking spike — plan (completed)

This section is kept as a historical record. The spike ran and passed; results are in §11.

**Spike scope:**

1. **Write a minimal supply-chain ontology fragment** in the pcg style: one flow (`submit_procurement_request`), its quantum (`ProcurementRequest`), one role pair (`demand_planning` / `procurement`), one FSM (`RequestLifecycle`), one event (`demand_anomaly_detected`), and one blocking axiom (`respect_lead_time`). ~60 lines of YAML.
2. **Start writing the exploder.** Even the bare parse-and-produce-Python-objects version is enough for the first pass; shape validation and the resolved JSON view follow.
3. **Feed the fragment whole-cloth into the existing LLM validator / reasoning stack** and test three questions:
   - **Q1.** *"Given a candidate `ProcurementRequest` instance, does the axiom `respect_lead_time` fire?"* — tests Logical-layer reasoning.
   - **Q2.** *"When `submit_procurement_request` is in 'submitted' state, what role should the orchestrator route to next?"* — tests Kinetic-layer traversal.
   - **Q3.** *"If the axiom fires, what flow should fire instead?"* — tests that the unhappy-path routing is legible from the ontology alone.

**Decision gates:**

- ✅ **LLM reasoning succeeds on all three** → proceed to full `core.yaml` + `supply_chain_demo.yaml` with confidence. The exploder grows into a development aid, validator, and orchestrator-side interface. **This gate tripped.**
- ⏸ Kinetic-layer traversal is shaky → use the exploder's resolved JSON view as the primary LLM context format. *(Not triggered.)*
- ⏸ Logical-layer axiom firing is shaky → strengthen the `nl:` prose, add `llm_prompt_hint` on axiom entries themselves, retry. *(Not triggered.)*
- ⏸ Something unexpected breaks → revisit §6.4 fallback. *(Not triggered.)*

---

## 11. Spike results and learnings

Context given to the LLM: `ontology_primer.md` + `core.yaml` + `supply_chain_demo.yaml` (whole-schema stuffing). Three questions asked, answers analyzed below.

### Q1 — Does `respect_lead_time` fire for a given instance?

**Answer (correct):** Yes — fires as a blocking violation.

The LLM evaluated the `expr` body (`{quantum.required_by} >= today() + {quantum.supplier.lead_time}`), substituted the given values (`200 >= 180 + 30`), computed `200 >= 210 → false`, and correctly identified that the axiom's `severity: blocking` means the orchestrator must invoke the recovery route named in `on_failure_route_to`. This is the straightforward case — the axiom body is right there and the arithmetic is trivial — but it confirms the **Tier-2 annotation-carried axiom** reads cleanly from whole-schema context.

### Q2 — Where does the orchestrator route when the quantum is in 'submitted'?

**Answer (correct):** To the `procurement` role.

Read from `submit_procurement_request.scont:flow`: `source_role: demand_planning` / `target_role: procurement`. The `submitted` state is the handoff point.

**The interesting part:** the LLM went further than the question required. It noted that *"the next transition, `submitted → approved`, is guarded by `respect_lead_time` and is procurement's responsibility to attempt."* That's a four-hop traversal:

```
FSM transition "submitted → approved"
  → "guard": "respect_lead_time"
  → (recognized as an axiom name by convention)
  → axiom defined on submit_procurement_request with severity: blocking
  → "procurement's responsibility because target_role is procurement"
```

The LLM inferred this without the primer or the ontology explicitly stating "guards on FSM transitions resolve to axiom names defined on the parent flow." It was legible from name convergence alone.

### Q3 — What flow fires instead when the blocking axiom triggers?

**Answer (correct):** `replan_on_infeasible_request`.

Read directly from the axiom body's `on_failure_route_to` field. The LLM then resolved that flow's body and correctly described its shape: reversed direction (`procurement → demand_planning`), same quantum (`ProcurementRequest`, preserving context), new trigger event (`procurement_infeasible`), same lifecycle FSM. A clean two-hop resolution.

### What we learned

1. **The extension pattern works for abstract orchestration content**, not just the virtual-twin-over-SQL content that `pcg.yaml` demonstrated. This was the narrower concern remaining after pcg validated the pattern; it's now also resolved.
2. **`ontology_primer.md` + `core.yaml` + the demo file together are sufficient context** for the LLM to answer meaningful questions about the ontology without hallucination or missed cross-references. The primer was well worth writing.
3. **The LLM reasons about the ontology more deeply than prompt engineering alone would predict.** Q2's guard-to-axiom resolution was a genuine piece of inference chain, not a lookup. This strongly suggests the pattern will hold under wider variation than we tested — the LLM is understanding structure, not pattern-matching on field names.
4. **`llm_prompt_hint` pays for itself.** Every concrete role / event / flow in the demo carried a hint; the LLM's answers quoted from them verbatim in several places. They are load-bearing, not decorative.
5. **`on_failure_route_to` as an axiom-level field is the right shape** for orchestrator recovery routing. Explicit, no-guessing, validated by the exploder. Keep it.

### One subtlety the spike exposed

**FSM transition guards are named strings that happen to resolve to axiom names — a convention, not an enforced relationship.** In the demo, `RequestLifecycle`'s `submitted → approved` transition has `"guard": "respect_lead_time"`, which matches the name of the Tier-2 axiom on `submit_procurement_request`. The LLM resolved this correctly, but nothing in the ontology or the exploder validates that guards must resolve to declared axioms. If a typo slipped into the guard name, neither LinkML nor the exploder would catch it.

**Decision for POC:** leave as convention. The LLM handles it and the risk is low at current scale. Revisit when either (a) we add an agent that cannot do the inference the LLM does, or (b) we see a real bug caused by a drifted guard name. When we do tighten it, the fix is a small addition to the exploder's validator: for each FSM, walk its transition guards and confirm each resolves to a declared axiom somewhere in scope (the parent flow, the parent class, or a standalone axiom).

---

## 12. Context management — from POC stuffing to enterprise production

The current POC feeds the entire ontology (`ontology_primer.md` + `core.yaml` + `supply_chain_demo.yaml`) into the LLM's context window on every query. This is the right default *now*, was empirically validated at ~3000 lines via `pcg.yaml`, and will remain the right default for a meaningful set of usage patterns even at enterprise scale (see §12.2). But the question *"what do we do when this breaks?"* is the wrong framing. The right question is *"what shape of access do different consumers actually need, and how do we get there from here without boxing ourselves in?"*

This section lays out the thinking so that the POC decisions in §12.7 have a clear rationale and the enterprise-production path is forward-compatibly preserved.

### 12.1 The real axes — context window size is the least interesting one

When production pressure eventually forces a move off whole-schema stuffing for some use cases, the driver is almost never literal context overflow. Frontier models have enough headroom that even 10× the current ontology fits comfortably. The axes that actually bind are:

- **Cost.** Production orchestration running at transaction-scale can't afford to feed ~20K tokens on every call. Per-transaction workloads hit cost-prohibitive well before they hit context-length limits.
- **Latency.** Each stuffed call adds processing time that a synchronous orchestrator might not have.
- **Coherence.** Long contexts degrade on dense, cross-referenced content. `pcg.yaml`'s ~3000 lines works empirically; we should not assume 30K lines works equally well, and certainly not linearly.
- **Debuggability.** Tool calls produce transcripts of "what did the agent ask for and what did it get" — a YAML blob in context does not. Production incidents will want the transcript.

Frame any architecture decision around these axes, not around context window size. Context window size is the last binding constraint, not the first.

### 12.2 Hot path vs cold path — the foundational distinction

The ontology has **two fundamentally different usage modes**, each with its own architectural sweet spot. These are not alternatives; they coexist on the same ontology artifact.

**Cold path** — development, debugging, design review, demo, schema authoring and evolution, exploratory LLM reasoning about the ontology itself. Characteristics: *infrequent, panoramic (often cross-domain), cost-insensitive, latency-insensitive.* **Whole-schema context stuffing stays the default here indefinitely.** The cost is trivial when the frequency is low, the reasoning is high-value, and the agent needs full cross-domain visibility to catch design issues or explain intent. There is no migration off stuffing for the cold path, ever.

**Hot path** — runtime orchestration decisions during production. *"Does this handoff pass its gates? What flow fires next? What's the recovery?"* Characteristics: *frequent (transaction-rate), narrow (one question per call), latency-sensitive, cost-sensitive.* **This is where targeted access — tool calls, query APIs, staged retrieval — pays off.** The hot path is where production pressure lives, and it's where the §12.3 spectrum earns its keep.

This framing dissolves a false choice. We are not "migrating off stuffing as the ontology grows." We are going to keep stuffing for the cold path forever *and* build targeted access for the hot path when production materializes. Same ontology artifact, two access patterns, no migration event.

### 12.3 The spectrum of hot-path options

For the hot path, ordered from simplest to most sophisticated:

#### 12.3.1 Modular loading via domain tags

Tag every class with `scont:domain` and `scont:subdomain` (already done across the expanded demo). The consumer filters to the relevant subset before loading. Works well for domain-scoped questions; degrades at cross-domain boundaries — a meaningful fraction of supply-chain questions span domains.

**Important nuance: annotations-as-domain are cheap; files-as-domain are expensive.** Annotations give you filter-based benefits without calcifying domain boundaries. Splitting into files (`procurement.yaml`, `fulfillment.yaml`) buys versioning independence at the cost of making every cross-domain flow a file-boundary negotiation. The POC should stick with annotations until an *organizational* pressure (separate teams owning separate sections, independent release cadence, merge-conflict fatigue) justifies the split. `pcg.yaml` is 3020 lines in a single file with domain annotations — strong evidence for "annotations first, files only if you must."

#### 12.3.2 Exploder as a callable tool

Expose `exploder.py` as an agent-callable tool with query-shaped methods:

- `get_flow(name) → Flow`
- `list_flows_where(source_role=..., target_role=..., quantum=...) → list[Flow]`
- `get_axioms_for(class_or_flow_name) → list[Axiom]`
- `resolve_role(name) → Role`
- `find_flows_triggered_by(event_name) → list[Flow]`
- `traverse_state_machine(fsm_name, from_state) → list[Transition]`
- `evaluate_axiom(axiom_name, instance_data) → bool`

The agent queries the ontology the way it queries any other structured tool; only the results enter its context. The ontology itself never touches the LLM prompt on the hot path.

**The exploder is already the proto-tool.** Its current Python API is one step away from a tool interface. The query methods above are worth adding to the exploder *regardless* of whether they are ever wrapped as an LLM-callable tool — they're the shape of the orchestrator-side read API (§13.3) for any consumer, LLM or otherwise. Every method added moves us closer to production-readiness without committing to a specific consumption architecture.

#### 12.3.3 Staged retrieval — manifest plus on-demand detail

A lightweight manifest (every class name, one-line description, type, domain tag) stays in context permanently. Full definitions are fetched on demand via tool calls. Hybrid of whole-stuffing and pure tool-calling: the table of contents stays in context; details arrive when asked for. Preserves cross-domain reasoning while bounding per-query payload.

This is not the third option in a menu — **it is probably the right default hot-path answer for most production cases.** Cheaper than stuffing, more coherent than pure tool calling, and it solves the paradox described in §12.5.

#### 12.3.4 Explorer agents — delegated ontology navigation

A dedicated sub-agent whose only job is to traverse and distill the ontology for the main orchestrator. The orchestrator asks *"for this demand signal, what's the feasible path and what are the gates?"* The explorer reads the ontology (via its own context or via tool calls to the exploder), reasons, and returns a distilled answer. The orchestrator never sees raw ontology.

Makes sense when the **consumer ecosystem** has many agents with *different distillation needs* — planning asks "what's feasible?", procurement asks "what's blocked?", audit asks "who approved this and when?" A single explorer that understands the ontology deeply and serves distilled answers to multiple consumers is the cleanest abstraction for a multi-agent production system.

**The exploder is the backend; the explorer agent is a frontend you put in front of it when you need to.** The exploder doesn't change when you add an explorer agent — you're adding a ~200-line LLM wrapper that translates NL queries into exploder calls. Nothing earlier has to be rebuilt.

### 12.4 These approaches compose — they are not alternatives

The §12.3 subsections look like a menu. They are not. Modularity (annotations or files), tool calling (exploder API), staged retrieval (manifest), and explorer agents (LLM wrapper) **stack cleanly**. A mature production system uses all of them simultaneously:

```
LLM query
   ↓
Explorer agent (NL → query plan)
   ↓
Exploder query API (structured read access)
   ↓
Domain-filtered access (annotations drive selection)
   ↓
Underlying LinkML schema (single file or imports)
```

The question is not "which approach?" It is "**which layer to build first**," and that depends on which of the §12.1 axes first forces the shift. For the POC, the answer is "none of the hot-path layers — cold-path stuffing is fine and the exploder's query API is the forward-compatible thing we build anyway."

### 12.5 The paradox of pure tool calling — and how to solve it

There is a real paradox in exploder-as-tool: **to query the ontology well via a tool, the LLM has to know *what to ask*. But knowing what to ask requires knowing what's in the ontology** — which is exactly what whole-schema stuffing gives you and what pure tool calling is supposed to replace.

Two ways out:

1. **Keep a lightweight manifest in context permanently** (staged retrieval, §12.3.3). A table of contents — every class name, one-line description, type, domain tag. The LLM plans queries against the manifest; the exploder returns detail on demand. Roughly 10% of the full ontology's token weight at current scale. This is why §12.3.3 is probably the production default.
2. **Expose browse methods on the exploder** — `list_all_flows()`, `list_classes_by_domain()`, `describe_class()`. The LLM takes a couple of exploratory calls before planning the real query. Works without a pre-loaded manifest but trades a few tool calls for context weight. Reasonable when the LLM is stateful across a session.

Regardless of which path: **the primer always stays in context.** It tells the LLM *how to read* the ontology — `instantiates:` dispatch, the JSON-in-string convention, navigation recipes, semantic rules. Primer cost is bounded (~75 lines, ~1K tokens) and does not grow with the ontology. You never remove it.

The mental model for hot-path context is three layers, each at a different resolution and cost profile:

| Layer | What's in it | Approx size (current / enterprise) | Frequency |
|---|---|---|---|
| Always-in-context primer | How to read the ontology | ~75 lines / ~75 lines | Every call |
| Hot-path manifest | What exists (index) | ~30 lines / ~500–2000 lines | Every call |
| On-demand detail | Specific flows, axioms, FSMs | Variable (~10–100 lines per tool call) | Per query |

### 12.6 Tradeoffs at a glance

| Approach | Latency | Cost per query | Cross-domain reasoning | Agent complexity | Dev/debug friendliness |
|---|---|---|---|---|---|
| Whole stuffing (**cold-path default, forever**) | Fast (1 call) | High per call / low frequency | Excellent | Trivial | Excellent |
| Whole stuffing + domain-annotation filtering | Fast | Lower (subset load) | Degraded at boundaries | Low | Excellent |
| Exploder as callable tool | Slower (multi-call) | Low (fetch what you ask) | Requires query planning | Medium | Good (tool transcripts) |
| Staged retrieval (manifest + detail) | Medium | Low–medium | Good (manifest holds frame) | Medium | Good |
| Explorer agents | Slower (agent-in-agent) | Low (explorer distills) | Excellent (explorer plans) | High | Weaker (two contexts) |

### 12.7 The opinionated POC track

Aggressively conservative for now, forward-compatible for enterprise production. The goal is to deliberately avoid premature optimization while making sure nothing we do now paints us into a corner later.

1. **Keep whole-schema stuffing as the dev/debug / cold path indefinitely.** It is already working, the primer is already designed for it, and it is how we will continue to author, validate, debug, and demo the ontology. There is **no migration off stuffing** for the cold path. The question is only what the hot path looks like, and we do not need a hot path yet.

2. **Build the exploder's query API** as part of direction 4 (the orchestrator-side read API — see §13.3). Not because we need scale yet, but because the query API is useful *right now* for any non-LLM programmatic consumer, *and* it's the forward-compatible substrate for every later hot-path option. Every method added to the exploder pays off immediately as a Python API and stays useful when we eventually wrap it as a tool.

3. **Do not split the ontology into files.** Keep `scont:domain` annotations across all elements (already done this session). Files cost calcification; annotations don't. Revisit file splitting only when organizational pressure (separate ownership, independent release cadence, merge-conflict fatigue) appears — not before.

4. **Leave staged retrieval and explorer agents in the "later" drawer.** Document the shape they would take (done — §12.3.3 and §12.3.4) so a future engineer knows what to build when the time comes, but do not commit code. Each is a real project that should materialize only when an actual hot-path use case drives the requirements.

### 12.8 Build order, forward-compatibly

Given the POC track, the concrete build order:

| Step | Status | Notes |
|---|---|---|
| `scont:domain` / `scont:subdomain` annotations on every element | ✅ Done this session | Forward-compatible with modular loading and manifest generation |
| Exploder query API (`get_flow`, `list_flows_where`, …) | Upcoming in direction 4 | Useful immediately as Python API; forward-compatible with tool wrapping |
| Manifest generator in the exploder | When a hot path materializes | Writes the table-of-contents index for staged retrieval |
| Exploder wrapped as an LLM-callable tool | When cost / latency demands it on a real consumer | Thin shim over the existing API |
| Explorer agent | Only when the consumer ecosystem has multiple agents with different distillation needs | ~200-line LLM wrapper; nothing earlier has to change |
| File-level modular split | Only under organizational pressure | Not driven by tech; driven by team ownership |

Each step is independently valuable and none requires rework of earlier steps. That's what "forward-compatibly" means in practice.

### 12.9 Triggers to re-evaluate

Revisit this section when any of the following hits — and do not act before one of them does:

- **Cost** becomes a constraint — per-transaction workload at a rate that makes stuffed-context calls prohibitive.
- **Latency** becomes a constraint — synchronous orchestration where the stuffing overhead exceeds the budget.
- **Coherence** degrades — the LLM starts hallucinating or missing cross-references on whole-schema queries as the ontology grows.
- **Debuggability** demands structured transcripts — production incidents where "what did the agent see?" matters more than development flexibility.
- **Multi-consumer ecosystem** emerges — many agents with different distillation needs. This is when explorer agents start earning their keep.
- **Organizational pressure** — separate teams needing to own separate sections of the ontology independently.

Context window size, by itself, is **not** on this list. It is the least interesting axis and almost never the first constraint to bind.

---

## 13. Forward-looking work

With the spike passed and the POC foundation in place, the remaining directions split into two tracks: **finishing the demo** (so we have an exec-ready narrative) and **productizing the pattern** (so the ontology can live beyond a single demo).

### 13.1 Expand the demo ontology toward the promo whiplash narrative

*Direction 2 from the spike-completion options.*

Session 2 delivered the first phase (supporting entities, Tier-1 rules example, MetricFlow-shaped metric, third flow completing the forward chain). The next phase expands toward the promo whiplash narrative (§7 / `demo_narrative.md`): adding `supply_planning`, `production_planning`, `logistics_planning` as internal roles; `customer_development` and `co_manufacturing` as boundary roles; the handoff flows that carry the signal through the loop; the query flows that supply/netops uses to assemble cross-domain context; a `line_capacity_not_exceeded` hard-gate axiom; and the supporting entities (`TradePromotion`, `SupplyRequest`, `ProductionRequest`, `CapacityConflict`, `OTIFExposure`, `ProductionLine`, `RetailerCommitment`). Full inventory in `demo_narrative.md`.

Likely size after expansion: ~800–1200 lines of YAML. Still readable in one sitting, still a single file. Precision bar is high — agents in a separate orchestrator build will consume this cold.

### 13.2 Harden the exploder

*Direction 3.*

Current state is first-cut: parser + object model + cross-reference validator + CLI summary. Forward work:

- **Resolved JSON view** (§6.5 second deliverable) — flat, fully-expanded alternative context format for LLM consumption experiments and downstream tooling.
- **Richer shape validation** — per-construct required/optional field enforcement, enum of severity levels, better error messages with source locations.
- **Tests** — the exploder currently has no test suite; as the schema grows it needs one to stay correct.
- **Query-shaped API methods** — move toward the shape described in §12.3 so the eventual tool-wrapping is a thin shim.

### 13.3 Design the orchestrator-side read API

*Direction 4.*

The exploder gives us a Python object model for the ontology. An orchestrator (agent or otherwise) needs a *read API* over that model — a thin interface describing how code gets from "I'm routing a ProcurementRequest" to "the relevant flow is X, its target role is Y, its axioms are Z, and here's the recovery route." This is the Python-side equivalent of the LLM-context interface: same information, different consumer.

Open questions:
- Does the read API return raw dataclasses from `exploder.py`, or a higher-level orchestrator-facing view?
- How does the orchestrator find the right flow for a given intent? (By event? By quantum type? By source-target role pair? All three?)
- What's the contract for axiom evaluation — does the read API evaluate `expr` bodies, or does the orchestrator?
- Where does `llm_prompt_hint` flow through — straight to the orchestrator's LLM prompts, or filtered / rewritten first?

### 13.4 Script the full demo narrative

*Direction 5.*

Beat-by-beat sketch of what an exec sees during the demo: the input (a simulated demand anomaly), the agent's reasoning trace, the axiom firing, the recovery routing, the outcome. Working backward from this script will surface ontology gaps faster than adding content speculatively.

Rough shape:
1. **Scene 1 — Happy path.** Demand signal arrives. Demand planning agent reads the ontology, finds `submit_procurement_request`, drafts a `ProcurementRequest`. Procurement agent receives, drafts a PO, all axioms pass, PO transmitted.
2. **Scene 2 — Unhappy path.** Same setup with a required_by date inside supplier lead time. Procurement drafts the PO, `respect_lead_time` fires on validation, `on_failure_route_to` directs to `replan_on_infeasible_request`. Demand planning agent receives the replan request with the original context, revises the forecast, resubmits. Axiom passes, PO transmitted.
3. **Executive framing.** "The ontology stopped the agent from doing the wrong thing. No one wrote 'if lead_time_insufficient then route_to_replan' — the ontology declared the invariant and the recovery path, and the agents respected it. That's the pattern. Now imagine this for every handoff in the supply chain."

### 13.5 Meta — proposal protocol and self-healing

*Previously tabled (§8); flagging here for completeness.* Once the expanded demo and the read API are in place, the proposal protocol for agent-authored ontology diffs becomes the next meaningful design discussion. Not urgent — the context annotation dimension (provenance / status / confidence) is already the hook point.
