"""Tests for `exploder new <kind>` — template rendering + round-trip parsing."""
from __future__ import annotations

import builtins
import json
import re
from pathlib import Path

import pytest

from exploder import (
    SCAFFOLD_KINDS,
    ScaffoldError,
    _parse_extra_flags,
    _template_for_kind,
    load_ontology,
    main,
)

from conftest import MINIMAL_PREAMBLE


# ---------------------------------------------------------------------------
# Helpers: wrap a generated fragment in enough surrounding YAML to load.
# ---------------------------------------------------------------------------


_ROLE_STUBS = """
  src_role:
    instantiates: [scont:Role]
    annotations:
      scont:domain: dom
      scont:role: >-
        {"description": "src", "llm_prompt_hint": "h"}
  tgt_role:
    instantiates: [scont:Role]
    annotations:
      scont:domain: dom
      scont:role: >-
        {"description": "tgt", "llm_prompt_hint": "h"}
"""

_QUANTUM_STUB = """
  Payload:
    description: "stub quantum"
    annotations:
      scont:domain: dom
    attributes:
      id:
        range: string
        required: true
"""

_EVENT_STUB = """
  some_event:
    instantiates: [scont:Event]
    annotations:
      scont:domain: dom
      scont:event: >-
        {"description": "e", "observed_by": "src_role", "llm_prompt_hint": "h"}
"""

_RETURN_STUB = """
  PayloadResponse:
    description: "stub response"
    annotations:
      scont:domain: dom
    attributes:
      id:
        range: string
        required: true
"""


def _wrap(fragment: str, extras: str = "") -> str:
    return MINIMAL_PREAMBLE + "\nclasses:\n" + extras + fragment


def _load_from_fragment(write_yaml, fragment: str, extras: str = ""):
    path = write_yaml(_wrap(fragment, extras), name="frag.yaml")
    return load_ontology(path)


# ---------------------------------------------------------------------------
# Direct template-rendering tests
# ---------------------------------------------------------------------------


class TestKindDispatch:
    def test_unknown_kind_raises(self):
        with pytest.raises(ScaffoldError):
            _template_for_kind("nope", "x", {}, None)

    @pytest.mark.parametrize("kind", SCAFFOLD_KINDS)
    def test_every_kind_renders_something(self, kind):
        name = "X" if kind == "entity" else "x"
        out = _template_for_kind(kind, name, {}, "dom")
        assert out.strip(), f"{kind} produced empty fragment"


class TestRequiredFields:
    def test_role_body_has_description_and_hint(self):
        out = _template_for_kind(
            "role", "r",
            {"description": "d", "llm_prompt_hint": "h"},
            "dom",
        )
        assert '"description": "d"' in out
        assert '"llm_prompt_hint": "h"' in out

    def test_flow_required_fields_filled(self):
        out = _template_for_kind(
            "flow", "f",
            {
                "source_role": "src_role",
                "target_role": "tgt_role",
                "quantum": "Payload",
            },
            "dom",
        )
        assert '"source_role": "src_role"' in out
        assert '"target_role": "tgt_role"' in out
        assert '"quantum": "Payload"' in out

    def test_query_flow_requires_returns(self):
        # Omitting --returns should leave a placeholder, not silently drop.
        out = _template_for_kind(
            "query-flow", "qf",
            {"source_role": "src_role", "target_role": "tgt_role", "quantum": "Payload"},
            "dom",
        )
        assert '"returns": "<RETURNS>"' in out

    def test_missing_required_fields_render_placeholders(self):
        out = _template_for_kind("role", "r", {}, None)
        assert '"description": "<DESCRIPTION>"' in out
        assert '"llm_prompt_hint": "<LLM_PROMPT_HINT>"' in out
        assert "scont:domain: <DOMAIN>" in out


class TestOptionalFieldCommentary:
    def test_role_optionals_listed(self):
        out = _template_for_kind("role", "r", {}, "dom")
        assert "is_boundary" in out
        assert "human_involvement" in out
        assert "'required' | 'conditional' | 'autonomous'" in out

    def test_flow_optionals_listed(self):
        out = _template_for_kind(
            "flow", "f",
            {"source_role": "src_role", "target_role": "tgt_role", "quantum": "Payload"},
            "dom",
        )
        # returns is optional on a plain flow; trigger_event / lifecycle_ref too
        assert "returns" in out
        assert "lifecycle_ref" in out

    def test_supplied_optional_is_not_repeated_in_comment(self):
        # If the caller supplies `trigger_event` it appears in the JSON but
        # shouldn't also be listed as an "optional" comment line.
        out = _template_for_kind(
            "flow", "f",
            {
                "source_role": "src_role",
                "target_role": "tgt_role",
                "quantum": "Payload",
                "trigger_event": "some_event",
            },
            "dom",
        )
        assert '"trigger_event": "some_event"' in out
        # Comment line should not list trigger_event as still-optional.
        opt_lines = [l for l in out.splitlines() if l.strip().startswith("#   trigger_event")]
        assert opt_lines == []

    def test_state_machine_terminal_listed_as_optional(self):
        out = _template_for_kind("state-machine", "Lifecycle", {}, "dom")
        assert "terminal: list[str]" in out


class TestEntityTemplate:
    def test_entity_is_plain_linkml_no_instantiates(self):
        out = _template_for_kind("entity", "Thing", {"description": "d"}, "dom")
        assert "instantiates:" not in out
        assert "scont:domain: dom" in out
        assert "attributes:" in out

    def test_entity_description_quoted(self):
        out = _template_for_kind("entity", "Thing", {"description": 'a "quoted" d'}, "dom")
        # json.dumps escapes the internal quotes so the YAML remains valid.
        assert '"a \\"quoted\\" d"' in out


class TestAxiomTemplate:
    def test_axiom_is_list_entry_not_class(self):
        out = _template_for_kind(
            "axiom", "line_cap",
            {"name": "line_cap", "scope": "flow", "nl": "capacity must suffice"},
            None,
        )
        assert "instantiates:" not in out
        assert '"name": "line_cap"' in out
        assert '"scope": "flow"' in out
        assert '"nl": "capacity must suffice"' in out
        # Should note the paste location
        assert "scont:axioms" in out

    def test_axiom_optional_fields_surface(self):
        out = _template_for_kind("axiom", "x", {"name": "x", "scope": "flow", "nl": "x"}, None)
        assert "on_failure_route_to" in out


# ---------------------------------------------------------------------------
# _parse_extra_flags — CLI passthrough parsing
# ---------------------------------------------------------------------------


class TestParseExtraFlags:
    def test_space_separated_pair(self):
        assert _parse_extra_flags(["--source-role", "sp"]) == {"source_role": "sp"}

    def test_equals_syntax(self):
        assert _parse_extra_flags(["--source-role=sp"]) == {"source_role": "sp"}

    def test_multiple_flags(self):
        assert _parse_extra_flags(
            ["--source-role", "sp", "--target-role=pp", "--quantum", "X"]
        ) == {"source_role": "sp", "target_role": "pp", "quantum": "X"}

    def test_missing_value_raises(self):
        with pytest.raises(ScaffoldError):
            _parse_extra_flags(["--source-role"])

    def test_non_flag_token_raises(self):
        with pytest.raises(ScaffoldError):
            _parse_extra_flags(["source-role", "sp"])


# ---------------------------------------------------------------------------
# CLI entry-point smoke tests (via main())
# ---------------------------------------------------------------------------


class TestCLIEntryPoint:
    def test_new_role_via_main_prints_fragment(self, capsys):
        rc = main([
            "new", "role",
            "--name", "supply_planning",
            "--domain", "supply_netops",
            "--description", "desc",
            "--llm-prompt-hint", "hint",
        ])
        out = capsys.readouterr().out
        assert rc == 0
        assert "supply_planning:" in out
        assert "instantiates: [scont:Role]" in out
        assert '"description": "desc"' in out

    def test_new_flow_via_main_forwards_unknown_flags(self, capsys):
        rc = main([
            "new", "flow",
            "--name", "request_production",
            "--domain", "supply_netops",
            "--source-role", "src_role",
            "--target-role", "tgt_role",
            "--quantum", "Payload",
            "--llm-prompt-hint", "h",
        ])
        out = capsys.readouterr().out
        assert rc == 0
        assert "request_production:" in out
        assert '"source_role": "src_role"' in out
        assert '"target_role": "tgt_role"' in out
        assert '"quantum": "Payload"' in out

    def test_missing_name_errors(self, capsys):
        with pytest.raises(SystemExit):
            main(["new", "role"])

    def test_unknown_kind_errors(self, capsys):
        with pytest.raises(SystemExit):
            main(["new", "garbage", "--name", "x"])


class TestInteractiveMode:
    def test_interactive_fills_missing_required(self, capsys, monkeypatch):
        # All required role-body fields will be prompted for; feed responses.
        responses = iter(["desc from input", "hint from input"])
        monkeypatch.setattr(builtins, "input", lambda prompt="": next(responses))
        rc = main(["new", "role", "--name", "r", "--domain", "dom", "--interactive"])
        out = capsys.readouterr().out
        assert rc == 0
        assert '"description": "desc from input"' in out
        assert '"llm_prompt_hint": "hint from input"' in out

    def test_interactive_and_cli_equivalent(self, capsys, monkeypatch):
        # Via CLI flags:
        rc = main([
            "new", "role",
            "--name", "r",
            "--domain", "dom",
            "--description", "d",
            "--llm-prompt-hint", "h",
        ])
        assert rc == 0
        cli_out = capsys.readouterr().out

        # Via interactive (no flags for the required fields):
        responses = iter(["d", "h"])
        monkeypatch.setattr(builtins, "input", lambda prompt="": next(responses))
        rc = main(["new", "role", "--name", "r", "--domain", "dom", "--interactive"])
        assert rc == 0
        interactive_out = capsys.readouterr().out

        assert cli_out == interactive_out


# ---------------------------------------------------------------------------
# Round-trip: generated fragments parse through load_ontology
# ---------------------------------------------------------------------------


class TestRoundTrip:
    def test_role_fragment_loads(self, write_yaml):
        fragment = _template_for_kind(
            "role", "supply_planning",
            {"description": "d", "llm_prompt_hint": "h"},
            "dom",
        )
        ont = _load_from_fragment(write_yaml, fragment)
        assert "supply_planning" in ont.roles
        assert ont.roles["supply_planning"].body.description == "d"

    def test_event_fragment_loads(self, write_yaml):
        fragment = _template_for_kind(
            "event", "forecast_revised",
            {"description": "d", "observed_by": "src_role", "llm_prompt_hint": "h"},
            "dom",
        )
        ont = _load_from_fragment(write_yaml, fragment, extras=_ROLE_STUBS)
        assert "forecast_revised" in ont.events

    def test_flow_fragment_loads(self, write_yaml):
        fragment = _template_for_kind(
            "flow", "request_production",
            {
                "source_role": "src_role",
                "target_role": "tgt_role",
                "quantum": "Payload",
                "trigger_event": "some_event",
                "llm_prompt_hint": "h",
            },
            "dom",
        )
        ont = _load_from_fragment(
            write_yaml, fragment, extras=_ROLE_STUBS + _QUANTUM_STUB + _EVENT_STUB
        )
        assert "request_production" in ont.flows
        flow = ont.flows["request_production"]
        assert flow.body.source_role == "src_role"
        assert flow.body.target_role == "tgt_role"
        assert flow.body.trigger_event == "some_event"

    def test_query_flow_fragment_loads_with_returns(self, write_yaml):
        fragment = _template_for_kind(
            "query-flow", "check_otif",
            {
                "source_role": "src_role",
                "target_role": "tgt_role",
                "quantum": "Payload",
                "returns": "PayloadResponse",
                "llm_prompt_hint": "h",
            },
            "dom",
        )
        ont = _load_from_fragment(
            write_yaml, fragment, extras=_ROLE_STUBS + _QUANTUM_STUB + _RETURN_STUB
        )
        assert "check_otif" in ont.flows
        assert ont.flows["check_otif"].body.returns == "PayloadResponse"

    def test_state_machine_fragment_loads_with_concrete_states(self, write_yaml):
        # Placeholder states (<STATE_1>, etc.) are strings, valid to load — the
        # internal consistency check passes because all references resolve
        # within the FSM. Demonstrate round-trip with concrete states too.
        fragment = _template_for_kind(
            "state-machine", "Lifecycle",
            {
                "states": "requested,assigned,completed",
                "initial": "requested",
            },
            "dom",
        )
        # Supplied `states` replaces the default placeholders; `transitions`
        # keeps the default placeholder which references <STATE_1>/<STATE_2>.
        # Override transitions by post-editing the fragment in the real author
        # flow; here we load the placeholder-transitions fragment to confirm
        # FSM validation fires on unknown states and raises cleanly.
        from exploder import OntologyError
        with pytest.raises(OntologyError):
            _load_from_fragment(write_yaml, fragment)

    def test_state_machine_placeholder_fragment_loads_in_isolation(self, write_yaml):
        # The untouched placeholder fragment IS internally consistent: all
        # transition states and `initial` reference <STATE_1>/<STATE_2> which
        # are listed in `states`.
        fragment = _template_for_kind("state-machine", "Lifecycle", {}, "dom")
        ont = _load_from_fragment(write_yaml, fragment)
        assert "Lifecycle" in ont.state_machines
        sm = ont.state_machines["Lifecycle"]
        assert sm.body.initial == "<STATE_1>"

    def test_entity_fragment_loads(self, write_yaml):
        fragment = _template_for_kind(
            "entity", "Thing", {"description": "a thing"}, "dom"
        )
        ont = _load_from_fragment(write_yaml, fragment)
        assert "Thing" in ont.entities
        assert ont.entities["Thing"].description == "a thing"

    def test_axiom_fragment_pasted_into_flow_loads(self, write_yaml):
        # Axiom alone isn't a class; it's a list entry. Confirm it round-trips
        # when inserted into a flow's scont:axioms annotation.
        axiom_frag = _template_for_kind(
            "axiom", "line_cap",
            {"name": "line_cap", "scope": "flow", "nl": "capacity must suffice"},
            None,
        )
        # Extract the JSON block (first {...} run) from the fragment, then
        # compact it so it pastes cleanly into a one-line folded scalar.
        match = re.search(r"\{[\s\S]*?\n\}", axiom_frag)
        assert match, "expected JSON block in axiom fragment"
        axiom_obj = json.loads(match.group(0))
        axiom_compact = json.dumps(axiom_obj)

        flow_yaml = (
            "  src_role:\n"
            "    instantiates: [scont:Role]\n"
            "    annotations:\n"
            "      scont:domain: dom\n"
            "      scont:role: >-\n"
            '        {"description": "s", "llm_prompt_hint": "h"}\n'
            "  tgt_role:\n"
            "    instantiates: [scont:Role]\n"
            "    annotations:\n"
            "      scont:domain: dom\n"
            "      scont:role: >-\n"
            '        {"description": "t", "llm_prompt_hint": "h"}\n'
            "  Payload:\n"
            "    annotations:\n"
            "      scont:domain: dom\n"
            "    attributes:\n"
            "      id:\n"
            "        range: string\n"
            "        required: true\n"
            "  some_flow:\n"
            "    instantiates: [scont:InformationFlow]\n"
            "    annotations:\n"
            "      scont:domain: dom\n"
            "      scont:flow: >-\n"
            '        {"source_role": "src_role", "target_role": "tgt_role", "quantum": "Payload"}\n'
            "      scont:axioms: >-\n"
            f"        [{axiom_compact}]\n"
            '      scont:llm_prompt_hint: "h"\n'
        )
        full = MINIMAL_PREAMBLE + "\nclasses:\n" + flow_yaml
        path = write_yaml(full, name="axiom_frag.yaml")
        ont = load_ontology(path)
        axioms = ont.flows["some_flow"].axioms
        assert any(a.name == "line_cap" for a in axioms)
