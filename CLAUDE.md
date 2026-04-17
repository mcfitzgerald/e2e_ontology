# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A supply chain ontology POC. The deliverable is the **ontology itself** (LinkML YAML) plus a **control plane** (`exploder.py`) that validates, queries, and renders it. Target consumer is a separate agent orchestrator repo that will read the ontology as its source of truth for domain handoffs.

Not a framework, not a library, not a runtime. The ontology is the product.

## Authoritative reading order

Before making non-trivial changes, read in this order:

1. `initial_design_draft.md` — the authoritative design document. §3 (meta-model), §6 (LinkML extension pattern), §11 (spike results), §12 (hot/cold path context management). Long but load-bearing.
2. `ontology_primer.md` — how to read the ontology. Short, prepended to LLM prompts.
3. `CONTRIBUTING.md` — authoring process, templates, command set.
4. `CHANGELOG.md` — session-by-session deltas. The most recent entry always describes current state.

The README is lighter and slightly stale; prefer the four above.

## Architecture: the LinkML extension pattern

Everything in the ontology is a **LinkML class**. Two kinds:

- **Plain entities** (`Supplier`, `ProcurementRequest`, `TradePromotion`, …) — no `instantiates:` tag, just typed LinkML slots. Standard structural types.
- **Meta-typed constructs** — tagged via `instantiates: [scont:Role | scont:Event | scont:InformationFlow | scont:MaterialFlow | scont:CashFlow | scont:StateMachine]`. Semantic content lives in `annotations:` as **JSON strings inside YAML folded scalars** (`>-`). Must parse as JSON.

This is not LinkML 1.6's enforced metaclass extension — LinkML's native annotation validation isn't implemented yet. `instantiates:` is used as a **type discriminator**. The validation spine is:

```
scont_meta.yaml  ──gen-pydantic──▶  scont_bodies.py  ──used by──▶  exploder.py
 (body shape spec)                   (auto-generated,              (parses + cross-refs
                                     committed)                     + dispatches)
```

When LinkML ships native annotation validation, `scont_meta.yaml` slots straight in — `class_uri:` values already align with the `instantiates:` tags.

**Never hand-edit `scont_bodies.py`.** It's regenerated from `scont_meta.yaml`.

## Critical files

| File | Role |
|---|---|
| `scont_meta.yaml` | Metaschema. Source of truth for annotation body shapes (`RoleBody`, `FlowBody`, `AxiomBody`, `StateMachineBody`, `EventBody`, `MetricBody`, `AxiomReferences`, `TransitionBody`) and enums (`Severity`, `Scope`, `HumanInvolvement`, `FlowKind`, `MetricKind`, `MetricSource`). |
| `scont_bodies.py` | Auto-generated Pydantic models from `scont_meta.yaml`. Regenerate via `exploder.py regen-bodies`. |
| `core.yaml` | Meta-class documentation shells — `Role`, `Event`, `Flow` (abstract) + `InformationFlow`/`MaterialFlow`/`CashFlow`, `StateMachine`. No enforced slots; just canonical docs. Imported by content schemas. |
| `supply_chain_demo.yaml` | Current concrete content (~1300 lines). Promo whiplash narrative spanning commercial/demand/supply_netops/manufacturing/logistics. |
| `exploder.py` | Parser + object model + cross-reference validator + query API + CLI. Built on `linkml_runtime.SchemaView`. |
| `tests/` | pytest suite (78 tests). `test_bodies` (Pydantic shape validation), `test_loader` (parsing), `test_query_api`, `test_integration` (end-to-end counts + specific invariants on the live demo YAML). |
| `.linkmllint.yaml` | linkml-lint config. `standard_naming` is disabled because scont-tagged classes use snake_case by convention. |

## Commands

All Python is run under `uv`. The project has no pinned env — `uv run --with ...` installs on the fly.

```bash
# Strict validation (must pass clean before commit — warnings count)
uv run --with linkml --with pyyaml --with pydantic python exploder.py validate --strict supply_chain_demo.yaml

# Full test suite
uv run --with linkml --with pyyaml --with pydantic --with pytest python -m pytest tests/

# Run a single test
uv run --with linkml --with pyyaml --with pydantic --with pytest python -m pytest tests/test_integration.py::TestDemoParity::test_flow_names -v

# Render docs (markdown + Mermaid diagrams — 140+ files under docs/)
uv run --with linkml --with pyyaml --with pydantic python exploder.py doc supply_chain_demo.yaml --output docs/

# Inspect a single element
uv run --with linkml --with pyyaml --with pydantic python exploder.py inspect request_production

# Ad-hoc query
uv run --with linkml --with pyyaml --with pydantic python exploder.py query source_role=supply_planning

# Regenerate scont_bodies.py after editing scont_meta.yaml (commit both together)
uv run --with linkml --with pyyaml --with pydantic python exploder.py regen-bodies
```

The CLI subcommand set: `validate`, `summary`, `inspect`, `query`, `doc`, `regen-bodies`.

## What validates what

| Check | Enforced by |
|---|---|
| Annotation body field shapes (types, required, enum membership) | Auto-generated Pydantic in `scont_bodies.py` |
| Cross-refs (`source_role`, `target_role`, `quantum`, `trigger_event`, `lifecycle_ref`, `returns`, `on_failure_route_to`, FSM guards) | `exploder.py` cross-ref resolver |
| FSM internal consistency | `exploder.py` |
| LinkML-level best practices | `linkml-lint` (invoked by exploder) |
| Non-blocking warnings (unused roles/events/FSMs, missing domain tags, boundary-role misuse) | `exploder.py` warnings layer |
| Tier-1 class-level invariants | Native LinkML `rules:` |

## Key ontology conventions

- **Flow body `returns:` is the query/handoff discriminator.** Present → request-response; source retains responsibility for the result. Absent → handoff; responsibility transfers.
- **`is_boundary: true` on a role** marks it as external to the supply chain. The ontology doesn't model its internals; agents treat its outputs as facts-from-outside and its inputs as commitments.
- **`human_involvement` on a role** (`required`/`conditional`/`autonomous`) declares domain truth only. **The orchestrator owns thresholds and mechanisms.** The ontology never declares "when" — only that a human *may* be needed.
- **Two reasoning modes.** Mode 1: hard gates (blocking axiom + `on_failure_route_to` → recovery flow). Mode 2: context assembly (a role with `human_involvement: conditional` fans out query flows, reasons, decides). `supply_planning` is the canonical Mode 2 hub.
- **`llm_prompt_hint` is load-bearing.** Every meta-typed element carries one. They resolve ambiguity that structure alone can't. Never treat as decoration.
- **Multiple flows can share a `lifecycle_ref`.** FSM guards resolve against axioms declared on any participating flow. Example: `request_production` and `re_request_production` both govern `ProductionRequestLifecycle`.
- **`nl:` is authoritative for axiom reasoning.** `expr:` is semi-symbolic (e.g. `respect_lead_time.expr` mixes integer day-of-year with `today()` — `nl:` is what actually captures intent).

## Working with user feedback

The user is a supply chain technologist. Expects honest pushback and debate, not deference. Saved feedback from the memory layer worth surfacing here:

- **Keep ontology language generic.** No ADK, LangGraph, or any orchestration-framework-specific references in the ontology content or primer.
- **HITL belongs in the orchestrator, not the ontology.** Ontology declares what *may* need humans + context to surface the need; orchestrator owns thresholds and mechanisms. Don't let ontology fields specify runtime policy.
- **`llm_prompt_hint` governance is a future concern.** Watch for it becoming a generic catch-all bucket; don't try to formalize it during the POC.

## Gotchas

- **Warnings count in `--strict` mode.** "Only a warning" is not a get-out — if your change adds an orphan event or unused role, strict will fail and the consumer handoff is blocked.
- **`uv run` invocations must list every dependency.** `linkml`, `pyyaml`, `pydantic`, and `pytest` (when testing) all need `--with` flags. Missing one fails opaquely.
- **The exploder is built on `SchemaView`, not raw YAML.** When adding validation logic, prefer `SchemaView.all_classes()`, `.get_class()`, `.class_induced_slots()`, etc. over re-parsing the YAML.
- **`docs/` is generated output.** Don't hand-edit; re-run `exploder doc` after ontology changes.
- **Before recommending a file or symbol from memory, verify it exists.** The ontology moves fast between sessions; names change.
