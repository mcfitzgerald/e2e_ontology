# Parity review — Phase 4b (Commit B) · Structure view on React Flow

**Commit under review:** pending Phase 4b Commit B on `feat/editor-frontend`
**Implementation:**
- `editor/frontend/src/screens/Structure/index.tsx` (rewritten to use `<ReactFlow>`)
- `editor/frontend/src/screens/Structure/RoleNode.tsx` (new — HTML-based custom node)
- `editor/frontend/src/screens/Structure/FlowEdge.tsx` (new — SVG custom edge via `BaseEdge`)
- `editor/frontend/src/screens/Structure/SwimlaneBackground.tsx` (new — ViewportPortal'd backgrounds)
- `editor/frontend/src/screens/Structure/edgeGeometry.ts` (simplified — returns bundle indices only; path math moved into FlowEdge)
- `editor/frontend/src/screens/Structure/Structure.css` (appended `.rf-*` rules + React Flow overrides)
- `editor/frontend/src/screens/Structure/SwimlaneGraph.tsx` **deleted**
**Reviewer:** approved by user

## What shipped

The Structure view runs entirely on `@xyflow/react@12.10.2`. Visual grammar and interaction semantics preserved from Phase 1 + Phase 3; rendering substrate swapped from raw SVG to React Flow.

- **Nodes** are HTML divs via the `RoleNode` custom component. Domain swimlanes continue to drive Y positions (via `computeLayout`'s dagre + force-Y algorithm, unchanged). Role cards keep the same shape: ink border, cream fill, 170×36 minimum, boundary dash, selected cream fill + bold border, dimmed at 0.28 opacity.
- **HITL badge** (HTML span, top-right corner) and **diff gutter** (HTML tab, left edge) are now sibling elements inside the role card div rather than SVG groups. Same colors, same glyphs (`!`/`?`, `+`/`~`), same behavior.
- **Edges** are SVG via `BaseEdge`. Quadratic bezier with bundle-index perpendicular offset; parallel flows between the same role pair fan out identically to the pre-port render. Kind-specific CSS classes preserved (`.flow-edge.material|information|cash`). Cash double-line retained.
- **Axiom dots** rendered via `EdgeLabelRenderer` as absolutely-positioned HTML spans in the flow's viewport — they pan/zoom with edges. Hover tooltip via `title` attribute.
- **Diff underlay** still a 7px semi-transparent path under the kind-styled edge for added/changed flows.
- **Swimlane backgrounds** via `ViewportPortal` so they pan/zoom with nodes. Lane reorder `↑↓` buttons ride along, hooked to the same `moveLane` store action.
- **Removed-since-HEAD banner** unchanged, positioned inside `.structure-canvas`.
- **Legend** unchanged, still pinned to bottom-left corner.

### New capabilities (brief-mandated, deferred from Phase 1 because of SVG)

- **Pan**: drag empty canvas.
- **Zoom**: scroll wheel. Bounded 30% to 200%. Double-click fit-view.
- **Auto fit-view** on mount with 12% padding.
- **Hover-to-dim**: hovering a role highlights its neighborhood (adjacent flows + their other role); everything else dims to 0.28. Moving off the node restores.
- **Controls panel** (bottom-right): zoom in/out, fit view.

## Intentional deviations from the mockup and from the pre-port SVG

- **HTML role card instead of SVG group.** The mockup used SVG; pre-port code used SVG. React Flow idiom is HTML custom nodes. Visual output is the same; behavior (hit-target, selection, hover) is cleaner because DOM events route through React Flow's own layer. The only loss: can't apply the `#roughen` SVG filter to HTML; that filter was never load-bearing.
- **React Flow attribution.** Bottom-right "React Flow" attribution stays visible per the library's free-tier terms. Their Pro license ($ one-time) removes it; out of scope for the POC.
- **Controls panel style.** Uses React Flow's default `<Controls>` component with minor palette overrides (paper bg, ink border). Matches the editor's warm-ink treatment without rebuilding the icons.
- **ViewportPortal z-index override.** `.react-flow__viewport-portal` renders after nodes/edges in DOM order → on top by default. Forced below via `z-index: -1` in CSS. Safe because we only use ViewportPortal for the swimlane background; would need refactor if we added on-top overlays via ViewportPortal later.
- **Bundle path math moved into `FlowEdge`.** Pre-port computed the bezier in `edgeGeometry.ts` as a pre-pass. Now `edgeGeometry.ts` only emits `{flow, bundleIndex, bundleTotal}`, and the custom edge builds the path from `sourceX/Y`/`targetX/Y` it receives each render. Keeps edges consistent under pan/zoom and future node position changes. Same output.

## Carried-forward items from earlier parity memos

Not addressed in this commit; still on the list for later passes:

- Edge underlay opacity (0.45) — defer to Commit E or a perception pass
- Axiom-trip branch weight (only visible on Cascade) — defer to Commit C
- Card width / swimlane density — does React Flow's pan/zoom make this moot? Likely yes; re-assess at the end of the port
- Breadcrumb kind glyphs — unchanged
- `BranchBadge` clickability — unchanged

## Points to verify (signed off by user)

### Core parity
- [x] Roles render in their domain swimlanes with the same X ordering
- [x] Flow edges render with kind-specific styling
- [x] Axiom dots at edge midpoints with severity color
- [x] Boundary roles render with dashed borders
- [x] HITL badge on applicable roles
- [x] Diff gutter on changed/added roles; diff underlay on changed/added edges
- [x] Removed-since-HEAD banner when applicable
- [x] Legend pinned to bottom-left

### New capabilities
- [x] Pan + zoom work
- [x] Fit-view on mount
- [x] Hover-to-dim highlights neighborhood
- [x] Lane reorder still works
- [x] Click role/edge → ContextPanel populates
- [x] Empty pane click → deselect

## Known follow-ups

- Same substrate refactor is next for Cascade (Commit C). This solves the Phase 4a "via label overlap" bug via React Flow's built-in edge-label placement.
- Then FSM (Commit D) on the same substrate.
- Keyboard shortcuts (`/`, `esc`, `g`/`c`/`f`) and polished hover-to-dim consistency across screens land in Commit E.
