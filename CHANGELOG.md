# Changelog

All notable changes to the supply chain ontology POC are documented in this file.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). There are no tagged releases yet; everything lives under [Unreleased] until we cut a first version.

## [Unreleased]

### 2026-04-13 — Ontology control plane hardened; promo whiplash content built (session 3)

- **Added.** `scont_meta.yaml` — LinkML metaschema that formally specifies every scont annotation body shape (`RoleBody`, `FlowBody`, `AxiomBody`, `StateMachineBody`, `TransitionBody`, `EventBody`, `MetricBody`, `AxiomReferences`) and every controlled vocabulary (`Severity`, `Scope`, `HumanInvolvement`, `FlowKind`, `MetricKind`, `MetricSource`). This is the source of truth for body shapes; prose conventions in `core.yaml` cross-reference it.
- **Added.** `scont_bodies.py` — Pydantic models auto-generated from `scont_meta.yaml` via `gen-pydantic`. Never hand-edited; regenerate via `exploder regen-bodies` when the metaschema changes. Validation of annotation bodies is `FlowBody.model_validate(json.loads(folded_string))` and friends — zero hand-written Pydantic.
- **Changed.** `exploder.py` — deep refactor onto LinkML primitives. `SchemaView` is the base introspection layer. Scont validation dispatches on `instantiates:` tag to the auto-generated Pydantic models. Cross-reference resolver validates every structural pointer (`source_role`, `target_role`, `quantum`, `trigger_event`, `lifecycle_ref`, `returns`, `on_failure_route_to`, FSM guards, axiom references). New non-blocking warnings layer (unused roles / events / FSMs; missing domain tags; boundary roles as handoff targets). New query API (`get_flow`, `list_flows_where`, `get_axioms_for`, `find_flows_triggered_by`, `list_boundary_roles`, `list_query_flows`, `list_handoff_flows`, `traverse_fsm`, etc.). New CLI subcommands: `validate` (with `--strict`), `summary`, `inspect`, `query`, `doc`, `regen-bodies`. `linkml-lint` and `gen-doc` invoked as pipeline steps rather than reimplemented.
- **Added.** `tests/` — pytest suite (78 tests across `test_bodies`, `test_loader`, `test_query_api`, `test_integration`). Covers body-shape validation, cross-ref resolution, FSM internal consistency, query API, and end-to-end integration against `supply_chain_demo.yaml`.
- **Added.** Design draft §3.3 decision: `returns: <ClassName>` on the flow body is the formal discriminator between query (request-response) and handoff (responsibility transfer) flows. Supersedes the earlier non-decision that carried request-response only in prose.
- **Changed.** `core.yaml` — meta-class descriptions updated for the new constructs (boundary role pattern on `Role`, `human_involvement` on `Role`, `returns:` on `Flow`, multiple-flows-per-lifecycle convention on `StateMachine`, the two reasoning modes cross-reference). `core.yaml` now defers to `scont_meta.yaml` as the formal specification of body shapes.
- **Added.** `supply_chain_demo.yaml` — promo whiplash narrative built on the hardened foundation. Content now spans commercial / demand / supply_netops / manufacturing / logistics:
  - **Topology rewire (Phase B):** `submit_procurement_request` re-sourced from `supply_planning` (not `demand_planning`) and re-triggered by `production_assigned`. Procurement now routes through supply/netops. `replan_on_infeasible_request` re-targets `supply_planning`.
  - **Roles (Phase C + F):** `supply_planning` (`human_involvement: conditional`), `production_planning`, `logistics_planning`, `customer_development` (boundary), `co_manufacturing` (boundary), `demand_sensing` (boundary — symmetric ingress for demand anomalies).
  - **Entities (Phase D):** `TradePromotion`, `ProductionLine`, `RetailerCommitment`, `SupplyRequest`, `ProductionRequest`, `CapacityConflict`, `OTIFExposure`, `OTIFQuery`, `PromoFlexibilityQuery`, `PromoFlexibility`, `ComanAvailabilityQuery`, `ComanAvailability`, `DemandAnomaly`. Every entity carries `scont:domain` / `scont:subdomain` tags for future modular loading.
  - **Events (Phase E + F):** `promo_plan_aligned`, `forecast_revised`, `capacity_conflict_detected`, `capacity_resolved` (Mode 2 → Mode 1 pivot event).
  - **State machines (Phase E):** `ProductionRequestLifecycle` (with `line_capacity_not_exceeded` as the `requested → assigned` guard) and `TradePromotionLifecycle`.
  - **Flows (Phase F):** `submit_promo_plan`, `raise_demand_anomaly`, `submit_supply_request`, `request_production` (carrying the blocking `line_capacity_not_exceeded` axiom), `escalate_capacity_conflict`, `shift_to_coman`, `plan_fulfillment`, `request_promo_revision` (skeletal), `re_request_production` (internal-resolution re-entry), and three query flows with `returns:` — `check_otif_exposure`, `check_promo_flexibility`, `check_coman_availability`.
  - **Enums (Phase D):** `CommitmentStatus`, `ProductionRequestStatus`.
- **Fixed (Phase G).** `respect_lead_time.expr` — corrected slot name (`lead_time` → `lead_time_days`) and metric reference name. Surfaced by cold-read LLM validation.
- **Added (Phase G).** `re_request_production` flow — first-class internal-resolution re-entry path. Previously the mechanism was only in prose on `capacity_resolved`'s hint; an agent traversing flows structurally could not discover it. Surfaced by cold-read LLM validation.
- **Validated (Phase G).** `exploder validate --strict` clean. Pytest 78/78. Cold-read LLM validation (regression R1–R3 + new-pattern N1–N7, executed by a fresh agent against primer + core + demo YAML only) passed after the two precision fixes above. Known-and-accepted limitation: `respect_lead_time.expr` mixes integer day-of-year arithmetic with `today()` date arithmetic — `nl` is authoritative, `expr` is semi-symbolic.
- **Added.** `ontology_primer.md` (124 lines) — extended with Role body, Event body, query flow discriminator (`returns:`), the two reasoning modes section, boundary role and human_involvement navigation recipes, and a refreshed worked pattern. Topology in the worked example now matches the current supply/netops routing.
- **Added.** `CONTRIBUTING.md` — authoring process reference: how to add each construct, what validates what, the command set, regen workflow, pre-handoff checks for orchestrator-team consumption, guidance on writing good `llm_prompt_hint`s.
- **Final ontology shape.** 17 entities, 9 roles, 8 events, 4 state machines, 15 flows, 5 enums.

### 2026-04-11 — Spike outcome memorialized, ontology expanded (session 2)

- **Added.** Design draft §11 — spike results and learnings. All three LLM-reasoning test questions passed cleanly on first run. Q2 in particular demonstrated four-hop cross-reference traversal (FSM transition guard → axiom name → axiom body → target role ownership), showing the LLM is genuinely understanding structure rather than pattern-matching on field names. Added a note on the FSM-guard-to-axiom resolution convention (currently unenforced; decision is to leave as convention for POC).
- **Added.** Design draft §12 — context management from POC stuffing to enterprise production. Reframed around two foundational points: (1) context window size is the **least** interesting axis — the real drivers are cost, latency, coherence, and debuggability; (2) **hot path vs cold path are different regimes that coexist** on the same ontology artifact rather than compete — cold path (dev / debug / demo / schema evolution) stays on whole-schema stuffing *indefinitely*, hot path (runtime orchestration) is where targeted access earns its keep. The four production-path options (modular loading, exploder-as-tool, staged retrieval, explorer agents) compose and stack rather than being alternatives. The paradox of pure tool calling (to query well, you must know what's there) is solved by the manifest layer; the primer stays in context regardless of architecture. Opinionated POC track: (1) keep whole-schema stuffing for dev/debug/cold path forever, (2) build the exploder's query API as part of direction 4 — useful immediately as a Python API and forward-compatible with every later hot-path option, (3) do not split the ontology into files, (4) leave staged retrieval and explorer agents documented but unbuilt.
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
