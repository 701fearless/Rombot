from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.schemas import DeduplicatedObject, DetectedObject, VideoAnalysis
from app.services.model3d.feature_hunyuan_provider import FeatureHunyuanModel3DProvider
from app.services.video_preprocess.analysis_store import read_analysis, video_output_dir
from app.storage.local_store import file_to_data_url, output_url_to_path


REFERENCE_NAME = "reference_oblique_3quarter.png"


def parse_video_ids(value: str) -> list[str]:
    result: list[str] = []
    for part in value.split(","):
        item = part.strip()
        if not item:
            continue
        if "-" in item:
            start_text, end_text = item.split("-", 1)
            start, end = int(start_text), int(end_text)
            if start > end:
                raise ValueError(f"Invalid video range: {item}")
            result.extend(str(number) for number in range(start, end + 1))
        else:
            result.append(item)
    return result


def build_provider() -> FeatureHunyuanModel3DProvider:
    settings = get_settings()
    if not settings.ark_api_key:
        raise RuntimeError("ARK_API_KEY is required")
    return FeatureHunyuanModel3DProvider(
        ark_api_key=settings.ark_api_key,
        ark_base_url=settings.ark_base_url,
        ark_vision_model=settings.ark_vision_model,
        ark_image_model=settings.ark_image_model,
        ark_image_size=settings.ark_image_size,
        hunyuan_api_key=settings.hunyuan_api_key or "unused-for-reference-generation",
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


def representative_object(
    analysis: VideoAnalysis,
    candidate: DeduplicatedObject,
) -> DetectedObject:
    for frame in analysis.frames:
        if frame.frameId != candidate.representativeFrameId:
            continue
        for detected_object in frame.objects:
            if detected_object.id == candidate.representativeObjectId:
                return detected_object.model_copy(
                    update={
                        "id": candidate.id,
                        "cropUrl": candidate.cropUrl,
                        "deduplicatedObjectId": candidate.id,
                        "deduplicatedCropUrl": candidate.cropUrl,
                        "estimatedDimensions": candidate.estimatedDimensions,
                    }
                )
    raise ValueError(f"Representative object not found for {candidate.id}")


def validate_reference(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        width, height = image.size
    if width < 1024 or height < 1024:
        raise ValueError(f"Reference image is unexpectedly small: {width}x{height}")
    return width, height


async def materialize_remote_reference(url: str, destination: Path) -> None:
    async with httpx.AsyncClient(timeout=180, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
    destination.write_bytes(response.content)


async def generate_one(
    provider: FeatureHunyuanModel3DProvider,
    video_id: str,
    analysis: VideoAnalysis,
    candidate: DeduplicatedObject,
    *,
    overwrite: bool,
    semaphore: asyncio.Semaphore,
    delay_sec: float,
    max_attempts: int,
) -> dict:
    output_root = video_output_dir(video_id) / "generated"
    target_dir = output_root / candidate.id
    reference_path = target_dir / REFERENCE_NAME
    if reference_path.exists() and not overwrite:
        width, height = validate_reference(reference_path)
        print(f"{video_id}/{candidate.id}: skipped ({width}x{height})", flush=True)
        return {"videoId": video_id, "candidateId": candidate.id, "status": "skipped"}

    crop_path = output_url_to_path(candidate.cropUrl)
    if crop_path is None or not crop_path.exists():
        raise FileNotFoundError(f"Missing candidate crop: {candidate.cropUrl}")
    detected_object = representative_object(analysis, candidate)
    temporary_root = video_output_dir(video_id) / ".reference_generation_tmp"
    temporary_dir = temporary_root / f"{candidate.id}_{uuid.uuid4().hex}"

    try:
        async with semaphore:
            temporary_dir.mkdir(parents=True, exist_ok=False)
            source_image = file_to_data_url(crop_path)
            brief = (
                provider._brief_from_step1(detected_object)
                if detected_object.visualFeatures and detected_object.generationHints
                else await provider._create_generation_brief(detected_object, source_image)
            )
            references = None
            last_error: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    references = await provider._create_reference_views(
                        brief,
                        temporary_dir,
                        source_image=source_image,
                    )
                    break
                except (
                    httpx.HTTPStatusError,
                    httpx.ReadTimeout,
                    httpx.ConnectTimeout,
                    httpx.RemoteProtocolError,
                ) as exc:
                    last_error = exc
                    retryable = not isinstance(exc, httpx.HTTPStatusError) or (
                        exc.response.status_code in {408, 409, 429, 500, 502, 503, 504}
                    )
                    response_detail = ""
                    if isinstance(exc, httpx.HTTPStatusError):
                        response_detail = exc.response.text[:500].replace("\n", " ")
                    print(
                        f"{video_id}/{candidate.id}: attempt {attempt}/{max_attempts} "
                        f"failed ({type(exc).__name__}: {response_detail or exc})",
                        flush=True,
                    )
                    if not retryable or attempt >= max_attempts:
                        raise
                    retry_after = (
                        exc.response.headers.get("retry-after")
                        if isinstance(exc, httpx.HTTPStatusError)
                        else None
                    )
                    try:
                        wait_seconds = float(retry_after) if retry_after else 0.0
                    except ValueError:
                        wait_seconds = 0.0
                    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
                        wait_seconds = max(wait_seconds, min(180.0, attempt * 30.0))
                    else:
                        wait_seconds = max(wait_seconds, min(30.0, attempt * 5.0))
                    await asyncio.sleep(wait_seconds)
            if references is None:
                raise RuntimeError(f"Seedream reference generation failed: {last_error}")
            if delay_sec > 0:
                await asyncio.sleep(delay_sec)

        reference = next(
            (item for item in references if item.type == "reference_oblique_3quarter"),
            None,
        )
        if reference is None:
            raise ValueError("Seedream did not return reference_oblique_3quarter")
        generated_path = Path(reference.path) if reference.path else temporary_dir / REFERENCE_NAME
        if not generated_path.exists():
            if not reference.url:
                raise ValueError("Seedream reference has neither a local path nor a URL")
            await materialize_remote_reference(reference.url, generated_path)
        width, height = validate_reference(generated_path)

        shutil.copy2(crop_path, temporary_dir / "source_crop.jpg")
        (temporary_dir / "FurnitureGenerationBrief.json").write_text(
            brief.model_dump_json(indent=2),
            encoding="utf-8",
        )
        metadata = {
            "videoId": video_id,
            "candidateId": candidate.id,
            "label": candidate.label,
            "name": candidate.name,
            "sourceCropUrl": candidate.cropUrl,
            "referenceFile": REFERENCE_NAME,
            "referenceView": "45-degree front-left oblique",
            "referenceSize": [width, height],
            "estimatedDimensions": (
                candidate.estimatedDimensions.model_dump()
                if candidate.estimatedDimensions
                else None
            ),
            "arkImageModel": provider.ark_image_model,
            "arkImageSize": provider.ark_image_size,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        }
        (temporary_dir / "generation_meta.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        target_dir.parent.mkdir(parents=True, exist_ok=True)
        if target_dir.exists():
            shutil.rmtree(target_dir)
        temporary_dir.replace(target_dir)
        print(f"{video_id}/{candidate.id}: generated ({width}x{height})", flush=True)
        return {
            "videoId": video_id,
            "candidateId": candidate.id,
            "status": "generated",
            "reference": str(target_dir / REFERENCE_NAME),
        }
    except Exception:
        shutil.rmtree(temporary_dir, ignore_errors=True)
        raise


def archive_stale_generated_directories(
    video_id: str,
    expected_candidate_ids: set[str],
) -> Path | None:
    generated_root = video_output_dir(video_id) / "generated"
    if not generated_root.exists():
        return None
    stale = [
        path
        for path in generated_root.iterdir()
        if path.is_dir() and path.name not in expected_candidate_ids
    ]
    if not stale:
        return None
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_root = video_output_dir(video_id) / f"generated_legacy_{stamp}"
    archive_root.mkdir(parents=True, exist_ok=False)
    for path in stale:
        shutil.move(str(path), str(archive_root / path.name))
    return archive_root


async def run(
    video_ids: list[str],
    *,
    overwrite: bool,
    concurrency: int,
    delay_sec: float,
    max_attempts: int,
    candidate_ids: set[str] | None,
) -> list[dict]:
    provider = build_provider()
    semaphore = asyncio.Semaphore(max(1, concurrency))
    jobs = []
    for video_id in video_ids:
        analysis = read_analysis(video_id)
        if analysis is None:
            print(f"{video_id}: skipped (analysis.json not found)", flush=True)
            continue
        candidates = [
            candidate
            for candidate in analysis.deduplicatedObjects
            if not candidate_ids or candidate.id in candidate_ids
        ]
        archive = archive_stale_generated_directories(
            video_id,
            {candidate.id for candidate in analysis.deduplicatedObjects},
        )
        if archive:
            print(f"{video_id}: archived stale generated directories to {archive}", flush=True)
        for candidate in candidates:
            jobs.append(
                (
                    video_id,
                    candidate.id,
                    asyncio.create_task(
                        generate_one(
                            provider,
                            video_id,
                            analysis,
                            candidate,
                            overwrite=overwrite,
                            semaphore=semaphore,
                            delay_sec=delay_sec,
                            max_attempts=max_attempts,
                        )
                    ),
                )
            )

    results: list[dict] = []
    for video_id, candidate_id, task in jobs:
        try:
            results.append(await task)
        except Exception as exc:  # noqa: BLE001 - finish all paid independent jobs
            print(
                f"{video_id}/{candidate_id}: failed ({type(exc).__name__}: {exc})",
                flush=True,
            )
            results.append(
                {
                    "videoId": video_id,
                    "candidateId": candidate_id,
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate one Seedream 45-degree reference image per deduplicated candidate "
            "under outputs/videos/<videoId>/generated/<candidateId>/."
        )
    )
    parser.add_argument("--video-ids", default="1-6")
    parser.add_argument("--candidate-ids", default="")
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument(
        "--delay-sec",
        type=float,
        default=0.0,
        help="Minimum cooldown after each successful Seedream request.",
    )
    parser.add_argument("--max-attempts", type=int, default=8)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    selected_candidates = {
        item.strip() for item in args.candidate_ids.split(",") if item.strip()
    }
    results = asyncio.run(
        run(
            parse_video_ids(args.video_ids),
            overwrite=args.overwrite,
            concurrency=args.concurrency,
            delay_sec=max(0.0, args.delay_sec),
            max_attempts=max(1, args.max_attempts),
            candidate_ids=selected_candidates or None,
        )
    )
    report_path = ROOT / "outputs" / "candidate_reference_generation_report.json"
    report_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    generated = sum(item["status"] == "generated" for item in results)
    skipped = sum(item["status"] == "skipped" for item in results)
    failed = sum(item["status"] == "failed" for item in results)
    print(
        f"summary: generated={generated}, skipped={skipped}, failed={failed}, "
        f"report={report_path}",
        flush=True,
    )
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
