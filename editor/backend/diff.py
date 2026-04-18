"""
Diff endpoint helpers.

Wraps `exploder._resolve_diff_inputs` + `compute_delta` and reshapes the
`TypedDelta` list into a JSON-friendly payload organized by element kind.
The frontend uses the per-kind structure to paint diff gutters and the
context-panel `panel-diff` section.

The default contract for the editor is:
    base = <git ref>          (default: "HEAD")
    head = <working copy YAML on disk>

`head` is intentionally not exposed as a query param — the editor is
always comparing the working tree against a chosen ref. If the brief ever
needs ref-vs-ref, that's a follow-up.
"""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterator

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from exploder import (  # type: ignore[import-not-found]
    DiffInputError,
    ElementChange,
    TypedDelta,
    _resolve_diff_inputs,
    compute_delta,
    load_ontology,
)


def compute_diff_payload(head_path: Path, base: str) -> dict[str, Any]:
    """Resolve `base` (a git ref) against the on-disk `head_path` and return
    a JSON-friendly diff payload. Raises DiffInputError on resolution failure."""
    base_path = str(base)
    head_str = str(head_path)
    with _chdir(REPO_ROOT), _resolve_diff_inputs(base_path, head_str, head_path.name) as (p1, p2):
        old = load_ontology(p1)
        new = load_ontology(p2)
        deltas = compute_delta(old, new)

    base_resolved = _resolve_ref(base) if base != "working" else None

    return {
        "base": base,
        "base_resolved": base_resolved,
        "head": "working",
        "head_path": str(head_path),
        "kinds": _deltas_to_kinds(deltas),
        "summary": _summary(deltas),
    }


def _deltas_to_kinds(deltas: list[TypedDelta]) -> dict[str, dict[str, Any]]:
    """Transform `list[TypedDelta]` into `{kind: {added, removed, changed}}`.
    Kinds with no changes are omitted entirely so the frontend can use
    `kind in payload.kinds` as a quick has-changes check."""
    out: dict[str, dict[str, Any]] = {}
    for d in deltas:
        out[d.kind] = {
            "added": list(d.added),
            "removed": list(d.removed),
            "changed": [_change(c) for c in d.changed],
        }
    return out


def _change(c: ElementChange) -> dict[str, Any]:
    return {
        "name": c.name,
        "changes": [
            {"path": path, "before": _jsonable(before), "after": _jsonable(after)}
            for (path, before, after) in c.changes
        ],
    }


def _jsonable(value: Any) -> Any:
    """ElementChange tuples carry whatever `_element_to_comparable` produced —
    plain dicts, lists, and scalars from `model_dump(mode='json')`. Tuples
    occasionally sneak through (e.g. Ontology.warnings comparison); coerce
    to lists for JSON serialization."""
    if isinstance(value, tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


def _summary(deltas: list[TypedDelta]) -> dict[str, int]:
    """Aggregate counts across all kinds. Used by the top-bar branch badge
    (e.g. `+3 ~2 -0`). Warnings are excluded from the badge — they're not
    structural changes."""
    added = changed = removed = 0
    for d in deltas:
        if d.kind == "warnings":
            continue
        added += len(d.added)
        changed += len(d.changed)
        removed += len(d.removed)
    return {"added": added, "changed": changed, "removed": removed}


def _resolve_ref(ref: str) -> str | None:
    """Best-effort: turn a ref like `HEAD` into its short SHA for display.
    Returns None on failure rather than raising — the badge can show the
    symbolic name alone."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", ref],
            cwd=REPO_ROOT,
            capture_output=True,
            check=True,
            text=True,
            timeout=2,
        )
        return out.stdout.strip() or None
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None


@contextlib.contextmanager
def _chdir(path: Path) -> Iterator[None]:
    """`exploder._git_archive_to` invokes `git archive` with no explicit cwd,
    so it inherits the process cwd — which is `editor/backend/` under uvicorn.
    From there `git archive HEAD` only ships that subdirectory's files.
    Switch to repo root for the duration of the diff and restore afterwards."""
    prev = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


__all__ = ["compute_diff_payload", "DiffInputError"]
