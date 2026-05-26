"""
FastAPI backend for the ontology editor.

Run:
    cd editor/backend
    uv run --with linkml --with pyyaml --with pydantic --with fastapi --with uvicorn \\
        uvicorn main:app --reload --port 8787
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

from cache import OntologyCache
from diff import compute_diff_payload
from git_status import get_git_status
from serialize import serialize_ontology

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_YAML = REPO_ROOT / "supply_chain_demo.yaml"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from exploder import DiffInputError  # type: ignore[import-not-found]  # noqa: E402


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


@app.get("/api/diff")
def diff(base: str = Query(default="HEAD")) -> dict[str, object]:
    head_path = _cache.path
    if not head_path.is_file():
        raise HTTPException(status_code=404, detail=f"Ontology YAML not found: {head_path}")
    try:
        return compute_diff_payload(head_path, base)
    except DiffInputError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute diff: {e}") from e


@app.get("/api/git-status")
def git_status() -> dict[str, object]:
    return get_git_status()
