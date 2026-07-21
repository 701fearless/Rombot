import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from app.storage.local_store import BACKEND_ROOT


class FrameExtractionError(RuntimeError):
    pass


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
    max_frames: int,
    allow_placeholder: bool,
) -> list[tuple[Path, float]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    source = resolve_video_source(video_url)
    ffmpeg = shutil.which("ffmpeg")
    if source and ffmpeg:
        extracted = _extract_with_ffmpeg(ffmpeg, source, output_dir, sample_interval_sec, max_frames)
        if extracted:
            return extracted
    if allow_placeholder:
        return _create_placeholder_frames(output_dir, sample_interval_sec, max_frames)
    raise FrameExtractionError("ffmpeg is not available or video source could not be extracted")


def _extract_with_ffmpeg(
    ffmpeg: str,
    source: str,
    output_dir: Path,
    sample_interval_sec: float,
    max_frames: int,
) -> list[tuple[Path, float]]:
    fps = 1.0 / sample_interval_sec
    pattern = output_dir / "%06d.jpg"
    command = [
        ffmpeg,
        "-y",
        "-i",
        source,
        "-vf",
        f"fps={fps},scale='min(1024,iw)':-2",
        "-frames:v",
        str(max_frames),
        str(pattern),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        return []
    return [(path, index * sample_interval_sec) for index, path in enumerate(sorted(output_dir.glob("*.jpg")))]


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
