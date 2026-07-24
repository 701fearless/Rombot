import asyncio

import httpx

from app.schemas import DetectedObject, ObjectAnalysis, SelectObjectResponse, SelectedAsset
from app.services.model3d.base import Model3DProvider
from app.services.model3d.mock_provider import MockModel3DProvider
from app.storage.local_store import frame_output_dir, path_to_output_url


class MeshyModel3DProvider(Model3DProvider):
    def __init__(self, api_key: str, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def generate_asset(
        self,
        frame_id: str,
        detected_object: DetectedObject,
        image_url: str | None = None,
    ) -> SelectObjectResponse:
        if not image_url:
            return await MockModel3DProvider().generate_asset(frame_id, detected_object)

        task_id = await self._create_task(image_url=image_url)
        result = await self._poll_task(task_id)
        model_urls = result.get("model_urls") or {}
        glb_url = model_urls.get("glb")
        status = result.get("status", "unknown")
        if not glb_url:
            glb_url = "/sample_data/models/sofa.glb"
            status = "fallback_mock"

        return SelectObjectResponse(
            taskId=task_id,
            status=status,
            object=SelectedAsset(
                id=detected_object.id,
                label=detected_object.label,
                name=detected_object.name,
                bbox=detected_object.bbox,
                cropUrl=image_url,
                maskUrl=path_to_output_url(frame_output_dir(frame_id) / f"{detected_object.id}_mask.png"),
                glbUrl=glb_url,
            ),
            analysis=ObjectAnalysis(
                summary=f"{detected_object.name}已进入 3D 资产生成流程。",
                placementAdvice="生成后建议根据真实尺寸缩放，再放入 scene.json 的目标位置。",
            ),
        )

    async def _create_task(self, image_url: str) -> str:
        payload = {
            "image_url": image_url,
            "target_formats": ["glb"],
            "should_texture": True,
            "enable_pbr": True,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/openapi/v1/image-to-3d",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        return data.get("result") or data.get("id") or data.get("task_id")

    async def _poll_task(self, task_id: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            for _ in range(30):
                response = await client.get(
                    f"{self.base_url}/openapi/v1/image-to-3d/{task_id}",
                    headers=self._headers(),
                )
                response.raise_for_status()
                data = response.json()
                status = data.get("status")
                if status in {"SUCCEEDED", "succeeded", "FAILED", "failed", "EXPIRED", "expired"}:
                    return data
                await asyncio.sleep(2)
        return {"status": "timeout"}

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
