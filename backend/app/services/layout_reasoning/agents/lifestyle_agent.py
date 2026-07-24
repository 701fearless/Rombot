"""Lifestyle Agent: user / household lifestyle suggestions only."""

from __future__ import annotations

from typing import Any

from app.services.layout_reasoning.agents.llm_client import SpatialLLMClient
from app.services.layout_reasoning.agents.prompts import LIFESTYLE_AGENT_PROMPT, SYSTEM_PROMPT, format_json
from app.services.layout_reasoning.agents.schemas import AgentOutput, AgentSuggestion, CoordinatorTask


async def run_lifestyle_agent(task: CoordinatorTask, llm: SpatialLLMClient) -> AgentOutput:
    if llm.is_live:
        try:
            raw = await llm.complete_json(
                system=SYSTEM_PROMPT,
                user=LIFESTYLE_AGENT_PROMPT.format(
                    task_json=format_json(task.model_dump()),
                    user_profile=format_json(task.userProfile),
                ),
            )
            return _parse_output(raw)
        except Exception:
            pass
    return _mock_lifestyle_output(task)


def _parse_output(raw: dict) -> AgentOutput:
    suggestions: list[AgentSuggestion] = []
    for index, item in enumerate(raw.get("suggestions") or [], start=1):
        if not isinstance(item, dict):
            continue
        suggestions.append(
            AgentSuggestion(
                id=str(item.get("id") or f"lifestyle_{index:03d}"),
                category=str(item.get("category") or "Lifestyle"),
                priority=str(item.get("priority") or "Medium"),
                title=str(item.get("title") or "Lifestyle suggestion"),
                reason=str(item.get("reason") or ""),
                action=str(item.get("action") or item.get("recommendation") or ""),
                confidence=float(item.get("confidence") or 0.8),
            )
        )
    return AgentOutput(agent="lifestyle", suggestions=suggestions)


def _mock_lifestyle_output(task: CoordinatorTask) -> AgentOutput:
    profile = task.userProfile or {}
    suggestions: list[AgentSuggestion] = []
    idx = 1

    pets = profile.get("pets") or []
    if pets:
        pet_names = ", ".join(str(p) for p in pets)
        suggestions.append(
            AgentSuggestion(
                id=f"lifestyle_{idx:03d}",
                category="Lifestyle",
                priority="Medium",
                title="Create Pet Activity Area",
                reason=f"Household includes pets ({pet_names}); window-side activity space improves comfort.",
                action="Reserve at least 1 square meter beside the window for pet activity, clear of furniture edges.",
                confidence=0.88,
            )
        )
        idx += 1

    members = profile.get("familyMembers") or profile.get("members") or []
    has_children = bool(profile.get("hasChildren")) or any(
        str(m).lower() in {"child", "children", "kid", "kids"} for m in members
    )
    if has_children:
        suggestions.append(
            AgentSuggestion(
                id=f"lifestyle_{idx:03d}",
                category="Safety",
                priority="High",
                title="Child-Safe Clear Pathways",
                reason="Children in the household increase the need for unobstructed circulation.",
                action="Keep a continuous 0.8 m walking path between sofa, door, and main seating.",
                confidence=0.9,
            )
        )
        idx += 1

    has_elderly = bool(profile.get("hasElderly")) or any(
        str(m).lower() in {"elderly", "senior", "elder"} for m in members
    )
    if has_elderly:
        suggestions.append(
            AgentSuggestion(
                id=f"lifestyle_{idx:03d}",
                category="Accessibility",
                priority="High",
                title="Improve Accessibility Near Seating",
                reason="Elderly household members benefit from easier sit-to-stand clearance.",
                action="Leave at least 0.6 m free space in front of primary seating for safe transfer.",
                confidence=0.87,
            )
        )
        idx += 1

    if profile.get("fengShuiPreference") or profile.get("preferFengShui"):
        suggestions.append(
            AgentSuggestion(
                id=f"lifestyle_{idx:03d}",
                category="Lifestyle",
                priority="Low",
                title="Prefer Open Sightline from Entrance",
                reason="User prefers Feng Shui-oriented comfort cues without reconstruction.",
                action="Avoid placing tall cabinets that fully block the entrance sightline.",
                confidence=0.7,
            )
        )
        idx += 1

    storage = profile.get("storageHabits") or profile.get("storage")
    if storage:
        suggestions.append(
            AgentSuggestion(
                id=f"lifestyle_{idx:03d}",
                category="Lifestyle",
                priority="Medium",
                title="Support Daily Storage Habits",
                reason=f"User storage preference noted: {storage}.",
                action="Keep a small clear surface or basket zone near the entrance for daily items.",
                confidence=0.8,
            )
        )
        idx += 1

    if not suggestions:
        suggestions.append(
            AgentSuggestion(
                id="lifestyle_001",
                category="Lifestyle",
                priority="Low",
                title="Maintain Comfortable Living Rhythm",
                reason="No strong lifestyle constraints were provided; keep circulation and seating comfort.",
                action="Preserve open floor area in the center for daily movement and guests.",
                confidence=0.75,
            )
        )

    return AgentOutput(agent="lifestyle", suggestions=suggestions)


def default_user_profile(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = {
        "familyMembers": ["adult", "adult"],
        "hasChildren": False,
        "hasElderly": False,
        "pets": ["cat"],
        "dailyHabits": ["remote_work", "evening_tv"],
        "storageHabits": "keep_daily_items_near_entrance",
        "fengShuiPreference": False,
        "preferPrivacy": True,
        "preferComfort": True,
    }
    if overrides:
        profile.update(overrides)
    return profile
