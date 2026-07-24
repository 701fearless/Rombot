import argparse
import asyncio
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings
from app.routers.video import get_ark_grounding_pipeline
from app.schemas import VideoPreprocessRequest
from app.services.video_preprocess.analysis_store import analysis_path, video_output_dir
from app.services.video_preprocess.clip_deduplicator import ClipFurnitureDeduplicator
from app.services.video_preprocess.preprocessor import VideoPreprocessor


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch preprocess manually selected video frames.")
    parser.add_argument("--videos", nargs="+", default=[str(index) for index in range(1, 11)])
    parser.add_argument("--mode", default="ark_grounding")
    parser.add_argument("--force", action="store_true", help="Rebuild videos even when analysis.json already succeeded.")
    return parser.parse_args()


def _successful_analysis_exists(video_id: str) -> bool:
    path = analysis_path(video_id)
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return False
    return payload.get("status") == "succeeded"


def _manual_frame_count(video_id: str) -> int:
    path = video_output_dir(video_id) / "frames.json"
    if not path.exists():
        return 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return 0
    return len(payload.get("frames") or [])


async def _main() -> int:
    args = _parse_args()
    settings = get_settings()
    ark_pipeline = get_ark_grounding_pipeline() if args.mode == "ark_grounding" else None
    if args.mode == "ark_grounding" and ark_pipeline is None:
        print("ERROR: ARK_API_KEY is required for ark_grounding mode.", flush=True)
        return 2

    preprocessor = VideoPreprocessor(
        ark_grounding_pipeline=ark_pipeline,
        furniture_deduplicator=ClipFurnitureDeduplicator(
            threshold=settings.furniture_dedupe_threshold,
            batch_size=settings.furniture_dedupe_batch_size,
            model_name=settings.furniture_dedupe_model,
            device=settings.furniture_dedupe_device,
        ),
        furniture_dedupe_enabled=settings.furniture_dedupe_enabled,
    )

    failures: list[tuple[str, str]] = []
    for video_id in args.videos:
        frame_count = _manual_frame_count(video_id)
        if frame_count <= 0:
            print(f"SKIP {video_id}: no manual frames found.", flush=True)
            continue
        if not args.force and _successful_analysis_exists(video_id):
            print(f"SKIP {video_id}: analysis.json already succeeded ({frame_count} manual frames).", flush=True)
            continue

        print(f"RUN  {video_id}: {frame_count} manual frames -> detection + dedupe", flush=True)
        try:
            analysis = await preprocessor.preprocess(
                VideoPreprocessRequest(
                    videoId=video_id,
                    mode=args.mode,
                    reuseExistingFrames=True,
                )
            )
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            print(f"FAIL {video_id}: {message}", flush=True)
            failures.append((video_id, message))
            continue

        detected_count = sum(len(frame.objects) for frame in analysis.frames)
        dedupe_status = "ok" if analysis.dedupeWarning is None else f"warning: {analysis.dedupeWarning}"
        print(
            f"DONE {video_id}: {len(analysis.frames)} frames, "
            f"{detected_count} detections, {len(analysis.deduplicatedObjects)} candidates, {dedupe_status}",
            flush=True,
        )

    if failures:
        print("FAILED VIDEOS:", flush=True)
        for video_id, message in failures:
            print(f"- {video_id}: {message}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
