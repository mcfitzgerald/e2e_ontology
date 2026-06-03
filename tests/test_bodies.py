"""Pydantic body validation tests — exercise the auto-generated scont_bodies
module directly to confirm that gen-pydantic produces the expected strict
validators. These tests are the canary for the scont_meta.yaml schema — if
someone edits the metaschema and regenerates, failures here point at shape
drift."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from scont_bodies import (
    AxiomBody,
    EventBody,
    FlowBody,
    HumanInvolvement,
    MetricBody,
    PlaybookBody,
    RoleBody,
    Severity,
    StateMachineBody,
    ToolBody,
    TransitionBody,
)


class TestRoleBody:
    def test_minimal_valid(self):
        r = RoleBody.model_validate({"description": "x", "llm_prompt_hint": "y"})
        assert r.description == "x"
        assert r.is_boundary is None  # optional, defaults to None
        assert r.human_involvement is None

    def test_full_valid(self):
        r = RoleBody.model_validate(
            {
                "description": "External commercial",
                "llm_prompt_hint": "Signals enter here",
                "is_boundary": True,
                "human_involvement": "conditional",
                "can_be_played_by": "humans or agents",
            }
        )
        assert r.is_boundary is True
        assert r.human_involvement == HumanInvolvement.conditional.value

    def test_missing_description(self):
        with pytest.raises(ValidationError):
            RoleBody.model_validate({"llm_prompt_hint": "y"})

    def test_missing_hint(self):
        with pytest.raises(ValidationError):
            RoleBody.model_validate({"description": "x"})

    def test_invalid_human_involvement(self):
        with pytest.raises(ValidationError):
            RoleBody.model_validate(
                {"description": "x", "llm_prompt_hint": "y", "human_involvement": "bogus"}
            )

    def test_extra_field_forbidden(self):
        with pytest.raises(ValidationError):
            RoleBody.model_validate({"description": "x", "llm_prompt_hint": "y", "junk": 1})


class TestEventBody:
    def test_minimal_valid(self):
        e = EventBody.model_validate(
            {"description": "x", "observed_by": "some_role", "llm_prompt_hint": "y"}
        )
        assert e.observed_by == "some_role"

    def test_missing_observed_by(self):
        with pytest.raises(ValidationError):
            EventBody.model_validate({"description": "x", "llm_prompt_hint": "y"})


class TestFlowBody:
    def test_handoff_flow(self):
        f = FlowBody.model_validate(
            {
                "source_role": "a",
                "target_role": "b",
                "quantum": "X",
                "trigger_event": "e",
                "lifecycle_ref": "L",
            }
        )
        assert f.returns is None

    def test_query_flow_with_returns(self):
        f = FlowBody.model_validate(
            {"source_role": "a", "target_role": "b", "quantum": "Q", "returns": "R"}
        )
        assert f.returns == "R"

    def test_missing_quantum(self):
        with pytest.raises(ValidationError):
            FlowBody.model_validate({"source_role": "a", "target_role": "b"})

    def test_missing_source_role(self):
        with pytest.raises(ValidationError):
            FlowBody.model_validate({"target_role": "b", "quantum": "X"})

    def test_missing_target_role(self):
        with pytest.raises(ValidationError):
            FlowBody.model_validate({"source_role": "a", "quantum": "X"})


class TestAxiomBody:
    def test_minimal_valid(self):
        a = AxiomBody.model_validate({"name": "n", "scope": "flow", "nl": "text"})
        assert a.scope == "flow"

    def test_invalid_scope(self):
        with pytest.raises(ValidationError):
            AxiomBody.model_validate({"name": "n", "scope": "bogus", "nl": "text"})

    def test_invalid_severity(self):
        with pytest.raises(ValidationError):
            AxiomBody.model_validate(
                {"name": "n", "scope": "flow", "nl": "text", "severity": "critical"}
            )

    def test_missing_nl(self):
        with pytest.raises(ValidationError):
            AxiomBody.model_validate({"name": "n", "scope": "flow"})

    def test_with_references(self):
        a = AxiomBody.model_validate(
            {
                "name": "n",
                "scope": "flow",
                "nl": "text",
                "references": {"metrics": ["m1"], "classes": ["C1"]},
            }
        )
        assert a.references.metrics == ["m1"]
        assert a.references.classes == ["C1"]

    def test_severity_blocking(self):
        a = AxiomBody.model_validate(
            {"name": "n", "scope": "flow", "nl": "text", "severity": "blocking"}
        )
        assert a.severity == Severity.blocking.value

    def test_with_tool_ref(self):
        a = AxiomBody.model_validate(
            {
                "name": "line_capacity_not_exceeded",
                "scope": "flow",
                "expr": "sum_scheduled_units(...) <= cap",
                "tool_ref": "evaluate_line_capacity_not_exceeded",
                "nl": "Line capacity must not be exceeded.",
                "severity": "blocking",
            }
        )
        assert a.tool_ref == "evaluate_line_capacity_not_exceeded"
        assert a.expr  # expr remains as documentation alongside tool_ref

    def test_advisory_via_nl_only(self):
        # Neither tool_ref nor expr — axiom is evaluated by an LLM reading nl.
        a = AxiomBody.model_validate(
            {"name": "n", "scope": "flow", "nl": "text"}
        )
        assert a.tool_ref is None
        assert a.expr is None


class TestStateMachineBody:
    def test_minimal_valid_with_from_state(self):
        sm = StateMachineBody.model_validate(
            {
                "states": ["a", "b"],
                "transitions": [{"from_state": "a", "to_state": "b", "trigger": "t"}],
                "initial": "a",
                "terminal": ["b"],
            }
        )
        assert sm.transitions[0].from_state == "a"

    def test_transition_missing_from_state(self):
        with pytest.raises(ValidationError):
            StateMachineBody.model_validate(
                {"states": ["a", "b"], "transitions": [{"to_state": "b"}], "initial": "a"}
            )

    def test_missing_initial(self):
        with pytest.raises(ValidationError):
            StateMachineBody.model_validate({"states": ["a", "b"], "transitions": []})


class TestMetricBody:
    def test_minimal_valid(self):
        m = MetricBody.model_validate({"name": "m", "kind": "measure", "entity": "E"})
        assert m.kind == "measure"

    def test_invalid_kind(self):
        with pytest.raises(ValidationError):
            MetricBody.model_validate({"name": "m", "kind": "bogus", "entity": "E"})

    def test_invalid_source(self):
        with pytest.raises(ValidationError):
            MetricBody.model_validate(
                {"name": "m", "kind": "measure", "entity": "E", "source": "bogus"}
            )

    def test_full_valid(self):
        m = MetricBody.model_validate(
            {
                "name": "supplier_lead_time",
                "kind": "measure",
                "entity": "Supplier",
                "aggregation": "avg",
                "time_grain": "day",
                "unit": "days",
                "source": "local",
                "promotion_target": "dbt",
            }
        )
        assert m.promotion_target == "dbt"


class TestPlaybookBody:
    """Phase 1.8 — Playbook body shape. `llm_prompt_hint` is intentionally NOT
    a body field (carried as a sibling annotation, like FlowBody); a body that
    includes it must be rejected by extra=forbid."""

    def _minimal(self):
        return {
            "role": "supply_planning",
            "triggered_by": "capacity_conflict_detected",
            "input_quantum": "CapacityConflict",
        }

    def test_minimal_valid(self):
        p = PlaybookBody.model_validate(self._minimal())
        assert p.role == "supply_planning"
        assert p.context_assembly is None
        assert p.decision is None
        assert p.always_fires is None

    def test_full_valid(self):
        p = PlaybookBody.model_validate(
            {
                **self._minimal(),
                "context_assembly": [
                    {"flow": "check_otif_exposure", "required": True},
                    {"flow": "check_coman_availability"},
                ],
                "synchronization": "wait_all",
                "decision": {
                    "criteria_refs": ["tolerable_otif_penalty"],
                    "selects_one_of": ["shift_to_coman", "re_request_production"],
                },
                "always_fires": [
                    {"event": "capacity_resolved"},
                    {"flow": "plan_fulfillment"},
                ],
            }
        )
        assert p.synchronization == "wait_all"
        assert [s.flow for s in p.context_assembly] == [
            "check_otif_exposure", "check_coman_availability",
        ]
        # `required` defaults to None (the loader treats None as true).
        assert p.context_assembly[1].required is None
        assert p.decision.criteria_refs == ["tolerable_otif_penalty"]
        assert p.always_fires[0].event == "capacity_resolved"
        assert p.always_fires[1].flow == "plan_fulfillment"

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            PlaybookBody.model_validate({"role": "r", "triggered_by": "e"})

    def test_invalid_synchronization(self):
        with pytest.raises(ValidationError):
            PlaybookBody.model_validate({**self._minimal(), "synchronization": "wait_some"})

    def test_decision_requires_both_lists(self):
        with pytest.raises(ValidationError):
            PlaybookBody.model_validate(
                {**self._minimal(), "decision": {"criteria_refs": ["x"]}}
            )

    def test_llm_prompt_hint_in_body_rejected(self):
        """Hint is a sibling annotation, never a body field (FlowBody precedent)."""
        with pytest.raises(ValidationError):
            PlaybookBody.model_validate({**self._minimal(), "llm_prompt_hint": "x"})

    def test_inputs_from_quantum_and_closed_set(self):
        """Seed C — query steps bind inputs to the input quantum, and the
        assembly set can be marked closed (necessary-and-sufficient)."""
        p = PlaybookBody.model_validate(
            {
                **self._minimal(),
                "closed_set": True,
                "context_assembly": [
                    {
                        "flow": "check_coman_availability",
                        "inputs_from_quantum": [
                            {"param": "sku", "from_quantum": "competing_skus"},
                            {"param": "volume", "from_quantum": "shortfall_units"},
                        ],
                    },
                    {"flow": "check_promo_flexibility"},
                ],
            }
        )
        assert p.closed_set is True
        step = p.context_assembly[0]
        assert [(b.param, b.from_quantum) for b in step.inputs_from_quantum] == [
            ("sku", "competing_skus"),
            ("volume", "shortfall_units"),
        ]
        # closed_set defaults to None (loader treats as open/false).
        assert PlaybookBody.model_validate(self._minimal()).closed_set is None
        # a step without bindings stays agent-shaped.
        assert p.context_assembly[1].inputs_from_quantum is None

    def test_input_binding_requires_both_fields(self):
        with pytest.raises(ValidationError):
            PlaybookBody.model_validate(
                {
                    **self._minimal(),
                    "context_assembly": [
                        {"flow": "check_coman_availability",
                         "inputs_from_quantum": [{"param": "sku"}]},
                    ],
                }
            )


class TestToolBody:
    """Phase 1.8 — Tool body shape."""

    def _minimal(self):
        return {
            "description": "Reads lines for a SKU",
            "category": "reader",
            "input_class": "PlantQuery",
            "output_class": "PlantQueryResult",
            "implementation": "query_plants_for_sku",
            "available_to": ["supply_planning"],
        }

    def test_minimal_valid(self):
        t = ToolBody.model_validate(self._minimal())
        assert t.category == "reader"
        assert t.available_to == ["supply_planning"]
        assert t.deterministic is None

    def test_compute_category(self):
        t = ToolBody.model_validate({**self._minimal(), "category": "compute", "deterministic": True})
        assert t.category == "compute"
        assert t.deterministic is True

    def test_invalid_category(self):
        with pytest.raises(ValidationError):
            ToolBody.model_validate({**self._minimal(), "category": "writer"})

    def test_missing_available_to(self):
        body = self._minimal()
        del body["available_to"]
        with pytest.raises(ValidationError):
            ToolBody.model_validate(body)

    def test_llm_prompt_hint_in_body_rejected(self):
        with pytest.raises(ValidationError):
            ToolBody.model_validate({**self._minimal(), "llm_prompt_hint": "x"})
