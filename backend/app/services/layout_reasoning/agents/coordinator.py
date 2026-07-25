"""Coordinator Agent: parse house JSON and dispatch structured tasks."""

from __future__ import annotations

from typing import Any

from app.services.layout_reasoning.agents.llm_client import SpatialLLMClient
from app.services.layout_reasoning.agents.prompts import COORDINATOR_PROMPT, SYSTEM_PROMPT, format_json
from app.services.layout_reasoning.agents.schemas import CoordinatorTask


LAYOUT_FOCUS = [
    "furniture_layout",
    "walking_path",
    "spacing",
    "space_utilization",
    "visual_balance",
    "lighting",
    "zoning",
    "orientation",
]

LIFESTYLE_FOCUS = [
    "family",
    "children",
    "elderly",
    "pets",
    "daily_habits",
    "storage",
    "feng_shui",
    "accessibility",
    "privacy",
    "comfort",
]


async def run_coordinator(house_json: dict[str, Any], llm: SpatialLLMClient) -> CoordinatorTask:
    """Parse upstream JSON into a structured task object (no suggestions)."""
    if llm.is_live:
        try:
            raw = await llm.complete_json(
                system=SYSTEM_PROMPT,
                user=COORDINATOR_PROMPT.format(house_json=format_json(house_json)),
            )
            return _normalize_task(raw, house_json)
        except Exception:
            # Fall back to deterministic parse so the pipeline remains available.
            pass
    return _deterministic_task(house_json)


def _deterministic_task(house_json: dict[str, Any]) -> CoordinatorTask:
    return CoordinatorTask(
        room=dict(house_json.get("room") or {}),
        furniture=list(house_json.get("furniture") or []),
        openings=list(house_json.get("openings") or []),
        geometryChecks=list(house_json.get("geometryChecks") or []),
        candidate=dict(house_json.get("candidate") or {}),
        userProfile=dict(house_json.get("userProfile") or {}),
        layoutFocus=list(LAYOUT_FOCUS),
        lifestyleFocus=list(LIFESTYLE_FOCUS),
    )


def _normalize_task(raw: dict[str, Any], house_json: dict[str, Any]) -> CoordinatorTask:
    base = _deterministic_task(house_json)
    return CoordinatorTask(
        room=raw.get("room") or base.room,
        furniture=raw.get("furniture") or base.furniture,
        openings=raw.get("openings") or base.openings,
        geometryChecks=raw.get("geometryChecks") or base.geometryChecks,
        candidate=raw.get("candidate") or base.candidate,
        userProfile=raw.get("userProfile") or base.userProfile,
        layoutFocus=raw.get("layoutFocus") or base.layoutFocus,
        lifestyleFocus=raw.get("lifestyleFocus") or base.lifestyleFocus,
    )
