from __future__ import annotations

import base64
import binascii
import json
import uuid
from io import BytesIO
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Request
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field, model_validator

from app.config import get_settings
from app.services.floorplan_whitebox.ai_parser import ArkFloorplanParser
from app.services.floorplan_whitebox.schemas import FloorplanWhiteboxScene
from app.services.floorplan_whitebox.whitebox_builder import build_whitebox_glb
from app.storage.local_store import BACKEND_ROOT, OUTPUTS_ROOT, path_to_output_url


router = APIRouter()
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
KNOWN_LENGTH_WARNING = "knownLength was recorded but not applied to scale calibration"
FLOORPLAN_PRESETS_ROOT = BACKEND_ROOT / "sample_data" / "floorplans"
FLOORPLAN_PRESETS_MANIFEST = FLOORPLAN_PRESETS_ROOT / "presets.json"


class KnownLengthHint(BaseModel):
    pixelStart: list[float] | None = Field(default=None, min_length=2, max_length=2)
    pixelEnd: list[float] | None = Field(default=None, min_length=2, max_length=2)
    meters: float | None = Field(default=None, gt=0)


class FloorplanReconstructRequest(BaseModel):
    image: str | None = None
    imagePath: str | None = None
    knownLength: KnownLengthHint | None = None
    sceneId: str | None = None

    @model_validator(mode="after")
    def validate_image_source(self) -> "FloorplanReconstructRequest":
        if bool(self.image) == bool(self.imagePath):
            raise ValueError("Exactly one of image or imagePath is required")
        return self


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


class FloorplanPreset(BaseModel):
    sceneId: str
    title: str
    sourceImageUrl: str
    sourceSha256: str
    sceneUrl: str
    whiteboxGlbUrl: str
    quality: str


class FloorplanPresetsResponse(BaseModel):
    presets: list[FloorplanPreset]


def _read_floorplan_presets() -> list[FloorplanPreset]:
    if not FLOORPLAN_PRESETS_MANIFEST.exists():
        return []
    try:
        payload = json.loads(FLOORPLAN_PRESETS_MANIFEST.read_text(encoding="utf-8"))
        records = payload.get("presets", payload) if isinstance(payload, dict) else payload
        return [FloorplanPreset.model_validate(item) for item in records]
    except (OSError, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Floorplan preset manifest is invalid: {exc}",
        ) from exc


@router.get("/presets", response_model=FloorplanPresetsResponse)
async def list_floorplan_presets() -> FloorplanPresetsResponse:
    return FloorplanPresetsResponse(presets=_read_floorplan_presets())


@router.get("/presets/{scene_id}", response_model=FloorplanPreset)
async def get_floorplan_preset(scene_id: str) -> FloorplanPreset:
    preset = next(
        (item for item in _read_floorplan_presets() if item.sceneId == scene_id),
        None,
    )
    if preset is None:
        raise HTTPException(status_code=404, detail="Floorplan preset not found")
    return preset


class FloorplanWhiteboxSaveResponse(BaseModel):
    sceneId: str
    status: str
    whiteboxGlbUrl: str
    bytesWritten: int


@router.put("/presets/{scene_id}/whitebox", response_model=FloorplanWhiteboxSaveResponse)
async def save_floorplan_preset_whitebox(
    scene_id: str,
    request: Request,
) -> FloorplanWhiteboxSaveResponse:
    """Overwrite a preset whitebox.glb with an edited sandbox export (local demo)."""
    cleaned = _clean_scene_id(scene_id)
    if not cleaned:
        raise HTTPException(status_code=400, detail="Invalid sceneId")

    preset = next(
        (item for item in _read_floorplan_presets() if item.sceneId == cleaned),
        None,
    )
    if preset is None:
        raise HTTPException(status_code=404, detail="Floorplan preset not found")

    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty GLB body")
    if len(body) > 80 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="GLB exceeds 80 MB")
    if body[:4] != b"glTF":
        raise HTTPException(status_code=415, detail="Body must be a binary GLB (glTF)")

    target = (FLOORPLAN_PRESETS_ROOT / "preprocessed" / cleaned / "whitebox.glb").resolve()
    root = (FLOORPLAN_PRESETS_ROOT / "preprocessed").resolve()
    if target != root and root not in target.parents:
        raise HTTPException(status_code=400, detail="Invalid whitebox path")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)

    return FloorplanWhiteboxSaveResponse(
        sceneId=cleaned,
        status="saved",
        whiteboxGlbUrl=f"/sample_data/floorplans/preprocessed/{cleaned}/whitebox.glb",
        bytesWritten=len(body),
    )


@router.post("/reconstruct", response_model=FloorplanReconstructResponse)
async def reconstruct_floorplan(
    request: FloorplanReconstructRequest,
) -> FloorplanReconstructResponse:
    settings = get_settings()
    if not settings.ark_api_key:
        raise HTTPException(
            status_code=500,
            detail="ARK_API_KEY is required for floorplan AI parsing",
        )

    scene_id = _clean_scene_id(request.sceneId) or f"floorplan_{uuid.uuid4().hex[:10]}"
    output_dir = OUTPUTS_ROOT / "floorplans" / scene_id
    output_dir.mkdir(parents=True, exist_ok=True)

    source_bytes = _load_image_bytes(request, settings.floorplan_max_upload_mb)
    image = _decode_image(source_bytes)
    original_path = output_dir / "original.png"
    image.save(original_path, format="PNG", optimize=True)

    ai_image_data_url = _prepare_ai_image_data_url(
        image,
        settings.floorplan_ai_input_max_side,
    )
    ai_input_path = output_dir / "ai_input.jpg"
    ai_input_path.write_bytes(_decode_data_url(ai_image_data_url))

    parser = ArkFloorplanParser(
        api_key=settings.ark_api_key,
        base_url=settings.ark_base_url,
        model=settings.ark_vision_model,
        timeout_sec=settings.floorplan_ai_timeout_sec,
    )
    try:
        result = await parser.parse(ai_image_data_url)
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:1000] if exc.response is not None else str(exc)
        status_code = exc.response.status_code if exc.response is not None else 502
        if status_code == 429 or any(
            marker in detail for marker in ("TooManyRequests", "SetLimitExceeded")
        ):
            raise HTTPException(
                status_code=429,
                detail=f"Floorplan AI request was rate limited: {detail}",
            ) from exc
        raise HTTPException(
            status_code=502,
            detail=f"Floorplan AI request failed: {detail}",
        ) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="Floorplan AI request timed out",
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        detail = str(exc) or exc.__class__.__name__
        raise HTTPException(
            status_code=502,
            detail=f"Floorplan AI parsing failed: {detail}",
        ) from exc

    scene = _force_whitebox_defaults(result.scene)
    scene.sceneId = scene_id
    warnings = list(result.warnings)
    if request.knownLength:
        warnings.append(KNOWN_LENGTH_WARNING)

    normalized_scene_path = output_dir / "normalized_scene.json"
    ai_raw_path = output_dir / "ai_raw.json"
    glb_path = output_dir / "whitebox.glb"

    normalized_scene_path.write_text(scene.model_dump_json(indent=2), encoding="utf-8")
    ai_raw_path.write_text(
        json.dumps(
            {
                "rawText": result.raw_text,
                "parsed": result.parsed_json,
                "warnings": warnings,
                "knownLength": (
                    request.knownLength.model_dump() if request.knownLength else None
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    try:
        build_whitebox_glb(scene, glb_path)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Floorplan geometry could not be built: {exc}",
        ) from exc

    return FloorplanReconstructResponse(
        sceneId=scene_id,
        status="succeeded",
        sceneUrl=path_to_output_url(normalized_scene_path),
        whiteboxGlbUrl=path_to_output_url(glb_path),
        aiRawUrl=path_to_output_url(ai_raw_path),
        originalImageUrl=path_to_output_url(original_path),
        warnings=warnings,
    )


@router.post("/build-whitebox", response_model=FloorplanBuildWhiteboxResponse)
async def build_whitebox_from_scene(
    scene: FloorplanWhiteboxScene,
) -> FloorplanBuildWhiteboxResponse:
    scene_id = _clean_scene_id(scene.sceneId) or f"floorplan_json_{uuid.uuid4().hex[:10]}"
    normalized_scene = _force_whitebox_defaults(scene)
    normalized_scene.sceneId = scene_id
    output_dir = OUTPUTS_ROOT / "floorplans" / scene_id
    output_dir.mkdir(parents=True, exist_ok=True)

    normalized_scene_path = output_dir / "normalized_scene.json"
    glb_path = output_dir / "whitebox.glb"
    normalized_scene_path.write_text(
        normalized_scene.model_dump_json(indent=2),
        encoding="utf-8",
    )
    try:
        build_whitebox_glb(normalized_scene, glb_path)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Floorplan geometry could not be built: {exc}",
        ) from exc

    return FloorplanBuildWhiteboxResponse(
        sceneId=scene_id,
        status="succeeded",
        sceneUrl=path_to_output_url(normalized_scene_path),
        whiteboxGlbUrl=path_to_output_url(glb_path),
        warnings=[],
    )


def _load_image_bytes(
    request: FloorplanReconstructRequest,
    max_upload_mb: int,
) -> bytes:
    if request.image:
        data = _decode_data_url(request.image)
    else:
        image_path = _resolve_allowed_image_path(request.imagePath or "")
        if not image_path.exists() or not image_path.is_file():
            raise HTTPException(
                status_code=404,
                detail=f"Image not found: {request.imagePath}",
            )
        data = image_path.read_bytes()

    max_bytes = max_upload_mb * 1024 * 1024
    if not data:
        raise HTTPException(status_code=400, detail="Floorplan image is empty")
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Floorplan image exceeds {max_upload_mb} MB",
        )
    return data


def _resolve_allowed_image_path(image_path: str) -> Path:
    roots = {
        "/sample_data/floorplans/": (BACKEND_ROOT / "sample_data" / "floorplans").resolve(),
        "/outputs/": OUTPUTS_ROOT.resolve(),
    }
    for prefix, root in roots.items():
        if image_path.startswith(prefix):
            relative = image_path[len(prefix) :]
            candidate = (root / relative).resolve()
            if candidate == root or root in candidate.parents:
                return candidate
            break
    raise HTTPException(
        status_code=400,
        detail="imagePath must stay under /sample_data/floorplans/ or /outputs/",
    )


def _decode_image(data: bytes) -> Image.Image:
    try:
        source = Image.open(BytesIO(data))
        source.verify()
        source = Image.open(BytesIO(data))
        image_format = (source.format or "").upper()
        if image_format not in ALLOWED_IMAGE_FORMATS:
            raise HTTPException(
                status_code=415,
                detail="Floorplan image must be JPEG, PNG, or WebP",
            )
        width, height = source.size
        if width <= 0 or height <= 0 or width * height > 40_000_000:
            raise HTTPException(
                status_code=413,
                detail="Floorplan image dimensions are invalid or too large",
            )
        return source.convert("RGB")
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Floorplan image could not be decoded",
        ) from exc


def _decode_data_url(data_url: str) -> bytes:
    if not data_url.startswith("data:image/") or ";base64," not in data_url:
        raise HTTPException(
            status_code=400,
            detail="image must be a base64 image Data URL",
        )
    _, encoded = data_url.split(",", 1)
    try:
        return base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail="image contains invalid base64 data",
        ) from exc


def _prepare_ai_image_data_url(image: Image.Image, max_side: int) -> str:
    width, height = image.size
    scale = min(1.0, max_side / max(width, height))
    if scale < 1:
        image = image.resize(
            (round(width * scale), round(height * scale)),
            Image.Resampling.LANCZOS,
        )
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=88, optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _clean_scene_id(scene_id: str | None) -> str | None:
    if not scene_id:
        return None
    cleaned = "".join(
        character if character.isalnum() or character in {"_", "-"} else "_"
        for character in scene_id.strip()
    )
    return cleaned[:64] or None


def _force_whitebox_defaults(
    scene: FloorplanWhiteboxScene,
) -> FloorplanWhiteboxScene:
    data = scene.model_dump()
    data["wallHeight"] = 3.0
    data["defaultWallThickness"] = 0.1
    for wall in data["walls"]:
        wall["height"] = 3.0
        wall["thickness"] = 0.1
    return FloorplanWhiteboxScene.model_validate(data)
