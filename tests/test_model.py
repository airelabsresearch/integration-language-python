"""Unit tests for the LCOE model and data lookup.

Run with:  uv run pytest tests/test_model.py
"""

import pytest

from lcoe.data_lookup import load_cost_assumptions
from lcoe.model import capital_recovery_factor, compute_lcoe

# ── CRF ─────────────────────────────────────────────────────────────────────────


def test_crf():
    # CRF at 8%, 25yr: manually = 0.08 * 1.08^25 / (1.08^25 - 1)
    r, n = 0.08, 25
    expected = r * (1 + r) ** n / ((1 + r) ** n - 1)
    assert capital_recovery_factor(0.08, 25) == pytest.approx(expected, abs=1e-8)


def test_crf_rejects_bad_inputs():
    with pytest.raises(ValueError):
        capital_recovery_factor(0, 25)  # zero rate
    with pytest.raises(ValueError):
        capital_recovery_factor(-0.05, 25)  # negative rate
    with pytest.raises(ValueError):
        capital_recovery_factor(0.08, 0)  # zero lifetime


# ── LCOE ────────────────────────────────────────────────────────────────────────


def test_solar_lcoe():
    # Solar 2027: capex=960, opex=16.5, cf=0.28, discount=8%, lifetime=25yr
    lcoe = compute_lcoe(960, 16.5, 0.28, 0.08, 25)

    # Manual: CRF = 0.09368, LCOE = (960 * CRF + 16.5) / (0.28 * 8760) * 1000
    r, n = 0.08, 25
    crf = r * (1 + r) ** n / ((1 + r) ** n - 1)
    expected = (960 * crf + 16.5) / (0.28 * 8760) * 1000
    assert lcoe == pytest.approx(expected, abs=0.01)

    # Sanity: solar LCOE should be in the 30-80 $/MWh range.
    assert 30 < lcoe < 80


def test_wind_lcoe():
    # Wind 2030: capex=1150, opex=37.5, cf=0.37
    lcoe = compute_lcoe(1150, 37.5, 0.37, 0.08, 25)
    assert 30 < lcoe < 100


def test_lcoe_rejects_bad_capacity_factor():
    with pytest.raises(ValueError):
        compute_lcoe(960, 16.5, 0, 0.08, 25)  # zero cf
    with pytest.raises(ValueError):
        compute_lcoe(960, 16.5, 1.5, 0.08, 25)  # cf > 1


# ── Data lookup ───────────────────────────────────────────────────────────────


def test_load_solar():
    costs = load_cost_assumptions("solar", 2027)
    assert costs.capex == 960
    assert costs.opex == 16.5
    assert costs.capacity_factor == 0.28


def test_unknown_dataset():
    with pytest.raises(ValueError):
        load_cost_assumptions("geothermal", 2027)


def test_unknown_year():
    with pytest.raises(ValueError):
        load_cost_assumptions("solar", 2050)
