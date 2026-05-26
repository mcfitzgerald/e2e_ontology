# Ontology Editor — Claude Design Brief

Target: Claude Design (anthropic.com). Output: interactive prototype mocks → handoff to Claude Code for implementation.

---

## What we're building

An interactive graph-first editor and demo surface for a supply-chain ontology. The ontology is a typed knowledge graph (roles, events, flows, state machines, axioms, entities) modeling how information / material / cash actually move through a supply chain. The editor treats the ontology *as that graph*, not as the YAML file it happens to be stored in.

## Who it's for

One primary user: a supply-chain technologist doing R&D on the ontology itself.

Secondary use: the same person walking engineering teams and stakeholders through the domain model live, as a teaching tool — instead of slides. Design for clarity at conference-room distance, not density.

## What matters most

- **Physical + process structure is visually primary.** The three flow kinds (material / information / cash) are not interchangeable — they obey different conservation laws and must *look* different at a glance. Boundary roles (external actors: customers, co-manufacturers, market-signal sources) must read as *outside* the enterprise. Domains must read as distinct territory on the canvas.
- **Graph is the starting point**, not a feature tucked inside a tab. The homepage is the whole ontology laid out.
- **Navigation is relational.** Clicking any cross-reference (a role's outgoing flow, a flow's quantum, an axiom's recovery route) moves the camera to that element. No modals, no tab-hopping.
- **Diff-vs-HEAD is ambient.** Changes since last commit are indicated on the affected elements themselves, not in a separate panel.

Deliberately **not** in scope: LLM-assisted authoring (hint drafting, semantic-duplicate detection, etc.). This is a structural tool, not a copilot.

---

## Surface & responsiveness

Desktop-first, single window. Target canvas 1440×900 minimum; 1920×1080 ideal. Not mobile-responsive — this is an R&D tool and a projected-on-a-wall demo surface. Use real estate liberally; no hamburger menus or collapsed side rails.

---

## Data source

The ontology lives in this repo at `supply_chain_demo.yaml` — 17 entities, 9 roles, 8 events, 4 state machines, 15 flows, 5 enums across **commercial / demand / supply_netops / manufacturing / logistics** domains. Read that file directly for all names, relationships, and body content. Also read `ontology_primer.md` (the construct semantics) and `CLAUDE.md` (repo orientation).

**Do not invent supply-chain terminology.** Everything the mock displays should trace to an actual class or annotation in `supply_chain_demo.yaml`.

### Record shapes (for calibration)

- **Flow body carries:** `source_role`, `target_role`, `quantum`, optional `trigger_event`, optional `lifecycle_ref`, optional `returns` (presence = query flow). Flows also carry a sibling `llm_prompt_hint` annotation and a sibling `scont:axioms` list.
- **Role body carries:** `description`, `llm_prompt_hint`, optional `is_boundary`, optional `human_involvement` (`required` / `conditional` / `autonomous`), optional `can_be_played_by`.
- **Event body carries:** `description`, `observed_by` (role name), `llm_prompt_hint`.
- **State machine body carries:** `states`, `transitions` (each: `from_state`, `to_state`, `trigger`, optional `guard` that resolves to an axiom name), `initial`, optional `terminal`.
- **Axiom body carries:** `name`, `scope` (`class` | `flow`), `nl` (natural-language statement — authoritative), optional `expr`, optional `severity` (`blocking` | `warning` | `advisory`), optional `message`, optional `references`, optional `on_failure_route_to` (recovery flow name).

### Canonical flow to calibrate mocks against

`request_production`: `source_role: supply_planning`, `target_role: production_planning`, `quantum: ProductionRequest`, `trigger_event: production_assigned`, `lifecycle_ref: ProductionRequestLifecycle`, carrying a blocking axiom `line_capacity_not_exceeded` that routes to `escalate_capacity_conflict` on failure. This single flow exercises most of the visual grammar the editor needs.

---

## Visual language (non-negotiable)

| Element | Treatment |
|---|---|
| Domain | Named swimlane / region on the canvas. Consistent per-domain tint across all screens. |
| Enterprise role | Solid-bordered node, filled per domain color. |
| Boundary role (`is_boundary: true`) | Dashed-bordered node, positioned at the outer edge of its swimlane. Subtle "external" label. |
| Human-involvement envelope | Corner badge on role node — person icon (`required`), half-person (`conditional`), no badge (`autonomous`). |
| **Material flow** | Thick solid arrow, earth-tone or neutral-dark. Must feel *heavy* — conservation of mass. |
| **Information flow** | Thin arrow, dotted or dashed, cool color (blue / grey). Must feel *light* — copyable, non-conserved. |
| **Cash flow** | Doubled line, distinct color (gold or green). Settlement-final. |
| Query flow (any kind with `returns:`) | Same flow style + a small return-arc glyph at the arrowhead. Distinguishes request-response from fire-and-forget. |
| Axiom on flow | Small badge at edge midpoint — red dot (blocking), amber (warning), grey (advisory). |
| State machine spanning multiple flows | Faint halo / lasso visually grouping the flows that share a `lifecycle_ref`. (Multiple flows sharing one lifecycle is a real and subtle ontology pattern — `request_production` and `re_request_production` both govern `ProductionRequestLifecycle`.) |
| Diff-vs-HEAD indicator | Subtle left-edge color gutter on changed elements — green (added), yellow (changed), red (removed). Field-level change count on hover. |

---

## Screens

Build **Screen 1 (Structure view) first and fully.** Screens 2–4 layer onto the same interaction grammar and can land iteratively. If canvas attention is limited, polish Screen 1 to a demonstrable state before starting Screen 2.

### Screen 1 — Structure view (home)

**Purpose:** one-glance legibility of the whole supply chain. Clicking any element reveals its detail.

```
┌──────────┬───────────────────────────────────────┬────────────┐
│ FILTERS  │                                       │  CONTEXT   │
│          │                                       │   PANEL    │
│ domain ▾ │   [ commercial swimlane            ]  │            │
│ kind   ▾ │   [ demand swimlane                ]  │ (selected  │
│ hitl   ▾ │   [ supply_netops swimlane         ]  │  element)  │
│ changed  │   [ manufacturing swimlane         ]  │            │
│          │   [ logistics swimlane             ]  │            │
│ search   │                                       │            │
│ ______   │   nodes + edges with styling above    │            │
│          │                                       │            │
│ + new ▾  │                                       │            │
└──────────┴───────────────────────────────────────┴────────────┘
```

**Left rail (filters + palette):**
- Domain multi-select
- Flow-kind toggles (material / info / cash)
- Human-involvement filter
- "Show only changed since HEAD" toggle
- Text search (name, description, hint)
- Bottom: `+ new` dropdown (role / flow / query-flow / event / state-machine / axiom / entity)

**Center (canvas):**
- Horizontal swimlanes, one per domain, labeled
- Pan / zoom (drag to pan, scroll-wheel zoom, pinch)
- Node positions stable across reloads (persist layout)

**Right rail (context panel):**
- Populates on selection; empty state when nothing selected
- Name + kind header
- Body fields rendered human-readably (typed rows, not JSON dumps)
- Cross-refs as *clickable chips* — clicking navigates camera to that element
- Axioms as a bullet list, color-coded by severity
- `llm_prompt_hint` in a quieter muted block at the bottom
- Top of panel: diff-vs-HEAD summary if the element is changed ("1 field modified since HEAD" → expandable inline diff)
- Breadcrumb above the panel so the user can retrace navigation: `supply_planning → request_production → ProductionRequest`

**Interactions:**
- Click node or edge → context panel populates
- Click a cross-ref chip → camera pans/zooms to target; panel replaces; breadcrumb extends
- Hover a node → its incoming/outgoing edges highlight; non-adjacent elements dim
- Right-click a role → quick actions: "Add outgoing flow from this role," "Add event observed by this role"

### Screen 2 — Cascade view

**Purpose:** teach the propagation story. Trace a single event through its downstream consequences across domains. This is the killer view for showing *why* an ontology beats scattered process docs.

```
┌──────────────────────────────────────────────────────────────┐
│  ← back to structure       [ event: promo_plan_aligned  ▾ ]  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  commercial      ●──▶                                        │
│                      \                                       │
│  demand               ●──▶──▶                                │
│                              \                               │
│  supply_netops                ●──▶──▶ (axiom trips) ──▶ ●    │
│                                        \                     │
│  manufacturing                          ●──▶                 │
│                                                              │
│  logistics                                     ●──▶          │
│                                                              │
│         T0      T1       T2       T3       T4       T5       │
└──────────────────────────────────────────────────────────────┘
```

- **X-axis:** logical time, derived topologically from the triggering event
- **Y-axis:** domain swimlanes, same vertical order as Screen 1
- **Nodes on the cascade** are flow occurrences. Edges connect each upstream flow's triggering event to the downstream flow it fires
- **Axiom trips** render as a visible branch into the recovery flow (named by `on_failure_route_to`)
- Top control: event picker (any declared event in the ontology)
- Secondary control: toggle showing the underlying structural graph as a faint ghost layer behind the cascade
- Clicking any cascade node opens the same right-rail context panel as Screen 1

**Derivation (how the cascade is computed from the ontology):**
- Start from the selected event
- Find flows whose `trigger_event` matches → these fire at T+1
- For each flow, follow its `axioms` → blocking axioms branch to the flow named by `on_failure_route_to`
- For each flow, follow its `lifecycle_ref` → the state transitions it drives
- For each flow, look for downstream events whose `observed_by` is the flow's `target_role` (or events referenced inside the flow's axioms) → these fire at T+2
- Repeat until no new flows are added

### Screen 3 — Authoring overlay

**Purpose:** add a new element without leaving the graph.

Triggered from left-rail `+ new` or by right-clicking a role. Opens as a **right-rail panel** — not a modal:

- **Kind** — fixed by entry point, or a picker (role / flow / query-flow / event / state-machine / axiom / entity)
- **Name** — text, live-validated against existing ontology names (no duplicates)
- **Domain** — dropdown of existing domains, with "add new…" option
- **Body fields** as typed inputs:
  - `source_role`, `target_role`, `quantum`, `trigger_event`, `lifecycle_ref` → pickers populated from existing ontology elements. Unknown values disallowed.
  - `returns` → entity picker; presence flips a visible "this is a query flow" indicator
  - Enum fields (`human_involvement`, axiom `severity`, `scope`) → segmented buttons
  - Free text (`description`, `llm_prompt_hint`, axiom `nl`) → text areas
- **Ghost preview on the canvas** — as the user fills source/target, a dotted placeholder node or edge appears in real time showing where the new element would land
- **Section anchor picker** — which commented section of `supply_chain_demo.yaml` to insert into; default inferred from `domain`
- **Live strict-validate** runs against a tempfile on every meaningful change. Errors surface as field-level inline markers, not a post-hoc rollback dialog
- **Commit button** disabled until: all required fields filled, no placeholders remaining, strict-validate green

### Screen 4 — State-machine detail

**Purpose:** visualize a quantum's lifecycle as a proper FSM, not a JSON dump.

Triggered by clicking a state machine (either its halo on Screen 1, or via `lifecycle_ref` in a flow's context panel):

- Canvas swaps to FSM view: states as nodes, transitions as directed edges
- Each transition labeled with its `trigger` and `guard`; clicking a guard label navigates to the axiom it resolves to (possibly on a *different* flow — this is important to visualize because the "multiple flows share one lifecycle" convention is one of the subtler ontology patterns)
- Initial state marked with an entry arrow; terminal states marked with a terminator glyph
- Same right-rail context panel grammar as Screen 1
- Back button returns to Screen 1 at the same zoom / pan state

---

## Interaction grammar (shared across all screens)

- **Left rail:** filter / search / create
- **Center:** current view's canvas
- **Right rail:** selection context; always visible; empty state when nothing selected
- **Breadcrumb** above the right rail on every view
- **Keyboard:**
  - `/` focus search
  - `esc` deselect
  - arrow keys pan
  - `+` / `-` zoom
  - `g` structure view, `c` cascade view

---

## Out of scope for this mockup

- Rendering-library choice (React Flow vs. Cytoscape vs. d3) — post-design decision
- Authentication / multi-user / deploy story — single-user local app
- LLM-assisted hint drafting or semantic analysis
- Graph export / screenshot / share links
- Metrics and dbt-delegation views
- Mobile / tablet layouts
