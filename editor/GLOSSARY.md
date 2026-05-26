# Editor & Ontology Glossary

Terms used in the editor UI and the underlying ontology. Source-of-truth for
data shapes is `scont_meta.yaml`; this is the human-readable mapping.

---

## Core ontology constructs

**Role**
A named participant in the supply chain who *does work*. May be internal (a
domain like `supply_planning`, `demand_sensing`) or external — see *boundary
role*. Roles carry a `domain`, an optional `human_involvement` declaration,
and an `llm_context` hint.

**Flow**
A directed connection between two roles that represents a *handoff or
request* of information, material, or cash. Every flow has a
`source_role`, `target_role`, `kind`, `quantum`, an optional
`trigger_event`, optional `returns` (query vs handoff discriminator), and
zero or more **axioms**.

**Event**
A named, observable fact-of-the-world (e.g. `forecast_revised`,
`demand_anomaly_detected`). Events are emitted by *observation* — every
event has an `observed_by` role. Other flows can subscribe to an event via
`trigger_event:` to fire when it occurs.

**Axiom**
A constraint or assertion about the ontology. The authoritative form is
`nl:` (natural language); `expr:` is a semi-symbolic companion. Axioms
have:
- `severity` — `blocking`, `warning`, or `advisory`. Blocking axioms can
  trip a *recovery branch* via `on_failure_route_to:`.
- `scope` — `flow` (attached to one flow) or `class` (entity-level
  invariant).
- Optional `references` to metrics / classes / flows / events used in the
  expression.

**State machine (FSM)**
A typed lifecycle (named e.g. `ProductionRequestLifecycle`). Has `states`,
`initial`, `terminal[]`, and `transitions` between them. Multiple flows
may share a lifecycle via `lifecycle_ref:` — they are different *governance
verbs* over the same underlying state machine.

**Transition**
A move between two FSM states. Carries an optional `trigger` (event name)
and an optional `guard` (axiom name — the gate that must hold for the
transition to fire).

**Entity**
A plain LinkML class — typed data shape with no `instantiates:` tag. The
"things" referenced by flows and events (e.g. `ProcurementRequest`,
`TradePromotion`).

---

## Flow vocabulary

**Source / target**
A flow's source is the role that *emits* the request or handoff; the
target is the role that *receives* it. Cascade depth grows from the
target end (the next layer fires when something the target produces gets
observed).

**Kind**
`material`, `information`, or `cash`. Visually marked with a colored pill
on cards and a colored glyph in chip lists. (Information flows dominate
in the demo; material and cash are rarer but present.)

**Quantum**
The *thing being moved* on a flow — a typed payload class (e.g.
`ProductionRequest`, `PurchaseOrder`). The quantum is the data shape that
travels source → target.

**Trigger**
The event that fires this flow. If a flow has a `trigger_event`, it is
*subscribed* to that event — when the event is observed, the flow fires.
A flow without a trigger is initiated by direct request.

**Lifecycle**
Reference to a state machine (`lifecycle_ref:`) that this flow
participates in governing. Two flows sharing a lifecycle (e.g.
`request_production` and `re_request_production` both pointing at
`ProductionRequestLifecycle`) is a deliberate ontology pattern, not a
bug.

**Returns**
Discriminator between *query* and *handoff*:
- Present (`returns: <quantum>`) → query/request-response. Source keeps
  responsibility for the result.
- Absent → handoff. Responsibility transfers to the target.

**Axiom-trip**
A specific kind of cascade edge: when a *blocking* axiom on a flow fails
and that axiom carries `on_failure_route_to:`, control routes to the
named recovery flow. Drawn dashed-red on Cascade with a `⊥` glyph.

**`on_failure_route_to`**
The recovery flow named on a blocking axiom. Only blocking axioms can
trip; warnings/advisories surface as context but do not branch.

---

## Visual / editor vocabulary

**Domain**
Top-level grouping of roles by where they sit in the chain
(`commercial`, `demand`, `supply_netops`, `manufacturing`,
`logistics`, `procurement`, etc.). Domains drive *swimlane* placement on
both Structure and Cascade screens. Configured in
`editor/frontend/src/config/domains.ts` (color tint, label, ordering).

**Subdomain**
Optional finer grouping within a domain. Surfaced in panels but not used
for layout.

**Swimlane**
A horizontal band representing one domain. Same vertical order across
Structure and Cascade so a role's position is mentally stable as you
switch screens. Lane order is user-reorderable (Structure rail buttons,
persisted in localStorage).

**Boundary role**
A role with `is_boundary: true` — external to the supply chain. The
ontology doesn't model its internals; agents treat its outputs as
facts-from-outside and its inputs as commitments. Marked with a dashed
border on role cards.

**Depth (Cascade only)**
How many causal hops the cascade has taken from the starting flow.
Depth 0 is the request; depth 1 is what fires *because of* depth 0; etc.
The depth slider in the Cascade rail bounds the BFS.

**Cascade step**
One occurrence of a flow inside a cascade traversal. The same flow may
appear multiple times if reached via different parents (the BFS marks
visited per-flow to keep this finite).

**Focus neighborhood**
When a node is hovered or selected, the editor dims everything except
the node itself plus the flows that directly touch it (one hop on
either side of a parent edge). Used to read dense canvases without
losing the global frame.

**Diff gutter**
The bright-red strip on the left edge of a card / chip / panel header
indicating the element has changed vs. `HEAD`. Pairs with the Branch
Badge in the chrome.

**Branch Badge**
Top-bar indicator showing current git branch + ahead/behind counts. Tells
you what "vs. HEAD" means right now.

**HITL / `human_involvement`**
Per-role declaration of human-in-the-loop posture:
- `required` — humans always involved
- `conditional` — humans involved when context warrants
- `autonomous` — no human involvement expected

The ontology declares *that* humans may be needed; the orchestrator
decides *when*. Marked with the `H` badge on role cards.

---

## Flow card / cascade card chrome

**INFO badge**
Indicates the element has an `llm_context` hint worth reading. Click the
card → ContextPanel shows the hint plus references.

**Axiom dot**
Small colored dot on a card indicating it carries axioms:
- Red — blocking axiom present
- Amber — warning axiom
- Grey — advisory only

**Source/target tint bands**
On Cascade flow-occurrence cards, thin colored bars at the top (source
domain) and bottom (target domain) so the *domain hop* is legible
without reading names.

**Kind pill**
Colored block in the top-right of a flow card showing flow kind
(`INFO` / `MAT` / `CASH`).

---

## Diff vocabulary

**HEAD**
Git's pointer to the most recent committed state on the current branch.
"Diff vs HEAD" = what's changed in the working tree since the last
commit. The editor recomputes this on focus.

**Added / changed / removed**
Element-level diff status. Shown in the Diff tab of the ContextPanel and
as gutter strips on cards/chips.

**RemovedSinceHead**
Pseudo-element rendered as a ghost row in panels when an element existed
at HEAD but no longer exists in the working file. Click to read what
was there.

---

## Reasoning patterns (orchestrator-relevant)

**Mode 1 — hard gate**
A blocking axiom enforces a precondition. Failure → trip the recovery
flow named in `on_failure_route_to`. The cascade shows this as a
dashed-red branch.

**Mode 2 — context assembly**
A role with `human_involvement: conditional` fans out *query flows*
(returns-bearing flows) to gather context, then reasons over it and
decides. `supply_planning` is the canonical Mode 2 hub in the demo.

---

## Where things live

| Concept | File |
|---|---|
| Body shapes (RoleBody, FlowBody, AxiomBody, …) | `scont_meta.yaml` |
| Concrete content (the demo) | `supply_chain_demo.yaml` |
| Backend payload shape | `editor/backend/serialize.py` |
| Frontend type mirrors | `editor/frontend/src/api/types.ts` |
| Domain colors / order | `editor/frontend/src/config/domains.ts` |
| Cascade BFS | `editor/frontend/src/screens/Cascade/traversal.ts` |
