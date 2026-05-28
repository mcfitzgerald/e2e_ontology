# Supply Chain Ontology POC

A supply chain ontology that sits in an agent orchestration layer, providing the structural and process context agents need to navigate the domain. The ontology describes concepts, roles, events, flows, and invariants; the orchestrator binds them to actual tools and runtimes.

## State of the project

The ontology layer is in place and validated. Strict validation is clean (17 entities, 9 roles, 8 events, 4 state machines, 15 flows, 5 enums); the LLM-reasoning de-risking spike passed cleanly; the editor / visualizer shipped (Phase I.3); the promo whiplash demo narrative is wired into the YAML.

The agent system that will consume this ontology is designed but not yet built. `agent_system_design.md` captures the architectural intent (generic ADK agents instantiated from the ontology, two-layer orchestrator with swappable durability backend, MCP as the front door for analysis agents and knowledge workers). `plan_of_attack.md` is the phased build plan. Phase 0 (foundations: design rule into `CONTRIBUTING.md` + world-state fixture) and Phase 1 (Ontology Service + format-agnostic role-view renderer in `ontology_service/`) are complete. Phase 2 (first transactional agent in a new orchestrator repo) is next; Phase 7 (MCP server over the Ontology Service) can start in parallel.

## Authoritative reading order

Before non-trivial work, read in this order:

1. `initial_design_draft.md` — authoritative design for the ontology layer.
2. `ontology_primer.md` — how to read the ontology (prepended to LLM prompts).
3. `agent_system_design.md` — design of the agent system that consumes the ontology.
4. `plan_of_attack.md` — phased build plan with definitions-of-done.
5. `demo_narrative.md` — the promo whiplash scenario the system executes.
6. `CONTRIBUTING.md` — authoring process and the durable design discipline.
7. `CHANGELOG.md` — session-by-session deltas.

## Files

| File | Purpose |
|---|---|
| `initial_design_draft.md` | Authoritative design for the ontology layer. |
| `agent_system_design.md` | Design of the agent system consuming the ontology. |
| `plan_of_attack.md` | Phased build plan with definitions-of-done. |
| `ontology_primer.md` | LLM context bootstrap — prepend to prompts that consume the ontology. |
| `demo_narrative.md` | Promo whiplash narrative — the demo proof point. |
| `CONTRIBUTING.md` | Authoring guide + the world-model-vs-decision-policy design rule. |
| `CHANGELOG.md` | Session-by-session log of changes. |
| `scont_meta.yaml` | Metaschema. Source of truth for annotation body shapes. |
| `scont_bodies.py` | Auto-generated Pydantic models from `scont_meta.yaml` (commit both together). |
| `core.yaml` | LinkML meta-class documentation shells (Role, Event, Flow, StateMachine). |
| `supply_chain_demo.yaml` | Concrete demo ontology — promo whiplash narrative wired in. |
| `world_state.yaml` | Demo world fixture (SKUs, plants/lines, retailers, commitments, promos, baseline schedule). Validated by `tests/test_world_state.py`. |
| `exploder.py` | Parser, object model, cross-reference validator, query API, CLI. |
| `editor/` | Visual ontology editor / explorer (Phase I.3 MVP). |
| `ontology_service/` | Read-only role-scoped query API + format-agnostic `RoleView` render (`as_agent_prompt` / `as_markdown` / `as_json`). Phase 1 deliverable; substrate for the agent runtime (Phase 2) and the MCP front door (Phase 7). |
| `tests/` | pytest suite (192 tests; adds ontology-service unit tests + role-view snapshots over the original 160). |
| `docs/` | Generated markdown + Mermaid documentation (re-run `exploder doc` after ontology changes). |
| `reference/` | Older session notes and the prior `pcg.yaml` virtual-twin ontology for reference. |

## Quick start

```bash
# Strict validation (must pass clean before commit)
uv run --with linkml --with pyyaml --with pydantic python exploder.py validate --strict supply_chain_demo.yaml

# Full test suite
uv run --with linkml --with pyyaml --with pydantic --with pytest python -m pytest tests/

# Render docs (markdown + Mermaid diagrams)
uv run --with linkml --with pyyaml --with pydantic python exploder.py doc supply_chain_demo.yaml --output docs/

# Inspect one element
python exploder.py inspect request_production

# Ad-hoc query
python exploder.py query source_role=supply_planning
```

See `CONTRIBUTING.md` for the full command reference and authoring workflow.

## Test LLM reasoning over the ontology

Concatenate and feed to your LLM:

1. `ontology_primer.md` — reader's guide, sets up navigation conventions.
2. `core.yaml` — meta-class definitions.
3. `supply_chain_demo.yaml` — the content under test.

Ask questions about handoffs, axioms, and recovery routing. See `initial_design_draft.md` §10 for the three questions used in the de-risking spike and §11 for the results.

## Key design decisions at a glance

- **Ontology models the world and the action vocabulary; never the decision policy.** The durable design discipline (see `CONTRIBUTING.md` and `agent_system_design.md` §2). Without it, the ontology drifts into being a workflow engine in YAML — at which point we have automation, not agentic coordination.
- **LinkML as host format**, extended via `instantiates:` tags as lightweight type discriminators. Not LinkML 1.6's enforced metaclass extension — but `scont_meta.yaml`'s class_uris align so the upgrade path is clean.
- **Class-centric structure.** Everything is a LinkML class. Plain entities have no `instantiates:`; meta-typed constructs (Role / Event / Flow / StateMachine) carry the tag and put structured semantics in `annotations:` as JSON-in-folded-string values.
- **Two reasoning modes.** Mode 1: hard gates (blocking axiom + `on_failure_route_to` → recovery flow). Mode 2: cross-domain context assembly (a role with `human_involvement: conditional` fans out query flows, weighs trade-offs, decides). See `ontology_primer.md`.
- **Agent system: generic agents from ontology + deterministic two-layer orchestrator.** One ADK `LlmAgent` template, parameterized by role; orchestrator is plain Python with application/durability layer split (swappable durability backend: JSONL today, Temporal/Restate later). See `agent_system_design.md` §4-§5.
- **Front door: MCP over the ontology.** Analysis agents and knowledge workers don't need a separate runtime — they ride on an MCP server wrapping the Ontology Service. See `agent_system_design.md` §15.

## Next steps

See `plan_of_attack.md` for the phased plan. In short:

1. **Phase 0** ✅ — design rule into `CONTRIBUTING.md`; world-state fixture.
2. **Phase 1** ✅ — Ontology Service + format-agnostic role-view renderer (`ontology_service/`).
3. **Phase 2** — First transactional agent in a new orchestrator repo.
4. **Phases 3-6** — Multi-role happy path; deterministic backbone; Playbook + Scene 5; full demo.
5. **Phase 7** — MCP front door (can start after Phase 1).
6. **Phase 8** — Demo UI (parallels Phases 5-6).
