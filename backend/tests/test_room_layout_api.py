import unittest

from fastapi.testclient import TestClient

from app.main import app


class RoomLayoutApiTests(unittest.TestCase):
    def test_geometry_only_room_layout_returns_layout(self) -> None:
        response = TestClient(app).post(
            "/api/room/room-layout",
            json={
                "enableAgents": False,
                "scene": {
                    "sceneId": "room6",
                    "unit": "meter",
                    "room": {"width": 6.0, "depth": 4.2, "height": 3.0},
                    "objects": [
                        {
                            "id": "chair_1",
                            "label": "chair",
                            "name": "测试椅子",
                            "position": [0.2, 0.45, 0.2],
                            "rotation": [0.0, 0.0, 0.0],
                            "size": [0.8, 0.9, 0.8],
                        }
                    ],
                    "openings": [],
                    "suggestions": [],
                },
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["mode"], "room")
        self.assertIsNotNone(payload["layout"])
        self.assertIn("moves", payload["layout"])
        self.assertIn("advices", payload["layout"])


if __name__ == "__main__":
    unittest.main()
