from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.routers.feed import get_model3d_provider
from app.schemas import DebugImagePipelineRequest, DetectResponse, FeedPipelineResponse
from app.services.detection.ark_grounding_provider import ArkGroundingProvider
from app.services.video_preprocess.ark_grounding_pipeline import ArkGroundingPipeline
from app.storage.local_store import BACKEND_ROOT, file_to_data_url, output_url_to_path, save_detection_response


router = APIRouter()


@router.post("/image-pipeline", response_model=FeedPipelineResponse)
async def image_pipeline(request: DebugImagePipelineRequest) -> FeedPipelineResponse:
    settings = get_settings()
    if not settings.ark_api_key:
        raise HTTPException(status_code=500, detail="ARK_API_KEY is required")

    image_path = _resolve_image_path(request.imagePath)
    if not image_path.exists():
        raise HTTPException(status_code=404, detail=f"Image not found: {request.imagePath}")

    frame_id = f"debug_{image_path.stem}"
    image_data_url = file_to_data_url(image_path)
    pipeline = ArkGroundingPipeline(
        grounding_provider=ArkGroundingProvider(
            api_key=settings.ark_api_key,
            base_url=settings.ark_base_url,
            model=settings.ark_vision_model,
        )
    )
    objects = await pipeline.process_frame(frame_id=frame_id, frame_path=image_path, image_data_url=image_data_url)
    detection = DetectResponse(frameId=frame_id, frameImageUrl=request.imagePath, objects=objects)
    save_detection_response(detection)

    if not objects:
        raise HTTPException(status_code=404, detail="Ark grounding did not return any furniture objects")
    if request.objectIndex >= len(objects):
        raise HTTPException(status_code=400, detail=f"objectIndex out of range; got {request.objectIndex}, max {len(objects) - 1}")

    selected_object = objects[request.objectIndex]
    crop_path = output_url_to_path(selected_object.cropUrl) if selected_object.cropUrl else None
    crop_image = file_to_data_url(crop_path) if crop_path and crop_path.exists() else image_data_url
    selected = await get_model3d_provider().generate_asset(
        frame_id=frame_id,
        detected_object=selected_object,
        image_url=crop_image,
    )
    selected.object.cropUrl = selected_object.cropUrl
    selected.object.maskUrl = selected_object.maskUrl
    return FeedPipelineResponse(detection=detection, selected=selected)


def _resolve_image_path(image_path: str) -> Path:
    if image_path.startswith("/sample_data/"):
        return (BACKEND_ROOT / image_path.lstrip("/")).resolve()
    path = Path(image_path)
    if path.is_absolute():
        return path
    return (BACKEND_ROOT / path).resolve()
