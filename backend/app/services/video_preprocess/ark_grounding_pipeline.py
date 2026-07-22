from pathlib import Path

from PIL import Image, ImageDraw

from app.schemas import DetectedObject
from app.services.detection.ark_grounding_provider import ArkGroundingProvider
from app.storage.local_store import OUTPUTS_ROOT, path_to_output_url


class ArkGroundingPipeline:
    def __init__(self, grounding_provider: ArkGroundingProvider) -> None:
        self.grounding_provider = grounding_provider

    async def process_frame(self, frame_id: str, frame_path: Path, image_data_url: str) -> list[DetectedObject]:
        image = Image.open(frame_path).convert("RGB")
        objects = await self.grounding_provider.detect(image_data_url)
        processed: list[DetectedObject] = []
        for index, item in enumerate(objects, start=1):
            object_id = f"obj_{item.label}_{index:03d}"
            crop_url = self._save_crop(frame_id, object_id, image, item.bbox)
            mask_url = self._save_mask(frame_id, object_id, image.size, item.bbox)
            processed.append(item.model_copy(update={"id": object_id, "cropUrl": crop_url, "maskUrl": mask_url}))
        return processed

    def _video_id_from_frame_id(self, frame_id: str) -> str:
        return frame_id.rsplit("_", 1)[0]

    def _save_crop(self, frame_id: str, object_id: str, image: Image.Image, bbox: list[int]) -> str:
        crop_path = OUTPUTS_ROOT / "videos" / self._video_id_from_frame_id(frame_id) / "objects" / f"{frame_id}_{object_id}_crop.jpg"
        crop_path.parent.mkdir(parents=True, exist_ok=True)
        image.crop(tuple(bbox)).save(crop_path, quality=92)
        return path_to_output_url(crop_path)

    def _save_mask(self, frame_id: str, object_id: str, image_size: tuple[int, int], bbox: list[int]) -> str:
        mask_path = OUTPUTS_ROOT / "videos" / self._video_id_from_frame_id(frame_id) / "objects" / f"{frame_id}_{object_id}_mask.png"
        mask_path.parent.mkdir(parents=True, exist_ok=True)
        mask = Image.new("L", image_size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rectangle(tuple(bbox), fill=255)
        mask.save(mask_path)
        return path_to_output_url(mask_path)
