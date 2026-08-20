"""Fixture loader for contract extraction examples."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_extraction_fixture(name: str) -> dict[str, Any]:
    path = Path(__file__).resolve().parents[2] / "contracts" / "examples" / f"{name}.json"
    with path.open(encoding="utf-8") as fixture_file:
        payload = json.load(fixture_file)
    if not isinstance(payload, dict):
        raise ValueError(f"fixture {name!r} must contain an object")
    return payload

