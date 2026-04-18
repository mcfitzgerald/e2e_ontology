"""
FastAPI backend for the ontology editor.

Phase 0 exposes only /api/health. Phases 1+ will add /api/ontology and
/api/diff, which wrap exploder.load_ontology() and cmd_diff respectively.

Run:
    cd editor/backend
    uv run --with linkml --with pyyaml --with pydantic --with fastapi --with uvicorn \\
        uvicorn main:app --reload --port 8787
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_YAML = REPO_ROOT / "supply_chain_demo.yaml"

app = FastAPI(title="Ontology Editor API", version="0.0.1")


def _yaml_path() -> Path:
    override = os.environ.get("ONTOLOGY_YAML")
    return Path(override) if override else DEFAULT_YAML


@app.get("/api/health")
def health() -> dict[str, object]:
    path = _yaml_path()
    return {
        "status": "ok",
        "yaml_path": str(path),
        "yaml_exists": path.is_file(),
    }
