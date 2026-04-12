# Initial Design Draft — Supply Chain Ontology POC

**Status:** Early design, converging. Format choice (LinkML) validated. Extension pattern refined against a reference ontology (`pcg.yaml`) proven in the user's LLM stack. Load-bearing concerns largely resolved. No new YAML written yet.
**Purpose:** Memorialize the brainstorming session's conclusions so we can resume with shared context and avoid re-litigating settled points.

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

Two slices chosen to prove the ontology earns its keep on both the structural and behavioral axes.

### Slice 1 — Happy path: demand → procurement

```
demand anomaly detected
  → demand planning revises forecast
  → submit_procurement_request flow fires
  → ProcurementRequest quantum moves draft → submitted
  → procurement consumes the quantum, drafts a PO
```

Proves: the ontology serves as a handoff contract across functional domains; roles, flows, and quanta compose cleanly.

### Slice 2 — Unhappy path: disruption → replan

```
procurement drafts a PO
  → axiom `respect_lead_time` fires: required_by inside supplier lead time (blocking)
  → replan_on_infeasible_request flow fires
  → ReplanRequest quantum routes back to demand planning
```

Proves: **the Logical layer catches a bad handoff the orchestrator couldn't have known about on its own**. This is the single most compelling demo moment — an axiom stops the agent from doing a dumb thing, and a second flow defines the recovery path, all read from the ontology without the orchestrator "knowing" anything ahead of time.

Both slices share the `ProcurementRequest` quantum, so slice 2 reuses slice 1's ontology surface. Disproportionate narrative payoff for low incremental cost.

**Executive framing:** "autonomous bullwhip prevention" — a demand signal triggers procurement action, the ontology enforces feasibility, and a cross-functional handoff happens without human-in-the-loop for the common case.

---

## 8. What's tabled (intentionally)

- **Proposal protocol for self-healing / meta-ontology build rules.** Revisit once a working ontology exists. The hook point is the Context annotation dimension — every element already carries `status`, `provenance`, `confidence`, which is the metadata a future proposal protocol needs. We are not painting ourselves into a corner as long as Context stays cross-cutting and extensible.
- **Live dbt semantic layer resolver.** Future, when dbt is deployed at scale. For now, alignment is design-time only.
- **Additional flow kinds beyond info/material/cash.** Service is the canonical next addition and the parent-shape sanity check. Out of POC scope.
- **Action semantics beyond declaration.** Actions are declared as affordances with pre/post conditions; binding to actual tools is orchestrator-side, out of scope.
- **Navigation tools / graph-query backends.** Neo4j + Cypher and dedicated navigation tools are scale answers. The POC works with whole-schema context consumption; we revisit if scale or coherence issues appear.

---

## 9. Open points to close before writing production YAML

1. **Run the focused spike in §10.** Gate every subsequent item on this.
2. **Concrete annotation shapes** for each tag — what fields `scont:role` / `scont:event` / `scont:flow` / `scont:state_machine` / `scont:axioms` each require, accept as optional, and forbid. Documented in `core.yaml` as prose descriptions on the meta-classes; enforced by the exploder's shape validator.
3. **FSM representation — confirm shape.** Proposed: `StateMachine` meta-class with annotation body `{states: [...], transitions: [{from, to, trigger, guard}], initial, terminal}`. Declared as a class with `instantiates: [scont:StateMachine]`, referenced from flows by `lifecycle_ref`.
4. **Axiom unification.** Confirm a single axiom body shape with a `scope: class | flow` field on each entry, rather than separate `ClassInvariant` / `FlowInvariant` constructs. Tier-1 simple invariants stay in native `rules:`; Tier-2 complex invariants use the annotation form.
5. **File layout.**
   - `core.yaml` — lightweight meta-class documentation shells (Role / Event / Flow + 3 subtypes / StateMachine). Importable.
   - `supply_chain_demo.yaml` — imports `core.yaml`, declares concrete entities, roles, events, flows, FSMs, and axioms for the two slices.
   - `exploder.py` — Python module that parses, validates, and structures the ontology (§6.5).

---

## 10. Next step — focused spike + exploder

The `pcg.yaml` evidence shrinks the spike significantly. Remaining questions are specific to our abstract-orchestration use case (pcg models SQL-table content; we model process and handoffs).

**Spike scope (~2 hours):**

1. **Write a minimal supply-chain ontology fragment** in the pcg style: one flow (`submit_procurement_request`), its quantum (`ProcurementRequest`), one role pair (`demand_planning` / `procurement`), one FSM (`RequestLifecycle`), one event (`demand_anomaly_detected`), and one blocking axiom (`respect_lead_time`). ~60 lines of YAML.
2. **Start writing the exploder.** Even the bare parse-and-produce-Python-objects version is enough for the first pass; shape validation and the resolved JSON view follow.
3. **Feed the fragment whole-cloth into the existing LLM validator / reasoning stack** and test three questions:
   - *"Given a candidate `ProcurementRequest` instance, does the axiom `respect_lead_time` fire?"* — tests Logical-layer reasoning.
   - *"When `submit_procurement_request` is in 'submitted' state, what role should the orchestrator route to next?"* — tests Kinetic-layer traversal.
   - *"If the axiom fires, what flow should fire instead?"* — tests that the unhappy-path routing is legible from the ontology alone.

**Decision gates:**

- **LLM reasoning succeeds on all three** → proceed to full `core.yaml` + `supply_chain_demo.yaml` with confidence. The exploder grows into a development aid, validator, and orchestrator-side interface.
- **Kinetic-layer traversal is shaky** → use the exploder's resolved JSON view as the primary LLM context format. Cheap adjustment, no design change.
- **Logical-layer axiom firing is shaky** → strengthen the `nl:` prose, add `llm_prompt_hint` on axiom entries themselves, retry.
- **Something unexpected breaks** → revisit §6.4 fallback.

Once the spike completes and gates clear, the next concrete artifact is the two-file draft (`core.yaml` + `supply_chain_demo.yaml`) plus a working `exploder.py`, realizing the design end-to-end and ready to expose any remaining design gaps before we commit.
