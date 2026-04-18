"""
Mtime-keyed cache for the resolved ontology. Reloads from disk only when
the YAML file's mtime changes; returns the cached Ontology otherwise.
"""

from __future__ import annotations

import sys
from pathlib import Path
from threading import Lock

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from exploder import Ontology, load_ontology  # type: ignore[import-not-found]


class OntologyCache:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._mtime: float | None = None
        self._ontology: Ontology | None = None
        self._lock = Lock()

    @property
    def path(self) -> Path:
        return self._path

    def get(self) -> Ontology:
        if not self._path.is_file():
            raise FileNotFoundError(f"Ontology YAML not found: {self._path}")
        current = self._path.stat().st_mtime
        with self._lock:
            if self._ontology is None or self._mtime != current:
                self._ontology = load_ontology(self._path)
                self._mtime = current
            return self._ontology
