"""Integration tests — full HookInput -> Python computation -> HookOutput flow.

Run with:  uv run pytest tests/test_main.py
"""

import importlib
import json
import os
from typing import Any

import pytest

import main


def run_with_fixture(tmp_path, fixture_name: str) -> dict[str, Any]:
    """Run main.main() against a fixture and return the parsed HookOutput."""
    fixture_path = os.path.join(
        os.path.dirname(__file__), "..", "fixtures", fixture_name
    )
    output_path = tmp_path / "hook-output.json"
    os.environ["AIRELABS_HOOK_INPUT_PATH"] = os.path.abspath(fixture_path)
    os.environ["AIRELABS_HOOK_OUTPUT_PATH"] = str(output_path)

    # Reload so each run picks up the freshly-set env vars cleanly.
    importlib.reload(main)
    main.main()

    assert output_path.exists()
    with open(output_path, encoding="utf-8") as f:
        return json.load(f)


def get_result_value(output: dict[str, Any], name: str, field: str = "number"):
    entry = next(r for r in output["results"] if r["name"] == name)
    if field == "number":
        return float(entry["number"]["value"])
    if field == "string":
        return entry["string"]
    if field == "error":
        return entry.get("error")
    raise ValueError(f"unknown field '{field}'")


def test_solar(tmp_path):
    output = run_with_fixture(tmp_path, "hook-input.json")
    lcoe = get_result_value(output, "lcoe")
    assert 30 < lcoe < 80
    assert get_result_value(output, "capex") == pytest.approx(960, abs=0.01)
    assert get_result_value(output, "dataset", "string") == "solar"


def test_wind(tmp_path):
    output = run_with_fixture(tmp_path, "hook-input-wind.json")
    lcoe = get_result_value(output, "lcoe")
    assert 30 < lcoe < 100
    assert get_result_value(output, "dataset", "string") == "wind"


def test_error_result(tmp_path):
    output = run_with_fixture(tmp_path, "hook-input-bad-rate.json")
    err = get_result_value(output, "lcoe", "error")
    assert err == "INVALID_DISCOUNT_RATE"
    # Other outputs should still have values.
    assert get_result_value(output, "capex") == pytest.approx(960, abs=0.01)
