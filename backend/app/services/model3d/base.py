from abc import ABC, abstractmethod

from app.schemas import DetectedObject, SelectObjectResponse


class Model3DProvider(ABC):
    @abstractmethod
    async def generate_asset(
        self,
        frame_id: str,
        detected_object: DetectedObject,
        image_url: str | None = None,
    ) -> SelectObjectResponse:
        raise NotImplementedError
