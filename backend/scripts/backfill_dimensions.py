import argparse
import asyncio
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.services.video_preprocess.analysis_store import analysis_path, read_analysis, write_analysis
from app.services.video_preprocess.dimension_estimator import ArkFurnitureDimensionEstimator


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


def legacy_candidate_ranges(video_id: str) -> dict[str, dict]:
    path = analysis_path(video_id)
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    result: dict[str, dict] = {}
    for candidate in raw.get("deduplicatedObjects") or []:
        dimensions = candidate.get("estimatedDimensions")
        ranges = dimensions.get("range") if isinstance(dimensions, dict) else None
        if isinstance(ranges, dict) and candidate.get("id"):
            result[str(candidate["id"])] = ranges
    return result


async def backfill(
    video_ids: list[str],
    force: bool,
    candidate_ids: set[str] | None = None,
) -> list[str]:
    settings = get_settings()
    if not settings.ark_api_key:
        raise RuntimeError("ARK_API_KEY is required for dimension estimation")

    estimator = ArkFurnitureDimensionEstimator(
        api_key=settings.ark_api_key,
        base_url=settings.ark_base_url,
        model=settings.ark_vision_model,
    )
    failures: list[str] = []
    for video_id in video_ids:
        legacy_ranges = legacy_candidate_ranges(video_id)
        analysis = read_analysis(video_id)
        if analysis is None:
            print(f"{video_id}: skipped (analysis.json not found)", flush=True)
            continue
        candidates = [
            candidate
            for candidate in analysis.deduplicatedObjects
            if not candidate_ids or candidate.id in candidate_ids
        ]
        if not candidates:
            print(f"{video_id}: skipped (no deduplicated candidates)", flush=True)
            continue

        estimated = 0
        migrated = 0
        skipped = 0
        candidate_failures = 0
        for index, candidate in enumerate(candidates, start=1):
            if candidate.id in legacy_ranges and not force:
                candidate.estimatedDimensions = estimator.initial_dimensions_from_ranges(
                    legacy_ranges[candidate.id]
                )
                migrated += 1
            if candidate.estimatedDimensions is not None and not force:
                # Also repair frame-object propagation for partially written old data.
                await estimator.enrich_candidates(analysis.frames, [candidate])
                skipped += 1
                continue
            try:
                estimated += await estimator.enrich_candidates(
                    analysis.frames,
                    [candidate],
                    force=force,
                    on_update=lambda: write_analysis(analysis),
                )
                print(
                    f"{video_id}: [{index}/{len(candidates)}] "
                    f"{candidate.id} -> "
                    f"{candidate.estimatedDimensions.widthM:.2f} x "
                    f"{candidate.estimatedDimensions.depthM:.2f} x "
                    f"{candidate.estimatedDimensions.heightM:.2f} m",
                    flush=True,
                )
            except Exception as exc:  # noqa: BLE001 - persist other candidates and audit all
                candidate_failures += 1
                print(
                    f"{video_id}: [{index}/{len(candidates)}] "
                    f"{candidate.id} failed ({type(exc).__name__}: {exc})",
                    flush=True,
                )
        write_analysis(analysis)
        linked = sum(
            1
            for frame in analysis.frames
            for detected_object in frame.objects
            if detected_object.estimatedDimensions is not None
        )
        print(
            f"{video_id}: estimated={estimated}, migrated={migrated}, skipped={skipped}, "
            f"failed={candidate_failures}, frameObjectsWithDimensions={linked}",
            flush=True,
        )
        if candidate_failures:
            failures.append(video_id)
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Estimate dimensions for existing deduplicated candidates and write them to "
            "analysis.json without rerunning detection, segmentation or CLIP deduplication."
        )
    )
    parser.add_argument(
        "--video-ids",
        default="1-10",
        help="Comma-separated IDs and numeric ranges, for example: 1-10,dining_room_001",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-estimate candidates that already have estimatedDimensions.",
    )
    parser.add_argument(
        "--candidate-ids",
        default="",
        help="Optional comma-separated candidate IDs to limit the backfill.",
    )
    args = parser.parse_args()

    candidate_ids = {item.strip() for item in args.candidate_ids.split(",") if item.strip()}
    failures = asyncio.run(
        backfill(
            parse_video_ids(args.video_ids),
            args.force,
            candidate_ids or None,
        )
    )
    if failures:
        raise SystemExit(f"Dimension backfill had candidate failures in: {', '.join(failures)}")


if __name__ == "__main__":
    main()
