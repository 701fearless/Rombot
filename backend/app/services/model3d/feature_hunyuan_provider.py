import asyncio
import base64
import json
from pathlib import Path
from typing import Any

import httpx

from app.schemas import DetectedObject, FurnitureGenerationBrief, GenerationArtifact
from app.services.model3d.feature_meshy_provider import FeatureMeshyModel3DProvider
from app.storage.local_store import path_to_output_url


class FeatureHunyuanModel3DProvider(FeatureMeshyModel3DProvider):
    """
    Uses Volcengine Ark for feature capture and Seedream reference views, then submits
    the images to Tencent Hunyuan's async 3D API:
    POST /v1/api/3d/submit
    POST /v1/api/3d/query
    """

    def __init__(
        self,
        ark_api_key: str,
        ark_base_url: str,
        ark_vision_model: str,
        ark_image_model: str,
        ark_image_size: str,
        hunyuan_api_key: str,
        hunyuan_base_url: str,
        hunyuan_model: str,
        hunyuan_generate_type: str,
        hunyuan_face_count: int,
        hunyuan_enable_pbr: bool,
        hunyuan_enable_geometry: bool,
        hunyuan_result_format: str,
        hunyuan_poll_interval_sec: float,
        hunyuan_poll_attempts: int,
    ) -> None:
        super().__init__(
            openai_api_key="",
            openai_base_url="",
            openai_vision_model="",
            openai_image_model="",
            openai_image_size=ark_image_size,
            meshy_api_key="",
            meshy_base_url="",
            meshy_ai_model="",
            meshy_poll_interval_sec=hunyuan_poll_interval_sec,
            meshy_poll_attempts=hunyuan_poll_attempts,
        )
        self.provider_name = "feature_hunyuan"
        self.ark_api_key = ark_api_key
        self.ark_base_url = ark_base_url.rstrip("/")
        self.ark_vision_model = ark_vision_model
        self.ark_image_model = ark_image_model
        self.ark_image_size = ark_image_size
        self.hunyuan_api_key = hunyuan_api_key
        self.hunyuan_base_url = hunyuan_base_url.rstrip("/")
        self.hunyuan_model = hunyuan_model
        self.hunyuan_generate_type = hunyuan_generate_type
        self.hunyuan_face_count = hunyuan_face_count
        self.hunyuan_enable_pbr = hunyuan_enable_pbr
        self.hunyuan_enable_geometry = hunyuan_enable_geometry
        self.hunyuan_result_format = hunyuan_result_format
        self.hunyuan_poll_interval_sec = hunyuan_poll_interval_sec
        self.hunyuan_poll_attempts = hunyuan_poll_attempts

    async def _create_generation_brief(
        self,
        detected_object: DetectedObject,
        source_image: str,
    ) -> FurnitureGenerationBrief:
        if detected_object.visualFeatures and detected_object.generationHints:
            return self._brief_from_step1(detected_object)

        prompt = f"""
快速读取图片中的主体家居/商品，只返回紧凑 JSON，不要解释。

【强制主体规则】
1. 必须独立识别画面中的唯一主体商品/家具，只围绕该主体建模。
2. 严禁把人手、手臂、桌面、椅子、背景货架、房间环境、手机 UI、字幕、水印、点赞评论按钮等杂物写进主体。
3. 若其他主体遮挡主体局部，按类别先验、对称性与材质连续性合理补全被遮挡部分，而不是把手一起生成。
4. 对未露全的背面、侧面、底面、支架、开口内侧，基于结构合理性推断补全，并在 confidence 中标注不确定度。
5. 最终模型是完整独立资产，不是场景扫描；可见区域必须忠于图片证据。

【常见家居补全先验】
1. 矩形/方形物件：四边边框连续等宽，倒角、厚度、内外轮廓应一致。
2. 相框/画框/托盘/柜门/装饰面板：内部纹样必须连续铺满到边缘；遮挡、缺失或低置信区域使用镜像、平移、重复纹样补全，禁止留下空白纹理块。
3. 花瓶/杯/灯罩/桌腿：优先轴对称或左右对称，轮廓平滑闭合。
4. 沙发/床/柜/桌椅：左右对称、部件重复、材质连续，不考虑过度异形或怪异设计。
5. 遮挡区只能做规整合理补全，不要生成随机新装饰。

检测提示（仅供参考，仍以图片中真实主体为准）：
- id: {detected_object.id}
- label: {detected_object.label}
- name: {detected_object.name}
- bbox: {detected_object.bbox}

【输出格式硬性要求】
只返回一个 JSON 对象，不要 Markdown。字段类型必须严格如下：
- objectId: string
- category: string
- observed: object（键值对，不要用长字符串）
- inferred: object
- symmetryPrior: object
- textureFeatures: object
- constraints: object（至少含 subjectIsolation、occlusionCompletion）
- prompt: string（英文）
- negativePrompt: string
- confidence: object（数值或短文本值）

内容要求：
- observed 只描述主体可见部分；inferred 描述补全的遮挡/未见部分。
- constraints 必须包含 subjectIsolation 与 occlusionCompletion。
- prompt 必须英文，120-180 词，并写明 isolated single object, symmetry, repeated pattern continuation, no missing texture gaps, plain background, no hands/people/UI/furniture clutter。
- negativePrompt 必须排除 hands, people, UI, captions, table, chair, background props。
"""
        step1_features = json.dumps(detected_object.visualFeatures, ensure_ascii=False)
        step1_hints = json.dumps(detected_object.generationHints, ensure_ascii=False)
        dimension_evidence = json.dumps(
            (
                detected_object.estimatedDimensions.model_dump()
                if detected_object.estimatedDimensions
                else None
            ),
            ensure_ascii=False,
        )
        prompt = f"""
You are a senior furniture asset director. Return one compact JSON object only.
The output will drive a single generated product reference image and then a 3D model.

Detected object:
- id: {detected_object.id}
- category: {detected_object.label}
- display name: {detected_object.name}
- bbox: {detected_object.bbox}
- estimated metric dimensions: {dimension_evidence}

Step-1 evidence already extracted from the original frame:
visualFeatures = {step1_features}
generationHints = {step1_hints}

Use those fields as primary evidence. Inspect the supplied crop only to verify or add
missing visible details. Do not repeat a long scene description.

Required behavior:
1. Keep one isolated main object. Exclude people, hands, phone UI, captions, watermarks,
   floor, walls, tables and unrelated furniture or props.
2. Preserve visible identity-defining geometry, proportions, colors, materials and motifs.
3. Regularize temporary household disorder before generation:
   - beds: align pillows, straighten and center duvet/blanket, remove clothes;
   - sofas/armchairs: align cushions and pillows, smooth throws, restore repeated seats;
   - desks/tables/nightstands: remove dishes, cables and loose items;
   - cabinets/wardrobes/bookshelves: align doors, drawers, handles and repeated modules;
   - chairs: center loose cushions and restore paired legs/arms;
   - rugs/curtains: flatten curled edges or use orderly natural folds;
   - lamps/vases/frames/mirrors: restore continuous borders, axial/bilateral symmetry,
     repeated decorative patterns and complete occluded areas.
   - simplify for efficient 3D generation: remove temporary overlapping fabric layers,
     tangled throws, crumpled bedding, scattered pillows, cables, piles, fringe tangles,
     deep wrinkles and dense tiny folds; convert them into clean broad surfaces, shallow
     regular folds and separated non-intersecting parts.
4. Complete unseen back, side, underside and occluded regions conservatively using
   category priors, symmetry, repeated modules, material continuity and closed geometry.
5. Repeated texture must continue through occluded or low-confidence regions. Never
   create blank texture islands. Do not invent random decorations, extra parts, bizarre
   shapes or unusually artistic furniture unless clearly supported by visible evidence.

Return these exact fields:
{{
  "objectId": "string",
  "category": "string",
  "observed": {{}},
  "inferred": {{}},
  "symmetryPrior": {{}},
  "textureFeatures": {{}},
  "constraints": {{
    "subjectIsolation": "string",
    "regularization": [],
    "complexityReduction": [],
    "occlusionCompletion": "string"
  }},
  "prompt": "80-170 word English product-generation prompt",
  "negativePrompt": "comma-separated exclusions",
  "confidence": {{}}
}}
"""
        payload = {
            "model": self.ark_vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": source_image}},
                    ],
                }
            ],
            "temperature": 0.1,
            "max_tokens": 1400,
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=360.0, write=60.0, connect=30.0)) as client:
            last_error: Exception | None = None
            data = None
            for attempt in range(1, 4):
                try:
                    response = await client.post(
                        f"{self.ark_base_url}/chat/completions",
                        headers=self._ark_headers(),
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    break
                except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.RemoteProtocolError) as exc:
                    last_error = exc
                    if attempt >= 3:
                        raise
                    await asyncio.sleep(2 * attempt)
            if data is None:
                raise RuntimeError(f"Ark vision failed: {last_error}")

        raw_text = self._extract_chat_completion_text(data)
        parsed = self._parse_json_object(raw_text)
        parsed.setdefault("objectId", detected_object.id)
        parsed.setdefault("category", detected_object.label)
        parsed.setdefault("prompt", self._fallback_prompt(detected_object))
        parsed.setdefault(
            "negativePrompt",
            "hands, people, UI icons, captions, watermarks, table, chair, background props, clutter, low quality, distorted geometry",
        )
        for key in ("observed", "inferred", "symmetryPrior", "textureFeatures", "constraints", "confidence"):
            value = parsed.get(key)
            if isinstance(value, str):
                parsed[key] = {"text": value}
            elif value is None:
                parsed[key] = {}
            elif isinstance(value, list):
                parsed[key] = {"items": value}
        if detected_object.estimatedDimensions:
            parsed["constraints"]["physicalDimensionsMeters"] = self._dimension_constraint(detected_object)
            parsed["confidence"]["dimensionEstimate"] = "category-prior initial size"
        return FurnitureGenerationBrief.model_validate(parsed)

    def _brief_from_step1(self, detected_object: DetectedObject) -> FurnitureGenerationBrief:
        features = detected_object.visualFeatures
        hints = detected_object.generationHints
        materials = features.get("materials") or []
        colors = features.get("colors") or []
        texture_pattern = features.get("texturePattern") or "preserve visible material continuity"
        cleanup_actions = hints.get("cleanupActions") or []
        symmetry = hints.get("symmetry") or {}
        occlusion = hints.get("occlusionCompletion") or []
        complexity_reduction = hints.get("complexityReduction") or []
        pattern_completion = hints.get("patternCompletion") or "continue repeated visible motifs without gaps"
        preserve = hints.get("preserve") or []
        remove = hints.get("remove") or []
        dimension_constraint = self._dimension_constraint(detected_object)
        dimension_prompt = ""
        if dimension_constraint:
            dimension_prompt = (
                f"Target plausible real-world dimensions are approximately "
                f"{dimension_constraint['widthM']:.2f} m wide, "
                f"{dimension_constraint['depthM']:.2f} m deep and "
                f"{dimension_constraint['heightM']:.2f} m high. "
                "Preserve the corresponding width-to-depth-to-height proportions. "
                "These are category-prior estimates rather than pixel measurements. "
            )

        prompt = (
            f"Create one complete, realistic, isolated {detected_object.label} as a regular household product. "
            f"Visible geometry and style: {features.get('geometry', 'preserve the observed silhouette and proportions')}; "
            f"{features.get('style', 'ordinary coherent design')}. "
            f"Use materials {materials} and colors {colors}. Preserve {preserve}. "
            f"Regularize temporary disorder with {cleanup_actions}. "
            f"Simplify modeling complexity with {complexity_reduction}: use clean broad surfaces, "
            "shallow orderly folds, separated non-intersecting parts, and avoid tangled fabric or dense tiny wrinkles. "
            f"Complete occluded, back, side and underside regions using {symmetry} and {occlusion}. "
            f"Texture rule: {texture_pattern}; {pattern_completion}. "
            f"{dimension_prompt}"
            "Use conservative category structure, repeated modules, continuous closed geometry, and one "
            "45-degree product view on a plain light background. Keep only the main object."
        )
        negative_prompt = (
            "people, hands, body parts, phone UI, captions, watermarks, room background, floor, walls, "
            f"unrelated furniture, temporary clutter, {remove}, blank texture gaps, random ornaments, "
            "extra parts, bizarre shapes, asymmetry unsupported by evidence, distorted geometry"
        )
        return FurnitureGenerationBrief(
            objectId=detected_object.id,
            category=detected_object.label,
            observed=features,
            inferred={
                "cleanupActions": cleanup_actions,
                "complexityReduction": complexity_reduction,
                "occlusionCompletion": occlusion,
                "patternCompletion": pattern_completion,
            },
            symmetryPrior=symmetry if isinstance(symmetry, dict) else {"rule": symmetry},
            textureFeatures={
                "materials": materials,
                "colors": colors,
                "texturePattern": texture_pattern,
            },
            constraints={
                "subjectIsolation": "one isolated main object only",
                "regularization": cleanup_actions,
                "complexityReduction": complexity_reduction,
                "occlusionCompletion": occlusion,
                "preserve": preserve,
                "remove": remove,
                "physicalDimensionsMeters": dimension_constraint,
            },
            prompt=prompt,
            negativePrompt=negative_prompt,
            confidence={
                "step1Detection": detected_object.confidence,
                "visibleEvidence": "high",
                "inferredHiddenParts": "medium",
                "dimensionEstimate": (
                    "category-prior initial size"
                    if detected_object.estimatedDimensions
                    else "unavailable"
                ),
            },
        )

    def _dimension_constraint(self, detected_object: DetectedObject) -> dict:
        dimensions = detected_object.estimatedDimensions
        if dimensions is None:
            return {}
        return {
            "widthM": dimensions.widthM,
            "depthM": dimensions.depthM,
            "heightM": dimensions.heightM,
            "unit": dimensions.unit,
            "source": dimensions.source,
            "isMeasured": dimensions.isMeasured,
            "selectionRule": dimensions.selectionRule,
        }

    async def _create_reference_views(
        self,
        brief: FurnitureGenerationBrief,
        work_dir: Path,
        source_image: str | None = None,
    ) -> list[GenerationArtifact]:
        artifacts: list[GenerationArtifact] = []
        for view_id, view_text in [
            ("oblique_3quarter", "single 45-degree front-left oblique product reference render"),
        ]:
            payload = {
                "model": self.ark_image_model,
                "prompt": self._reference_view_prompt(brief, view_text),
                "size": self.ark_image_size,
                "sequential_image_generation": "disabled",
                "stream": False,
                "response_format": "b64_json",
                "watermark": False,
            }
            if source_image:
                payload["image"] = [source_image]
            async with httpx.AsyncClient(timeout=300) as client:
                response = await client.post(
                    f"{self.ark_base_url}/images/generations",
                    headers=self._ark_headers(),
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

            image_item = (data.get("data") or [{}])[0]
            b64_json = image_item.get("b64_json")
            image_result_url = image_item.get("url")
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
                artifacts.append(
                    GenerationArtifact(
                        type=f"reference_{view_id}",
                        url=image_result_url,
                        note=view_text,
                    )
                )
            else:
                raise ValueError("Seedream returned no reference image payload")
        return artifacts

    async def _create_3d_task(self, image_inputs: list[str], brief: FurnitureGenerationBrief) -> str:
        # The original crop guides Seedream. Hunyuan consumes the final generated
        # 45-degree product reference, matching 识图生图生3D协议与Prompt.md.
        primary_image = image_inputs[-1] if image_inputs else None
        payload: dict[str, Any] = {
            "model": self.hunyuan_model,
            "enable_pbr": self.hunyuan_enable_pbr,
        }
        if primary_image and primary_image.startswith("data:image/"):
            payload["image_base64"] = self._data_url_to_base64(primary_image)
        elif primary_image:
            payload["image_url"] = primary_image
        else:
            payload["prompt"] = self._limit_prompt(brief.prompt)

        if self.hunyuan_model == "hy-3d-express":
            payload.update(
                {
                    "result_format": self.hunyuan_result_format,
                    "enable_geometry": self.hunyuan_enable_geometry,
                }
            )
        elif self.hunyuan_model in {"hy-3d-3.0", "hy-3d-3.1"}:
            payload.update(
                {
                    "generate_type": self.hunyuan_generate_type,
                    "face_count": self.hunyuan_face_count,
                }
            )
            # LowPoly / Sketch are supported on 3.0; 3.1 rejects LowPoly.
            if self.hunyuan_generate_type == "LowPoly":
                payload["polygon_type"] = "triangle"
        else:
            payload["result_format"] = "GLB"

        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                async with httpx.AsyncClient(timeout=180) as client:
                    response = await client.post(
                        self._submit_url(),
                        headers=self._hunyuan_headers(),
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                break
            except Exception as exc:  # noqa: BLE001 - retry gateway timeouts
                last_error = exc
                if attempt >= 3:
                    raise
                await asyncio.sleep(2 * attempt)
        else:
            raise RuntimeError(f"Hunyuan submit failed: {last_error}")

        task_id = self._extract_task_id(data)
        if not task_id:
            raise ValueError(f"Hunyuan submit did not return a task id: {data}")
        return task_id

    def _reference_view_prompt(self, brief: FurnitureGenerationBrief, view_text: str) -> str:
        return f"""
Create a clean isolated product reference image for single-object 3D generation.
View: {view_text}.

CRITICAL SUBJECT RULES:
- Independently keep ONLY the main subject product from the evidence.
- Remove all clutter: human hands, people, phone UI, captions, watermarks, table, chair, shelves, room background, other props.
- Reconstruct any hand-occluded or incomplete regions with plausible symmetry, material continuity, and category priors.
- Apply the brief's regularization actions: align loose cushions and pillows, smooth
  blankets or throws, close/align repeated doors and drawers, clear temporary clutter,
  and restore regular folds or paired components as appropriate for the category.
- Simplify the generated reference for faster 3D modeling: use broad clean surfaces,
  shallow low-frequency folds, tidy bedding, aligned pillows/cushions, flat rugs,
  simple hanging curtain waves and clearly separated components. Remove tangled cloth,
  crumpled blankets, deep wrinkles, dense tiny folds, fringe tangles, cables, piles,
  scattered loose objects and overlapping temporary layers.
- Show one complete centered object on a plain white/light studio background.
- If the object has a rectangular frame, panel, tray, cabinet door, picture-frame vase, or decorative inset, keep all borders continuous and equal-width.
- Continue repeated decorative textures across missing, occluded, or low-confidence areas by mirroring, translating, or tiling the visible pattern. No blank texture gaps are allowed.
- Prefer regular household symmetry: bilateral symmetry, axial symmetry, repeated modules, continuous material, and smooth closed outlines.

Generation brief prompt:
{brief.prompt}

Texture and material notes:
{json.dumps(brief.textureFeatures, ensure_ascii=False)}

Inferred / completed details:
{json.dumps(brief.inferred, ensure_ascii=False)}

Constraints:
{json.dumps(brief.constraints, ensure_ascii=False)}

Avoid: {brief.negativePrompt}; hands; people; UI icons; captions; furniture clutter; merged background objects.
Also avoid high-frequency wrinkles, excessive folds, intersecting cloth layers, chaotic overlaps, thin dangling strands, clutter piles and complex soft-body drapery.
"""

    async def _poll_3d_task(self, task_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=60) as client:
            for _ in range(self.hunyuan_poll_attempts):
                data = await self._query_once(client, task_id)
                status = self._normalize_status(data)
                if status in {"SUCCEEDED", "FAILED", "EXPIRED"}:
                    data.setdefault("status", status)
                    return data
                await asyncio.sleep(self.hunyuan_poll_interval_sec)
        return {"status": "timeout"}

    async def _query_once(self, client: httpx.AsyncClient, task_id: str) -> dict[str, Any]:
        payload = {"model": self.hunyuan_model, "id": task_id}
        response = await client.post(
            self._query_url(),
            headers=self._hunyuan_headers(),
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def _extract_task_id(self, data: dict[str, Any]) -> str | None:
        candidates = [
            data.get("task_id"),
            data.get("taskId"),
            data.get("id"),
            data.get("job_id"),
            data.get("JobId"),
        ]
        for container_name in ("result", "data", "Response", "response"):
            container = data.get(container_name)
            if isinstance(container, dict):
                candidates.extend(
                    [
                        container.get("task_id"),
                        container.get("taskId"),
                        container.get("id"),
                        container.get("job_id"),
                        container.get("JobId"),
                    ]
                )
            elif isinstance(container, str):
                candidates.append(container)
        return next((str(item) for item in candidates if item), None)

    def _extract_glb_url(self, result: dict[str, Any]) -> str | None:
        for response_key in ("Response", "response"):
            response = result.get(response_key)
            if not isinstance(response, dict):
                continue
            rapid_files = response.get("ResultFile3Ds") or response.get("result_file_3ds") or []
            if isinstance(rapid_files, list):
                for item in rapid_files:
                    if not isinstance(item, dict):
                        continue
                    item_type = str(item.get("Type") or item.get("type") or "").lower()
                    url = item.get("Url") or item.get("url")
                    if item_type == "glb" and url:
                        return str(url)

        # Prefer explicit glb entries first — Hunyuan often returns obj zip before glb.
        for container_name in ("data", "result", "output"):
            container = result.get(container_name)
            if isinstance(container, list):
                for item in container:
                    if isinstance(item, dict) and str(item.get("type", "")).lower() == "glb" and item.get("url"):
                        return str(item["url"])
            if isinstance(container, dict):
                model_urls = container.get("model_urls") or container.get("modelUrls")
                if isinstance(model_urls, dict) and model_urls.get("glb"):
                    return str(model_urls["glb"])
                for key in ("glb_url", "model_url", "modelUrl", "file_url"):
                    if container.get(key):
                        value = str(container[key])
                        if ".glb" in value.lower():
                            return value

        candidates = [
            result.get("glb_url"),
            result.get("model_url"),
            result.get("modelUrl"),
            result.get("file_url"),
        ]
        model_urls = result.get("model_urls") or result.get("modelUrls")
        if isinstance(model_urls, dict):
            candidates.append(model_urls.get("glb"))
        for item in candidates:
            if item and ".glb" in str(item).lower():
                return str(item)
        return next((str(item) for item in candidates if item), None)

    def _normalize_status(self, data: dict[str, Any]) -> str:
        raw_status = data.get("status") or data.get("state")
        for container_name in ("result", "data", "output", "Response", "response"):
            container = data.get(container_name)
            if not raw_status and isinstance(container, dict):
                raw_status = container.get("status") or container.get("state") or container.get("Status")

        status = str(raw_status or "").upper()
        if status in {"SUCCEEDED", "SUCCESS", "DONE", "COMPLETED", "FINISHED"}:
            return "SUCCEEDED"
        if status in {"FAILED", "FAIL", "ERROR"}:
            return "FAILED"
        if status in {"EXPIRED", "TIMEOUT"}:
            return "EXPIRED"
        # queued / in_progress / running / pending / WAIT / RUN all keep polling
        return "RUNNING"

    def _hunyuan_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.hunyuan_api_key}", "Content-Type": "application/json"}

    def _ark_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.ark_api_key}", "Content-Type": "application/json"}

    def _extract_chat_completion_text(self, response_data: dict[str, Any]) -> str:
        choices = response_data.get("choices") or []
        if not choices:
            return ""
        content = (choices[0].get("message") or {}).get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            return "\n".join(parts)
        return str(content)

    def _submit_url(self) -> str:
        base = self.hunyuan_base_url.rstrip("/")
        if base.endswith("/v1/api/3d/submit"):
            return base
        if base.endswith("/v1/api/3d/query"):
            return base[: -len("/query")] + "/submit"
        return f"{base}/v1/api/3d/submit"

    def _query_url(self) -> str:
        base = self.hunyuan_base_url.rstrip("/")
        if base.endswith("/v1/api/3d/query"):
            return base
        if base.endswith("/v1/api/3d/submit"):
            return base[: -len("/submit")] + "/query"
        return f"{base}/v1/api/3d/query"

    def _data_url_to_base64(self, data_url: str) -> str:
        if "," in data_url:
            return data_url.split(",", 1)[1]
        return data_url

    def _limit_prompt(self, prompt: str) -> str:
        limit = 200 if self.hunyuan_model.lower().endswith("express") else 1024
        return prompt[:limit]
