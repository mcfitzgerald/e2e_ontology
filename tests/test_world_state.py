"""Validate world_state.yaml against the ontology schema and the dimensions
declared in plan_of_attack.md Phase 0.2.

Three classes of check:
  1. Structural — every entity carries the required slots from its schema class.
  2. Dimensional — counts match the plan.
  3. Narrative — the conflict math in demo_narrative.md works out against
     the fixture's production schedule + promo uplift.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from linkml_runtime import SchemaView


REPO_ROOT = Path(__file__).resolve().parent.parent


# Map fixture list keys to the schema class each item should match.
ENTITY_LISTS = [
    ("skus", "SKU"),
    ("production_lines", "ProductionLine"),
    ("suppliers", "Supplier"),
    ("retailer_commitments", "RetailerCommitment"),
    ("trade_promotions", "TradePromotion"),
]


@pytest.fixture(scope="module")
def fixture() -> dict:
    return yaml.safe_load((REPO_ROOT / "world_state.yaml").read_text())


@pytest.fixture(scope="module")
def schema_view() -> SchemaView:
    return SchemaView(str(REPO_ROOT / "supply_chain_demo.yaml"))


def test_fixture_parses(fixture):
    """world_state.yaml is well-formed YAML with the expected top-level keys."""
    expected_keys = {
        "clock",
        "skus",
        "production_lines",
        "suppliers",
        "retailer_commitments",
        "trade_promotions",
        "production_schedule",
    }
    assert expected_keys.issubset(fixture.keys())


def test_clock_present(fixture):
    """Clock seed is an integer day-of-year (1-365)."""
    today = fixture["clock"]["today_day_of_year"]
    assert isinstance(today, int)
    assert 1 <= today <= 365


@pytest.mark.parametrize("list_key, class_name", ENTITY_LISTS)
def test_required_slots_present(fixture, schema_view, list_key, class_name):
    """Every item in each entity list carries the slots its schema class
    declares as required."""
    slots = schema_view.class_induced_slots(class_name)
    required = {s.name for s in slots if s.required}

    items = fixture[list_key]
    assert items, f"{list_key} is empty"
    for i, item in enumerate(items):
        missing = required - set(item.keys())
        assert not missing, (
            f"{class_name}[{i}] (id-ish: {next(iter(item.values()), '?')}) "
            f"missing required slots: {sorted(missing)}"
        )


def test_dimensions_match_plan(fixture):
    """Counts match plan_of_attack.md Phase 0.2 dimensions."""
    assert len(fixture["skus"]) == 5
    assert len(fixture["production_lines"]) == 4  # 2 plants × 2 lines
    assert len(fixture["suppliers"]) == 6
    assert len(fixture["retailer_commitments"]) == 8
    assert len(fixture["trade_promotions"]) == 2


def test_two_plants_two_lines_each(fixture):
    """Production lines distribute as 2 plants × 2 lines."""
    by_plant: dict[str, list[str]] = {}
    for line in fixture["production_lines"]:
        by_plant.setdefault(line["plant_code"], []).append(line["line_code"])
    assert len(by_plant) == 2
    for plant, lines in by_plant.items():
        assert len(lines) == 2, f"plant {plant} has {len(lines)} lines"


def test_three_retailers_present(fixture):
    """The fixture exercises three retailers across commitments + promos."""
    retailers = {c["retailer"] for c in fixture["retailer_commitments"]}
    retailers |= {p["retailer"] for p in fixture["trade_promotions"]}
    assert retailers == {"WALMART", "TARGET", "KROGER"}


def test_sku_references_resolve(fixture):
    """Every SKU code referenced by commitments, promos, and the production
    schedule appears in the skus list."""
    sku_codes = {s["sku_code"] for s in fixture["skus"]}

    for c in fixture["retailer_commitments"]:
        assert c["sku"] in sku_codes, f"commitment {c['commitment_id']} → unknown sku {c['sku']}"
    for p in fixture["trade_promotions"]:
        assert p["sku"] in sku_codes, f"promo {p['promo_id']} → unknown sku {p['sku']}"
    for entry in fixture["production_schedule"]:
        assert entry["sku"] in sku_codes, f"schedule entry → unknown sku {entry['sku']}"


def test_line_references_resolve(fixture):
    """Every line code in the production schedule appears in production_lines."""
    line_codes = {line["line_code"] for line in fixture["production_lines"]}
    for entry in fixture["production_schedule"]:
        assert entry["line"] in line_codes, f"schedule entry → unknown line {entry['line']}"


def test_promo_commitment_status_is_valid_enum(fixture, schema_view):
    """Promo commitment_status values match the CommitmentStatus enum."""
    enum = schema_view.get_enum("CommitmentStatus")
    permitted = set(enum.permissible_values.keys())
    for p in fixture["trade_promotions"]:
        assert p["commitment_status"] in permitted, (
            f"promo {p['promo_id']} has commitment_status={p['commitment_status']} "
            f"not in {sorted(permitted)}"
        )


def test_capacity_conflict_math(fixture):
    """The fixture's production schedule + the Walmart promo uplift creates
    the canonical NJ-L1 capacity conflict (per demo_narrative.md Scene 4).

    Math:
        NJ-L1 capacity:          5000 units/week
        Baseline week 140:
          TP-FLAG-6OZ:           1500
          TP-SEC-6OZ:            2000
                                 ----
          Total baseline:        3500   (70% loaded — fine)
        With promo (3× TP-FLAG):
          TP-FLAG-6OZ:           4500   (1500 × 3)
          TP-SEC-6OZ:            2000
                                 ----
          Total with promo:      6500   (130% — CONFLICT)
        Shortfall:               1500 units/week
    """
    nj_l1 = next(l for l in fixture["production_lines"] if l["line_code"] == "NJ-L1")
    assert nj_l1["rated_weekly_capacity"] == 5000

    walmart_promo = next(
        p for p in fixture["trade_promotions"]
        if p["promo_id"] == "PROMO-WMT-FLAG-2026Q2"
    )
    assert walmart_promo["sku"] == "TP-FLAG-6OZ"
    assert walmart_promo["volume_uplift_factor"] == 3.0

    # Week 140 baseline load on NJ-L1
    week_140 = [
        e for e in fixture["production_schedule"]
        if e["line"] == "NJ-L1" and e["week_start_day"] == 140
    ]
    baseline_total = sum(e["units"] for e in week_140)
    flag_baseline = next(e["units"] for e in week_140 if e["sku"] == "TP-FLAG-6OZ")

    assert baseline_total == 3500
    assert baseline_total < nj_l1["rated_weekly_capacity"]  # baseline alone is fine

    # With the promo's uplift on TP-FLAG-6OZ
    with_promo = (
        baseline_total
        - flag_baseline
        + flag_baseline * walmart_promo["volume_uplift_factor"]
    )
    assert with_promo == 6500
    assert with_promo > nj_l1["rated_weekly_capacity"]  # the conflict

    shortfall = with_promo - nj_l1["rated_weekly_capacity"]
    assert shortfall == 1500


def test_target_at_risk_commitment_exists(fixture):
    """The narrative's at-risk commitment (Target on TP-SEC-6OZ) is present
    and its MABD falls within the conflict window."""
    com = next(
        c for c in fixture["retailer_commitments"]
        if c["commitment_id"] == "COM-TGT-SEC-Q2"
    )
    assert com["retailer"] == "TARGET"
    assert com["sku"] == "TP-SEC-6OZ"
    # MABD day 130, promo runs days 142-156 → commitment is upstream of promo
    # window; the conflict arises because production for it shares NJ-L1.
    assert com["mabd_day"] == 130


def test_walmart_promo_is_renegotiable(fixture):
    """The Walmart promo is `aligned`, not `committed` — making promo
    renegotiation a viable resolution path per
    viable_promo_renegotiation (introduced as an advisory criterion in
    Phase 5)."""
    walmart_promo = next(
        p for p in fixture["trade_promotions"]
        if p["promo_id"] == "PROMO-WMT-FLAG-2026Q2"
    )
    assert walmart_promo["commitment_status"] == "aligned"


def test_supplier_lead_times_span_meaningful_range(fixture):
    """Lead times need variation for the respect_lead_time axiom to bite
    on tight required-by dates."""
    leads = [s["lead_time_days"] for s in fixture["suppliers"]]
    assert min(leads) <= 10
    assert max(leads) >= 21
