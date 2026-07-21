from abc import ABC, abstractmethod

from app.schemas import DetectRequest, DetectResponse, DetectedObject


class DetectionProvider(ABC):
    @abstractmethod
    async def detect(self, request: DetectRequest) -> DetectResponse:
        raise NotImplementedError

    @abstractmethod
    async def get_object(self, frame_id: str, object_id: str) -> DetectedObject | None:
        raise NotImplementedError
