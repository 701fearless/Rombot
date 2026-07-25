from fastapi import APIRouter, HTTPException

from app.schemas import (
    LayoutModule,
    PlacementCheckRequest,
    PlacementCheckResponse,
    RoomLayoutRequest,
    RoomLayoutResponse,
    RoomScanRequest,
    ScenarioAdviceRequest,
    ScenarioAdviceResponse,
    SceneResponse,
    SpatialCheckRequest,
    SpatialCheckResponse,
)
from app.services.layout_reasoning import run_spatial_check
from app.services.layout_reasoning.agents.phase1 import get_scenario_options, run_layout_module
from app.services.layout_reasoning.agents.room_layout import run_room_layout
from app.services.layout_reasoning.agents.scenario_agent import run_scenario_advice
from app.services.layout_reasoning.propose_moves import propose_moves_from_geometry
from app.services.room_scan.mock_scene import build_mock_scene


router = APIRouter()


def _resolve_scene(scene: SceneResponse | None, scene_id: str | None) -> SceneResponse:
    if scene is not None:
        return scene
    return build_mock_scene(scene_id=scene_id or "demo_living_room")


@router.post("/scan", response_model=SceneResponse)
async def scan_room(request: RoomScanRequest | None = None) -> SceneResponse:
    scan_id = request.scanId if request and request.scanId else "demo_living_room"
    return build_mock_scene(scene_id=scan_id)


async def _run_placement_check(request: PlacementCheckRequest) -> PlacementCheckResponse:
    scene = _resolve_scene(request.scene, request.sceneId)
    if scene.room.width <= 0 or scene.room.depth <= 0:
        raise HTTPException(status_code=400, detail="房间尺寸无效")
    if any(v <= 0 for v in request.candidate.size):
        raise HTTPException(status_code=400, detail="家具尺寸无效")

    result = run_spatial_check(request.candidate, scene)
    options = get_scenario_options()
    geometry_moves = propose_moves_from_geometry(
        request.candidate,
        scene,
        result.checks,
    )

    if request.enableAgents:
        layout = await run_layout_module(
            candidate=request.candidate,
            scene=scene,
            checks=result.checks,
        )
    else:
        layout = LayoutModule(
            moves=geometry_moves,
            advices=[],
            summary=result.feedback,
        )

    return PlacementCheckResponse(
        mode="placement",
        overallStatus=result.overallStatus,
        checks=result.checks,
        feedback=result.feedback,
        layout=layout,
        scenarioOptions=options,
        agentReport=None,
    )


@router.post("/placement-check", response_model=PlacementCheckResponse)
async def placement_check(request: PlacementCheckRequest) -> PlacementCheckResponse:
    """单家具摆放：几何四检 + 可选 Agent 文案。enableAgents=false 时仍返回几何 moves。"""
    return await _run_placement_check(request)


@router.post("/spatial-check", response_model=SpatialCheckResponse, deprecated=True)
async def spatial_check(request: SpatialCheckRequest) -> SpatialCheckResponse:
    """兼容旧接口，等价于 /placement-check。"""
    return await _run_placement_check(request)


@router.post("/room-layout", response_model=RoomLayoutResponse)
async def room_layout(request: RoomLayoutRequest) -> RoomLayoutResponse:
    scene = _resolve_scene(request.scene, request.sceneId)
    if scene.room.width <= 0 or scene.room.depth <= 0:
        raise HTTPException(status_code=400, detail="房间尺寸无效")
    if not scene.objects:
        raise HTTPException(status_code=400, detail="场景中没有家具，无法进行全屋布局分析")
    return await run_room_layout(scene=scene, enable_agents=request.enableAgents)


@router.post("/scenario-advice", response_model=ScenarioAdviceResponse)
async def scenario_advice(request: ScenarioAdviceRequest) -> ScenarioAdviceResponse:
    scene = _resolve_scene(request.scene, request.sceneId)
    if scene.room.width <= 0 or scene.room.depth <= 0:
        raise HTTPException(status_code=400, detail="房间尺寸无效")
    if request.candidate is not None and any(v <= 0 for v in request.candidate.size):
        raise HTTPException(status_code=400, detail="家具尺寸无效")

    try:
        return await run_scenario_advice(
            scenarios=request.scenarios,
            mode=request.mode,
            candidate=request.candidate,
            scene=scene,
            layout=request.layout,
            geometry_checks=request.geometryChecks,
            user_profile=request.userProfile,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
