from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.schemas import DetectResponse, VideoAnalysis, VideoAnalysisFrame, VideoPreprocessRequest, VideoPreprocessResponse
from app.services.detection.grounded_sam2_provider import GroundedSAM2DetectionProvider
from app.services.video_preprocess.analysis_store import analysis_url, nearest_frame, read_analysis
from app.services.video_preprocess.preprocessor import VideoPreprocessor


router = APIRouter()


def get_grounded_sam2_provider() -> GroundedSAM2DetectionProvider | None:
    settings = get_settings()
    if not settings.grounded_sam2_endpoint:
        return None
    return GroundedSAM2DetectionProvider(
        endpoint=settings.grounded_sam2_endpoint,
        api_key=settings.grounded_sam2_api_key,
        prompt=settings.grounded_sam2_prompt,
        max_objects=settings.grounded_sam2_max_objects,
        min_confidence=settings.grounded_sam2_min_confidence,
    )


@router.post("/preprocess", response_model=VideoPreprocessResponse)
async def preprocess_video(request: VideoPreprocessRequest) -> VideoPreprocessResponse:
    if request.mode == "grounded_sam2" and not get_settings().grounded_sam2_endpoint:
        raise HTTPException(status_code=500, detail="GROUNDED_SAM2_ENDPOINT is required for grounded_sam2 mode")
    try:
        analysis = await VideoPreprocessor(get_grounded_sam2_provider()).preprocess(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return VideoPreprocessResponse(
        videoId=analysis.videoId,
        status=analysis.status,
        frameCount=len(analysis.frames),
        analysisUrl=analysis_url(analysis.videoId),
    )


@router.get("/analysis/{video_id}", response_model=VideoAnalysis)
async def get_analysis(video_id: str) -> VideoAnalysis:
    analysis = read_analysis(video_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Video analysis not found")
    return analysis


@router.get("/analysis/{video_id}/nearest", response_model=VideoAnalysisFrame)
async def get_nearest_analysis_frame(video_id: str, time: float = Query(ge=0)) -> VideoAnalysisFrame:
    frame = nearest_frame(video_id, time)
    if not frame:
        raise HTTPException(status_code=404, detail="Video analysis frame not found")
    return frame


@router.get("/detect/{video_id}", response_model=DetectResponse)
async def detect_from_analysis(video_id: str, time: float = Query(ge=0)) -> DetectResponse:
    frame = nearest_frame(video_id, time)
    if not frame:
        raise HTTPException(status_code=404, detail="Video analysis frame not found")
    return DetectResponse(frameId=frame.frameId, objects=frame.objects, frameImageUrl=frame.frameImageUrl)
