"""
FastAPI backend for the ontology editor.

Run:
    cd editor/backend
    uv run --with linkml --with pyyaml --with pydantic --with fastapi --with uvicorn \\
        uvicorn main:app --reload --port 8787
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException

from cache import OntologyCache
from serialize import serialize_ontology

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_YAML = REPO_ROOT / "supply_chain_demo.yaml"


def _yaml_path() -> Path:
    override = os.environ.get("ONTOLOGY_YAML")
    return Path(override) if override else DEFAULT_YAML


app = FastAPI(title="Ontology Editor API", version="0.1.0")
_cache = OntologyCache(_yaml_path())


@app.get("/api/health")
def health() -> dict[str, object]:
    path = _cache.path
    return {
        "status": "ok",
        "yaml_path": str(path),
        "yaml_exists": path.is_file(),
    }


@app.get("/api/ontology")
def ontology() -> dict[str, object]:
    try:
        ont = _cache.get()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load ontology: {e}") from e
    return serialize_ontology(ont)
