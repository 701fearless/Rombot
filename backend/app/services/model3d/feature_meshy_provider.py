import asyncio
import base64
import json
import re
from pathlib import Path
from typing import Any

import httpx
from PIL import Image, ImageDraw

from app.schemas import (
    DetectedObject,
    FurnitureGenerationBrief,
    FurnitureGenerationTrace,
    GenerationArtifact,
    ObjectAnalysis,
    SelectObjectResponse,
    SelectedAsset,
)
from app.services.model3d.base import Model3DProvider
from app.storage.local_store import (
    file_to_data_url,
    frame_output_dir,
    output_url_to_path,
    path_to_output_url,
    save_data_url,
)


VIEW_SPECS = [
    ("front", "front orthographic product render"),
    ("left_3quarter", "left front three-quarter product render"),
    ("back", "back orthographic product render inferred from symmetry and material continuity"),
]


class FeatureMeshyModel3DProvider(Model3DProvider):
    """
    Feature-grounded full generation:
    evidence image -> detailed furniture brief -> reference views/material board -> Meshy multi-image-to-3D.
    """

    def __init__(
        self,
        openai_api_key: str,
        openai_base_url: str,
        openai_vision_model: str,
        openai_image_model: str,
        openai_image_size: str,
        meshy_api_key: str,
        meshy_base_url: str,
        meshy_ai_model: str,
        meshy_poll_interval_sec: float,
        meshy_poll_attempts: int,
    ) -> None:
        self.provider_name = "feature_meshy"
        self.openai_api_key = openai_api_key
        self.openai_base_url = openai_base_url.rstrip("/")
        self.openai_vision_model = openai_vision_model
        self.openai_image_model = openai_image_model
        self.openai_image_size = openai_image_size
        self.meshy_api_key = meshy_api_key
        self.meshy_base_url = meshy_base_url.rstrip("/")
        self.meshy_ai_model = meshy_ai_model
        self.meshy_poll_interval_sec = meshy_poll_interval_sec
        self.meshy_poll_attempts = meshy_poll_attempts

    async def generate_asset(
        self,
        frame_id: str,
        detected_object: DetectedObject,
        image_url: str | None = None,
    ) -> SelectObjectResponse:
        if not image_url:
            raise ValueError("feature_meshy requires a segmented crop image or image URL")

        work_dir = frame_output_dir(frame_id) / f"{detected_object.id}_feature_generation"
        work_dir.mkdir(parents=True, exist_ok=True)

        source_image = self._normalize_image_input(image_url)
        brief = await self._create_generation_brief(detected_object, source_image)
        brief_path = work_dir / "FurnitureGenerationBrief.json"
        brief_path.write_text(brief.model_dump_json(indent=2), encoding="utf-8")

        texture_refs = self._create_texture_reference_board(source_image, work_dir)
        reference_refs = await self._create_reference_views(brief, work_dir, source_image)

        image_inputs = [source_image]
        for ref in reference_refs:
            if ref.path and Path(ref.path).exists():
                image_inputs.append(file_to_data_url(Path(ref.path)))
            elif ref.url:
                image_inputs.append(ref.url)
        image_inputs = image_inputs[:4]

        task_id = await self._create_3d_task(image_inputs=image_inputs, brief=brief)
        task_path = work_dir / "model3d_task.json"
        task_path.write_text(
            json.dumps({"provider": self.provider_name, "taskId": task_id}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        result = await self._poll_3d_task(task_id)
        result_path = work_dir / "model3d_result.json"
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        remote_glb_url = self._extract_glb_url(result)
        glb_url = await self._cache_remote_glb(remote_glb_url, work_dir) if remote_glb_url else None
        glb_url = glb_url or remote_glb_url or "/sample_data/models/sofa.glb"
        status = result.get("status", "unknown") if remote_glb_url else "fallback_mock"

        generation = FurnitureGenerationTrace(
            briefUrl=path_to_output_url(brief_path),
            sourceImageUrl=image_url,
            referenceImages=reference_refs,
            textureReferences=texture_refs,
            provider=self.provider_name,
            notes=[
                "Furniture geometry is fully generated from feature brief and reference images.",
                "estimatedDimensions provides the initial metric import scale; the user may adjust it later.",
                f"3D task metadata: {path_to_output_url(task_path)}",
                f"3D result metadata: {path_to_output_url(result_path)}",
                f"Remote GLB source: {remote_glb_url}" if remote_glb_url else "No remote GLB URL found; using fallback.",
            ],
        )

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
                estimatedDimensions=detected_object.estimatedDimensions,
                glbUrl=glb_url,
            ),
            analysis=ObjectAnalysis(
                summary="已按“特征捕捉 -> 联想补全 -> 完整 3D 生成”链路创建家具资产。",
                placementAdvice="导入空间时先按 estimatedDimensions 设置宽、深、高；用户后续可按观感继续缩放。",
            ),
            generation=generation,
        )

    def _normalize_image_input(self, image_url: str) -> str:
        if image_url.startswith("data:image/"):
            return image_url
        local_path = output_url_to_path(image_url)
        if local_path and local_path.exists():
            return file_to_data_url(local_path)
        return image_url

    async def _create_generation_brief(
        self,
        detected_object: DetectedObject,
        source_image: str,
    ) -> FurnitureGenerationBrief:
        schema = FurnitureGenerationBrief.model_json_schema()
        prompt = f"""
You are a senior 3D furniture asset director.

Read the furniture image and produce a detailed generation brief for a full generative 3D model.
The final 3D model will be generated, not reconstructed. Visible evidence should constrain the asset;
unseen back, side, underside, and occluded parts should be inferred using furniture symmetry,
category priors, repeated components, and material consistency.
Before writing the prompt, regularize household disorder and reduce 3D modeling
complexity: remove temporary clutter, overlapping fabric layers, crumpled bedding,
scattered pillows, cables, piles, deep wrinkles, dense tiny folds and fringe tangles.
Prefer broad clean surfaces, shallow orderly folds, aligned soft parts, simple curtain
waves and clearly separated non-intersecting components.

Detected object:
- id: {detected_object.id}
- label: {detected_object.label}
- display name: {detected_object.name}
- bbox: {detected_object.bbox}

Return JSON only. The `prompt` field must be a detailed English prompt suitable for a 3D generation model.
The `negativePrompt` field must list visual traits to avoid.
Mark uncertain inferred details with low confidence values.
"""
        payload = {
            "model": self.openai_vision_model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": source_image},
                    ],
                }
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "furniture_generation_brief",
                    "schema": schema,
                    "strict": False,
                }
            },
        }
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{self.openai_base_url}/v1/responses",
                headers=self._openai_headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        raw_text = self._extract_output_text(data)
        parsed = self._parse_json_object(raw_text)
        parsed.setdefault("objectId", detected_object.id)
        parsed.setdefault("category", detected_object.label)
        parsed.setdefault("prompt", self._fallback_prompt(detected_object))
        parsed.setdefault("negativePrompt", "low quality, distorted furniture, impossible structure, extra random parts")
        return FurnitureGenerationBrief.model_validate(parsed)

    async def _create_reference_views(
        self,
        brief: FurnitureGenerationBrief,
        work_dir: Path,
        source_image: str | None = None,
    ) -> list[GenerationArtifact]:
        _ = source_image
        artifacts: list[GenerationArtifact] = []
        for view_id, view_text in VIEW_SPECS:
            prompt = self._reference_view_prompt(brief, view_text)
            payload = {
                "model": self.openai_image_model,
                "prompt": prompt,
                "size": self.openai_image_size,
                "n": 1,
            }
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.openai_base_url}/v1/images/generations",
                    headers=self._openai_headers(),
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

            b64_json = (data.get("data") or [{}])[0].get("b64_json")
            image_result_url = (data.get("data") or [{}])[0].get("url")
            if b64_json:
                output_path = work_dir / f"reference_{view_id}.png"
                output_path.write_bytes(base64.b64decode(b64_json))
                artifacts.append(
                    GenerationArtifact(
                        type=f"reference_{view_id}",
                        url=path_to_output_url(output_path),
                        path=str(output_path),
                        note=view_text,
                    )
                )
            elif image_result_url:
                artifacts.append(GenerationArtifact(type=f"reference_{view_id}", url=image_result_url, note=view_text))
        return artifacts

    def _create_texture_reference_board(self, source_image: str, work_dir: Path) -> list[GenerationArtifact]:
        if not source_image.startswith("data:image/"):
            return []

        source_path = work_dir / "source_crop.png"
        save_data_url(source_image, source_path)
        image = Image.open(source_path).convert("RGB")
        width, height = image.size

        crops = [
            image.crop((0, 0, width, height)),
            image.crop((width * 1 // 4, height * 1 // 4, width * 3 // 4, height * 3 // 4)),
            image.crop((width * 1 // 8, height * 1 // 3, width * 7 // 8, height * 2 // 3)),
            image.crop((width * 1 // 3, height * 1 // 8, width * 2 // 3, height * 7 // 8)),
        ]

        tile = 256
        board = Image.new("RGB", (tile * 2, tile * 2), "white")
        for idx, crop in enumerate(crops):
            crop.thumbnail((tile, tile))
            x = (idx % 2) * tile + (tile - crop.width) // 2
            y = (idx // 2) * tile + (tile - crop.height) // 2
            board.paste(crop, (x, y))

        draw = ImageDraw.Draw(board)
        draw.rectangle((0, 0, board.width - 1, board.height - 1), outline=(180, 180, 180), width=2)
        output_path = work_dir / "material_board.png"
        board.save(output_path)
        return [
            GenerationArtifact(
                type="material_board",
                url=path_to_output_url(output_path),
                path=str(output_path),
                note="Local texture/color reference board cropped from the furniture evidence image.",
            )
        ]

    async def _create_3d_task(self, image_inputs: list[str], brief: FurnitureGenerationBrief) -> str:
        _ = brief
        payload = {
            "image_urls": image_inputs,
            "ai_model": self.meshy_ai_model,
            "target_formats": ["glb"],
            "should_texture": True,
            "enable_pbr": True,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.meshy_base_url}/openapi/v1/multi-image-to-3d",
                headers=self._meshy_headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        task_id = data.get("result") or data.get("id") or data.get("task_id")
        if not task_id:
            raise ValueError(f"Meshy did not return a task id: {data}")
        return task_id

    async def _poll_3d_task(self, task_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            for _ in range(self.meshy_poll_attempts):
                response = await client.get(
                    f"{self.meshy_base_url}/openapi/v1/multi-image-to-3d/{task_id}",
                    headers=self._meshy_headers(),
                )
                response.raise_for_status()
                data = response.json()
                if data.get("status") in {"SUCCEEDED", "succeeded", "FAILED", "failed", "EXPIRED", "expired"}:
                    return data
                await asyncio.sleep(self.meshy_poll_interval_sec)
        return {"status": "timeout"}

    def _extract_glb_url(self, result: dict[str, Any]) -> str | None:
        model_urls = result.get("model_urls") or {}
        if isinstance(model_urls, dict):
            return model_urls.get("glb")
        return None

    async def _cache_remote_glb(self, glb_url: str | None, work_dir: Path) -> str | None:
        if not glb_url or glb_url.startswith("/"):
            return glb_url
        if not glb_url.startswith(("http://", "https://")):
            return None

        output_path = work_dir / "generated_model.glb"
        async with httpx.AsyncClient(timeout=180, follow_redirects=True) as client:
            response = await client.get(glb_url)
            response.raise_for_status()
            content = response.content
        if content[:4] != b"glTF":
            raise ValueError(f"Downloaded model is not a GLB file: {content[:16]!r}")
        output_path.write_bytes(content)
        return path_to_output_url(output_path)

    def _reference_view_prompt(self, brief: FurnitureGenerationBrief, view_text: str) -> str:
        return f"""
Create a clean isolated product reference image for 3D generation.
View: {view_text}.

Furniture generation prompt:
{brief.prompt}

Texture and material notes:
{json.dumps(brief.textureFeatures, ensure_ascii=False)}

Inferred details:
{json.dumps(brief.inferred, ensure_ascii=False)}

Use a plain white background. Show one complete object only. Keep the object centered, realistic,
regular, and consistent with the visible evidence. Do not add labels, text, people, room background, or extra props.
Simplify for fast 3D modeling: broad surfaces, shallow regular folds, aligned cushions or pillows,
flat rugs, simple curtain waves and no tangled fabric, deep wrinkles, dense tiny folds,
clutter piles, cables, fringe tangles or intersecting temporary layers.
Avoid: {brief.negativePrompt}
"""

    def _fallback_prompt(self, detected_object: DetectedObject) -> str:
        return (
            f"Create a complete realistic 3D model of a {detected_object.label}. "
            "Use a regular furniture structure, plausible symmetry, clean PBR materials, and a complete closed mesh."
        )

    def _extract_output_text(self, response_data: dict[str, Any]) -> str:
        if isinstance(response_data.get("output_text"), str):
            return response_data["output_text"]
        parts: list[str] = []
        for item in response_data.get("output", []):
            for content in item.get("content", []):
                text = content.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)

    def _parse_json_object(self, raw_text: str) -> dict[str, Any]:
        candidates = [raw_text.strip()]
        match = re.search(r"\{.*\}", raw_text, flags=re.S)
        if match:
            candidates.append(match.group(0))
        # Repair truncated JSON from max_tokens cutoffs.
        repaired = raw_text.strip()
        if repaired and not repaired.endswith("}"):
            if repaired.count('"') % 2 == 1:
                repaired += '"'
            open_braces = repaired.count("{") - repaired.count("}")
            open_brackets = repaired.count("[") - repaired.count("]")
            repaired += "]" * max(0, open_brackets)
            repaired += "}" * max(0, open_braces)
            candidates.append(repaired)
        last_error: Exception | None = None
        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except Exception as exc:  # noqa: BLE001
                last_error = exc
        raise ValueError(f"Failed to parse JSON brief: {last_error}\nraw={raw_text[:500]}")

    def _openai_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.openai_api_key}", "Content-Type": "application/json"}

    def _meshy_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.meshy_api_key}", "Content-Type": "application/json"}
