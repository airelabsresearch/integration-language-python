"""LCOE (Levelized Cost of Energy) calculator.

Computes the cost of generating one MWh of electricity over a project's
lifetime using the standard formula::

    LCOE = (capex * CRF + opex) / (capacity_factor * 8760) * 1000

where CRF (Capital Recovery Factor) converts a lump-sum capex into an
equivalent annual payment::

    CRF = r * (1 + r)^n / ((1 + r)^n - 1)

Pure business logic — no knowledge of JSON, Docker, or Aire Labs. You can
import this module in a REPL and call :func:`compute_lcoe` directly.
"""

from __future__ import annotations

HOURS_PER_YEAR = 8760


def capital_recovery_factor(discount_rate: float, lifetime_years: float) -> float:
    """Compute the Capital Recovery Factor."""
    if discount_rate <= 0:
        raise ValueError("discount_rate must be positive")
    if lifetime_years <= 0:
        raise ValueError("lifetime_years must be positive")
    r = discount_rate
    n = lifetime_years
    return r * (1 + r) ** n / ((1 + r) ** n - 1)


def compute_lcoe(
    capex: float,
    opex: float,
    capacity_factor: float,
    discount_rate: float,
    lifetime_years: float,
) -> float:
    """Compute LCOE in USD/MWh from cost assumptions."""
    if capacity_factor <= 0 or capacity_factor > 1:
        raise ValueError("capacity_factor must be between 0 and 1")
    crf = capital_recovery_factor(discount_rate, lifetime_years)
    lcoe_per_kwh = (capex * crf + opex) / (capacity_factor * HOURS_PER_YEAR)
    return lcoe_per_kwh * 1000
