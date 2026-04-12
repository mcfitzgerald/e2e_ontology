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

Every meta-typed element may carry an **`llm_prompt_hint`** written specifically to guide your navigation of that element. **Read hints before inferring from structure** — they often resolve ambiguity directly.

## Flow body

A `scont:flow` body contains:

- `source_role`, `target_role` — role class names
- `quantum` — the class of the typed payload that moves through the flow
- `trigger_event` — event class that fires this flow
- `lifecycle_ref` — StateMachine class governing the quantum's state

## Axiom body

A `scont:axioms` body is a list. Each entry contains:

- `name`, `scope` (`class` | `flow`), `severity` (`blocking` | `warning` | `advisory`)
- `nl` — natural-language statement; always present; **use this for reasoning**
- `expr` — optional Python-subset expression with `{slot.path}` references (LinkML `equals_expression` syntax)
- `message` — human-readable failure message
- `references` — metrics, flows, or classes the axiom depends on
- `on_failure_route_to` — optional; names the recovery flow when a blocking axiom fails

## Navigation recipes

- **"What triggers this flow?"** → read `trigger_event` on the flow body.
- **"Who does this flow hand off to?"** → read `target_role`.
- **"What states can this quantum be in?"** → resolve `lifecycle_ref` → read the StateMachine's `states`.
- **"Does this axiom fire for an instance?"** → evaluate `nl` against the instance; check `severity: blocking`.
- **"If a blocking axiom fails, what should happen instead?"** → read the axiom's `on_failure_route_to` — that's the recovery flow the orchestrator should invoke with the same quantum.
- **"Is this a flow or a relation?"** → a flow has `instantiates: [scont:*Flow]` and a quantum. A relation is a slot on an entity class with a `range:` pointing at another class. Flows are *occurrences*; relations are *capabilities*.

## Rules and gotchas

- **Plain entities never carry flow / axiom / state_machine annotations.** Those always attach to meta-typed classes.
- **Absence of `instantiates:` is meaningful** — it marks a plain entity; don't treat such classes as missing metadata.
- **A flow's quantum is always a declared class** — you should be able to resolve it.
- **`nl:` is authoritative for reasoning.** `expr:` is for deterministic evaluators; when in doubt, defer to `nl:`.
- **`llm_prompt_hint` fields are load-bearing**, not decorative — they carry intent that the structure alone does not.

## Worked pattern

When you see a class like this:

```yaml
submit_procurement_request:
  instantiates: [scont:InformationFlow]
  annotations:
    scont:flow: >-
      { "source_role": "demand_planning",
        "target_role": "procurement",
        "quantum": "ProcurementRequest",
        "trigger_event": "demand_anomaly_detected",
        "lifecycle_ref": "RequestLifecycle" }
    scont:axioms: >-
      [ { "name": "respect_lead_time",
          "severity": "blocking",
          "nl": "...",
          "on_failure_route_to": "replan_on_infeasible_request" } ]
    scont:llm_prompt_hint: >-
      Happy-path information flow from demand_planning to procurement...
```

Read it as: *"An information flow from `demand_planning` to `procurement`, carrying a `ProcurementRequest`, triggered by `demand_anomaly_detected`, governed by the `RequestLifecycle` state machine, gated by a blocking axiom that routes to `replan_on_infeasible_request` on failure."*
