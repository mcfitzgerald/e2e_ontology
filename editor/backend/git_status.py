"""
Repo state for the top-bar branch badge.

Returns branch, ahead/behind counts vs upstream, and a dirty flag. All
fields degrade independently — the editor still renders if the checkout
is detached, has no upstream, or isn't a git repo at all.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]


def get_git_status() -> dict[str, Any]:
    if not (REPO_ROOT / ".git").exists():
        return _empty(reason="not a git repository")

    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if branch == "HEAD":
        sha = _run(["git", "rev-parse", "--short", "HEAD"])
        branch_label = f"detached@{sha}" if sha else "detached"
        branch_value = None
    else:
        branch_label = branch or ""
        branch_value = branch

    ahead, behind = _ahead_behind()
    dirty = _dirty()
    head_short = _run(["git", "rev-parse", "--short", "HEAD"])

    return {
        "branch": branch_value,
        "branch_label": branch_label,
        "head_short": head_short,
        "ahead": ahead,
        "behind": behind,
        "dirty": dirty,
        "reason": None,
    }


def _empty(reason: str) -> dict[str, Any]:
    return {
        "branch": None,
        "branch_label": None,
        "head_short": None,
        "ahead": None,
        "behind": None,
        "dirty": None,
        "reason": reason,
    }


def _ahead_behind() -> tuple[int | None, int | None]:
    """`git rev-list --left-right --count @{upstream}...HEAD` → "behind\\tahead".
    Returns (None, None) when there's no upstream."""
    out = _run(["git", "rev-list", "--left-right", "--count", "@{upstream}...HEAD"])
    if out is None or "\t" not in out:
        return (None, None)
    behind_str, ahead_str = out.split("\t", 1)
    try:
        return (int(ahead_str), int(behind_str))
    except ValueError:
        return (None, None)


def _dirty() -> bool | None:
    """Any untracked, modified, or staged files → dirty."""
    out = _run(["git", "status", "--porcelain"])
    if out is None:
        return None
    return bool(out.strip())


def _run(cmd: list[str]) -> str | None:
    try:
        result = subprocess.run(
            cmd, cwd=REPO_ROOT, capture_output=True, check=True, text=True, timeout=2
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None
