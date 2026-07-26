import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Path as PathParam, UploadFile
from pydantic import BaseModel, Field

from app.schemas import EstimatedDimensions
from app.storage.local_store import OUTPUTS_ROOT, path_to_output_url


router = APIRouter()
UPLOAD_DIR = OUTPUTS_ROOT / "uploaded_furniture"
MANIFEST_PATH = UPLOAD_DIR / "manifest.json"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
GLB_MAGIC = b"glTF"
VIDEOS_DIR = OUTPUTS_ROOT / "videos"


class FurnitureItem(BaseModel):
    id: str
    name: str
    glbUrl: str
    sizeBytes: int = Field(ge=1)
    uploadedAt: str


class FurnitureUploadResponse(FurnitureItem):
    message: str


class GeneratedFurnitureItem(BaseModel):
    id: str
    videoId: str
    candidateId: str
    representativeFrameId: str
    representativeObjectId: str
    label: str
    category: str
    name: str
    previewUrl: str
    glbUrl: str
    sizeBytes: int = Field(ge=1)
    estimatedDimensions: EstimatedDimensions | None = None


def _category_for_label(label: str) -> str:
    normalized = label.lower().replace("_", " ")
    categories = (
        (("sofa",), "沙发"),
        (("bed",), "床"),
        (("table", "desk"), "桌"),
        (("chair", "armchair"), "椅"),
        (("cabinet", "bookshelf", "wardrobe", "nightstand", "tv stand"), "柜"),
        (("lamp", "light", "chandelier"), "灯"),
        (("rug", "carpet"), "地毯"),
        (("curtain",), "软装"),
        (("vase", "mirror", "painting", "plant", "decoration"), "装饰"),
    )
    return next((category for keywords, category in categories if any(keyword in normalized for keyword in keywords)), "其他")


def _load_generated_items() -> list[GeneratedFurnitureItem]:
    items: list[GeneratedFurnitureItem] = []
    if not VIDEOS_DIR.is_dir():
        return items
    for video_dir in sorted(VIDEOS_DIR.iterdir(), key=lambda path: (not path.name.isdigit(), path.name)):
        if not video_dir.is_dir() or not re.fullmatch(r"[A-Za-z0-9_-]+", video_dir.name):
            continue
        analysis_path = video_dir / "analysis.json"
        try:
            analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for candidate in analysis.get("deduplicatedObjects") or []:
            if not isinstance(candidate, dict):
                continue
            candidate_id = str(candidate.get("id") or "")
            if not re.fullmatch(r"[A-Za-z0-9_-]+", candidate_id):
                continue
            glb_path = video_dir / "glb" / f"{candidate_id}.glb"
            if not glb_path.is_file():
                glb_path = video_dir / "generated" / candidate_id / "generated_model.glb"
            preview_path = video_dir / "generated" / candidate_id / "reference_oblique_3quarter.png"
            if not glb_path.is_file() or not preview_path.is_file():
                continue
            label = str(candidate.get("label") or "furniture")
            try:
                items.append(GeneratedFurnitureItem(
                    id=f"video-{video_dir.name}-{candidate_id}",
                    videoId=video_dir.name,
                    candidateId=candidate_id,
                    representativeFrameId=str(candidate.get("representativeFrameId") or ""),
                    representativeObjectId=str(candidate.get("representativeObjectId") or ""),
                    label=label,
                    category=_category_for_label(label),
                    name=str(candidate.get("name") or label),
                    previewUrl=path_to_output_url(preview_path),
                    glbUrl=path_to_output_url(glb_path),
                    sizeBytes=glb_path.stat().st_size,
                    estimatedDimensions=candidate.get("estimatedDimensions"),
                ))
            except (OSError, ValueError):
                continue
    return items
CATEGORY_BY_LABEL = {
    "sofa": "沙发",
    "bed": "床",
    "chair": "椅",
    "armchair": "椅",
    "coffee_table": "桌",
    "dining_table": "桌",
    "desk": "桌",
    "cabinet": "柜",
    "wardrobe": "柜",
    "tv_stand": "柜",
    "bookshelf": "柜",
    "nightstand": "柜",
    "chandelier": "灯",
    "pendant_light": "灯",
    "floor_lamp": "灯",
    "table_lamp": "灯",
    "rug": "地毯",
    "curtain": "软装",
    "plant": "装饰",
    "mirror": "装饰",
    "painting": "装饰",
    "vase": "装饰",
}


def _safe_stem(filename: str) -> str:
    stem = Path(filename).stem.strip()
    cleaned = re.sub(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+", "_", stem).strip("._")
    return cleaned[:80] or "furniture"


def _load_items() -> list[FurnitureItem]:
    if not MANIFEST_PATH.exists():
        return []
    try:
        payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        return [FurnitureItem.model_validate(item) for item in payload]
    except (json.JSONDecodeError, OSError, ValueError):
        return []


def _save_items(items: list[FurnitureItem]) -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    temporary = MANIFEST_PATH.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps([item.model_dump() for item in items], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary, MANIFEST_PATH)


def _item_path(item: FurnitureItem) -> Path:
    filename = Path(item.glbUrl).name
    candidate = (UPLOAD_DIR / filename).resolve()
    try:
        candidate.relative_to(UPLOAD_DIR.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="家具文件路径无效") from exc
    return candidate


def _read_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _generated_item(model_path: Path) -> GeneratedFurnitureItem | None:
    candidate_dir = model_path.parent
    candidate_id = candidate_dir.name
    video_id = candidate_dir.parents[1].name
    result = _read_json(candidate_dir / "hunyuan_result.json")
    if not result:
        result = _read_json(candidate_dir / "generation_meta.json")
    metadata = _read_json(
        OUTPUTS_ROOT / "videos" / video_id / "deduplicated" / candidate_id / "metadata.json"
    )

    reference_meta = result.get("referenceGenerationMeta")
    reference_meta = reference_meta if isinstance(reference_meta, dict) else {}
    reference_name = Path(str(reference_meta.get("referenceFile", ""))).name
    preview_candidates = [
        candidate_dir / reference_name if reference_name else None,
        candidate_dir / "reference_oblique_3quarter.png",
        *sorted(candidate_dir.glob("reference*.png")),
    ]
    preview_path = next(
        (path for path in preview_candidates if path is not None and path.is_file()),
        None,
    )
    if preview_path is None:
        return None

    label = str(result.get("label") or metadata.get("label") or "").strip()
    if not label and candidate_id.startswith("candidate_"):
        label = re.sub(r"_\d+$", "", candidate_id.removeprefix("candidate_"))
    category_key = re.sub(r"[\s-]+", "_", label.lower())
    name = str(result.get("name") or metadata.get("name") or label or candidate_id).strip()
    dimensions = reference_meta.get("estimatedDimensions")
    if not isinstance(dimensions, dict):
        dimensions = None

    return GeneratedFurnitureItem(
        id=f"{video_id}__{candidate_id}",
        videoId=video_id,
        candidateId=candidate_id,
        representativeFrameId=str(metadata.get("representativeFrameId") or f"{video_id}_000001"),
        representativeObjectId=str(metadata.get("representativeObjectId") or candidate_id),
        label=label or "furniture",
        category=CATEGORY_BY_LABEL.get(category_key, "其他"),
        name=name,
        previewUrl=path_to_output_url(preview_path),
        glbUrl=path_to_output_url(model_path),
        sizeBytes=model_path.stat().st_size,
        estimatedDimensions=dimensions,
    )


@router.post("/upload", response_model=FurnitureUploadResponse)
async def upload_furniture_glb(file: UploadFile = File(...)) -> FurnitureUploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    if Path(file.filename).suffix.lower() != ".glb":
        raise HTTPException(status_code=400, detail="当前仅支持完整的 .glb 家具模型")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="家具模型不能为空")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="家具模型不能超过 50 MB")
    if content[:4] != GLB_MAGIC:
        raise HTTPException(status_code=400, detail="文件不是有效的 GLB 模型")

    furniture_id = f"furniture_{uuid.uuid4().hex[:12]}"
    stored_name = f"{furniture_id}_{_safe_stem(file.filename)}.glb"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    storage_path = UPLOAD_DIR / stored_name
    storage_path.write_bytes(content)

    item = FurnitureItem(
        id=furniture_id,
        name=Path(file.filename).stem[:120] or "上传家具",
        glbUrl=path_to_output_url(storage_path),
        sizeBytes=len(content),
        uploadedAt=datetime.now(timezone.utc).isoformat(),
    )
    items = [existing for existing in _load_items() if existing.id != item.id]
    items.append(item)
    try:
        _save_items(items)
    except OSError as exc:
        storage_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="家具清单保存失败") from exc

    return FurnitureUploadResponse(**item.model_dump(), message="上传成功")


@router.get("/list", response_model=list[FurnitureItem])
async def list_uploaded_furniture() -> list[FurnitureItem]:
    items = [item for item in _load_items() if _item_path(item).is_file()]
    return sorted(items, key=lambda item: item.uploadedAt, reverse=True)


@router.get("/generated", response_model=list[GeneratedFurnitureItem])
async def list_generated_furniture() -> list[GeneratedFurnitureItem]:
    items = _load_generated_items()
    known_candidates = {(item.videoId, item.candidateId) for item in items}
    generated_root = OUTPUTS_ROOT / "videos"
    if generated_root.exists():
        for model_path in generated_root.glob("*/generated/*/generated_model.glb"):
            item = _generated_item(model_path)
            if item is None or (item.videoId, item.candidateId) in known_candidates:
                continue
            items.append(item)
            known_candidates.add((item.videoId, item.candidateId))
    return sorted(items, key=lambda item: (item.category, item.name, item.videoId))


@router.delete("/{furniture_id}")
async def delete_furniture(
    furniture_id: str = PathParam(pattern=r"^furniture_[a-f0-9]{12}$"),
) -> dict[str, str]:
    items = _load_items()
    item = next((candidate for candidate in items if candidate.id == furniture_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="家具不存在")

    _item_path(item).unlink(missing_ok=True)
    _save_items([candidate for candidate in items if candidate.id != furniture_id])
    return {"message": "删除成功", "id": furniture_id}
