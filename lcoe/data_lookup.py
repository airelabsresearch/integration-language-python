"""Load cost assumptions from a bundled CSV dataset.

The ``data/`` directory contains CSV files built into the Docker image. Each
file represents a generation technology (solar, wind) with year-by-year cost
projections. Uses only the standard-library ``csv`` module — no pandas — to
keep the image small.
"""

from __future__ import annotations

import csv
import os
from typing import NamedTuple

# Resolve data/ relative to the repo root (the parent of this package), so the
# lookup works regardless of the process's current working directory.
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


class CostAssumptions(NamedTuple):
    capex: float
    opex: float
    capacity_factor: float


def available_datasets() -> list[str]:
    """List available datasets (CSV file stems in ``data/``)."""
    if not os.path.isdir(DATA_DIR):
        return []
    return sorted(
        os.path.splitext(f)[0] for f in os.listdir(DATA_DIR) if f.endswith(".csv")
    )


def load_cost_assumptions(dataset: str, target_year: int) -> CostAssumptions:
    """Load cost assumptions for a technology and year.

    Raises with a clear message if the dataset or year is not found.
    """
    datasets = available_datasets()
    if dataset not in datasets:
        raise ValueError(
            f"unknown dataset '{dataset}' — available datasets: {', '.join(datasets)}"
        )

    path = os.path.join(DATA_DIR, f"{dataset}.csv")
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        if int(row["year"]) == target_year:
            return CostAssumptions(
                capex=float(row["capex_usd_per_kw"]),
                opex=float(row["opex_usd_per_kw_yr"]),
                capacity_factor=float(row["capacity_factor"]),
            )

    years = ", ".join(row["year"] for row in rows)
    raise ValueError(
        f"year {target_year} not found in '{dataset}' dataset — available years: {years}"
    )
