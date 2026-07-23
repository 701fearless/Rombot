from io import BytesIO

from PIL import Image, ImageDraw

from app.schemas import DetectRequest, DetectResponse, DetectedObject
from app.services.detection.ark_grounding_provider import ArkGroundingProvider
from app.services.detection.base import DetectionProvider
from app.storage.local_store import (
    OUTPUTS_ROOT,
    data_url_to_bytes,
    load_detected_object,
    path_to_output_url,
    save_data_url,
)


class ArkFeedDetectionProvider(DetectionProvider):
    """Adapts Ark grounding to the paused-feed detection provider contract."""

    def __init__(self, grounding_provider: ArkGroundingProvider) -> None:
        self.grounding_provider = grounding_provider

    async def detect(self, request: DetectRequest) -> DetectResponse:
        if not request.frameImage:
            raise ValueError("frameImage is required for ark_grounding detection")

        frame_id = self._frame_id(request.videoId, request.time)
        frame_path = OUTPUTS_ROOT / frame_id / "frame.jpg"
        save_data_url(request.frameImage, frame_path)

        image = Image.open(BytesIO(data_url_to_bytes(request.frameImage))).convert("RGB")
        objects = await self.grounding_provider.detect(request.frameImage)
        processed = [
            item.model_copy(
                update={
                    "cropUrl": self._save_crop(frame_id, item.id, image, item.bbox),
                    "maskUrl": self._save_box_mask(frame_id, item.id, image.size, item.bbox),
                }
            )
            for item in objects
        ]
        return DetectResponse(
            frameId=frame_id,
            objects=processed,
            frameImageUrl=path_to_output_url(frame_path),
        )

    async def get_object(self, frame_id: str, object_id: str) -> DetectedObject | None:
        return load_detected_object(frame_id, object_id)

    def _save_crop(self, frame_id: str, object_id: str, image: Image.Image, bbox: list[int]) -> str:
        crop_path = OUTPUTS_ROOT / frame_id / f"{object_id}_crop.jpg"
        crop_path.parent.mkdir(parents=True, exist_ok=True)
        image.crop(tuple(bbox)).save(crop_path, quality=92)
        return path_to_output_url(crop_path)

    def _save_box_mask(
        self,
        frame_id: str,
        object_id: str,
        image_size: tuple[int, int],
        bbox: list[int],
    ) -> str:
        mask_path = OUTPUTS_ROOT / frame_id / f"{object_id}_mask.png"
        mask_path.parent.mkdir(parents=True, exist_ok=True)
        mask = Image.new("L", image_size, 0)
        ImageDraw.Draw(mask).rectangle(tuple(bbox), fill=255)
        mask.save(mask_path)
        return path_to_output_url(mask_path)

    def _frame_id(self, video_id: str, timestamp: float) -> str:
        normalized_time = f"{timestamp:.2f}".replace(".", "_")
        return f"frame_{video_id}_{normalized_time}"
