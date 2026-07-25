from __future__ import annotations

from app.schemas import CheckDetail, PlacementCandidate, SceneObject
from app.services.layout_reasoning.geometry import OrientedRect, overlap_depth_m
from app.services.layout_reasoning.rules_loader import is_solid_furniture


def check_collision(
    candidate: PlacementCandidate,
    objects: list[SceneObject],
) -> CheckDetail:
    cand_rect = OrientedRect.from_center_size(candidate.position, candidate.size, candidate.rotation)
    conflicts: list[dict] = []

    for obj in objects:
        if obj.id == candidate.id:
            continue
        if not is_solid_furniture(obj.label):
            continue
        other = OrientedRect.from_center_size(obj.position, obj.size, obj.rotation)
        if not cand_rect.intersects(other):
            continue
        conflicts.append(
            {
                "objectId": obj.id,
                "label": obj.label,
                "name": obj.name,
                "overlapDepth_m": round(overlap_depth_m(cand_rect, other), 3),
            }
        )

    if not conflicts:
        return CheckDetail(
            ruleId="collision",
            name="家具冲突",
            status="pass",
            message="未与其他家具发生重叠",
            details={"conflicts": []},
        )

    names = "、".join(item["name"] for item in conflicts)
    worst = max(item["overlapDepth_m"] for item in conflicts)
    move_cm = max(5, round(worst * 100))
    return CheckDetail(
        ruleId="collision",
        name="家具冲突",
        status="fail",
        message=f"与{names}发生重叠",
        suggestion=f"该家具与{names}发生重叠，请调整摆放位置（建议移开约 {move_cm} cm）。",
        details={"conflicts": conflicts},
    )
