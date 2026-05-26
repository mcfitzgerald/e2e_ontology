# Parity review — Screen 01 · Structure (Variant A: role swimlane graph)

**Commit under review:** pending Phase 1 commit on `feat/editor-frontend`
**Implementation:** `editor/frontend/src/screens/Structure/`
**Mockup source:** `editor/design_reference/wireframe.html` (Screen 1, variant A)
**Reviewer:** awaiting user sign-off

## How to render side-by-side

1. Start the backend: `cd editor/backend && uv run --with linkml --with pyyaml --with pydantic --with fastapi --with uvicorn uvicorn main:app --reload --port 8787`
2. Start the frontend: `cd editor/frontend && npm run dev` — open http://localhost:5173
3. Open `editor/design_reference/wireframe.html` in a second browser tab. Click "01 structure" if needed (localStorage may restore prior state).
4. Arrange windows side-by-side at 1440+ width.

## Intentional deviations from the mockup

These are known design decisions, not drift. Each is justified here so future parity reviews can recognize them.

### Tech stack
- **Implementation uses raw SVG, not React Flow**, despite the plan naming React Flow. Rationale: the mockup renders the whole scene as one cohesive SVG with sketchy filter, swimlane backgrounds, nodes, edges, and badges living in the same coordinate space. React Flow splits nodes into HTML divs and edges into SVG, which fragments the sketchy filter application and makes swimlane backgrounds awkward. SVG direct is both simpler and more faithful. React Flow remains installed as a dep for future phases that need node dragging or richer interactions.
- **No pan/zoom in Phase 1.** The mockup uses `preserveAspectRatio="xMidYMid meet"` and lets the SVG fit its container. Real impl matches. Pan/zoom can arrive later if deemed necessary.

### Data source
- **Role/flow/event data is live** from `/api/ontology` (backed by `exploder.load_ontology` on `supply_chain_demo.yaml`), not the mockup's inline `window.ONTOLOGY` snapshot. Counts should match exactly (9 roles, 15 flows, 8 events, 4 FSMs).
- **No `diff` field on records.** The mockup hardcodes `diff: "changed"` on `supply_planning` + `request_production`, and `diff: "added"` on `re_request_production`. These are mockup-only demo flourishes — real diff gutters will land in Phase 3 via `/api/diff`. Screen 1 should render without diff gutters for now.
- **No branch badge.** The mockup's `feat/coman-transfer · +2 ~1` is static flavor; the real version will fetch `git status` in Phase 3.

### Layout
- **Roles are auto-positioned via dagre (rankdir=LR) with Y forced to each role's domain swimlane.** The mockup uses hand-placed coords optimized for minimum crossings. The real layout should look topologically similar (boundary sources on the left, `supply_planning` as a hub near the middle, boundary sinks on the right) but exact X positions will differ.
- **Graph width adapts to dagre's output** rather than the mockup's fixed `W=1100`. On a typical 9-role topology the computed width should be 1200–1400px.
- **Swimlane height is 100px per domain, top-pad 40px.** Mockup lanes vary from 80px (commercial) to 120px (procurement); real impl standardizes. Total height ~680px vs mockup's 640px.

### Header
- Real header shows a truncated screen-tabs row (Structure active, Cascade/Authoring/FSM disabled) instead of the mockup's full context pane controls. This is intentional Phase 1 scope — context panel and filters land in Phase 2.

## Points to verify during review (expected parity)

- [ ] **Palette matches exactly.** Paper `#f7f3ea`, ink `#1a1a1a`, domain tints per `tokens/colors.css`, flow-kind colors (material `#5a3b22`, information `#3b6a96`, cash `#b78d2a`), axiom-blocking `#c04a3a`.
- [ ] **Fonts load correctly.** JetBrains Mono for structure, Caveat for hand annotations (swimlane side-label, HITL badges, "~scribbled live" tag).
- [ ] **Sketchy filter visible on edges.** Edges should have the fractalNoise-displaced stroke, not straight lines.
- [ ] **Paper-grain background.** Body shows the subtle radial gradients + horizontal rule pattern.
- [ ] **Flow kinds visually distinct per mockup rules:** material is earth-tone heavy solid (3.2px), information is blue dashed thin (1.4px, 5/3 dash), cash is gold doubled (two 1.6px parallel lines with 4px separation).
- [ ] **Boundary roles have dashed borders** (customer_development, demand_sensing, co_manufacturing).
- [ ] **HITL badge on `supply_planning`.** Yellow circle, `?` inside, top-right of card. No other roles should show a badge (none of the others have `human_involvement` set to `conditional`/`required` in the YAML).
- [ ] **Axiom dots on 2 edges.** `request_production` and `submit_procurement_request` should each carry a red `!` dot at the edge midpoint (both have `line_capacity_not_exceeded` / `respect_lead_time` blocking axioms).
- [ ] **Bundled parallel edges.** `request_production` and `re_request_production` both go `supply_planning → production_planning`; they should render as two curves with a perpendicular offset, not overlaid.
- [ ] **Swimlane labels.** Left: uppercase `COMMERCIAL`, `DEMAND`, etc. Right: hand-drawn `~retailers & promos`, `~what will sell`, etc.
- [ ] **Legend bottom-left.** Flow kinds + boundary marker + HITL marker + blocking-axiom marker.

## Potential drift to flag

Possible issues to look for when rendering:

- **Dagre layout puts roles where they look weird.** If a role ends up far from its neighbors or crossings are worse than the mockup's hand placement, flag it — may need manual position hints per domain or a 2-pass layout.
- **Edges crossing swimlane dividers at awkward angles.** The mockup's hand-placed nodes minimize this; dagre may not.
- **Font loading flashes FOUT.** JetBrains Mono + Caveat come from Google Fonts — on cold cache first paint may show fallback font. Not a drift per se, but worth noting.
- **Axiom badge position.** Mockup places the badge at the exact midpoint between source and target role centers. Real impl uses the bundled edge's control point (offset perpendicular), which can differ for multi-flow pairs.
- **Text overflow in role cards.** Longer role names (`customer_development`, `logistics_planning`) may crowd the 170px card. Check all 9 fit without clipping.

## Sign-off

- [ ] Reviewer: _______________________
- [ ] Date: _______________________
- [ ] Status: pending / approved / needs-revision
- [ ] Notes:
