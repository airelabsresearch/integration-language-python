"""Aire Labs Hook I/O helpers for Python.

Thin wrapper around the standard-library ``json`` module that reads HookInput
parameters and writes HookOutput results. Copy this file into any Python
container function project as a starting point — it has no third-party
dependencies.

The platform passes parameters as a ``parametersV1`` list, where every numeric
value is encoded as a *string* (e.g. ``{"value": "2027"}``), and expects
results back under a ``results`` key with the same string encoding. These
helpers hide that wire format so your model code works with plain Python
numbers.
"""

from __future__ import annotations

import json
import os
from datetime import date
from typing import Any

# ── Reading input ─────────────────────────────────────────────────────────────


def read_hook_input() -> list[dict[str, Any]]:
    """Read and parse the HookInput JSON file.

    Returns the ``parametersV1`` list of parameter rows.
    """
    path = os.environ.get("AIRELABS_HOOK_INPUT_PATH", "")
    if not path:
        raise RuntimeError("AIRELABS_HOOK_INPUT_PATH is not set")
    with open(path, encoding="utf-8") as f:
        hook_input = json.load(f)
    return hook_input.get("parametersV1", [])


def _require_param(params: list[dict[str, Any]], name: str) -> dict[str, Any]:
    """Look up a single parameter row by name. Raises if missing."""
    for row in params:
        if row.get("name") == name:
            return row
    raise ValueError(f"missing required parameter: '{name}'")


def require_number(
    params: list[dict[str, Any]],
    name: str,
    expected_unit: str | None = None,
) -> float:
    """Extract a numeric parameter as a float.

    Optionally checks that the unit matches ``expected_unit``.
    """
    row = _require_param(params, name)
    num = row.get("number")
    if num is None:
        raise ValueError(f"parameter '{name}': expected 'number' field")
    unit = num.get("unit")
    if expected_unit is not None and unit is not None and unit != expected_unit:
        raise ValueError(
            f"parameter '{name}': expected unit '{expected_unit}', got '{unit}'"
        )
    return float(num["value"])


def require_string(params: list[dict[str, Any]], name: str) -> str:
    """Extract a string parameter."""
    row = _require_param(params, name)
    if "string" not in row:
        raise ValueError(f"parameter '{name}': expected 'string' field")
    return str(row["string"])


def require_boolean(params: list[dict[str, Any]], name: str) -> bool:
    """Extract a boolean parameter (returns a Python ``bool``)."""
    row = _require_param(params, name)
    if "boolean" not in row:
        raise ValueError(f"parameter '{name}': expected 'boolean' field")
    return str(row["boolean"]) == "true"


def require_date(params: list[dict[str, Any]], name: str) -> date:
    """Extract a date parameter (returns a ``datetime.date``)."""
    row = _require_param(params, name)
    if "date" not in row:
        raise ValueError(f"parameter '{name}': expected 'date' field")
    return date.fromisoformat(str(row["date"]))


# ── Building results ────────────────────────────────────────────────────────────


def _format_number(value: float) -> str:
    """Round to 2 decimals and render as a plain (non-scientific) string."""
    return f"{round(value, 2):.2f}"


def number_result(name: str, value: float, unit: str | None = None) -> dict[str, Any]:
    """Build a number result entry."""
    num: dict[str, Any] = {"value": _format_number(value)}
    if unit is not None:
        num["unit"] = unit
    return {"name": name, "number": num}


def number_array_result(
    name: str, values: list[float], unit: str | None = None
) -> dict[str, Any]:
    """Build a numberArray result entry."""
    arr: dict[str, Any] = {"values": [_format_number(v) for v in values]}
    if unit is not None:
        arr["unit"] = unit
    return {"name": name, "numberArray": arr}


def string_result(name: str, value: str) -> dict[str, Any]:
    """Build a string result entry."""
    return {"name": name, "string": value}


def boolean_result(name: str, value: bool) -> dict[str, Any]:
    """Build a boolean result entry."""
    return {"name": name, "boolean": "true" if value else "false"}


def date_result(name: str, value: date) -> dict[str, Any]:
    """Build a date result entry."""
    return {"name": name, "date": value.isoformat()}


def error_result(name: str, error_code: str) -> dict[str, Any]:
    """Build an error result entry.

    Use this when a specific output could not be computed. The platform
    displays the error string in the model cell and marks downstream cells as
    dependent errors.
    """
    return {"name": name, "error": error_code}


# ── Writing output ──────────────────────────────────────────────────────────────


def write_hook_output(results: list[dict[str, Any]]) -> None:
    """Write a list of results to the HookOutput JSON file."""
    path = os.environ.get("AIRELABS_HOOK_OUTPUT_PATH", "")
    if not path:
        raise RuntimeError("AIRELABS_HOOK_OUTPUT_PATH is not set")
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"results": results}, f)
