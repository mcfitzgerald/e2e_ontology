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

# Structural diff between two ontology YAMLs (files or git refs)
python exploder.py diff old.yaml new.yaml
python exploder.py diff HEAD~1 HEAD --file supply_chain_demo.yaml  # bare refs
python exploder.py diff HEAD~1:supply_chain_demo.yaml HEAD:supply_chain_demo.yaml  # ref:path
python exploder.py diff HEAD~1 supply_chain_demo.yaml              # mixed — infers file
python exploder.py diff old.yaml new.yaml --only roles,flows       # filter kinds
python exploder.py diff old.yaml new.yaml --json                   # machine-readable

# Scaffold a YAML fragment for a new element (stdout only; paste into the demo)
python exploder.py new role --name supply_planning --domain supply_netops \
    --description "Plans supply" --llm-prompt-hint "..."
python exploder.py new flow --name request_production --domain supply_netops \
    --source-role supply_planning --target-role production_planning \
    --quantum ProductionRequest --trigger-event production_assigned \
    --llm-prompt-hint "..."
python exploder.py new role --name supply_planning --interactive  # prompt for required fields

# Regenerate scont_bodies.py after scont_meta.yaml changes
python exploder.py regen-bodies
```

## Reviewing changes with `exploder diff`

Raw-YAML diffs hide structural intent — a resequenced flow, a renamed slot on a body, and a whitespace tweak all look similar in `git diff`. Use `exploder diff` for a typed delta that groups by element kind and reports field-level changes on bodies, axioms, and the flow's `llm_prompt_hint`.

Args can be disk paths, git refs, or `<ref>:<path>`:

```bash
# Most common: diff your working tree against HEAD
python exploder.py diff HEAD supply_chain_demo.yaml

# Review a range of commits
python exploder.py diff HEAD~3 HEAD --file supply_chain_demo.yaml

# Explicit form when the file name differs between refs
python exploder.py diff HEAD~1:old_name.yaml HEAD:supply_chain_demo.yaml

# Compare two branches
python exploder.py diff main feature-branch --file supply_chain_demo.yaml
```

Git refs are materialized via `git archive` into a tempdir so that LinkML imports (e.g. `core.yaml`) resolve correctly. When one arg is a disk path and the other is a bare ref, the ref borrows the disk arg's basename; when both args are bare refs, pass `--file <path>` or use the `<ref>:<path>` form.

Valid `--only` kinds: `entities`, `roles`, `events`, `state_machines`, `flows`, `enums`, `warnings`. The `warnings` kind surfaces gained/lost warnings across the two ontologies — reviewer-relevant since strict-mode regressions often show up there first.

## Scaffolding new elements with `exploder new`

`exploder new <kind> --name <name> [--domain ...] [--<field> <value>]...` prints a ready-to-paste YAML fragment to stdout. The command never edits `supply_chain_demo.yaml` — the file has opinionated section comments and ordering; authors paste into the right section.

Valid kinds: `role`, `event`, `flow`, `query-flow`, `state-machine`, `axiom`, `entity`. `query-flow` is `flow` with a required `returns:` field. `axiom` emits a list entry meant to be inserted into a flow's `scont:axioms` annotation, not a standalone class. `entity` is plain LinkML (no `instantiates:`).

Body fields are passed as `--kebab-case-field VALUE`: e.g. `--source-role supply_planning`, `--trigger-event production_assigned`, `--llm-prompt-hint "..."`. Any missing required field renders as a `<UPPERCASE_PLACEHOLDER>` string — search-and-replace before pasting, or re-run with `--interactive` to get a prompt loop for the required set.

The fragment also carries a YAML comment block listing the available optional body fields (with types or enum values), so authors can add them into the JSON as needed without a round trip to `scont_meta.yaml`.

Scaffolding output is structural, not cross-ref validated. After pasting, run `exploder validate --strict`.

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
