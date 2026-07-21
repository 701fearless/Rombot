from pathlib import Path

from PIL import Image, ImageDraw

from app.schemas import DetectedObject
from app.services.detection.grounding_dino_provider import GroundingDinoProvider
from app.services.segmentation.sam_box_provider import SamBoxProvider
from app.services.vision_semantics.doubao_provider import DoubaoVisionProvider
from app.services.vision_semantics.label_policy import (
    bbox_area_ratio,
    dedupe_objects,
    is_allowed_label,
    label_name,
    normalize_label,
    tag_position,
)
from app.storage.local_store import OUTPUTS_ROOT, path_to_output_url, save_data_url


class DoubaoGroundingSamPipeline:
    def __init__(
        self,
        doubao_provider: DoubaoVisionProvider,
        grounding_dino_provider: GroundingDinoProvider,
        sam_provider: SamBoxProvider | None = None,
    ) -> None:
        self.doubao_provider = doubao_provider
        self.grounding_dino_provider = grounding_dino_provider
        self.sam_provider = sam_provider

    async def process_frame(self, frame_id: str, frame_path: Path, image_data_url: str) -> list[DetectedObject]:
        semantic_items = await self.doubao_provider.classify_frame(image_data_url)
        labels = [item["label"] for item in semantic_items]
        names_by_label = {item["label"]: item.get("name") for item in semantic_items}
        if not labels:
            return []

        detections = await self.grounding_dino_provider.detect_with_labels(image_data_url, labels)
        detections = [item for item in detections if is_allowed_label(item["label"])]
        if not detections:
            return []

        image = Image.open(frame_path).convert("RGB")
        image_width, image_height = image.size
        boxes = []
        for item in detections:
            bbox = self._normalize_bbox(item["bbox"], image_width, image_height)
            if bbox_area_ratio(bbox, image_width, image_height) < 0.01:
                continue
            boxes.append({"label": normalize_label(item["label"]), "confidence": item["confidence"], "bbox": bbox})

        masks_by_key = await self._segment(image_data_url, boxes)
        objects: list[DetectedObject] = []
        for index, item in enumerate(boxes, start=1):
            label = normalize_label(item["label"])
            object_id = f"obj_{label}_{index:03d}"
            crop_url = self._save_crop(frame_id, object_id, image, item["bbox"])
            mask_url = self._save_mask(frame_id, object_id, image.size, item["bbox"], masks_by_key.get(self._mask_key(item)))
            objects.append(
                DetectedObject(
                    id=object_id,
                    label=label,
                    name=label_name(label, names_by_label.get(label)),
                    confidence=item["confidence"],
                    bbox=item["bbox"],
                    tagPosition=tag_position(item["bbox"], image_width, image_height),
                    cropUrl=crop_url,
                    maskUrl=mask_url,
                )
            )

        return dedupe_objects(objects, max_items=6)

    async def _segment(self, image_data_url: str, boxes: list[dict]) -> dict[str, str]:
        if not self.sam_provider or not boxes:
            return {}
        try:
            segmented = await self.sam_provider.segment_boxes(image_data_url, boxes)
        except Exception:
            return {}
        masks: dict[str, str] = {}
        for item in segmented:
            label = normalize_label(str(item.get("label", "")))
            bbox = item.get("bbox")
            mask = item.get("mask") or item.get("maskImage") or item.get("mask_image")
            if label and bbox and mask:
                masks[self._mask_key({"label": label, "bbox": self._bbox_as_int(bbox)})] = mask
        return masks

    def _normalize_bbox(self, bbox: list[float], image_width: int, image_height: int) -> list[int]:
        if all(0 <= value <= 1 for value in bbox):
            left, top, right, bottom = [
                bbox[0] * image_width,
                bbox[1] * image_height,
                bbox[2] * image_width,
                bbox[3] * image_height,
            ]
        else:
            left, top, right, bottom = bbox
        return [
            max(0, min(int(round(left)), image_width - 1)),
            max(0, min(int(round(top)), image_height - 1)),
            max(1, min(int(round(right)), image_width)),
            max(1, min(int(round(bottom)), image_height)),
        ]

    def _bbox_as_int(self, bbox: list) -> list[int]:
        return [int(round(float(value))) for value in bbox]

    def _save_crop(self, frame_id: str, object_id: str, image: Image.Image, bbox: list[int]) -> str:
        crop_path = OUTPUTS_ROOT / "videos" / frame_id.rsplit("_", 1)[0] / "objects" / f"{frame_id}_{object_id}_crop.jpg"
        crop_path.parent.mkdir(parents=True, exist_ok=True)
        image.crop(tuple(bbox)).save(crop_path, quality=92)
        return path_to_output_url(crop_path)

    def _save_mask(
        self,
        frame_id: str,
        object_id: str,
        image_size: tuple[int, int],
        bbox: list[int],
        mask_data_url: str | None,
    ) -> str:
        mask_path = OUTPUTS_ROOT / "videos" / frame_id.rsplit("_", 1)[0] / "objects" / f"{frame_id}_{object_id}_mask.png"
        mask_path.parent.mkdir(parents=True, exist_ok=True)
        if mask_data_url:
            save_data_url(mask_data_url, mask_path)
            return path_to_output_url(mask_path)
        mask = Image.new("L", image_size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rectangle(tuple(bbox), fill=255)
        mask.save(mask_path)
        return path_to_output_url(mask_path)

    def _mask_key(self, item: dict) -> str:
        bbox = item["bbox"]
        return f"{normalize_label(item['label'])}:{','.join(str(int(value)) for value in bbox)}"
