import json
import re
from io import BytesIO

import httpx
from PIL import Image

from app.schemas import DetectedObject
from app.services.vision_semantics.label_policy import (
    bbox_area_ratio,
    dedupe_objects,
    is_allowed_label,
    label_name,
    normalize_label,
    tag_position,
)
from app.storage.local_store import data_url_to_bytes


ARK_GROUNDING_PROMPT = """请检测这张室内家装图片中适合打暂停 tag 的主要家具和家居物品。
只允许从以下英文类别中选择：
sofa, bed, chair, armchair, dining_table, coffee_table, desk,
cabinet, wardrobe, tv_stand, bookshelf, nightstand,
chandelier, pendant_light, floor_lamp, table_lamp,
rug, curtain, plant, vase, mirror, painting.

不要输出餐具、食物、书本、小摆件、人物、宠物。
最多输出 6 个。
请只输出 JSON 数组：
[
  {
    "category": "dining_table",
    "name": "餐桌",
    "bbox": "<bbox>x1 y1 x2 y2</bbox>"
  }
]
bbox 坐标必须是 0 到 999 的整数。
"""


class ArkGroundingProvider:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def detect(self, image_data_url: str) -> list[DetectedObject]:
        image = Image.open(BytesIO(data_url_to_bytes(image_data_url))).convert("RGB")
        image_width, image_height = image.size
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                        {"type": "text", "text": ARK_GROUNDING_PROMPT},
                    ],
                }
            ],
            "temperature": 0,
        }
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        raw_items = self._parse_items(self._extract_text(data))
        objects: list[DetectedObject] = []
        for index, item in enumerate(raw_items, start=1):
            label = normalize_label(str(item.get("category") or item.get("label") or ""))
            if not is_allowed_label(label):
                continue
            bbox = self._parse_bbox(str(item.get("bbox") or ""))
            if bbox is None:
                continue
            pixel_bbox = self._scale_ark_bbox(bbox, image_width, image_height)
            if bbox_area_ratio(pixel_bbox, image_width, image_height) < 0.01:
                continue
            objects.append(
                DetectedObject(
                    id=f"obj_{label}_{index:03d}",
                    label=label,
                    name=label_name(label, str(item.get("name") or "")),
                    confidence=float(item.get("confidence") or item.get("score") or 1.0),
                    bbox=pixel_bbox,
                    tagPosition=tag_position(pixel_bbox, image_width, image_height),
                )
            )
        return dedupe_objects(objects, max_items=6)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _extract_text(self, data: dict) -> str:
        if "choices" in data:
            message = data["choices"][0].get("message", {})
            content = message.get("content", "")
            if isinstance(content, list):
                return "".join(str(item.get("text", "")) for item in content if isinstance(item, dict))
            return str(content)
        return json.dumps(data, ensure_ascii=False)

    def _parse_items(self, text: str) -> list[dict]:
        cleaned = text.strip()
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\[.*\]", cleaned, flags=re.S)
            if not match:
                return []
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                return []
        if isinstance(parsed, dict):
            parsed = parsed.get("objects", [])
        return parsed if isinstance(parsed, list) else []

    def _parse_bbox(self, raw: str) -> list[int] | None:
        match = re.search(r"<bbox>\s*([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s*</bbox>", raw)
        if not match:
            nums = re.findall(r"\d+", raw)
            if len(nums) < 4:
                return None
            values = [int(value) for value in nums[:4]]
        else:
            values = [int(value) for value in match.groups()]
        if len(values) != 4:
            return None
        return [max(0, min(value, 999)) for value in values]

    def _scale_ark_bbox(self, bbox: list[int], image_width: int, image_height: int) -> list[int]:
        left = int(round(bbox[0] * image_width / 1000))
        top = int(round(bbox[1] * image_height / 1000))
        right = int(round(bbox[2] * image_width / 1000))
        bottom = int(round(bbox[3] * image_height / 1000))
        return [
            max(0, min(left, image_width - 1)),
            max(0, min(top, image_height - 1)),
            max(1, min(right, image_width)),
            max(1, min(bottom, image_height)),
        ]
