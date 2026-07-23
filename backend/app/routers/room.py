from fastapi import APIRouter, HTTPException

from app.schemas import RoomScanRequest, SceneResponse, SpatialCheckRequest, SpatialCheckResponse
from app.services.layout_reasoning import run_spatial_check
from app.services.room_scan.mock_scene import build_mock_scene


router = APIRouter()


@router.post("/scan", response_model=SceneResponse)
async def scan_room(request: RoomScanRequest | None = None) -> SceneResponse:
    scan_id = request.scanId if request and request.scanId else "demo_living_room"
    return build_mock_scene(scene_id=scan_id)


@router.post("/spatial-check", response_model=SpatialCheckResponse)
async def spatial_check(request: SpatialCheckRequest) -> SpatialCheckResponse:
    """基础空间可行性检测：空间适配 / 障碍物 / 门窗可达性 / 活动空间。"""
    scene = request.scene
    if scene is None:
        scene_id = request.sceneId or "demo_living_room"
        scene = build_mock_scene(scene_id=scene_id)
    if scene.room.width <= 0 or scene.room.depth <= 0:
        raise HTTPException(status_code=400, detail="房间尺寸无效")
    if any(v <= 0 for v in request.candidate.size):
        raise HTTPException(status_code=400, detail="家具尺寸无效")
    return run_spatial_check(request.candidate, scene)
