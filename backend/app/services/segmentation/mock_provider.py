import base64
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

from app.schemas import DetectedObject, SegmentationResult
from app.services.segmentation.base import SegmentationProvider
from app.storage.local_store import OUTPUTS_ROOT, path_to_output_url


class MockSegmentationProvider(SegmentationProvider):
    async def segment(
        self,
        frame_id: str,
        detected_object: DetectedObject,
        frame_image_path: Path | None = None,
        frame_image_data_url: str | None = None,
    ) -> SegmentationResult:
        output_dir = OUTPUTS_ROOT / frame_id
        output_dir.mkdir(parents=True, exist_ok=True)
        crop_path = output_dir / f"{detected_object.id}_crop.jpg"
        mask_path = output_dir / f"{detected_object.id}_mask.png"

        image = self._load_image(frame_image_path, frame_image_data_url)
        if image is None:
            image = Image.new("RGB", (512, 512), (225, 218, 206))
            bbox = [96, 144, 416, 368]
        else:
            bbox = self._clamp_bbox(detected_object.bbox, image.size)

        crop = image.crop(tuple(bbox))
        crop.save(crop_path, quality=92)

        mask = Image.new("L", image.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rectangle(tuple(bbox), fill=255)
        mask.save(mask_path)

        return SegmentationResult(
            frameId=frame_id,
            objectId=detected_object.id,
            cropUrl=path_to_output_url(crop_path),
            maskUrl=path_to_output_url(mask_path),
            cropImage=self._to_data_url(crop),
        )

    def _load_image(self, frame_image_path: Path | None, frame_image_data_url: str | None) -> Image.Image | None:
        if frame_image_path and frame_image_path.exists():
            return Image.open(frame_image_path).convert("RGB")
        if frame_image_data_url:
            raw = base64.b64decode(frame_image_data_url.split(",", 1)[-1])
            return Image.open(BytesIO(raw)).convert("RGB")
        return None

    def _clamp_bbox(self, bbox: list[int], image_size: tuple[int, int]) -> list[int]:
        width, height = image_size
        left, top, right, bottom = bbox
        left = max(0, min(left, width - 1))
        top = max(0, min(top, height - 1))
        right = max(left + 1, min(right, width))
        bottom = max(top + 1, min(bottom, height))
        return [left, top, right, bottom]

    def _to_data_url(self, image: Image.Image) -> str:
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=92)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"
