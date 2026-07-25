import re
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.config import get_settings
from app.schemas import (
    DetectResponse,
    VideoAnalysis,
    VideoAnalysisFrame,
    VideoPreprocessRequest,
    VideoPreprocessResponse,
    VideoUploadResponse,
    ManualFrameItem,
    ManualFrameSaveRequest,
    ManualFramesResponse,
)
from app.services.detection.ark_grounding_provider import ArkGroundingProvider
from app.services.detection.grounded_sam2_provider import GroundedSAM2DetectionProvider
from app.services.detection.grounding_dino_provider import GroundingDinoProvider
from app.services.segmentation.sam_box_provider import SamBoxProvider
from app.services.shop_store import append_search_result, resolve_media_path, whitened_results
from app.services.video_preprocess.ark_grounding_pipeline import ArkGroundingPipeline
from app.services.video_preprocess.doubao_grounding_sam_pipeline import DoubaoGroundingSamPipeline
from app.services.video_preprocess.analysis_store import analysis_url, nearest_frame, read_analysis, video_output_dir
from app.services.video_preprocess.clip_deduplicator import ClipFurnitureDeduplicator
from app.services.video_preprocess.dimension_estimator import ArkFurnitureDimensionEstimator
from app.services.video_preprocess.preprocessor import VideoPreprocessor
from app.services.vision_semantics.doubao_provider import DoubaoVisionProvider
from app.storage.local_store import BACKEND_ROOT, OUTPUTS_ROOT, path_to_output_url, save_data_url


router = APIRouter()

SUPPORTED_VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".avi", ".webm"}


class ClipSearchRequest(BaseModel):
    cropUrl: str | None = None
    image: str | None = None
    bbox: list[int] | None = Field(default=None, min_length=4, max_length=4)
    topK: int = Field(default=3, ge=1, le=20)
    imageName: str | None = None
    analysis: dict | None = None
    hint: dict | None = None
    textWeight: float = Field(default=0.45, ge=0.0, le=1.0)
    textOnly: bool = False
    persist: bool = True


def _retrieval_python() -> Path:
    candidate = BACKEND_ROOT / ".venv-retrieval" / "Scripts" / "python.exe"
    if candidate.exists():
        return candidate
    alt = BACKEND_ROOT / ".venv-retrieval" / "bin" / "python"
    if alt.exists():
        return alt
    raise HTTPException(
        status_code=503,
        detail="Missing .venv-retrieval. Create it per docs/product_clip_offline.md",
    )


def _crop_from_data_url(image: str, bbox: list[int], output_path: Path) -> Path:
    import base64
    import io

    from PIL import Image

    if "," in image:
        _, encoded = image.split(",", 1)
    else:
        encoded = image
    raw = base64.b64decode(encoded)
    with Image.open(io.BytesIO(raw)) as img:
        rgb = img.convert("RGB")
        x1, y1, x2, y2 = [int(v) for v in bbox]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(rgb.width, x2), min(rgb.height, y2)
        if x2 <= x1 or y2 <= y1:
            raise HTTPException(status_code=400, detail="Invalid bbox for crop")
        cropped = rgb.crop((x1, y1, x2, y2))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cropped.save(output_path, format="JPEG", quality=90)
    return output_path


def _resolve_search_hint(request: ClipSearchRequest) -> dict | None:
    if request.hint:
        return request.hint
    if not request.analysis:
        return None
    hints_dir = BACKEND_ROOT / "scripts" / "product_retrieval"
    if str(hints_dir) not in sys.path:
        sys.path.insert(0, str(hints_dir))
    from hints import find_object_hint  # noqa: WPS433

    ref = request.imageName or request.cropUrl or ""
    return find_object_hint(request.analysis, ref)


def _run_clip_search(
    image_path: Path | None,
    top_k: int,
    *,
    hint: dict | None = None,
    text_weight: float = 0.45,
    text_only: bool = False,
) -> dict:
    python_exe = _retrieval_python()
    script = BACKEND_ROOT / "scripts" / "product_retrieval" / "search.py"
    pretrained = BACKEND_ROOT / "data" / "product_index" / "ViT-B-32.pt"
    hints_path: Path | None = None
    cmd = [
        str(python_exe),
        str(script),
        "--top-k",
        str(top_k),
        "--text-weight",
        str(text_weight),
        "--json",
    ]
    if text_only:
        cmd.append("--text-only")
    elif image_path is not None:
        cmd.extend(["--image", str(image_path)])
    else:
        raise HTTPException(status_code=400, detail="Image path required unless textOnly=true")
    if pretrained.exists():
        cmd.extend(["--pretrained", str(pretrained)])
    try:
        if hint:
            hints_path = Path(tempfile.mkdtemp(prefix="clip_hints_")) / "hint.json"
            hints_path.write_text(json.dumps(hint, ensure_ascii=False), encoding="utf-8")
            cmd.extend(["--hints-json", str(hints_path)])
            if hint.get("label"):
                cmd.extend(["--label", str(hint["label"])])
        completed = subprocess.run(
            cmd,
            cwd=str(BACKEND_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="CLIP search timed out") from exc
    finally:
        if hints_path is not None:
            try:
                shutil.rmtree(hints_path.parent, ignore_errors=True)
            except Exception:  # noqa: BLE001
                pass
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "clip search failed").strip()
        raise HTTPException(status_code=500, detail=detail[-800:])
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Invalid CLIP search JSON output") from exc
    return payload


def _whiten_matches_payload(payload: dict) -> dict:
    matches = payload.get("matches")
    if isinstance(matches, dict):
        whitened = {}
        for key, value in matches.items():
            if not isinstance(value, dict):
                whitened[key] = value
                continue
            row = dict(value)
            row["products"] = whitened_results(value.get("products") or [])
            whitened[key] = row
        payload = {**payload, "matches": whitened}
    if "results" in payload:
        payload = {**payload, "results": whitened_results(payload.get("results"))}
    payload.pop("source", None)
    if payload.get("provider") in {"ikea", "ikea_clip", "ikea_clip_live"}:
        payload["provider"] = "local_clip"
    return payload


def _validate_video_id(video_id: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", video_id):
        raise HTTPException(status_code=400, detail="videoId may only contain letters, numbers, underscores, and hyphens")


def _manual_manifest_path(video_id: str) -> Path:
    return video_output_dir(video_id) / "frames.json"


def _read_manual_manifest(video_id: str) -> dict:
    path = _manual_manifest_path(video_id)
    if not path.exists():
        return {"videoId": video_id, "frames": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload.get("frames"), list):
            raise ValueError
        return payload
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail=f"Invalid frame manifest for videoId={video_id}") from exc


def _manifest_response(video_id: str, manifest: dict) -> ManualFramesResponse:
    frame_dir = video_output_dir(video_id) / "frames"
    frames = []
    for item in sorted(manifest.get("frames", []), key=lambda value: float(value["timeSec"])):
        file_name = Path(str(item["fileName"])).name
        frame_path = frame_dir / file_name
        if frame_path.exists():
            frames.append(
                ManualFrameItem(
                    timeSec=float(item["timeSec"]),
                    timeMs=int(item.get("timeMs", round(float(item["timeSec"]) * 1000))),
                    fileName=file_name,
                    imageUrl=path_to_output_url(frame_path),
                )
            )
    return ManualFramesResponse(
        videoId=video_id,
        sourceFileName=manifest.get("sourceFileName") or manifest.get("sourceVideo"),
        durationSec=manifest.get("durationSec"),
        samplingMode=manifest.get("samplingMode"),
        frames=frames,
    )


def _write_manual_manifest(video_id: str, manifest: dict) -> None:
    path = _manual_manifest_path(video_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(".json.tmp")
    temporary_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary_path.replace(path)
    analysis_file = path.parent / "analysis.json"
    if analysis_file.exists():
        analysis_file.unlink()
    deduplicated_dir = path.parent / "deduplicated"
    if deduplicated_dir.exists():
        shutil.rmtree(deduplicated_dir)
    objects_dir = path.parent / "objects"
    if objects_dir.exists():
        shutil.rmtree(objects_dir)


@router.get("/manual-frames/{video_id}", response_model=ManualFramesResponse)
async def get_manual_frames(video_id: str) -> ManualFramesResponse:
    _validate_video_id(video_id)
    return _manifest_response(video_id, _read_manual_manifest(video_id))


@router.post("/manual-frames", response_model=ManualFramesResponse)
async def save_manual_frame(request: ManualFrameSaveRequest) -> ManualFramesResponse:
    _validate_video_id(request.videoId)
    if request.timeSec > request.durationSec + 0.05:
        raise HTTPException(status_code=400, detail="timeSec exceeds video duration")

    time_ms = round(request.timeSec * 1000)
    file_name = f"frame_t{time_ms:09d}ms.jpg"
    frame_dir = video_output_dir(request.videoId) / "frames"
    frame_path = frame_dir / file_name
    save_data_url(request.frameImage, frame_path)

    manifest = _read_manual_manifest(request.videoId)
    records = [item for item in manifest.get("frames", []) if int(item.get("timeMs", -1)) != time_ms]
    records.append(
        {
            "timeSec": round(request.timeSec, 6),
            "timeMs": time_ms,
            "fileName": file_name,
        }
    )
    records.sort(key=lambda item: item["timeMs"])
    intervals = [right["timeSec"] - left["timeSec"] for left, right in zip(records, records[1:])]
    manifest = {
        "videoId": request.videoId,
        "sourceFileName": Path(request.sourceFileName).name,
        "durationSec": round(request.durationSec, 6),
        "samplingMode": "manual",
        "plannedFrameCount": len(records),
        "retainedFrameCount": len(records),
        "samplingIntervalSec": round(min(intervals), 6) if intervals else 1.0,
        "frames": records,
    }
    _write_manual_manifest(request.videoId, manifest)
    return _manifest_response(request.videoId, manifest)


@router.delete("/manual-frames/{video_id}/{time_ms}", response_model=ManualFramesResponse)
async def delete_manual_frame(video_id: str, time_ms: int) -> ManualFramesResponse:
    _validate_video_id(video_id)
    manifest = _read_manual_manifest(video_id)
    records = [item for item in manifest.get("frames", []) if int(item.get("timeMs", -1)) != time_ms]
    frame_path = video_output_dir(video_id) / "frames" / f"frame_t{time_ms:09d}ms.jpg"
    if frame_path.exists():
        frame_path.unlink()
    manifest["frames"] = records
    manifest["plannedFrameCount"] = len(records)
    manifest["retainedFrameCount"] = len(records)
    _write_manual_manifest(video_id, manifest)
    return _manifest_response(video_id, manifest)


@router.delete("/manual-frames/{video_id}", response_model=ManualFramesResponse)
async def clear_manual_frames(video_id: str) -> ManualFramesResponse:
    _validate_video_id(video_id)
    manifest = _read_manual_manifest(video_id)
    frame_dir = video_output_dir(video_id) / "frames"
    for frame_path in frame_dir.glob("frame_t*ms.jpg"):
        frame_path.unlink()
    manifest["frames"] = []
    manifest["samplingMode"] = "manual"
    manifest["plannedFrameCount"] = 0
    manifest["retainedFrameCount"] = 0
    _write_manual_manifest(video_id, manifest)
    return _manifest_response(video_id, manifest)


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    request: Request,
    videoId: str = Query(min_length=1, max_length=80),
    fileName: str = Query(min_length=1, max_length=255),
) -> VideoUploadResponse:
    _validate_video_id(videoId)
    suffix = Path(fileName).suffix.lower()
    if suffix not in SUPPORTED_VIDEO_SUFFIXES:
        raise HTTPException(status_code=400, detail=f"Unsupported video type: {suffix or 'missing extension'}")

    output_dir = video_output_dir(videoId)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"source{suffix}"
    temporary_path = output_dir / f"source{suffix}.uploading"
    size_bytes = 0
    try:
        with temporary_path.open("wb") as output:
            async for chunk in request.stream():
                if not chunk:
                    continue
                output.write(chunk)
                size_bytes += len(chunk)
        if size_bytes == 0:
            raise HTTPException(status_code=400, detail="Uploaded video is empty")
        temporary_path.replace(output_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    return VideoUploadResponse(
        videoId=videoId,
        fileName=fileName,
        videoUrl=f"/outputs/videos/{videoId}/{output_path.name}",
        sizeBytes=size_bytes,
    )


def get_grounded_sam2_provider() -> GroundedSAM2DetectionProvider | None:
    settings = get_settings()
    if not settings.grounded_sam2_endpoint:
        return None
    return GroundedSAM2DetectionProvider(
        endpoint=settings.grounded_sam2_endpoint,
        api_key=settings.grounded_sam2_api_key,
        prompt=settings.grounded_sam2_prompt,
        max_objects=settings.grounded_sam2_max_objects,
        min_confidence=settings.grounded_sam2_min_confidence,
    )


def get_doubao_grounding_sam_pipeline() -> DoubaoGroundingSamPipeline | None:
    settings = get_settings()
    if not settings.doubao_endpoint or not settings.doubao_api_key or not settings.grounding_dino_endpoint:
        return None

    sam_provider = (
        SamBoxProvider(endpoint=settings.sam_endpoint, api_key=settings.sam_api_key)
        if settings.sam_endpoint
        else None
    )
    return DoubaoGroundingSamPipeline(
        doubao_provider=DoubaoVisionProvider(
            endpoint=settings.doubao_endpoint,
            api_key=settings.doubao_api_key,
            model=settings.doubao_model,
        ),
        grounding_dino_provider=GroundingDinoProvider(
            endpoint=settings.grounding_dino_endpoint,
            api_key=settings.grounding_dino_api_key,
            min_confidence=settings.grounding_dino_min_confidence,
            max_objects=settings.grounding_dino_max_objects,
        ),
        sam_provider=sam_provider,
    )


def get_ark_grounding_pipeline() -> ArkGroundingPipeline | None:
    settings = get_settings()
    if not settings.ark_api_key:
        return None
    return ArkGroundingPipeline(
        grounding_provider=ArkGroundingProvider(
            api_key=settings.ark_api_key,
            base_url=settings.ark_base_url,
            model=settings.ark_vision_model,
        )
    )


@router.post("/preprocess", response_model=VideoPreprocessResponse)
async def preprocess_video(request: VideoPreprocessRequest) -> VideoPreprocessResponse:
    settings = get_settings()
    if request.mode == "grounded_sam2" and not get_settings().grounded_sam2_endpoint:
        raise HTTPException(status_code=500, detail="GROUNDED_SAM2_ENDPOINT is required for grounded_sam2 mode")
    if request.mode == "doubao_grounding_sam" and not get_doubao_grounding_sam_pipeline():
        raise HTTPException(
            status_code=500,
            detail="DOUBAO_ENDPOINT, DOUBAO_API_KEY, and GROUNDING_DINO_ENDPOINT are required for doubao_grounding_sam mode",
        )
    if request.mode == "ark_grounding" and not get_ark_grounding_pipeline():
        raise HTTPException(status_code=500, detail="ARK_API_KEY is required for ark_grounding mode")
    try:
        analysis = await VideoPreprocessor(
            grounded_sam2_provider=get_grounded_sam2_provider(),
            doubao_grounding_sam_pipeline=get_doubao_grounding_sam_pipeline(),
            ark_grounding_pipeline=get_ark_grounding_pipeline(),
            furniture_deduplicator=ClipFurnitureDeduplicator(
                threshold=settings.furniture_dedupe_threshold,
                batch_size=settings.furniture_dedupe_batch_size,
                model_name=settings.furniture_dedupe_model,
                device=settings.furniture_dedupe_device,
            ),
            dimension_estimator=(
                ArkFurnitureDimensionEstimator(
                    api_key=settings.ark_api_key,
                    base_url=settings.ark_base_url,
                    model=settings.ark_vision_model,
                )
                if request.mode == "ark_grounding" and settings.ark_api_key
                else None
            ),
            furniture_dedupe_enabled=settings.furniture_dedupe_enabled,
        ).preprocess(request)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc
    return VideoPreprocessResponse(
        videoId=analysis.videoId,
        status=analysis.status,
        frameCount=len(analysis.frames),
        detectedObjectCount=sum(len(frame.objects) for frame in analysis.frames),
        deduplicatedObjectCount=len(analysis.deduplicatedObjects),
        analysisUrl=analysis_url(analysis.videoId),
    )


@router.get("/analysis/{video_id}", response_model=VideoAnalysis)
async def get_analysis(video_id: str) -> VideoAnalysis:
    analysis = read_analysis(video_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Video analysis not found")
    return analysis


@router.get("/analysis/{video_id}/nearest", response_model=VideoAnalysisFrame)
async def get_nearest_analysis_frame(video_id: str, time: float = Query(ge=0)) -> VideoAnalysisFrame:
    frame = nearest_frame(video_id, time)
    if not frame:
        raise HTTPException(status_code=404, detail="Video analysis frame not found")
    return frame


@router.get("/detect/{video_id}", response_model=DetectResponse)
async def detect_from_analysis(video_id: str, time: float = Query(ge=0)) -> DetectResponse:
    frame = nearest_frame(video_id, time)
    if not frame:
        raise HTTPException(status_code=404, detail="Video analysis frame not found")
    return DetectResponse(frameId=frame.frameId, objects=frame.objects, frameImageUrl=frame.frameImageUrl)


@router.get("/{video_id}/product-matches")
async def get_product_matches(video_id: str) -> dict:
    """Return offline CLIP match cache for a video (white-labeled, local only)."""
    _validate_video_id(video_id)
    path = video_output_dir(video_id) / "product_matches.json"
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"product_matches.json not found for videoId={video_id}. "
                "Run scripts/product_retrieval/batch_match_vedios_all.py first."
            ),
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Invalid product_matches.json") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="Invalid product_matches.json")
    return _whiten_matches_payload(payload)


@router.post("/clip-search")
async def clip_search_products(request: ClipSearchRequest) -> dict:
    """Live CLIP search; results are white-labeled and appended to local shop log."""
    temp_path: Path | None = None
    try:
        hint = _resolve_search_hint(request)
        text_only = bool(request.textOnly)
        image_path: Path | None = None

        if text_only:
            if not hint:
                raise HTTPException(
                    status_code=400,
                    detail="textOnly search requires hint or analysis JSON keywords",
                )
        elif request.cropUrl:
            image_path = resolve_media_path(request.cropUrl)
            if image_path is None or not image_path.exists():
                relative = request.cropUrl.lstrip("/").removeprefix("outputs/")
                candidate = OUTPUTS_ROOT / Path(relative)
                image_path = candidate if candidate.exists() else None
            if image_path is None or not image_path.exists():
                raise HTTPException(status_code=404, detail=f"cropUrl not found: {request.cropUrl}")
        elif request.image and request.bbox:
            temp_path = Path(tempfile.mkdtemp(prefix="clip_search_")) / "crop.jpg"
            image_path = _crop_from_data_url(request.image, request.bbox, temp_path)
        elif request.image:
            temp_dir = Path(tempfile.mkdtemp(prefix="clip_search_"))
            temp_path = temp_dir / "query.jpg"
            import base64
            import io

            from PIL import Image

            if "," in request.image:
                _, encoded = request.image.split(",", 1)
            else:
                encoded = request.image
            raw = base64.b64decode(encoded)
            with Image.open(io.BytesIO(raw)) as img:
                img.convert("RGB").save(temp_path, format="JPEG", quality=92)
            image_path = temp_path
        else:
            raise HTTPException(status_code=400, detail="Provide cropUrl, image, or image + bbox")

        payload = _run_clip_search(
            image_path,
            request.topK,
            hint=hint,
            text_weight=1.0 if text_only else request.textWeight,
            text_only=text_only,
        )
        results = whitened_results(payload.get("results") or [])
        response = {
            "source": "local_clip_text" if text_only else "local_clip",
            "topK": request.topK,
            "queryText": payload.get("queryText"),
            "label": payload.get("label") or (hint or {}).get("label"),
            "hint": hint,
            "textOnly": text_only,
            "textWeight": 1.0 if text_only else request.textWeight,
            "results": results,
        }
        if request.persist:
            append_search_result(
                {
                    "query": {
                        "cropUrl": request.cropUrl,
                        "imageName": request.imageName,
                        "label": response.get("label"),
                        "queryText": response.get("queryText"),
                        "topK": request.topK,
                        "textOnly": text_only,
                    },
                    "results": results,
                }
            )
        return response
    finally:
        if temp_path is not None:
            try:
                shutil.rmtree(temp_path.parent, ignore_errors=True)
            except Exception:  # noqa: BLE001
                pass
