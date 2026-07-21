from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.schemas import DetectRequest, DetectResponse, FeedPipelineRequest, FeedPipelineResponse, SelectObjectRequest, SelectObjectResponse
from app.services.detection.grounded_sam2_provider import GroundedSAM2DetectionProvider
from app.services.detection.mock_provider import MockDetectionProvider
from app.services.model3d.meshy_provider import MeshyModel3DProvider
from app.services.model3d.mock_provider import MockModel3DProvider
from app.services.model3d.pixal3d_provider import Pixal3DModel3DProvider
from app.services.segmentation.mock_provider import MockSegmentationProvider
from app.services.segmentation.sam3_provider import SAM3SegmentationProvider
from app.services.video_preprocess.analysis_store import detect_response_for_time, find_object as find_preprocessed_object
from app.storage.local_store import (
    OUTPUTS_ROOT,
    find_saved_frame,
    load_detected_object,
    path_to_output_url,
    output_url_to_path,
    file_to_data_url,
    save_data_url,
    save_detection_response,
)


router = APIRouter()


def get_detection_provider() -> MockDetectionProvider | GroundedSAM2DetectionProvider:
    settings = get_settings()
    if settings.detection_provider == "grounded_sam2":
        if not settings.grounded_sam2_endpoint:
            raise HTTPException(status_code=500, detail="GROUNDED_SAM2_ENDPOINT is required")
        return GroundedSAM2DetectionProvider(
            endpoint=settings.grounded_sam2_endpoint,
            api_key=settings.grounded_sam2_api_key,
            prompt=settings.grounded_sam2_prompt,
            max_objects=settings.grounded_sam2_max_objects,
            min_confidence=settings.grounded_sam2_min_confidence,
        )
    if settings.detection_provider != "mock":
        raise HTTPException(status_code=501, detail=f"Detection provider not implemented: {settings.detection_provider}")
    return MockDetectionProvider()


def get_model3d_provider() -> MockModel3DProvider | MeshyModel3DProvider:
    settings = get_settings()
    if settings.model3d_provider == "meshy" and settings.meshy_api_key:
        return MeshyModel3DProvider(api_key=settings.meshy_api_key, base_url=settings.meshy_base_url)
    if settings.model3d_provider == "pixal3d" and settings.pixal3d_endpoint:
        return Pixal3DModel3DProvider(endpoint=settings.pixal3d_endpoint, api_key=settings.pixal3d_api_key)
    return MockModel3DProvider()


def get_segmentation_provider() -> MockSegmentationProvider | SAM3SegmentationProvider:
    settings = get_settings()
    if settings.segmentation_provider == "sam3" and settings.sam3_endpoint:
        return SAM3SegmentationProvider(endpoint=settings.sam3_endpoint, api_key=settings.sam3_api_key)
    return MockSegmentationProvider()


def save_frame_image(frame_id: str, frame_image: str | None) -> Path | None:
    if not frame_image:
        return find_saved_frame(frame_id)
    output_path = OUTPUTS_ROOT / frame_id / "frame.jpg"
    return save_data_url(frame_image, output_path)


@router.post("/detect", response_model=DetectResponse)
async def detect(request: DetectRequest) -> DetectResponse:
    preprocessed_response = detect_response_for_time(request.videoId, request.time)
    if preprocessed_response:
        return preprocessed_response

    provider = get_detection_provider()
    try:
        response = await provider.detect(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    frame_path = save_frame_image(response.frameId, request.frameImage)
    if frame_path:
        response.frameImageUrl = path_to_output_url(frame_path)
    save_detection_response(response)
    return response


@router.post("/select-object", response_model=SelectObjectResponse)
async def select_object(request: SelectObjectRequest) -> SelectObjectResponse:
    detected_object = find_preprocessed_object(request.frameId, request.objectId)
    detection_provider = get_detection_provider()
    if detected_object is None:
        detected_object = await detection_provider.get_object(request.frameId, request.objectId)
    if detected_object is None:
        detected_object = load_detected_object(request.frameId, request.objectId)
    if detected_object is None:
        raise HTTPException(status_code=404, detail="Object not found for the given frameId/objectId")

    frame_path = save_frame_image(request.frameId, request.frameImage)
    if detected_object.cropUrl and detected_object.maskUrl:
        segmentation_crop_url = detected_object.cropUrl
        segmentation_mask_url = detected_object.maskUrl
        segmentation_crop_path = output_url_to_path(segmentation_crop_url)
        segmentation_crop_image = file_to_data_url(segmentation_crop_path) if segmentation_crop_path and segmentation_crop_path.exists() else None
    else:
        segmentation_provider = get_segmentation_provider()
        segmentation = await segmentation_provider.segment(
            frame_id=request.frameId,
            detected_object=detected_object,
            frame_image_path=frame_path,
            frame_image_data_url=request.frameImage,
        )
        segmentation_crop_url = segmentation.cropUrl
        segmentation_mask_url = segmentation.maskUrl
        segmentation_crop_image = segmentation.cropImage

    model_provider = get_model3d_provider()
    response = await model_provider.generate_asset(
        frame_id=request.frameId,
        detected_object=detected_object,
        image_url=request.imageUrl or request.cropImage or segmentation_crop_image or segmentation_crop_url,
    )
    response.object.cropUrl = segmentation_crop_url
    response.object.maskUrl = segmentation_mask_url
    return response


@router.post("/run-pipeline", response_model=FeedPipelineResponse)
async def run_pipeline(request: FeedPipelineRequest) -> FeedPipelineResponse:
    detection = await detect(
        DetectRequest(videoId=request.videoId, time=request.time, frameImage=request.frameImage)
    )
    if not detection.objects:
        raise HTTPException(status_code=404, detail="No furniture objects detected")

    object_id = request.objectId or detection.objects[0].id
    selected = await select_object(
        SelectObjectRequest(frameId=detection.frameId, objectId=object_id, frameImage=request.frameImage)
    )
    return FeedPipelineResponse(detection=detection, selected=selected)
