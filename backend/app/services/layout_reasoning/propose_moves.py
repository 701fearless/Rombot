"""Derive deterministic furniture move proposals from geometry check results."""

from __future__ import annotations

from app.schemas import (
    CheckDetail,
    FurnitureMove,
    PlacementCandidate,
    SceneResponse,
)
from app.services.layout_reasoning.checks.accessibility import _opening_keepout
from app.services.layout_reasoning.geometry import Aabb2, OrientedRect, Vec2, overlap_depth_m
from app.services.layout_reasoning.rules_loader import is_solid_furniture


def propose_moves_from_geometry(
    candidate: PlacementCandidate,
    scene: SceneResponse,
    checks: list[CheckDetail],
) -> list[FurnitureMove]:
    """Build Chinese-labeled move proposals for the candidate furniture."""
    by_rule = {c.ruleId: c for c in checks}
    pos = list(candidate.position)
    rot = list(candidate.rotation)
    delta = Vec2(0.0, 0.0)
    reasons: list[str] = []

    fit = by_rule.get("fit")
    if fit and fit.status == "fail":
        overflow = (fit.details or {}).get("overflow_m") or {}
        # left overflow -> move +x; right -> -x; front -> +z; back -> -z
        dx = float(overflow.get("left") or 0.0) - float(overflow.get("right") or 0.0)
        dz = float(overflow.get("front") or 0.0) - float(overflow.get("back") or 0.0)
        if abs(dx) > 1e-4 or abs(dz) > 1e-4:
            delta = delta + Vec2(dx, dz)
            bits = []
            if overflow.get("left"):
                bits.append(f"向右约 {round(overflow['left'] * 100)} cm")
            if overflow.get("right"):
                bits.append(f"向左约 {round(overflow['right'] * 100)} cm")
            if overflow.get("front"):
                bits.append(f"向后约 {round(overflow['front'] * 100)} cm")
            if overflow.get("back"):
                bits.append(f"向前约 {round(overflow['back'] * 100)} cm")
            reasons.append("房间越界：" + "，".join(bits))

    collision = by_rule.get("collision")
    if collision and collision.status == "fail":
        cand_rect = OrientedRect.from_center_size(pos, candidate.size, rot)
        sep = _collision_separation(candidate, scene, cand_rect)
        if sep.length() > 1e-4:
            delta = delta + sep
            cm = max(5, round(sep.length() * 100))
            conflicts = (collision.details or {}).get("conflicts") or []
            names = "、".join(item.get("name") or item.get("objectId") or "?" for item in conflicts) or "其他家具"
            reasons.append(f"与{names}重叠，建议分离约 {cm} cm")

    access = by_rule.get("accessibility")
    if access and access.status == "fail":
        push = _accessibility_push(candidate, scene, pos, rot)
        if push.length() > 1e-4:
            delta = delta + push
            blocked = (access.details or {}).get("blocked") or []
            names = "、".join(item.get("name") or "?" for item in blocked) or "门窗"
            cm = max(5, round(push.length() * 100))
            reasons.append(f"离开{names}净空区，建议移开约 {cm} cm")

    clearance = by_rule.get("clearance")
    if clearance and clearance.status in {"fail", "warn"}:
        push = _clearance_push(candidate, clearance)
        if push.length() > 1e-4:
            delta = delta + push
            cm = max(5, round(push.length() * 100))
            reasons.append(f"补充活动空间，建议调整约 {cm} cm")

    if delta.length() < 1e-4:
        return []

    to_pos = [round(pos[0] + delta.x, 3), round(pos[1], 3), round(pos[2] + delta.z, 3)]
    to_pos = _clamp_center_to_room(to_pos, candidate.size, rot, scene.room.width, scene.room.depth)
    if _almost_same(pos, to_pos):
        return []

    return [
        FurnitureMove(
            objectId=candidate.id,
            name=candidate.name,
            fromPosition=[round(v, 3) for v in pos],
            toPosition=to_pos,
            fromRotation=[round(v, 4) for v in rot],
            toRotation=[round(v, 4) for v in rot],
            reason="；".join(reasons) if reasons else "根据几何检测建议调整位置",
            source="geometry",
        )
    ]


def _collision_separation(
    candidate: PlacementCandidate,
    scene: SceneResponse,
    cand_rect: OrientedRect,
) -> Vec2:
    best = Vec2(0.0, 0.0)
    best_len = 0.0
    for obj in scene.objects:
        if obj.id == candidate.id or not is_solid_furniture(obj.label):
            continue
        other = OrientedRect.from_center_size(obj.position, obj.size, obj.rotation)
        if not cand_rect.intersects(other):
            continue
        depth = overlap_depth_m(cand_rect, other)
        direction = (cand_rect.center - other.center)
        if direction.length() < 1e-6:
            direction = Vec2(1.0, 0.0)
        else:
            direction = direction.normalized()
        # add small margin beyond penetration
        sep = direction * (depth + 0.05)
        if sep.length() > best_len:
            best = sep
            best_len = sep.length()
    return best


def _accessibility_push(
    candidate: PlacementCandidate,
    scene: SceneResponse,
    pos: list[float],
    rot: list[float],
) -> Vec2:
    cand_rect = OrientedRect.from_center_size(pos, candidate.size, rot)
    total = Vec2(0.0, 0.0)
    for opening in scene.openings:
        keepout = _opening_keepout(opening, scene.room)
        if not cand_rect.intersects(keepout):
            continue
        direction = (cand_rect.center - keepout.center)
        if direction.length() < 1e-6:
            # push toward room center
            room_center = Vec2(scene.room.width * 0.5, scene.room.depth * 0.5)
            direction = room_center - cand_rect.center
        direction = direction.normalized()
        depth = overlap_depth_m(cand_rect, keepout)
        total = total + direction * (depth + 0.08)
    return total


def _clearance_push(candidate: PlacementCandidate, clearance: CheckDetail) -> Vec2:
    """Use first failing/warning side deficit if present in details."""
    sides = (clearance.details or {}).get("sides") or []
    axis_map = {
        "front": Vec2(0.0, 1.0),   # need more front clearance -> move back (+z in default yaw0)
        "back": Vec2(0.0, -1.0),
        "left": Vec2(1.0, 0.0),
        "right": Vec2(-1.0, 0.0),
    }
    # Prefer local axes of candidate
    rect = OrientedRect.from_center_size(candidate.position, candidate.size, candidate.rotation)
    total = Vec2(0.0, 0.0)
    for item in sides:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "")
        if status not in {"fail", "warn"}:
            continue
        side = str(item.get("side") or "")
        required = float(item.get("required_m") or item.get("required") or 0.0)
        actual = float(item.get("actual_m") or item.get("actual") or 0.0)
        deficit = max(0.0, required - actual)
        if deficit <= 1e-4:
            continue
        if side in ("front", "back", "left", "right"):
            local = {"front": (0.0, -1.0), "back": (0.0, 1.0), "left": (-1.0, 0.0), "right": (1.0, 0.0)}[side]
            # move opposite to the short side so clearance grows on that side
            move_dir = rect.world_direction((-local[0], -local[1]))
            total = total + move_dir * deficit
        elif side in axis_map:
            total = total + axis_map[side] * deficit
    return total


def _clamp_center_to_room(
    position: list[float],
    size: list[float],
    rotation: list[float],
    room_width: float,
    room_depth: float,
) -> list[float]:
    rect = OrientedRect.from_center_size(position, size, rotation)
    room = Aabb2.from_room(room_width, room_depth)
    overflow = room.clamp_overflow(rect)
    x = position[0] + overflow["left"] - overflow["right"]
    z = position[2] + overflow["front"] - overflow["back"]
    return [round(x, 3), round(position[1], 3), round(z, 3)]


def _almost_same(a: list[float], b: list[float], eps: float = 1e-3) -> bool:
    return all(abs(x - y) <= eps for x, y in zip(a, b))
