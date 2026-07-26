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
    return _load_generated_items()


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
