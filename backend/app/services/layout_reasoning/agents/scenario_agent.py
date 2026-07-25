"""Scenario Agent: elder / infant / pet / fengshui advice in Chinese."""

from __future__ import annotations

import asyncio
from typing import Any

from app.schemas import (
    CheckDetail,
    LayoutModule,
    PlacementCandidate,
    ScenarioAdviceItem,
    ScenarioAdviceResponse,
    SceneResponse,
    UserProfile,
)
from app.services.layout_reasoning.agents.llm_client import SpatialLLMClient
from app.services.layout_reasoning.agents.phase1 import build_task_json, create_llm_client
from app.services.layout_reasoning.agents.prompts import (
    SCENARIO_AGENT_PROMPT,
    SCENARIO_CATALOG,
    SYSTEM_PROMPT,
    format_json,
)


PRIORITY_MAP = {
    "high": "高",
    "medium": "中",
    "low": "低",
    "高": "高",
    "中": "中",
    "低": "低",
}

VALID_SCENARIOS = set(SCENARIO_CATALOG.keys())


async def run_scenario_advice(
    *,
    scenarios: list[str],
    scene: SceneResponse,
    candidate: PlacementCandidate | None = None,
    mode: str = "placement",
    layout: LayoutModule | None = None,
    geometry_checks: list[CheckDetail] | None = None,
    user_profile: UserProfile | dict[str, Any] | None = None,
    llm: SpatialLLMClient | None = None,
) -> ScenarioAdviceResponse:
    mode_key = (mode or "placement").strip().lower()
    if mode_key not in {"placement", "room"}:
        raise ValueError("mode 仅支持 placement 或 room")
    if mode_key == "placement" and candidate is None:
        raise ValueError("单家具模式（placement）必须提供 candidate")

    selected = []
    for item in scenarios:
        key = str(item).strip().lower()
        if key in VALID_SCENARIOS and key not in selected:
            selected.append(key)
    if not selected:
        raise ValueError("未选择有效场景，可选：elder / infant / pet / fengshui")

    client = llm or create_llm_client()
    checks = geometry_checks or []
    if candidate is not None:
        task_json = build_task_json(candidate, scene, checks)
    else:
        task_json = {
            "mode": "room",
            "sceneId": scene.sceneId,
            "unit": scene.unit,
            "room": scene.room.model_dump(),
            "furniture": [obj.model_dump() for obj in scene.objects],
            "openings": [op.model_dump() for op in scene.openings],
            "geometryChecks": [c.model_dump() for c in checks],
            "candidate": None,
        }
    task_json["mode"] = mode_key
    if user_profile is not None:
        if hasattr(user_profile, "model_dump"):
            task_json["userProfile"] = user_profile.model_dump()  # type: ignore[union-attr]
        elif isinstance(user_profile, dict):
            task_json["userProfile"] = user_profile

    layout_dump = layout.model_dump() if layout else {"moves": [], "advices": [], "summary": ""}

    results = await asyncio.gather(
        *[_run_one_scenario(sid, task_json, layout_dump, client) for sid in selected]
    )

    advices_by_scenario: dict[str, list[ScenarioAdviceItem]] = {}
    summaries: list[str] = []
    for sid, summary, advices in results:
        advices_by_scenario[sid] = advices
        if summary:
            summaries.append(f"{SCENARIO_CATALOG[sid]['name']}：{summary}")

    overall = "；".join(summaries) if summaries else "已生成所选场景的修改建议。"
    return ScenarioAdviceResponse(
        selectedScenarios=selected,
        mode=mode_key,
        advicesByScenario=advices_by_scenario,
        summary=overall,
    )


async def _run_one_scenario(
    scenario_id: str,
    task_json: dict[str, Any],
    layout_json: dict[str, Any],
    llm: SpatialLLMClient,
) -> tuple[str, str, list[ScenarioAdviceItem]]:
    meta = SCENARIO_CATALOG[scenario_id]
    if llm.is_live:
        try:
            raw = await llm.complete_json(
                system=SYSTEM_PROMPT,
                user=SCENARIO_AGENT_PROMPT.format(
                    scenario_name=meta["name"],
                    scenario_description=meta["description"],
                    scenario_focus=meta["focus"],
                    scenario_id=scenario_id,
                    mode_label="全屋布局" if task_json.get("mode") == "room" else "单家具摆放",
                    task_json=format_json(task_json),
                    layout_json=format_json(layout_json),
                ),
            )
            summary, advices = _parse_scenario(raw, scenario_id)
            return scenario_id, summary, advices
        except Exception:
            pass
    summary, advices = _mock_scenario(scenario_id, task_json, layout_json)
    return scenario_id, summary, advices


def _parse_scenario(raw: dict[str, Any], scenario_id: str) -> tuple[str, list[ScenarioAdviceItem]]:
    summary = str(raw.get("summary") or f"已完成{SCENARIO_CATALOG[scenario_id]['name']}场景建议。")
    advices: list[ScenarioAdviceItem] = []
    for index, item in enumerate(raw.get("advices") or [], start=1):
        if not isinstance(item, dict):
            continue
        priority = str(item.get("priority") or "中")
        priority = PRIORITY_MAP.get(priority.lower(), PRIORITY_MAP.get(priority, "中"))
        target = item.get("targetPosition")
        target_pos = None
        if isinstance(target, list) and len(target) == 3:
            try:
                target_pos = [float(target[0]), float(target[1]), float(target[2])]
            except (TypeError, ValueError):
                target_pos = None
        advices.append(
            ScenarioAdviceItem(
                id=str(item.get("id") or f"{scenario_id}_{index:03d}"),
                scenarioId=scenario_id,
                priority=priority,
                title=str(item.get("title") or "场景建议"),
                reason=str(item.get("reason") or ""),
                action=str(item.get("action") or item.get("suggestion") or ""),
                relatedObjectIds=[str(x) for x in (item.get("relatedObjectIds") or [])],
                targetPosition=target_pos,
            )
        )
    return summary, advices[:5]


def _mock_scenario(
    scenario_id: str,
    task_json: dict[str, Any],
    layout_json: dict[str, Any],
) -> tuple[str, list[ScenarioAdviceItem]]:
    candidate = task_json.get("candidate") or {}
    name = str(candidate.get("name") or "主要家具")
    cand_id = str(candidate.get("id") or "")
    mode = str(task_json.get("mode") or "placement")
    openings = task_json.get("openings") or []
    window_ids = [str(o.get("id")) for o in openings if str(o.get("type") or "").lower() == "window"]
    door_ids = [str(o.get("id")) for o in openings if str(o.get("type") or "").lower() == "door"]
    furniture_ids = [str(o.get("id")) for o in (task_json.get("furniture") or [])][:4]

    templates = {
        "elder": [
            ScenarioAdviceItem(
                id="elder_001",
                scenarioId="elder",
                priority="高",
                title="保证座位前方起身净空",
                reason="老人起身与转身需要更充足的前方空间，降低跌倒风险。",
                action=f"若{name}靠近座位区，请至少留出 0.6 米前方净空，并避开门口堆物。",
                relatedObjectIds=[cand_id] if cand_id else furniture_ids,
                targetPosition=None,
            ),
            ScenarioAdviceItem(
                id="elder_002",
                scenarioId="elder",
                priority="高",
                title="保持主要通行路径连续",
                reason="适老化布局需要沙发、门与主要座位之间连续可达。",
                action="保留一条不少于 0.9 米宽的连续通道，避免家具边角侵入动线。",
                relatedObjectIds=door_ids or furniture_ids,
                targetPosition=None,
            ),
        ],
        "infant": [
            ScenarioAdviceItem(
                id="infant_001",
                scenarioId="infant",
                priority="高",
                title="设置儿童安全活动角",
                reason="集中活动区便于看护，也减少玩具散落造成的绊倒风险。",
                action="在远离门口的角落设置柔软活动区，并配置低矮收纳，避免占用主通道。",
                relatedObjectIds=[cand_id] if cand_id else furniture_ids,
                targetPosition=None,
            ),
            ScenarioAdviceItem(
                id="infant_002",
                scenarioId="infant",
                priority="中",
                title="避免高大家具压迫儿童通道",
                reason="儿童身高视野低，通道两侧应减少突出家具。",
                action=(
                    f"检查{name}是否挤占门到沙发的通道；若占用，向墙侧平移 20–40 cm。"
                    if mode == "placement"
                    else "检查门到沙发主通道两侧是否有高柜突出；必要时整体内收 20–40 cm。"
                ),
                relatedObjectIds=([cand_id, *door_ids] if cand_id else [*door_ids, *furniture_ids]),
                targetPosition=None,
            ),
        ],
        "pet": [
            ScenarioAdviceItem(
                id="pet_001",
                scenarioId="pet",
                priority="中",
                title="预留窗边宠物活动区",
                reason="猫狗通常偏好采光较好的窗边休息与观察。",
                action="在窗户内侧预留至少 1 平方米空地，避免高大柜体贴窗遮挡。",
                relatedObjectIds=window_ids or furniture_ids,
                targetPosition=None,
            ),
            ScenarioAdviceItem(
                id="pet_002",
                scenarioId="pet",
                priority="高",
                title="避免堵住门旁宠物通行",
                reason="宠物频繁穿行门区，门口障碍物易造成冲撞与夹伤风险。",
                action=(
                    f"勿将{name}放在门扇开启轨迹内，门口两侧至少留出 0.5 米通过宽度。"
                    if mode == "placement"
                    else "清理入户门与阳台门两侧障碍，门口通过宽度不少于 0.5 米。"
                ),
                relatedObjectIds=([cand_id, *door_ids] if cand_id else door_ids),
                targetPosition=None,
            ),
        ],
        "fengshui": [
            ScenarioAdviceItem(
                id="fengshui_001",
                scenarioId="fengshui",
                priority="中",
                title="保持入户视线通透",
                reason="入口正对高大遮挡会带来压迫感，影响空间气场与第一观感。",
                action="避免在入户门正前方摆放高于 1.5 米的柜体；可侧移形成斜向缓冲。",
                relatedObjectIds=door_ids or furniture_ids,
                targetPosition=None,
            ),
            ScenarioAdviceItem(
                id="fengshui_002",
                scenarioId="fengshui",
                priority="中",
                title="主座尽量背靠实墙",
                reason="沙发或主座背后有实墙更稳定，减少背后开门窗的不安感。",
                action="优先让主要座位靠实墙；若背后是门窗，建议旋转朝向或后移靠墙。",
                relatedObjectIds=[cand_id] if cand_id else furniture_ids,
                targetPosition=None,
            ),
        ],
    }

    advices = templates.get(scenario_id, [])
    # Mention layout moves if any
    moves = (layout_json or {}).get("moves") or []
    if moves and scenario_id in {"elder", "infant", "pet"}:
        move = moves[0]
        advices = [
            ScenarioAdviceItem(
                id=f"{scenario_id}_000",
                scenarioId=scenario_id,
                priority="高",
                title="先落实几何安全移动",
                reason="场景优化前应先消除碰撞/堵门等硬冲突。",
                action=f"请先将{move.get('name') or name}从 {move.get('fromPosition')} 调整到 {move.get('toPosition')}：{move.get('reason')}",
                relatedObjectIds=[str(move.get("objectId") or cand_id)],
                targetPosition=move.get("toPosition"),
            ),
            *advices,
        ]
    summary = f"围绕{SCENARIO_CATALOG[scenario_id]['name']}场景给出可执行调整建议。"
    return summary, advices[:5]
