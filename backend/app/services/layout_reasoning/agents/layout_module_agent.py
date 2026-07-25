"""Layout Agent: Chinese layout advices only (no lifestyle/scenario content)."""

from __future__ import annotations

from typing import Any

from app.schemas import FurnitureMove, LayoutAdviceItem
from app.services.layout_reasoning.agents.llm_client import SpatialLLMClient
from app.services.layout_reasoning.agents.prompts import LAYOUT_MODULE_PROMPT, SYSTEM_PROMPT, format_json


PRIORITY_MAP = {
    "high": "高",
    "medium": "中",
    "low": "低",
    "高": "高",
    "中": "中",
    "低": "低",
}


async def run_layout_module_agent(
    *,
    task_json: dict[str, Any],
    moves: list[FurnitureMove],
    llm: SpatialLLMClient,
) -> tuple[str, list[LayoutAdviceItem]]:
    """Return (summary, advices) in Chinese."""
    if llm.is_live:
        try:
            raw = await llm.complete_json(
                system=SYSTEM_PROMPT,
                user=LAYOUT_MODULE_PROMPT.format(
                    task_json=format_json(task_json),
                    moves_json=format_json([m.model_dump() for m in moves]),
                ),
            )
            return _parse_layout_module(raw)
        except Exception:
            pass
    return _mock_layout_module(task_json, moves)


def _parse_layout_module(raw: dict[str, Any]) -> tuple[str, list[LayoutAdviceItem]]:
    summary = str(raw.get("summary") or "已完成布局优化建议。")
    advices: list[LayoutAdviceItem] = []
    for index, item in enumerate(raw.get("advices") or [], start=1):
        if not isinstance(item, dict):
            continue
        priority = str(item.get("priority") or "中")
        priority = PRIORITY_MAP.get(priority.lower(), PRIORITY_MAP.get(priority, "中"))
        advices.append(
            LayoutAdviceItem(
                id=str(item.get("id") or f"layout_{index:03d}"),
                priority=priority,
                title=str(item.get("title") or "布局建议"),
                problem=str(item.get("problem") or item.get("reason") or ""),
                suggestion=str(item.get("suggestion") or item.get("action") or ""),
                relatedObjectIds=[str(x) for x in (item.get("relatedObjectIds") or [])],
            )
        )
    return summary, advices[:5]


def _mock_layout_module(
    task_json: dict[str, Any],
    moves: list[FurnitureMove],
) -> tuple[str, list[LayoutAdviceItem]]:
    candidate = task_json.get("candidate") or {}
    name = str(candidate.get("name") or "家具")
    checks = task_json.get("geometryChecks") or []
    advices: list[LayoutAdviceItem] = []
    idx = 1
    for check in checks:
        status = str(check.get("status") or "pass")
        if status == "pass":
            continue
        rule = str(check.get("ruleId") or "layout")
        title_map = {
            "fit": f"调整{name}使其完全位于房间内",
            "collision": f"消除{name}与其他家具的重叠",
            "accessibility": f"避开门窗开启区域放置{name}",
            "clearance": f"为{name}补充活动净空",
        }
        advices.append(
            LayoutAdviceItem(
                id=f"layout_{idx:03d}",
                priority="高" if status == "fail" else "中",
                title=title_map.get(rule, f"优化{name}布局"),
                problem=str(check.get("message") or "存在布局问题"),
                suggestion=str(check.get("suggestion") or "请调整摆放位置后重试。"),
                relatedObjectIds=[str(candidate.get("id") or "")],
            )
        )
        idx += 1

    if not advices:
        advices.append(
            LayoutAdviceItem(
                id="layout_001",
                priority="低",
                title=f"{name}当前位置几何可行",
                problem="空间适配、碰撞、门窗可达性与活动空间检测均通过。",
                suggestion="可保持当前位置，必要时微调朝向以改善视觉平衡与动线。",
                relatedObjectIds=[str(candidate.get("id") or "")],
            )
        )

    if moves:
        summary = f"{name}存在布局问题，已给出建议移动位置与优化建议。"
    else:
        summary = f"{name}布局基本合理，可按建议做轻度优化。"
    return summary, advices[:5]
