import json
import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import SceneSnapshot
from app.services import scene_snapshot, skill_advice, user_floorplan
from app.services.scene_snapshot import load_snapshot


class SkillAdviceApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.patches = [
            patch.object(scene_snapshot, "OUTPUTS_ROOT", root / "runtime"),
            patch.object(user_floorplan, "USER_DATA_ROOT", root / "user"),
        ]
        for item in self.patches:
            item.start()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()
        self.temporary.cleanup()

    def test_save_creates_user_floorplan_from_export(self) -> None:
        snapshot = load_snapshot("room1").model_copy(deep=True)
        snapshot.objects[0].transform.position[0] = 1.75
        snapshot = SceneSnapshot.model_validate({**snapshot.model_dump(), "revision": 1})
        user_floorplan.save_user_floorplan(snapshot)

        path = user_floorplan.user_floorplan_path("room1")
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("floorplan", payload)
        self.assertEqual(payload["status"], "user_customized")
        self.assertEqual(len(payload["deduplicatedObjects"]), len(snapshot.objects))
        self.assertEqual(payload["deduplicatedObjects"][0]["transform"]["position"][0], 1.75)
        self.assertEqual(payload["userSnapshot"]["revision"], 1)

    def test_room2_snapshot_round_trip(self) -> None:
        initial_response = self.client.get("/api/room/snapshots/room2")
        self.assertEqual(initial_response.status_code, 200)
        initial = initial_response.json()
        self.assertEqual(initial["sceneId"], "room2")
        self.assertEqual(initial["revision"], 0)
        self.assertEqual(initial["room"]["whiteboxGlbUrl"], "/sample_data/floorplans/room2.glb")
        self.assertEqual(len(initial["objects"]), 9)
        self.assertTrue(all(item["geometry"]["glbUrl"] for item in initial["objects"]))

        changed = json.loads(json.dumps(initial))
        changed["objects"][0]["transform"]["position"][0] = 2.25
        saved_response = self.client.put("/api/room/snapshots/room2", json=changed)
        self.assertEqual(saved_response.status_code, 200)
        saved = saved_response.json()
        self.assertEqual(saved["revision"], 1)
        self.assertEqual(saved["objects"][0]["transform"]["position"][0], 2.25)
        self.assertEqual(self.client.get("/api/room/snapshots/room2").json(), saved)

        user_payload = user_floorplan.load_user_floorplan("room2")
        self.assertEqual(user_payload["sceneId"], "room2")
        self.assertEqual(len(user_payload["deduplicatedObjects"]), 9)

        restored = self.client.post("/api/room/snapshots/room2/reset").json()
        self.assertEqual(restored["revision"], 0)
        self.assertNotEqual(restored["objects"][0]["transform"]["position"][0], 2.25)

    def test_options_and_missing_key_response(self) -> None:
        options = self.client.get("/api/room/advice-options")
        self.assertEqual(options.status_code, 200)
        self.assertEqual({item["id"] for item in options.json()}, {"children", "pets", "fengshui", "other"})

        settings = SimpleNamespace(deepseek_api_key=None)
        with patch.object(skill_advice, "get_settings", return_value=settings):
            response = self.client.post(
                "/api/room/snapshots/room1/skill-advice",
                json={"scenarioId": "children", "profile": {"ageRange": "3-6岁", "mobilityStage": "walking"}},
            )
        self.assertEqual(response.status_code, 503)
        self.assertIn("DEEPSEEK_API_KEY", response.json()["detail"])
        payload = user_floorplan.load_user_floorplan("room1")
        self.assertEqual(payload["userRequirements"]["scenarioId"], "children")

    def test_missing_fields_are_explicit(self) -> None:
        floorplan = {"userSnapshot": {"room": {"openings": []}, "objects": [{"semantic": {"materials": []}, "source": {"type": "feed"}}]}}
        gaps = skill_advice.missing_fields(floorplan, "pets", {"species": "cat"})
        self.assertTrue(any("门窗" in item for item in gaps))
        self.assertTrue(any("行为" in item for item in gaps))
        self.assertTrue(any("实测" in item for item in gaps))
        self.assertTrue(any("具体目标" in item for item in skill_advice.missing_fields(floorplan, "other", {})))

    def test_generation_uses_skill_and_strips_embedded_glb(self) -> None:
        captured = {}

        class FakeClient:
            async def complete_json(self, *, system, user):
                captured["system"] = system
                captured["user"] = user
                return {
                    "summary": "先处理高风险，再做可逆调整。",
                    "suggestions": [{"priority": "P1", "title": "固定高柜", "reason": "存在倾倒后果", "action": "现场确认墙体后使用合适固定件", "relatedObjectIds": ["cabinet_1"]}],
                    "followUpQuestions": ["高柜是否已固定？"],
                }

        settings = SimpleNamespace(
            deepseek_api_key="test-key", deepseek_base_url="https://api.deepseek.com",
            deepseek_model="deepseek-v4-pro", skill_advice_timeout_sec=90,
        )
        floorplan = {"floorplan": {"glbBase64": "large-binary", "room": {}}, "userSnapshot": {"room": {"openings": []}, "objects": []}}
        with patch.object(skill_advice, "get_settings", return_value=settings), patch.object(skill_advice, "SpatialLLMClient", return_value=FakeClient()):
            result = asyncio.run(skill_advice.generate_skill_advice(floorplan=floorplan, scenario_id="children", profile={"ageRange": "3-6岁", "mobilityStage": "walking", "extraRequest": "增加阅读角"}))
        self.assertEqual(result["model"], "deepseek-v4-pro")
        self.assertEqual(result["suggestions"][0]["priority"], "P1")
        self.assertIn("adapt-home-for-children", captured["system"])
        self.assertIn("其他需求", captured["system"])
        self.assertIn("增加阅读角", captured["user"])
        self.assertNotIn("large-binary", captured["user"])


if __name__ == "__main__":
    unittest.main()
