# Contributing to the Supply Chain Ontology

Authoring reference for this POC. Read `ontology_primer.md` first — it explains the constructs; this doc explains the process.

## The authoring loop

Every change flows through the exploder. The metaschema (`scont_meta.yaml`) defines what the annotation bodies must look like; `scont_bodies.py` is auto-generated from it; the exploder parses, validates, and cross-references. If the exploder says OK, the orchestrator team can consume the artifact.

```
edit supply_chain_demo.yaml  →  exploder validate --strict  →  pytest tests/  →  exploder doc
```

Strict is the gate. Warnings count.

## Adding elements

### Plain entity

Plain entities carry no `instantiates:` tag. Structure-only.

```yaml
ProductionRequest:
  description: >-
    ...
  annotations:
    scont:domain: supply_netops
    scont:subdomain: production_request
  attributes:
    sku: { range: SKU, required: true }
    volume: { range: decimal, required: true }
    status: { range: ProductionRequestStatus, required: true }
```

Tier-1 class-level invariants go in `rules:` (native LinkML, validated by LinkML itself). Metrics go in a `scont:metrics` annotation as a folded JSON list.

### Role

Mark boundary roles with `is_boundary: true`. Declare the autonomy envelope with `human_involvement`; the orchestrator owns thresholds.

```yaml
supply_planning:
  instantiates: [scont:Role]
  annotations:
    scont:domain: supply_netops
    scont:role: >-
      {
        "description": "...",
        "llm_prompt_hint": "...",
        "human_involvement": "conditional"
      }
```

### Event

```yaml
capacity_resolved:
  instantiates: [scont:Event]
  annotations:
    scont:domain: supply_netops
    scont:event: >-
      {
        "description": "...",
        "observed_by": "supply_planning",
        "llm_prompt_hint": "..."
      }
```

Every event must have a consumer (a flow that lists it as `trigger_event`) or strict will warn. If a role consumes an event via internal behavior — not a flow — model the ingress with a boundary role + flow (see `demand_sensing` + `raise_demand_anomaly` for the pattern).

### Flow

Handoff:

```yaml
request_production:
  instantiates: [scont:InformationFlow]
  annotations:
    scont:domain: supply_netops
    scont:flow: >-
      {
        "source_role": "supply_planning",
        "target_role": "production_planning",
        "quantum": "ProductionRequest",
        "trigger_event": "production_assigned",
        "lifecycle_ref": "ProductionRequestLifecycle"
      }
    scont:axioms: >-
      [ { "name": "line_capacity_not_exceeded", "scope": "flow",
          "severity": "blocking", "nl": "...",
          "on_failure_route_to": "escalate_capacity_conflict" } ]
    scont:llm_prompt_hint: "..."
```

Query (add `returns:`):

```yaml
check_otif_exposure:
  instantiates: [scont:InformationFlow]
  annotations:
    scont:domain: logistics
    scont:flow: >-
      {
        "source_role": "supply_planning",
        "target_role": "logistics_planning",
        "quantum": "OTIFQuery",
        "returns": "OTIFExposure"
      }
    scont:llm_prompt_hint: "..."
```

Axiom `on_failure_route_to` names a recovery flow. FSM transition `guard` names an axiom on the parent flow (or on any flow sharing the same lifecycle). The exploder enforces these resolutions.

### State machine

```yaml
ProductionRequestLifecycle:
  instantiates: [scont:StateMachine]
  annotations:
    scont:domain: manufacturing
    scont:state_machine: >-
      {
        "states": ["requested", "assigned", ...],
        "transitions": [
          { "from_state": "requested", "to_state": "assigned",
            "trigger": "assign", "guard": "line_capacity_not_exceeded" },
          ...
        ],
        "initial": "requested",
        "terminal": ["completed", "cancelled"]
      }
```

Multiple flows may share one lifecycle (e.g. `request_production` and `re_request_production`). Guards resolve against axioms declared on any participating flow.

## What validates what

| Check | Enforced by |
|---|---|
| Body field shapes (types, required, enums) | Auto-generated Pydantic in `scont_bodies.py` |
| Cross-refs (source/target role, quantum, trigger_event, lifecycle_ref, returns, on_failure_route_to, FSM guards) | `exploder.py` |
| FSM internal consistency (known states, reachable initial/terminal) | `exploder.py` |
| LinkML-level best practices (naming, canonical prefixes) | `linkml-lint` |
| Non-blocking warnings (unused roles/events/FSMs, missing domain tags) | `exploder.py` warnings layer |
| Class-level invariants on entities | Native LinkML `rules:` (Tier-1) |

## Commands

```bash
# Validate — must be strict-clean before commit
uv run --with linkml --with pyyaml --with pydantic python exploder.py validate --strict supply_chain_demo.yaml

# Tests
uv run --with linkml --with pyyaml --with pydantic --with pytest python -m pytest tests/

# Render docs (markdown + Mermaid)
uv run --with linkml --with pyyaml --with pydantic python exploder.py doc supply_chain_demo.yaml --output docs/

# Inspect one element
python exploder.py inspect request_production

# Ad-hoc query
python exploder.py query source_role=supply_planning

# Regenerate scont_bodies.py after scont_meta.yaml changes
python exploder.py regen-bodies
```

## Regenerating `scont_bodies.py`

`scont_meta.yaml` is the source of truth for annotation body shapes. `scont_bodies.py` is auto-generated and committed to the repo for reproducibility. Never hand-edit.

When you change `scont_meta.yaml`:

```bash
python exploder.py regen-bodies
```

Commit both files together.

## Pre-handoff checks (orchestrator team consumption)

Before asking another team to consume the ontology, verify the LLM reasoning gates pass (see `initial_design_draft.md` §10 and the Phase G regression/new-pattern questions):

1. Concatenate `ontology_primer.md` + `core.yaml` + `supply_chain_demo.yaml`.
2. Exercise an LLM against the regression questions (R1–R3) and the new-pattern questions (N1–N7) from Phase G.
3. Any hedged or incorrect answer is a **precision bug**: fix the YAML or the primer, then re-run. Do not patch it in the orchestrator.
4. Share `scont_meta.yaml` + the generated `docs/` with the consumer team so they have the formal shape spec and browsable reference.

## Writing good `llm_prompt_hint`s

Hints are load-bearing. Agents read them when structure alone is ambiguous. Good hints:

- Name the upstream signal and downstream consumer explicitly.
- State what the agent is responsible for (own vs. delegate).
- Point at related flows/axioms/events by name so an agent can pivot.
- Note the reasoning mode (Mode 1 hard gate vs. Mode 2 context assembly) if non-obvious.
- Flag boundary crossings — "this role is external, treat its outputs as facts-from-outside."

Avoid:

- Restating what the structure already says.
- Generic advice ("handle errors gracefully").
- Implementation specifics (ADK, LangGraph, etc.) — hints should be orchestrator-agnostic.
