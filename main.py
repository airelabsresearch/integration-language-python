"""Entry point — compute LCOE from bundled cost data.

Reads a dataset name, target year, discount rate, and project lifetime from
the Aire Labs platform, loads cost assumptions from a CSV built into the
Docker image, and computes Levelized Cost of Energy.
"""

from __future__ import annotations

import sys

from lcoe.airelabs import (
    error_result,
    number_result,
    read_hook_input,
    require_number,
    require_string,
    string_result,
    write_hook_output,
)
from lcoe.data_lookup import load_cost_assumptions
from lcoe.model import compute_lcoe


def main() -> None:
    params = read_hook_input()

    dataset = require_string(params, "dataset")
    target_year = int(require_number(params, "target_year"))
    discount_rate = require_number(params, "discount_rate")
    lifetime_years = int(
        require_number(params, "lifetime_years", expected_unit="years")
    )

    # Load cost assumptions from the bundled CSV.
    costs = load_cost_assumptions(dataset, target_year)

    # Return an error result (not a crash) if discount_rate is invalid. The
    # platform marks the LCOE cell as an error and propagates to downstream
    # formulas, while other outputs still get their values.
    if discount_rate <= 0:
        write_hook_output(
            [
                string_result("dataset", dataset),
                number_result("capex", costs.capex, "USD/kW"),
                number_result("opex", costs.opex, "USD/kW/yr"),
                number_result("capacity_factor", costs.capacity_factor),
                error_result("lcoe", "INVALID_DISCOUNT_RATE"),
            ]
        )
        print(
            f"ERROR — discount_rate must be positive, got {discount_rate:.4f}",
            file=sys.stderr,
        )
        return

    lcoe = compute_lcoe(
        capex=costs.capex,
        opex=costs.opex,
        capacity_factor=costs.capacity_factor,
        discount_rate=discount_rate,
        lifetime_years=lifetime_years,
    )

    write_hook_output(
        [
            string_result("dataset", dataset),
            number_result("capex", costs.capex, "USD/kW"),
            number_result("opex", costs.opex, "USD/kW/yr"),
            number_result("capacity_factor", costs.capacity_factor),
            number_result("lcoe", lcoe, "USD/MWh"),
        ]
    )

    print(
        f"OK — dataset={dataset}, year={target_year}, lcoe={lcoe:.2f} USD/MWh",
        file=sys.stderr,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001 — top-level guard, mirrors main.R tryCatch
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
