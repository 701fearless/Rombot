"""Product attribute recognition via Ark vision with mock fallback."""

from __future__ import annotations

import json
import re
from pathlib import Path

import httpx

from app.config import get_settings
from app.schemas import ProductAttributes, ProductRecognizeRequest, ProductRecognizeResponse
from app.services.product.prompts import PRODUCT_RECOGNIZE_PROMPT
from app.storage.local_store import BACKEND_ROOT, file_to_data_url, output_url_to_path


DEFAULT_SIZE_BY_CATEGORY: dict[str, list[float]] = {
    "sofa": [2.0, 0.85, 0.9],
    "coffee_table": [1.0, 0.4, 0.55],
    "dining_table": [1.5, 0.75, 0.9],
    "desk": [1.2, 0.75, 0.6],
    "cabinet": [1.2, 0.8, 0.4],
    "wardrobe": [1.6, 2.0, 0.55],
    "tv_stand": [1.5, 0.45, 0.4],
    "bookshelf": [0.8, 1.8, 0.3],
    "armchair": [0.8, 0.85, 0.8],
    "chair": [0.45, 0.85, 0.5],
    "chandelier": [0.6, 0.45, 0.6],
    "floor_lamp": [0.35, 1.6, 0.35],
    "table_lamp": [0.25, 0.45, 0.25],
    "rug": [2.0, 0.01, 1.4],
}

DISPLAY_NAME_BY_CATEGORY: dict[str, str] = {
    "sofa": "布艺沙发",
    "coffee_table": "茶几",
    "dining_table": "餐桌",
    "desk": "书桌",
    "cabinet": "储物柜",
    "wardrobe": "衣柜",
    "tv_stand": "电视柜",
    "bookshelf": "书架",
    "armchair": "单人沙发椅",
    "chair": "餐椅",
    "chandelier": "吊灯",
    "floor_lamp": "落地灯",
    "table_lamp": "台灯",
    "rug": "地毯",
}

MOCK_ATTRS_BY_CATEGORY: dict[str, dict[str, str]] = {
    "sofa": {"color": "米色", "material": "布艺", "style": "现代"},
    "coffee_table": {"color": "原木色", "material": "实木", "style": "现代"},
    "dining_table": {"color": "胡桃木色", "material": "实木", "style": "现代"},
    "desk": {"color": "白色", "material": "密度板", "style": "极简"},
    "cabinet": {"color": "橡木色", "material": "实木", "style": "北欧"},
    "wardrobe": {"color": "白色", "material": "密度板", "style": "现代"},
    "tv_stand": {"color": "黑色", "material": "密度板", "style": "现代"},
    "bookshelf": {"color": "橡木色", "material": "实木", "style": "北欧"},
    "armchair": {"color": "米色", "material": "布艺", "style": "现代"},
    "chair": {"color": "浅木色", "material": "实木", "style": "北欧"},
    "chandelier": {"color": "金色", "material": "金属", "style": "现代"},
    "floor_lamp": {"color": "原木色", "material": "实木", "style": "北欧"},
    "table_lamp": {"color": "米白", "material": "陶瓷", "style": "日式"},
    "rug": {"color": "暖橙", "material": "涤纶", "style": "现代"},
}


def _normalize_category(raw: str | None) -> str:
    if not raw:
        return "sofa"
    key = raw.strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "couch": "sofa",
        "sofa_bed": "sofa",
        "table": "coffee_table",
        "茶几": "coffee_table",
        "沙发": "sofa",
        "灯": "chandelier",
    }
    key = aliases.get(key, key)
    if key in DEFAULT_SIZE_BY_CATEGORY:
        return key
    return key or "sofa"


def _guess_category_from_object_id(object_id: str | None) -> str | None:
    if not object_id:
        return None
    # obj_sofa_001 / sofa_1
    lower = object_id.lower()
    for cat in DEFAULT_SIZE_BY_CATEGORY:
        if cat in lower:
            return cat
    return None


def resolve_image_data_url(request: ProductRecognizeRequest) -> str | None:
    if request.image and request.image.startswith("data:"):
        return request.image
    if request.image and not request.image.startswith("/"):
        # bare base64
        return f"data:image/jpeg;base64,{request.image}"

    url = request.cropUrl
    if not url:
        return None

    if url.startswith("data:"):
        return url

    path: Path | None = None
    if url.startswith("/outputs/"):
        path = output_url_to_path(url)
    elif url.startswith("/sample_data/"):
        path = BACKEND_ROOT / url.lstrip("/").replace("/", "\\")
    elif Path(url).exists():
        path = Path(url)

    if path and path.exists():
        return file_to_data_url(path)
    return None


def mock_recognize(
    *,
    label: str | None = None,
    object_id: str | None = None,
) -> ProductRecognizeResponse:
    category = _normalize_category(label or _guess_category_from_object_id(object_id) or "sofa")
    attrs = MOCK_ATTRS_BY_CATEGORY.get(category, {"color": "中性色", "material": "混合", "style": "现代"})
    size = list(DEFAULT_SIZE_BY_CATEGORY.get(category, [1.0, 0.8, 0.6]))
    name = DISPLAY_NAME_BY_CATEGORY.get(category, category)
    tags = [category, attrs.get("color", ""), attrs.get("material", ""), attrs.get("style", "")]
    tags = [t for t in tags if t]
    # English-ish tags for search
    color_en = {
        "米色": "beige",
        "灰色": "gray",
        "白色": "white",
        "黑色": "black",
        "原木色": "wood",
        "金色": "gold",
        "暖橙": "warm",
        "奶油色": "cream",
        "深棕": "brown",
        "胡桃木色": "walnut",
        "橡木色": "oak",
        "浅木色": "light_wood",
        "米白": "offwhite",
        "中性色": "neutral",
    }
    material_en = {
        "布艺": "fabric",
        "真皮": "leather",
        "实木": "wood",
        "密度板": "mdf",
        "金属": "metal",
        "涤纶": "polyester",
        "陶瓷": "ceramic",
        "人造石": "stone",
        "混合": "mixed",
    }
    if attrs.get("color") in color_en:
        tags.append(color_en[attrs["color"]])
    if attrs.get("material") in material_en:
        tags.append(material_en[attrs["material"]])

    return ProductRecognizeResponse(
        category=category,
        name=name,
        attributes=ProductAttributes(
            color=attrs.get("color"),
            material=attrs.get("material"),
            style=attrs.get("style"),
        ),
        estimatedSize_m=size,
        sizeConfidence="low",
        queryTags=list(dict.fromkeys(tags)),
        source="mock",
    )


def _parse_json_object(text: str) -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", cleaned, flags=re.S)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}


def _from_ark_payload(data: dict, fallback_label: str | None) -> ProductRecognizeResponse:
    category = _normalize_category(str(data.get("category") or fallback_label or "sofa"))
    attrs_raw = data.get("attributes") if isinstance(data.get("attributes"), dict) else {}
    size_raw = data.get("estimatedSize_m") or data.get("size_m") or DEFAULT_SIZE_BY_CATEGORY.get(category, [1.0, 0.8, 0.6])
    size = [float(size_raw[i]) if i < len(size_raw) else 0.8 for i in range(3)]
    tags = data.get("queryTags") if isinstance(data.get("queryTags"), list) else []
    tags = [str(t) for t in tags if t]
    if category not in tags:
        tags = [category, *tags]
    conf = str(data.get("sizeConfidence") or "medium").lower()
    if conf not in {"low", "medium", "high"}:
        conf = "medium"
    return ProductRecognizeResponse(
        category=category,
        name=str(data.get("name") or DISPLAY_NAME_BY_CATEGORY.get(category, category)),
        attributes=ProductAttributes(
            color=(str(attrs_raw["color"]) if attrs_raw.get("color") else None),
            material=(str(attrs_raw["material"]) if attrs_raw.get("material") else None),
            style=(str(attrs_raw["style"]) if attrs_raw.get("style") else None),
        ),
        estimatedSize_m=size,
        sizeConfidence=conf,
        queryTags=list(dict.fromkeys(tags))[:10],
        source="ark",
    )


async def recognize_product(request: ProductRecognizeRequest) -> ProductRecognizeResponse:
    settings = get_settings()
    label = request.label or _guess_category_from_object_id(request.objectId)
    image_data_url = resolve_image_data_url(request)

    if not settings.ark_api_key or not image_data_url:
        return mock_recognize(label=label, object_id=request.objectId)

    hint = f"\n可选类别提示：{label}" if label else ""
    payload = {
        "model": settings.ark_vision_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                    {"type": "text", "text": PRODUCT_RECOGNIZE_PROMPT + hint},
                ],
            }
        ],
        "temperature": 0,
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.ark_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.ark_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        message = data.get("choices", [{}])[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            text = "".join(str(item.get("text", "")) for item in content if isinstance(item, dict))
        else:
            text = str(content)
        parsed = _parse_json_object(text)
        if not parsed:
            return mock_recognize(label=label, object_id=request.objectId)
        return _from_ark_payload(parsed, label)
    except Exception:
        return mock_recognize(label=label, object_id=request.objectId)
