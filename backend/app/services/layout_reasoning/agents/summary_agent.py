"""Summary Agent: merge, rank, and summarize Layout + Lifestyle outputs."""

from __future__ import annotations

import re
from typing import Any

from app.services.layout_reasoning.agents.llm_client import SpatialLLMClient
from app.services.layout_reasoning.agents.prompts import SUMMARY_AGENT_PROMPT, SYSTEM_PROMPT, format_json
from app.services.layout_reasoning.agents.schemas import (
    AgentOutput,
    AgentReport,
    AgentSuggestion,
    CoordinatorTask,
    ScoreDimensions,
)


CATEGORY_RANK = {
    "Safety": 0,
    "Accessibility": 1,
    "Layout": 2,
    "Lifestyle": 3,
    "Decoration": 4,
}

PRIORITY_RANK = {"High": 0, "Medium": 1, "Low": 2}


async def run_summary_agent(
    *,
    layout: AgentOutput,
    lifestyle: AgentOutput,
    task: CoordinatorTask,
    geometry_status: str,
    llm: SpatialLLMClient,
) -> AgentReport:
    if llm.is_live:
        try:
            raw = await llm.complete_json(
                system=SYSTEM_PROMPT,
                user=SUMMARY_AGENT_PROMPT.format(
                    layout_result=format_json(layout.model_dump()),
                    lifestyle_result=format_json(lifestyle.model_dump()),
                    geometry_status=geometry_status,
                ),
            )
            return _parse_report(raw, layout=layout, lifestyle=lifestyle, task=task)
        except Exception:
            pass
    return _deterministic_summary(
        layout=layout,
        lifestyle=lifestyle,
        task=task,
        geometry_status=geometry_status,
    )


def _parse_report(
    raw: dict[str, Any],
    *,
    layout: AgentOutput,
    lifestyle: AgentOutput,
    task: CoordinatorTask,
) -> AgentReport:
    dims_raw = raw.get("scoreDimensions") or {}
    suggestions: list[AgentSuggestion] = []
    for index, item in enumerate(raw.get("suggestions") or [], start=1):
        if not isinstance(item, dict):
            continue
        suggestions.append(
            AgentSuggestion(
                id=str(item.get("id") or f"summary_{index:03d}"),
                category=str(item.get("category") or "Layout"),
                priority=str(item.get("priority") or "Medium"),
                title=str(item.get("title") or "Suggestion"),
                reason=str(item.get("reason") or ""),
                action=str(item.get("action") or ""),
                confidence=float(item.get("confidence") or 0.8),
            )
        )
    if not suggestions:
        suggestions = merge_and_rank([*layout.suggestions, *lifestyle.suggestions])[:5]

    return AgentReport(
        score=int(raw.get("score") or 70),
        scoreDimensions=ScoreDimensions(
            layout=int(dims_raw.get("layout") or 70),
            comfort=int(dims_raw.get("comfort") or 70),
            functionality=int(dims_raw.get("functionality") or 70),
            lifestyleCompatibility=int(dims_raw.get("lifestyleCompatibility") or 70),
        ),
        summary=str(raw.get("summary") or "Room advice generated."),
        highlights=[str(h) for h in (raw.get("highlights") or [])][:5],
        suggestions=suggestions[:5],
        agentOutputs=[layout, lifestyle],
        coordinator=task,
    )


def _deterministic_summary(
    *,
    layout: AgentOutput,
    lifestyle: AgentOutput,
    task: CoordinatorTask,
    geometry_status: str,
) -> AgentReport:
    merged = merge_and_rank([*layout.suggestions, *lifestyle.suggestions])
    top5 = merged[:5]
    dims = _score_dimensions(task, geometry_status)
    score = int(round(sum(dims.model_dump().values()) / 4))

    candidate = str((task.candidate or {}).get("name") or "furniture")
    fail_count = sum(1 for c in task.geometryChecks if c.get("status") == "fail")
    warn_count = sum(1 for c in task.geometryChecks if c.get("status") == "warn")

    if geometry_status == "pass":
        summary = (
            f"The placement of {candidate} is geometrically feasible. "
            f"Multi-agent review found {len(top5)} practical improvement(s)."
        )
    else:
        summary = (
            f"The placement of {candidate} has {fail_count} hard issue(s) and {warn_count} warning(s). "
            f"Prioritize safety and accessibility before lifestyle refinements."
        )

    highlights: list[str] = []
    if geometry_status == "pass":
        highlights.append("Basic spatial feasibility checks passed.")
    if any(s.category == "Lifestyle" for s in lifestyle.suggestions):
        highlights.append("Lifestyle preferences were considered in the final ranking.")
    if any(s.priority == "Low" and s.category == "Layout" for s in layout.suggestions):
        highlights.append("Core layout remains usable with only minor refinements.")
    if not highlights:
        highlights.append("Suggestions are grounded in geometry checks and user profile.")

    return AgentReport(
        score=score,
        scoreDimensions=dims,
        summary=summary,
        highlights=highlights[:5],
        suggestions=top5,
        agentOutputs=[layout, lifestyle],
        coordinator=task,
    )


def merge_and_rank(suggestions: list[AgentSuggestion]) -> list[AgentSuggestion]:
    deduped: list[AgentSuggestion] = []
    seen_keys: set[str] = set()
    for item in suggestions:
        key = _dedupe_key(item)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(item)

    deduped.sort(
        key=lambda s: (
            CATEGORY_RANK.get(s.category, 99),
            PRIORITY_RANK.get(s.priority, 99),
            -s.confidence,
            s.title,
        )
    )
    return deduped


def _dedupe_key(item: AgentSuggestion) -> str:
    text = f"{item.title} {item.action}".lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", text)
    tokens = [t for t in text.split() if len(t) > 1][:8]
    return " ".join(tokens) or item.id


def _score_dimensions(task: CoordinatorTask, geometry_status: str) -> ScoreDimensions:
    layout = 88
    comfort = 80
    functionality = 82
    lifestyle = 78

    for check in task.geometryChecks:
        status = check.get("status")
        rule = check.get("ruleId")
        penalty = 25 if status == "fail" else 10 if status == "warn" else 0
        if rule == "fit":
            layout -= penalty
            functionality -= penalty // 2
        elif rule == "collision":
            layout -= penalty
            comfort -= penalty // 2
        elif rule == "accessibility":
            functionality -= penalty
            comfort -= penalty // 2
        elif rule == "clearance":
            comfort -= penalty
            functionality -= penalty // 2

    profile = task.userProfile or {}
    if profile.get("pets"):
        lifestyle += 6
    if profile.get("hasChildren") or profile.get("hasElderly"):
        lifestyle += 4
        if geometry_status != "pass":
            lifestyle -= 8

    def clamp(value: int) -> int:
        return max(0, min(100, value))

    return ScoreDimensions(
        layout=clamp(layout),
        comfort=clamp(comfort),
        functionality=clamp(functionality),
        lifestyleCompatibility=clamp(lifestyle),
    )
