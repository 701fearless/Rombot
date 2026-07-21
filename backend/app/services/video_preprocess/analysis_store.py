import json
from pathlib import Path

from app.schemas import DetectedObject, DetectResponse, VideoAnalysis, VideoAnalysisFrame
from app.storage.local_store import OUTPUTS_ROOT


def video_output_dir(video_id: str) -> Path:
    return OUTPUTS_ROOT / "videos" / video_id


def analysis_path(video_id: str) -> Path:
    return video_output_dir(video_id) / "analysis.json"


def analysis_url(video_id: str) -> str:
    return f"/outputs/videos/{video_id}/analysis.json"


def write_analysis(analysis: VideoAnalysis) -> Path:
    path = analysis_path(analysis.videoId)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")
    return path


def read_analysis(video_id: str) -> VideoAnalysis | None:
    path = analysis_path(video_id)
    if not path.exists():
        return None
    return VideoAnalysis.model_validate(json.loads(path.read_text(encoding="utf-8")))


def nearest_frame(video_id: str, timestamp: float) -> VideoAnalysisFrame | None:
    analysis = read_analysis(video_id)
    if not analysis or not analysis.frames:
        return None
    return min(analysis.frames, key=lambda frame: abs(frame.time - timestamp))


def detect_response_for_time(video_id: str, timestamp: float) -> DetectResponse | None:
    frame = nearest_frame(video_id, timestamp)
    if not frame:
        return None
    return DetectResponse(frameId=frame.frameId, objects=frame.objects, frameImageUrl=frame.frameImageUrl)


def find_object(frame_id: str, object_id: str) -> DetectedObject | None:
    video_root = OUTPUTS_ROOT / "videos"
    if not video_root.exists():
        return None
    for path in video_root.glob("*/analysis.json"):
        analysis = VideoAnalysis.model_validate(json.loads(path.read_text(encoding="utf-8")))
        for frame in analysis.frames:
            if frame.frameId != frame_id:
                continue
            return next((item for item in frame.objects if item.id == object_id), None)
    return None
