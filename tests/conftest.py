"""Shared fixtures for exploder tests."""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def demo_yaml_path(repo_root: Path) -> Path:
    return repo_root / "supply_chain_demo.yaml"


@pytest.fixture
def write_yaml(tmp_path: Path):
    """Factory for writing a single test YAML file. The core.yaml is not
    imported — scont tags are recognized as strings by the exploder."""

    def _write(content: str, name: str = "test.yaml") -> Path:
        f = tmp_path / name
        f.write_text(textwrap.dedent(content).lstrip())
        return f

    return _write


# Minimal valid ontology snippets used as building blocks in several tests.

MINIMAL_PREAMBLE = """
id: https://test.example/x
name: x
prefixes:
  linkml: https://w3id.org/linkml/
  scont:  https://e2e-ontology.dev/
default_prefix: scont
imports:
  - linkml:types
"""


@pytest.fixture
def preamble() -> str:
    return MINIMAL_PREAMBLE
