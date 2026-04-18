# Editor — phase progress

A compact resume card for the ontology editor workstream. Start here if
you're a new session or coming back after a break.

## Where things are

- **Branch:** `feat/editor-frontend` (not yet merged to `main`).
- **Last commit:** `726b85d` — Phase 2 context panel + relational navigation.
- **Directory:** `editor/` in the repo root.
- **Plan of record:** `/Users/michael/.claude/plans/squishy-scribbling-parnas.md`
- **Design intent:** [`reference/ontology_editor_design_brief.md`](ontology_editor_design_brief.md).
- **Visual spec:** [`editor/design_reference/wireframe.html`](../editor/design_reference/wireframe.html) (reference only — NOT the implementation).
- **Directives for agents working in `editor/`:** [`editor/AGENTS.md`](../editor/AGENTS.md). Read before changing anything under that subtree.
- **Parity reviews:** [`editor/parity_reviews/`](../editor/parity_reviews/) — sign-off memos per screen.

## Phases

| Phase | Commit | Status | Scope |
|---|---|---|---|
| 0 — Scaffolding | `b089a7b` | ✅ merged on branch | `editor/` tree, Vite + React + TS frontend, FastAPI `/api/health` backend, design tokens extracted from mockup, AGENTS.md + READMEs |
| 1 — Structure screen (Variant A) | `6c1cdb8` | ✅ merged on branch | `/api/ontology`, SVG swimlane graph with dagre layout + per-lane X redistribution, custom RoleNode + FlowEdge, reorderable lanes, Legend, click-to-dim |
| 2 — Context panel + navigation | `726b85d` | ✅ merged on branch | Right-rail ContextPanel (collapsible), Breadcrumb with history stack, six kind panels (Role, Flow, Event, FSM, Axiom, Entity), Chip cross-links, Legend collapse |
| 3 — Ambient diff indicators | — | ⏳ next | `/api/diff?base=<ref>&head=<ref>` endpoint wrapping `exploder.cmd_diff`, diff gutters on roles/flows (green add, amber change, red remove), branch/changes badge in top bar |
| 4 — Screens 2/3/4 | — | ⏳ later | Cascade view (BFS over flow trigger_event chains), FSM detail screen, Authoring overlay (static demo only) |
| — Authoring write-through | — | ⏳ deferred | Out of scope until Phase 3 lands and patterns prove out. Will wrap `exploder new <kind>` behind `POST /api/elements/<kind>`. |

## Running locally

**Two terminals. You (the human) drive them — do not ask Claude Code to start servers in background.**

Terminal 1 — backend:
```bash
cd editor/backend
uv run --with linkml --with pyyaml --with pydantic --with fastapi --with uvicorn \
  uvicorn main:app --reload --port 8787
```

Terminal 2 — frontend:
```bash
cd editor/frontend
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api/*` to port 8787.

## Entry point for Phase 3

Next phase adds diff gutters. Rough shape:

1. **Backend.** Add `GET /api/diff?base=<ref>&head=<ref>` in `editor/backend/main.py` that calls existing `exploder._resolve_diff_inputs` + `compute_delta` and returns the `TypedDelta` as JSON. Add `GET /api/git-status` returning the current branch + ahead/behind counts for the top bar badge.
2. **Frontend types.** Add `DiffPayload` / `ElementChange` / `TypedDelta` TypeScript mirrors to `editor/frontend/src/api/types.ts`. Extend the Zustand store to hold diff state alongside ontology state.
3. **Rendering.** Paint diff gutters on role cards (left edge 3px strip) and on flow edges (dash pattern + color overlay). Colors already in tokens (`--diff-add`, `--diff-change`, `--diff-remove`).
4. **Top bar badge.** Branch name + `+N ~M -K` summary from `git-status`.
5. **Parity review memo** at `editor/parity_reviews/03_diff_gutters.md`. Sign-off before commit.

## Conventions worth not forgetting

- **Never launch long-running servers in background via Bash.** User handles process starts; use one-shot curls for smoke tests.
- **No handwritten fonts anywhere.** JetBrains Mono only. The mockup's Caveat / Shadows Into Light were design-tool flourish, not intent.
- **Visual parity gate per screen.** Side-by-side render vs `editor/design_reference/wireframe.html`, memo in `editor/parity_reviews/`, user sign-off before merge.
- **Use `frontend-design` skill for UI work and `context7` for library docs.** Recorded in root `CLAUDE.md` under "Tooling conventions".
- **The ontology is the product; the editor is a tool.** Do not let editor scope leak into ontology semantics. When in doubt, consult the design brief.
