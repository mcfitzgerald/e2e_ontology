"""Integration test: the refactored exploder produces the same counts and
key cross-references on the current supply_chain_demo.yaml as the pre-refactor
version. Phase A parity proof."""
from __future__ import annotations

from exploder import load_ontology


class TestDemoParity:
    """Post-Phase-B topology: procurement routes through supply/netops.
    demand_planning no longer drives procurement directly; supply_planning is
    the hub that emits submit_procurement_request once production is assigned."""

    def test_counts(self, demo_yaml_path):
        ontology = load_ontology(demo_yaml_path)
        # Post-Phase-D: original 4 + 7 core promo-whiplash entities (D1-D7)
        # + 5 query request/response entities (D8) = 16
        assert len(ontology.entities) == 16
        # Post-Phase-C: supply_planning, production_planning, logistics_planning
        # (internal) + customer_development, co_manufacturing (boundary)
        assert len(ontology.roles) == 8
        assert len(ontology.events) == 4
        assert len(ontology.state_machines) == 2
        assert len(ontology.flows) == 3
        # Post-Phase-D: +CommitmentStatus, +ProductionRequestStatus
        assert len(ontology.enums) == 5

    def test_entity_names(self, demo_yaml_path):
        ontology = load_ontology(demo_yaml_path)
        assert set(ontology.entities.keys()) == {
            # Pre-Phase-D (baseline procurement corridor)
            "ProcurementRequest", "Supplier", "SKU", "PurchaseOrder",
            # Phase D core entities
            "TradePromotion", "ProductionLine", "RetailerCommitment",
            "SupplyRequest", "ProductionRequest", "CapacityConflict", "OTIFExposure",
            # Phase D query flow quantum + response entities
            "OTIFQuery", "PromoFlexibilityQuery", "PromoFlexibility",
            "ComanAvailabilityQuery", "ComanAvailability",
        }

    def test_role_names(self, demo_yaml_path):
        ontology = load_ontology(demo_yaml_path)
        assert set(ontology.roles.keys()) == {
            "demand_planning",
            "procurement",
            "supplier_management",
            "supply_planning",
            "production_planning",
            "logistics_planning",
            "customer_development",
            "co_manufacturing",
        }

    def test_boundary_roles_identified(self, demo_yaml_path):
        ontology = load_ontology(demo_yaml_path)
        boundary_names = {r.name for r in ontology.list_boundary_roles()}
        assert boundary_names == {"customer_development", "co_manufacturing"}

    def test_flow_names(self, demo_yaml_path):
        ontology = load_ontology(demo_yaml_path)
        assert set(ontology.flows.keys()) == {
            "submit_procurement_request",
            "replan_on_infeasible_request",
            "submit_po_to_supplier",
        }

    def test_submit_procurement_request_shape(self, demo_yaml_path):
        ontology = load_ontology(demo_yaml_path)
        f = ontology.get_flow("submit_procurement_request")
        # Post-Phase-B: sourced by supply_planning, triggered by production_assigned
        assert f.body.source_role == "supply_planning"
        assert f.body.target_role == "procurement"
        assert f.body.quantum == "ProcurementRequest"
        assert f.body.trigger_event == "production_assigned"
        assert f.body.lifecycle_ref == "RequestLifecycle"
        assert f.body.returns is None  # not a query flow
        assert len(f.axioms) == 1
        assert f.axioms[0].name == "respect_lead_time"
        assert f.axioms[0].on_failure_route_to == "replan_on_infeasible_request"

    def test_replan_routes_to_supply_planning(self, demo_yaml_path):
        ontology = load_ontology(demo_yaml_path)
        f = ontology.get_flow("replan_on_infeasible_request")
        # Post-Phase-B: replan lands at supply_planning, not demand_planning
        assert f.body.source_role == "procurement"
        assert f.body.target_role == "supply_planning"

    def test_supply_planning_carries_conditional_hitl(self, demo_yaml_path):
        ontology = load_ontology(demo_yaml_path)
        sp = ontology.get_role("supply_planning")
        assert sp is not None
        assert sp.body.human_involvement == "conditional"

    def test_phase_d_core_entities_present(self, demo_yaml_path):
        ontology = load_ontology(demo_yaml_path)
        expected_core = {
            "TradePromotion",
            "ProductionLine",
            "RetailerCommitment",
            "SupplyRequest",
            "ProductionRequest",
            "CapacityConflict",
            "OTIFExposure",
        }
        assert expected_core.issubset(set(ontology.entities.keys()))

    def test_phase_d_query_entities_present(self, demo_yaml_path):
        ontology = load_ontology(demo_yaml_path)
        expected_query_pairs = {
            "OTIFQuery",
            "PromoFlexibilityQuery",
            "PromoFlexibility",
            "ComanAvailabilityQuery",
            "ComanAvailability",
        }
        assert expected_query_pairs.issubset(set(ontology.entities.keys()))

    def test_production_request_references_line(self, demo_yaml_path):
        ontology = load_ontology(demo_yaml_path)
        pr = ontology.get_entity("ProductionRequest")
        assert pr is not None
        assert pr.attributes["assigned_line"]["range"] == "ProductionLine"

    def test_capacity_conflict_references_commitments(self, demo_yaml_path):
        ontology = load_ontology(demo_yaml_path)
        cc = ontology.get_entity("CapacityConflict")
        assert cc.attributes["at_risk_commitments"]["range"] == "RetailerCommitment"
        assert cc.attributes["at_risk_commitments"].get("multivalued") is True

    def test_supplier_metric_parsed(self, demo_yaml_path):
        ontology = load_ontology(demo_yaml_path)
        supplier = ontology.get_entity("Supplier")
        assert len(supplier.metrics) == 1
        assert supplier.metrics[0].name == "supplier_lead_time"
        assert supplier.metrics[0].source == "local"
        assert supplier.metrics[0].promotion_target == "dbt"

    def test_procurement_request_has_rule(self, demo_yaml_path):
        ontology = load_ontology(demo_yaml_path)
        pr = ontology.get_entity("ProcurementRequest")
        assert len(pr.rules) == 1

    def test_fsm_transitions(self, demo_yaml_path):
        ontology = load_ontology(demo_yaml_path)
        sm = ontology.get_state_machine("RequestLifecycle")
        assert sm.body.initial == "draft"
        assert "approved" in sm.body.terminal
        # Verify the `from`→`from_state` normalization shim worked
        assert all(t.from_state for t in sm.body.transitions)

    def test_guard_resolves(self, demo_yaml_path):
        """Guards on RequestLifecycle should resolve to axiom names defined on flows."""
        ontology = load_ontology(demo_yaml_path)
        # respect_lead_time is the only guard; it resolves to the axiom on
        # submit_procurement_request. If the guard resolver is broken, load
        # would raise.
        sm = ontology.get_state_machine("RequestLifecycle")
        guarded = [t for t in sm.body.transitions if t.guard]
        assert guarded
        assert guarded[0].guard == "respect_lead_time"
