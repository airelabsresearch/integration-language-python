"""This container's declared inputs and outputs, read from ``hook-schema.json``.

``hook-schema.json`` is the only place they are written down. The build copies
it into the image label ``com.airelabs.schema.v1.hook`` (``scripts/release.sh``),
and ``main.py`` reads its units from here, so the label and the code cannot
disagree.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HOOK_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "hook-schema.json"


def load_hook_schema() -> dict[str, Any]:
    with open(HOOK_SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


HOOK_SCHEMA = load_hook_schema()


def _spec(kind: str, name: str) -> dict[str, Any]:
    for spec in HOOK_SCHEMA.get(kind, []):
        if spec["name"] == name:
            return spec
    raise KeyError(f"{name!r} is not declared in hook-schema.json {kind}")


def input_unit(name: str) -> str | None:
    """The unit an input is declared in, or None. Raises on an undeclared name."""
    return _spec("inputs", name).get("unit")


def output_unit(name: str) -> str | None:
    """The unit an output is declared in, or None. Raises on an undeclared name."""
    return _spec("outputs", name).get("unit")
