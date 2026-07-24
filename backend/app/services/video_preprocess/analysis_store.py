import json
from pathlib import Path

from app.schemas import DetectedObject, DetectResponse, VideoAnalysis, VideoAnalysisFrame
from app.storage.local_store import OUTPUTS_ROOT
from app.storage.local_store import output_url_to_path
from app.services.video_preprocess.frame_similarity import (
    difference_hash_data_url,
    difference_hash_path,
    hash_distance,
)


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


def nearest_frame(
    video_id: str,
    timestamp: float,
    pause_frame_image: str | None = None,
) -> VideoAnalysisFrame | None:
    analysis = read_analysis(video_id)
    if not analysis or not analysis.frames:
        return None
    frames = sorted(analysis.frames, key=lambda frame: frame.time)
    exact = next((frame for frame in frames if abs(frame.time - timestamp) <= 1e-6), None)
    if exact is not None:
        return exact

    previous = next((frame for frame in reversed(frames) if frame.time < timestamp), None)
    following = next((frame for frame in frames if frame.time > timestamp), None)
    candidates = [frame for frame in (previous, following) if frame is not None]
    if len(candidates) == 1:
        return candidates[0]
    if not pause_frame_image:
        return min(candidates, key=lambda frame: (abs(frame.time - timestamp), frame.time > timestamp))

    try:
        pause_hash = difference_hash_data_url(pause_frame_image)
        scored: list[tuple[int, float, bool, VideoAnalysisFrame]] = []
        for frame in candidates:
            frame_hash = frame.perceptualHash
            if not frame_hash:
                frame_path = output_url_to_path(frame.frameImageUrl)
                if frame_path is None or not frame_path.exists():
                    continue
                frame_hash = difference_hash_path(frame_path)
            scored.append(
                (
                    hash_distance(pause_hash, frame_hash),
                    abs(frame.time - timestamp),
                    frame.time > timestamp,
                    frame,
                )
            )
        if scored:
            return min(scored, key=lambda item: item[:3])[3]
    except (OSError, TypeError, ValueError):
        pass
    return min(candidates, key=lambda frame: (abs(frame.time - timestamp), frame.time > timestamp))


def detect_response_for_time(
    video_id: str,
    timestamp: float,
    pause_frame_image: str | None = None,
) -> DetectResponse | None:
    frame = nearest_frame(video_id, timestamp, pause_frame_image)
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
