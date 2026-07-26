from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.services.layout_reasoning.agents.llm_client import SpatialLLMClient
from app.storage.local_store import BACKEND_ROOT


SKILLS_ROOT = BACKEND_ROOT / "sample_data" / "skills"
SCENARIOS = {
    "children": {
        "name": "儿童友好",
        "description": "优先检查防倾倒、跌落、夹困、触电与照护动线。",
        "skill": "adapt-home-for-children",
        "references": ["json-contract.md", "child-safety-rules.md", "geometry-and-safety.md"],
    },
    "pets": {
        "name": "宠物友好",
        "description": "检查防逃逸、误食、抓咬、清洁与休息活动分区。",
        "skill": "adapt-home-for-pets",
        "references": ["json-contract.md", "pet-safety-rules.md", "geometry-and-safety.md"],
    },
    "fengshui": {
        "name": "风水与动线",
        "description": "在空间可用和安全优先的前提下给出低成本可逆微调。",
        "skill": "analyze-home-fengshui",
        "references": ["json-contract.md", "fengshui-rules.md", "geometry-and-safety.md"],
    },
    "other": {
        "name": "其他需求",
        "description": "依据用户自由填写的目标，结合当前空间事实给出通用、可执行的建议。",
        "skill": "general-home-advice",
        "references": [],
    },
}


def scenario_options() -> list[dict[str, str]]:
    return [
        {"id": key, "name": value["name"], "description": value["description"]}
        for key, value in SCENARIOS.items()
    ]


def missing_fields(floorplan: dict[str, Any], scenario_id: str, profile: dict[str, Any]) -> list[str]:
    snapshot = floorplan.get("userSnapshot") or {}
    room = snapshot.get("room") or {}
    objects = snapshot.get("objects") or []
    missing: list[str] = []
    if not room.get("openings"):
        missing.append("门窗的结构化位置、尺寸、开启方向和净空区")
    if not objects:
        missing.append("当前场景家具")
    if any(not (item.get("semantic") or {}).get("materials") for item in objects):
        missing.append("部分家具的材质、边角、固定方式等安全属性")
    if any(((item.get("source") or {}).get("type") in {"feed", "library"}) for item in objects):
        missing.append("新增家具尺寸是否为现场实测值")
    if scenario_id == "children":
        if not profile.get("ageRange"):
            missing.append("儿童年龄段")
        if not profile.get("mobilityStage"):
            missing.append("儿童行动阶段")
    elif scenario_id == "pets":
        if not profile.get("species"):
            missing.append("宠物物种")
        if not profile.get("behaviors"):
            missing.append("宠物抓咬、攀爬或逃逸等行为")
    elif scenario_id == "fengshui" and not profile.get("focus"):
        missing.append("本次最希望改善的区域或体验")
    elif scenario_id == "other" and not profile.get("extraRequest"):
        missing.append("其他需求的具体目标")
    return missing


def _skill_prompt(scenario_id: str) -> str:
    config = SCENARIOS[scenario_id]
    skill_root = SKILLS_ROOT / config["skill"]
    parts = [(skill_root / "SKILL.md").read_text(encoding="utf-8")]
    for name in config["references"]:
        path = skill_root / "references" / name
        if path.is_file():
            parts.append(f"\n# Reference: {name}\n{path.read_text(encoding='utf-8')}")
    return "\n".join(parts)


async def generate_skill_advice(
    *, floorplan: dict[str, Any], scenario_id: str, profile: dict[str, Any]
) -> dict[str, Any]:
    if scenario_id not in SCENARIOS:
        raise ValueError(f"Unsupported advice scenario: {scenario_id}")
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")

    gaps = missing_fields(floorplan, scenario_id, profile)
    expected = {
        "summary": "2-4句总体判断",
        "suggestions": [{
            "priority": "P0|P1|P2|P3", "title": "标题", "reason": "依据",
            "action": "具体且可执行的动作", "relatedObjectIds": ["家具ID"],
        }],
        "followUpQuestions": ["最多3个会改变建议的问题"],
    }
    system = _skill_prompt(scenario_id) + (
        "\n\n你正在为网页生成建议。严格遵守以上技能边界。只返回一个 JSON 对象，"
        "当 selectedScenario 为“其他需求”时，userProfile.extraRequest 是本次分析的主要目标，"
        "不要套用儿童、宠物或风水预设。"
        "不要 Markdown，不要声称未验证的事实，不要直接改写户型。输出结构示例：\n"
        + json.dumps(expected, ensure_ascii=False)
    )
    analysis_floorplan = deepcopy(floorplan)
    floorplan_model = analysis_floorplan.get("floorplan")
    if isinstance(floorplan_model, dict):
        floorplan_model.pop("glbBase64", None)
    user = json.dumps({
        "selectedScenario": SCENARIOS[scenario_id],
        "userProfile": profile,
        "knownMissingFields": gaps,
        "floorplan": analysis_floorplan,
    }, ensure_ascii=False)
    client = SpatialLLMClient(
        provider="deepseek", api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url, model=settings.deepseek_model,
        timeout=settings.skill_advice_timeout_sec,
    )
    result = await client.complete_json(system=system, user=user)
    suggestions = result.get("suggestions")
    if not isinstance(result.get("summary"), str) or not isinstance(suggestions, list):
        raise ValueError("AI response is missing summary or suggestions")
    normalized = []
    for index, item in enumerate(suggestions[:8]):
        if not isinstance(item, dict):
            continue
        normalized.append({
            "id": str(item.get("id") or f"{scenario_id}_{index + 1}"),
            "priority": str(item.get("priority") or "P2"),
            "title": str(item.get("title") or "空间建议"),
            "reason": str(item.get("reason") or ""),
            "action": str(item.get("action") or ""),
            "relatedObjectIds": [str(value) for value in item.get("relatedObjectIds", []) if value],
        })
    return {
        "scenarioId": scenario_id,
        "scenarioName": SCENARIOS[scenario_id]["name"],
        "skillName": SCENARIOS[scenario_id]["skill"],
        "provider": "deepseek",
        "model": settings.deepseek_model,
        "summary": result["summary"],
        "suggestions": normalized,
        "missingFields": gaps,
        "followUpQuestions": [str(value) for value in result.get("followUpQuestions", [])][:3],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
