"""Phase B Definition-of-Done — 7-O, the ontology knowledge-MCP (read-the-model).

  DoD: a knowledge worker can ask the model questions about the supply-chain
  STRUCTURE over MCP — roles, flows, quanta, events, playbooks — and the headline
  question *"if Megalomart's promo slips a week, who's affected?"* is answered by
  traversing the ontology, no run required.

Pins, deterministically (no LLM, no API key):

  • the read-the-element tools (read_role/flow/quantum/playbook, model_summary)
    project the real Ontology Service;
  • traverse() + impact_analysis() walk the structural graph; the headline impact
    query lights up the promo-whiplash machinery from `TradePromotion`;
  • §2 — impact is an UNRANKED structural set (no score/priority/preference); the
    model surfaces decision *criteria*, never their weighting;
  • through a real MCP `ClientSession` over the SDK's in-memory transport (the
    handlers are tested against the real seams, not mocks): list tools/resource
    templates, call impact_analysis, read `ontology://source` + `roleview://{role}`;
  • `roleview://{role}` is byte-identical to render_role_view(role).as_agent_prompt().

7-O wraps the Ontology Service, NOT the orchestrator — no event log, no ingress,
no scenario registry (distinct from 7-S).
"""
from __future__ import annotations

import json
from datetime import timedelta

import pytest
from mcp.shared.memory import create_connected_server_and_client_session as connect
from mcp.types import AnyUrl

from mcp_server.core import OntologyKnowledgeService, UnknownNodeError
from mcp_server.server import build_server


@pytest.fixture(scope="module")
def k() -> OntologyKnowledgeService:
    return OntologyKnowledgeService()


# ---------------------------------------------------------------------------
# read-the-element tools project the real model
# ---------------------------------------------------------------------------


def test_model_summary(k):
    s = k.model_summary()
    assert s["counts"]["roles"] >= 8
    assert "supply_planning" in s["roles"]
    assert "resolve_capacity_conflict" in s["playbooks"]
    # boundary roles are derived from the ontology's is_boundary, not enumerated
    assert "customer_development" in s["boundary_roles"]


def test_read_role(k):
    r = k.read_role("supply_planning")
    assert r["kind"] == "role"
    assert r["is_boundary"] is False
    # it runs the resolution playbook and fans out the context queries
    assert "resolve_capacity_conflict" in r["playbooks"]
    assert "check_promo_flexibility" in r["outgoing_queries"]


def test_read_flow(k):
    f = k.read_flow("request_promo_revision")
    assert f["quantum"] == "TradePromotion"
    assert f["source_role"] and f["target_role"]


def test_read_quantum(k):
    q = k.read_quantum("TradePromotion")
    assert "commitment_status" in q["attributes"]
    assert q["attributes"]["promo_id"]["required"] is True
    assert "submit_promo_plan" in q["carried_by_flows"]


def test_read_playbook_surfaces_criteria_not_weighting(k):
    p = k.read_playbook("resolve_capacity_conflict")
    assert p["role"] == "supply_planning"
    assert p["selects_one_of"]  # the action vocabulary
    assert p["context_assembly"]  # the query flows it assembles
    # §2: the playbook exposes WHICH criteria are weighed and WHICH actions are
    # available — never a weighting/preference/priority over them.
    forbidden = {"weight", "weights", "priority", "preference", "ranking", "score", "prefer"}
    assert forbidden.isdisjoint(set(p.keys()))


# ---------------------------------------------------------------------------
# traverse + impact (the headline)
# ---------------------------------------------------------------------------


def test_traverse_one_hop(k):
    t = k.traverse("supply_planning")
    assert t["kind"] == "role"
    rels = {e["relation"] for e in t["neighbors"]}
    assert "runs_playbook" in rels
    # filtered traversal
    only = k.traverse("supply_planning", relation="runs_playbook")
    assert all(e["relation"] == "runs_playbook" for e in only["neighbors"])
    assert {e["id"] for e in only["neighbors"]} == {"resolve_capacity_conflict"}


def test_impact_analysis_headline(k):
    """'If Megalomart's promo (a TradePromotion) slips a week, who's affected?'"""
    imp = k.impact_analysis("TradePromotion", change="slip_one_week")
    assert imp["start"] == "TradePromotion"
    assert imp["change"] == "slip_one_week"
    roles = set(imp["affected"].get("role", []))
    # the slip ripples to the whole resolution cast — trade (owns the promo
    # revision), supply_planning (resolves), customer_development (boundary)
    assert {"trade", "supply_planning", "customer_development"} <= roles
    assert "resolve_capacity_conflict" in imp["affected"].get("playbook", [])
    # a structural path explains WHY each element is reachable (for the client)
    assert imp["paths"]["resolve_capacity_conflict"]


def test_impact_is_unranked_structural_set(k):
    """§2: the closure is returned grouped + name-sorted, NOT ranked by impact.
    No score/priority surface anywhere in the result."""
    imp = k.impact_analysis("TradePromotion")
    for kind, names in imp["affected"].items():
        assert names == sorted(names), f"{kind} list is ordered by something other than name"
    blob = json.dumps(imp).lower()
    for word in ("priority", "ranking", "score", "most_affected", "severity"):
        assert word not in blob, f"impact result leaked a ranking word: {word}"
    assert "unranked" in imp["note"].lower()


def test_walk_flow_chain_is_ontology_only(k):
    w = k.walk_flow_chain("submit_promo_plan")
    assert w["start_flow"] == "submit_promo_plan"
    assert w["steps"]
    assert w["steps"][0]["flow"] == "submit_promo_plan"


def test_unknown_nodes_raise(k):
    with pytest.raises(UnknownNodeError):
        k.read_role("no_such_role")
    with pytest.raises(UnknownNodeError):
        k.impact_analysis("NoSuchEntity")
    with pytest.raises(UnknownNodeError):
        k.doc("../pyproject.toml")  # path traversal guarded


# ---------------------------------------------------------------------------
# resources
# ---------------------------------------------------------------------------


def test_resources_project_the_model(k):
    src = k.ontology_source()
    assert "supply_chain" in src.lower()
    rv = k.roleview("supply_planning")
    assert rv == k.service.render_role_view("supply_planning").as_agent_prompt()
    assert k.doc("plan_of_attack.md")  # a real repo-root doc


# ---------------------------------------------------------------------------
# through a real MCP ClientSession (in-memory transport, real seams)
# ---------------------------------------------------------------------------


async def test_end_to_end_through_mcp_client(k):
    """A standard MCP client lists tools/resource-templates, calls
    impact_analysis, and reads ontology://source + roleview://{role} — the CSCO's
    'ask the model' loop, over the protocol."""
    server = build_server(k)
    async with connect(server, read_timeout_seconds=timedelta(seconds=60)) as session:
        await session.initialize()

        tools = {t.name for t in (await session.list_tools()).tools}
        assert {"read_role", "read_flow", "read_quantum", "read_playbook",
                "traverse", "impact_analysis", "model_summary", "walk_flow_chain"} <= tools

        templates = {t.uriTemplate for t in (await session.list_resource_templates()).resourceTemplates}
        assert {"roleview://{role}", "docs://{name}"} <= templates

        call = await session.call_tool(
            "impact_analysis", {"start_id": "TradePromotion", "change": "slip_one_week"}
        )
        out = json.loads(call.content[0].text)
        assert "trade" in out["affected"]["role"]
        assert out["affected_count"] > 10

        # static resource: the model's own YAML
        src = await session.read_resource(AnyUrl("ontology://source"))
        assert "supply_chain" in src.contents[0].text.lower()

        # template resource: byte-faithful role view through the protocol
        rv = await session.read_resource(AnyUrl("roleview://supply_planning"))
        assert rv.contents[0].text == k.service.render_role_view("supply_planning").as_agent_prompt()
