# Demo narrative — Promo whiplash

**Status:** Draft, aligned through discussion. Not yet reflected in the ontology YAML.

**Executive story:** A retailer promotion commitment enters the supply chain through S&OP alignment, then ripples across demand planning, supply/network operations, manufacturing, procurement, and logistics. The ontology enables agents to autonomously detect cross-domain conflicts, assemble context from every affected function, and surface a decision to a human planner with quantified trade-offs — in minutes instead of the days it normally takes. Where resolution is straightforward, agents act autonomously; where trade-offs span domains, they escalate with full context.

**Industry grounding:** CPG oral/personal/home care (model: P&G, Colgate). 30-40% of CPG volume runs through trade promotions. McKinsey estimates 1-3% of revenue destroyed annually from promotion-supply misalignment. This is recognized as the #1 cross-domain coordination failure in CPG.

---

## Functional model

Six supply chain functions, plus one external boundary function:

| Function | What it owns | Ontology role(s) |
|---|---|---|
| **Demand** | Forecast, demand sensing, demand shaping | `demand_planning` |
| **Supply / NetOps** | Global capacity planning, network optimization — which plants, co-mans, DCs can/should handle volume | `supply_planning` |
| **Manufacturing** | Plant operations, line scheduling, production execution | `production_planning` |
| **Procurement** | Raw material sourcing from suppliers | `procurement`, `supplier_management` |
| **Logistics** | Warehousing, transportation, delivery compliance (OTIF) | `logistics_planning` |
| **Customer service** | Retailer order management, fulfillment interface | `customer_service` (not in POC scope) |

**Boundary role (external to supply chain):**

| Function | What it owns | Ontology role |
|---|---|---|
| **Customer development** (commercial) | Trade promotion commitments, retailer negotiations | `customer_development` |

Customer development is outside the supply chain. The ontology declares it as a boundary role — thin, representing "the external function that sends us signals." The interface is the S&OP alignment process, where commercial and supply chain agree on a promo plan. This boundary role pattern generalizes: customer orders from sales, regulatory signals from legal, cost targets from finance — all enter the supply chain the same way.

---

## The setup

- **Company:** CPG manufacturer of oral care products (toothpaste, mouthwash).
- **Product A:** A flagship toothpaste SKU (think "Colgate Total 6oz").
- **Product B:** A secondary toothpaste SKU on a shared production line.
- **Retailer 1:** Walmart (promo target, tier-1 with OTIF penalties).
- **Retailer 2:** Target (standing replenishment commitment for Product B, OTIF penalties).
- **Time horizon:** ~8 weeks out.

Product A and Product B share a manufacturing line at the same plant. The line runs at a known weekly capacity. Both SKUs have standing replenishment commitments to retailers with OTIF (On-Time In-Full) penalty windows.

---

## Beat-by-beat

### Scene 1 — The promo signal enters (S&OP boundary)

Customer development has committed to a BOGO promotion on Product A at Walmart, starting in 6 weeks. The expected volume lift is 3x baseline for the 2-week promo window. This promo plan has been aligned through S&OP. A `promo_plan_aligned` event fires, carrying a `TradePromotion` quantum into the supply chain.

**What the ontology provides:** The `submit_promo_plan` flow carries the aligned promo commitment from the `customer_development` boundary role to `demand_planning`. The promo is not a vague signal — it's a structured, typed quantum (SKU, retailer, volume uplift, window, commitment status) that the demand planning agent can consume directly. The boundary role pattern declares "this signal comes from outside SC — here's its shape and who receives it."

**Ontology elements:** `customer_development` (boundary role), `demand_planning` (role), `submit_promo_plan` (flow), `TradePromotion` (entity/quantum), `promo_plan_aligned` (event).

### Scene 2 — Demand plan revision (Demand function)

The demand planning agent receives the promo signal. It revises the forecast for Product A: baseline + 3x uplift for weeks 6-7. A `forecast_revised` event fires.

The revised forecast doesn't fan out directly to procurement and manufacturing. Instead, it flows to **supply/netops** — the function with network-level visibility. Supply planning decides *where* and *how* to fulfill, then assigns to the right downstream functions.

**What the ontology provides:** The demand planning agent reads the ontology to discover which flow is triggered by a `forecast_revised` event: `submit_supply_request` targets `supply_planning`. The agent doesn't hardcode downstream routing — the ontology is the routing table.

**Ontology elements:** `forecast_revised` (event), `submit_supply_request` (flow: demand_planning → supply_planning), `SupplyRequest` (entity/quantum — the revised demand signal with volume, timing, SKU).

### Scene 3 — Network evaluation (Supply/NetOps function)

The supply planning agent receives the supply request. This is the network brain — it evaluates *where* to fulfill:

- Which plant(s) can produce Product A?
- Is there enough line capacity at the assigned plant for the promo window?
- Are raw materials available on the required timeline?
- Which DCs need to be staged for Walmart delivery?

Supply planning assigns the production to a specific plant and emits two downstream requests:

1. **Production request** to `production_planning` — "produce X units of Product A in weeks 6-7 on line L at plant P."
2. **Procurement request** to `procurement` — "source incremental raw materials for the promo volume." (This connects to the existing `submit_procurement_request` flow.)

**What the ontology provides:** Supply planning reads the ontology to discover the downstream flows: `request_production` targets `production_planning`, `submit_procurement_request` targets `procurement`. The axioms on these flows tell the supply planning agent what constraints the downstream functions will enforce — it can anticipate conflicts before they fire.

**Ontology elements:** `supply_planning` (role), `request_production` (flow: supply_planning → production_planning), `ProductionRequest` (entity/quantum — SKU, volume, window, assigned plant/line).

### Scene 4 — Capacity conflict (Manufacturing function)

The production planning agent receives the production request. It checks the line schedule for weeks 6-7 and discovers:

- Product A promo volume requires 80% of line capacity for 2 weeks.
- Product B is currently scheduled for 40% of that same line during the same window (standing replenishment for Target).
- **Total demand: 120% of capacity.** Something has to give.

An axiom fires: **`line_capacity_not_exceeded`** (blocking). The total scheduled production on the line exceeds rated capacity. This is a hard gate — you cannot produce 120% on a line.

The axiom's `on_failure_route_to` directs to `escalate_capacity_conflict`, a flow back to `supply_planning`. The manufacturing agent doesn't decide how to resolve the conflict — it signals the conflict with full context (which SKUs, which line, what the shortfall is, what commitments are at risk) and routes back to the function with network visibility.

**What the ontology provides:** The axiom catches a constraint violation that manufacturing can detect but cannot resolve alone (the resolution requires cross-domain visibility). The `on_failure_route_to` tells the agent exactly where to escalate. The axiom body's references tell the receiving agent what entities are involved.

**Ontology elements:** `production_planning` (role), `line_capacity_not_exceeded` (axiom on `request_production`), `escalate_capacity_conflict` (flow: production_planning → supply_planning), `CapacityConflict` (entity/quantum — the structured description of the conflict).

### Scene 5 — Context assembly (Supply/NetOps — the money moment)

Supply planning receives the capacity conflict. This is not a situation with a single declared recovery path — it's a cross-domain trade-off that requires assembling context from multiple functions before a decision can be made.

The `supply_planning` role carries a `human_involvement: conditional` annotation. The ontology declares: "this role handles decisions that may require human input, depending on complexity and financial exposure." The orchestrator applies its threshold policy to decide whether to escalate or let the agent resolve autonomously. Either way, the agent's first job is the same: **assemble the full picture.**

The supply planning agent reads the ontology to discover what context it needs and queries each affected domain:

**1. Query logistics for OTIF exposure.**
Via `check_otif_exposure` flow (supply_planning → logistics_planning): "if Product B ships N days late to Target, what's the financial exposure?" Logistics calculates: Target's MABD is day X, delay pushes shipment to day X+3, OTIF penalty = 3% of COGS on affected shipments = $Y.

**2. Query commercial for promo flexibility.**
Via `check_promo_flexibility` flow (supply_planning → customer_development): "is the Walmart promo timing negotiable?" The `TradePromotion` quantum's `commitment_status` field answers this — if `contractually_locked`, renegotiation is off the table.

**3. Check co-manufacturer availability.**
Via `check_coman_availability` flow (supply_planning → co_manufacturing boundary): "is a qualified co-man available for Product B volume in weeks 6-7?" The co-man entity carries qualification status, capacity, and premium cost.

**4. Check procurement for material availability.**
Via existing ontology flows: can raw materials for the promo volume be sourced on the required timeline?

The agent now has the full cross-domain picture:

| Resolution path | Available? | Cost | Source of info |
|---|---|---|---|
| Renegotiate promo timing | Depends on `commitment_status` | Relationship risk (qualitative) | Commercial |
| Shift Product B to co-man | If co-man qualified + has capacity | Co-man premium: $Z/unit | Co-manufacturing |
| Accept OTIF penalty on Product B | Always available | 3% COGS = $Y | Logistics |
| Partial promo volume (2x not 3x) | Depends on `commitment_status` | Reduced trade spend ROI | Commercial |

**What the ontology provides:** The agent didn't have a hardcoded decision tree. It discovered the affected domains by reading the axiom's references and the flows connected to `supply_planning`. It gathered context from each domain via declared query flows. It assembled a decision surface with quantified trade-offs using declared metrics. The ontology structured the information gathering; the decision itself — whether made by an agent or a human — uses the ontology's information architecture as its input.

**Two kinds of ontology reasoning on display:**
1. **Hard gates** (Scene 4): axiom fires, recovery route is declared, agent follows it. Deterministic.
2. **Context assembly for judgment calls** (Scene 5): the ontology tells the agent what to gather and from whom. The decision is made by whichever actor (agent or human) the orchestrator assigns based on its autonomy policy.

**Ontology elements:** `check_otif_exposure` (query flow: supply_planning → logistics_planning), `check_promo_flexibility` (query flow: supply_planning → customer_development), `check_coman_availability` (query flow: supply_planning → co_manufacturing), `OTIFExposure` (entity), `human_involvement` annotation on `supply_planning` role.

### Scene 6 — Decision and execution

**If autonomous (below orchestrator's escalation threshold):** The supply planning agent evaluates the assembled context and selects the co-man shift — lowest risk, quantifiable cost, preserves all commitments.

**If escalated (above threshold):** The orchestrator surfaces the assembled decision surface to a human supply chain planner: "Here's the conflict. Here's who's affected. Here are the viable resolution paths with costs. What do you want to do?" The human selects the co-man shift. The agent executes.

Either way, the execution path is the same — declared flows in the ontology:

- `shift_to_coman` flow executes: Product B's volume for weeks 6-7 routes to a qualified co-manufacturer.
- Product A promo volume proceeds on the internal line — `request_production` re-evaluated, axiom now passes.
- Product B's OTIF commitments to Target are preserved via the co-man route.
- `procurement` may need to adjust raw material sourcing (co-man may source independently or need materials shipped).
- `logistics_planning` updates the fulfillment plan — Product A ships from internal plant DC, Product B ships from co-man DC.

The downstream flows execute, and the supply chain re-converges on the happy path.

### Executive punchline

> "A promo commitment entered the supply chain and hit a capacity wall. Within minutes, agents across five functions — commercial, demand planning, supply network operations, manufacturing, and logistics — assembled the full cross-domain impact: OTIF exposure at Target, co-manufacturer availability, promo flexibility with Walmart. A human planner saw the complete picture with quantified trade-offs and made the call. No one built a dashboard for this scenario. No one wrote integration code between these systems. The ontology declared the domains, the constraints, and the information the decision-maker needs. The agents navigated it. That's what an autonomous supply chain looks like — not replacing human judgment, but making sure every decision has complete, cross-functional context in minutes instead of days."

---

## Domains and roles summary

```
customer_development ──(boundary)──→ demand_planning ──→ supply_planning ──→ production_planning
                                                      │                         │ (capacity conflict)
                                                      │                         ↓
                                                      │                    ←── escalate back to supply_planning
                                                      │
                                                      ├──→ procurement ──→ supplier_management
                                                      │
                                                      ├──→ logistics_planning (OTIF check)
                                                      │
                                                      └──→ co_manufacturing (boundary, shift volume)
```

| Role | Function | Type | In current ontology? |
|---|---|---|---|
| `customer_development` | Commercial (external) | Boundary | No — new |
| `demand_planning` | Demand | Internal | Yes |
| `supply_planning` | Supply / NetOps | Internal | No — new |
| `production_planning` | Manufacturing | Internal | No — new |
| `procurement` | Procurement | Internal | Yes |
| `supplier_management` | Procurement | Internal | Yes |
| `logistics_planning` | Logistics | Internal | No — new |
| `co_manufacturing` | External co-man | Boundary | No — new |
| `customer_service` | Customer service | Internal | Not in POC scope |

---

## What exists vs. what's needed

### Exists (reusable as-is or with minor adaptation)
- `demand_planning` role
- `procurement` role, `supplier_management` role
- `submit_procurement_request` flow with `respect_lead_time` axiom
- `replan_on_infeasible_request` recovery flow
- `submit_po_to_supplier` downstream flow
- `ProcurementRequest`, `PurchaseOrder`, `Supplier`, `SKU` entities
- `RequestLifecycle`, `PurchaseOrderLifecycle` FSMs
- `UrgencyLevel`, `RequestStatus`, `POStatus` enums

### New entities needed
- `TradePromotion` — the quantum entering from commercial (SKU, retailer, volume uplift, window, commitment status)
- `SupplyRequest` — revised demand signal from demand_planning to supply_planning
- `ProductionRequest` — assigned production (SKU, volume, window, plant, line)
- `CapacityConflict` — structured conflict description (line, competing SKUs, shortfall, at-risk commitments)
- `OTIFExposure` — logistics' calculation of penalty exposure (retailer, SKU, delay, penalty amount)
- `ProductionLine` — the shared resource with rated capacity
- `RetailerCommitment` — standing delivery commitment (retailer, SKU, volume, MABD window)

### New roles needed
- `customer_development` (boundary role)
- `supply_planning`
- `production_planning`
- `logistics_planning`
- `co_manufacturing` (boundary role)

### New flows needed

**Handoff flows** (quantum moves, source role hands off responsibility):
- `submit_promo_plan` (customer_development → demand_planning) — promo signal enters SC
- `submit_supply_request` (demand_planning → supply_planning) — revised forecast
- `request_production` (supply_planning → production_planning) — assigned production
- `escalate_capacity_conflict` (production_planning → supply_planning) — conflict escalation
- `shift_to_coman` (supply_planning → co_manufacturing) — volume shift to external co-man
- `plan_fulfillment` (supply_planning → logistics_planning) — fulfillment assignment
- `request_promo_revision` (supply_planning → customer_development) — negotiate promo change (resolution path)

**Query flows** (request-response, agent gathers context — new pattern):
- `check_otif_exposure` (supply_planning → logistics_planning) — "what's the OTIF penalty if SKU X ships N days late?"
- `check_promo_flexibility` (supply_planning → customer_development) — "is the promo timing negotiable?"
- `check_coman_availability` (supply_planning → co_manufacturing) — "can you handle SKU X volume in weeks Y-Z?"

### New events needed
- `promo_plan_aligned` — S&OP alignment complete, promo signal enters SC
- `forecast_revised` — demand plan updated
- `production_assigned` — supply planning has assigned production to a plant
- `capacity_conflict_detected` — manufacturing cannot fit the volume
- `capacity_resolved` — supply planning has selected a resolution path
- `otif_exposure_assessed` — logistics has calculated the penalty risk

### New axioms needed
- `line_capacity_not_exceeded` — blocking, on `request_production` flow. Hard gate: scheduled production on a line cannot exceed rated capacity.
- (OTIF is modeled as a metric/constraint for soft reasoning, not a blocking axiom.)

### New state machines needed
- `ProductionRequestLifecycle` (requested → assigned → scheduled → in_production → completed | cancelled)
- `TradePromotionLifecycle` (proposed → aligned → committed → executing → completed | revised | cancelled)

---

## Design decisions captured in this narrative

1. **Demand planning does not fan out directly to manufacturing and procurement.** It flows through supply/netops, which has network-level visibility and decides where/how to fulfill. This matches how P&G/Colgate actually operate.

2. **Supply/netops is the natural hub for cross-domain reasoning.** Not the orchestrator — a domain function. When manufacturing escalates a capacity conflict, supply planning evaluates alternatives because it has visibility across the network (other plants, co-mans, DCs).

3. **Commercial/customer development is a boundary role.** It exists in the ontology to declare the interface where promo signals enter the supply chain. The ontology doesn't model commercial's internals. The boundary role pattern generalizes to any external signal source (customer orders from sales, regulatory signals from legal, cost targets from finance).

4. **Two kinds of reasoning:** hard gates (axioms fire, recovery routes are declared) and context assembly for judgment calls (agent gathers cross-domain information, decision is made by agent or human). Scene 4 demonstrates the first; Scene 5 demonstrates the second.

5. **Logistics is a participant, not just a constraint.** The `logistics_planning` role actively calculates OTIF exposure on request and participates in the resolution decision via a query flow.

6. **Co-manufacturing is a boundary role.** Like customer development, the co-manufacturer is external. The ontology declares the interface (what flow, what quantum, what constraints) without modeling the co-man's internals.

7. **Human-in-the-loop is a hybrid of ontology and orchestrator.**
   - **Ontology declares (domain truth):** which roles/situations may require human input (`human_involvement: required | conditional | autonomous` annotation on roles), what context to assemble (query flows to affected domains), what the decision options are (available resolution flows).
   - **Orchestrator owns (execution semantics):** how to reach the human (UI, Slack, etc.), autonomy thresholds (financial exposure > $X → escalate), SLA timers, confidence-based fallbacks.
   - Escalation to a human is structurally identical to any other flow routing — the ontology doesn't care if a role is played by an agent or a human. The orchestrator binds roles to actors. This preserves the ontology's neutrality toward orchestration specifics.

8. **Resolution alternatives are not hardcoded in the ontology.** The ontology declares flows that *could* be used as resolution paths, but the specific options available in a given situation are dynamic — discovered by the agent at runtime by reading the ontology's topology. The agent (or human) evaluates based on context, not a predetermined decision tree. The ontology provides the information architecture for the decision; it doesn't make the decision.

---

## Open questions

1. **POC build scope for resolution paths.** The narrative declares four alternatives in Scene 5. For the minimum interesting working narrative, recommendation: build the co-man shift end-to-end as the primary resolution, declare the promo renegotiation flow with minimal body so the agent can see it exists, leave OTIF-acceptance and partial-volume as described-but-unsculpted. The query flows (`check_otif_exposure`, `check_promo_flexibility`, `check_coman_availability`) should all be built — they're the context assembly mechanism that makes Scene 5 work.

2. **Query flows vs. handoff flows.** Scene 5 introduces query flows (`check_otif_exposure`, `check_promo_flexibility`, `check_coman_availability`) that are request-response: the agent asks a question and gets an answer back. These are structurally different from handoff flows (`submit_procurement_request`) where a quantum moves from one role to another and the source role is done. Does the ontology need to distinguish between these? Options: (a) a `flow_kind: handoff | query` annotation, (b) treat them as information flows with a lightweight quantum and a return flow, (c) something else. This is a design question with implications for how the exploder models them.

3. **Procurement flow source role.** The existing `submit_procurement_request` has `source_role: demand_planning`. In the promo narrative, procurement is triggered by supply planning. Does `submit_procurement_request` need to change its source to `supply_planning`, or can there be multiple flows with the same quantum but different source roles? Or does demand planning still emit procurement requests directly for non-promo scenarios (the promo narrative adds a new flow, and the existing one stays for the baseline replenishment case)?

4. **`human_involvement` annotation shape.** What's the right annotation body for declaring the autonomy envelope on a role? Simple enum (`required | conditional | autonomous`) or richer (includes what context to gather, what the decision surface looks like, what the escalation criteria hint at)? Keeping it simple is probably right for POC — the `llm_prompt_hint` on the role already describes the behavioral pattern.

5. ~~**Demo execution format.**~~ ✅ Resolved: live agent execution (option B). The orchestrator and agents are built in a separate repo/project and will consume this ontology as their source of truth. The ontology must be precise enough that agents reading it cold can make correct routing decisions — no hand-waving. If we build B, scripted walkthroughs (option A) are just recordings of B.
