import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.services.video_preprocess.analysis_store import read_analysis, video_output_dir, write_analysis
from app.services.video_preprocess.clip_deduplicator import ClipFurnitureDeduplicator


def parse_video_ids(value: str) -> list[str]:
    result: list[str] = []
    for part in value.split(","):
        item = part.strip()
        if not item:
            continue
        if "-" in item:
            start_text, end_text = item.split("-", 1)
            start = int(start_text)
            end = int(end_text)
            if start > end:
                raise ValueError(f"Invalid video range: {item}")
            result.extend(str(number) for number in range(start, end + 1))
        else:
            result.append(item)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Re-run local CLIP deduplication and persist frame-object to candidate crop links."
    )
    parser.add_argument(
        "--video-ids",
        default="1-10",
        help="Comma-separated IDs and numeric ranges, for example: 1-10,dining_room_001",
    )
    args = parser.parse_args()

    settings = get_settings()
    deduplicator = ClipFurnitureDeduplicator(
        threshold=settings.furniture_dedupe_threshold,
        batch_size=settings.furniture_dedupe_batch_size,
        model_name=settings.furniture_dedupe_model,
        device=settings.furniture_dedupe_device,
    )

    failures: list[str] = []
    for video_id in parse_video_ids(args.video_ids):
        analysis = read_analysis(video_id)
        if analysis is None:
            print(f"{video_id}: skipped (analysis.json not found)")
            continue
        try:
            candidates, warning = deduplicator.deduplicate(
                video_id,
                analysis.frames,
                video_output_dir(video_id),
                enabled=settings.furniture_dedupe_enabled,
                fallback_on_error=False,
            )
            analysis.deduplicatedObjects = candidates
            analysis.dedupeWarning = warning
            write_analysis(analysis)
            linked = sum(
                1
                for frame in analysis.frames
                for detected_object in frame.objects
                if detected_object.deduplicatedObjectId and detected_object.deduplicatedCropUrl
            )
            print(f"{video_id}: {len(candidates)} candidates, {linked} linked frame objects")
        except Exception as exc:  # noqa: BLE001 - continue so all requested videos are audited
            failures.append(video_id)
            print(f"{video_id}: failed ({type(exc).__name__}: {exc})")

    if failures:
        raise SystemExit(f"Backfill failed for: {', '.join(failures)}")


if __name__ == "__main__":
    main()
