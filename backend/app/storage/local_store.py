import base64
import json
import mimetypes
import re
from pathlib import Path

from app.schemas import DetectResponse, DetectedObject


BACKEND_ROOT = Path(__file__).resolve().parents[2]
OUTPUTS_ROOT = BACKEND_ROOT / "outputs"


def video_id_from_frame_id(frame_id: str) -> str | None:
    match = re.fullmatch(r"(.+)_(\d{6})", frame_id)
    if not match:
        return None
    video_id = match.group(1)
    if not re.fullmatch(r"[A-Za-z0-9_-]+", video_id):
        return None
    return video_id


def frame_output_dir(frame_id: str) -> Path:
    video_id = video_id_from_frame_id(frame_id)
    if video_id:
        return OUTPUTS_ROOT / "videos" / video_id / "generated" / frame_id
    return OUTPUTS_ROOT / frame_id


def save_data_url(data_url: str, output_path: Path) -> Path:
    if "," in data_url:
        _, encoded = data_url.split(",", 1)
    else:
        encoded = data_url
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(base64.b64decode(encoded))
    return output_path


def data_url_to_bytes(data_url: str) -> bytes:
    if "," in data_url:
        _, encoded = data_url.split(",", 1)
    else:
        encoded = data_url
    return base64.b64decode(encoded)


def path_to_output_url(path: Path) -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(OUTPUTS_ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"Path is not under outputs: {path}") from exc
    return "/outputs/" + "/".join(relative.parts)


def output_url_to_path(url: str) -> Path | None:
    prefix = "/outputs/"
    if not url.startswith(prefix):
        return None
    relative = url[len(prefix) :].replace("/", "\\")
    return OUTPUTS_ROOT / relative


def file_to_data_url(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def find_saved_frame(frame_id: str) -> Path | None:
    frame_dir = frame_output_dir(frame_id)
    for candidate in ("frame.jpg", "frame.jpeg", "frame.png", "frame.webp"):
        path = frame_dir / candidate
        if path.exists():
            return path
    return None


def save_detection_response(response: DetectResponse) -> Path:
    output_path = frame_output_dir(response.frameId) / "detection.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(response.model_dump_json(indent=2), encoding="utf-8")
    return output_path


def load_detection_response(frame_id: str) -> DetectResponse | None:
    input_path = frame_output_dir(frame_id) / "detection.json"
    if not input_path.exists():
        return None
    return DetectResponse.model_validate(json.loads(input_path.read_text(encoding="utf-8")))


def load_detected_object(frame_id: str, object_id: str) -> DetectedObject | None:
    response = load_detection_response(frame_id)
    if response is None:
        return None
    return next((item for item in response.objects if item.id == object_id), None)
