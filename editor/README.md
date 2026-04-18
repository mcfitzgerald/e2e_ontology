# Ontology Editor

A graph-first editor and explainer for the supply-chain ontology. Primary user: the ontology author, for R&D and walking the team through the model.

The editor renders live state from `supply_chain_demo.yaml` via `exploder.load_ontology()` — no data duplication, no drift.

> **Working on this directory?** Read [`AGENTS.md`](AGENTS.md) first. It documents the visual parity gate, stack conventions, and scope guardrails specific to this subtree.

## Status

Phase 0 scaffolding. Screen 1 (role swimlane graph) is the immediate next milestone.

Design intent: [`reference/ontology_editor_design_brief.md`](../reference/ontology_editor_design_brief.md).
Visual spec: [`editor/design_reference/wireframe.html`](design_reference/wireframe.html).

## Layout

```
editor/
  AGENTS.md                    ← directives for coding agents
  README.md                    ← this file
  design_reference/            ← Claude Design mockup, reference-only
  parity_reviews/              ← per-screen parity memos
  frontend/                    ← React + Vite + TypeScript SPA
  backend/                     ← FastAPI wrapping exploder.load_ontology()
```

## Running locally

You'll need two shells.

### Backend

```bash
cd editor/backend
uv run --with linkml --with pyyaml --with pydantic --with fastapi --with uvicorn \
  uvicorn main:app --reload --port 8787
```

Serves `/api/health`, `/api/ontology`, `/api/diff` on `http://localhost:8787`.

### Frontend

```bash
cd editor/frontend
npm install              # one-time
npm run dev
```

Vite serves on `http://localhost:5173` (or the next open port) and proxies `/api/*` to the backend.

### First-time smoke check

With both running, open `http://localhost:5173`. You should see the swimlane graph populated from `supply_chain_demo.yaml`. If the graph is empty, check that the backend started and that `/api/ontology` returns JSON.
