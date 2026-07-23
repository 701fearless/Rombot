import base64
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


ARK_GROUNDING_PROMPT = """
Analyze the room image once and return the main furniture/home objects that are
useful for tagging and later single-object 3D generation.

Allowed category values only:
sofa, bed, chair, armchair, dining_table, coffee_table, desk,
cabinet, wardrobe, tv_stand, bookshelf, nightstand,
chandelier, pendant_light, floor_lamp, table_lamp,
rug, curtain, plant, vase, mirror, painting.

Return one compact JSON object and nothing else:
{
  "objects": [
    {
      "category": "sofa",
      "name": "沙发",
      "confidence": 0.95,
      "bbox": "<bbox>x1 y1 x2 y2</bbox>",
      "features": {
        "geometry": "compact description of silhouette, proportions and visible components",
        "materials": ["visible material"],
        "colors": ["dominant color"],
        "style": "conservative style description",
        "texturePattern": "grain, weave, print or repeated motif",
        "visibleComponents": ["evidence-backed part"]
      },
      "generationHints": {
        "clutterState": "clean|messy|occluded",
        "cleanupActions": ["specific action for a clean product presentation"],
        "symmetry": {
          "type": "bilateral|axial|radial|repeated_modules|none",
          "completionRule": "how missing regular structure should be completed"
        },
        "occlusionCompletion": ["conservative category-based completion"],
        "patternCompletion": "continue visible repeated texture without blank gaps",
        "preserve": ["identity-defining visible feature"],
        "remove": ["temporary clutter or unrelated occluder"]
      }
    }
  ]
}

Rules:
- Return at most 4 objects, ordered by foreground/product salience. Prefer complete,
  centered foreground objects; if the image is a product-demo screenshot, return the
  demonstrated central object before large border-touching background furniture.
- Keep each string under 16 words and each list at no more than 3 items.
- bbox coordinates must be integers from 0 to 999.
- Exclude people, hands, pets, food, tableware, books, loose small decorations,
  phone UI, captions and unrelated background objects.
- Describe visible evidence in features. Put inferred cleanup/completion only in generationHints.
- Regularize ordinary household disorder before image generation while preserving
  the product identity, style, material and color:
  * bed: straighten and center blankets/duvets, align pillows, remove clothes;
  * sofa/armchair: align cushions and pillows, smooth throws, restore repeated seats;
  * table/desk/nightstand: clear dishes, cables and loose items, preserve built-in parts;
  * cabinet/wardrobe/bookshelf/tv stand: align doors/drawers/handles and repeated modules;
  * chair: center removable cushions and restore paired legs/arms;
  * rug/curtain: flatten curled edges or arrange regular hanging folds;
  * lamp/vase/mirror/painting: restore axial/bilateral symmetry, continuous borders,
    complete repeated decorative patterns, and remove hands or temporary contents.
- For unseen or occluded parts, prefer symmetry, repeated modules, continuous material,
  closed outlines and standard category structure. Do not invent bizarre shapes,
  random ornaments, extra components or over-designed furniture.
"""


class ArkGroundingProvider:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.last_response_text = ""

    async def detect(self, image_data_url: str) -> list[DetectedObject]:
        image = Image.open(BytesIO(data_url_to_bytes(image_data_url))).convert("RGB")
        image_width, image_height = image.size
        vision_image = self._prepare_vision_image(image)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": vision_image}},
                        {"type": "text", "text": ARK_GROUNDING_PROMPT},
                    ],
                }
            ],
            "temperature": 0,
            "max_tokens": 1200,
            "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
        }
        timeout = httpx.Timeout(connect=20, read=120, write=30, pool=20)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        self.last_response_text = self._extract_text(data)
        raw_items = self._parse_items(self.last_response_text)
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
                    confidence=self._confidence(item.get("confidence") or item.get("score")),
                    bbox=pixel_bbox,
                    tagPosition=tag_position(pixel_bbox, image_width, image_height),
                    visualFeatures=self._dict_value(item.get("features")),
                    generationHints=self._dict_value(item.get("generationHints") or item.get("generation_hints")),
                )
            )
        return dedupe_objects(objects, max_items=6)

    def _prepare_vision_image(self, image: Image.Image, max_side: int = 1280) -> str:
        width, height = image.size
        scale = min(1.0, max_side / max(width, height))
        if scale < 1.0:
            image = image.resize(
                (max(1, int(round(width * scale))), max(1, int(round(height * scale)))),
                Image.Resampling.LANCZOS,
            )
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=84, optimize=True)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"

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
            match = re.search(r"\{.*\}|\[.*\]", cleaned, flags=re.S)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                except json.JSONDecodeError:
                    parsed = self._parse_complete_items(cleaned)
            else:
                parsed = self._parse_complete_items(cleaned)
        if isinstance(parsed, dict):
            parsed = parsed.get("objects", [])
        return [item for item in parsed if isinstance(item, dict)] if isinstance(parsed, list) else []

    def _parse_complete_items(self, text: str) -> list[dict]:
        """Salvage complete top-level objects when a capped model response is truncated."""
        decoder = json.JSONDecoder()
        items: list[dict] = []
        cursor = 0
        while cursor < len(text):
            start = text.find("{", cursor)
            if start < 0:
                break
            try:
                item, consumed = decoder.raw_decode(text[start:])
            except json.JSONDecodeError:
                cursor = start + 1
                continue
            cursor = start + consumed
            if isinstance(item, dict) and item.get("bbox") and (item.get("category") or item.get("label")):
                items.append(item)
        return items

    def _parse_bbox(self, raw: str) -> list[int] | None:
        match = re.search(r"<bbox>\s*([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s*</bbox>", raw)
        if not match:
            nums = re.findall(r"\d+", raw)
            if len(nums) < 4:
                return None
            values = [int(value) for value in nums[:4]]
        else:
            values = [int(value) for value in match.groups()]
        return [max(0, min(value, 999)) for value in values]

    def _scale_ark_bbox(self, bbox: list[int], image_width: int, image_height: int) -> list[int]:
        left = int(round(bbox[0] * image_width / 1000))
        top = int(round(bbox[1] * image_height / 1000))
        right = int(round(bbox[2] * image_width / 1000))
        bottom = int(round(bbox[3] * image_height / 1000))
        left = max(0, min(left, image_width - 1))
        top = max(0, min(top, image_height - 1))
        right = max(left + 1, min(right, image_width))
        bottom = max(top + 1, min(bottom, image_height))
        return [left, top, right, bottom]

    def _dict_value(self, value: object) -> dict:
        return value if isinstance(value, dict) else {}

    def _confidence(self, value: object) -> float:
        try:
            return max(0.0, min(float(value if value is not None else 1.0), 1.0))
        except (TypeError, ValueError):
            return 1.0
