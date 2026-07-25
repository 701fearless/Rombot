"""Generate modular layout + scenario advice case docs (Chinese)."""

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

# Prefer project .env; do not force mock.
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

from app.config import get_settings
from app.schemas import SpatialCheckRequest
from app.services.layout_reasoning import (
    get_scenario_options,
    run_layout_module,
    run_scenario_advice,
    run_spatial_check,
)
from app.services.layout_reasoning.agents.phase1 import create_llm_client

get_settings.cache_clear()


CASES = [
    {
        "id": "case_bookshelf_balcony",
        "title": "案例1：落地书架堵住阳台门",
        "scenarios": ["elder", "pet", "fengshui"],
    },
    {
        "id": "case_sofa_overlap",
        "title": "案例2：新沙发压到茶几区",
        "candidate": {
            "id": "candidate_sofa_new",
            "label": "sofa",
            "name": "新沙发",
            "position": [2.1, 0.0, 2.9],
            "rotation": [0.0, 0.0, 0.0],
            "size": [2.2, 0.9, 0.9],
        },
        "scenarios": ["infant", "elder"],
    },
    {
        "id": "case_wardrobe_entry",
        "title": "案例3：衣柜靠近入户门",
        "candidate": {
            "id": "candidate_wardrobe",
            "label": "wardrobe",
            "name": "衣柜",
            "position": [0.55, 0.0, 0.55],
            "rotation": [0.0, 0.0, 0.0],
            "size": [1.0, 2.2, 0.55],
        },
        "scenarios": ["fengshui", "pet", "elder"],
    },
]


def _scene_input_summary(scene: dict) -> dict:
    return {
        "sceneId": scene.get("sceneId"),
        "unit": scene.get("unit"),
        "room": scene.get("room"),
        "objectCount": len(scene.get("objects") or []),
        "objects": [
            {
                "id": o.get("id"),
                "name": o.get("name"),
                "label": o.get("label"),
                "position": o.get("position"),
                "size": o.get("size"),
            }
            for o in (scene.get("objects") or [])
        ],
        "openings": scene.get("openings") or [],
    }


async def main() -> None:
    settings = get_settings()
    client = create_llm_client()
    rich = json.loads(
        (ROOT / "sample_data/scenes/rich_family_living_dining_spatial_check.json").read_text(
            encoding="utf-8"
        )
    )
    fence = chr(96) * 3
    lines: list[str] = []
    a = lines.append
    a("# 模块化布局 + 场景化建议 案例效果")
    a("")
    a(f"- 生成时间：{datetime.now().isoformat(timespec='seconds')}")
    a(f"- Provider：`{settings.spatial_agent_provider}`")
    a(f"- Model：`{settings.ark_text_model}`")
    a(f"- Base URL：`{settings.ark_base_url}`")
    a(f"- LLM live：`{client.is_live}`")
    a("- Phase1：`layout.moves` + `layout.advices` + `scenarioOptions`")
    a("- Phase2：`/api/room/scenario-advice` 按场景返回修改建议")
    a("")
    a("## 可选场景")
    a("")
    for opt in get_scenario_options():
        a(f"- `{opt.id}` {opt.name}：{opt.description}")
    a("")

    for case in CASES:
        payload = {
            "enableAgents": True,
            "candidate": case.get("candidate") or rich["candidate"],
            "scene": rich["scene"],
            "userProfile": rich["userProfile"],
        }
        req = SpatialCheckRequest.model_validate(payload)

        t0 = time.perf_counter()
        t1 = time.perf_counter()
        geo = run_spatial_check(req.candidate, req.scene)
        layout = await run_layout_module(
            candidate=req.candidate,
            scene=req.scene,
            checks=geo.checks,
            llm=client,
        )
        phase1_sec = round(time.perf_counter() - t1, 3)

        phase2_body = {
            "scenarios": case["scenarios"],
            "candidate": req.candidate.model_dump(),
            "scene": rich["scene"],
            "layout": layout.model_dump(),
            "geometryChecks": [c.model_dump() for c in geo.checks],
            "userProfile": req.userProfile.model_dump() if req.userProfile else None,
        }
        t2 = time.perf_counter()
        scen = await run_scenario_advice(
            scenarios=case["scenarios"],
            candidate=req.candidate,
            scene=req.scene,
            layout=layout,
            geometry_checks=geo.checks,
            user_profile=req.userProfile,
            llm=client,
        )
        phase2_sec = round(time.perf_counter() - t2, 3)
        total_sec = round(time.perf_counter() - t0, 3)

        phase1_input = {
            "enableAgents": True,
            "candidate": req.candidate.model_dump(),
            "userProfile": req.userProfile.model_dump() if req.userProfile else None,
            "scene": _scene_input_summary(rich["scene"]),
        }

        a(f"## {case['title']}")
        a("")
        a("### 耗时")
        a("")
        a(f"- Phase1（几何 + 布局模块）：**{phase1_sec}s**")
        a(f"- Phase2（场景建议）：**{phase2_sec}s**")
        a(f"- 合计：**{total_sec}s**")
        a("")
        a("### 输入（Phase1 `POST /api/room/spatial-check`）")
        a("")
        a(f"{fence}json")
        a(json.dumps(phase1_input, ensure_ascii=False, indent=2))
        a(fence)
        a("")
        a("### 输入（Phase2 `POST /api/room/scenario-advice`）")
        a("")
        a(f"{fence}json")
        a(
            json.dumps(
                {
                    "scenarios": phase2_body["scenarios"],
                    "candidate": phase2_body["candidate"],
                    "userProfile": phase2_body["userProfile"],
                    "geometryChecks": phase2_body["geometryChecks"],
                    "layout": phase2_body["layout"],
                    "scene": _scene_input_summary(rich["scene"]),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        a(fence)
        a("")
        a("### 输出摘要")
        a("")
        a(f"- 几何 overallStatus：`{geo.overallStatus}`")
        a(f"- 布局 summary：{layout.summary}")
        a(f"- 场景 summary：{scen.summary}")
        a("")
        a("### 模块A：家具移动后的位置 `layout.moves`")
        a(f"{fence}json")
        a(json.dumps([m.model_dump() for m in layout.moves], ensure_ascii=False, indent=2))
        a(fence)
        a("")
        a("### 模块B：布局优化建议 `layout.advices`（中文）")
        a(f"{fence}json")
        a(json.dumps([x.model_dump() for x in layout.advices], ensure_ascii=False, indent=2))
        a(fence)
        a("")
        a("### 场景选择后的修改建议")
        a(f"- 已选场景：{', '.join(scen.selectedScenarios)}")
        a("")
        a(f"{fence}json")
        a(
            json.dumps(
                {k: [i.model_dump() for i in v] for k, v in scen.advicesByScenario.items()},
                ensure_ascii=False,
                indent=2,
            )
        )
        a(fence)
        a("")
        a("---")
        a("")
        print(
            f"DONE {case['id']} phase1={phase1_sec}s phase2={phase2_sec}s total={total_sec}s",
            flush=True,
        )

    out = ROOT / "docs" / "spatial_modular_scenario_cases.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print("WROTE", out, "live=", client.is_live)


if __name__ == "__main__":
    asyncio.run(main())
