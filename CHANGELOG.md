# Changelog

All notable changes to the supply chain ontology POC are documented in this file.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). There are no tagged releases yet; everything lives under [Unreleased] until we cut a first version.

## [Unreleased]

### 2026-04-11 — Spike outcome memorialized, ontology expanded (session 2)

- **Added.** Design draft §11 — spike results and learnings. All three LLM-reasoning test questions passed cleanly on first run. Q2 in particular demonstrated four-hop cross-reference traversal (FSM transition guard → axiom name → axiom body → target role ownership), showing the LLM is genuinely understanding structure rather than pattern-matching on field names. Added a note on the FSM-guard-to-axiom resolution convention (currently unenforced; decision is to leave as convention for POC).
- **Added.** Design draft §12 — context management as the ontology scales. Spectrum of five approaches from whole-schema stuffing (current) through modular loading, exploder-as-tool, staged retrieval, to dedicated explorer agents. Tradeoff table, POC decisions, and triggers to re-evaluate. Decision: stay on whole-schema stuffing for now, but add `scont:domain` annotations and keep the exploder's API query-shaped so the eventual shift to tool-based access is a thin shim rather than a rewrite.
- **Added.** Design draft §13 — forward-looking work. Captures directions 2–5 from the post-spike planning: expand the demo ontology, harden the exploder, design the orchestrator-side read API, script the full demo narrative, plus a forward-pointer to the proposal protocol for self-healing.
- **Changed.** Design draft status line updated from "refined and load-bearing concerns resolved" to "POC foundation in place and validated." §9 open points all marked as closed by POC. §10 marked as historical record of the completed spike with decision gates annotated as tripped or not-triggered.
- **Added.** `supply_chain_demo.yaml` — expanded from minimal slice to narrative-capable ontology:
  - New plain entities: `Supplier` (with `lead_time_days`, now typed-referenced by `ProcurementRequest.supplier` and `PurchaseOrder.supplier`), `SKU`, `PurchaseOrder`.
  - `ProcurementRequest.sku` and `.supplier` changed from `range: string` to typed references (`SKU` and `Supplier`).
  - **Tier-1 native LinkML `rules:` example** on `ProcurementRequest`: critical-urgency requests must include a written justification. Demonstrates the two-tier axiom strategy from design draft §4 in practice, not just in prose.
  - **Metric example** on `Supplier` as a `scont:metrics` annotation: `supplier_lead_time` in MetricFlow-compatible shape (measure / entity / aggregation / time_grain / unit) with `source: local` and `promotion_target: dbt`.
  - New role: `supplier_management` (enterprise-side interface that talks to suppliers; distinct from `Supplier` the entity).
  - New event: `po_drafted`.
  - New state machine: `PurchaseOrderLifecycle` (draft → transmitted → acknowledged → fulfilled, with cancel branches).
  - New flow: `submit_po_to_supplier` (procurement → supplier_management, carrying `PurchaseOrder`, triggered by `po_drafted`). Completes the forward three-step narrative: demand sense → procurement action → supplier transmission.
  - New enum: `POStatus`.
  - `scont:domain` / `scont:subdomain` annotations added across entities, roles, events, state machines, and flows. Forward-compatible with §12.2 modular loading.
- **Changed.** `exploder.py`:
  - `Entity` dataclass now carries `annotations` and `rules` as passthrough fields so Tier-1 native rules and entity-level annotations (metrics, domain tags) are preserved rather than silently dropped.
  - `_build_entity` populates the new fields.
  - CLI summary now includes an Entities block with annotation/rule counts.
- **Added.** `CHANGELOG.md` (this file).
- **Added.** `README.md` — project orientation for fresh sessions.
- **Added.** `.gitignore`.
- **Infrastructure.** Git repository initialized. First commit captured the session-1 baseline; this changelog entry is the session-2 delta.

### 2026-04-11 — Initial design and de-risking spike (session 1)

- **Added.** `initial_design_draft.md` — the authoritative design through the post-spike refinement: layer model (Structural / Logical / Kinetic / Metric + Context / Domain cross-cuts), first-class constructs (Role / Event / Flow / StateMachine / Axiom), LinkML implementation mechanism (`instantiates:` as type discriminator + JSON-in-folded-string annotations + `llm_prompt_hint` convention, all validated against `pcg.yaml`), demo plan (demand→procurement happy path + disruption→replan recovery), de-risking spike plan.
- **Added.** `core.yaml` — lightweight meta-class documentation shells for `Role`, `Event`, `Flow` (abstract), `InformationFlow` / `MaterialFlow` / `CashFlow`, `StateMachine`. Importable; no enforced slots; exists to give humans and LLMs a canonical home for the meta-vocabulary.
- **Added.** `supply_chain_demo.yaml` — minimal ontology slice exercising the full extension pattern end-to-end. 1 entity (`ProcurementRequest`), 2 roles, 2 events, 1 state machine (`RequestLifecycle`), 2 flows (`submit_procurement_request` + `replan_on_infeasible_request`), 1 Tier-2 annotation-carried axiom (`respect_lead_time`) with `on_failure_route_to` for recovery routing, 2 enums.
- **Added.** `exploder.py` (~430 lines) — parser, object model, and cross-reference validator. Dispatches on `instantiates:` tags, parses JSON-in-folded-string annotation bodies, builds typed dataclass instances of `Role` / `Event` / `StateMachine` / `Flow` / `Axiom`, validates cross-references (source/target roles resolve, quanta resolve, trigger events resolve, lifecycle FSMs resolve, axiom recovery routes resolve, state machine internal consistency). Collects all errors in one pass before raising. CLI: `python exploder.py supply_chain_demo.yaml`.
- **Added.** `ontology_primer.md` — LLM context bootstrap. Documents the class-centric structure, the `instantiates:` dispatch table, the JSON-in-folded-string convention, the flow / axiom / state machine body shapes, navigation recipes, and key semantic rules. Intended to be prepended to LLM prompts that consume the ontology.
- **Validated.** De-risking spike passed cleanly. All three test questions answered correctly on first run; Q2 exhibited four-hop traversal (see §11 of the design draft). Decision gate tripped: "LLM reasoning succeeds on all three → proceed to full `core.yaml` + `supply_chain_demo.yaml` with confidence."

### Context / references

- `reference/pcg.yaml` — prior virtual-twin ontology (~3000 lines) that demonstrated the `instantiates:` + JSON-in-folded-string + `llm_prompt_hint` pattern working with the user's existing LLM stack. Not POC content, but load-bearing validation evidence.
