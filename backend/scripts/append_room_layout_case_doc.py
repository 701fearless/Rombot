"""Append a whole-room layout case section into the modular cases doc."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)
# For doc append speed, prefer mock unless LIVE=1
if os.getenv("LIVE", "0") != "1":
    os.environ["SPATIAL_AGENT_PROVIDER"] = "mock"

from app.config import get_settings
from app.services.layout_reasoning import run_room_layout, run_scenario_advice
from app.services.layout_reasoning.agents.phase1 import create_llm_client

get_settings.cache_clear()


async def main() -> None:
    settings = get_settings()
    client = create_llm_client()
    rich = json.loads(
        (ROOT / "sample_data/scenes/rich_family_living_dining_spatial_check.json").read_text(
            encoding="utf-8"
        )
    )
    from app.schemas import SceneResponse

    scene = SceneResponse.model_validate(rich["scene"])
    fence = chr(96) * 3

    t0 = time.perf_counter()
    room = await run_room_layout(scene=scene, llm=client, enable_agents=True)
    phase1 = round(time.perf_counter() - t0, 3)
    t1 = time.perf_counter()
    scen = await run_scenario_advice(
        scenarios=["elder", "fengshui"],
        mode="room",
        candidate=None,
        scene=scene,
        layout=room.layout,
        llm=client,
    )
    phase2 = round(time.perf_counter() - t1, 3)

    lines = [
        "",
        "## 模式说明（两套 API）",
        "",
        "- 单家具摆放：`POST /api/room/placement-check`（旧 `/spatial-check` 兼容）",
        "- 全屋布局：`POST /api/room/room-layout`",
        "- 场景深化：`POST /api/room/scenario-advice`（`mode=placement|room`）",
        "",
        f"文档追加全屋案例时间：{datetime.now().isoformat(timespec='seconds')}；provider=`{settings.spatial_agent_provider}`；live=`{client.is_live}`",
        "",
        "## 案例（全屋模式）：rich_family_living_dining",
        "",
        "### 耗时",
        "",
        f"- Phase1 room-layout：**{phase1}s**",
        f"- Phase2 scenario-advice：**{phase2}s**",
        f"- 合计：**{round(phase1 + phase2, 3)}s**",
        "",
        "### 输入（`POST /api/room/room-layout`）",
        "",
        f"{fence}json",
        json.dumps(
            {
                "enableAgents": True,
                "scene": {
                    "sceneId": scene.sceneId,
                    "room": scene.room.model_dump(),
                    "objectCount": len(scene.objects),
                    "openingCount": len(scene.openings),
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        fence,
        "",
        "### 输出摘要",
        "",
        f"- mode：`{room.mode}`",
        f"- overallStatus：`{room.overallStatus}`",
        f"- feedback：{room.feedback}",
        f"- layout.summary：{(room.layout.summary if room.layout else '')}",
        f"- objectChecks：{len(room.objectChecks)} 件",
        f"- moves：{len(room.layout.moves) if room.layout else 0}",
        "",
        "### objectChecks（有问题的家具）",
        "",
        f"{fence}json",
        json.dumps(
            [
                {
                    "objectId": b.objectId,
                    "name": b.name,
                    "overallStatus": b.overallStatus,
                    "issues": [
                        {"ruleId": c.ruleId, "status": c.status, "message": c.message}
                        for c in b.checks
                        if c.status != "pass"
                    ],
                }
                for b in room.objectChecks
                if b.overallStatus != "pass"
            ],
            ensure_ascii=False,
            indent=2,
        ),
        fence,
        "",
        "### layout.moves",
        "",
        f"{fence}json",
        json.dumps([m.model_dump() for m in (room.layout.moves if room.layout else [])], ensure_ascii=False, indent=2),
        fence,
        "",
        "### layout.advices",
        "",
        f"{fence}json",
        json.dumps([a.model_dump() for a in (room.layout.advices if room.layout else [])], ensure_ascii=False, indent=2),
        fence,
        "",
        "### 场景建议（mode=room, elder+fengshui）",
        "",
        f"- summary：{scen.summary}",
        "",
        f"{fence}json",
        json.dumps({k: [i.model_dump() for i in v] for k, v in scen.advicesByScenario.items()}, ensure_ascii=False, indent=2),
        fence,
        "",
    ]

    out = ROOT / "docs" / "spatial_modular_scenario_cases.md"
    existing = out.read_text(encoding="utf-8") if out.exists() else "# 模块化布局 + 场景化建议 案例效果\n"
    # Insert mode section after title block if not present
    if "## 模式说明（两套 API）" not in existing:
        parts = existing.split("\n## 可选场景", 1)
        if len(parts) == 2:
            existing = parts[0] + "\n".join(lines[:8]) + "\n## 可选场景" + parts[1]
        existing = existing.rstrip() + "\n" + "\n".join(lines[8:]) + "\n"
    else:
        existing = existing.rstrip() + "\n" + "\n".join(lines[8:]) + "\n"
    out.write_text(existing, encoding="utf-8")
    print("UPDATED", out, "phase1", phase1, "phase2", phase2)


if __name__ == "__main__":
    asyncio.run(main())
