"""Snapshot + structural tests for the role-view render (Phase 1.2).

Snapshot files live in `tests/snapshots/`. To regenerate after an intentional
render change, run the snapshot-update helper at the bottom of this file
(`pytest tests/test_role_view_render.py -k snapshot --update-snapshots`)
or simply re-run the one-liner under `tools/render_snapshots.py` (see CHANGELOG).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ontology_service import ORIENTATION, OntologyService, RoleView


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


class TestQuantumSchemaRendering:
    """Phase 1.5 — the slot block under each flow must surface in the
    rendered prompt so the LLM doesn't guess payload shape."""

    def test_handoff_prompt_includes_quantum_slot_block(self, svc):
        prompt = svc.render_role_view("demand_planning").as_agent_prompt()
        assert "quantum SupplyRequest slots:" in prompt
        # Required slot with no description renders as bare type/required.
        assert "request_id: string (required)" in prompt
        # Class-typed slot carries the "pass entity id as a string" nudge.
        assert "sku: SKU (required) — Pass the entity id as a string." in prompt
        # Slot with a description renders the description.
        assert (
            "required_by: integer (required) — Day (1-365) by which supply must be in position."
            in prompt
        )
        # Optional slot is marked optional.
        assert "source_signal_ref: string (optional)" in prompt

    def test_query_prompt_includes_both_slot_blocks(self, svc):
        prompt = svc.render_role_view("supply_planning").as_agent_prompt()
        # The query carries OTIFQuery; the response carries OTIFExposure.
        assert "quantum OTIFQuery slots:" in prompt
        assert "returns OTIFExposure slots:" in prompt
        assert "calculated_penalty: decimal (required)" in prompt

    def test_enum_slot_renders_permissible_values(self, svc):
        prompt = svc.render_role_view("supply_planning").as_agent_prompt()
        assert (
            "commitment_status: CommitmentStatus (required) — "
            "Values: proposed, aligned, committed, contractually_locked."
            in prompt
        )

    def test_multivalued_slot_renders_array_marker(self, svc):
        prompt = svc.render_role_view("supply_planning").as_agent_prompt()
        # CapacityConflict.competing_skus
        assert "competing_skus: SKU[] (required) — " in prompt


class TestPlaybookRendering:
    """Phase 1.8 — the PLAYBOOKS ANCHORED TO ME section, and the §2-critical
    neutralization: list order must never read as priority."""

    def test_playbook_section_present_for_supply_planning(self, svc):
        prompt = svc.render_role_view("supply_planning").as_agent_prompt()
        assert "PLAYBOOKS ANCHORED TO ME" in prompt
        assert "resolve_capacity_conflict" in prompt
        assert "triggered_by: capacity_conflict_detected" in prompt
        assert "input_quantum: CapacityConflict" in prompt

    def test_playbook_absent_for_unanchored_role(self, svc):
        prompt = svc.render_role_view("production_planning").as_agent_prompt()
        assert "(none — no playbook is anchored to this role)" in prompt
        assert "resolve_capacity_conflict" not in prompt

    def test_context_assembly_shows_returns_and_sync(self, svc):
        prompt = svc.render_role_view("supply_planning").as_agent_prompt()
        # closed_set tightens the header in place of the bare ':' form.
        assert "context_assembly (parallel, wait_all) — complete set" in prompt
        assert "check_otif_exposure  (returns OTIFExposure)" in prompt
        assert "check_coman_availability  (returns ComanAvailability)" in prompt

    def test_context_assembly_inputs_bound_to_input_quantum(self, svc):
        """Seed C: the query inputs are projected from the CapacityConflict the
        agent was handed, so it scopes each query to the conflict's entities
        rather than sweeping. The binding is structural, not a prompt nudge."""
        v = svc.render_role_view("supply_planning")
        pb = v.playbooks_anchored_to[0]
        assert pb.closed_set is True
        steps = {s.flow: s for s in pb.context_assembly}
        # coman is scoped to the competing SKUs, the shortfall, and the window.
        coman = {b.param: b.from_quantum for b in steps["check_coman_availability"].inputs_from_quantum}
        assert coman == {
            "sku": "competing_skus",
            "volume": "shortfall_units",
            "window_start_day": "window_start_day",
            "window_end_day": "window_end_day",
        }
        # otif co-indexes sku + retailer per at-risk commitment.
        otif = {b.param: b.from_quantum for b in steps["check_otif_exposure"].inputs_from_quantum}
        assert otif == {
            "sku": "at_risk_commitments.sku",
            "retailer": "at_risk_commitments.retailer",
        }
        # promo flexibility stays agent-shaped (the conflict names no promo).
        assert steps["check_promo_flexibility"].inputs_from_quantum == ()
        prompt = v.as_agent_prompt()
        assert "input sku <- CapacityConflict.competing_skus" in prompt
        assert "input retailer <- CapacityConflict.at_risk_commitments.retailer" in prompt

    def test_resolution_paths_neutralized(self, svc):
        """The load-bearing §2 test: resolution paths render alphabetized and
        explicitly labelled 'order arbitrary'. A reader must not be able to
        infer a preferred path from list position."""
        v = svc.render_role_view("supply_planning")
        pb = v.playbooks_anchored_to[0]
        flows = [r.flow for r in pb.selects_one_of]
        assert flows == sorted(flows), "resolution paths must be alphabetized (neutralized)"
        prompt = v.as_agent_prompt()
        assert "resolution paths (pick one; order arbitrary):" in prompt
        # Each path carries its target role.
        assert "request_promo_revision  (to customer_development)" in prompt
        assert "shift_to_coman  (to co_manufacturing)" in prompt

    def test_criteria_carry_nl(self, svc):
        v = svc.render_role_view("supply_planning")
        pb = v.playbooks_anchored_to[0]
        crit_names = {c.name for c in pb.criteria}
        assert crit_names == {
            "viable_promo_renegotiation", "viable_coman_shift", "tolerable_otif_penalty",
        }
        # nl text is resolved from the advisory axioms, not left as a bare name.
        assert all(len(c.nl) > 20 for c in pb.criteria)

    def test_always_fires_rendered(self, svc):
        prompt = svc.render_role_view("supply_planning").as_agent_prompt()
        assert "always fires on completion:" in prompt
        assert "event: capacity_resolved" in prompt
        assert "flow: plan_fulfillment" in prompt


class TestToolRendering:
    """Phase 1.8 — the TOOLS AVAILABLE TO ME section, filtered by available_to."""

    def test_tools_section_lists_readers(self, svc):
        prompt = svc.render_role_view("supply_planning").as_agent_prompt()
        assert "TOOLS AVAILABLE TO ME" in prompt
        assert "(reader) query_plants_for_sku:" in prompt
        assert "input:  PlantQuery (sku: SKU)" in prompt
        assert "output: PlantQueryResult (lines: ProductionLine[])" in prompt

    def test_tools_filtered_by_available_to(self, svc):
        """production_planning is in available_to only for query_line_load."""
        v = svc.render_role_view("production_planning")
        names = [t.name for t in v.tools_available_to]
        assert names == ["query_line_load"]
        prompt = v.as_agent_prompt()
        assert "(reader) query_line_load:" in prompt
        assert "query_plants_for_sku" not in prompt

    def test_call_tool_kit_line_lists_available_tools(self, svc):
        prompt = svc.render_role_view("supply_planning").as_agent_prompt()
        # The fixed tool-kit call_tool line now enumerates the role's tools.
        assert "call_tool(name, input): invoke a declared tool available to you" in prompt
        assert "query_commitments_in_window" in prompt


class TestPlaybookToolSerialization:
    def test_round_trip_preserves_playbooks_and_tools(self, svc):
        v = svc.render_role_view("supply_planning")
        data = v.as_json()
        assert data["playbooks_anchored_to"][0]["name"] == "resolve_capacity_conflict"
        assert len(data["tools_available_to"]) == 4
        round_trip = RoleView.model_validate(data)
        assert round_trip == v


class TestOrientation:
    """Phase 1.6 — static system orientation preface. Identical across all
    roles by design; replaces what used to be a one-paragraph "supply chain
    coordination system" opener. §2: world-model commentary about how the
    system works, not policy. The "no per-role code in the orientation"
    invariant is the load-bearing test — if a future change tries to vary
    the preface per role, it'd belong in the role-specific section, not
    here."""

    @pytest.mark.parametrize("role", ["demand_planning", "supply_planning"])
    def test_agent_prompt_leads_with_orientation(self, svc, role):
        prompt = svc.render_role_view(role).as_agent_prompt()
        # The orientation appears verbatim at the top, before ROLE:.
        assert prompt.startswith(ORIENTATION.rstrip())
        # ROLE: label appears after the orientation, not before it.
        role_idx = prompt.index(f"ROLE: {role}")
        orientation_end_idx = len(ORIENTATION.rstrip())
        assert role_idx > orientation_end_idx

    @pytest.mark.parametrize("role", ["demand_planning", "supply_planning"])
    def test_markdown_leads_with_orientation(self, svc, role):
        md = svc.render_role_view(role).as_markdown()
        assert md.startswith(ORIENTATION.rstrip())
        # # Role: header appears after the orientation.
        assert f"# Role: {role}" in md
        assert md.index(f"# Role: {role}") > len(ORIENTATION.rstrip())

    def test_orientation_byte_for_byte_identical_across_roles(self, svc):
        """The load-bearing invariant: every agent gets the same orientation.
        If this fails, somebody made the preface role-conditional — push it
        back into the role-specific section."""
        prompt_a = svc.render_role_view("demand_planning").as_agent_prompt()
        prompt_b = svc.render_role_view("supply_planning").as_agent_prompt()
        prefix_a = prompt_a[: len(ORIENTATION.rstrip())]
        prefix_b = prompt_b[: len(ORIENTATION.rstrip())]
        assert prefix_a == prefix_b == ORIENTATION.rstrip()

        md_a = svc.render_role_view("demand_planning").as_markdown()
        md_b = svc.render_role_view("supply_planning").as_markdown()
        assert md_a[: len(ORIENTATION.rstrip())] == md_b[: len(ORIENTATION.rstrip())]

    def test_orientation_is_domain_agnostic(self):
        """No supply-chain-specific terms in the orientation — the same
        preface should render verbatim against any ontology that follows
        this architecture (procurement, healthcare, anything)."""
        lowered = ORIENTATION.lower()
        for forbidden in (
            "supply chain", "promo", "otif", "procurement", "manufacturing",
            "retailer", "sku", "logistics",
        ):
            assert forbidden not in lowered, (
                f"orientation mentions {forbidden!r} — should be domain-agnostic"
            )

    def test_orientation_names_the_design_rule_and_modes(self):
        """Two pieces of operational stance the agent needs to internalize —
        the ontology's world-vs-policy rule (so it knows where its judgment
        lives) and the two reasoning modes (so it knows how to handle a
        blocking axiom vs. a fan-out)."""
        assert "models the world" in ORIENTATION
        assert "action vocabulary" in ORIENTATION
        assert "Mode 1" in ORIENTATION and "Mode 2" in ORIENTATION
        assert "Routing is deterministic" in ORIENTATION
        assert "ephemeral" in ORIENTATION


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
