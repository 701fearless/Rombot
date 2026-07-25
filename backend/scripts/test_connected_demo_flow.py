import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app
from app.services.video_preprocess.analysis_store import read_analysis


class ConnectedDemoFlowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_pipeline_page_exposes_product_and_layout_stages(self) -> None:
        response = self.client.get("/static/pipeline-test.html")
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="productSearchButton"', response.text)
        self.assertIn('id="placementCheckButton"', response.text)
        self.assertIn('id="step-product"', response.text)
        self.assertIn('id="step-layout"', response.text)

    def test_cached_object_continues_to_mock_product_and_geometry(self) -> None:
        analysis = read_analysis("2")
        self.assertIsNotNone(analysis)

        selected_frame = None
        selected_object = None
        for frame in analysis.frames:
            detection_response = self.client.post(
                "/api/feed/detect",
                json={
                    "videoId": "2",
                    "time": frame.time,
                    "frameHash": frame.perceptualHash,
                },
            )
            self.assertEqual(detection_response.status_code, 200, detection_response.text)
            for item in detection_response.json()["objects"]:
                if item.get("prebuiltGlbUrl"):
                    selected_frame = detection_response.json()
                    selected_object = item
                    break
            if selected_object:
                break

        self.assertIsNotNone(selected_frame)
        self.assertIsNotNone(selected_object)

        asset_response = self.client.get(
            "/api/feed/prebuilt-asset",
            params={"frameId": selected_frame["frameId"], "objectId": selected_object["id"]},
        )
        self.assertEqual(asset_response.status_code, 200, asset_response.text)
        asset = asset_response.json()
        self.assertTrue(asset["glbUrl"].endswith("generated_model.glb"))

        product_response = self.client.post(
            "/api/product/mock-search",
            json={
                "objectId": selected_object["id"],
                "label": selected_object["label"],
                "name": selected_object["name"],
                "estimatedDimensions": selected_object.get("estimatedDimensions"),
            },
        )
        self.assertEqual(product_response.status_code, 200, product_response.text)
        products = product_response.json()
        self.assertTrue(products["isMock"])
        self.assertEqual(products["source"], "mock_catalog")
        self.assertEqual(len(products["matches"]), 3)

        dimensions = selected_object.get("estimatedDimensions")
        size = (
            [dimensions["widthM"], dimensions["heightM"], dimensions["depthM"]]
            if dimensions
            else [1.2, 0.8, 0.6]
        )
        placement_response = self.client.post(
            "/api/room/placement-check",
            json={
                "sceneId": "demo_living_room",
                "candidate": {
                    "id": selected_object["id"],
                    "label": selected_object["label"],
                    "name": selected_object["name"],
                    "position": [0.6, 0.0, 0.5],
                    "rotation": [0.0, 0.0, 0.0],
                    "size": size,
                },
                "enableAgents": False,
            },
        )
        self.assertEqual(placement_response.status_code, 200, placement_response.text)
        placement = placement_response.json()
        self.assertEqual(placement["mode"], "placement")
        self.assertEqual(len(placement["checks"]), 4)
        self.assertIsNotNone(placement["layout"])
        self.assertEqual(placement["layout"]["advices"], [])


if __name__ == "__main__":
    unittest.main()
