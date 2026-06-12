"""
Editor backend serialization parity (Playbook + Tool).

The visual editor reads the ontology through editor/backend/serialize.py. These
tests lock the Playbook/Tool serialization added so the constructs reach the
frontend rather than being silently dropped (the drift this suite was added to
prevent). Structural shape only — content lives in supply_chain_demo.yaml.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EDITOR_BACKEND = REPO_ROOT / "editor" / "backend"
for p in (str(REPO_ROOT), str(EDITOR_BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)

from exploder import load_ontology  # noqa: E402
from serialize import serialize_ontology  # noqa: E402

DEMO = REPO_ROOT / "supply_chain_demo.yaml"


@pytest.fixture(scope="module")
def payload() -> dict:
    return serialize_ontology(load_ontology(str(DEMO)))


def test_playbooks_and_tools_present(payload: dict) -> None:
    assert payload["playbooks"], "no playbooks serialized — editor would be blind to them"
    assert payload["tools"], "no tools serialized — editor would be blind to them"


def test_summary_counts_match(payload: dict) -> None:
    assert payload["summary"]["playbooks"] == len(payload["playbooks"])
    assert payload["summary"]["tools"] == len(payload["tools"])


def test_playbook_shape(payload: dict) -> None:
    pb = payload["playbooks"][0]
    expected = {
        "name",
        "domain",
        "subdomain",
        "role",
        "triggered_by",
        "input_quantum",
        "synchronization",
        "closed_set",
        "context_assembly",
        "decision",
        "always_fires",
        "llm_prompt_hint",
    }
    assert expected <= set(pb)
    assert isinstance(pb["context_assembly"], list)
    for step in pb["context_assembly"]:
        assert {"flow", "required", "inputs_from_quantum"} <= set(step)
        for binding in step["inputs_from_quantum"]:
            assert set(binding) == {"param", "from_quantum"}
    if pb["decision"] is not None:
        assert {"criteria_refs", "selects_one_of"} <= set(pb["decision"])
    for af in pb["always_fires"]:
        assert set(af) == {"event", "flow"}


def test_tool_shape(payload: dict) -> None:
    tool = payload["tools"][0]
    expected = {
        "name",
        "domain",
        "subdomain",
        "description",
        "category",
        "input_class",
        "output_class",
        "implementation",
        "deterministic",
        "available_to",
        "llm_prompt_hint",
    }
    assert expected <= set(tool)
    assert isinstance(tool["available_to"], list)


def test_capacity_playbook_resolves(payload: dict) -> None:
    """The canonical Scene-5 playbook must round-trip with its choreography."""
    by_name = {p["name"]: p for p in payload["playbooks"]}
    pb = by_name.get("resolve_capacity_conflict")
    assert pb is not None
    assert pb["role"] == "supply_planning"
    assert pb["triggered_by"] == "capacity_conflict_detected"
    assert pb["decision"] is not None
    assert len(pb["decision"]["selects_one_of"]) >= 2
    assert len(pb["context_assembly"]) >= 1


def test_tools_reference_real_roles(payload: dict) -> None:
    role_names = {r["name"] for r in payload["roles"]}
    for tool in payload["tools"]:
        for role in tool["available_to"]:
            assert role in role_names, f"{tool['name']} available_to unknown role {role!r}"
