"""Orchestrate Coordinator -> Layout/Lifestyle (parallel) -> Summary."""

from __future__ import annotations

import asyncio
from typing import Any

from app.config import get_settings
from app.schemas import CheckDetail, PlacementCandidate, SceneResponse
from app.services.layout_reasoning.agents.coordinator import run_coordinator
from app.services.layout_reasoning.agents.layout_agent import run_layout_agent
from app.services.layout_reasoning.agents.lifestyle_agent import default_user_profile, run_lifestyle_agent
from app.services.layout_reasoning.agents.llm_client import SpatialLLMClient
from app.services.layout_reasoning.agents.schemas import AgentReport
from app.services.layout_reasoning.agents.summary_agent import run_summary_agent


def build_house_json(
    candidate: PlacementCandidate,
    scene: SceneResponse,
    checks: list[CheckDetail],
    user_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Upstream JSON consumed by the Coordinator Agent."""
    return {
        "sceneId": scene.sceneId,
        "unit": scene.unit,
        "room": scene.room.model_dump(),
        "furniture": [obj.model_dump() for obj in scene.objects],
        "openings": [op.model_dump() for op in scene.openings],
        "candidate": candidate.model_dump(),
        "geometryChecks": [check.model_dump() for check in checks],
        "userProfile": default_user_profile(user_profile),
    }


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


async def run_multi_agent_advice(
    *,
    candidate: PlacementCandidate,
    scene: SceneResponse,
    checks: list[CheckDetail],
    geometry_status: str,
    user_profile: dict[str, Any] | None = None,
    llm: SpatialLLMClient | None = None,
) -> AgentReport:
    """Run the full multi-agent advice pipeline after geometry checks."""
    client = llm or create_llm_client()
    house_json = build_house_json(candidate, scene, checks, user_profile)
    task = await run_coordinator(house_json, client)
    layout, lifestyle = await asyncio.gather(
        run_layout_agent(task, client),
        run_lifestyle_agent(task, client),
    )
    return await run_summary_agent(
        layout=layout,
        lifestyle=lifestyle,
        task=task,
        geometry_status=geometry_status,
        llm=client,
    )
