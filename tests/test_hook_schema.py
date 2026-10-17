"""hook-schema.json must describe what main.py actually reads and writes.

The registry rejects a label with an unknown key, so these tests also keep the
file to the declared fields. `moon run lcoe:schema-check` validates the rest
(types, name patterns) against the published JSON Schema.
"""

import json
import os
from typing import Any

import pytest

from lcoe.hook_schema import HOOK_SCHEMA
from tests.test_main import run_with_fixture

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "fixtures")


def load_fixture(name: str) -> dict[str, Any]:
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return json.load(f)


def declared(kind: str) -> dict[str, dict[str, Any]]:
    return {spec["name"]: spec for spec in HOOK_SCHEMA[kind]}


def test_only_known_top_level_keys():
    assert set(HOOK_SCHEMA) <= {"version", "inputs", "outputs"}
    assert HOOK_SCHEMA["version"] == 1


@pytest.mark.parametrize(
    "fixture",
    ["hook-input.json", "hook-input-wind.json", "hook-input-bad-rate.json"],
)
def test_fixture_sends_every_required_input_in_its_declared_unit(fixture):
    params = {p["name"]: p for p in load_fixture(fixture)["parametersV1"]}
    for name, spec in declared("inputs").items():
        if spec["required"]:
            assert name in params, f"{fixture} does not send required {name!r}"
        if "unit" in spec and name in params:
            assert params[name]["number"].get("unit") == spec["unit"]
    assert set(params) <= set(declared("inputs")), "fixture sends undeclared input"


def test_every_result_is_declared_with_its_declared_unit(tmp_path):
    output = run_with_fixture(tmp_path, "hook-input.json")
    results = {r["name"]: r for r in output["results"]}
    assert set(results) == set(declared("outputs"))
    for name, spec in declared("outputs").items():
        if "number" in results[name]:
            assert results[name]["number"].get("unit") == spec.get("unit")
