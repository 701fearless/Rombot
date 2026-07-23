from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


RULES_PATH = Path(__file__).resolve().parent / "rules" / "clearance_rules.json"


@lru_cache
def load_rules() -> dict[str, Any]:
    with RULES_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def normalize_label(label: str) -> str:
    normalized = label.strip().lower().replace("-", "_").replace(" ", "_")
    return "_".join(part for part in normalized.split("_") if part)


def furniture_rule(label: str) -> dict[str, Any] | None:
    rules = load_rules()
    return rules.get("furniture", {}).get(normalize_label(label))


def clearance_sides(label: str) -> dict[str, float]:
    rule = furniture_rule(label)
    if not rule:
        return {}
    return {side: float(value) for side, value in rule.get("sides", {}).items()}


def non_solid_labels() -> set[str]:
    rules = load_rules()
    return {normalize_label(item) for item in rules.get("nonSolidLabels", [])}


def is_solid_furniture(label: str) -> bool:
    return normalize_label(label) not in non_solid_labels()


def accessibility_defaults() -> dict[str, float]:
    rules = load_rules().get("accessibility", {})
    return {
        "door": float(rules.get("doorDefaultClearanceDepth", 0.9)),
        "window": float(rules.get("windowDefaultClearanceDepth", 0.3)),
    }


def display_name(label: str, fallback: str | None = None) -> str:
    rule = furniture_rule(label)
    if rule and rule.get("name"):
        return str(rule["name"])
    return fallback or normalize_label(label)
