"""Unit tests for the Ontology Service (Phase 1.1) — role-scoped queries
over the loaded ontology. Snapshot tests for the rendered role views live in
`test_role_view_render.py`."""
from __future__ import annotations

import pytest

from ontology_service import OntologyService, UnknownRoleError


@pytest.fixture
def svc(demo_yaml_path) -> OntologyService:
    return OntologyService.load(demo_yaml_path)


class TestRoleLookup:
    def test_get_role_existing(self, svc):
        r = svc.get_role("demand_planning")
        assert r is not None
        assert r.body.description.startswith("Forecasts demand")

    def test_get_role_missing(self, svc):
        assert svc.get_role("does_not_exist") is None

    def test_human_involvement_conditional(self, svc):
        assert svc.human_involvement("supply_planning") == "conditional"

    def test_human_involvement_unspecified(self, svc):
        assert svc.human_involvement("demand_planning") is None

    def test_human_involvement_unknown_role_raises(self, svc):
        with pytest.raises(UnknownRoleError):
            svc.human_involvement("does_not_exist")


class TestHandoffs:
    def test_demand_planning_incoming_handoffs(self, svc):
        names = [f.name for f in svc.incoming_handoffs("demand_planning")]
        # Two ingresses: external boundary handoffs from demand_sensing and customer_development.
        assert names == ["raise_demand_anomaly", "submit_promo_plan"]

    def test_demand_planning_outgoing_handoffs(self, svc):
        names = [f.name for f in svc.outgoing_handoffs("demand_planning")]
        assert names == ["submit_supply_request"]

    def test_supply_planning_incoming_handoffs(self, svc):
        names = [f.name for f in svc.incoming_handoffs("supply_planning")]
        # Recovery + the topology-hinge intake from demand.
        assert set(names) == {
            "escalate_capacity_conflict",
            "replan_on_infeasible_request",
            "submit_supply_request",
        }

    def test_handoffs_exclude_query_flows(self, svc):
        """Flows with `returns:` set must never appear in handoff lists."""
        out = svc.outgoing_handoffs("supply_planning")
        assert all(f.body.returns is None for f in out)


class TestQueries:
    def test_supply_planning_outgoing_queries(self, svc):
        names = [f.name for f in svc.outgoing_queries("supply_planning")]
        # The three canonical context-assembly queries (Scene 5).
        assert set(names) == {
            "check_otif_exposure",
            "check_promo_flexibility",
            "check_coman_availability",
        }

    def test_logistics_planning_incoming_queries(self, svc):
        names = [f.name for f in svc.incoming_queries("logistics_planning")]
        assert names == ["check_otif_exposure"]

    def test_demand_planning_has_no_queries(self, svc):
        assert svc.outgoing_queries("demand_planning") == []
        assert svc.incoming_queries("demand_planning") == []

    def test_queries_exclude_handoffs(self, svc):
        """Flows without `returns:` must never appear in query lists."""
        out = svc.outgoing_queries("supply_planning")
        assert all(f.body.returns is not None for f in out)


class TestEventSurface:
    def test_demand_planning_observed_events(self, svc):
        names = [e.name for e in svc.events_observed("demand_planning")]
        # Triggers on raise_demand_anomaly + submit_promo_plan.
        assert set(names) == {"demand_anomaly_detected", "promo_plan_aligned"}

    def test_demand_planning_emitted_events(self, svc):
        names = [e.name for e in svc.events_emitted("demand_planning")]
        # observed_by == demand_planning.
        assert set(names) == {"demand_anomaly_detected", "forecast_revised"}

    def test_supply_planning_emitted_events(self, svc):
        names = [e.name for e in svc.events_emitted("supply_planning")]
        assert "production_assigned" in names
        assert "capacity_resolved" in names


class TestFSMs:
    def test_supply_planning_fsms(self, svc):
        names = [sm.name for sm in svc.fsms_for_role("supply_planning")]
        # ProductionRequestLifecycle (re_request_production, shift_to_coman),
        # RequestLifecycle (procurement-side recovery / submit_procurement_request),
        # TradePromotionLifecycle (request_promo_revision).
        assert "ProductionRequestLifecycle" in names
        assert "RequestLifecycle" in names
        assert "TradePromotionLifecycle" in names

    def test_fsm_shared_lifecycle_pattern(self, svc):
        """The canonical multi-flow shared-lifecycle case: supply_planning
        sources three outgoing flows on ProductionRequestLifecycle —
        request_production (initial assignment), re_request_production
        (internal re-entry after capacity_resolved), and shift_to_coman
        (external boundary handoff under the same lifecycle)."""
        flows = svc.flows_governed_by_fsm("ProductionRequestLifecycle", "supply_planning")
        names = sorted(f.name for f in flows)
        assert names == ["re_request_production", "request_production", "shift_to_coman"]


class TestAxioms:
    def test_axioms_on_request_production(self, svc):
        ax = svc.axioms_on_flow("request_production")
        assert len(ax) == 1
        assert ax[0].name == "line_capacity_not_exceeded"
        assert ax[0].on_failure_route_to == "escalate_capacity_conflict"

    def test_axioms_on_unknown_flow_empty(self, svc):
        assert svc.axioms_on_flow("does_not_exist") == []


class TestOrderDiscipline:
    """The §2 design rule forbids inventing priority. All result lists are
    sorted alphabetically by name so order is deterministic across runs and
    legible to humans without implying preference."""

    def test_outgoing_handoffs_sorted_by_name(self, svc):
        out = svc.outgoing_handoffs("supply_planning")
        names = [f.name for f in out]
        assert names == sorted(names)

    def test_outgoing_queries_sorted_by_name(self, svc):
        out = svc.outgoing_queries("supply_planning")
        names = [f.name for f in out]
        assert names == sorted(names)

    def test_events_emitted_sorted_by_name(self, svc):
        names = [e.name for e in svc.events_emitted("supply_planning")]
        assert names == sorted(names)


class TestQuantumSchemas:
    """Phase 1.5 — quantum + returns slot schemas surface in FlowSummary so
    the agent prompt teaches the LLM payload shape. Without this, Phase 2
    showed that LLMs guess slot names and "get lucky." Slot structure is
    world model (§2), the same kind of declaration as `target_role`."""

    def test_handoff_carries_quantum_schema(self, svc):
        v = svc.render_role_view("demand_planning")
        f = next(x for x in v.outgoing_handoffs if x.name == "submit_supply_request")
        assert f.quantum_schema is not None
        assert f.quantum_schema.name == "SupplyRequest"
        slot_names = {s.name for s in f.quantum_schema.slots}
        assert slot_names == {
            "request_id", "sku", "volume", "required_by", "source_signal_ref",
        }
        # Required-ness is load-bearing — Phase 2 failed when the LLM omitted
        # required slots. Snapshot the contract explicitly.
        required = {s.name for s in f.quantum_schema.slots if s.required}
        assert required == {"request_id", "sku", "volume", "required_by"}
        # No `returns:` on a handoff.
        assert f.returns_schema is None

    def test_class_typed_slot_marked_class_kind(self, svc):
        v = svc.render_role_view("demand_planning")
        f = next(x for x in v.outgoing_handoffs if x.name == "submit_supply_request")
        sku_slot = next(s for s in f.quantum_schema.slots if s.name == "sku")
        assert sku_slot.range == "SKU"
        assert sku_slot.range_kind == "class"
        # Permissible values only populate for enums.
        assert sku_slot.permissible_values == ()

    def test_query_flow_carries_both_quantum_and_returns_schemas(self, svc):
        v = svc.render_role_view("supply_planning")
        f = next(x for x in v.outgoing_queries if x.name == "check_otif_exposure")
        assert f.quantum_schema is not None and f.quantum_schema.name == "OTIFQuery"
        assert f.returns_schema is not None and f.returns_schema.name == "OTIFExposure"
        # OTIFExposure includes calculated_penalty — the field supply_planning
        # actually reads during Mode 2 trade-off reasoning.
        returns_slots = {s.name for s in f.returns_schema.slots}
        assert "calculated_penalty" in returns_slots
        assert "affected_shipment_value" in returns_slots

    def test_enum_slot_carries_permissible_values(self, svc):
        """PromoFlexibility.commitment_status is an enum; the agent needs the
        permissible values inline so it can interpret a returned value without
        a second read_ontology trip."""
        v = svc.render_role_view("supply_planning")
        f = next(x for x in v.outgoing_queries if x.name == "check_promo_flexibility")
        cs_slot = next(s for s in f.returns_schema.slots if s.name == "commitment_status")
        assert cs_slot.range == "CommitmentStatus"
        assert cs_slot.range_kind == "enum"
        assert set(cs_slot.permissible_values) == {
            "proposed", "aligned", "committed", "contractually_locked",
        }

    def test_multivalued_slot_carried_through(self, svc):
        """CapacityConflict.competing_skus is multivalued. The render needs
        to expose this so the LLM knows to pass a list, not a single id."""
        # CapacityConflict appears on escalate_capacity_conflict
        # (production_planning → supply_planning).
        v = svc.render_role_view("supply_planning")
        f = next(x for x in v.incoming_handoffs if x.name == "escalate_capacity_conflict")
        skus_slot = next(
            s for s in f.quantum_schema.slots if s.name == "competing_skus"
        )
        assert skus_slot.multivalued is True
        assert skus_slot.range == "SKU"
        assert skus_slot.range_kind == "class"

    def test_optional_slot_marked_optional(self, svc):
        v = svc.render_role_view("demand_planning")
        f = next(x for x in v.outgoing_handoffs if x.name == "submit_supply_request")
        signal_ref = next(
            s for s in f.quantum_schema.slots if s.name == "source_signal_ref"
        )
        assert signal_ref.required is False
