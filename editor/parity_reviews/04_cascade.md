# Parity review — Phase 4a · Cascade view (Screen 2)

**Commit under review:** pending Phase 4a commit on `feat/editor-frontend`
**Implementation:**
- Screen routing: `editor/frontend/src/store/screen.ts`, `components/AppHeader.tsx`, `App.tsx`
- Cascade: `editor/frontend/src/screens/Cascade/{index,layout,traversal}.tsx` + `Cascade.css`
**Mockup source:** `editor/design_reference/wireframe.html` lines 1930–2112 (`CascadeScreen`)
**Design brief:** `reference/ontology_editor_design_brief.md` §"Screen 2 — Cascade view"
**Reviewer:** awaiting user sign-off

## What shipped

- **Screen switcher.** Tabs enabled in the header: 01 structure, 02 cascade, 04 fsm. 03 authoring stays disabled per the scope guardrail. A Zustand slice (`store/screen.ts`) holds current screen; breadcrumb/selection persist across switches.
- **`CascadeScreen`.** Left rail + canvas. ContextPanel remains mounted to the right.
- **BFS traversal** in `traversal.ts`. Two edge kinds feed depth d+1:
  - *event-mediated*: events observed_by the parent flow's target_role → flows that trigger_event on those events.
  - *axiom-trip*: blocking axioms on the parent flow with an `on_failure_route_to` → that recovery flow.
  First-touch seen-set suppresses cycles; hardCap=80 bounds runaway chains.
- **Layout** in `layout.ts`. Y-axis = domain swimlanes (same palette / order as Structure view). X-axis = depth column. Nodes land in the *target_role's* domain lane — the cascade is about where the work arrives. Multiple flows in the same (depth, lane) cell stack vertically.
- **Canvas rendering:**
  - Swimlane backgrounds with the same tints, labels, and dashed strokes as Structure view
  - Depth column headers `DEPTH 0 (request)`, `DEPTH 1`, … with faint dashed dividers
  - Flow-occurrence cards: source+target domain tint bands on top/bottom of the card, flow name, `source_role → target_role` route, kind glyph (`INFO`/`MATE`/`CASH`), axiom severity dot
  - Parent arrows: bezier curve from parent's right edge to child's left edge with `via <event>` label; axiom-trip arrows are red + dashed with `⊥ <axiom>` label
- **Left rail controls:**
  - Full-flow picker (select with all flows)
  - Depth slider (1-8)
  - Show-axiom-trips toggle
  - "Common starting points" chip list — heuristic: flows sourced from boundary roles or root flows (their trigger_event has no observer, or observed by a boundary)
  - Explainer block at the bottom of the rail

## Intentional deviations from the mockup

- **Y-axis = domain swimlanes.** Mockup packs all steps at a row-per-step, ignoring domain. The design brief is explicit: Y should be domains in the same order as Screen 1. This lets the user read the cascade against the same spatial mental model as the structure view — a request "crosses" from commercial to demand to supply_netops and so on, which is the story the view exists to tell. Mockup's packed layout looked tidier but flattened the domain semantics the brief says matter most.
- **Target-role's domain determines lane.** The brief doesn't specify; the mockup punts. Choice: lane = where the work *lands*. When flow A's target role is `supply_planning`, the card sits in supply_netops even if the source was in commercial. The domain tint bands on the card surface both source and target domain so the hop is visible.
- **Axiom trips render as first-class branches.** Mockup showed axioms only as a severity dot on the card. Brief says "axiom trips render as a visible branch into the recovery flow" — we honored the brief by adding dashed red arrows labeled `⊥ <axiom>` from parent to recovery flow whenever a blocking axiom with `on_failure_route_to` appears. Toggleable via the show-axioms checkbox.
- **No handwritten fonts.** Mockup sprinkled `font-family: Caveat` on arrow labels, hint blocks, and the cascade-empty placeholder. All replaced with JetBrains Mono with weight/size/color hierarchy. (Third consecutive parity review calling this out — noted.)
- **No ghost structural layer.** Brief mentions a "faint ghost layer behind the cascade" as a secondary control. Deferred — the flow-occurrence cards already surface source/target/kind/axiom and the cascade makes the causal structure primary. If the ghost-overlay turns out to be load-bearing, easy add.
- **Flow kind abbreviation.** Card shows `INFO`/`MATE`/`CASH` in a colored pill on the right side. The mockup did `info.slice(0,4).toUpperCase()` so `CASH` accidentally becomes `CASH` (4 chars) and `MATERIAL` becomes `MATE`. I kept the exact behavior — it's intentional shorthand at canvas distance; full kind name is in the context panel.

## Points to verify during review

### Routing
- [ ] Clicking `02 cascade` in the header switches to Cascade
- [ ] Clicking a flow card in Cascade populates the same ContextPanel as Structure
- [ ] Clicking `01 structure` returns to Structure with selection+breadcrumb preserved
- [ ] `03 authoring` remains disabled with a "deferred" tooltip

### Starting flow
- [ ] Default start flow picks one of the suggested starts (first alphabetically)
- [ ] Picker enumerates all flows and switching updates the canvas
- [ ] Common-starts chips update the picker when clicked
- [ ] Starting from `submit_promo_plan` produces a visible multi-domain cascade (this is the canonical promo-whiplash trace)
- [ ] Starting from `request_production` shows the axiom-trip branch into `escalate_capacity_conflict` when axioms are enabled

### Layout
- [ ] Swimlanes stack in the same vertical order as Structure
- [ ] Flow cards land in the lane matching their target role's domain
- [ ] Two flows at the same (depth, lane) stack vertically without overlap
- [ ] Depth column headers align with their columns

### Visual
- [ ] Source/target domain tint bands on the card are readable (top = src, bottom = dst)
- [ ] Axiom dots use the severity colors from the Structure-view legend
- [ ] Parent-arrow labels don't overrun neighboring cards at tight spacing
- [ ] Axiom-trip arrows are visually distinct from event arrows (dashed red vs solid dark)
- [ ] `show axiom trips` toggle hides/shows the axiom branches

### Edge cases
- [ ] Starting flow with no downstream chain renders the single card alone (not an error)
- [ ] Starting flow with no target-role domain (shouldn't happen in current ontology) doesn't crash
- [ ] Max-depth = 1 only shows the starting flow plus its immediate children

## Manual walkthrough for visual review

1. Switch to `02 cascade`.
2. Pick `submit_promo_plan` from the common-starts chips.
3. Expected: a cascade that enters demand, fans into supply_netops, then forks into manufacturing + logistics + procurement over ~4-5 depth columns.
4. Click any flow card → ContextPanel shows the FlowPanel (same as Structure).
5. Switch to `request_production` and enable axiom trips.
6. Expected: blue-dashed axiom arrow from `request_production` to `escalate_capacity_conflict` labeled `⊥ line_capacity_not_exceeded`.
7. Flip depth slider to 1 and confirm only direct children show; to 8 and confirm the cascade extends.
8. Click `01 structure` tab → you're back on Structure with the same selection intact.

## Open questions for sign-off

- Domain-swimlane Y instead of packed rows: does the cascade read well at conference-room distance? If it feels sparse for short cascades (e.g. 2 steps only), we can dial LANE_HEIGHT down.
- Card-width 200px: tight for the longer flow names (`shift_production_to_coman_and_notify_...` etc). Happy to widen to 240 if names get truncated in practice.
- Axiom-trip branches as dashed red: too loud? Alternative is to keep them subtle and show the ⊥ marker only.
- "Common starting points" heuristic: boundary-sourced OR no-upstream-event. Should match what you'd want to demo.
