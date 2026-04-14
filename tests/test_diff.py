"""Tests for the structural diff: compute_delta + renderers."""
from __future__ import annotations

import json

import pytest

from exploder import (
    DIFF_KINDS,
    TypedDelta,
    compute_delta,
    load_ontology,
    render_delta_human,
    render_delta_json,
)


# A minimal-but-loadable ontology skeleton. Variants below layer on / swap
# out elements to exercise each diff code path.
BASE = """
id: https://test.example/diff
name: diff_test
prefixes:
  linkml: https://w3id.org/linkml/
  scont:  https://e2e-ontology.dev/
default_prefix: scont
imports:
  - linkml:types

classes:
  Payload:
    description: "Base payload entity"
    annotations:
      scont:domain: dom
    attributes:
      sku:
        range: string
        required: true

  role_a:
    instantiates: [scont:Role]
    annotations:
      scont:domain: dom
      scont:role: >-
        {"description": "A", "llm_prompt_hint": "a"}
  role_b:
    instantiates: [scont:Role]
    annotations:
      scont:domain: dom
      scont:role: >-
        {"description": "B", "llm_prompt_hint": "b"}

  event_one:
    instantiates: [scont:Event]
    annotations:
      scont:domain: dom
      scont:event: >-
        {"description": "e", "observed_by": "role_a", "llm_prompt_hint": "h"}

  flow_one:
    instantiates: [scont:InformationFlow]
    annotations:
      scont:domain: dom
      scont:flow: >-
        {"source_role": "role_a", "target_role": "role_b",
         "quantum": "Payload", "trigger_event": "event_one"}
      scont:llm_prompt_hint: "base hint"

enums:
  Color:
    permissible_values:
      red:
      blue:
"""


@pytest.fixture
def base_ontology(write_yaml):
    return load_ontology(write_yaml(BASE, name="base.yaml"))


class TestIdentity:
    def test_same_ontology_empty_delta(self, base_ontology, write_yaml):
        other = load_ontology(write_yaml(BASE, name="other.yaml"))
        assert compute_delta(base_ontology, other) == []

    def test_renders_no_differences(self):
        assert render_delta_human([]).startswith("(no differences)")
        assert render_delta_json([]) == "[]"


def _insert_class(yaml_text: str, class_block: str) -> str:
    """Insert `class_block` into the classes: section, before the enums: block."""
    marker = "\nenums:"
    idx = yaml_text.index(marker)
    return yaml_text[:idx] + class_block + yaml_text[idx:]


class TestAdditions:
    def test_role_added(self, base_ontology, write_yaml):
        modified = _insert_class(BASE, """
  role_c:
    instantiates: [scont:Role]
    annotations:
      scont:domain: dom
      scont:role: >-
        {"description": "C", "llm_prompt_hint": "c"}
""")
        new = load_ontology(write_yaml(modified, name="mod.yaml"))
        deltas = compute_delta(base_ontology, new)
        by_kind = {d.kind: d for d in deltas}
        assert "roles" in by_kind
        assert by_kind["roles"].added == ("role_c",)
        assert by_kind["roles"].removed == ()
        assert by_kind["roles"].changed == ()

    def test_flow_added(self, base_ontology, write_yaml):
        modified = _insert_class(BASE, """
  flow_two:
    instantiates: [scont:InformationFlow]
    annotations:
      scont:domain: dom
      scont:flow: >-
        {"source_role": "role_b", "target_role": "role_a",
         "quantum": "Payload"}
      scont:llm_prompt_hint: "hint"
""")
        new = load_ontology(write_yaml(modified, name="mod.yaml"))
        deltas = compute_delta(base_ontology, new)
        by_kind = {d.kind: d for d in deltas}
        assert by_kind["flows"].added == ("flow_two",)

    def test_enum_value_added(self, base_ontology, write_yaml):
        modified = BASE.replace("      blue:\n", "      blue:\n      green:\n")
        new = load_ontology(write_yaml(modified, name="mod.yaml"))
        deltas = compute_delta(base_ontology, new)
        by_kind = {d.kind: d for d in deltas}
        # Enum gains a permissible value → surfaced as a 'changed' on the enum
        assert "enums" in by_kind
        assert any(c.name == "Color" for c in by_kind["enums"].changed)


class TestRemovals:
    def test_role_removed(self, base_ontology, write_yaml):
        # Drop role_b AND drop the flow that references it; otherwise the
        # removed YAML fails to load (cross-ref error).
        lines = BASE.splitlines(keepends=True)
        start_b = next(i for i, l in enumerate(lines) if l.startswith("  role_b:"))
        # role_b occupies 6 lines
        del lines[start_b:start_b + 6]
        # Also drop flow_one (8 lines).
        modified = "".join(lines)
        start_f = modified.index("\n  flow_one:")
        modified = modified[:start_f]
        new = load_ontology(write_yaml(modified, name="mod.yaml"))
        deltas = compute_delta(base_ontology, new)
        by_kind = {d.kind: d for d in deltas}
        assert "role_b" in by_kind["roles"].removed
        assert by_kind["flows"].removed == ("flow_one",)


class TestChanges:
    def test_role_body_field_changed(self, base_ontology, write_yaml):
        modified = BASE.replace(
            '{"description": "A", "llm_prompt_hint": "a"}',
            '{"description": "A-modified", "llm_prompt_hint": "a"}',
        )
        new = load_ontology(write_yaml(modified, name="mod.yaml"))
        deltas = compute_delta(base_ontology, new)
        by_kind = {d.kind: d for d in deltas}
        assert "roles" in by_kind
        change = next(c for c in by_kind["roles"].changed if c.name == "role_a")
        field_paths = [p for p, _, _ in change.changes]
        assert "body.description" in field_paths

    def test_flow_source_role_changed(self, base_ontology, write_yaml):
        modified = BASE.replace(
            '"source_role": "role_a", "target_role": "role_b"',
            '"source_role": "role_b", "target_role": "role_a"',
        )
        new = load_ontology(write_yaml(modified, name="mod.yaml"))
        deltas = compute_delta(base_ontology, new)
        flow_delta = next(d for d in deltas if d.kind == "flows")
        change = next(c for c in flow_delta.changed if c.name == "flow_one")
        paths = {p for p, _, _ in change.changes}
        assert "body.source_role" in paths
        assert "body.target_role" in paths
        src_change = next(c for c in change.changes if c[0] == "body.source_role")
        assert src_change == ("body.source_role", "role_a", "role_b")

    def test_flow_hint_changed(self, base_ontology, write_yaml):
        modified = BASE.replace('"base hint"', '"updated hint"')
        new = load_ontology(write_yaml(modified, name="mod.yaml"))
        deltas = compute_delta(base_ontology, new)
        flow_delta = next(d for d in deltas if d.kind == "flows")
        change = next(c for c in flow_delta.changed if c.name == "flow_one")
        paths = {p for p, _, _ in change.changes}
        assert "llm_prompt_hint" in paths


class TestOnlyFilter:
    def test_only_roles_excludes_flow_changes(self, base_ontology, write_yaml):
        modified = BASE.replace(
            '"source_role": "role_a", "target_role": "role_b"',
            '"source_role": "role_b", "target_role": "role_a"',
        ).replace(
            '{"description": "A", "llm_prompt_hint": "a"}',
            '{"description": "A-modified", "llm_prompt_hint": "a"}',
        )
        new = load_ontology(write_yaml(modified, name="mod.yaml"))
        deltas = compute_delta(base_ontology, new, kinds={"roles"})
        assert {d.kind for d in deltas} == {"roles"}

    def test_only_flows_excludes_role_changes(self, base_ontology, write_yaml):
        modified = BASE.replace(
            '{"description": "A", "llm_prompt_hint": "a"}',
            '{"description": "A-modified", "llm_prompt_hint": "a"}',
        )
        new = load_ontology(write_yaml(modified, name="mod.yaml"))
        deltas = compute_delta(base_ontology, new, kinds={"flows"})
        assert deltas == []


class TestRendering:
    def test_human_renders_added_changed_removed(self):
        deltas = [
            TypedDelta(
                kind="roles",
                added=("role_x",),
                removed=("role_y",),
                changed=(),
            )
        ]
        out = render_delta_human(deltas, use_color=False)
        assert "+ role_x" in out
        assert "- role_y" in out
        assert "roles" in out

    def test_human_color_emits_ansi(self):
        deltas = [TypedDelta(kind="roles", added=("r",))]
        colored = render_delta_human(deltas, use_color=True)
        plain = render_delta_human(deltas, use_color=False)
        assert "\033[" in colored
        assert "\033[" not in plain

    def test_json_is_parseable_and_structured(self, base_ontology, write_yaml):
        modified = BASE.replace(
            '{"description": "A", "llm_prompt_hint": "a"}',
            '{"description": "A-modified", "llm_prompt_hint": "a"}',
        )
        new = load_ontology(write_yaml(modified, name="mod.yaml"))
        deltas = compute_delta(base_ontology, new)
        payload = json.loads(render_delta_json(deltas))
        assert isinstance(payload, list)
        roles_entry = next(p for p in payload if p["kind"] == "roles")
        assert any(c["name"] == "role_a" for c in roles_entry["changed"])

    def test_none_value_renders_as_null_sentinel(self):
        deltas = [
            TypedDelta(
                kind="flows",
                changed=(
                    # Using a dummy inline change tuple
                    # via direct construction — the helper exercises _fmt_value
                    # for None on the 'before' side.
                    __import__("exploder").ElementChange(
                        name="f", changes=(("body.returns", None, "Shape"),)
                    ),
                ),
            )
        ]
        out = render_delta_human(deltas, use_color=False)
        assert "∅" in out


class TestDiffKindsConstant:
    def test_contains_expected_kinds(self):
        assert set(DIFF_KINDS) == {
            "entities", "roles", "events", "state_machines", "flows", "enums", "warnings",
        }
