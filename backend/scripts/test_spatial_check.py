"""验证单家具 placement-check 与全屋 room-layout 两套模式。"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("SPATIAL_AGENT_PROVIDER", "mock")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.schemas import PlacementCandidate
from app.services.layout_reasoning import (
    run_layout_module,
    run_room_layout,
    run_scenario_advice,
    run_spatial_check,
)
from app.services.room_scan.mock_scene import build_mock_scene


async def main() -> None:
    scene = build_mock_scene("demo_living_room")

    print("===== 模式一：单家具摆放 =====")
    candidate = PlacementCandidate(
        id="candidate_cabinet",
        label="wardrobe",
        name="衣柜",
        position=[0.6, 0.0, 0.5],
        rotation=[0.0, 0.0, 0.0],
        size=[0.6, 2.0, 0.5],
    )
    geo = run_spatial_check(candidate, scene)
    layout = await run_layout_module(candidate=candidate, scene=scene, checks=geo.checks)
    print("overall:", geo.overallStatus)
    print("moves:", len(layout.moves), layout.moves[0].reason if layout.moves else None)
    print("advices:", [a.title for a in layout.advices])
    scen = await run_scenario_advice(
        scenarios=["elder", "pet"],
        mode="placement",
        candidate=candidate,
        scene=scene,
        layout=layout,
        geometry_checks=geo.checks,
    )
    print("scenario:", scen.mode, list(scen.advicesByScenario.keys()))

    print("\n===== 模式二：全屋布局 =====")
    room = await run_room_layout(scene=scene, enable_agents=True)
    print("overall:", room.overallStatus)
    print("objectChecks:", len(room.objectChecks))
    print("moves:", len(room.layout.moves) if room.layout else 0)
    print("advices:", [a.title for a in (room.layout.advices if room.layout else [])])
    scen2 = await run_scenario_advice(
        scenarios=["fengshui", "elder"],
        mode="room",
        candidate=None,
        scene=scene,
        layout=room.layout,
    )
    print("scenario:", scen2.mode, scen2.summary)
    print(json.dumps({k: [i.title for i in v] for k, v in scen2.advicesByScenario.items()}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
