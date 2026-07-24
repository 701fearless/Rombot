import asyncio
import mimetypes
from pathlib import Path
from typing import Any

import httpx

from app.schemas import FurnitureGenerationBrief
from app.services.model3d.feature_hunyuan_provider import FeatureHunyuanModel3DProvider


class FeatureTripoModel3DProvider(FeatureHunyuanModel3DProvider):
    """
    Reuses the verified Ark feature brief + Seedream reference image stages, then
    sends the generated reference image to Tripo Turbo image-to-3D.
    """

    def __init__(
        self,
        ark_api_key: str,
        ark_base_url: str,
        ark_vision_model: str,
        ark_image_model: str,
        ark_image_size: str,
        tripo_api_key: str,
        tripo_base_url: str,
        tripo_model_version: str,
        tripo_texture: bool,
        tripo_pbr: bool,
        tripo_texture_quality: str,
        tripo_texture_alignment: str,
        tripo_export_uv: bool,
        tripo_enable_image_autofix: bool,
        tripo_poll_interval_sec: float,
        tripo_poll_attempts: int,
    ) -> None:
        super().__init__(
            ark_api_key=ark_api_key,
            ark_base_url=ark_base_url,
            ark_vision_model=ark_vision_model,
            ark_image_model=ark_image_model,
            ark_image_size=ark_image_size,
            hunyuan_api_key="",
            hunyuan_base_url="",
            hunyuan_model="",
            hunyuan_generate_type="",
            hunyuan_face_count=0,
            hunyuan_enable_pbr=False,
            hunyuan_enable_geometry=False,
            hunyuan_result_format="GLB",
            hunyuan_poll_interval_sec=tripo_poll_interval_sec,
            hunyuan_poll_attempts=tripo_poll_attempts,
        )
        self.provider_name = "feature_tripo"
        self.tripo_api_key = tripo_api_key
        self.tripo_base_url = tripo_base_url.rstrip("/")
        self.tripo_model_version = tripo_model_version
        self.tripo_texture = tripo_texture
        self.tripo_pbr = tripo_pbr
        self.tripo_texture_quality = tripo_texture_quality
        self.tripo_texture_alignment = tripo_texture_alignment
        self.tripo_export_uv = tripo_export_uv
        self.tripo_enable_image_autofix = tripo_enable_image_autofix
        self.tripo_poll_interval_sec = tripo_poll_interval_sec
        self.tripo_poll_attempts = tripo_poll_attempts

    async def _create_3d_task(self, image_inputs: list[str], brief: FurnitureGenerationBrief) -> str:
        _ = brief
        primary_image = image_inputs[-1] if image_inputs else None
        if not primary_image:
            raise ValueError("Tripo image_to_model requires one reference image")

        file_token, file_type = await self._upload_image(primary_image)
        payload = self._build_task_payload(file_token, file_type)
        data = await self._post_task(payload)
        task_id = self._extract_task_id(data)
        if not task_id:
            raise ValueError(f"Tripo did not return a task id: {data}")
        return task_id

    async def _upload_image(self, image_input: str) -> tuple[str, str]:
        content, filename, mime_type = self._image_input_to_upload(image_input)
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                self._upload_url(),
                headers=self._tripo_auth_headers(),
                files={"file": (filename, content, mime_type)},
            )
            response.raise_for_status()
            data = response.json()
        token = self._extract_upload_token(data)
        if not token:
            raise ValueError(f"Tripo upload did not return a file token: {data}")
        return token, self._file_type_from_mime(filename, mime_type)

    async def _post_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                self._submit_url(),
                headers=self._tripo_json_headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def _poll_3d_task(self, task_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=60) as client:
            for _ in range(self.tripo_poll_attempts):
                response = await client.get(
                    self._query_url(task_id),
                    headers=self._tripo_auth_headers(),
                )
                response.raise_for_status()
                data = response.json()
                status = self._normalize_status(data)
                if status in {"SUCCEEDED", "FAILED", "EXPIRED"}:
                    data.setdefault("status", status)
                    return data
                await asyncio.sleep(self.tripo_poll_interval_sec)
        return {"status": "timeout"}

    def _build_task_payload(self, file_token: str, file_type: str) -> dict[str, Any]:
        common = {
            "texture": self.tripo_texture,
            "pbr": self.tripo_pbr,
            "texture_quality": self.tripo_texture_quality,
            "texture_alignment": self.tripo_texture_alignment,
            "export_uv": self.tripo_export_uv,
            "enable_image_autofix": self.tripo_enable_image_autofix,
        }
        if self._is_v3_base():
            return {
                "input": file_token,
                "model": self.tripo_model_version,
                **common,
            }
        return {
            "type": "image_to_model",
            "file": {
                "type": file_type,
                "file_token": file_token,
            },
            "model_version": self.tripo_model_version,
            **common,
        }

    def _upload_url(self) -> str:
        base = self.tripo_base_url.rstrip("/")
        if self._is_v3_base():
            if base.endswith("/files"):
                return base
            return f"{base}/files"
        if base.endswith("/upload"):
            return base
        if base.endswith("/task"):
            return base[: -len("/task")] + "/upload"
        if base.endswith("/v2/openapi"):
            return f"{base}/upload"
        return f"{base}/v2/openapi/upload"

    def _submit_url(self) -> str:
        base = self.tripo_base_url.rstrip("/")
        if self._is_v3_base():
            if base.endswith("/generation/image-to-model"):
                return base
            return f"{base}/generation/image-to-model"
        if base.endswith("/task"):
            return base
        if base.endswith("/upload"):
            return base[: -len("/upload")] + "/task"
        if base.endswith("/v2/openapi"):
            return f"{base}/task"
        return f"{base}/v2/openapi/task"

    def _query_url(self, task_id: str) -> str:
        base = self.tripo_base_url.rstrip("/")
        if self._is_v3_base():
            if "/generation/image-to-model" in base:
                base = base.split("/generation/image-to-model", 1)[0]
            if base.endswith("/files"):
                base = base[: -len("/files")]
            return f"{base}/tasks/{task_id}"
        if base.endswith("/task"):
            return f"{base}/{task_id}"
        if base.endswith("/upload"):
            return base[: -len("/upload")] + f"/task/{task_id}"
        if base.endswith("/v2/openapi"):
            return f"{base}/task/{task_id}"
        return f"{base}/v2/openapi/task/{task_id}"

    def _is_v3_base(self) -> bool:
        base = self.tripo_base_url.rstrip("/").lower()
        return "openapi.tripo3d.com" in base or "/v3" in base

    def _normalize_status(self, data: dict[str, Any]) -> str:
        task = self._task_data(data)
        raw_status = task.get("status") or data.get("status") or data.get("state")
        status = str(raw_status or "").lower()
        if status in {"success", "succeeded", "done", "completed", "finished"}:
            return "SUCCEEDED"
        if status in {"failed", "fail", "error"}:
            return "FAILED"
        if status in {"expired", "timeout", "cancelled", "canceled"}:
            return "EXPIRED"
        return "RUNNING"

    def _extract_task_id(self, data: dict[str, Any]) -> str | None:
        task = self._task_data(data)
        candidates = [
            task.get("task_id"),
            task.get("taskId"),
            task.get("id"),
            data.get("task_id"),
            data.get("taskId"),
            data.get("id"),
        ]
        return next((str(item) for item in candidates if item), None)

    def _extract_glb_url(self, result: dict[str, Any]) -> str | None:
        task = self._task_data(result)
        output = task.get("output") if isinstance(task.get("output"), dict) else {}
        nested_result = task.get("result") if isinstance(task.get("result"), dict) else {}
        nested_model = nested_result.get("model") if isinstance(nested_result.get("model"), dict) else {}
        candidates = [
            output.get("pbr_model") if self.tripo_pbr else None,
            output.get("model"),
            output.get("base_model"),
            output.get("pbr_model"),
            nested_model.get("url"),
            task.get("model"),
            task.get("model_url"),
            task.get("glb_url"),
        ]
        return next((str(item) for item in candidates if item), None)

    def _extract_upload_token(self, data: dict[str, Any]) -> str | None:
        candidates = [
            data.get("file_token"),
            data.get("image_token"),
            data.get("token"),
            data.get("id"),
        ]
        for container_name in ("data", "result", "output"):
            container = data.get(container_name)
            if isinstance(container, dict):
                candidates.extend(
                    [
                        container.get("file_token"),
                        container.get("image_token"),
                        container.get("token"),
                        container.get("id"),
                    ]
                )
            elif isinstance(container, str):
                candidates.append(container)
        return next((str(item) for item in candidates if item), None)

    def _task_data(self, data: dict[str, Any]) -> dict[str, Any]:
        task = data.get("data")
        if isinstance(task, dict):
            return task
        result = data.get("result")
        if isinstance(result, dict):
            return result
        return data

    def _image_input_to_upload(self, image_input: str) -> tuple[bytes, str, str]:
        if image_input.startswith("data:image/"):
            mime_type = image_input.split(";", 1)[0].replace("data:", "")
            extension = self._file_type_from_mime("reference.png", mime_type)
            filename = f"reference.{extension}"
            return self._data_url_to_bytes(image_input), filename, mime_type

        local_path = Path(image_input)
        if local_path.exists():
            mime_type = mimetypes.guess_type(local_path.name)[0] or "image/png"
            return local_path.read_bytes(), local_path.name, mime_type

        raise ValueError("Tripo provider can only upload data URLs or local image paths")

    def _file_type_from_mime(self, filename: str, mime_type: str) -> str:
        suffix = Path(filename).suffix.lower().lstrip(".")
        if suffix in {"jpg", "jpeg", "png", "webp"}:
            return "jpg" if suffix == "jpeg" else suffix
        if mime_type.endswith("jpeg"):
            return "jpg"
        if mime_type.endswith("png"):
            return "png"
        if mime_type.endswith("webp"):
            return "webp"
        return "png"

    def _tripo_auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.tripo_api_key}"}

    def _tripo_json_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.tripo_api_key}", "Content-Type": "application/json"}

    def _data_url_to_bytes(self, data_url: str) -> bytes:
        import base64

        return base64.b64decode(self._data_url_to_base64(data_url))
