"""Phase-1 layout module pipeline: geometry moves + Chinese layout advices."""

from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.schemas import (
    CheckDetail,
    LayoutModule,
    PlacementCandidate,
    ScenarioOption,
    SceneResponse,
)
from app.services.layout_reasoning.agents.layout_module_agent import run_layout_module_agent
from app.services.layout_reasoning.agents.llm_client import SpatialLLMClient
from app.services.layout_reasoning.agents.prompts import scenario_options
from app.services.layout_reasoning.propose_moves import propose_moves_from_geometry


def create_llm_client() -> SpatialLLMClient:
    settings = get_settings()
    provider = settings.spatial_agent_provider
    if provider == "ark" and not settings.ark_api_key:
        provider = "mock"
    return SpatialLLMClient(
        provider=provider,
        api_key=settings.ark_api_key,
        base_url=settings.ark_base_url,
        model=settings.ark_text_model,
        timeout=150.0,
    )


def build_task_json(
    candidate: PlacementCandidate,
    scene: SceneResponse,
    checks: list[CheckDetail],
) -> dict[str, Any]:
    return {
        "sceneId": scene.sceneId,
        "unit": scene.unit,
        "room": scene.room.model_dump(),
        "furniture": [obj.model_dump() for obj in scene.objects],
        "openings": [op.model_dump() for op in scene.openings],
        "candidate": candidate.model_dump(),
        "geometryChecks": [check.model_dump() for check in checks],
    }


def get_scenario_options() -> list[ScenarioOption]:
    return [ScenarioOption.model_validate(item) for item in scenario_options()]


async def run_layout_module(
    *,
    candidate: PlacementCandidate,
    scene: SceneResponse,
    checks: list[CheckDetail],
    llm: SpatialLLMClient | None = None,
) -> LayoutModule:
    """Build modular Chinese layout output for Phase 1."""
    client = llm or create_llm_client()
    moves = propose_moves_from_geometry(candidate, scene, checks)
    task_json = build_task_json(candidate, scene, checks)
    summary, advices = await run_layout_module_agent(task_json=task_json, moves=moves, llm=client)
    if not summary:
        if moves:
            summary = f"建议调整{candidate.name}位置，并参考布局优化建议。"
        else:
            summary = f"{candidate.name}布局基本可行，可继续选择生活场景获取专项建议。"
    return LayoutModule(moves=moves, advices=advices, summary=summary)
