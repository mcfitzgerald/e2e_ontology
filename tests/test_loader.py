"""Integration tests for the exploder's load_ontology — body parsing,
cross-reference resolution, FSM guard checks, and warnings."""
from __future__ import annotations

import pytest

from exploder import OntologyError, ValidationIssue, load_ontology


def _classes_block(name: str, extra: str = "") -> str:
    """Convenient shorthand: declare a minimal role + event + lifecycle pair
    so flows can reference them. `extra` is appended verbatim."""
    return f"""
classes:
  role_a:
    instantiates: [scont:Role]
    annotations:
      scont:domain: dom
      scont:role: >-
        {{"description": "A", "llm_prompt_hint": "a"}}
  role_b:
    instantiates: [scont:Role]
    annotations:
      scont:domain: dom
      scont:role: >-
        {{"description": "B", "llm_prompt_hint": "b"}}
  e1:
    instantiates: [scont:Event]
    annotations:
      scont:domain: dom
      scont:event: >-
        {{"description": "d", "observed_by": "role_a", "llm_prompt_hint": "h"}}
  Payload:
    description: "A payload entity"
    annotations:
      scont:domain: dom
{extra}
"""


class TestHappyPath:
    def test_loads_minimal_ontology(self, write_yaml, preamble):
        src = preamble + _classes_block("x") + """
  simple_flow:
    instantiates: [scont:InformationFlow]
    annotations:
      scont:domain: dom
      scont:flow: >-
        {"source_role": "role_a", "target_role": "role_b", "quantum": "Payload",
         "trigger_event": "e1"}
      scont:llm_prompt_hint: >-
        simple flow hint
"""
        path = write_yaml(src)
        ontology = load_ontology(path)
        assert len(ontology.roles) == 2
        assert len(ontology.events) == 1
        assert len(ontology.flows) == 1
        assert ontology.get_flow("simple_flow").body.source_role == "role_a"


class TestCrossReferenceErrors:
    def test_dangling_source_role(self, write_yaml, preamble):
        src = preamble + _classes_block("x") + """
  bad_flow:
    instantiates: [scont:InformationFlow]
    annotations:
      scont:domain: dom
      scont:flow: >-
        {"source_role": "ghost", "target_role": "role_b", "quantum": "Payload"}
      scont:llm_prompt_hint: "hint"
"""
        path = write_yaml(src)
        with pytest.raises(OntologyError) as exc:
            load_ontology(path)
        assert any(
            i.field == "source_role" and "ghost" in i.message
            for i in exc.value.issues
        )

    def test_dangling_target_role(self, write_yaml, preamble):
        src = preamble + _classes_block("x") + """
  bad_flow:
    instantiates: [scont:InformationFlow]
    annotations:
      scont:domain: dom
      scont:flow: >-
        {"source_role": "role_a", "target_role": "ghost", "quantum": "Payload"}
      scont:llm_prompt_hint: "hint"
"""
        path = write_yaml(src)
        with pytest.raises(OntologyError) as exc:
            load_ontology(path)
        assert any(i.field == "target_role" for i in exc.value.issues)

    def test_dangling_quantum(self, write_yaml, preamble):
        src = preamble + _classes_block("x") + """
  bad_flow:
    instantiates: [scont:InformationFlow]
    annotations:
      scont:domain: dom
      scont:flow: >-
        {"source_role": "role_a", "target_role": "role_b", "quantum": "Ghost"}
      scont:llm_prompt_hint: "hint"
"""
        path = write_yaml(src)
        with pytest.raises(OntologyError) as exc:
            load_ontology(path)
        assert any(i.field == "quantum" for i in exc.value.issues)

    def test_dangling_returns(self, write_yaml, preamble):
        src = preamble + _classes_block("x") + """
  bad_query:
    instantiates: [scont:InformationFlow]
    annotations:
      scont:domain: dom
      scont:flow: >-
        {"source_role": "role_a", "target_role": "role_b", "quantum": "Payload",
         "returns": "GhostResponse"}
      scont:llm_prompt_hint: "hint"
"""
        path = write_yaml(src)
        with pytest.raises(OntologyError) as exc:
            load_ontology(path)
        assert any(i.field == "returns" for i in exc.value.issues)

    def test_dangling_trigger_event(self, write_yaml, preamble):
        src = preamble + _classes_block("x") + """
  bad_flow:
    instantiates: [scont:InformationFlow]
    annotations:
      scont:domain: dom
      scont:flow: >-
        {"source_role": "role_a", "target_role": "role_b", "quantum": "Payload",
         "trigger_event": "ghost_event"}
      scont:llm_prompt_hint: "hint"
"""
        path = write_yaml(src)
        with pytest.raises(OntologyError) as exc:
            load_ontology(path)
        assert any(i.field == "trigger_event" for i in exc.value.issues)

    def test_dangling_on_failure_route(self, write_yaml, preamble):
        src = preamble + _classes_block("x") + """
  flow_with_axiom:
    instantiates: [scont:InformationFlow]
    annotations:
      scont:domain: dom
      scont:flow: >-
        {"source_role": "role_a", "target_role": "role_b", "quantum": "Payload"}
      scont:llm_prompt_hint: "hint"
      scont:axioms: >-
        [{"name": "ax", "scope": "flow", "nl": "text", "severity": "blocking",
          "on_failure_route_to": "ghost_flow"}]
"""
        path = write_yaml(src)
        with pytest.raises(OntologyError) as exc:
            load_ontology(path)
        assert any("ghost_flow" in i.message for i in exc.value.issues)

    def test_event_observed_by_unknown_role(self, write_yaml, preamble):
        src = preamble + """
classes:
  role_a:
    instantiates: [scont:Role]
    annotations:
      scont:domain: dom
      scont:role: >-
        {"description": "A", "llm_prompt_hint": "a"}
  bad_event:
    instantiates: [scont:Event]
    annotations:
      scont:domain: dom
      scont:event: >-
        {"description": "d", "observed_by": "ghost", "llm_prompt_hint": "h"}
"""
        path = write_yaml(src)
        with pytest.raises(OntologyError) as exc:
            load_ontology(path)
        assert any(i.field == "observed_by" for i in exc.value.issues)


class TestFSMValidation:
    def test_unknown_initial(self, write_yaml, preamble):
        src = preamble + _classes_block("x") + """
  bad_fsm:
    instantiates: [scont:StateMachine]
    annotations:
      scont:domain: dom
      scont:state_machine: >-
        {"states": ["a", "b"],
         "transitions": [{"from_state": "a", "to_state": "b"}],
         "initial": "ghost"}
"""
        path = write_yaml(src)
        with pytest.raises(OntologyError) as exc:
            load_ontology(path)
        assert any(i.field == "initial" for i in exc.value.issues)

    def test_transition_unknown_state(self, write_yaml, preamble):
        src = preamble + _classes_block("x") + """
  bad_fsm:
    instantiates: [scont:StateMachine]
    annotations:
      scont:domain: dom
      scont:state_machine: >-
        {"states": ["a"],
         "transitions": [{"from_state": "a", "to_state": "ghost"}],
         "initial": "a"}
"""
        path = write_yaml(src)
        with pytest.raises(OntologyError) as exc:
            load_ontology(path)
        assert any("ghost" in i.message for i in exc.value.issues)

    def test_guard_resolves_to_declared_axiom(self, write_yaml, preamble):
        """Guard named on an FSM transition must match a declared axiom."""
        src = preamble + _classes_block("x") + """
  my_fsm:
    instantiates: [scont:StateMachine]
    annotations:
      scont:domain: dom
      scont:state_machine: >-
        {"states": ["a", "b"],
         "transitions": [{"from_state": "a", "to_state": "b", "guard": "ax_one"}],
         "initial": "a",
         "terminal": ["b"]}
  my_flow:
    instantiates: [scont:InformationFlow]
    annotations:
      scont:domain: dom
      scont:flow: >-
        {"source_role": "role_a", "target_role": "role_b", "quantum": "Payload",
         "lifecycle_ref": "my_fsm"}
      scont:llm_prompt_hint: "hint"
      scont:axioms: >-
        [{"name": "ax_one", "scope": "flow", "nl": "text", "severity": "blocking"}]
"""
        path = write_yaml(src)
        ontology = load_ontology(path)
        assert "ax_one" in {a.name for a in ontology.get_flow("my_flow").axioms}

    def test_guard_without_axiom_fails(self, write_yaml, preamble):
        src = preamble + _classes_block("x") + """
  my_fsm:
    instantiates: [scont:StateMachine]
    annotations:
      scont:domain: dom
      scont:state_machine: >-
        {"states": ["a", "b"],
         "transitions": [{"from_state": "a", "to_state": "b", "guard": "nonexistent_axiom"}],
         "initial": "a",
         "terminal": ["b"]}
"""
        path = write_yaml(src)
        with pytest.raises(OntologyError) as exc:
            load_ontology(path)
        assert any("nonexistent_axiom" in i.message for i in exc.value.issues)


class TestBodyValidationErrors:
    def test_invalid_enum_in_role_body(self, write_yaml, preamble):
        src = preamble + """
classes:
  my_role:
    instantiates: [scont:Role]
    annotations:
      scont:domain: dom
      scont:role: >-
        {"description": "x", "llm_prompt_hint": "y", "human_involvement": "bogus"}
"""
        path = write_yaml(src)
        with pytest.raises(OntologyError) as exc:
            load_ontology(path)
        assert any("human_involvement" in (i.field or "") for i in exc.value.issues)

    def test_extra_field_in_flow_body(self, write_yaml, preamble):
        src = preamble + _classes_block("x") + """
  bad_flow:
    instantiates: [scont:InformationFlow]
    annotations:
      scont:domain: dom
      scont:flow: >-
        {"source_role": "role_a", "target_role": "role_b", "quantum": "Payload",
         "typo_field": "oops"}
      scont:llm_prompt_hint: "hint"
"""
        path = write_yaml(src)
        with pytest.raises(OntologyError) as exc:
            load_ontology(path)
        assert any("typo_field" in (i.field or "") for i in exc.value.issues)


class TestWarnings:
    def test_missing_domain_is_warning(self, write_yaml, preamble):
        src = preamble + """
classes:
  naked_role:
    instantiates: [scont:Role]
    annotations:
      scont:role: >-
        {"description": "x", "llm_prompt_hint": "y"}
"""
        path = write_yaml(src)
        ontology = load_ontology(path)  # no error
        assert any(w.field == "scont:domain" for w in ontology.warnings)

    def test_strict_warnings_raises(self, write_yaml, preamble):
        src = preamble + """
classes:
  naked_role:
    instantiates: [scont:Role]
    annotations:
      scont:role: >-
        {"description": "x", "llm_prompt_hint": "y"}
"""
        path = write_yaml(src)
        with pytest.raises(OntologyError):
            load_ontology(path, strict_warnings=True)

    def test_unused_role_warns(self, write_yaml, preamble):
        src = preamble + """
classes:
  used_role:
    instantiates: [scont:Role]
    annotations:
      scont:domain: dom
      scont:role: >-
        {"description": "x", "llm_prompt_hint": "y"}
  unused_role:
    instantiates: [scont:Role]
    annotations:
      scont:domain: dom
      scont:role: >-
        {"description": "z", "llm_prompt_hint": "w"}
  Payload:
    description: "A payload entity"
    annotations:
      scont:domain: dom
  dummy_event:
    instantiates: [scont:Event]
    annotations:
      scont:domain: dom
      scont:event: >-
        {"description": "d", "observed_by": "used_role", "llm_prompt_hint": "h"}
  solo_flow:
    instantiates: [scont:InformationFlow]
    annotations:
      scont:domain: dom
      scont:flow: >-
        {"source_role": "used_role", "target_role": "used_role", "quantum": "Payload"}
      scont:llm_prompt_hint: "hint"
"""
        path = write_yaml(src)
        ontology = load_ontology(path)
        unused_warnings = [w for w in ontology.warnings if w.element == "unused_role" and "not referenced" in w.message]
        assert unused_warnings


# ============================================================================
# Playbook + Tool cross-references (Phase 1.8)
# ============================================================================


def _pb_base(extra: str) -> str:
    """role_a/role_b/e1/Payload + a query flow carrying one advisory and one
    blocking axiom, plus a handoff resolution flow. `extra` appends a playbook
    or tool to exercise."""
    return _classes_block("x") + """
  qflow:
    instantiates: [scont:InformationFlow]
    annotations:
      scont:domain: dom
      scont:flow: >-
        {"source_role": "role_a", "target_role": "role_b", "quantum": "Payload",
         "returns": "Payload"}
      scont:axioms: >-
        [ {"name": "crit_adv", "scope": "flow", "nl": "advisory criterion", "severity": "advisory"},
          {"name": "crit_block", "scope": "flow", "nl": "blocking", "severity": "blocking"} ]
      scont:llm_prompt_hint: "query"
  res_flow:
    instantiates: [scont:InformationFlow]
    annotations:
      scont:domain: dom
      scont:flow: >-
        {"source_role": "role_a", "target_role": "role_b", "quantum": "Payload"}
      scont:llm_prompt_hint: "resolution"
""" + extra


class TestPlaybookCrossReferences:
    def test_valid_playbook_loads(self, write_yaml, preamble):
        src = preamble + _pb_base("""
  pb_ok:
    instantiates: [scont:Playbook]
    annotations:
      scont:domain: dom
      scont:playbook: >-
        {"role": "role_a", "triggered_by": "e1", "input_quantum": "Payload",
         "context_assembly": [{"flow": "qflow", "required": true}],
         "synchronization": "wait_all",
         "decision": {"criteria_refs": ["crit_adv"], "selects_one_of": ["res_flow"]},
         "always_fires": [{"flow": "res_flow"}]}
      scont:llm_prompt_hint: "ok"
""")
        ontology = load_ontology(write_yaml(src))
        assert "pb_ok" in ontology.playbooks
        assert ontology.playbooks_for_role("role_a")[0].name == "pb_ok"

    def test_criteria_must_be_advisory(self, write_yaml, preamble):
        src = preamble + _pb_base("""
  pb_bad:
    instantiates: [scont:Playbook]
    annotations:
      scont:domain: dom
      scont:playbook: >-
        {"role": "role_a", "triggered_by": "e1", "input_quantum": "Payload",
         "decision": {"criteria_refs": ["crit_block"], "selects_one_of": ["res_flow"]}}
      scont:llm_prompt_hint: "bad"
""")
        with pytest.raises(OntologyError) as exc:
            load_ontology(write_yaml(src))
        assert any("advisory" in i.message for i in exc.value.issues)

    def test_selects_one_of_must_be_flow(self, write_yaml, preamble):
        src = preamble + _pb_base("""
  pb_bad:
    instantiates: [scont:Playbook]
    annotations:
      scont:domain: dom
      scont:playbook: >-
        {"role": "role_a", "triggered_by": "e1", "input_quantum": "Payload",
         "decision": {"criteria_refs": ["crit_adv"], "selects_one_of": ["ghost_flow"]}}
      scont:llm_prompt_hint: "bad"
""")
        with pytest.raises(OntologyError) as exc:
            load_ontology(write_yaml(src))
        assert any("selects_one_of" in (i.field or "") for i in exc.value.issues)

    def test_context_assembly_must_be_query_flow(self, write_yaml, preamble):
        # res_flow has no `returns:`, so it can't be a context-assembly step.
        src = preamble + _pb_base("""
  pb_bad:
    instantiates: [scont:Playbook]
    annotations:
      scont:domain: dom
      scont:playbook: >-
        {"role": "role_a", "triggered_by": "e1", "input_quantum": "Payload",
         "context_assembly": [{"flow": "res_flow"}]}
      scont:llm_prompt_hint: "bad"
""")
        with pytest.raises(OntologyError) as exc:
            load_ontology(write_yaml(src))
        assert any("query flow" in i.message for i in exc.value.issues)

    def test_single_playbook_per_anchor_enforced(self, write_yaml, preamble):
        src = preamble + _pb_base("""
  pb_one:
    instantiates: [scont:Playbook]
    annotations:
      scont:domain: dom
      scont:playbook: >-
        {"role": "role_a", "triggered_by": "e1", "input_quantum": "Payload"}
      scont:llm_prompt_hint: "one"
  pb_two:
    instantiates: [scont:Playbook]
    annotations:
      scont:domain: dom
      scont:playbook: >-
        {"role": "role_a", "triggered_by": "e1", "input_quantum": "Payload"}
      scont:llm_prompt_hint: "two"
""")
        with pytest.raises(OntologyError) as exc:
            load_ontology(write_yaml(src))
        assert any("duplicate playbook anchor" in i.message for i in exc.value.issues)


class TestToolCrossReferences:
    def test_valid_tool_loads(self, write_yaml, preamble):
        src = preamble + _pb_base("""
  tool_ok:
    instantiates: [scont:Tool]
    annotations:
      scont:domain: dom
      scont:tool: >-
        {"description": "d", "category": "reader", "input_class": "Payload",
         "output_class": "Payload", "implementation": "do_it",
         "available_to": ["role_a"]}
      scont:llm_prompt_hint: "ok"
""")
        ontology = load_ontology(write_yaml(src))
        assert "tool_ok" in ontology.tools
        assert ontology.tools_for_role("role_a")[0].name == "tool_ok"

    def test_unknown_input_class(self, write_yaml, preamble):
        src = preamble + _pb_base("""
  tool_bad:
    instantiates: [scont:Tool]
    annotations:
      scont:domain: dom
      scont:tool: >-
        {"description": "d", "category": "reader", "input_class": "Ghost",
         "output_class": "Payload", "implementation": "do_it",
         "available_to": ["role_a"]}
      scont:llm_prompt_hint: "bad"
""")
        with pytest.raises(OntologyError) as exc:
            load_ontology(write_yaml(src))
        assert any(i.field == "input_class" for i in exc.value.issues)

    def test_unknown_available_to_role(self, write_yaml, preamble):
        src = preamble + _pb_base("""
  tool_bad:
    instantiates: [scont:Tool]
    annotations:
      scont:domain: dom
      scont:tool: >-
        {"description": "d", "category": "reader", "input_class": "Payload",
         "output_class": "Payload", "implementation": "do_it",
         "available_to": ["ghost_role"]}
      scont:llm_prompt_hint: "bad"
""")
        with pytest.raises(OntologyError) as exc:
            load_ontology(write_yaml(src))
        assert any("available_to" in (i.field or "") for i in exc.value.issues)

    def test_implementation_need_not_resolve(self, write_yaml, preamble):
        """`implementation` is a contract name bound at boot — it must NOT be
        required to resolve to anything in the ontology."""
        src = preamble + _pb_base("""
  tool_ok:
    instantiates: [scont:Tool]
    annotations:
      scont:domain: dom
      scont:tool: >-
        {"description": "d", "category": "compute", "input_class": "Payload",
         "output_class": "Payload", "implementation": "nonexistent.callable.v1",
         "available_to": ["role_a"]}
      scont:llm_prompt_hint: "ok"
""")
        ontology = load_ontology(write_yaml(src))  # no error
        assert ontology.get_tool("tool_ok").body.implementation == "nonexistent.callable.v1"
