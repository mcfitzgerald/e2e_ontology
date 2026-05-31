"""Filesystem locations of the ontology's authored data files.

Resolved relative to this package so downstream consumers (e.g. the
`e2e_orchestrator` runtime) can locate the YAML sources without hard-coding a
repo path or relying on a sys.path shim. The authored data files live at the
repo root, one level above this package; an editable install (`uv` local
source) or a git-source checkout keeps them in place, so `__file__`-relative
resolution holds. (A non-editable wheel does not vendor these YAMLs — they are
not package data — which is intentional: the ontology is consumed from a
source checkout, not a built artifact.)
"""
from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

SUPPLY_CHAIN_DEMO_YAML: Path = _REPO_ROOT / "supply_chain_demo.yaml"
WORLD_STATE_YAML: Path = _REPO_ROOT / "world_state.yaml"
SCONT_META_YAML: Path = _REPO_ROOT / "scont_meta.yaml"
