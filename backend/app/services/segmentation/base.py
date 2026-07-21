from abc import ABC, abstractmethod
from pathlib import Path

from app.schemas import DetectedObject, SegmentationResult


class SegmentationProvider(ABC):
    @abstractmethod
    async def segment(
        self,
        frame_id: str,
        detected_object: DetectedObject,
        frame_image_path: Path | None = None,
        frame_image_data_url: str | None = None,
    ) -> SegmentationResult:
        raise NotImplementedError
