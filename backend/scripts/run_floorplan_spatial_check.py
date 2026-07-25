"""Convert floorplan-AI JSON → SceneResponse and run spatial checks (provider from .env)."""

from __future__ import annotations

import asyncio
import json
import math
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Respect .env (SPATIAL_AGENT_PROVIDER=ark by default in config); do not force mock.
load_dotenv(ROOT / ".env", override=True)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.schemas import (  # noqa: E402
    PlacementCandidate,
    RoomSize,
    SceneObject,
    SceneOpening,
    SceneResponse,
    SceneSuggestion,
)
from app.services.layout_reasoning import run_spatial_check  # noqa: E402
from app.services.layout_reasoning.agents.phase1 import (  # noqa: E402
    create_llm_client,
    run_layout_module,
)
from app.services.layout_reasoning.agents.room_layout import run_room_layout  # noqa: E402

FLOORPLAN = {
    "sceneId": "floorplan_ai_001",
    "unit": "meter",
    "wallHeight": 3.0,
    "defaultWallThickness": 0.3,
    "floorPolygon": [
        [0.0, 0.0],
        [0.69, 0.0],
        [0.69, -0.73],
        [2.55, -0.73],
        [2.55, 0.0],
        [3.01, 0.0],
        [4.71, 0.0],
        [4.71, 0.65],
        [6.47, 0.65],
        [6.47, 7.05],
        [0.0, 7.05],
    ],
    "walls": [
        {"id": "wall_001", "start": [0.0, 7.05], "end": [6.47, 7.05], "thickness": 0.3, "height": 3.0},
        {"id": "wall_002", "start": [6.47, 0.65], "end": [6.47, 7.05], "thickness": 0.3, "height": 3.0},
        {"id": "wall_003", "start": [4.71, 0.65], "end": [6.47, 0.65], "thickness": 0.3, "height": 3.0},
        {"id": "wall_004", "start": [4.71, 0.0], "end": [4.71, 0.65], "thickness": 0.3, "height": 3.0},
        {"id": "wall_005", "start": [3.01, 0.0], "end": [4.71, 0.0], "thickness": 0.3, "height": 3.0},
        {"id": "wall_006", "start": [2.55, 0.0], "end": [3.01, 0.0], "thickness": 0.3, "height": 3.0},
        {"id": "wall_007", "start": [2.55, -0.73], "end": [2.55, 0.0], "thickness": 0.3, "height": 3.0},
        {"id": "wall_008", "start": [0.69, -0.73], "end": [2.55, -0.73], "thickness": 0.3, "height": 3.0},
        {"id": "wall_009", "start": [0.69, -0.73], "end": [0.69, 0.0], "thickness": 0.3, "height": 3.0},
        {"id": "wall_010", "start": [0.0, 0.0], "end": [0.69, 0.0], "thickness": 0.3, "height": 3.0},
        {"id": "wall_011", "start": [0.0, 0.0], "end": [0.0, 7.05], "thickness": 0.3, "height": 3.0},
        {"id": "wall_012", "start": [4.71, 0.65], "end": [4.71, 7.05], "thickness": 0.3, "height": 3.0},
        {"id": "wall_013", "start": [4.71, 5.97], "end": [6.47, 5.97], "thickness": 0.3, "height": 3.0},
        {"id": "wall_014", "start": [4.71, 3.85], "end": [6.47, 3.85], "thickness": 0.3, "height": 3.0},
        {"id": "wall_015", "start": [0.0, 2.15], "end": [3.01, 2.15], "thickness": 0.3, "height": 3.0},
        {"id": "wall_016", "start": [3.01, 2.15], "end": [4.71, 2.15], "thickness": 0.3, "height": 3.0},
        {"id": "wall_017", "start": [3.01, 0.0], "end": [3.01, 2.15], "thickness": 0.3, "height": 3.0},
    ],
    "wallFixtures": [
        {
            "id": "door_entry",
            "type": "door",
            "wallId": "wall_001",
            "offset": 3.5,
            "width": 0.9,
            "bottom": 0.0,
            "height": 2.1,
            "style": "minimal_panel_door",
            "side": "front",
        },
        {
            "id": "door_toilet",
            "type": "door",
            "wallId": "wall_013",
            "offset": 0.88,
            "width": 0.8,
            "bottom": 0.0,
            "height": 2.1,
            "style": "minimal_panel_door",
            "side": "front",
        },
        {
            "id": "door_kitchen",
            "type": "door",
            "wallId": "wall_012",
            "offset": 3.0,
            "width": 0.9,
            "bottom": 0.0,
            "height": 2.1,
            "style": "minimal_panel_door",
            "side": "front",
        },
        {
            "id": "door_balcony",
            "type": "door",
            "wallId": "wall_016",
            "offset": 0.85,
            "width": 1.0,
            "bottom": 0.0,
            "height": 2.1,
            "style": "minimal_panel_door",
            "side": "front",
        },
        {
            "id": "door_bedroom",
            "type": "door",
            "wallId": "wall_017",
            "offset": 1.5,
            "width": 0.9,
            "bottom": 0.0,
            "height": 2.1,
            "style": "minimal_panel_door",
            "side": "front",
        },
        {
            "id": "window_toilet",
            "type": "window",
            "wallId": "wall_002",
            "offset": 4.7,
            "width": 0.8,
            "bottom": 0.9,
            "height": 1.2,
            "style": "simple_framed_window",
            "side": "front",
        },
        {
            "id": "window_kitchen",
            "type": "window",
            "wallId": "wall_003",
            "offset": 0.88,
            "width": 1.5,
            "bottom": 0.9,
            "height": 1.2,
            "style": "simple_framed_window",
            "side": "front",
        },
        {
            "id": "window_balcony",
            "type": "window",
            "wallId": "wall_005",
            "offset": 0.85,
            "width": 1.5,
            "bottom": 0.9,
            "height": 1.2,
            "style": "simple_framed_window",
            "side": "front",
        },
        {
            "id": "window_bay",
            "type": "window",
            "wallId": "wall_008",
            "offset": 0.93,
            "width": 1.8,
            "bottom": 0.9,
            "height": 1.2,
            "style": "simple_framed_window",
            "side": "front",
        },
    ],
    "warnings": [
        "Dimensions converted from millimeter labels; minor rounding applied; "
        "bedroom door placed on east partition wall as no clear door symbol was visible."
    ],
}

FIXTURE_NAMES = {
    "door_entry": "入户门",
    "door_toilet": "卫生间门",
    "door_kitchen": "厨房门",
    "door_balcony": "阳台门",
    "door_bedroom": "卧室门",
    "window_toilet": "卫生间窗",
    "window_kitchen": "厨房窗",
    "window_balcony": "阳台窗",
    "window_bay": "飘窗",
}


def _bbox(polygon: list[list[float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return min(xs), min(ys), max(xs), max(ys)


def _fixture_to_opening(
    fixture: dict,
    walls_by_id: dict[str, dict],
    origin_x: float,
    origin_y: float,
    default_thickness: float,
) -> SceneOpening:
    wall = walls_by_id[fixture["wallId"]]
    sx, sy = float(wall["start"][0]), float(wall["start"][1])
    ex, ey = float(wall["end"][0]), float(wall["end"][1])
    dx, dy = ex - sx, ey - sy
    length = math.hypot(dx, dy)
    if length < 1e-9:
        raise ValueError(f"wall {fixture['wallId']} has zero length")
    ux, uy = dx / length, dy / length
    offset = float(fixture["offset"])
    width = float(fixture["width"])
    bottom = float(fixture["bottom"])
    height = float(fixture["height"])
    mid = offset + width * 0.5
    cx = sx + ux * mid
    cy = sy + uy * mid
    # Scene yaw: local +X along wall tangent in XZ plane.
    yaw = math.atan2(-uy, ux)
    thickness = float(wall.get("thickness") or default_thickness)
    opening_depth = min(0.12, thickness)
    ftype = str(fixture["type"]).lower()
    clearance = 0.9 if ftype == "door" else 0.3
    fid = str(fixture["id"])
    return SceneOpening(
        id=fid,
        type=ftype,
        name=FIXTURE_NAMES.get(fid, fid),
        position=[round(cx - origin_x, 4), round(bottom + height * 0.5, 4), round(cy - origin_y, 4)],
        rotation=[0.0, round(yaw, 6), 0.0],
        size=[width, height, opening_depth],
        clearanceDepth=clearance,
    )


def floorplan_to_scene(fp: dict, *, with_demo_furniture: bool = False) -> SceneResponse:
    polygon = fp["floorPolygon"]
    min_x, min_y, max_x, max_y = _bbox(polygon)
    width = max_x - min_x
    depth = max_y - min_y
    height = float(fp.get("wallHeight") or 2.8)
    default_thickness = float(fp.get("defaultWallThickness") or 0.2)
    walls_by_id = {w["id"]: w for w in fp["walls"]}
    openings = [
        _fixture_to_opening(f, walls_by_id, min_x, min_y, default_thickness)
        for f in fp.get("wallFixtures") or []
    ]
    suggestions = [
        SceneSuggestion(type="warning", text=w) for w in (fp.get("warnings") or [])
    ]
    suggestions.append(
        SceneSuggestion(
            type="adapter",
            text=(
                "户型为多边形+隔墙；SceneResponse 仅用包围盒矩形房间近似。"
                f"原点平移=({min_x},{min_y})，房间约 {width:.2f}×{depth:.2f}×{height:.2f}m。"
            ),
        )
    )

    objects: list[SceneObject] = []
    if with_demo_furniture:
        # 客厅大致在西侧中部（入户门南侧）：floorplan (2.2, 4.5) → 平移后
        living_x = 2.2 - min_x
        living_z = 4.5 - min_y
        objects = [
            SceneObject(
                id="demo_sofa",
                label="sofa",
                name="沙发",
                position=[living_x, 0.0, living_z],
                rotation=[0.0, 0.0, 0.0],
                size=[2.0, 0.9, 0.85],
                glbUrl=None,
            ),
            SceneObject(
                id="demo_coffee_table",
                label="coffee_table",
                name="茶几",
                position=[living_x, 0.0, living_z - 1.0],
                rotation=[0.0, 0.0, 0.0],
                size=[1.0, 0.45, 0.5],
                glbUrl=None,
            ),
        ]

    return SceneResponse(
        sceneId=str(fp.get("sceneId") or "floorplan_ai"),
        unit=str(fp.get("unit") or "meter"),
        room=RoomSize(width=round(width, 4), depth=round(depth, 4), height=height),
        objects=objects,
        openings=openings,
        suggestions=suggestions,
    )


def _print_checks(checks) -> None:
    for c in checks:
        print(f"  - [{c.status}] {c.name}: {c.message}")
        if c.suggestion:
            print(f"    建议: {c.suggestion}")


async def main() -> None:
    out_scene = ROOT / "sample_data" / "scenes" / "floorplan_ai_001_scene.json"
    out_result = ROOT / "outputs" / "floorplan_ai_001_spatial_check.json"
    out_result.parent.mkdir(parents=True, exist_ok=True)

    # Faithful conversion: openings only (no furniture)
    scene_bare = floorplan_to_scene(FLOORPLAN, with_demo_furniture=False)
    out_scene.write_text(
        json.dumps(scene_bare.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved scene: {out_scene}")
    print(
        f"room={scene_bare.room.model_dump()} openings={len(scene_bare.openings)} "
        f"objects={len(scene_bare.objects)}"
    )
    print(f"SPATIAL_AGENT_PROVIDER={os.environ.get('SPATIAL_AGENT_PROVIDER')}")
    print(f"ARK_API_KEY set={bool(os.environ.get('ARK_API_KEY'))}")
    print(f"ARK_BASE_URL={os.environ.get('ARK_BASE_URL')}")
    print(f"ARK_TEXT_MODEL={os.environ.get('ARK_TEXT_MODEL')}")

    llm = create_llm_client()
    llm_trace: dict = {"ok": 0, "fail": 0, "errors": []}
    _orig_complete = llm.complete_json

    async def _tracked_complete_json(**kwargs):
        try:
            result = await _orig_complete(**kwargs)
            llm_trace["ok"] += 1
            print(f"[LLM] complete_json OK (ok={llm_trace['ok']})")
            return result
        except Exception as exc:
            llm_trace["fail"] += 1
            llm_trace["errors"].append(f"{type(exc).__name__}: {exc}")
            print(f"[LLM] complete_json FAIL: {type(exc).__name__}: {exc}")
            raise

    llm.complete_json = _tracked_complete_json  # type: ignore[method-assign]
    print(f"llm.provider={llm.provider} llm.is_live={llm.is_live}")

    # Demo sofa candidate in living area for placement-check
    # floorplan (2.2, 4.5), origin y=-0.73 → z=5.23
    candidate = PlacementCandidate(
        id="candidate_sofa",
        label="sofa",
        name="沙发",
        position=[2.2 - 0.0, 0.0, 4.5 - (-0.73)],
        rotation=[0.0, 0.0, 0.0],
        size=[2.0, 0.9, 0.85],
    )

    print("\n===== placement-check（客厅 demo 沙发）=====")
    geo = run_spatial_check(candidate, scene_bare)
    layout = await run_layout_module(
        candidate=candidate, scene=scene_bare, checks=geo.checks, llm=llm
    )
    print("overallStatus:", geo.overallStatus)
    print("feedback:", geo.feedback)
    print("layout.summary:", layout.summary)
    _print_checks(geo.checks)
    print("moves:")
    for m in layout.moves:
        print(
            f"  - {m.name}: {m.fromPosition} → {m.toPosition} "
            f"({m.reason}) [{m.source}]"
        )
    print("advices:")
    for a in layout.advices:
        print(f"  - [{a.priority}] {a.title}: {a.problem} → {a.suggestion}")

    print("\n===== room-layout（含客厅 demo 家具）=====")
    scene_demo = floorplan_to_scene(FLOORPLAN, with_demo_furniture=True)
    room = await run_room_layout(scene=scene_demo, enable_agents=True, llm=llm)
    print("overallStatus:", room.overallStatus)
    print("feedback:", room.feedback)
    for b in room.objectChecks:
        print(f"  object {b.name}: {b.overallStatus}")
        for c in b.checks:
            if c.status != "pass":
                print(f"    - [{c.status}] {c.name}: {c.message}")
    if room.layout:
        print("layout.summary:", room.layout.summary)
        for m in room.layout.moves:
            print(
                f"  move {m.name}: {m.fromPosition} → {m.toPosition} ({m.reason})"
            )
        for a in room.layout.advices:
            print(f"  advice [{a.priority}] {a.title}: {a.suggestion}")

    llm_used = llm_trace["ok"] > 0
    fallback_local = llm.is_live and llm_trace["fail"] > 0 and llm_trace["ok"] < 2
    payload = {
        "provider": llm.provider,
        "llmLive": llm.is_live,
        "llmUsed": llm_used,
        "llmCalls": llm_trace,
        "fallbackToLocal": fallback_local,
        "scenePath": str(out_scene),
        "conversionNotes": {
            "roomFrom": "floorPolygon AABB (origin-shifted)",
            "openingsFrom": "wallFixtures on walls",
            "polygonWalls": "not modeled; interior partitions ignored by rectangular room model",
        },
        "placementCheck": {
            "overallStatus": geo.overallStatus,
            "feedback": geo.feedback,
            "checks": [c.model_dump() for c in geo.checks],
            "candidate": candidate.model_dump(),
            "layout": layout.model_dump() if layout else None,
        },
        "roomLayout": {
            "overallStatus": room.overallStatus,
            "feedback": room.feedback,
            "objectChecks": [b.model_dump() for b in room.objectChecks],
            "layout": room.layout.model_dump() if room.layout else None,
            "demoFurnitureNote": "demo sofa + coffee table injected only for room-layout",
        },
    }
    out_result.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nllmUsed={llm_used} llmCalls={llm_trace} fallbackToLocal={fallback_local}")
    print(f"Saved results: {out_result}")


if __name__ == "__main__":
    asyncio.run(main())
