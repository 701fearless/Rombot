from fastapi import APIRouter

from app.schemas import RoomScanRequest, SceneResponse
from app.services.room_scan.mock_scene import build_mock_scene


router = APIRouter()


@router.post("/scan", response_model=SceneResponse)
async def scan_room(request: RoomScanRequest | None = None) -> SceneResponse:
    scan_id = request.scanId if request and request.scanId else "demo_living_room"
    return build_mock_scene(scene_id=scan_id)
