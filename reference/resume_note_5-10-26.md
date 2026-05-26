# Resume note — 2026-05-10

Read this first if you're a new session picking up the editor workstream.

## State

- **Branch:** `feat/editor-frontend` (not merged to `main`)
- **Last commit:** `b2a2aa1` — Phase 4b Commit D (FSM detail on React Flow)
- **Active plan:** `claude_plans/linear-pondering-platypus.md`
  (React Flow port, 5-commit decomposition A→E. Original was lost;
  reconstructed 2026-05-25 from commit messages + this resume note.)

## Recent commits this session (all on `feat/editor-frontend`)

```
b2a2aa1  Phase 4b (Commit D): FSM detail view on React Flow
8ae54b6  UX polish: "llm prompt hint" → "llm context" + GLOSSARY.md
ea4cee1  Phase 4b (Commit C): Cascade view on React Flow + hover-only via labels
3db55d6  Phase 4b (Commit B): Structure view on React Flow
00ae495  Phase 4b (Commit A): resizable rails + state persistence
46d38d3  Phase 4a:    Cascade view + screen router (pre-RF, hand SVG)
2690124  Phase 3:     ambient diff gutters + branch badge
```

The React Flow port (Commits B/C/D) replaced hand-rolled SVG on Structure,
Cascade, and FSM. Cascade's old "via label overlap" bug is gone (HTML
labels via `EdgeLabelRenderer` + `paper`-background pills). Resizable
panes (`react-resizable-panels@^2`) on every screen, persisted via
`autoSaveId`. FSM was previously a stub — Commit D is its first real
implementation.

## What's next: Commit E (last one in the plan)

Interaction cleanup pass. Roughly an hour of work.

1. **Keyboard shortcuts** — new hook `editor/frontend/src/hooks/useKeyboardShortcuts.ts`:
   - `g` / `c` / `f` → switch between Structure / Cascade / FSM (mutates `useScreen`)
   - `esc` → clear selection (calls `useOntology.navigate(null)`)
   - `/` → focus a search input. No filter rail exists yet, so this is a
     no-op that logs to console.debug for now — adding it forward-keeps
     the binding when the filter rail lands later.
2. **Hover-to-dim consistency** — verify all three RF screens behave the
   same way. Structure and Cascade dim on node hover; FSM dims state
   neighbors. Visually consistent now; just a check pass.
3. **Pan/zoom polish** — `fitView` only on mount, no auto-refit on
   rail-resize. Confirm min/max zoom is consistent across screens
   (currently Structure 0.3-2, Cascade 0.3-2, FSM 0.4-2 — align).
4. **Parity memo** `editor/parity_reviews/08_interactions.md` (see
   "Workflow caveat" below — we may skip the formal memo if user signs
   off verbally, but the file slot is reserved).

## Bookkeeping deficit (not blocking Commit E but worth a batched commit)

These are stale or missing:

- **CHANGELOG.md** is frozen at the Phase 2 entry (`2026-04-18`). Missing
  entries for Phase 3, Phase 4a, and Phase 4b Commits A/B/C/D plus the
  UX polish commit. Seven entries to backfill.
- **`reference/editor_phase_progress.md`** still says "Phase 3 ⏳ next"
  and has a Phase 3 entry-point section that's now historical. Needs a
  full rewrite reflecting where we are.
- **`editor/README.md`** §Status line says "Phase 0 scaffolding. Screen 1
  is the immediate next milestone." Wildly stale. Running-locally section
  is still accurate.
- **`editor/parity_reviews/06_rf_cascade.md` and `07_fsm_detail.md`
  don't exist** — both signed off verbally in this session. Either
  backfill brief memos or formally retire the per-commit memo
  convention. (See workflow caveat.)
- **`docs/` (root, auto-generated)** — last regen was before the
  ontology last changed. Not urgent since nothing this session touched
  the YAML, but worth a regen before the editor merges to main.

Suggested order for next session: **bookkeeping → Commit E → merge**.

## Workflow caveat: verbal sign-off pattern

The plan originally called for a written parity memo before every
commit. In practice this session, sign-off has been verbal in chat
("looks good, commit"). We dropped memos `06_rf_cascade.md` and
`07_fsm_detail.md`. The pattern is faster and the user can review the
diff directly, but the parity-gate convention in `editor/AGENTS.md` is
no longer being honored literally. Worth either updating that doc to
reflect reality or backfilling memos. Don't silently continue the drift
without acknowledging it.

## After Commit E

1. **Merge `feat/editor-frontend` to `main`.** Editor MVP complete.
2. **Decide next direction.** Three live options:
   - **Filter rail** — deferred from the React Flow plan. Domain
     multi-select, kind toggle, HITL filter, changed-since-HEAD toggle,
     search. Right rail wiring + Zustand filter state.
   - **Authoring overlay (Screen 3) + write-through API** — wraps
     `exploder new <kind>` behind `POST /api/elements/<kind>`. Scope
     guardrail in `editor/AGENTS.md` mandates revisit after the editor
     substrate is stable.
   - **Direction 4** (from `initial_design_draft.md` §12) — orchestrator-
     side read API. Standalone work, doesn't block editor merge.
     Strongest forward move per the original design doc.

User has not committed to one yet.

## Critical files / patterns to know

- `editor/GLOSSARY.md` — vocabulary reference written this session
  (flow, depth, swimlane, source, target, kind, quantum, trigger,
  lifecycle, domain, axiom + ~25 more). Read this if any term feels
  unfamiliar.
- `editor/frontend/src/screens/{Structure,Cascade,FSM}/` — three React
  Flow screens, all following the same pattern:
  `index.tsx` (screen + rail) + custom node + custom edge + `layout.ts`
  + `*.css`.
- **Marker reuse:** `editor/frontend/src/tokens/SketchyFilters.tsx` is
  mounted at root and defines SVG markers (`#arrow-ink` etc.) that all
  three React Flow edge components reference via `markerEnd`. Don't
  re-implement.
- **`flowOwningAxiom(data, axiomName)`** in
  `editor/frontend/src/components/panels/helpers.ts` — resolves an
  axiom name to its owning flow regardless of which flow declares it.
  Load-bearing for FSM guard click-through (axioms can live on a
  different flow than the lifecycle owner).
- **Zustand stores:** `ontology`, `diff`, `screen`, `swimlaneOrder`.
  Selection lives in `ontology`. Screen routing in `screen`.

## Conventions (don't re-derive)

- **Two terminals, user runs them.** Never start uvicorn or npm dev
  servers in background. One-shot curls against the user's instance
  are fine.
- **JetBrains Mono only.** No handwritten/scribble fonts.
- **No backwards-compat shims.** Branch is unmerged; user is fine with
  in-place changes.
- **`uv run --with linkml --with pyyaml --with pydantic ...`** for any
  Python invocation that touches the ontology.

## TaskList state at end of session

```
#16-19   completed   Commits A, B, C, D (Phase 4b React Flow port)
#20      pending     Commit E: Interaction cleanup
```
