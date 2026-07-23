from __future__ import annotations

from app.schemas import CheckDetail, PlacementCandidate, RoomSize, SceneObject
from app.services.layout_reasoning.geometry import Aabb2, OrientedRect, free_distance_along_side
from app.services.layout_reasoning.rules_loader import (
    clearance_sides,
    furniture_rule,
    is_solid_furniture,
)


SIDE_LABELS = {
    "front": "前方",
    "back": "后方",
    "left": "左侧",
    "right": "右侧",
}


def check_clearance(
    candidate: PlacementCandidate,
    room: RoomSize,
    objects: list[SceneObject],
) -> CheckDetail:
    required = clearance_sides(candidate.label)
    if not required:
        return CheckDetail(
            ruleId="clearance",
            name="活动空间",
            status="pass",
            message="该家具类型暂无活动空间阈值，跳过检测",
            details={"sides": [], "skipped": True},
        )

    furniture = OrientedRect.from_center_size(candidate.position, candidate.size, candidate.rotation)
    room_box = Aabb2.from_room(room.width, room.depth)
    blockers = [
        OrientedRect.from_center_size(obj.position, obj.size, obj.rotation)
        for obj in objects
        if obj.id != candidate.id and is_solid_furniture(obj.label)
    ]

    side_results: list[dict] = []
    shortages: list[dict] = []

    for side, need in required.items():
        available = free_distance_along_side(furniture, side, blockers, room_box, max_probe=max(need, 1.0))
        ok = available + 1e-4 >= need
        item = {
            "side": side,
            "required_m": need,
            "available_m": available,
            "ok": ok,
        }
        side_results.append(item)
        if not ok:
            shortages.append(item)

    rule = furniture_rule(candidate.label) or {}
    hint = str(rule.get("hint") or "活动空间")

    if not shortages:
        return CheckDetail(
            ruleId="clearance",
            name="活动空间",
            status="pass",
            message=f"{hint}充足",
            details={"sides": side_results},
        )

    messages: list[str] = []
    suggestions: list[str] = []
    for item in shortages:
        side = item["side"]
        available_cm = round(item["available_m"] * 100)
        required_cm = round(item["required_m"] * 100)
        deficit_cm = max(1, required_cm - available_cm)
        messages.append(f"{SIDE_LABELS[side]}活动空间不足（{available_cm} cm，需 ≥ {required_cm} cm）")
        move_dir = {"front": "后", "back": "前", "left": "右", "right": "左"}[side]
        suggestions.append(f"建议向{move_dir}移动约 {deficit_cm} cm")

    status = "warn"
    return CheckDetail(
        ruleId="clearance",
        name="活动空间",
        status=status,
        message="；".join(messages),
        suggestion=f"{candidate.name}{hint}不足，" + "，".join(suggestions) + "。",
        details={"sides": side_results, "shortages": shortages},
    )
