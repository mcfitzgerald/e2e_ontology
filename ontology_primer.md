# Supply Chain Ontology — Reader's Primer

A supply chain ontology in extended LinkML YAML. Declares the concepts, roles, events, flows, and invariants an agent needs to reason about handoffs without a hardcoded capability manifest.

## Class-centric structure

Every construct is a **LinkML class**. Two kinds:

- **Plain entities** (e.g. `ProcurementRequest`, `Supplier`, `SKU`) — no `instantiates:` tag, just typed slots. Things that exist.
- **Meta-typed constructs** — tagged via `instantiates:` so tools dispatch correctly. Semantic content lives in `annotations:` as **JSON strings inside YAML folded scalars** (`>-`). Parse them as JSON when reading.

Tag dispatch:

| Tag | Meaning | Body annotation |
|---|---|---|
| `scont:Role` | Logical actor entities can fulfill | `scont:role` |
| `scont:Event` | Observable happening | `scont:event` |
| `scont:StateMachine` | Finite state machine (`states`, `transitions`, `initial`, `terminal`) | `scont:state_machine` |
| `scont:InformationFlow` | Non-conserved handoff (signals, requests, approvals) | `scont:flow` (+ optional `scont:axioms`) |
| `scont:MaterialFlow` | Mass-conserving physical handoff | `scont:flow` (+ optional `scont:axioms`) |
| `scont:CashFlow` | Value-conserving, settlement-final | `scont:flow` (+ optional `scont:axioms`) |
| `scont:Playbook` | Named multi-flow choreography anchored to a (role, event) pair | `scont:playbook` |
| `scont:Tool` | Declared deterministic service an agent can invoke via `call_tool` | `scont:tool` |

Every meta-typed element may carry an **`llm_prompt_hint`** written specifically to guide your navigation of that element. **Read hints before inferring from structure** — they often resolve ambiguity directly.

## Role body

A `scont:role` body contains:

- `description`, `llm_prompt_hint` — always present
- `is_boundary` — optional boolean. `true` marks the role as **external** to the supply chain (commercial / customer development, co-manufacturer, external sensors). Boundary roles appear as flow endpoints but the ontology does not model their internals. Treat operations at boundary roles as negotiation or observation, **not orchestration**.
- `human_involvement` — optional enum: `required` | `conditional` | `autonomous`. Declares the **domain truth** about whether this role may need a human actor. The ontology declares what *may* need humans; the **orchestrator owns thresholds and mechanisms** for deciding per-case.

## Event body

A `scont:event` body contains:

- `description`, `llm_prompt_hint`
- `observed_by` — the role class that produces or detects the event. Must resolve to a declared Role.

## Flow body

A `scont:flow` body contains:

- `source_role`, `target_role` — role class names
- `quantum` — the class of the typed payload that moves through the flow
- `trigger_event` — optional; event class that fires this flow
- `lifecycle_ref` — optional; StateMachine class governing the quantum's state (a single FSM may be shared across multiple flows)
- `returns` — optional; class name of the response payload. **Presence discriminates flow shape:** absent → handoff (responsibility transfers), present → query flow (request-response; source retains responsibility and consumes the `returns` class as the response)

## Axiom body

A `scont:axioms` body is a list. Each entry contains:

- `name`, `scope` (`class` | `flow`), `severity` (`blocking` | `warning` | `advisory`)
- `nl` — natural-language statement; always present; **use this for reasoning**
- `expr` — optional Python-subset expression with `{slot.path}` references (LinkML `equals_expression` syntax)
- `tool_ref` — optional; names a deterministic compute tool the orchestrator binds to a Python callable for evaluation. Use when the axiom needs world-state access (schedules, lead times, calendars) beyond `equals_expression`. **Precedence:** when both are present, `tool_ref` is the source of truth for evaluation and `expr` stays as documentation; `nl` remains authoritative for human/LLM reading regardless.
- `message` — human-readable failure message
- `references` — metrics, flows, or classes the axiom depends on
- `on_failure_route_to` — optional; names the recovery flow when a blocking axiom fails

## Playbook body

A `scont:playbook` body anchors a multi-flow choreography to a `(role, event)` pair. It scaffolds **how** an agent assembles context and identifies the choice space for a class of situation; it never declares which choice to prefer (that stays agentic — the §2 world-vs-policy rule).

- `role`, `triggered_by`, `input_quantum` — the structural anchor: which role runs this, on which event, carrying which quantum.
- `context_assembly` — the query flows to fan out before deciding. Each step names a flow that has a `returns:` (a query flow). **Order is not priority or sequence** — the orchestrator composes responses per `synchronization`.
- `synchronization` — `wait_all` (default; the decision sees every response) or `wait_any` (rare; only for interchangeable evidence).
- `decision.criteria_refs` — names of **advisory** axioms the agent weighs as viability inputs. The orchestrator evaluates each against the assembled context; the agent reads typed pass/fail-style results, not just the names.
- `decision.selects_one_of` — the resolution flows available. The agent picks exactly **one**. **Order is arbitrary** — the renderer presents the list neutralized (alphabetized) and the listed position carries no preference. A reader who treats the first entry as "the default" has reintroduced policy.
- `always_fires` — events/flows that fire on **every** successful resolution, regardless of which path was chosen (structural post-resolution effects).

The Playbook's `llm_prompt_hint` is a **sibling** `scont:llm_prompt_hint` annotation (same as flows), not a body field.

## Tool body

A `scont:tool` body declares a deterministic service an agent can invoke via `call_tool`. Two categories:

- **reader** — reads world state; no side effects. Safe to call freely. (Prefer reading world state with a reader tool over inventing facts.)
- **compute** — a pure function over typed input; no side effects.

Fields: `description`, `category`, `input_class`, `output_class` (the typed input/output classes, validated by the orchestrator), `implementation` (a **contract name** the orchestrator binds to a Python callable at boot — it does not resolve to anything in the ontology, same shape as an axiom's `tool_ref`), and `available_to` (the role names that may invoke it — the role-view renderer filters tools by membership). `llm_prompt_hint` is a sibling annotation.

The Tool registry is **separate** from the axiom `tool_ref` registry: Tools are agent-callable; axiom evaluators are internal to the deterministic backbone.

## Two reasoning modes

The ontology supports two distinct agent reasoning patterns. Recognize which one the situation calls for:

- **Mode 1 — hard gates.** A blocking axiom fires on a handoff flow; the orchestrator follows its `on_failure_route_to` to a recovery flow. Deterministic; no judgment required. (Example: `respect_lead_time` on `submit_procurement_request` → `replan_on_infeasible_request`.)
- **Mode 2 — cross-domain context assembly.** A conflict needs quantified trade-off reasoning across domains. A role with `human_involvement: conditional` (typically `supply_planning`) fans out **query flows** to gather structured responses, evaluates options, and decides. The orchestrator may surface the decision to a human per its own policy. (Example: `capacity_conflict_detected` lands at supply_planning, which queries OTIF exposure, promo flexibility, and coman availability before choosing a resolution path.)

## Navigation recipes

- **"What triggers this flow?"** → read `trigger_event` on the flow body.
- **"Who does this flow hand off to?"** → read `target_role`.
- **"Is this a handoff or a query?"** → check for `returns:` on the flow body. Present → query (expect a response of that class). Absent → handoff.
- **"What states can this quantum be in?"** → resolve `lifecycle_ref` → read the StateMachine's `states`. Multiple flows may share one FSM (e.g. an initial-assignment flow and a re-entry flow both governing the same lifecycle).
- **"Does this axiom fire for an instance?"** → evaluate `nl` against the instance; check `severity: blocking`.
- **"If a blocking axiom fails, what should happen instead?"** → read the axiom's `on_failure_route_to` — that's the recovery flow the orchestrator should invoke with the same quantum.
- **"Is this role inside the supply chain?"** → read `is_boundary` on the role body. Boundary roles are external; agents treat their outputs as facts-from-outside and their inputs as commitments, not operations.
- **"Does this decision need a human?"** → read `human_involvement` on the role body. `conditional` means the orchestrator decides per-case; the ontology doesn't declare thresholds.
- **"Is this a flow or a relation?"** → a flow has `instantiates: [scont:*Flow]` and a quantum. A relation is a slot on an entity class with a `range:` pointing at another class. Flows are *occurrences*; relations are *capabilities*.
- **"What playbook fires when event X happens at role R?"** → find the `scont:Playbook` whose body has `role == R` and `triggered_by == X`. Single-playbook-per-(role, event) is enforced at validation, so there is at most one.
- **"Which path should the playbook pick?"** → that is **not** in the ontology. `selects_one_of` lists the paths that are *available*; choosing among them is the agent's judgment. List order is arbitrary, never a ranking.
- **"What tools can role R call?"** → filter all `scont:Tool` instances by `R in available_to`. Reader tools let you read world state instead of guessing it.

## Rules and gotchas

- **Plain entities never carry flow / axiom / state_machine annotations.** Those always attach to meta-typed classes.
- **Absence of `instantiates:` is meaningful** — it marks a plain entity; don't treat such classes as missing metadata.
- **A flow's quantum is always a declared class** — you should be able to resolve it.
- **`nl:` is authoritative for reasoning.** `expr:` is for deterministic evaluators; when in doubt, defer to `nl:`.
- **`llm_prompt_hint` fields are load-bearing**, not decorative — they carry intent that the structure alone does not.

## Worked patterns

**Handoff flow with a blocking axiom (Mode 1):**

```yaml
submit_procurement_request:
  instantiates: [scont:InformationFlow]
  annotations:
    scont:flow: >-
      { "source_role": "supply_planning",
        "target_role": "procurement",
        "quantum": "ProcurementRequest",
        "trigger_event": "production_assigned",
        "lifecycle_ref": "RequestLifecycle" }
    scont:axioms: >-
      [ { "name": "respect_lead_time",
          "severity": "blocking",
          "nl": "...",
          "on_failure_route_to": "replan_on_infeasible_request" } ]
```

Read: *"Information handoff from supply_planning to procurement, carrying a ProcurementRequest, triggered by production_assigned, governed by RequestLifecycle. If the blocking axiom fails, route the same quantum to replan_on_infeasible_request."*

**Query flow (Mode 2):**

```yaml
check_otif_exposure:
  instantiates: [scont:InformationFlow]
  annotations:
    scont:flow: >-
      { "source_role": "supply_planning",
        "target_role": "logistics_planning",
        "quantum": "OTIFQuery",
        "returns": "OTIFExposure" }
```

Read: *"Request-response flow. supply_planning asks logistics_planning a question carried as an OTIFQuery; the response arrives as an OTIFExposure. supply_planning retains responsibility and uses the response to reason about trade-offs."* The presence of `returns:` is the only signal distinguishing this from a handoff.
