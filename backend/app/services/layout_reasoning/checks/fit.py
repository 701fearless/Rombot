from __future__ import annotations

from app.schemas import CheckDetail, PlacementCandidate, RoomSize
from app.services.layout_reasoning.geometry import Aabb2, OrientedRect


def check_fit(candidate: PlacementCandidate, room: RoomSize) -> CheckDetail:
    rect = OrientedRect.from_center_size(candidate.position, candidate.size, candidate.rotation)
    room_box = Aabb2.from_room(room.width, room.depth)
    overflow = room_box.clamp_overflow(rect)
    outside = {side: value for side, value in overflow.items() if value > 1e-4}

    if not outside and candidate.size[1] <= room.height + 1e-4:
        return CheckDetail(
            ruleId="fit",
            name="空间适配",
            status="pass",
            message="家具可正常放置",
            details={"withinRoom": True, "overflow_m": overflow},
        )

    parts: list[str] = []
    suggestion_bits: list[str] = []
    side_names = {"left": "左侧", "right": "右侧", "front": "前侧", "back": "后侧"}
    for side, value in outside.items():
        cm = round(value * 100)
        parts.append(f"{side_names[side]}超出约 {cm} cm")
        suggestion_bits.append(f"向{ {'left': '右', 'right': '左', 'front': '后', 'back': '前'}[side] }移动约 {cm} cm")

    if candidate.size[1] > room.height + 1e-4:
        over_h = round((candidate.size[1] - room.height) * 100)
        parts.append(f"高度超出约 {over_h} cm")
        suggestion_bits.append("选择更矮的家具")

    return CheckDetail(
        ruleId="fit",
        name="空间适配",
        status="fail",
        message="当前摆放区域空间不足" + ("：" + "，".join(parts) if parts else ""),
        suggestion="当前摆放区域空间不足，建议调整位置或选择小尺寸家具。"
        + ((" " + "；".join(suggestion_bits) + "。") if suggestion_bits else ""),
        details={"withinRoom": False, "overflow_m": overflow, "heightOk": candidate.size[1] <= room.height},
    )
