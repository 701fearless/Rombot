from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.services.floorplan_whitebox.schemas import FloorplanWhiteboxScene


FLOORPLAN_SYSTEM_PROMPT = """Return only compact valid JSON. Parse the floorplan as an architectural plan for simple 3D whitebox modeling. Wall height is always 3.0m. Wall thickness is always 0.1m. Every physical wall run is an independent segment. Door/window fixtures are decorative 3D assemblies mounted in the wall plane; they must pass through the full wall thickness and be visible from both wall faces."""


FLOORPLAN_USER_PROMPT = """Output one compact JSON object:

{
  "sceneId": "floorplan_ai_001",
  "unit": "meter",
  "wallHeight": 3.0,
  "defaultWallThickness": 0.1,
  "floorPolygon": [[0.0, 0.0], [6.0, 0.0], [6.0, 4.0], [0.0, 4.0]],
  "walls": [
    {
      "id": "wall_001",
      "start": [0.0, 0.0],
      "end": [6.0, 0.0],
      "thickness": 0.1,
      "height": 3.0
    }
  ],
  "wallFixtures": [
    {
      "id": "door_001",
      "type": "door",
      "wallId": "wall_001",
      "offset": 1.2,
      "width": 0.9,
      "bottom": 0.0,
      "height": 2.1,
      "style": "swing_panel_door",
      "side": "front"
    },
    {
      "id": "window_001",
      "type": "window",
      "wallId": "wall_002",
      "offset": 2.0,
      "width": 1.5,
      "bottom": 0.9,
      "height": 1.2,
      "style": "simple_framed_window",
      "side": "front"
    }
  ],
  "warnings": []
}

Rules:
- Estimate dimensions from printed dimension labels first; labels are usually millimeters, convert to meters.
- Use a consistent top-down coordinate system in meters. Prefer origin at the lower-left outermost footprint; x grows right/east, y grows up/north. Avoid negative coordinates when a shifted origin can express the footprint.
- Build the outer footprint from real wall bands and filled room edges only. Ignore dimension leader lines, compass marks, room-name text, area text, tile texture seams, furniture, and decorative textures.
- Include only structural outer walls and major interior partition walls. Do not create walls from door swing arcs, window frame lines, labels, or decorative floor boundaries.
- A wall segment must represent one visible continuous physical wall run between corners, T-junctions, openings, or material breaks. Split walls at real corners and T-junctions. Do not extend a local partition across an open circulation area unless a wall is visibly continuous there.
- Preserve room topology over cosmetic symmetry. Rooms, corridors, balconies, alcoves, and open living areas must stay connected exactly as shown by door openings and open circulation.
- Use room labels and area text only as semantic anchors. They may help identify room purpose, but they must not create walls or fixtures by themselves.
- Model stepped footprints, recesses, balconies, alcoves, shafts, and bay-window projections when they are visible in the structural outline. Do not simplify a non-rectangular footprint into a rectangle.
- Identify doors only from clear door symbols. Common symbols: a swing/rotating hinged door is shown by a door leaf plus an opening arc; a sliding door is shown by parallel or overlapping door rails/panels in the wall opening. Place each door on the wall that contains the drawn door opening, not on an adjacent room divider. If a door is unclear, omit it and add a warning instead of guessing.
- Use door styles to preserve the symbol type: `swing_panel_door` for arc-based hinged/rotating doors, `sliding_glass_door` for sliding doors or balcony-style sliding panels, and `minimal_panel_door` only when the drawing clearly has a door but the type is uncertain.
- Entry doors are usually on an exterior wall and open inward. Interior doors connect adjacent rooms through a shared partition. The door side and wall assignment must follow the drawn opening, not the nearest room label.
- Identify windows only from thin parallel frame lines embedded in an exterior wall. Do not infer windows from dimension ticks or room labels. Place each window on the exact exterior wall where the frame is drawn.
- Door/window fixtures are not holes only: they are visible modeled components. Swing/rotating doors need a hinged slab/panel, frame, jambs on both wall faces, and handle. Sliding doors need overlapping panels, top/bottom tracks, side jambs, and pulls. Windows need frame, glass, sill, and trim on both wall faces.
- Avoid clipping/intersections: every fixture width plus trim must fit inside its wall segment and must not overlap a corner, T-junction, another fixture, or an adjacent perpendicular wall.
- Do not attach a fixture to a very short wall segment unless the fixture width is reduced to fit with at least 0.15m clearance from both ends.
- Fixture offset is the fixture center along the wall, in meters from wall.start.
- Keep fixture offset between half fixture width plus 0.15m and wall length minus half fixture width minus 0.15m whenever possible.
- Doors and windows must align with the wall centerline and pass through both wall faces.
- Doors: bottom 0, height 2.1, width 0.8-1.0. Use narrower width only when the drawn door is small.
- Windows: bottom 0.9, height 1.2, width 0.6-1.8. Small utility-room windows may be narrower than main-room windows.
- After drafting JSON, mentally verify: closed outer footprint, no partition crosses an open room, no missing required room separator, no fixture floats away from its wall, no fixture exceeds wall length, no door/window assigned to the wrong adjacent wall.
- Keep ids ASCII. Keep warnings short and specific.
"""


@dataclass(frozen=True)
class FloorplanAiParseResult:
    scene: FloorplanWhiteboxScene
    raw_text: str
    parsed_json: dict[str, Any]
    warnings: list[str]


class ArkFloorplanParser:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def parse(self, image_data_url: str) -> FloorplanAiParseResult:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": FLOORPLAN_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                        {"type": "text", "text": FLOORPLAN_USER_PROMPT},
                    ],
                },
            ],
            "temperature": 0,
            "max_tokens": 2600,
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        raw_text = self._extract_text(data)
        parsed = self._parse_json(raw_text)
        normalized = self._normalize_payload(parsed)
        scene = FloorplanWhiteboxScene.model_validate(normalized)
        scene = self._force_modeling_defaults(scene)
        warnings = [str(item) for item in parsed.get("warnings", []) if str(item).strip()]
        return FloorplanAiParseResult(scene=scene, raw_text=raw_text, parsed_json=parsed, warnings=warnings)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _extract_text(self, data: dict[str, Any]) -> str:
        if "choices" in data:
            message = data["choices"][0].get("message", {})
            content = message.get("content", "")
            if isinstance(content, list):
                return "".join(str(item.get("text", "")) for item in content if isinstance(item, dict))
            return str(content)
        return json.dumps(data, ensure_ascii=False)

    def _parse_json(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, flags=re.S)
            if not match:
                raise ValueError("AI response did not contain a JSON object")
            parsed = json.loads(match.group(0))
        if not isinstance(parsed, dict):
            raise ValueError("AI response JSON must be an object")
        return parsed

    def _normalize_payload(self, parsed: dict[str, Any]) -> dict[str, Any]:
        payload = parsed.get("scene") or parsed.get("normalizedScene") or parsed
        if not isinstance(payload, dict):
            raise ValueError("AI response scene payload must be an object")
        payload = dict(payload)
        payload.setdefault("sceneId", "floorplan_ai_scene")
        payload["unit"] = "meter"
        payload["wallHeight"] = 3.0
        payload["defaultWallThickness"] = 0.1
        payload.setdefault("wallFixtures", [])
        return payload

    def _force_modeling_defaults(self, scene: FloorplanWhiteboxScene) -> FloorplanWhiteboxScene:
        data = scene.model_dump()
        data["wallHeight"] = 3.0
        data["defaultWallThickness"] = 0.1
        for wall in data["walls"]:
            wall["thickness"] = 0.1
            wall["height"] = 3.0
        return FloorplanWhiteboxScene.model_validate(data)
