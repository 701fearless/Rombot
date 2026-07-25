from __future__ import annotations

from app.schemas import CheckDetail, PlacementCandidate, RoomSize, SceneOpening
from app.services.layout_reasoning.geometry import OrientedRect, Vec2
from app.services.layout_reasoning.rules_loader import accessibility_defaults


def _opening_keepout(opening: SceneOpening, room: RoomSize) -> OrientedRect:
    defaults = accessibility_defaults()
    opening_type = opening.type.strip().lower()
    depth = opening.clearanceDepth
    if depth <= 0:
        depth = defaults.get(opening_type, defaults["door"])

    base = OrientedRect.from_center_size(opening.position, opening.size, opening.rotation)
    # Prefer the local ±Z direction that points toward the room center.
    _, axis_z = base.local_axes()
    room_center = Vec2(room.width * 0.5, room.depth * 0.5)
    to_center = (room_center - base.center).normalized()
    inward = axis_z if axis_z.dot(to_center) >= 0 else axis_z * -1.0
    half_depth = depth * 0.5
    center = base.center + inward * (base.half_depth + half_depth)
    yaw = base.yaw if inward.dot(axis_z) >= 0 else base.yaw + 3.141592653589793
    return OrientedRect(
        center=center,
        half_width=base.half_width,
        half_depth=half_depth,
        yaw=yaw,
    )


def check_accessibility(
    candidate: PlacementCandidate,
    openings: list[SceneOpening],
    room: RoomSize,
) -> CheckDetail:
    if not openings:
        return CheckDetail(
            ruleId="accessibility",
            name="门窗可达性",
            status="pass",
            message="场景未标注门窗，跳过检测",
            details={"blocked": [], "skipped": True},
        )

    cand_rect = OrientedRect.from_center_size(candidate.position, candidate.size, candidate.rotation)
    blocked: list[dict] = []

    for opening in openings:
        keepout = _opening_keepout(opening, room)
        if cand_rect.intersects(keepout):
            blocked.append(
                {
                    "openingId": opening.id,
                    "type": opening.type,
                    "name": opening.name,
                }
            )

    if not blocked:
        return CheckDetail(
            ruleId="accessibility",
            name="门窗可达性",
            status="pass",
            message="不影响门窗使用",
            details={"blocked": []},
        )

    door_hits = [item for item in blocked if item["type"].lower() == "door"]
    window_hits = [item for item in blocked if item["type"].lower() == "window"]

    messages: list[str] = []
    suggestions: list[str] = []
    if door_hits:
        names = "、".join(item["name"] for item in door_hits)
        messages.append(f"进入{names}开启区域")
        suggestions.append("该位置会影响房门正常开启，建议远离门口区域。")
    if window_hits:
        names = "、".join(item["name"] for item in window_hits)
        messages.append(f"遮挡{names}")
        suggestions.append("该位置会遮挡窗户，建议挪开以保留采光与开启空间。")

    return CheckDetail(
        ruleId="accessibility",
        name="门窗可达性",
        status="fail",
        message="；".join(messages),
        suggestion="".join(suggestions),
        details={"blocked": blocked},
    )
