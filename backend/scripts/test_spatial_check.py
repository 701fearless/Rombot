"""手工验证基础空间可行性检测（Fit / Collision / Accessibility / Clearance）。"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.schemas import PlacementCandidate
from app.services.layout_reasoning import run_spatial_check
from app.services.room_scan.mock_scene import build_mock_scene


def _print_result(title: str, result) -> None:
    print(f"\n=== {title} ===")
    print(f"overall: {result.overallStatus}")
    for check in result.checks:
        mark = {"pass": "OK", "warn": "WARN", "fail": "FAIL"}[check.status]
        print(f"  [{mark}] {check.name}: {check.message}")
        if check.suggestion:
            print(f"         -> {check.suggestion}")
    print(f"feedback: {result.feedback}")


def main() -> None:
    scene = build_mock_scene("demo_living_room")

    # 1) 与茶几重叠 + 沙发前方空间不足
    overlapping_sofa = PlacementCandidate(
        id="candidate_sofa",
        label="sofa",
        name="沙发",
        position=[1.2, 0.0, 2.1],
        rotation=[0.0, 0.0, 0.0],
        size=[2.0, 0.9, 0.8],
    )
    _print_result("重叠沙发", run_spatial_check(overlapping_sofa, scene))

    # 2) 堵在门口
    blocking_door = PlacementCandidate(
        id="candidate_cabinet",
        label="wardrobe",
        name="衣柜",
        position=[0.6, 0.0, 0.5],
        rotation=[0.0, 0.0, 0.0],
        size=[0.6, 2.0, 0.5],
    )
    _print_result("堵门衣柜", run_spatial_check(blocking_door, scene))

    # 3) 超出房间
    oversized = PlacementCandidate(
        id="candidate_table",
        label="dining_table",
        name="餐桌",
        position=[3.8, 0.0, 1.8],
        rotation=[0.0, 0.0, 0.0],
        size=[1.6, 0.75, 0.9],
    )
    _print_result("越界餐桌", run_spatial_check(oversized, scene))

    # 4) 合理空位书桌
    ok_desk = PlacementCandidate(
        id="candidate_desk",
        label="desk",
        name="书桌",
        position=[3.5, 0.0, 2.6],
        rotation=[0.0, 0.0, 0.0],
        size=[1.2, 0.75, 0.6],
    )
    result = run_spatial_check(ok_desk, scene)
    _print_result("空位书桌", result)
    print("\nJSON sample:")
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
