# Editor frontend — directives for coding agents

Scope: everything under `editor/`. These directives supplement the root `CLAUDE.md`; when they conflict, this file wins inside this subtree.

## The mockup is the spec

- `editor/design_reference/wireframe.html` is the visual/UX spec. Consult it before implementing any screen.
- Extract design tokens (palette, fonts, sketchy SVG filter, flow-glyph styles) verbatim from the mockup into `editor/frontend/src/tokens/`. Do not reinvent.
- Do NOT copy the mockup's React+Babel-standalone runtime, inline `window.ONTOLOGY` data structure, or hand-positioned role coordinates. Those were mockup conveniences, not the contract.
- If the mockup and the design brief (`reference/ontology_editor_design_brief.md`) disagree, the brief wins — the mockup is one materialization of the brief, not the other way around. Flag the conflict to the user.

## Visual parity gate

Every screen requires a parity review before merge.

1. Open `editor/design_reference/wireframe.html` in one browser tab (pick the target screen — localStorage persists selection).
2. Serve the real editor locally and open the equivalent screen in a second tab.
3. Write a parity memo at `editor/parity_reviews/<screen>.md` enumerating visual diffs (intentional vs unintentional drift).
4. Request user sign-off. Only merge after approval.

## Tooling

- Frontend changes must invoke the `frontend-design` skill (see root `CLAUDE.md`). The skill produces distinctive, production-grade output and avoids generic AI-styled frontends.
- Library/API/CLI docs come from `context7`, not web search or model memory. This applies to React, Vite, React Flow, dagre, Zustand, FastAPI, `uv`, and anything else in the stack. Your training data may be stale.

## Scope guardrails

- Graph-first, physical+process-structure-first. Do not drift into LLM-prompt-hint authoring tooling — the user has explicitly deprioritized it.
- No authoring writes in v1 beyond what the design brief specifies. Screen 3 (Authoring) stays mockup-only until Screens 1/2/4 land and patterns prove out.
- Desktop-first (1440+ min, 1920+ ideal). Do not add mobile/tablet responsive breakpoints without user direction.
- Single-user. No auth, no multi-tenancy, no collaboration plumbing.

## Data flow

- Frontend reads ontology state exclusively from the FastAPI backend under `editor/backend/`.
- Backend reads ontology state exclusively via `exploder.load_ontology()` (from the repo root `exploder.py`) — never re-parse YAML directly.
- Everything goes through `Ontology` dataclass + `SchemaView`. If you need slot introspection, use `SchemaView.class_induced_slots()`.

## Stack conventions

- React 18 + TypeScript (strict mode). No `any` without a comment explaining why.
- Vite for dev/build. No Next.js, no SSR.
- React Flow (`@xyflow/react`) for the graph surface. Dagre (`@dagrejs/dagre`) for auto-layout.
- Zustand for state. No Redux.
- Plain CSS modules + CSS custom properties. No Tailwind, no styled-components, no CSS-in-JS.
- Inline SVG for icons/glyphs. No icon libraries.
- FastAPI + uvicorn for the backend. Deps via `uv run --with …`, consistent with repo convention.
