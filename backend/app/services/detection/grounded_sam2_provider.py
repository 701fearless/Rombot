from io import BytesIO

import httpx
from PIL import Image, ImageDraw

from app.schemas import DetectRequest, DetectResponse, DetectedObject
from app.services.detection.base import DetectionProvider
from app.services.detection.furniture_labels import label_to_zh, normalize_label
from app.storage.local_store import OUTPUTS_ROOT, data_url_to_bytes, load_detected_object, path_to_output_url, save_data_url


class GroundedSAM2DetectionProvider(DetectionProvider):
    def __init__(
        self,
        endpoint: str,
        prompt: str,
        api_key: str | None = None,
        max_objects: int = 8,
        min_confidence: float = 0.35,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.prompt = prompt
        self.api_key = api_key
        self.max_objects = max_objects
        self.min_confidence = min_confidence

    async def detect(self, request: DetectRequest) -> DetectResponse:
        if not request.frameImage:
            raise ValueError("frameImage is required for grounded_sam2 detection")

        frame_id = self._frame_id(request.videoId, request.time)
        frame_path = OUTPUTS_ROOT / frame_id / "frame.jpg"
        save_data_url(request.frameImage, frame_path)

        payload = {
            "image": request.frameImage,
            "prompt": self.prompt,
            "box_threshold": self.min_confidence,
            "text_threshold": self.min_confidence,
            "max_objects": self.max_objects,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(f"{self.endpoint}/detect-and-segment", headers=self._headers(), json=payload)
            response.raise_for_status()
            data = response.json()

        objects = self._parse_objects(frame_id=frame_id, frame_data_url=request.frameImage, raw_items=data.get("objects", []))
        return DetectResponse(frameId=frame_id, objects=objects, frameImageUrl=path_to_output_url(frame_path))

    async def get_object(self, frame_id: str, object_id: str) -> DetectedObject | None:
        return load_detected_object(frame_id, object_id)

    def _parse_objects(self, frame_id: str, frame_data_url: str, raw_items: list[dict]) -> list[DetectedObject]:
        image = Image.open(BytesIO(data_url_to_bytes(frame_data_url))).convert("RGB")
        image_width, image_height = image.size
        parsed: list[DetectedObject] = []

        for index, item in enumerate(raw_items):
            confidence = float(item.get("confidence") or item.get("score") or 0)
            if confidence < self.min_confidence:
                continue

            label = normalize_label(str(item.get("label") or item.get("class") or item.get("category") or "object"))
            bbox = self._normalize_bbox(item.get("bbox") or item.get("box"), image_width, image_height)
            if bbox is None:
                continue

            object_id = str(item.get("id") or f"obj_{label.replace(' ', '_')}_{index + 1:03d}")
            crop_url = self._save_crop(frame_id, object_id, image, bbox)
            mask_url = self._save_mask(frame_id, object_id, item.get("mask") or item.get("maskImage") or item.get("mask_image"))
            if not mask_url:
                mask_url = self._save_box_mask(frame_id, object_id, image.size, bbox)

            parsed.append(
                DetectedObject(
                    id=object_id,
                    label=label,
                    name=label_to_zh(label),
                    confidence=confidence,
                    bbox=bbox,
                    tagPosition=[round(((bbox[0] + bbox[2]) / 2) / image_width, 4), round(((bbox[1] + bbox[3]) / 2) / image_height, 4)],
                    cropUrl=crop_url,
                    maskUrl=mask_url,
                )
            )

        parsed.sort(key=lambda item: item.confidence, reverse=True)
        return parsed[: self.max_objects]

    def _normalize_bbox(self, bbox: list | None, image_width: int, image_height: int) -> list[int] | None:
        if not bbox or len(bbox) != 4:
            return None
        values = [float(value) for value in bbox]
        if all(0 <= value <= 1 for value in values):
            left, top, right, bottom = [
                values[0] * image_width,
                values[1] * image_height,
                values[2] * image_width,
                values[3] * image_height,
            ]
        else:
            left, top, right, bottom = values
        left = max(0, min(int(round(left)), image_width - 1))
        top = max(0, min(int(round(top)), image_height - 1))
        right = max(left + 1, min(int(round(right)), image_width))
        bottom = max(top + 1, min(int(round(bottom)), image_height))
        return [left, top, right, bottom]

    def _save_crop(self, frame_id: str, object_id: str, image: Image.Image, bbox: list[int]) -> str:
        crop_path = OUTPUTS_ROOT / frame_id / f"{object_id}_crop.jpg"
        crop_path.parent.mkdir(parents=True, exist_ok=True)
        crop = image.crop(tuple(bbox))
        crop.save(crop_path, quality=92)
        return path_to_output_url(crop_path)

    def _save_mask(self, frame_id: str, object_id: str, mask_data: str | None) -> str | None:
        if not mask_data:
            return None
        mask_path = OUTPUTS_ROOT / frame_id / f"{object_id}_mask.png"
        save_data_url(mask_data, mask_path)
        return path_to_output_url(mask_path)

    def _save_box_mask(self, frame_id: str, object_id: str, image_size: tuple[int, int], bbox: list[int]) -> str:
        mask_path = OUTPUTS_ROOT / frame_id / f"{object_id}_mask.png"
        mask_path.parent.mkdir(parents=True, exist_ok=True)
        mask = Image.new("L", image_size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rectangle(tuple(bbox), fill=255)
        mask.save(mask_path)
        return path_to_output_url(mask_path)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _frame_id(self, video_id: str, timestamp: float) -> str:
        normalized_time = f"{timestamp:.2f}".replace(".", "_")
        return f"frame_{video_id}_{normalized_time}"
