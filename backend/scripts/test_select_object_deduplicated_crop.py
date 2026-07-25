import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.routers.feed import select_object
from app.schemas import (
    DetectedObject,
    EstimatedDimensions,
    FurnitureGenerationTrace,
    ObjectAnalysis,
    SelectObjectRequest,
    SelectObjectResponse,
    SelectedAsset,
)


class RecordingProvider:
    def __init__(self) -> None:
        self.image_url: str | None = None

    async def generate_asset(
        self,
        frame_id: str,
        detected_object: DetectedObject,
        image_url: str | None = None,
    ) -> SelectObjectResponse:
        self.image_url = image_url
        return SelectObjectResponse(
            taskId="task",
            status="succeeded",
            object=SelectedAsset(
                id=detected_object.id,
                label=detected_object.label,
                name=detected_object.name,
                bbox=detected_object.bbox,
                cropUrl=image_url,
                maskUrl=detected_object.maskUrl,
                estimatedDimensions=detected_object.estimatedDimensions,
                glbUrl="/sample_data/models/sofa.glb",
            ),
            analysis=ObjectAnalysis(summary="ok", placementAdvice="ok"),
            generation=FurnitureGenerationTrace(provider="recording"),
        )


class SelectObjectDeduplicatedCropTest(unittest.TestCase):
    def test_preprocessed_object_uses_deduplicated_crop_as_model_input(self) -> None:
        detected = DetectedObject(
            id="obj_chair_001",
            label="chair",
            name="椅子",
            confidence=0.9,
            bbox=[10, 10, 100, 100],
            tagPosition=[0.5, 0.5],
            cropUrl="/outputs/videos/1/objects/frame-crop.jpg",
            maskUrl="/outputs/videos/1/objects/frame-mask.png",
            deduplicatedObjectId="candidate_chair_001",
            deduplicatedCropUrl="/outputs/videos/1/deduplicated/candidate_chair_001/crop.jpg",
            estimatedDimensions=EstimatedDimensions(widthM=0.5, depthM=0.55, heightM=0.9),
        )
        model_provider = RecordingProvider()
        with (
            patch("app.routers.feed.find_preprocessed_object", return_value=detected),
            patch("app.routers.feed.get_model3d_provider", return_value=model_provider),
        ):
            response = asyncio.run(
                select_object(SelectObjectRequest(frameId="1_000001", objectId=detected.id))
            )

        self.assertEqual(model_provider.image_url, detected.deduplicatedCropUrl)
        self.assertEqual(response.object.cropUrl, detected.deduplicatedCropUrl)
        self.assertEqual(response.object.estimatedDimensions, detected.estimatedDimensions)
        self.assertEqual(response.generation.sourceImageUrl, detected.deduplicatedCropUrl)


if __name__ == "__main__":
    unittest.main()
