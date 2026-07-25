import asyncio

import httpx

from app.schemas import DetectedObject, ObjectAnalysis, SelectObjectResponse, SelectedAsset
from app.services.image_generation.ark_seedream_provider import ArkSeedreamProvider
from app.services.model3d.base import Model3DProvider
from app.services.model3d.mock_provider import MockModel3DProvider
from app.storage.local_store import frame_output_dir, path_to_output_url


class Hunyuan3DProvider(Model3DProvider):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        poll_interval_sec: float,
        poll_attempts: int,
        reference_provider: ArkSeedreamProvider | None = None,
        generate_type: str = "LowPoly",
        face_count: int = 30000,
        enable_pbr: bool = False,
        enable_geometry: bool = False,
        result_format: str = "GLB",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.poll_interval_sec = poll_interval_sec
        self.poll_attempts = poll_attempts
        self.reference_provider = reference_provider
        self.generate_type = generate_type
        self.face_count = face_count
        self.enable_pbr = enable_pbr
        self.enable_geometry = enable_geometry
        self.result_format = result_format

    async def generate_asset(
        self,
        frame_id: str,
        detected_object: DetectedObject,
        image_url: str | None = None,
    ) -> SelectObjectResponse:
        if not image_url:
            return await MockModel3DProvider().generate_asset(frame_id, detected_object)
        try:
            generation_image = image_url
            if self.reference_provider:
                generation_image = await self.reference_provider.generate_reference_image(
                    image_data_url=image_url,
                    label=detected_object.label,
                    name=detected_object.name,
                    visual_features=detected_object.visualFeatures,
                    generation_hints=detected_object.generationHints,
                )
            task_id = await self._submit(generation_image)
            result = await self._poll(task_id)
            glb_url = self._extract_glb_url(result)
            if not glb_url:
                return await MockModel3DProvider().generate_asset(frame_id, detected_object, image_url=image_url)
            return SelectObjectResponse(
                taskId=task_id,
                status=str(result.get("status") or result.get("task_status") or "succeeded"),
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
                    summary=f"{detected_object.name}已通过混元 3D 生成模型资产。",
                    placementAdvice="生成后先按 estimatedDimensions 设置宽、深、高，再放入 scene.json；用户可继续缩放。",
                ),
            )
        except Exception:
            return await MockModel3DProvider().generate_asset(frame_id, detected_object, image_url=image_url)

    async def _submit(self, image_data_url: str) -> str:
        payload = {
            "model": self.model,
            "image_base64": self._strip_data_uri(image_data_url),
            "enable_pbr": self.enable_pbr,
        }
        if self.model == "hy-3d-express":
            payload.update(
                {
                    "result_format": self.result_format,
                    "enable_geometry": self.enable_geometry,
                }
            )
        elif self.model in {"hy-3d-3.0", "hy-3d-3.1"}:
            payload.update(
                {
                    "generate_type": self.generate_type,
                    "face_count": self.face_count,
                }
            )
            if self.generate_type == "LowPoly":
                payload["polygon_type"] = "triangle"
        else:
            payload["result_format"] = self.result_format
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.base_url}/v1/api/3d/submit",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        response_body = data.get("Response") or data.get("response") or {}
        task_id = (
            data.get("id")
            or data.get("task_id")
            or data.get("taskId")
            or (data.get("data") or {}).get("id")
            or response_body.get("JobId")
            or response_body.get("job_id")
        )
        if not task_id:
            raise ValueError("Hunyuan submit response did not include task id")
        return str(task_id)

    async def _poll(self, task_id: str) -> dict:
        payload = {"model": self.model, "id": task_id}
        async with httpx.AsyncClient(timeout=60) as client:
            for _ in range(self.poll_attempts):
                response = await client.post(
                    f"{self.base_url}/v1/api/3d/query",
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                response_body = data.get("Response") or data.get("response") or {}
                status = str(
                    data.get("status")
                    or data.get("task_status")
                    or data.get("state")
                    or response_body.get("Status")
                    or response_body.get("status")
                    or ""
                ).lower()
                if status in {"succeeded", "success", "completed", "complete", "done"} or self._extract_glb_url(data):
                    return data
                if status in {"failed", "fail", "error", "cancelled", "canceled"}:
                    return data
                await asyncio.sleep(self.poll_interval_sec)
        return {"status": "timeout", "id": task_id}

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _strip_data_uri(self, value: str) -> str:
        return value.split(",", 1)[1] if value.startswith("data:") and "," in value else value

    def _extract_glb_url(self, data: dict) -> str | None:
        response_body = data.get("Response") or data.get("response") or {}
        rapid_files = response_body.get("ResultFile3Ds") or response_body.get("result_file_3ds") or []
        if isinstance(rapid_files, list):
            for item in rapid_files:
                if not isinstance(item, dict):
                    continue
                item_type = str(item.get("Type") or item.get("type") or "").lower()
                url = item.get("Url") or item.get("url")
                if item_type == "glb" and url:
                    return str(url)

        candidates = data.get("data") or data.get("result") or data.get("results") or []
        if isinstance(candidates, dict):
            direct = candidates.get("glb") or candidates.get("glb_url") or candidates.get("url")
            if direct:
                return str(direct)
            candidates = candidates.get("files") or candidates.get("assets") or []
        if isinstance(candidates, list):
            for item in candidates:
                if not isinstance(item, dict):
                    continue
                item_type = str(item.get("type") or item.get("format") or "").lower()
                url = item.get("url") or item.get("file_url") or item.get("download_url")
                if url and (item_type == "glb" or str(url).lower().endswith(".glb")):
                    return str(url)
        return data.get("glbUrl") or data.get("glb_url")
