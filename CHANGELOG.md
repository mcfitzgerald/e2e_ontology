# Changelog

All notable changes to the supply chain ontology POC are documented in this file.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). There are no tagged releases yet; everything lives under [Unreleased] until we cut a first version.

## [Unreleased]

### 2026-05-27 — Phase 1: Ontology Service + role-view renderer

- **Added.** `ontology_service/` package — read-only role-scoped query layer over the loaded `Ontology`. `OntologyService.load(path)` constructs from a YAML file; `OntologyService(ontology)` wraps an already-loaded object for fixtures. Role-centric methods: `get_role`, `human_involvement`, `incoming_handoffs`, `outgoing_handoffs`, `incoming_queries`, `outgoing_queries`, `events_observed`, `events_emitted`, `fsms_for_role`, `flows_governed_by_fsm`, `axioms_on_flow`, `advisory_axioms_for`. All list-returning methods sort alphabetically by name — the §2 design rule forbids inventing priority the ontology doesn't declare.
- **Added.** `RoleView` typed Pydantic snapshot (`ontology_service/views.py`) — resolved, format-agnostic view of a single role's identity, all four flow categories (incoming/outgoing × handoffs/queries), event surface (events observed vs emitted, with `observed_by` capturing the producer-side declaration), FSMs governing quanta the role touches (with `governs_flows` exposing the multi-flow shared-lifecycle pattern), and Phase 5 stubs for playbooks / tools / advisory criteria so the prompt shape is stable across the upgrade.
- **Added.** Format adapters as `RoleView` methods: `as_json()` (wire form), `as_markdown()` (knowledge-worker onboarding doc), `as_agent_prompt()` (LLM system prompt; same content as markdown with headers demoted to plain labels separated by `---`). Adapters are pure functions over `RoleView` and never re-query the ontology — §15.4 *"one render function, multiple consumers"* discipline is enforced by `TestAdaptersAreFormatOnly`.
- **Added.** `OntologyService.render_role_view(name)` — composes the typed snapshot from the resolved ontology in one pass.
- **Added.** `tests/test_ontology_service.py` (23 cases) — coverage of getters, flow-side splits (handoffs vs queries on both sides), event surface (observed_by-based emission, trigger-based observation), FSM surface (incl. the canonical `ProductionRequestLifecycle` shared by `request_production` / `re_request_production` / `shift_to_coman` on supply_planning), axiom lookup, and the order-discipline invariant.
- **Added.** `tests/test_role_view_render.py` (9 cases) — structural assertions on `demand_planning` (simplest; no queries) and `supply_planning` (most complex; `human_involvement: conditional`, all three Scene 5 query flows, three FSMs); Pydantic round-trip via `as_json()`; section-title parity between markdown and agent-prompt adapters; snapshot tests against `tests/snapshots/{demand_planning,supply_planning}.{agent_prompt.txt,markdown.md}`.
- **Added.** `tests/snapshots/` — committed render snapshots. A drift here means the rendered prompt changed; regenerate intentionally and commit, or treat as a regression.
- **Phase 1 DoD met.** `OntologyService.load('supply_chain_demo.yaml').render_role_view('demand_planning').as_agent_prompt()` produces a deterministic, complete agent system prompt; same call works for `supply_planning`. No agent code; pure rendering. 192 tests pass; strict validation clean (0 warnings, 0 errors). Unblocks Phase 2 (transactional agent in the new orchestrator repo) and Phase 7 (MCP server over the Service).

### 2026-05-25 — Phase I.3 Editor, Phase 4b (Commit E): interaction polish + AGENTS.md retirement

- **Added.** `editor/frontend/src/hooks/useKeyboardShortcuts.ts` wired from `App.tsx`. `g` / `c` / `f` switch Structure / Cascade / FSM (mutates `useScreen`); `esc` clears selection (`useOntology.navigate(null)`); `/` is a no-op + `console.debug` that forward-keeps the binding for the eventual filter rail / search input. Listener skips when focus is inside `<input>` / `<select>` / `<textarea>` / `contentEditable` so the cascade picker, FSM picker, and depth slider still receive their keys.
- **Changed.** FSM `minZoom` 0.4 → 0.3 to align with Structure and Cascade. `fitView`-on-mount-only and hover-to-dim were already consistent across the three screens — verified, no change needed.
- **Removed.** `editor/AGENTS.md`. The file documented a parity-memo-per-screen convention plus stack / scope guardrails, but Claude Code only auto-loads `CLAUDE.md`, not `AGENTS.md` — so the rules sat there unsurfaced. The parity convention had drifted to verbal sign-off in practice (memos 06 / 07 were never written). Substantive content either lives in root `CLAUDE.md` (frontend-design / context7 / JetBrains-Mono-only) or is baked into committed code. Four stale references cleaned in `editor/README.md`, `store/screen.ts`, `components/ContextPanel.css`, `components/PanelDiff.tsx`.
- **Tracked.** `reference/resume_note_5-10-26.md` now in git, with the "Active plan" pointer repaired to `claude_plans/linear-pondering-platypus.md` (original plan file was lost; reconstructed earlier today from commit messages + this resume note).

### 2026-05-10 — Phase I.3 Editor, Phase 4b (Commit D): FSM detail view on React Flow

- **Added.** Real implementation of Screen 4 (FSM detail), replacing the Phase 4a stub. Horizontal lifecycle diagram via dagre LR layout with HTML custom state nodes and smoothstep transition edges.
- **Added.** `screens/FSM/StateNode.tsx` — HTML custom node. Initial states wear a small ▸ entry-arrow glyph hanging off the left edge; terminal states get a concentric outer ring (the automata accept-state double-rule). Tag chips (INITIAL / TERMINAL) inside the box for screen-readability.
- **Added.** `screens/FSM/TransitionEdge.tsx` — smoothstep paths (read better than bezier on strict-LR layout). HTML labels via `EdgeLabelRenderer` carry both `on <trigger>` and `⊢ <guard>` chips. Both interactive: trigger opens EventPanel, guard opens AxiomPanel. Unresolved guards render greyed + strikethrough. Labels at z-index 12 (above nodes); hover bumps to 50 with a soft drop-shadow.
- **Added.** `flowOwningAxiom(data, axiomName)` in `components/panels/helpers.ts`. Resolves an axiom name to its owning flow regardless of which flow declares it. Load-bearing for the canonical case: `request_production` and `re_request_production` both govern `ProductionRequestLifecycle`; the guard `line_capacity_not_exceeded` lives on one but is referenced by the other's FSM. Without this, guard click-through breaks on shared lifecycles.
- **Added.** FSM screen left rail (resizable, persisted via `autoSaveId="editor.layout.fsm"`): FSM picker, summary block, full transitions list with clickable triggers and guard buttons, "Flows sharing this lifecycle (N)" chip list, why-this-view note explaining the multi-flow guard pattern.
- **Deferred.** Per-commit parity memo `editor/parity_reviews/07_fsm_detail.md` not written — verbal sign-off only. The drift is later acknowledged and the convention retired at Commit E.

### 2026-05-09 — Phase I.3 Editor: UX polish — "llm prompt hint" → "llm context" + GLOSSARY

- **Changed.** ContextPanel UI label "llm prompt hint" renamed to "llm context" in FlowPanel, RolePanel, EventPanel. The underlying data field stays `llm_prompt_hint` (ontology truth in `scont_meta.yaml`); only the display label changes. All three constructs carry a single string used as agent context, so one general label suffices — no sub-typing in the data warrants disambiguation in the UI.
- **Added.** `editor/GLOSSARY.md` — vocabulary reference covering core constructs (role / flow / event / axiom / FSM / entity), flow vocabulary (source / target / kind / quantum / trigger / lifecycle / returns / axiom-trip / on_failure_route_to), visual + editor terms (domain / swimlane / boundary role / depth / focus neighborhood / diff gutter / branch badge / HITL), card chrome (INFO / axiom dot / kind pill / tint bands), diff vocabulary, reasoning patterns (Mode 1 hard gate / Mode 2 context assembly), and a "where things live" file map.

### 2026-05-09 — Phase I.3 Editor, Phase 4b (Commit C): Cascade view on React Flow

- **Changed.** Cascade screen ported from hand-rolled SVG to `@xyflow/react`. Trigger was the "via label" overlap on canonical cascades like `submit_promo_plan` — labels rendered on top of cards and each other at depth. React Flow's `EdgeLabelRenderer` places labels at true edge midpoints; HTML pills with a paper background replace the hand-measured bib rects.
- **Added.** `screens/Cascade/FlowOccurrenceNode.tsx` — HTML custom node with source / target tint bands, kind pill, axiom dot, dim / selected states. `screens/Cascade/CascadeEdges.tsx` — `EventEdge` + `AxiomTripEdge` using `getBezierPath` + `EdgeLabelRenderer`. `screens/Cascade/CascadeBackground.tsx` — `ViewportPortal`'d swimlanes + depth column headers / dividers; pans and zooms with content.
- **Changed.** Via labels are hover / focus-only — hidden by default, surfaced when the edge is hovered directly (24px hit zone) or sits in the focus neighborhood (an endpoint is hovered or selected). Closes the original clutter problem.
- **Carried forward.** `traversal.ts` unchanged (pure BFS preserved). `layout.ts` exposes `COL_WIDTH`; depth × domain bucket otherwise unchanged.
- **Deferred.** Per-commit parity memo `editor/parity_reviews/06_rf_cascade.md` not written — verbal sign-off only.

### 2026-04-19 — Phase I.3 Editor, Phase 4b (Commit B): Structure view on React Flow

- **Changed.** Structure screen ported from hand-rolled SVG to `@xyflow/react@12`. Visual grammar and interaction semantics preserved from Phase 1 + Phase 3; rendering substrate swap unlocks pan / zoom and hover-to-dim that had been deferred from Phase 1.
- **Added.** `screens/Structure/RoleNode.tsx` — HTML custom node. Role card chrome (ink border, cream fill, 170×36 min, boundary dash, selected fill + bold, dim at 0.28). Hidden source / target Handles for edge attachment points. HITL badge and diff gutter as sibling DOM elements inside the role card.
- **Added.** `screens/Structure/FlowEdge.tsx` — SVG custom edge via `BaseEdge`. Quadratic bezier with perpendicular bundle-index offset so parallel flows between the same role pair fan out. Kind-specific stroke classes preserved (`material` / `information` / `cash` with cash double-line). Diff underlay 7px. Axiom dot via `EdgeLabelRenderer`.
- **Added.** `screens/Structure/SwimlaneBackground.tsx` — domain tint bands + lane reorder ↑↓ buttons rendered inside `ViewportPortal` so they pan / zoom with nodes. Forces `.react-flow__viewport-portal { z-index: -1 }` so the portal sits below edges / nodes (default DOM order puts it on top).
- **Changed.** `screens/Structure/index.tsx` rewritten as `ReactFlowProvider + StructureInner`. Layout still computes via dagre + forced-Y swimlane algorithm; positions shifted to top-left corners (React Flow's coord convention) before emitting Node records. `edgeGeometry.ts` simplified to return `{flow, bundleIndex, bundleTotal}` only; path math moves into `FlowEdge`.
- **Removed.** `screens/Structure/SwimlaneGraph.tsx` (superseded by React Flow assembly).
- **Unlocked.** Pan on empty-canvas drag; scroll-zoom bounded 0.3–2; auto `fitView` on mount with 12% padding; hover-to-dim (focus neighborhood at 0.28 opacity for non-neighbors); `<Controls>` panel bottom-right.
- **Added.** `editor/parity_reviews/05_rf_structure.md` — Phase 4b Commit B parity memo (the last memo before the convention drifted to verbal sign-off).

### 2026-04-19 — Phase I.3 Editor, Phase 4b (Commit A): resizable rails + state persistence

- **Added.** `react-resizable-panels@^2` pinned (not v4 — v4 introduced a breaking API rename `Group` / `Separator` instead of `PanelGroup` / `PanelResizeHandle` and moved persistence to a `useDefaultLayout` hook; v2 is the widely-documented API and fits the codebase shape).
- **Added.** Outer `PanelGroup` in `App.tsx` between `ScreenRouter` and `ContextPanel`. Canvas Panel `defaultSize 72, minSize 40`; Rail Panel `defaultSize 28, minSize 18, maxSize 50, collapsible`. Widths persist via `autoSaveId="editor.layout.outer"`. Rail collapse state controlled from `App` via `useLocalToggle` and synced to the imperative panel handle; the existing `›` / `‹` affordance in `ContextPanel` now drives controlled props instead of owning state. Ink vertical splitter (6px, 2px grip, darkens on hover / active drag).
- **Added.** Cascade nested `PanelGroup` — 22 / 78 rail / canvas split, `autoSaveId="editor.layout.cascade"`. Independently resizable from the outer layout.
- **Added.** `useScreen` reads initial screen from `localStorage["editor.screen"]` and writes on `setScreen`. Reload lands the user back on the tab they were using rather than always snapping to Structure.
- **Fixed.** Cascade SVG sizing regression — dropped hardcoded `width` / `height` attrs that were overriding CSS and preventing the canvas from resizing when the outer rail moved. `preserveAspectRatio` switched to `xMidYMid` so narrow cascades center.
- **Architectural note.** Foundation commit for the React Flow port that follows (Commits B / C / D / E). Gives immediate ergonomic win without touching any canvas rendering.

### 2026-04-19 — Phase I.3 Editor, Phase 4a: Cascade view (hand SVG) + screen router

- **Added.** Screen 2 (Cascade) — traces a starting flow downstream through the causal chain. Events observed by a flow's target role trigger children at depth+1, and blocking axioms with `on_failure_route_to` contribute recovery branches.
- **Added.** Screen routing harness — `store/screen.ts` Zustand slice for current screen, kept off `store/ontology.ts` so screen switching doesn't disturb selection or breadcrumb stack. `AppHeader` tabs enable structure / cascade / fsm; authoring stays disabled with a "deferred — mockup only" tooltip per the scope guardrail.
- **Added.** Cascade traversal — BFS over flow-level edges with a first-touch seen-set + `hardCap=80`. Two edge kinds: event-mediated (`observed_by → trigger_event`) and axiom-trip (blocking + `on_failure_route_to`). Axiom-trip is enqueued first so the axiom edge wins the seen-set race when both paths reach the same target — that's the edge the view exists to surface.
- **Added.** Cascade layout (hand SVG, pre-React-Flow): Y = domain swimlane matching Structure's order; X = depth column. Multi-flow cells stack vertically. Flow-occurrence cards carry source + target domain tint bands, flow name, route, kind glyph, axiom severity dot. Parent arrows: bezier from right-edge to left-edge; event edges ink-soft solid, axiom-trip edges axiom-blocking dashed with a `⊥ <axiom>` label.
- **Added.** `screens/FSM/` stub so the router type-checks — real FSM implementation follows in Phase 4b Commit D.
- **Added.** `editor/parity_reviews/04_cascade.md` — parity memo.
- **Known issue at sign-off.** When multiple parent arrows converge on similar midpoints, the via-labels overlap even with bibs — the trigger for the Phase 4b Commit C port to React Flow.

### 2026-04-18 — Phase I.3 Editor, Phase 3: ambient diff gutters + branch badge

- **Added.** Backend `GET /api/diff?base=<ref>` wrapping `exploder._resolve_diff_inputs` + `compute_delta`; returns a per-kind `{added, removed, changed}` payload with field-level dotted paths. Chdirs to repo root for the call so `git archive` ships the full tree. `GET /api/git-status` returns branch, head sha, ahead / behind, dirty; each field degrades independently for detached HEAD / no upstream / non-git checkouts.
- **Added.** Zustand `diff` slice with O(1) per-kind status + change indices, loaded on mount and refreshed on window focus (no polling).
- **Added.** `BranchBadge` in app header — branch · @sha · `+N ~M -K`, color-coded.
- **Added.** Diff flag on role nodes — bright red tab with white `~` glyph for changed, green `+` for added, pulled outside the box so it can't be mistaken for box styling. Diff underlay on flow edges — 7px semi-transparent stroke under the kind-styled edge for added / changed flows.
- **Added.** `RemovedSinceHead` banner above the canvas listing elements that exist in base ref but not working copy (no layout coords for them).
- **Added.** `PanelDiff` banner above context-panel body — `+ added` / `~ N fields modified` / `− removed` since base, with inline ins / del field rows.
- **Polish during review.** Legend pill + expanded panel anchored flush to bottom-left corner so both states read as canvas-frame tabs, not floating widgets. Axiom badges on edges shrunk to plain colored dots (per brief: "small dot at edge midpoint"), dropping the mockup's `!` glyph flourish.
- **Added.** `editor/parity_reviews/03_diff_gutters.md` — Phase 3 parity memo.

### 2026-04-18 — Phase I.3 Editor, Phase 2: context panel + relational navigation

- **Added.** Right-rail **ContextPanel** (360px, always mounted, collapsible to a 26px vertical strip) backed by a **Selection history stack** in the Zustand store. `navigate()` pushes, `back()` pops, `jumpTo(depth)` truncates. Clicking any chip pushes the breadcrumb.
- **Added.** Six kind-specific panels: `RolePanel` (domain, boundary, HITL, description, outgoing/incoming flows, observed events, llm_prompt_hint), `FlowPanel` (source/target/kind/quantum/trigger/lifecycle/returns + axiom list with severity dots + route-on-fail), `EventPanel` (observed_by, description, triggered flows), `FSMPanel` (initial, terminal, states, full transitions table, flows sharing), `AxiomPanel` (nl as hint block, scope/severity, owning flow, route-on-fail, expr, violation message), `EntityPanel` (slots, carried-by flows, returned-by flows).
- **Added.** Shared `Chip` component with kind-tinted backgrounds, dashed border for boundary role chips, keyboard-accessible (Enter/Space). Relational helpers (`outgoingFlows`, `flowsTriggeredBy`, `flowOwningAxiom`, …) in one file so every panel queries the payload uniformly.
- **Added.** `Breadcrumb` — home button + kind-glyph + name chain; intermediate entries are jump-to-depth buttons.
- **Added.** `useLocalToggle` hook — boolean state persisted to localStorage, cross-tab synced via `storage` event. Powers both collapsibles.
- **Added.** Legend collapse to a small `ⓘ legend` pill.
- **Added.** `editor/parity_reviews/02_context_panel.md` — Phase 2 parity memo.
- **Deferred.** Diff gutters / ambient change indicators (Phase 3). Filter controls + search (Phase 2.5-ish, still TBD). Slot navigation from EntityPanel. Screens 2/3/4.

### 2026-04-18 — Phase I.3 Editor, Phase 1: swimlane graph (Screen 1 variant A)

- **Added.** `editor/backend/` — FastAPI service wrapping `exploder.load_ontology()`. `GET /api/ontology` returns a lean flat JSON (roles / events / flows / state_machines / entities / axioms / warnings / summary counts) suitable for the frontend; `GET /api/health` reports the configured YAML path + existence. Mtime-keyed cache (`cache.py`) so repeated hits don't re-parse.
- **Added.** `editor/frontend/src/screens/Structure/` — role swimlane graph rendered as a single SVG. `layout.ts` runs dagre (`rankdir=LR`) for X ordering, then forces each role's Y to its domain swimlane and redistributes X within each lane to guarantee minimum spacing (fixes the overlap where two same-domain roles would stack after the Y-snap). `edgeGeometry.ts` bundles parallel flows between the same role pair with a perpendicular offset so they don't overlay.
- **Added.** Custom SVG `RoleNode`s (170×36 cards, dashed for `is_boundary`, HITL badge for `human_involvement`, diff gutter left-edge placeholder for Phase 3). Custom edges with kind-specific strokes (material earth thick, information blue dashed, cash gold doubled). Axiom `!` dots at edge midpoints colored by severity (blocking / warning / advisory).
- **Added.** Reorderable swimlanes — `↑`/`↓` buttons at each lane's left edge; order persisted to localStorage (`editor.swimlaneOrder`).
- **Added.** `Legend` overlay bottom-left with flow-kind + boundary + HITL + axiom glyphs. API client (`api/client.ts`) and Zustand store (`store/ontology.ts`) + `OntologyPayload` TypeScript types mirroring `serialize.py`.
- **Added.** `editor/parity_reviews/01_structure_variant_a.md` — Phase 1 parity memo.
- **Changed.** Dropped the mockup's handwritten font accents (Caveat, Shadows Into Light). User feedback: "that was just for mockup, we need professional looking font". Imports stripped from `typography.css`; JetBrains Mono everywhere. `editor/AGENTS.md` records the rule for future agents.
- **Architectural note.** Phase 1 renders as raw SVG rather than wrapping React Flow (which the plan named) — the mockup's cohesive swimlane + sketchy filter + inline badges fragment awkwardly across React Flow's HTML-node + SVG-edge split. `@xyflow/react` stays installed for later phases that need dragging or richer interactivity.

### 2026-04-18 — Phase I.3 Editor, Phase 0: scaffolding

- **Added.** `editor/` tree under the repo root — `design_reference/` (Claude Design mockup verbatim + chat transcript + banner README marking it reference-only), `parity_reviews/` (per-screen sign-off memos), `frontend/` (Vite + React 18 + TypeScript strict with `@xyflow/react`, `@dagrejs/dagre`, `zustand` installed), `backend/` (FastAPI stub serving `/api/health`).
- **Added.** `editor/AGENTS.md` — editor-local directives for coding agents (the mockup is the spec, parity gate is mandatory per screen, stack conventions, scope guardrails). Scopes the rules to this subtree without bloating root `CLAUDE.md`.
- **Added.** Design tokens extracted verbatim from the mockup into `editor/frontend/src/tokens/` — `colors.css` (paper/ink + domain tints + flow-kind + axiom severity + diff states), `typography.css` (JetBrains Mono import + variables), `reset.css` (paper-grain background), `SketchyFilters.tsx` (SVG `feTurbulence` + `feDisplacementMap` roughen filters + kind-colored arrow markers), `flowStyles.ts` (stroke spec per flow kind).
- **Added.** `editor/README.md` — local-run instructions for the two-terminal workflow.

### 2026-04-18 — CLAUDE.md: tooling conventions

- **Added.** `## Tooling conventions` section in root `CLAUDE.md`. Codifies two rules: (1) frontend work invokes the `frontend-design` skill rather than writing UI code from scratch; (2) library / API / CLI docs go through `context7` rather than web search or model memory. Prevents the recurring failure mode where frontend tasks produce generic AI-styled UI or use stale API assumptions.

### 2026-04-17 — Phase I.3 Editor prototype (rolled back)

- **Added.** Streamlit-based editor (`editor.py` + `tests/test_editor.py`) produced in an Antigravity session — a three-tab UI (Viewer / Diff / WritableEditor) with `st.json` panels, broken inline Mermaid, and form-based authoring.
- **Rejected + removed** (commit `8276f96`). The design failed the task: three separate tabs forced context-switching, `st.json` isn't authoring-grade, Mermaid didn't render via `st.markdown`, form-first authoring fought the graph-first intent of the brief. User: "clunky af and not what i had in mind". Kept `reference/ontology_editor_design_brief.md` (untracked) so the next pass would start from intent, not the Streamlit dead-end.
- **Lesson encoded forward.** The replacement (Phase 0+1+2 above) is graph-first, single-surface, and validated against a visual-parity gate per screen.

### 2026-04-17 — Phase I.1 follow-up: git-ref inputs for diff

- **Added.** `exploder diff` now accepts git refs — `HEAD~1`, `main`, SHAs, and `<ref>:<path>` — as either or both arguments. Replaces the old `/tmp`-copy-and-stash recipe for diffing the working tree against an earlier commit. Refs are materialized via `git archive | tar -x` into a tempdir so LinkML imports (e.g. `core.yaml`) resolve relative to the materialized file.
- **Added.** `--file <path>` flag — names the file within a bare ref when neither arg is a disk path. When exactly one arg is a disk path, the other (ref) borrows its basename automatically, so `exploder diff HEAD supply_chain_demo.yaml` works without `--file`.
- **Added.** `tests/test_diff_gitref.py` — 10 tests covering bare-ref + `--file`, `<ref>:<path>` form, mixed ref/path (both orderings), bad-ref error path, resolver idempotence on identical refs, and a regression test that plain two-disk-path mode still works.
- **Updated.** `CONTRIBUTING.md` — replaced the `/tmp scd_before.yaml` recipe with the direct ref-based workflow.
- **Deferred.** `exploder install-diff-driver` (wires the structural diff into `git diff` via `.gitattributes` + `.gitconfig`) — still queued as explicit follow-up scope.

### 2026-04-17 — Phase I.2: scaffolding subcommand

- **Added.** `exploder new <kind> --name <name>` — print a ready-to-paste YAML fragment for a new ontology element to stdout. Kinds: `role`, `event`, `flow`, `query-flow`, `state-machine`, `axiom`, `entity`. Removes the lookup friction of consulting `scont_meta.yaml` for required field shapes and hand-rolling the folded-JSON annotation.
- **Added.** CLI-args-first input — `--source-role X --target-role Y --quantum Z --trigger-event E ...`. Unknown `--kebab-field VALUE` flags are routed to body fields via argparse `parse_known_args`. Missing required fields render as `<UPPERCASE_PLACEHOLDER>` strings. Optional fields surface as a YAML comment block (with types or enum values) above the body annotation so authors know what's available without a trip to the metaschema.
- **Added.** `--interactive` flag — prompt stdin for each required body field not supplied via flags. Produces output equivalent to the CLI-args form.
- **Added.** Stdout-only contract — never auto-edits `supply_chain_demo.yaml`. The demo has opinionated section comments and ordering; authors paste into the right section.
- **Added.** `tests/test_scaffolding.py` — 39 tests covering: per-kind rendering (`role`/`event`/`flow`/`query-flow`/`state-machine`/`axiom`/`entity`), required-field placeholders, optional-field commentary (including suppression when the caller has supplied the field), CLI entry-point routing via `main()`, `--interactive` parity with CLI flags, and round-trip parsing of every generated fragment through `load_ontology` (axiom fragment tested by pasting into a synthetic flow's `scont:axioms` list).
- **Updated.** `CONTRIBUTING.md` — `exploder new` usage and semantics section.
- **Deferred.** Streamlit editor (Phase I.3) — now has the authoring primitives it needs to shell out to.

### 2026-04-13 — Phase I.1: structural diff subcommand

- **Added.** `exploder diff <path1> <path2>` — typed delta between two ontology YAML files. Groups changes by element kind (`entities` / `roles` / `events` / `state_machines` / `flows` / `enums` / `warnings`) and reports field-level diffs on bodies, axioms, and flow `llm_prompt_hint`. Raw-YAML diffs don't distinguish a structural change from a resequence or a whitespace tweak; this does.
- **Added.** `compute_delta(old, new, kinds=None)` module-level function and `TypedDelta` / `ElementChange` dataclasses as the diff API. Body comparisons use Pydantic `model_dump(mode="json")` — no per-class comparators. Field paths are dotted (`body.source_role`, `axioms.line_capacity_not_exceeded.severity`).
- **Added.** Human rendering with ANSI color (auto-detected via `sys.stdout.isatty()`; `--no-color` to disable) and `--json` flag for machine-readable output. `--only <kinds>` filters by comma-separated element kind.
- **Added.** `tests/test_diff.py` — 16 tests covering additions / removals / changes per element kind, `--only` filter, identical-ontology empty-delta case, and both renderers.
- **Updated.** `CONTRIBUTING.md` — `exploder diff` command reference and a review-workflow recipe.
- **Deferred.** Git-ref inputs (`exploder diff HEAD~1 HEAD`) and `install-diff-driver` — explicit follow-up scope, not this commit.

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
