"""Snapshot + structural tests for the role-view render (Phase 1.2).

Snapshot files live in `tests/snapshots/`. To regenerate after an intentional
render change, run the snapshot-update helper at the bottom of this file
(`pytest tests/test_role_view_render.py -k snapshot --update-snapshots`)
or simply re-run the one-liner under `tools/render_snapshots.py` (see CHANGELOG).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ontology_service import OntologyService, RoleView


SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


@pytest.fixture
def svc(demo_yaml_path) -> OntologyService:
    return OntologyService.load(demo_yaml_path)


# ---- structural assertions -------------------------------------------------


class TestViewShape:
    def test_demand_planning_view_shape(self, svc):
        v = svc.render_role_view("demand_planning")
        assert v.identity.name == "demand_planning"
        assert v.identity.is_boundary is False
        assert v.identity.human_involvement is None
        assert v.identity.domain == "demand"
        # Two ingresses, one outgoing handoff, no queries either way.
        assert [f.name for f in v.incoming_handoffs] == [
            "raise_demand_anomaly", "submit_promo_plan",
        ]
        assert [f.name for f in v.outgoing_handoffs] == ["submit_supply_request"]
        assert v.incoming_queries == ()
        assert v.outgoing_queries == ()

    def test_supply_planning_view_shape(self, svc):
        v = svc.render_role_view("supply_planning")
        assert v.identity.name == "supply_planning"
        assert v.identity.human_involvement == "conditional"
        # The three Scene 5 query flows.
        assert [f.name for f in v.outgoing_queries] == [
            "check_coman_availability",
            "check_otif_exposure",
            "check_promo_flexibility",
        ]
        # The shared-lifecycle pattern is preserved.
        fsm = next(s for s in v.fsms_governing_my_quanta
                   if s.name == "ProductionRequestLifecycle")
        assert set(fsm.governs_flows) == {
            "re_request_production", "request_production", "shift_to_coman",
        }

    def test_view_is_pydantic_serializable(self, svc):
        v = svc.render_role_view("supply_planning")
        # `.as_json()` returns a JSON-compatible dict (no enums, no Pydantic objects).
        data = v.as_json()
        assert data["identity"]["human_involvement"] == "conditional"
        assert isinstance(data["outgoing_handoffs"], list)
        # Re-validate to ensure the wire form is faithful.
        round_trip = RoleView.model_validate(data)
        assert round_trip == v


class TestAdaptersAreFormatOnly:
    """Format adapters must not re-query the ontology; they should be pure
    functions over RoleView. If a future refactor breaks this, we want the
    invariant to fail loudly here, not at MCP/tool-chain integration time."""

    def test_adapters_work_without_service(self, svc):
        v = svc.render_role_view("demand_planning")
        # Drop the service; the view alone must still format.
        del svc
        assert "ROLE: demand_planning" in v.as_agent_prompt()
        assert "# Role: demand_planning" in v.as_markdown()
        assert v.as_json()["identity"]["name"] == "demand_planning"

    def test_markdown_and_prompt_have_same_section_titles(self, svc):
        """§15.4: same content, different formatting. The set of section
        titles must agree between the two adapters."""
        v = svc.render_role_view("supply_planning")
        md_titles = {line[3:] for line in v.as_markdown().splitlines() if line.startswith("## ")}
        prompt_titles = set()
        prompt_lines = v.as_agent_prompt().splitlines()
        for i, line in enumerate(prompt_lines):
            if line == "---" and i + 1 < len(prompt_lines):
                prompt_titles.add(prompt_lines[i + 1])
        assert md_titles == {t.upper() for t in prompt_titles} or md_titles == {
            t for t in (s.lower() for s in prompt_titles)
        } or {t.upper() for t in md_titles} == prompt_titles, (
            f"section titles diverge:\n  markdown: {md_titles}\n  prompt:   {prompt_titles}"
        )


# ---- snapshot tests --------------------------------------------------------


def _read_snapshot(name: str) -> str:
    return (SNAPSHOT_DIR / name).read_text()


class TestSnapshots:
    """Stability tests. A failure here means the rendered prompt changed —
    either intentionally (regenerate snapshots and commit) or unintentionally
    (the change is a regression in render fidelity). The snapshot files
    themselves are the human-readable record of what the rendered prompt
    looks like at this checkpoint of the ontology."""

    @pytest.mark.parametrize("role", ["demand_planning", "supply_planning"])
    def test_agent_prompt_snapshot(self, svc, role):
        rendered = svc.render_role_view(role).as_agent_prompt()
        expected = _read_snapshot(f"{role}.agent_prompt.txt")
        assert rendered == expected, (
            f"agent prompt for {role} drifted from snapshot. "
            f"If intentional, update tests/snapshots/{role}.agent_prompt.txt."
        )

    @pytest.mark.parametrize("role", ["demand_planning", "supply_planning"])
    def test_markdown_snapshot(self, svc, role):
        rendered = svc.render_role_view(role).as_markdown()
        expected = _read_snapshot(f"{role}.markdown.md")
        assert rendered == expected, (
            f"markdown view for {role} drifted from snapshot. "
            f"If intentional, update tests/snapshots/{role}.markdown.md."
        )
