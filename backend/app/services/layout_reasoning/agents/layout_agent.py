"""Layout Agent: spatial geometry / usability suggestions only."""

from __future__ import annotations

from app.services.layout_reasoning.agents.llm_client import SpatialLLMClient
from app.services.layout_reasoning.agents.prompts import LAYOUT_AGENT_PROMPT, SYSTEM_PROMPT, format_json
from app.services.layout_reasoning.agents.schemas import AgentOutput, AgentSuggestion, CoordinatorTask


async def run_layout_agent(task: CoordinatorTask, llm: SpatialLLMClient) -> AgentOutput:
    if llm.is_live:
        try:
            raw = await llm.complete_json(
                system=SYSTEM_PROMPT,
                user=LAYOUT_AGENT_PROMPT.format(task_json=format_json(task.model_dump())),
            )
            return _parse_output(raw, agent="layout")
        except Exception:
            pass
    return _mock_layout_output(task)


def _parse_output(raw: dict, *, agent: str) -> AgentOutput:
    suggestions: list[AgentSuggestion] = []
    for index, item in enumerate(raw.get("suggestions") or [], start=1):
        if not isinstance(item, dict):
            continue
        suggestions.append(
            AgentSuggestion(
                id=str(item.get("id") or f"{agent}_{index:03d}"),
                category=str(item.get("category") or "Layout"),
                priority=str(item.get("priority") or "Medium"),
                title=str(item.get("title") or "Layout suggestion"),
                reason=str(item.get("reason") or ""),
                action=str(item.get("action") or item.get("recommendation") or ""),
                confidence=float(item.get("confidence") or 0.8),
            )
        )
    return AgentOutput(agent=agent, suggestions=suggestions)


def _mock_layout_output(task: CoordinatorTask) -> AgentOutput:
    suggestions: list[AgentSuggestion] = []
    candidate_name = str((task.candidate or {}).get("name") or "furniture")
    idx = 1

    for check in task.geometryChecks:
        status = str(check.get("status") or "pass")
        if status == "pass":
            continue
        rule_id = str(check.get("ruleId") or "layout")
        category = {
            "fit": "Layout",
            "collision": "Safety",
            "accessibility": "Accessibility",
            "clearance": "Accessibility",
        }.get(rule_id, "Layout")
        priority = "High" if status == "fail" else "Medium"
        message = str(check.get("message") or "Spatial issue detected")
        suggestion = str(check.get("suggestion") or "Adjust furniture position and re-check.")
        suggestions.append(
            AgentSuggestion(
                id=f"layout_{idx:03d}",
                category=category,
                priority=priority,
                title=f"Resolve {rule_id} issue for {candidate_name}",
                reason=message,
                action=suggestion,
                confidence=0.95 if status == "fail" else 0.85,
            )
        )
        idx += 1

    if not suggestions:
        suggestions.append(
            AgentSuggestion(
                id="layout_001",
                category="Layout",
                priority="Low",
                title=f"{candidate_name} placement is geometrically feasible",
                reason="Fit, collision, accessibility, and clearance checks all passed.",
                action="Keep current position; optionally refine orientation for visual balance.",
                confidence=0.9,
            )
        )

    return AgentOutput(agent="layout", suggestions=suggestions)
