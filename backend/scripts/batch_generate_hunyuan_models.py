from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.schemas import DeduplicatedObject, FurnitureGenerationBrief, VideoAnalysis
from app.services.model3d.feature_hunyuan_provider import FeatureHunyuanModel3DProvider
from app.services.video_preprocess.analysis_store import read_analysis, video_output_dir
from app.storage.local_store import file_to_data_url


REFERENCE_NAME = "reference_oblique_3quarter.png"
BRIEF_NAME = "FurnitureGenerationBrief.json"
META_NAME = "generation_meta.json"
TASK_NAME = "hunyuan_task.json"
RESULT_NAME = "hunyuan_result.json"
MODEL_NAME = "generated_model.glb"


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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_provider() -> FeatureHunyuanModel3DProvider:
    settings = get_settings()
    if not settings.hunyuan_api_key:
        raise RuntimeError("HUNYUAN_API_KEY is required")
    return FeatureHunyuanModel3DProvider(
        ark_api_key=settings.ark_api_key or "unused-for-existing-reference",
        ark_base_url=settings.ark_base_url,
        ark_vision_model=settings.ark_vision_model,
        ark_image_model=settings.ark_image_model,
        ark_image_size=settings.ark_image_size,
        hunyuan_api_key=settings.hunyuan_api_key,
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


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def existing_result_model(result_path: Path, task_path: Path) -> str:
    if result_path.exists():
        result = load_json(result_path)
        model = str(result.get("model") or "")
        if model:
            return model
    if task_path.exists():
        task = load_json(task_path)
        return str((task.get("request") or {}).get("model") or "")
    return ""


def archive_existing_attempt(
    folder: Path,
    *,
    model_path: Path,
    task_path: Path,
    result_path: Path,
) -> Path | None:
    existing = [path for path in (model_path, task_path, result_path) if path.exists()]
    if not existing:
        return None

    task_state = load_json(task_path) if task_path.exists() else {}
    result_state = load_json(result_path) if result_path.exists() else {}
    previous_model = str(
        result_state.get("model")
        or (task_state.get("request") or {}).get("model")
        or "unknown-model"
    )
    task_id = str(
        result_state.get("taskId") or task_state.get("taskId") or "unknown-task"
    )
    archive_name = f"{previous_model}_{task_id}".replace("/", "_").replace("\\", "_")
    archive_dir = folder / "hunyuan_attempts" / archive_name
    if archive_dir.exists():
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive_dir = archive_dir.with_name(f"{archive_name}_{timestamp}")
    archive_dir.mkdir(parents=True, exist_ok=False)
    for path in existing:
        shutil.copy2(path, archive_dir / path.name)
    return archive_dir


def validate_glb(path: Path) -> int:
    if not path.exists():
        raise FileNotFoundError(path)
    size = path.stat().st_size
    if size < 20:
        raise ValueError(f"GLB is unexpectedly small: {size} bytes")
    with path.open("rb") as handle:
        if handle.read(4) != b"glTF":
            raise ValueError(f"Downloaded file is not a binary GLB: {path}")
    return size


def validate_candidate_inputs(
    video_id: str,
    candidate: DeduplicatedObject,
) -> tuple[Path, FurnitureGenerationBrief, dict]:
    folder = video_output_dir(video_id) / "generated" / candidate.id
    reference_path = folder / REFERENCE_NAME
    brief_path = folder / BRIEF_NAME
    metadata_path = folder / META_NAME
    for path in (reference_path, brief_path, metadata_path):
        if not path.exists():
            raise FileNotFoundError(f"Missing candidate generation input: {path}")

    brief = FurnitureGenerationBrief.model_validate_json(
        brief_path.read_text(encoding="utf-8")
    )
    metadata = load_json(metadata_path)
    if brief.objectId != candidate.id:
        raise ValueError(
            f"Brief objectId mismatch for {candidate.id}: {brief.objectId}"
        )
    if metadata.get("candidateId") != candidate.id:
        raise ValueError(f"Generation metadata mismatch for {candidate.id}")
    if metadata.get("referenceView") != "45-degree front-left oblique":
        raise ValueError(f"Unexpected reference view for {candidate.id}")

    expected_dimensions = (
        candidate.estimatedDimensions.model_dump()
        if candidate.estimatedDimensions
        else None
    )
    brief_dimensions = brief.constraints.get("physicalDimensionsMeters")
    if expected_dimensions and brief_dimensions:
        for field_name in ("widthM", "depthM", "heightM"):
            if brief_dimensions.get(field_name) != expected_dimensions.get(field_name):
                raise ValueError(
                    f"Dimension mismatch for {candidate.id}/{field_name}"
                )
    return reference_path, brief, metadata


async def download_glb(url: str, destination: Path) -> int:
    async with httpx.AsyncClient(timeout=240, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
    temporary = destination.with_suffix(".glb.download")
    temporary.write_bytes(response.content)
    size = validate_glb(temporary)
    temporary.replace(destination)
    return size


def request_provenance(
    provider: FeatureHunyuanModel3DProvider,
    reference_path: Path,
    brief: FurnitureGenerationBrief,
) -> dict:
    image_bytes = reference_path.read_bytes()
    provenance = {
        "endpoint": provider._submit_url(),
        "model": provider.hunyuan_model,
        "inputMode": "image_base64",
        "imageFile": REFERENCE_NAME,
        "imageBytes": len(image_bytes),
        "imageSha256": hashlib.sha256(image_bytes).hexdigest(),
        "promptSentToHunyuan": False,
        "promptProtocolNote": (
            "Hunyuan Normal image-to-3D forbids Prompt together with ImageBase64. "
            "The recorded generationBriefPrompt was already used upstream to create "
            "this exact 45-degree Seedream reference."
        ),
        "generationBriefPrompt": brief.prompt,
        "negativePrompt": brief.negativePrompt,
        "constraints": brief.constraints,
        "enablePbr": provider.hunyuan_enable_pbr,
    }
    if provider.hunyuan_model == "hy-3d-express":
        provenance.update(
            {
                "generationMode": "rapid",
                "resultFormatSent": provider.hunyuan_result_format,
                "enableGeometrySent": provider.hunyuan_enable_geometry,
                "generateTypeSent": None,
                "faceCountSent": None,
            }
        )
    else:
        provenance.update(
            {
                "generationMode": "professional",
                "generateTypeSent": provider.hunyuan_generate_type,
                "faceCountMode": (
                    "custom"
                    if provider.hunyuan_face_count is not None
                    else "provider_default"
                ),
                "faceCountSent": provider.hunyuan_face_count,
            }
        )
    return provenance


async def submit(
    provider: FeatureHunyuanModel3DProvider,
    reference_path: Path,
    brief: FurnitureGenerationBrief,
    task_path: Path,
) -> tuple[str, dict]:
    started = time.perf_counter()
    try:
        task_id = await provider._create_3d_task(
            [file_to_data_url(reference_path)],
            brief,
        )
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:2000]
        raise RuntimeError(
            f"Hunyuan submit HTTP {exc.response.status_code}: {detail}"
        ) from exc
    submit_sec = round(time.perf_counter() - started, 3)
    state = {
        "taskId": task_id,
        "status": "SUBMITTED",
        "submittedAt": now_iso(),
        "submitSec": submit_sec,
        "request": request_provenance(provider, reference_path, brief),
    }
    save_json(task_path, state)
    return task_id, state


async def poll(
    provider: FeatureHunyuanModel3DProvider,
    task_id: str,
    *,
    interval_sec: float,
    attempts: int,
    candidate_key: str,
) -> tuple[dict, float]:
    started = time.perf_counter()
    previous_status = ""
    async with httpx.AsyncClient(timeout=90) as client:
        for attempt in range(1, attempts + 1):
            try:
                result = await provider._query_once(client, task_id)
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text[:2000]
                raise RuntimeError(
                    f"Hunyuan query HTTP {exc.response.status_code}: {detail}"
                ) from exc
            status = provider._normalize_status(result)
            elapsed = time.perf_counter() - started
            if status != previous_status or attempt == 1 or attempt % 12 == 0:
                print(
                    f"{candidate_key}: status={status} "
                    f"poll={attempt}/{attempts} elapsed={elapsed:.1f}s",
                    flush=True,
                )
                previous_status = status
            if status == "SUCCEEDED":
                result.setdefault("status", status)
                return result, round(elapsed, 3)
            if status in {"FAILED", "EXPIRED"}:
                raise RuntimeError(
                    f"Hunyuan task {task_id} ended with {status}: "
                    f"{json.dumps(result, ensure_ascii=False)[:2000]}"
                )
            await asyncio.sleep(interval_sec)
    raise TimeoutError(
        f"Hunyuan task {task_id} did not finish after "
        f"{attempts * interval_sec:.1f}s"
    )


async def run_candidate(
    provider: FeatureHunyuanModel3DProvider,
    video_id: str,
    analysis: VideoAnalysis,
    candidate: DeduplicatedObject,
    *,
    interval_sec: float,
    attempts: int,
    resubmit: bool,
) -> dict:
    candidate_key = f"{video_id}/{candidate.id}"
    folder = video_output_dir(video_id) / "generated" / candidate.id
    model_path = folder / MODEL_NAME
    task_path = folder / TASK_NAME
    result_path = folder / RESULT_NAME
    if model_path.exists() and not resubmit:
        saved_model = existing_result_model(result_path, task_path)
        if saved_model and saved_model.lower() != provider.hunyuan_model.lower():
            raise RuntimeError(
                f"{candidate_key}: existing GLB uses {saved_model}, but current "
                f"model is {provider.hunyuan_model}. Use --resubmit to create a "
                "new model; the existing attempt will be archived first."
            )
        size = validate_glb(model_path)
        print(f"{candidate_key}: skipped existing GLB ({size} bytes)", flush=True)
        return {
            "videoId": video_id,
            "candidateId": candidate.id,
            "status": "skipped",
            "modelPath": str(model_path),
            "modelBytes": size,
        }

    if resubmit:
        archive_dir = archive_existing_attempt(
            folder,
            model_path=model_path,
            task_path=task_path,
            result_path=result_path,
        )
        if archive_dir is not None:
            print(
                f"{candidate_key}: archived previous attempt to {archive_dir}",
                flush=True,
            )

    reference_path, brief, metadata = validate_candidate_inputs(video_id, candidate)
    candidate_started = time.perf_counter()
    if task_path.exists() and not resubmit:
        task_state = load_json(task_path)
        task_id = str(task_state.get("taskId") or "")
        if not task_id:
            raise ValueError(f"Invalid saved task file: {task_path}")
        saved_model = str(
            (task_state.get("request") or {}).get("model") or ""
        ).lower()
        if saved_model and saved_model != provider.hunyuan_model.lower():
            raise RuntimeError(
                f"Saved task {task_id} uses {saved_model}, but current model is "
                f"{provider.hunyuan_model}. Use --resubmit to explicitly create "
                "a task with the current model."
            )
        if str(task_state.get("status") or "").upper() in {"FAILED", "EXPIRED"}:
            raise RuntimeError(
                f"Saved Hunyuan task {task_id} is {task_state['status']}. "
                "Use --resubmit to explicitly create a new task."
            )
        print(f"{candidate_key}: resuming task {task_id}", flush=True)
    else:
        print(
            f"{candidate_key}: submitting {provider.hunyuan_model} with "
            f"{REFERENCE_NAME}; brief={BRIEF_NAME}",
            flush=True,
        )
        task_id, task_state = await submit(
            provider,
            reference_path,
            brief,
            task_path,
        )
        print(
            f"{candidate_key}: taskId={task_id} "
            f"submit={task_state['submitSec']:.1f}s",
            flush=True,
        )

    try:
        result, poll_sec = await poll(
            provider,
            task_id,
            interval_sec=interval_sec,
            attempts=attempts,
            candidate_key=candidate_key,
        )
    except RuntimeError as exc:
        failure_text = str(exc)
        terminal_status = (
            "EXPIRED" if " ended with EXPIRED:" in failure_text else "FAILED"
        )
        failed_at = now_iso()
        task_state.update(
            {
                "status": terminal_status,
                "failedAt": failed_at,
                "error": failure_text,
            }
        )
        save_json(task_path, task_state)
        save_json(
            result_path,
            {
                "videoId": video_id,
                "candidateId": candidate.id,
                "status": terminal_status,
                "taskId": task_id,
                "model": provider.hunyuan_model,
                "referenceImage": str(reference_path),
                "promptProvenance": request_provenance(
                    provider, reference_path, brief
                ),
                "failedAt": failed_at,
                "error": failure_text,
            },
        )
        raise RuntimeError(
            f"{failure_text} The failure was saved; use --resubmit only to "
            "explicitly create a new task."
        ) from exc
    glb_url = provider._extract_glb_url(result)
    if not glb_url:
        raise RuntimeError(
            f"Hunyuan succeeded but returned no GLB URL: "
            f"{json.dumps(result, ensure_ascii=False)[:2000]}"
        )

    download_started = time.perf_counter()
    model_bytes = await download_glb(glb_url, model_path)
    download_sec = round(time.perf_counter() - download_started, 3)
    run_sec = round(time.perf_counter() - candidate_started, 3)
    submitted_at = task_state.get("submittedAt")
    end_to_end_sec = run_sec
    if submitted_at:
        try:
            submitted_time = datetime.fromisoformat(str(submitted_at))
            end_to_end_sec = round(
                (datetime.now(timezone.utc) - submitted_time).total_seconds(),
                3,
            )
        except ValueError:
            pass
    record = {
        "videoId": video_id,
        "candidateId": candidate.id,
        "label": candidate.label,
        "name": candidate.name,
        "status": "SUCCEEDED",
        "taskId": task_id,
        "model": provider.hunyuan_model,
        "referenceImage": str(reference_path),
        "referenceGenerationMeta": metadata,
        "promptProvenance": request_provenance(provider, reference_path, brief),
        "remoteGlbUrl": glb_url,
        "localGlb": str(model_path),
        "modelBytes": model_bytes,
        "timings": {
            "submitSec": task_state.get("submitSec", 0.0),
            "pollSecThisRun": poll_sec,
            "downloadSec": download_sec,
            "candidateRunSec": run_sec,
            "endToEndSinceSubmitSec": end_to_end_sec,
        },
        "completedAt": now_iso(),
        "rawResult": result,
    }
    save_json(result_path, record)
    task_state.update({"status": "SUCCEEDED", "completedAt": record["completedAt"]})
    save_json(task_path, task_state)
    print(
        f"{candidate_key}: done total={end_to_end_sec:.1f}s "
        f"poll={poll_sec:.1f}s download={download_sec:.1f}s "
        f"glb={model_bytes} bytes",
        flush=True,
    )
    return record


async def run(
    video_ids: list[str],
    *,
    candidate_ids: set[str] | None,
    interval_sec: float,
    attempts: int,
    resubmit: bool,
) -> tuple[list[dict], float]:
    provider = build_provider()
    supported_models = {"hy-3d-3.1", "hy-3d-express"}
    if provider.hunyuan_model not in supported_models:
        raise RuntimeError(
            f"Expected HUNYUAN_MODEL in {sorted(supported_models)}, "
            f"got {provider.hunyuan_model}"
        )
    if (
        provider.hunyuan_model == "hy-3d-3.1"
        and provider.hunyuan_generate_type != "Normal"
    ):
        raise RuntimeError(
            f"Expected HUNYUAN_GENERATE_TYPE=Normal, "
            f"got {provider.hunyuan_generate_type}"
        )
    if (
        provider.hunyuan_model == "hy-3d-express"
        and provider.hunyuan_result_format != "GLB"
    ):
        raise RuntimeError(
            f"Express batch download requires HUNYUAN_RESULT_FORMAT=GLB, "
            f"got {provider.hunyuan_result_format}"
        )

    started = time.perf_counter()
    results: list[dict] = []
    for video_id in video_ids:
        analysis = read_analysis(video_id)
        if analysis is None:
            raise FileNotFoundError(f"analysis.json not found for video {video_id}")
        candidates = [
            candidate
            for candidate in analysis.deduplicatedObjects
            if not candidate_ids or candidate.id in candidate_ids
        ]
        for candidate in candidates:
            results.append(
                await run_candidate(
                    provider,
                    video_id,
                    analysis,
                    candidate,
                    interval_sec=interval_sec,
                    attempts=attempts,
                    resubmit=resubmit,
                )
            )
    return results, round(time.perf_counter() - started, 3)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Submit existing candidate 45-degree Seedream references directly to "
            "Hunyuan 3D 3.1 or Express, preserving brief/prompt provenance and "
            "recording timings."
        )
    )
    parser.add_argument("--video-ids", default="2")
    parser.add_argument("--candidate-ids", default="")
    parser.add_argument("--poll-interval-sec", type=float, default=5.0)
    parser.add_argument("--poll-attempts", type=int, default=180)
    parser.add_argument(
        "--resubmit",
        action="store_true",
        help="Submit a new paid task even when a saved task or GLB exists.",
    )
    args = parser.parse_args()
    selected_candidates = {
        item.strip() for item in args.candidate_ids.split(",") if item.strip()
    }
    video_ids = parse_video_ids(args.video_ids)
    batch_started_at = now_iso()
    try:
        results, batch_sec = asyncio.run(
            run(
                video_ids,
                candidate_ids=selected_candidates or None,
                interval_sec=max(1.0, args.poll_interval_sec),
                attempts=max(1, args.poll_attempts),
                resubmit=args.resubmit,
            )
        )
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}", flush=True)
        raise

    report = {
        "videoIds": video_ids,
        "model": get_settings().hunyuan_model,
        "batchStartedAt": batch_started_at,
        "batchCompletedAt": now_iso(),
        "batchTotalSec": batch_sec,
        "candidateCount": len(results),
        "results": results,
    }
    if len(video_ids) == 1:
        report_path = (
            video_output_dir(video_ids[0]) / "hunyuan_batch_report.json"
        )
    else:
        report_path = ROOT / "outputs" / "hunyuan_batch_report.json"
    save_json(report_path, report)
    print(
        f"SUMMARY candidates={len(results)} total={batch_sec:.1f}s "
        f"({batch_sec / 60:.2f}min) report={report_path}",
        flush=True,
    )


if __name__ == "__main__":
    main()
