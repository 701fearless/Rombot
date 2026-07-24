import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

from app.storage.local_store import BACKEND_ROOT


class FrameExtractionError(RuntimeError):
    pass


@dataclass
class FrameExtractionResult:
    frames: list[tuple[Path, float]]
    duration_sec: float | None
    sample_interval_sec: float


def load_existing_frames(video_output_dir: Path) -> FrameExtractionResult:
    frame_dir = video_output_dir / "frames"
    manifest_path = video_output_dir / "frames.json"
    records: list[tuple[Path, float]] = []
    duration_sec: float | None = None
    sample_interval_sec: float | None = None

    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            if manifest.get("durationSec") is not None:
                duration_sec = float(manifest["durationSec"])
            if manifest.get("samplingIntervalSec") is not None:
                sample_interval_sec = float(manifest["samplingIntervalSec"])
            for item in manifest["frames"]:
                file_name = str(item["fileName"])
                if Path(file_name).name != file_name:
                    continue
                frame_path = frame_dir / file_name
                if frame_path.exists():
                    records.append((frame_path, float(item["timeSec"])))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid existing frame manifest: {manifest_path}") from exc
    else:
        for frame_path in frame_dir.glob("frame_t*ms.jpg"):
            match = re.fullmatch(r"frame_t(\d+)ms", frame_path.stem)
            if match:
                records.append((frame_path, int(match.group(1)) / 1000))

    records.sort(key=lambda item: item[1])
    if not records:
        raise ValueError(f"No existing timestamped frames found in {frame_dir}")
    if sample_interval_sec is None:
        intervals = [right[1] - left[1] for left, right in zip(records, records[1:]) if right[1] > left[1]]
        sample_interval_sec = min(intervals) if intervals else 1.0
    return FrameExtractionResult(
        frames=records,
        duration_sec=duration_sec,
        sample_interval_sec=sample_interval_sec,
    )


def resolve_video_source(video_url: str | None) -> str | None:
    if not video_url:
        return None
    if video_url.startswith(("http://", "https://")):
        return video_url
    if video_url.startswith("/"):
        return str((BACKEND_ROOT / video_url.lstrip("/")).resolve())
    return str(Path(video_url).resolve())


def extract_frames(
    video_url: str | None,
    output_dir: Path,
    sample_interval_sec: float,
    max_frames: int | None,
    allow_placeholder: bool,
) -> FrameExtractionResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    for old_frame in output_dir.glob("*.jpg"):
        old_frame.unlink()
    source = resolve_video_source(video_url)
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if source and ffmpeg and ffprobe:
        duration_sec = _probe_duration(ffprobe, source)
        frame_count = max_frames or frame_count_for_duration(duration_sec)
        extracted = _extract_with_ffmpeg(ffmpeg, source, output_dir, duration_sec, frame_count)
        if extracted:
            return FrameExtractionResult(
                frames=extracted,
                duration_sec=duration_sec,
                sample_interval_sec=duration_sec / frame_count,
            )
    if allow_placeholder:
        frame_count = max_frames or 10
        return FrameExtractionResult(
            frames=_create_placeholder_frames(output_dir, sample_interval_sec, frame_count),
            duration_sec=None,
            sample_interval_sec=sample_interval_sec,
        )
    raise FrameExtractionError("ffmpeg/ffprobe is unavailable or video source could not be extracted")


def frame_count_for_duration(duration_sec: float) -> int:
    if duration_sec <= 60:
        return 10
    if duration_sec <= 180:
        return 20
    return 30


def _probe_duration(ffprobe: str, source: str) -> float:
    command = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        source,
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise FrameExtractionError("ffprobe could not read the video duration")
    try:
        duration_sec = float(json.loads(result.stdout)["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise FrameExtractionError("ffprobe returned an invalid video duration") from exc
    if duration_sec <= 0:
        raise FrameExtractionError("video duration must be greater than zero")
    return duration_sec


def _extract_with_ffmpeg(
    ffmpeg: str,
    source: str,
    output_dir: Path,
    duration_sec: float,
    frame_count: int,
) -> list[tuple[Path, float]]:
    fps = frame_count / duration_sec
    pattern = output_dir / "%06d.jpg"
    command = [
        ffmpeg,
        "-y",
        "-i",
        source,
        "-vf",
        f"fps={fps},scale='min(1024,iw)':-2",
        "-frames:v",
        str(frame_count),
        str(pattern),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        return []
    interval_sec = duration_sec / frame_count
    return [(path, index * interval_sec) for index, path in enumerate(sorted(output_dir.glob("*.jpg")))]


def _create_placeholder_frames(output_dir: Path, sample_interval_sec: float, max_frames: int) -> list[tuple[Path, float]]:
    frames: list[tuple[Path, float]] = []
    for index in range(max_frames):
        path = output_dir / f"{index + 1:06d}.jpg"
        image = Image.new("RGB", (720, 1280), (226, 220, 210))
        draw = ImageDraw.Draw(image)
        draw.rectangle((100, 610, 620, 900), fill=(186, 166, 138), outline=(130, 110, 90), width=4)
        draw.rectangle((230, 500, 490, 610), fill=(166, 145, 120), outline=(120, 100, 80), width=4)
        draw.ellipse((290, 160, 430, 300), fill=(235, 200, 80), outline=(155, 120, 35), width=4)
        draw.rectangle((150, 930, 570, 1120), fill=(160, 90, 80), outline=(110, 55, 50), width=4)
        draw.text((24, 24), f"mock frame {index + 1}", fill=(60, 60, 60))
        image.save(path, quality=92)
        frames.append((path, index * sample_interval_sec))
    return frames
