"""Whole-room layout pipeline (no single candidate required)."""

from __future__ import annotations

from typing import Any

from app.schemas import (
    FurnitureMove,
    LayoutAdviceItem,
    LayoutModule,
    ObjectCheckBundle,
    PlacementCandidate,
    RoomLayoutResponse,
    SceneObject,
    SceneResponse,
)
from app.services.layout_reasoning.agents.llm_client import SpatialLLMClient
from app.services.layout_reasoning.agents.phase1 import create_llm_client, get_scenario_options
from app.services.layout_reasoning.agents.prompts import ROOM_LAYOUT_PROMPT, SYSTEM_PROMPT, format_json
from app.services.layout_reasoning.propose_moves import propose_moves_from_geometry
from app.services.layout_reasoning.rules_loader import is_solid_furniture
from app.services.layout_reasoning.spatial_check import run_spatial_check


PRIORITY_MAP = {
    "high": "高",
    "medium": "中",
    "low": "低",
    "高": "高",
    "中": "中",
    "低": "低",
}


def _object_as_candidate(obj: SceneObject) -> PlacementCandidate:
    return PlacementCandidate(
        id=obj.id,
        label=obj.label,
        name=obj.name,
        position=list(obj.position),
        rotation=list(obj.rotation),
        size=list(obj.size),
    )


def analyze_room_geometry(
    scene: SceneResponse,
) -> tuple[list[ObjectCheckBundle], list[FurnitureMove], str, str]:
    """Run per-object geometry checks and collect move proposals."""
    bundles: list[ObjectCheckBundle] = []
    moves: list[FurnitureMove] = []
    fail = 0
    warn = 0

    solids = [obj for obj in scene.objects if is_solid_furniture(obj.label)]
    for obj in solids:
        candidate = _object_as_candidate(obj)
        result = run_spatial_check(candidate, scene)
        bundles.append(
            ObjectCheckBundle(
                objectId=obj.id,
                name=obj.name,
                label=obj.label,
                overallStatus=result.overallStatus,
                checks=result.checks,
            )
        )
        if result.overallStatus == "fail":
            fail += 1
        elif result.overallStatus == "warn":
            warn += 1
        moves.extend(propose_moves_from_geometry(candidate, scene, result.checks))

    if fail:
        status = "fail"
        feedback = f"全屋检测发现 {fail} 件家具存在硬冲突（碰撞/堵门/越界等），建议优先调整。"
    elif warn:
        status = "warn"
        feedback = f"全屋检测发现 {warn} 件家具存在净空不足等警告，建议优化活动空间。"
    else:
        status = "pass"
        feedback = "全屋主要家具的基础几何检测均通过，可继续做布局优化与场景建议。"
    return bundles, moves, status, feedback


def build_room_task_json(
    scene: SceneResponse,
    bundles: list[ObjectCheckBundle],
) -> dict[str, Any]:
    return {
        "mode": "room",
        "sceneId": scene.sceneId,
        "unit": scene.unit,
        "room": scene.room.model_dump(),
        "furniture": [obj.model_dump() for obj in scene.objects],
        "openings": [op.model_dump() for op in scene.openings],
        "objectChecks": [
            {
                "objectId": b.objectId,
                "name": b.name,
                "label": b.label,
                "overallStatus": b.overallStatus,
                "issues": [
                    {
                        "ruleId": c.ruleId,
                        "status": c.status,
                        "message": c.message,
                        "suggestion": c.suggestion,
                    }
                    for c in b.checks
                    if c.status != "pass"
                ],
            }
            for b in bundles
        ],
    }


async def run_room_layout_agent(
    *,
    task_json: dict[str, Any],
    moves: list[FurnitureMove],
    llm: SpatialLLMClient,
) -> tuple[str, list[LayoutAdviceItem], list[FurnitureMove]]:
    if llm.is_live:
        try:
            raw = await llm.complete_json(
                system=SYSTEM_PROMPT,
                user=ROOM_LAYOUT_PROMPT.format(
                    task_json=format_json(task_json),
                    moves_json=format_json([m.model_dump() for m in moves]),
                ),
            )
            return _parse_room_layout(raw)
        except Exception:
            pass
    return _mock_room_layout(task_json, moves)


def _parse_room_layout(
    raw: dict[str, Any],
) -> tuple[str, list[LayoutAdviceItem], list[FurnitureMove]]:
    summary = str(raw.get("summary") or "已完成全屋布局优化建议。")
    advices: list[LayoutAdviceItem] = []
    for index, item in enumerate(raw.get("advices") or [], start=1):
        if not isinstance(item, dict):
            continue
        priority = str(item.get("priority") or "中")
        priority = PRIORITY_MAP.get(priority.lower(), PRIORITY_MAP.get(priority, "中"))
        advices.append(
            LayoutAdviceItem(
                id=str(item.get("id") or f"room_{index:03d}"),
                priority=priority,
                title=str(item.get("title") or "全屋布局建议"),
                problem=str(item.get("problem") or ""),
                suggestion=str(item.get("suggestion") or ""),
                relatedObjectIds=[str(x) for x in (item.get("relatedObjectIds") or [])],
            )
        )

    extra_moves: list[FurnitureMove] = []
    for item in raw.get("extraMoves") or []:
        if not isinstance(item, dict):
            continue
        from_pos = item.get("fromPosition")
        to_pos = item.get("toPosition")
        if not (isinstance(from_pos, list) and isinstance(to_pos, list) and len(from_pos) == 3 and len(to_pos) == 3):
            continue
        try:
            extra_moves.append(
                FurnitureMove(
                    objectId=str(item.get("objectId") or ""),
                    name=str(item.get("name") or item.get("objectId") or "家具"),
                    fromPosition=[float(from_pos[0]), float(from_pos[1]), float(from_pos[2])],
                    toPosition=[float(to_pos[0]), float(to_pos[1]), float(to_pos[2])],
                    reason=str(item.get("reason") or "布局优化建议移动"),
                    source="layout_agent",
                )
            )
        except (TypeError, ValueError):
            continue
    return summary, advices[:6], extra_moves[:4]


def _mock_room_layout(
    task_json: dict[str, Any],
    moves: list[FurnitureMove],
) -> tuple[str, list[LayoutAdviceItem], list[FurnitureMove]]:
    advices: list[LayoutAdviceItem] = []
    idx = 1
    for bundle in task_json.get("objectChecks") or []:
        issues = bundle.get("issues") or []
        if not issues:
            continue
        names = bundle.get("name") or bundle.get("objectId")
        first = issues[0]
        advices.append(
            LayoutAdviceItem(
                id=f"room_{idx:03d}",
                priority="高" if bundle.get("overallStatus") == "fail" else "中",
                title=f"优化{names}的摆放",
                problem=str(first.get("message") or "存在布局问题"),
                suggestion=str(first.get("suggestion") or "请调整该家具位置后重试。"),
                relatedObjectIds=[str(bundle.get("objectId") or "")],
            )
        )
        idx += 1
        if idx > 6:
            break

    if not advices:
        advices.append(
            LayoutAdviceItem(
                id="room_001",
                priority="低",
                title="全屋布局基本合理",
                problem="主要家具未发现硬性几何冲突。",
                suggestion="可保持现有分区；若需增强动线，优先疏通门到沙发/餐桌主通道。",
                relatedObjectIds=[],
            )
        )

    if moves:
        summary = f"全屋发现 {len(moves)} 处建议移动，并已给出布局优化建议。"
    else:
        summary = "全屋布局整体可行，可按建议做轻度优化或继续选择生活场景。"
    return summary, advices, []


async def run_room_layout(
    *,
    scene: SceneResponse,
    llm: SpatialLLMClient | None = None,
    enable_agents: bool = True,
) -> RoomLayoutResponse:
    client = llm or create_llm_client()
    bundles, geo_moves, status, feedback = analyze_room_geometry(scene)
    layout = None
    if enable_agents:
        task_json = build_room_task_json(scene, bundles)
        summary, advices, extra_moves = await run_room_layout_agent(
            task_json=task_json,
            moves=geo_moves,
            llm=client,
        )
        # Deduplicate moves by objectId (geometry first, then agent extras)
        merged: dict[str, FurnitureMove] = {m.objectId: m for m in geo_moves}
        for m in extra_moves:
            if m.objectId and m.objectId not in merged:
                merged[m.objectId] = m
        layout = LayoutModule(
            moves=list(merged.values()),
            advices=advices,
            summary=summary or feedback,
        )

    return RoomLayoutResponse(
        mode="room",
        overallStatus=status,
        objectChecks=bundles,
        feedback=feedback,
        layout=layout,
        scenarioOptions=get_scenario_options(),
    )
