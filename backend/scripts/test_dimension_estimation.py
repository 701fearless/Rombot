import asyncio
import shutil
import sys
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.schemas import (
    DeduplicatedObject,
    DetectedObject,
    EstimatedDimensions,
    VideoAnalysisFrame,
)
from app.services.video_preprocess.dimension_estimator import ArkFurnitureDimensionEstimator
from app.storage.local_store import OUTPUTS_ROOT, path_to_output_url


class FakeDimensionEstimator(ArkFurnitureDimensionEstimator):
    def __init__(self) -> None:
        super().__init__("test-key", "https://ark.example/api/v3", "test-model")
        self.calls: list[str] = []

    async def estimate(
        self,
        candidate: DeduplicatedObject,
        detected_object: DetectedObject,
    ) -> EstimatedDimensions:
        self.calls.append(candidate.id)
        return EstimatedDimensions(
            widthM=1.7,
            depthM=0.9,
            heightM=0.8,
        )


class DimensionEstimationTest(unittest.TestCase):
    @contextmanager
    def _test_directory(self):
        root = OUTPUTS_ROOT / f"_dimension_test_{uuid.uuid4().hex}"
        root.mkdir(parents=True, exist_ok=False)
        try:
            yield root
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def _objects_and_candidate(
        self,
        root: Path,
    ) -> tuple[list[VideoAnalysisFrame], DeduplicatedObject]:
        crop_path = root / "deduplicated" / "candidate_001" / "crop.jpg"
        annotated_path = root / "deduplicated" / "candidate_001" / "annotated.jpg"
        crop_path.parent.mkdir(parents=True)
        Image.new("RGB", (240, 140), (130, 90, 50)).save(crop_path)
        Image.new("RGB", (320, 240), (200, 200, 200)).save(annotated_path)

        frames: list[VideoAnalysisFrame] = []
        for index in range(2):
            detected = DetectedObject(
                id=f"obj_dining_table_{index + 1:03d}",
                label="dining_table",
                name="木质餐桌",
                confidence=0.9,
                bbox=[20, 30, 260, 180],
                tagPosition=[0.5, 0.45],
                cropUrl=path_to_output_url(crop_path),
                deduplicatedObjectId="candidate_001",
                deduplicatedCropUrl=path_to_output_url(crop_path),
                visualFeatures={"geometry": "rectangular tabletop with four legs"},
                generationHints={"preserve": ["wood grain", "four legs"]},
            )
            frames.append(
                VideoAnalysisFrame(
                    frameId=f"video_1_{index + 1:06d}",
                    time=float(index),
                    frameImageUrl=path_to_output_url(annotated_path),
                    objects=[detected],
                )
            )
        candidate = DeduplicatedObject(
            id="candidate_001",
            label="dining_table",
            name="木质餐桌",
            representativeFrameId=frames[0].frameId,
            representativeObjectId=frames[0].objects[0].id,
            annotatedImageUrl=path_to_output_url(annotated_path),
            cropUrl=path_to_output_url(crop_path),
            bbox=[20, 30, 260, 180],
            confidence=0.9,
            duplicateCount=2,
        )
        return frames, candidate

    def test_estimates_once_per_candidate_and_propagates_to_all_members(self) -> None:
        with self._test_directory() as root:
            frames, candidate = self._objects_and_candidate(root)
            estimator = FakeDimensionEstimator()
            estimated_count = asyncio.run(estimator.enrich_candidates(frames, [candidate]))

            self.assertEqual(estimated_count, 1)
            self.assertEqual(estimator.calls, ["candidate_001"])
            self.assertEqual(candidate.estimatedDimensions.widthM, 1.7)
            self.assertTrue(
                all(
                    frame.objects[0].estimatedDimensions == candidate.estimatedDimensions
                    for frame in frames
                )
            )

            estimated_count = asyncio.run(estimator.enrich_candidates(frames, [candidate]))
            self.assertEqual(estimated_count, 0)
            self.assertEqual(estimator.calls, ["candidate_001"])

    def test_normalizes_ranges_around_estimate(self) -> None:
        estimator = FakeDimensionEstimator()
        dimensions = estimator._normalize_estimate(
            {
                "widthM": 2,
                "depthM": 1,
                "heightM": 0.75,
                "range": {
                    "widthM": [2.4, 1.8],
                    "depthM": ["invalid", 1.2],
                    "heightM": [0.7, 0.8],
                },
                "confidence": 1.4,
                "basis": ["category"],
            }
        )

        self.assertEqual(dimensions.widthM, 1.9)
        self.assertEqual(dimensions.depthM, 0.9)
        self.assertEqual(dimensions.heightM, 0.8)
        self.assertFalse(dimensions.isMeasured)
        self.assertEqual(dimensions.source, "ark_category_prior")
        self.assertEqual(dimensions.selectionRule, "range_min_plus_0.10m_capped_at_max")


if __name__ == "__main__":
    unittest.main()
