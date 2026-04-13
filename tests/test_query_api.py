"""Tests for the Ontology query API (get_flow, list_flows_where, etc.)."""
from __future__ import annotations

import pytest

from exploder import load_ontology


@pytest.fixture
def loaded_demo(demo_yaml_path):
    return load_ontology(demo_yaml_path)


class TestGetters:
    def test_get_flow_existing(self, loaded_demo):
        f = loaded_demo.get_flow("submit_procurement_request")
        assert f is not None
        # Post-Phase-B: sourced by supply_planning
        assert f.body.source_role == "supply_planning"

    def test_get_flow_missing(self, loaded_demo):
        assert loaded_demo.get_flow("nonexistent") is None

    def test_get_role(self, loaded_demo):
        r = loaded_demo.get_role("procurement")
        assert r is not None
        assert r.body.description.startswith("Sources materials")

    def test_get_event(self, loaded_demo):
        e = loaded_demo.get_event("po_drafted")
        assert e is not None
        assert e.body.observed_by == "procurement"

    def test_get_entity(self, loaded_demo):
        e = loaded_demo.get_entity("ProcurementRequest")
        assert e is not None
        assert e.rules  # has a Tier-1 rule

    def test_get_state_machine(self, loaded_demo):
        sm = loaded_demo.get_state_machine("PurchaseOrderLifecycle")
        assert sm is not None
        assert "draft" in sm.body.states


class TestFlowFilters:
    def test_filter_by_source_role(self, loaded_demo):
        flows = loaded_demo.list_flows_where(source_role="procurement")
        names = {f.name for f in flows}
        assert "replan_on_infeasible_request" in names
        assert "submit_po_to_supplier" in names
        assert "submit_procurement_request" not in names

    def test_filter_by_quantum(self, loaded_demo):
        flows = loaded_demo.list_flows_where(quantum="PurchaseOrder")
        assert len(flows) == 1
        assert flows[0].name == "submit_po_to_supplier"

    def test_filter_by_trigger(self, loaded_demo):
        # Post-Phase-B: submit_procurement_request is now triggered by production_assigned
        flows = loaded_demo.list_flows_where(trigger_event="production_assigned")
        assert any(f.name == "submit_procurement_request" for f in flows)

    def test_no_filters_returns_all(self, loaded_demo):
        flows = loaded_demo.list_flows_where()
        assert len(flows) == len(loaded_demo.flows)


class TestQueryVsHandoff:
    def test_list_query_flows(self, loaded_demo):
        # Demo ontology has no query flows yet — all current flows are handoffs
        query_flows = loaded_demo.list_query_flows()
        assert query_flows == []

    def test_list_handoff_flows(self, loaded_demo):
        handoffs = loaded_demo.list_handoff_flows()
        assert len(handoffs) == len(loaded_demo.flows)


class TestMisc:
    def test_find_flows_triggered_by(self, loaded_demo):
        flows = loaded_demo.find_flows_triggered_by("po_drafted")
        assert any(f.name == "submit_po_to_supplier" for f in flows)

    def test_get_axioms_for_flow(self, loaded_demo):
        axioms = loaded_demo.get_axioms_for("submit_procurement_request")
        names = {a.name for a in axioms}
        assert "respect_lead_time" in names

    def test_get_axioms_for_unknown(self, loaded_demo):
        assert loaded_demo.get_axioms_for("nothing") == []

    def test_traverse_fsm(self, loaded_demo):
        transitions = loaded_demo.traverse_fsm("RequestLifecycle", "submitted")
        to_states = {t.to_state for t in transitions}
        assert "approved" in to_states
        assert "rejected" in to_states

    def test_list_boundary_roles(self, loaded_demo):
        # Post-Phase-C: customer_development and co_manufacturing are boundary roles
        boundary_names = {r.name for r in loaded_demo.list_boundary_roles()}
        assert boundary_names == {"customer_development", "co_manufacturing"}
