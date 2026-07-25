import asyncio
import base64
import shutil
import sys
import unittest
import uuid
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.schemas import DetectedObject, EstimatedDimensions, FurnitureGenerationBrief
from app.services.model3d.feature_hunyuan_provider import FeatureHunyuanModel3DProvider
from app.storage.local_store import OUTPUTS_ROOT


def image_base64(color: tuple[int, int, int]) -> str:
    buffer = BytesIO()
    Image.new("RGB", (256, 256), color).save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def brief() -> FurnitureGenerationBrief:
    return FurnitureGenerationBrief(
        objectId="obj_chair_001",
        category="chair",
        prompt="One isolated wooden chair with four legs.",
        negativePrompt="people, clutter",
    )


def provider() -> FeatureHunyuanModel3DProvider:
    return FeatureHunyuanModel3DProvider(
        ark_api_key="ark-test",
        ark_base_url="https://ark.example/api/v3",
        ark_vision_model="vision",
        ark_image_model="seedream",
        ark_image_size="2048x2048",
        hunyuan_api_key="hunyuan-test",
        hunyuan_base_url="https://hunyuan.example",
        hunyuan_model="hy-3d-3.1",
        hunyuan_generate_type="Normal",
        hunyuan_face_count=30000,
        hunyuan_enable_pbr=False,
        hunyuan_enable_geometry=False,
        hunyuan_result_format="GLB",
        hunyuan_poll_interval_sec=0,
        hunyuan_poll_attempts=1,
    )


class HunyuanReferenceProtocolTest(unittest.TestCase):
    @contextmanager
    def _test_directory(self):
        root = OUTPUTS_ROOT / f"_hunyuan_reference_test_{uuid.uuid4().hex}"
        root.mkdir(parents=True, exist_ok=False)
        try:
            yield root
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_seedream_creates_one_oblique_reference_image(self) -> None:
        response = httpx.Response(
            200,
            request=httpx.Request("POST", "https://ark.example/api/v3/images/generations"),
            json={
                "data": [
                    {"b64_json": image_base64((220, 20, 20))},
                ]
            },
        )
        with self._test_directory() as temp_dir:
            with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=response)) as post:
                artifacts = asyncio.run(
                    provider()._create_reference_views(
                        brief(),
                        temp_dir,
                        "data:image/jpeg;base64,source",
                    )
                )

            self.assertEqual([item.type for item in artifacts], ["reference_oblique_3quarter"])
            self.assertEqual(Path(artifacts[0].path or "").suffix, ".png")
            payload = post.await_args.kwargs["json"]
            self.assertEqual(payload["sequential_image_generation"], "disabled")
            self.assertNotIn("sequential_image_generation_options", payload)
            self.assertEqual(payload["image"], ["data:image/jpeg;base64,source"])
            self.assertIn("single 45-degree front-left oblique product reference render", payload["prompt"])

    def test_hunyuan_payload_uses_last_reference_as_single_primary_image(self) -> None:
        response = httpx.Response(
            200,
            request=httpx.Request("POST", "https://hunyuan.example/v1/api/3d/submit"),
            json={"id": "task-123"},
        )
        images = [
            "data:image/jpeg;base64,c291cmNl",
            "data:image/png;base64,cmVmZXJlbmNl",
        ]
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=response)) as post:
            task_id = asyncio.run(provider()._create_3d_task(images, brief()))

        self.assertEqual(task_id, "task-123")
        payload = post.await_args.kwargs["json"]
        self.assertEqual(payload["image_base64"], "cmVmZXJlbmNl")
        self.assertEqual(payload["generate_type"], "Normal")
        self.assertNotIn("multi_view_images", payload)

    def test_estimated_dimensions_are_added_to_generation_brief_and_prompt(self) -> None:
        detected = DetectedObject(
            id="obj_table_001",
            label="dining_table",
            name="木质餐桌",
            confidence=0.91,
            bbox=[10, 20, 300, 220],
            tagPosition=[0.5, 0.5],
            visualFeatures={
                "geometry": "rectangular tabletop and four legs",
                "materials": ["wood"],
                "colors": ["warm brown"],
            },
            generationHints={"preserve": ["four legs"], "cleanupActions": []},
            estimatedDimensions=EstimatedDimensions(
                widthM=1.7,
                depthM=0.9,
                heightM=0.8,
            ),
        )

        generation_brief = provider()._brief_from_step1(detected)
        dimensions = generation_brief.constraints["physicalDimensionsMeters"]
        self.assertEqual(dimensions["widthM"], 1.7)
        self.assertEqual(dimensions["depthM"], 0.9)
        self.assertEqual(dimensions["heightM"], 0.8)
        self.assertFalse(dimensions["isMeasured"])
        self.assertIn("1.70 m wide", generation_brief.prompt)
        self.assertIn("0.90 m deep", generation_brief.prompt)
        self.assertIn("0.80 m high", generation_brief.prompt)
        self.assertIn(
            '"physicalDimensionsMeters"',
            provider()._reference_view_prompt(
                generation_brief,
                "single 45-degree front-left oblique product reference render",
            ),
        )


if __name__ == "__main__":
    unittest.main()
