"""Validate world_state_balanced.yaml — the Phase A3 balanced variant.

world_state_balanced.yaml is world_state.yaml + the K1 delta only: CA-L1 (the
"alternative toothpaste capacity" line) is made a *grounded, viable* alternative
for the flagship TP-FLAG-6OZ so a live agent can resolve the NJ-L1 capacity
conflict by INTERNAL re-plan (exercising plant_scheduler) — not only by promo
revision. See world_state_balanced.yaml's header and
briefings/seed-phase-A3-balanced-variant.md (orchestrator repo).

Three classes of check:
  1. Schema — the variant parses with the same required slots as the canonical.
  2. K1 invariant — CA-L1 schedules the flagship AND has free residual >= the
     1500 shortfall (so internal re-plan is feasible on capacity).
  3. Drift guard — the variant equals the canonical EXCEPT the named CA-L1 rows.
     If a future edit to world_state.yaml breaks this, re-derive the variant;
     do not loosen the test.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from linkml_runtime import SchemaView


REPO_ROOT = Path(__file__).resolve().parent.parent

# The shortfall the balanced fixture must let CA-L1 absorb (NJ-L1 invariant).
SHORTFALL = 1500

# Map fixture list keys to the schema class each item should match.
ENTITY_LISTS = [
    ("skus", "SKU"),
    ("production_lines", "ProductionLine"),
    ("suppliers", "Supplier"),
    ("retailer_commitments", "RetailerCommitment"),
    ("trade_promotions", "TradePromotion"),
    ("baseline_demand", "BaselineDemand"),
]


@pytest.fixture(scope="module")
def canonical() -> dict:
    return yaml.safe_load((REPO_ROOT / "world_state.yaml").read_text())


@pytest.fixture(scope="module")
def balanced() -> dict:
    return yaml.safe_load((REPO_ROOT / "world_state_balanced.yaml").read_text())


@pytest.fixture(scope="module")
def schema_view() -> SchemaView:
    return SchemaView(str(REPO_ROOT / "supply_chain_demo.yaml"))


# --- 1. Schema -------------------------------------------------------------


@pytest.mark.parametrize("list_key, class_name", ENTITY_LISTS)
def test_required_slots_present(balanced, schema_view, list_key, class_name):
    """Every item in each entity list carries its schema class's required slots —
    the variant must validate exactly like the canonical fixture."""
    slots = schema_view.class_induced_slots(class_name)
    required = {s.name for s in slots if s.required}
    items = balanced[list_key]
    assert items, f"{list_key} is empty"
    for i, item in enumerate(items):
        missing = required - set(item.keys())
        assert not missing, (
            f"{class_name}[{i}] missing required slots: {sorted(missing)}"
        )


def test_same_top_level_shape(canonical, balanced):
    """The variant has the same top-level keys + entity counts as canonical."""
    assert set(balanced.keys()) == set(canonical.keys())
    for key in ("skus", "production_lines", "suppliers",
                "retailer_commitments", "trade_promotions", "baseline_demand"):
        assert len(balanced[key]) == len(canonical[key]), f"{key} count drifted"


# --- 2. K1 invariant -------------------------------------------------------


def _line(fixture: dict, code: str) -> dict:
    return next(l for l in fixture["production_lines"] if l["line_code"] == code)


def _scheduled(fixture: dict, line: str, week: int) -> int:
    return sum(
        e["units"] for e in fixture["production_schedule"]
        if e["line"] == line and e["week_start_day"] == week
    )


def test_ca_l1_makes_the_flagship(balanced):
    """K1(b): CA-L1 now runs a TP-FLAG-6OZ baseline, so query_plants_for_sku
    surfaces it as a line that CAN make the flagship (grounded capability)."""
    flag_on_ca_l1 = [
        e for e in balanced["production_schedule"]
        if e["line"] == "CA-L1" and e["sku"] == "TP-FLAG-6OZ"
    ]
    assert {e["week_start_day"] for e in flag_on_ca_l1} == {140, 147}
    assert all(e["units"] > 0 for e in flag_on_ca_l1)


def test_ca_l1_has_headroom_for_the_shortfall(balanced):
    """K1(a): CA-L1's residual leaves >= 1500 free after its own schedule, so
    internal re-plan to CA-L1 is feasible on capacity (line_capacity_not_exceeded
    checks scheduled + proposed <= available)."""
    ca_l1 = _line(balanced, "CA-L1")
    available = ca_l1["capacity_total"] - ca_l1["committed_load"]
    assert available == 5000  # raised from canonical 4000 via committed_load 46000->45000
    free = available - _scheduled(balanced, "CA-L1", 140)
    assert free >= SHORTFALL, f"CA-L1 free residual {free} < shortfall {SHORTFALL}"


def test_nj_l1_conflict_math_unchanged(balanced):
    """The NJ-L1 conflict invariant survives the variant: 5000 residual, the
    promo drives 6500, shortfall still exactly 1500. The variant adds an
    ALTERNATIVE; it does not rescale the conflict."""
    nj_l1 = _line(balanced, "NJ-L1")
    available = nj_l1["capacity_total"] - nj_l1["committed_load"]
    assert available == 5000
    promo = next(
        p for p in balanced["trade_promotions"]
        if p["promo_id"] == "PROMO-MGM-FLAG-2026Q2"
    )
    week_140 = [
        e for e in balanced["production_schedule"]
        if e["line"] == "NJ-L1" and e["week_start_day"] == 140
    ]
    baseline_total = sum(e["units"] for e in week_140)
    flag_baseline = next(e["units"] for e in week_140 if e["sku"] == "TP-FLAG-6OZ")
    with_promo = baseline_total - flag_baseline + flag_baseline * promo["volume_uplift_factor"]
    assert baseline_total == 3500
    assert with_promo == 6500
    assert with_promo - available == SHORTFALL


# --- 3. Drift guard --------------------------------------------------------


def test_variant_differs_only_in_named_ca_l1_rows(canonical, balanced):
    """The balanced fixture is canonical + the K1 deltas, and NOTHING else.

    Allowed deltas:
      - production_lines: CA-L1.committed_load 46000 -> 45000 (only that slot).
      - production_schedule: + two CA-L1/TP-FLAG-6OZ rows (weeks 140 & 147).
    Any other difference is drift — re-derive the variant, don't relax this.
    """
    # Everything except production_lines + production_schedule is byte-identical.
    for key in canonical:
        if key in ("production_lines", "production_schedule"):
            continue
        assert balanced[key] == canonical[key], f"unexpected drift in {key!r}"

    # production_lines: identical except CA-L1.committed_load.
    for c_line, b_line in zip(canonical["production_lines"], balanced["production_lines"]):
        assert c_line["line_code"] == b_line["line_code"]
        if b_line["line_code"] == "CA-L1":
            assert c_line["committed_load"] == 46000
            assert b_line["committed_load"] == 45000
            assert {k: v for k, v in b_line.items() if k != "committed_load"} == \
                   {k: v for k, v in c_line.items() if k != "committed_load"}
        else:
            assert b_line == c_line, f"{b_line['line_code']} drifted"

    # production_schedule: balanced = canonical + exactly the two new CA-L1 rows.
    def key_of(row: dict) -> tuple:
        return (row["line"], row["sku"], row["week_start_day"], row["units"])

    canonical_rows = {key_of(r) for r in canonical["production_schedule"]}
    balanced_rows = {key_of(r) for r in balanced["production_schedule"]}
    added = balanced_rows - canonical_rows
    removed = canonical_rows - balanced_rows
    assert removed == set(), f"variant removed schedule rows: {removed}"
    assert added == {
        ("CA-L1", "TP-FLAG-6OZ", 140, 400),
        ("CA-L1", "TP-FLAG-6OZ", 147, 400),
    }, f"unexpected added schedule rows: {added}"
