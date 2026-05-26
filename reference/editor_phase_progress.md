# Editor — phase progress

A durable resume card for the ontology editor workstream. Start here if
you're a new session or coming back after a break. (For point-in-time
session handoffs see `reference/resume_note_*.md`.)

## Where things are

- **Branch:** `feat/editor-frontend` — Phase 4b complete, ready to merge to `main`.
- **Last commit:** `5476b5b` — Phase 4b Commit E (interaction polish + AGENTS.md retirement).
- **Directory:** `editor/` in the repo root.
- **Plan of record:** `claude_plans/squishy-scribbling-parnas.md` (frontend scaffold through Screens 1/2/3/4) + `claude_plans/linear-pondering-platypus.md` (Phase 4b React Flow port, A–E; reconstructed 2026-05-25 after the original was lost).
- **Design intent:** [`reference/ontology_editor_design_brief.md`](ontology_editor_design_brief.md).
- **Visual spec:** [`editor/design_reference/wireframe.html`](../editor/design_reference/wireframe.html) (reference only — NOT the implementation).
- **Parity reviews:** [`editor/parity_reviews/`](../editor/parity_reviews/) — memos 01–05 are historical artifacts. The per-screen memo convention was retired at Commit E once it had drifted to verbal sign-off in practice.
- **Glossary:** [`editor/GLOSSARY.md`](../editor/GLOSSARY.md) — vocabulary reference for ontology + editor terms.

## Phases

| Phase | Commit | Status | Scope |
|---|---|---|---|
| 0 — Scaffolding | `b089a7b` | ✅ | `editor/` tree, Vite + React 18 + TS strict frontend, FastAPI `/api/health` backend, design tokens extracted from mockup |
| 1 — Structure screen (Variant A) | `6c1cdb8` | ✅ | `/api/ontology`, SVG swimlane graph with dagre + per-lane X redistribution, custom RoleNode + FlowEdge, reorderable lanes, Legend |
| 2 — Context panel + navigation | `726b85d` | ✅ | Right-rail ContextPanel (collapsible), Breadcrumb with history stack, six kind panels (Role, Flow, Event, FSM, Axiom, Entity), Chip cross-links |
| 3 — Ambient diff indicators | `2690124` | ✅ | `/api/diff?base=<ref>` + `/api/git-status`, Zustand diff slice, BranchBadge, role-card diff flags, edge diff underlay, RemovedSinceHead banner, PanelDiff banner |
| 4a — Cascade view (hand SVG) + screen router | `46d38d3` | ✅ | Screen 2 cascade traversal (BFS over events + axiom trips), screen routing harness, FSM stub for router type-checking |
| 4b Commit A — Resizable rails + persistence | `00ae495` | ✅ | `react-resizable-panels@^2`, outer + Cascade nested PanelGroups, autoSaveId persistence, screen routing in localStorage |
| 4b Commit B — Structure on React Flow | `3db55d6` | ✅ | Port to `@xyflow/react@12`. Unlocks pan/zoom, hover-to-dim, fitView. HTML RoleNode + SVG FlowEdge via BaseEdge + ViewportPortal'd SwimlaneBackground |
| 4b Commit C — Cascade on React Flow | `ea4cee1` | ✅ | Port. Fixes the "via label" overlap that hand SVG couldn't avoid. EdgeLabelRenderer with paper-background pills, hover/focus-only labels |
| 4b UX polish | `8ae54b6` | ✅ | UI label "llm prompt hint" → "llm context"; `editor/GLOSSARY.md` added |
| 4b Commit D — FSM detail on React Flow | `b2a2aa1` | ✅ | First real FSM screen (was a stub). Dagre LR + StateNode (initial ▸, terminal ring) + smoothstep TransitionEdge with clickable trigger/guard chips; `flowOwningAxiom` for shared-lifecycle guard resolution |
| 4b Commit E — Interaction polish + AGENTS.md retired | `5476b5b` | ✅ | `useKeyboardShortcuts` hook (g/c/f/esc/no-op `/`); FSM minZoom 0.4→0.3; AGENTS.md deleted (never auto-loaded by Claude Code) |

## Next directions (none picked)

- **Filter rail** — domain multi-select, kind toggle, HITL filter, changed-since-HEAD toggle, search. Right rail wiring + Zustand filter state. The `useKeyboardShortcuts` `/` no-op is already forward-keeping the search-focus binding.
- **Authoring overlay (Screen 3) + write-through API** — wraps `exploder new <kind>` behind `POST /api/elements/<kind>`. Design brief explicitly defers this until the substrate is stable; it is now.
- **Direction 4** (initial_design_draft §12) — orchestrator-side read API. Standalone work, doesn't block editor merge to `main`.

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

Open `http://localhost:5173`. Vite proxies `/api/*` to port 8787.

## Conventions worth not forgetting

- **Never launch long-running servers in background via Bash.** User handles process starts; use one-shot curls for smoke tests.
- **No handwritten fonts anywhere.** JetBrains Mono only. The mockup's Caveat / Shadows Into Light were design-tool flourish, not intent.
- **Use `frontend-design` skill for UI work and `context7` for library docs.** Recorded in root `CLAUDE.md` under "Tooling conventions".
- **The ontology is the product; the editor is a tool.** Do not let editor scope leak into ontology semantics. When in doubt, consult the design brief.
- **Parity memos are no longer required per-screen.** The convention drifted to verbal sign-off in practice and was formally retired at Commit E. Memos 01–05 stay as historical artifacts.
