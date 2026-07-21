from pathlib import Path

import httpx

from app.schemas import DetectedObject, SegmentationResult
from app.services.segmentation.base import SegmentationProvider
from app.services.segmentation.mock_provider import MockSegmentationProvider


class SAM3SegmentationProvider(SegmentationProvider):
    def __init__(self, endpoint: str, api_key: str | None = None) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key

    async def segment(
        self,
        frame_id: str,
        detected_object: DetectedObject,
        frame_image_path: Path | None = None,
        frame_image_data_url: str | None = None,
    ) -> SegmentationResult:
        if not frame_image_data_url:
            return await MockSegmentationProvider().segment(frame_id, detected_object, frame_image_path, frame_image_data_url)

        payload = {
            "image": frame_image_data_url,
            "prompts": [detected_object.name, detected_object.label],
            "bbox": detected_object.bbox,
            "object_id": detected_object.id,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{self.endpoint}/segment", headers=self._headers(), json=payload)
            response.raise_for_status()
            data = response.json()

        crop_url = data.get("cropUrl") or data.get("crop_url")
        mask_url = data.get("maskUrl") or data.get("mask_url")
        crop_image = data.get("cropImage") or data.get("crop_image")
        if not crop_url or not mask_url:
            return await MockSegmentationProvider().segment(frame_id, detected_object, frame_image_path, frame_image_data_url)

        return SegmentationResult(
            frameId=frame_id,
            objectId=detected_object.id,
            cropUrl=crop_url,
            maskUrl=mask_url,
            cropImage=crop_image,
        )

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
