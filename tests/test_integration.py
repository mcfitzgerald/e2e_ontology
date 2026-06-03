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
        # Post-Phase-F: adds DemandAnomaly as the ingress quantum → 16 + 1 = 17.
        # Phase 1.8: + 7 reader-tool query/result entities (PlantQuery,
        # PlantQueryResult, LineLoadQuery, LineLoad, CommitmentQuery,
        # CommitmentQueryResult, SupplierQuery) → 17 + 7 = 24.
        # Seed A (demand grounding): + BaselineDemandQuery, BaselineDemand → 26.
        assert len(ontology.entities) == 26
        # Post-Phase-F: + demand_sensing boundary role
        assert len(ontology.roles) == 9
        # Post-Phase-F: + capacity_resolved
        assert len(ontology.events) == 8
        assert len(ontology.state_machines) == 4
        # Post-Phase-F: original 3 + 8 handoffs (incl. re_request_production)
        # + 3 query + 1 ingress (raise_demand_anomaly) = 15
        assert len(ontology.flows) == 15
        # Phase 1.8: the Scene 5 Playbook + the four reader Tools.
        # Seed A: + query_baseline_demand reader Tool → 5.
        assert len(ontology.playbooks) == 1
        assert len(ontology.tools) == 5
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
            # Phase F ingress quantum
            "DemandAnomaly",
            # Phase 1.8 reader-tool query/result entities
            "PlantQuery", "PlantQueryResult", "LineLoadQuery", "LineLoad",
            "CommitmentQuery", "CommitmentQueryResult", "SupplierQuery",
            # Seed A demand-grounding reader-tool query/result entities
            "BaselineDemandQuery", "BaselineDemand",
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
            "demand_sensing",
        }

    def test_boundary_roles_identified(self, demo_yaml_path):
        ontology = load_ontology(demo_yaml_path)
        boundary_names = {r.name for r in ontology.list_boundary_roles()}
        assert boundary_names == {
            "customer_development",
            "co_manufacturing",
            "demand_sensing",
        }

    def test_flow_names(self, demo_yaml_path):
        ontology = load_ontology(demo_yaml_path)
        assert set(ontology.flows.keys()) == {
            # Baseline procurement corridor
            "submit_procurement_request",
            "replan_on_infeasible_request",
            "submit_po_to_supplier",
            # Phase F ingress + handoffs
            "submit_promo_plan",
            "raise_demand_anomaly",
            "submit_supply_request",
            "request_production",
            "escalate_capacity_conflict",
            "shift_to_coman",
            "plan_fulfillment",
            "request_promo_revision",
            "re_request_production",
            # Phase F query flows
            "check_otif_exposure",
            "check_promo_flexibility",
            "check_coman_availability",
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

    def test_phase_e_events_observed_by_right_roles(self, demo_yaml_path):
        ontology = load_ontology(demo_yaml_path)
        assert ontology.get_event("promo_plan_aligned").body.observed_by == "customer_development"
        assert ontology.get_event("forecast_revised").body.observed_by == "demand_planning"
        assert ontology.get_event("capacity_conflict_detected").body.observed_by == "production_planning"

    def test_phase_e_fsms_structurally_sound(self, demo_yaml_path):
        ontology = load_ontology(demo_yaml_path)
        prl = ontology.get_state_machine("ProductionRequestLifecycle")
        assert prl is not None
        assert prl.body.initial == "requested"
        assert "completed" in prl.body.terminal
        assert "cancelled" in prl.body.terminal

        tpl = ontology.get_state_machine("TradePromotionLifecycle")
        assert tpl is not None
        assert tpl.body.initial == "proposed"
        assert "completed" in tpl.body.terminal

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
