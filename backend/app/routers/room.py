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
    SceneResponse,
    SceneSnapshot,
    SkillAdviceRequest,
    SkillAdviceResponse,
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
from app.services.skill_advice import generate_skill_advice, scenario_options
from app.services.user_floorplan import load_user_floorplan, save_advice_result, save_user_floorplan


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
        saved = save_snapshot(scene_id, snapshot)
        save_user_floorplan(saved)
        return saved
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/advice-options")
async def get_skill_advice_options() -> list[dict[str, str]]:
    return scenario_options()


@router.post("/snapshots/{scene_id}/skill-advice", response_model=SkillAdviceResponse)
async def create_skill_advice(
    request: SkillAdviceRequest,
    scene_id: str = PathParam(pattern=r"^[A-Za-z0-9_-]+$"),
) -> SkillAdviceResponse:
    try:
        snapshot = load_snapshot(scene_id)
        save_user_floorplan(
            snapshot,
            user_requirements={"scenarioId": request.scenarioId, "profile": request.profile},
        )
        floorplan = load_user_floorplan(scene_id)
        result = await generate_skill_advice(
            floorplan=floorplan,
            scenario_id=request.scenarioId,
            profile=request.profile,
        )
        save_advice_result(scene_id, result)
        return SkillAdviceResponse.model_validate(result)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail=f"Skill advice generation failed: {exc}") from exc


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
    geometry_moves = propose_moves_from_geometry(request.candidate, scene, result.checks)
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
        scenarioOptions=get_scenario_options(),
        agentReport=None,
    )


@router.post("/placement-check", response_model=PlacementCheckResponse)
async def placement_check(request: PlacementCheckRequest) -> PlacementCheckResponse:
    """Check one furniture placement and return deterministic moves without agents."""
    return await _run_placement_check(request)


@router.post("/spatial-check", response_model=SpatialCheckResponse, deprecated=True)
async def spatial_check(request: SpatialCheckRequest) -> SpatialCheckResponse:
    """Compatibility alias for /placement-check."""
    return await _run_placement_check(request)


@router.post("/room-layout", response_model=RoomLayoutResponse)
async def room_layout(request: RoomLayoutRequest) -> RoomLayoutResponse:
    """Analyze every furniture item and return whole-room layout moves."""
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
