import asyncio

import httpx

from app.schemas import DetectedObject, ObjectAnalysis, SelectObjectResponse, SelectedAsset
from app.services.model3d.base import Model3DProvider
from app.services.model3d.mock_provider import MockModel3DProvider
from app.storage.local_store import frame_output_dir, path_to_output_url


class Pixal3DModel3DProvider(Model3DProvider):
    def __init__(self, endpoint: str, api_key: str | None = None) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key

    async def generate_asset(
        self,
        frame_id: str,
        detected_object: DetectedObject,
        image_url: str | None = None,
    ) -> SelectObjectResponse:
        if not image_url:
            return await MockModel3DProvider().generate_asset(frame_id, detected_object)

        payload = {
            "image": image_url,
            "object_id": detected_object.id,
            "label": detected_object.label,
            "target_format": "glb",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{self.endpoint}/image-to-3d", headers=self._headers(), json=payload)
            response.raise_for_status()
            data = response.json()

        task_id = data.get("taskId") or data.get("task_id") or data.get("id")
        if task_id and not (data.get("glbUrl") or data.get("glb_url")):
            data = await self._poll_task(task_id)

        glb_url = data.get("glbUrl") or data.get("glb_url") or (data.get("model_urls") or {}).get("glb")
        if not glb_url:
            return await MockModel3DProvider().generate_asset(frame_id, detected_object, image_url=image_url)

        return SelectObjectResponse(
            taskId=task_id or f"pixal3d_{frame_id}_{detected_object.id}",
            status=data.get("status", "succeeded"),
            object=SelectedAsset(
                id=detected_object.id,
                label=detected_object.label,
                name=detected_object.name,
                bbox=detected_object.bbox,
                cropUrl=image_url,
                maskUrl=path_to_output_url(frame_output_dir(frame_id) / f"{detected_object.id}_mask.png"),
                estimatedDimensions=detected_object.estimatedDimensions,
                glbUrl=glb_url,
            ),
            analysis=ObjectAnalysis(
                summary=f"{detected_object.name}已通过 Pixal3D 适配器进入 3D 生成流程。",
                placementAdvice="生成后先按 estimatedDimensions 设置宽、深、高，再放入 scene.json；用户可继续缩放。",
            ),
        )

    async def _poll_task(self, task_id: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            for _ in range(60):
                response = await client.get(f"{self.endpoint}/tasks/{task_id}", headers=self._headers())
                response.raise_for_status()
                data = response.json()
                if data.get("status") in {"SUCCEEDED", "succeeded", "FAILED", "failed"}:
                    return data
                await asyncio.sleep(2)
        return {"status": "timeout"}

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
