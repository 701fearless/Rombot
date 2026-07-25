from pathlib import Path

from fastapi import APIRouter, HTTPException
import httpx

from app.config import get_settings
from app.schemas import DetectRequest, DetectResponse, FeedPipelineRequest, FeedPipelineResponse, SelectObjectRequest, SelectObjectResponse
from app.services.detection.ark_feed_provider import ArkFeedDetectionProvider
from app.services.detection.ark_grounding_provider import ArkGroundingProvider
from app.services.detection.grounded_sam2_provider import GroundedSAM2DetectionProvider
from app.services.image_generation.ark_seedream_provider import ArkSeedreamProvider
from app.services.model3d.hunyuan3d_provider import Hunyuan3DProvider
from app.services.detection.mock_provider import MockDetectionProvider
from app.services.model3d.meshy_provider import MeshyModel3DProvider
from app.services.model3d.mock_provider import MockModel3DProvider
from app.services.model3d.pixal3d_provider import Pixal3DModel3DProvider
from app.services.model3d.feature_meshy_provider import FeatureMeshyModel3DProvider
from app.services.model3d.feature_hunyuan_provider import FeatureHunyuanModel3DProvider
from app.services.model3d.feature_tripo_provider import FeatureTripoModel3DProvider
from app.services.segmentation.mock_provider import MockSegmentationProvider
from app.services.segmentation.sam3_provider import SAM3SegmentationProvider
from app.services.video_preprocess.analysis_store import detect_response_for_time, find_object as find_preprocessed_object
from app.storage.local_store import (
    frame_output_dir,
    find_saved_frame,
    load_detected_object,
    path_to_output_url,
    output_url_to_path,
    file_to_data_url,
    save_data_url,
    save_detection_response,
)


router = APIRouter()


def get_detection_provider() -> MockDetectionProvider | GroundedSAM2DetectionProvider | ArkFeedDetectionProvider:
    settings = get_settings()
    if settings.detection_provider == "ark_grounding":
        if not settings.ark_api_key:
            raise HTTPException(status_code=500, detail="ARK_API_KEY is required for ark_grounding")
        return ArkFeedDetectionProvider(
            ArkGroundingProvider(
                api_key=settings.ark_api_key,
                base_url=settings.ark_base_url,
                model=settings.ark_vision_model,
            )
        )
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


def get_model3d_provider() -> (
    MockModel3DProvider
    | MeshyModel3DProvider
    | FeatureMeshyModel3DProvider
    | FeatureHunyuanModel3DProvider
    | FeatureTripoModel3DProvider
    | Hunyuan3DProvider
):
    settings = get_settings()
    # Local verified pipeline: Ark vision brief + Seedream refs + Hunyuan 3D.
    if settings.model3d_provider == "feature_hunyuan":
        missing = []
        if not settings.ark_api_key:
            missing.append("ARK_API_KEY")
        if not settings.hunyuan_api_key:
            missing.append("HUNYUAN_API_KEY")
        if not settings.hunyuan_base_url:
            missing.append("HUNYUAN_BASE_URL")
        if missing:
            raise HTTPException(status_code=500, detail=f"Missing required keys for feature_hunyuan: {', '.join(missing)}")
        return FeatureHunyuanModel3DProvider(
            ark_api_key=settings.ark_api_key,
            ark_base_url=settings.ark_base_url,
            ark_vision_model=settings.ark_vision_model,
            ark_image_model=settings.ark_image_model,
            ark_image_size=settings.ark_image_size,
            hunyuan_api_key=settings.hunyuan_api_key,
            hunyuan_base_url=settings.hunyuan_base_url,
            hunyuan_model=settings.hunyuan_model,
            hunyuan_generate_type=settings.hunyuan_generate_type,
            hunyuan_face_count=settings.hunyuan_face_count,
            hunyuan_enable_pbr=settings.hunyuan_enable_pbr,
            hunyuan_enable_geometry=settings.hunyuan_enable_geometry,
            hunyuan_result_format=settings.hunyuan_result_format,
            hunyuan_poll_interval_sec=settings.hunyuan_poll_interval_sec,
            hunyuan_poll_attempts=settings.hunyuan_poll_attempts,
        )
    if settings.model3d_provider == "feature_tripo":
        missing = []
        if not settings.ark_api_key:
            missing.append("ARK_API_KEY")
        if not settings.tripo_api_key:
            missing.append("TRIPO_API_KEY")
        if missing:
            raise HTTPException(status_code=500, detail=f"Missing required keys for feature_tripo: {', '.join(missing)}")
        return FeatureTripoModel3DProvider(
            ark_api_key=settings.ark_api_key,
            ark_base_url=settings.ark_base_url,
            ark_vision_model=settings.ark_vision_model,
            ark_image_model=settings.ark_image_model,
            ark_image_size=settings.ark_image_size,
            tripo_api_key=settings.tripo_api_key,
            tripo_base_url=settings.tripo_base_url,
            tripo_model_version=settings.tripo_model_version,
            tripo_texture=settings.tripo_texture,
            tripo_pbr=settings.tripo_pbr,
            tripo_texture_quality=settings.tripo_texture_quality,
            tripo_texture_alignment=settings.tripo_texture_alignment,
            tripo_export_uv=settings.tripo_export_uv,
            tripo_enable_image_autofix=settings.tripo_enable_image_autofix,
            tripo_poll_interval_sec=settings.tripo_poll_interval_sec,
            tripo_poll_attempts=settings.tripo_poll_attempts,
        )
    if settings.model3d_provider == "feature_meshy":
        missing = []
        if not settings.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if not settings.meshy_api_key:
            missing.append("MESHY_API_KEY")
        if missing:
            raise HTTPException(status_code=500, detail=f"Missing required keys for feature_meshy: {', '.join(missing)}")
        return FeatureMeshyModel3DProvider(
            openai_api_key=settings.openai_api_key,
            openai_base_url=settings.openai_base_url,
            openai_vision_model=settings.openai_vision_model,
            openai_image_model=settings.openai_image_model,
            openai_image_size=settings.openai_image_size,
            meshy_api_key=settings.meshy_api_key,
            meshy_base_url=settings.meshy_base_url,
            meshy_ai_model=settings.meshy_ai_model,
            meshy_poll_interval_sec=settings.meshy_poll_interval_sec,
            meshy_poll_attempts=settings.meshy_poll_attempts,
        )
    if settings.model3d_provider == "hunyuan3d" and settings.hunyuan_api_key:
        reference_provider = (
            ArkSeedreamProvider(
                api_key=settings.ark_api_key,
                base_url=settings.ark_base_url,
                model=settings.ark_image_model,
                image_size=settings.ark_image_size,
            )
            if settings.enable_ark_reference_image and settings.ark_api_key
            else None
        )
        return Hunyuan3DProvider(
            api_key=settings.hunyuan_api_key,
            base_url=settings.hunyuan_base_url,
            model=settings.hunyuan_model,
            poll_interval_sec=settings.hunyuan_poll_interval_sec,
            poll_attempts=settings.hunyuan_poll_attempts,
            reference_provider=reference_provider,
            generate_type=settings.hunyuan_generate_type,
            face_count=settings.hunyuan_face_count,
            enable_pbr=settings.hunyuan_enable_pbr,
            enable_geometry=settings.hunyuan_enable_geometry,
            result_format=settings.hunyuan_result_format,
        )
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
    output_path = frame_output_dir(frame_id) / "frame.jpg"
    return save_data_url(frame_image, output_path)


@router.post("/detect", response_model=DetectResponse)
async def detect(request: DetectRequest) -> DetectResponse:
    preprocessed_response = detect_response_for_time(
        request.videoId,
        request.time,
        request.frameImage,
        request.frameHash,
    )
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
    if detected_object is None:
        detection_provider = get_detection_provider()
        detected_object = await detection_provider.get_object(request.frameId, request.objectId)
    if detected_object is None:
        detected_object = load_detected_object(request.frameId, request.objectId)
    if detected_object is None:
        raise HTTPException(status_code=404, detail="Object not found for the given frameId/objectId")

    frame_path = save_frame_image(request.frameId, request.frameImage)
    settings = get_settings()
    refine_with_sam = (
        settings.segmentation_provider == "sam3"
        and bool(settings.sam3_endpoint)
        and bool(request.frameImage)
    )
    if detected_object.cropUrl and detected_object.maskUrl and not refine_with_sam:
        segmentation_crop_url = detected_object.cropUrl
        segmentation_mask_url = detected_object.maskUrl
        segmentation_crop_path = output_url_to_path(segmentation_crop_url)
        segmentation_crop_image = file_to_data_url(segmentation_crop_path) if segmentation_crop_path and segmentation_crop_path.exists() else None
    else:
        segmentation_provider = get_segmentation_provider()
        try:
            segmentation = await segmentation_provider.segment(
                frame_id=request.frameId,
                detected_object=detected_object,
                frame_image_path=frame_path,
                frame_image_data_url=request.frameImage,
            )
        except httpx.HTTPError:
            # SAM is optional: preserve the Ark bbox crop/mask or fall back to bbox segmentation.
            if detected_object.cropUrl and detected_object.maskUrl:
                segmentation_crop_url = detected_object.cropUrl
                segmentation_mask_url = detected_object.maskUrl
                segmentation_crop_path = output_url_to_path(segmentation_crop_url)
                segmentation_crop_image = (
                    file_to_data_url(segmentation_crop_path)
                    if segmentation_crop_path and segmentation_crop_path.exists()
                    else None
                )
                segmentation = None
            else:
                segmentation = await MockSegmentationProvider().segment(
                    frame_id=request.frameId,
                    detected_object=detected_object,
                    frame_image_path=frame_path,
                    frame_image_data_url=request.frameImage,
                )
        if segmentation is not None:
            segmentation_crop_url = segmentation.cropUrl
            segmentation_mask_url = segmentation.maskUrl
            segmentation_crop_image = segmentation.cropImage

    generation_source_url = (
        detected_object.deduplicatedCropUrl
        or request.imageUrl
        or request.cropImage
        or segmentation_crop_image
        or segmentation_crop_url
    )
    model_provider = get_model3d_provider()
    try:
        response = await model_provider.generate_asset(
            frame_id=request.frameId,
            detected_object=detected_object,
            image_url=generation_source_url,
        )
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:1200] if exc.response is not None else str(exc)
        status = exc.response.status_code if exc.response is not None else "unknown"
        raise HTTPException(status_code=502, detail=f"3D provider HTTP {status}: {detail}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"3D generation input/output validation failed: {exc}") from exc
    response.object.cropUrl = generation_source_url
    response.object.maskUrl = segmentation_mask_url
    if response.generation is not None:
        response.generation.sourceImageUrl = generation_source_url
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
