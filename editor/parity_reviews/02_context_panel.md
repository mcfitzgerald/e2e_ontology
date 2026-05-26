# Parity review — Phase 2 · Context panel + relational navigation

**Commit under review:** pending Phase 2 commit on `feat/editor-frontend`
**Implementation:** `editor/frontend/src/components/{ContextPanel,Breadcrumb,Chip}.tsx` + `components/panels/*`
**Mockup source:** `editor/design_reference/wireframe.html` (context panel on right of Screen 1)
**Reviewer:** awaiting user sign-off

## What shipped

- Right-rail **ContextPanel** (360px wide, bordered left) always mounted
- **Breadcrumb** at top of rail; home button + back-to-depth jumps; dotted-underline links + arrow separators
- **Chip** component with kind-based tints (role, flow, event, state_machine, entity, axiom); dashed border for boundary role chips; click navigates
- Per-kind **panels**:
  - `RolePanel` — domain, boundary flag, HITL, description, outgoing flows, incoming flows, observed events, llm_prompt_hint
  - `FlowPanel` — source/target/kind/quantum/trigger/lifecycle/returns + axiom list with severity dots + nl + on-failure route; llm_prompt_hint
  - `EventPanel` — observed_by, domain, description, triggers flows, llm_prompt_hint
  - `FSMPanel` — initial, terminal, states, transitions list (from→to on trigger [guard]), flows sharing lifecycle
  - `AxiomPanel` — nl (hint block), scope, severity, on flow, route-on-fail, expr if present, violation message if present
  - `EntityPanel` — attribute count, rule count, metrics, slots list, carried by flows, returned by flows
- Navigation history: click anywhere → pushes onto stack; breadcrumb jumps to any depth; `home` clears

## Intentional deviations from the mockup

- **No handwritten fonts.** Mockup used Caveat for axiom NL + hint blocks + HITL badge symbols; per feedback these were stripped. Italic mono + `panel-hint` callout (dark left border, paper-dark background) replaces the handwritten vibe for emphasis.
- **No mockup `diff` badge at panel top.** Mockup showed a yellow `+2 ~1` changes pill when the selected element was in the diff delta. Phase 2 is read-only; ambient diff arrives in Phase 3 via `/api/diff`.
- **Rail width 360px** instead of mockup's 330px. Extra 30px absorbs longer role names + chip wrapping without forcing horizontal overflow.
- **Chip icon column for kind** is color only, not glyph. Mockup didn't show kind glyphs inside chips either — but the breadcrumb does use kind glyphs (`●` role, `→` flow, `◆` event, `○` fsm, `▢` entity, `!` axiom) as a legibility aid. If these read too busy we can strip.

## Points to verify during review

### Navigation
- [ ] Clicking a role card in the graph opens its RolePanel
- [ ] Clicking a flow edge opens its FlowPanel
- [ ] Clicking an axiom `!` dot opens that axiom's AxiomPanel
- [ ] Click empty canvas → selection clears, rail shows empty hint
- [ ] Click through: role → outgoing-flow chip → flow's target-role chip → back via breadcrumb returns each step
- [ ] Breadcrumb `home` clears to empty state
- [ ] Breadcrumb intermediate link jumps back to that depth (truncates forward)
- [ ] Keyboard: Enter / Space on a chip activates it (it has role="button" + tabIndex)

### RolePanel content
- [ ] `supply_planning` shows: domain `supply_netops`, HITL `conditional`, description paragraph, 7 outgoing flows, 2 incoming flows, 2 observed events (`production_assigned`, `capacity_resolved`), llm_prompt_hint block at bottom
- [ ] `customer_development` shows kind label `boundary role`, dashed chip borders where it appears in other panels
- [ ] `production_planning` shows `escalate_capacity_conflict` outgoing, `request_production` + `re_request_production` incoming

### FlowPanel content
- [ ] `request_production` shows: source chip `supply_planning`, target chip `production_planning`, kind `information`, quantum `ProductionRequest` (entity chip), trigger `production_assigned` (event chip), lifecycle `ProductionRequestLifecycle` (fsm chip), **one axiom** `line_capacity_not_exceeded` with red dot + severity `blocking` + nl text + route `escalate_capacity_conflict`
- [ ] `submit_procurement_request` similarly has 1 axiom `respect_lead_time`
- [ ] `check_otif_exposure` shows kind `information · query` + returns chip `OTIFExposure`

### AxiomPanel content
- [ ] `line_capacity_not_exceeded` shows: kind label `axiom · blocking`, big nl hint block at top, scope `flow`, severity `blocking`, on flow chip `request_production`, route chip `escalate_capacity_conflict`
- [ ] Clicking the route chip navigates to `escalate_capacity_conflict` FlowPanel + pushes breadcrumb

### FSMPanel content
- [ ] `ProductionRequestLifecycle` shows: initial `requested`, terminal `completed, cancelled`, 6 states inline, 7 transitions with guard `line_capacity_not_exceeded` on one row (guard in warning color), 2 flows sharing (`request_production`, `re_request_production`)

### EventPanel content
- [ ] `production_assigned` shows: observed_by chip `supply_planning`, domain `supply_netops`, description paragraph, triggers flows `request_production` + `submit_procurement_request`

### EntityPanel content
- [ ] `ProductionRequest` shows: attribute count, slots list, carried by flows `request_production` + `re_request_production` + `shift_to_coman`
- [ ] Clicking on a slot name does nothing (Phase 2 scope — slot navigation deferred)

### Visual
- [ ] Panel kind label is small uppercase with muted border (not a colored pill)
- [ ] Panel name is 15px bold mono, wraps nicely for long ids
- [ ] Key/value rows use 96px label + value grid, dotted bottom separator
- [ ] Chips wrap when several fit on one row; no overflow
- [ ] Axiom NL rendered in italic mono (no handwritten font)
- [ ] Hint block has dark left border + paper-dark background

## Sign-off

- [ ] Reviewer:
- [ ] Date:
- [ ] Status: pending / approved / needs-revision
- [ ] Notes:
