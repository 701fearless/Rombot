import asyncio
import base64
import json
import re
from collections.abc import Callable
from io import BytesIO

import httpx
from PIL import Image

from app.schemas import DeduplicatedObject, DetectedObject, EstimatedDimensions, VideoAnalysisFrame
from app.storage.local_store import output_url_to_path


DIMENSION_ESTIMATION_PROMPT = """
Estimate plausible real-world metric dimensions for this single household
furniture/home object.

This image has no reliable physical scale. Do NOT claim the values were measured
from pixels. Use conservative category priors, ordinary manufacturing sizes,
ergonomics, visible proportions and visible component count. The estimate should
represent a normal real instance of this exact object, not an unusually small,
oversized or artistic version.

Dimensions must cover the reconstructed complete independent asset's maximum outer
bounding box, not only a visible panel, mattress surface, seat surface or cropped
component. In particular:
- bed height includes the highest headboard/backboard, not only mattress/deck height;
- chair/armchair/sofa height includes the full backrest;
- table/desk height is floor to tabletop;
- cabinet/bookshelf/wardrobe height covers the full storage body.

Canonical axes:
- widthM: left-to-right width when viewed from the canonical front.
- depthM: front-to-back depth.
- heightM: bottom-to-top height.
- Special case for a rug/carpet/mat lying on the floor: widthM and depthM are
  its two horizontal floor dimensions, and heightM is physical pile/thickness.

Object metadata:
- category: {label}
- display name: {name}
- visualFeatures: {visual_features}
- generationHints: {generation_hints}

Return one JSON object only:
{{
  "widthM": 1.0,
  "depthM": 1.0,
  "heightM": 1.0,
  "range": {{
    "widthM": [0.8, 1.2],
    "depthM": [0.8, 1.2],
    "heightM": [0.8, 1.2]
  }},
  "confidence": 0.5,
  "basis": [
    "short category-prior reason",
    "short visible-proportion reason"
  ],
  "assumptions": [
    "important scale or orientation assumption"
  ]
}}

Rules:
- All dimensions are meters and must be positive numbers.
- Use at most two decimal places.
- The estimate must lie inside its corresponding range.
- The range must describe plausible maximum outer dimensions of the complete asset.
- Use a wider range and lower confidence when scale, orientation or category is uncertain.
- For curtains, mirrors and paintings, depth means physical thickness.
- For rugs/carpets/mats, height means physical pile/thickness; never put a
  horizontal rug length into heightM.
- For lamps, plants and vases, dimensions cover the complete standalone object.
- Do not include explanations outside the JSON.
"""


class ArkFurnitureDimensionEstimator:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def estimate(
        self,
        candidate: DeduplicatedObject,
        detected_object: DetectedObject,
    ) -> EstimatedDimensions:
        crop_path = output_url_to_path(candidate.cropUrl)
        if crop_path is None or not crop_path.exists():
            raise FileNotFoundError(f"Dimension estimation crop not found: {candidate.cropUrl}")

        with Image.open(crop_path) as source:
            image_data_url = self._prepare_vision_image(source.convert("RGB"))
        prompt = DIMENSION_ESTIMATION_PROMPT.format(
            label=candidate.label,
            name=candidate.name,
            visual_features=json.dumps(detected_object.visualFeatures, ensure_ascii=False),
            generation_hints=json.dumps(detected_object.generationHints, ensure_ascii=False),
        )
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "temperature": 0.1,
            "max_tokens": 800,
            "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
        }
        data = await self._post_with_rate_limit_retry(payload)
        parsed = self._parse_json_object(self._extract_text(data))
        return self._normalize_estimate(parsed)

    async def enrich_candidates(
        self,
        frames: list[VideoAnalysisFrame],
        candidates: list[DeduplicatedObject],
        *,
        force: bool = False,
        on_update: Callable[[], None] | None = None,
    ) -> int:
        estimated_count = 0
        objects_by_ref = {
            (frame.frameId, detected_object.id): detected_object
            for frame in frames
            for detected_object in frame.objects
        }
        for candidate in candidates:
            representative = objects_by_ref.get(
                (candidate.representativeFrameId, candidate.representativeObjectId)
            )
            if representative is None:
                raise ValueError(
                    f"Representative object missing for dimension estimation: {candidate.id}"
                )
            estimate = candidate.estimatedDimensions
            if estimate is None or force:
                estimate = await self.estimate(candidate, representative)
                candidate.estimatedDimensions = estimate
                estimated_count += 1
            for frame in frames:
                for detected_object in frame.objects:
                    if detected_object.deduplicatedObjectId == candidate.id:
                        detected_object.estimatedDimensions = estimate
            if on_update is not None:
                on_update()
        return estimated_count

    def _prepare_vision_image(self, image: Image.Image, max_side: int = 1024) -> str:
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

    async def _post_with_rate_limit_retry(self, payload: dict) -> dict:
        timeout = httpx.Timeout(connect=20, read=120, write=30, pool=20)
        last_error: httpx.HTTPStatusError | None = None
        for attempt in range(6):
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            try:
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 429 or attempt >= 5:
                    raise
                last_error = exc
                retry_after = exc.response.headers.get("retry-after")
                try:
                    wait_seconds = float(retry_after) if retry_after else 10 + attempt * 10
                except ValueError:
                    wait_seconds = 10 + attempt * 10
                await asyncio.sleep(wait_seconds)
        raise last_error or RuntimeError("Ark dimension estimation request failed")

    def _extract_text(self, data: dict) -> str:
        choices = data.get("choices") or []
        if not choices:
            raise ValueError(f"Ark dimension estimation returned no choices: {data}")
        content = (choices[0].get("message") or {}).get("content", "")
        if isinstance(content, list):
            return "".join(
                str(item.get("text", ""))
                for item in content
                if isinstance(item, dict)
            )
        return str(content)

    def _parse_json_object(self, text: str) -> dict:
        cleaned = text.strip()
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, flags=re.S)
            if not match:
                raise ValueError(f"Ark dimension estimation returned invalid JSON: {text[:800]}")
            parsed = json.loads(match.group(0))
        if not isinstance(parsed, dict):
            raise ValueError("Ark dimension estimation response must be a JSON object")
        return parsed

    def _normalize_estimate(self, parsed: dict) -> EstimatedDimensions:
        width = self._positive_number(parsed.get("widthM"), "widthM")
        depth = self._positive_number(parsed.get("depthM"), "depthM")
        height = self._positive_number(parsed.get("heightM"), "heightM")
        raw_range = parsed.get("range") if isinstance(parsed.get("range"), dict) else {}
        normalized_range = {
            "widthM": self._normalize_range(raw_range.get("widthM"), width),
            "depthM": self._normalize_range(raw_range.get("depthM"), depth),
            "heightM": self._normalize_range(raw_range.get("heightM"), height),
        }
        return self.initial_dimensions_from_ranges(normalized_range)

    def initial_dimensions_from_ranges(self, ranges: dict) -> EstimatedDimensions:
        return EstimatedDimensions(
            widthM=self._initial_value(ranges.get("widthM"), "widthM"),
            depthM=self._initial_value(ranges.get("depthM"), "depthM"),
            heightM=self._initial_value(ranges.get("heightM"), "heightM"),
            unit="m",
            source="ark_category_prior",
            isMeasured=False,
            selectionRule="range_min_plus_0.10m_capped_at_max",
        )

    def _positive_number(self, value: object, field_name: str) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Ark dimension estimation omitted numeric {field_name}") from exc
        if not 0 < number <= 20:
            raise ValueError(f"Ark dimension estimation returned invalid {field_name}: {number}")
        return number

    def _normalize_range(self, value: object, estimate: float) -> list[float]:
        if isinstance(value, list) and len(value) >= 2:
            try:
                lower, upper = sorted((float(value[0]), float(value[1])))
            except (TypeError, ValueError):
                lower, upper = estimate * 0.8, estimate * 1.2
        else:
            lower, upper = estimate * 0.8, estimate * 1.2
        lower = max(0.01, min(lower, estimate))
        upper = min(20.0, max(upper, estimate))
        return [round(lower, 2), round(upper, 2)]

    def _initial_value(self, value: object, field_name: str) -> float:
        if not isinstance(value, list) or len(value) < 2:
            raise ValueError(f"Missing normalized range for {field_name}")
        lower, upper = sorted((float(value[0]), float(value[1])))
        return round(min(lower + 0.10, upper), 2)
