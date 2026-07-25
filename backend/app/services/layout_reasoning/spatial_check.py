from __future__ import annotations

from app.schemas import (
    PlacementCandidate,
    SceneResponse,
    SpatialCheckResponse,
)
from app.services.layout_reasoning.checks.accessibility import check_accessibility
from app.services.layout_reasoning.checks.clearance import check_clearance
from app.services.layout_reasoning.checks.collision import check_collision
from app.services.layout_reasoning.checks.fit import check_fit
from app.services.layout_reasoning.feedback import compose_feedback, overall_status


def run_spatial_check(candidate: PlacementCandidate, scene: SceneResponse) -> SpatialCheckResponse:
    """执行 V1 四条基础空间可行性检测。"""
    checks = [
        check_fit(candidate, scene.room),
        check_collision(candidate, scene.objects),
        check_accessibility(candidate, scene.openings, scene.room),
        check_clearance(candidate, scene.room, scene.objects),
    ]
    return SpatialCheckResponse(
        overallStatus=overall_status(checks),
        checks=checks,
        feedback=compose_feedback(candidate, checks),
    )
