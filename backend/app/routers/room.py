import json

from fastapi import APIRouter, File, Form, HTTPException, Path as PathParam, UploadFile

from app.schemas import (
    LayoutModule,
    PlacementCheckRequest,
    PlacementCheckResponse,
    RoomLayoutRequest,
    RoomLayoutResponse,
    RoomScanRequest,
    ScenarioAdviceRequest,
    ScenarioAdviceResponse,
    SceneSnapshot,
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
from app.services.scene_snapshot import load_snapshot, reset_snapshot, save_runtime_whitebox, save_snapshot


router = APIRouter()


@router.get("/snapshots/{scene_id}", response_model=SceneSnapshot)
async def get_scene_snapshot(
    scene_id: str = PathParam(pattern=r"^[A-Za-z0-9_-]+$"),
) -> SceneSnapshot:
    try:
        return load_snapshot(scene_id)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/snapshots/{scene_id}", response_model=SceneSnapshot)
async def put_scene_snapshot(
    snapshot: SceneSnapshot,
    scene_id: str = PathParam(pattern=r"^[A-Za-z0-9_-]+$"),
) -> SceneSnapshot:
    try:
        return save_snapshot(scene_id, snapshot)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/snapshots/{scene_id}/reset", response_model=SceneSnapshot)
async def restore_scene_snapshot(
    scene_id: str = PathParam(pattern=r"^[A-Za-z0-9_-]+$"),
) -> SceneSnapshot:
    try:
        return reset_snapshot(scene_id)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/snapshots/{scene_id}/whitebox", response_model=SceneSnapshot)
async def put_scene_whitebox(
    scene_id: str = PathParam(pattern=r"^[A-Za-z0-9_-]+$"),
    file: UploadFile = File(...),
    snapshot: str = Form(...),
) -> SceneSnapshot:
    try:
        parsed = SceneSnapshot.model_validate(json.loads(snapshot))
        payload = await file.read()
        return save_runtime_whitebox(scene_id, parsed, payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="snapshot must be valid JSON") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    if any(value <= 0 for value in request.candidate.size):
        raise HTTPException(status_code=400, detail="家具尺寸无效")

    result = run_spatial_check(request.candidate, scene)
    if request.enableAgents:
        layout = await run_layout_module(
            candidate=request.candidate,
            scene=scene,
            checks=result.checks,
        )
    else:
        moves = propose_moves_from_geometry(request.candidate, scene, result.checks)
        layout = LayoutModule(
            moves=moves,
            advices=[],
            summary=(
                "几何检查已给出建议移动位置。"
                if moves
                else "当前位置未产生确定性移动建议。"
            ),
        )

    return PlacementCheckResponse(
        mode="placement",
        overallStatus=result.overallStatus,
        checks=result.checks,
        feedback=result.feedback,
        layout=layout,
        scenarioOptions=get_scenario_options(),
        agentReport=None,
    )


@router.post("/placement-check", response_model=PlacementCheckResponse)
async def placement_check(request: PlacementCheckRequest) -> PlacementCheckResponse:
    """模式一：单家具摆放建议（几何检测 + 该家具移动位姿 + 中文布局建议）。"""
    return await _run_placement_check(request)


@router.post("/spatial-check", response_model=SpatialCheckResponse, deprecated=True)
async def spatial_check(request: SpatialCheckRequest) -> SpatialCheckResponse:
    """Compatibility alias for /placement-check."""
    return await _run_placement_check(request)


@router.post("/room-layout", response_model=RoomLayoutResponse)
async def room_layout(request: RoomLayoutRequest) -> RoomLayoutResponse:
    """模式二：全屋布局建议（逐件几何扫描 + 多家具移动 + 全屋中文建议）。"""
    scene = _resolve_scene(request.scene, request.sceneId)
    if scene.room.width <= 0 or scene.room.depth <= 0:
        raise HTTPException(status_code=400, detail="房间尺寸无效")
    if not scene.objects:
        raise HTTPException(status_code=400, detail="场景中没有家具，无法进行全屋布局分析")
    return await run_room_layout(scene=scene, enable_agents=request.enableAgents)


@router.post("/scenario-advice", response_model=ScenarioAdviceResponse)
async def scenario_advice(request: ScenarioAdviceRequest) -> ScenarioAdviceResponse:
    """场景深化：养老/育婴/养宠/风水。mode=placement|room。"""
    scene = _resolve_scene(request.scene, request.sceneId)
    if scene.room.width <= 0 or scene.room.depth <= 0:
        raise HTTPException(status_code=400, detail="房间尺寸无效")
    if request.candidate is not None and any(value <= 0 for value in request.candidate.size):
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
