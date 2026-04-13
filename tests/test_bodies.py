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
    RoleBody,
    Severity,
    StateMachineBody,
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
