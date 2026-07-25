from __future__ import annotations

import json
import uuid
from io import BytesIO
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from PIL import Image
from pydantic import BaseModel, Field

from app.config import get_settings
from app.services.floorplan_whitebox.schemas import FloorplanWhiteboxScene
from app.services.floorplan_whitebox.ai_parser import ArkFloorplanParser
from app.services.floorplan_whitebox.whitebox_builder import build_whitebox_glb
from app.storage.local_store import BACKEND_ROOT, OUTPUTS_ROOT, file_to_data_url, path_to_output_url, save_data_url


router = APIRouter()
AI_INPUT_MAX_SIDE = 768


class KnownLengthHint(BaseModel):
    pixelStart: list[float] | None = Field(default=None, min_length=2, max_length=2)
    pixelEnd: list[float] | None = Field(default=None, min_length=2, max_length=2)
    meters: float | None = Field(default=None, gt=0)


class FloorplanReconstructRequest(BaseModel):
    image: str | None = None
    imagePath: str | None = None
    knownLength: KnownLengthHint | None = None
    sceneId: str | None = None


class FloorplanReconstructResponse(BaseModel):
    sceneId: str
    status: str
    sceneUrl: str
    whiteboxGlbUrl: str
    aiRawUrl: str
    originalImageUrl: str
    warnings: list[str]


class FloorplanBuildWhiteboxResponse(BaseModel):
    sceneId: str
    status: str
    sceneUrl: str
    whiteboxGlbUrl: str
    warnings: list[str]


@router.post("/reconstruct", response_model=FloorplanReconstructResponse)
async def reconstruct_floorplan(request: FloorplanReconstructRequest) -> FloorplanReconstructResponse:
    settings = get_settings()
    if not settings.ark_api_key:
        raise HTTPException(status_code=500, detail="ARK_API_KEY is required for floorplan AI parsing")

    scene_id = _clean_scene_id(request.sceneId) or f"floorplan_{uuid.uuid4().hex[:10]}"
    output_dir = OUTPUTS_ROOT / "floorplans" / scene_id
    output_dir.mkdir(parents=True, exist_ok=True)

    image_data_url = _load_image_data_url(request)
    original_path = save_data_url(image_data_url, output_dir / "original.png")
    ai_image_data_url = _prepare_ai_image_data_url(image_data_url)
    if ai_image_data_url != image_data_url:
        save_data_url(ai_image_data_url, output_dir / "ai_input.jpg")

    parser = ArkFloorplanParser(
        api_key=settings.ark_api_key,
        base_url=settings.ark_base_url,
        model=settings.ark_vision_model,
    )
    try:
        result = await parser.parse(ai_image_data_url)
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:1000] if exc.response is not None else str(exc)
        status_code = exc.response.status_code if exc.response is not None else 502
        if status_code == 429 or "TooManyRequests" in detail or "SetLimitExceeded" in detail:
            raise HTTPException(status_code=429, detail=f"Floorplan AI request was rate limited: {detail}") from exc
        raise HTTPException(status_code=502, detail=f"Floorplan AI request failed: {detail}") from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Floorplan AI request timed out") from exc
    except (httpx.HTTPError, ValueError) as exc:
        detail = str(exc) or exc.__class__.__name__
        raise HTTPException(status_code=502, detail=f"Floorplan AI parsing failed: {detail}") from exc

    scene = result.scene
    scene.sceneId = scene_id
    normalized_scene_path = output_dir / "normalized_scene.json"
    ai_raw_path = output_dir / "ai_raw.json"
    glb_path = output_dir / "whitebox.glb"

    normalized_scene_path.write_text(scene.model_dump_json(indent=2), encoding="utf-8")
    ai_raw_path.write_text(
        json.dumps(
            {
                "rawText": result.raw_text,
                "parsed": result.parsed_json,
                "warnings": result.warnings,
                "knownLength": request.knownLength.model_dump() if request.knownLength else None,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    build_whitebox_glb(scene, glb_path)

    return FloorplanReconstructResponse(
        sceneId=scene_id,
        status="succeeded",
        sceneUrl=path_to_output_url(normalized_scene_path),
        whiteboxGlbUrl=path_to_output_url(glb_path),
        aiRawUrl=path_to_output_url(ai_raw_path),
        originalImageUrl=path_to_output_url(original_path),
        warnings=result.warnings,
    )


@router.post("/build-whitebox", response_model=FloorplanBuildWhiteboxResponse)
async def build_whitebox_from_scene(scene: FloorplanWhiteboxScene) -> FloorplanBuildWhiteboxResponse:
    scene_id = _clean_scene_id(scene.sceneId) or f"floorplan_json_{uuid.uuid4().hex[:10]}"
    scene.sceneId = scene_id
    scene = _force_whitebox_defaults(scene)
    output_dir = OUTPUTS_ROOT / "floorplans" / scene_id
    output_dir.mkdir(parents=True, exist_ok=True)

    normalized_scene_path = output_dir / "normalized_scene.json"
    glb_path = output_dir / "whitebox.glb"
    normalized_scene_path.write_text(scene.model_dump_json(indent=2), encoding="utf-8")
    build_whitebox_glb(scene, glb_path)

    return FloorplanBuildWhiteboxResponse(
        sceneId=scene_id,
        status="succeeded",
        sceneUrl=path_to_output_url(normalized_scene_path),
        whiteboxGlbUrl=path_to_output_url(glb_path),
        warnings=[],
    )


def _load_image_data_url(request: FloorplanReconstructRequest) -> str:
    if request.image:
        return request.image
    if not request.imagePath:
        raise HTTPException(status_code=400, detail="Either image or imagePath is required")
    image_path = _resolve_image_path(request.imagePath)
    if not image_path.exists():
        raise HTTPException(status_code=404, detail=f"Image not found: {request.imagePath}")
    return file_to_data_url(image_path)


def _resolve_image_path(image_path: str) -> Path:
    if image_path.startswith("/sample_data/") or image_path.startswith("/outputs/"):
        return (BACKEND_ROOT / image_path.lstrip("/")).resolve()
    path = Path(image_path)
    if path.is_absolute():
        return path
    return (BACKEND_ROOT / path).resolve()


def _clean_scene_id(scene_id: str | None) -> str | None:
    if not scene_id:
        return None
    cleaned = "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in scene_id.strip())
    return cleaned[:64] or None


def _force_whitebox_defaults(scene: FloorplanWhiteboxScene) -> FloorplanWhiteboxScene:
    data = scene.model_dump()
    data["wallHeight"] = 3.0
    data["defaultWallThickness"] = 0.1
    for wall in data["walls"]:
        wall["height"] = 3.0
        wall["thickness"] = 0.1
    return FloorplanWhiteboxScene.model_validate(data)


def _prepare_ai_image_data_url(image_data_url: str) -> str:
    raw = _decode_data_url(image_data_url)
    try:
        image = Image.open(BytesIO(raw)).convert("RGB")
    except Exception:
        return image_data_url
    width, height = image.size
    scale = min(1.0, AI_INPUT_MAX_SIDE / max(width, height))
    if scale < 1.0:
        image = image.resize((round(width * scale), round(height * scale)), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=88, optimize=True)
    import base64

    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _decode_data_url(data_url: str) -> bytes:
    import base64

    if "," in data_url:
        _, encoded = data_url.split(",", 1)
    else:
        encoded = data_url
    return base64.b64decode(encoded)
