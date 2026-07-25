"""Optional size-fit check against a placement slot / candidate."""

from __future__ import annotations

from app.schemas import PlacementCandidate, SceneResponse


def evaluate_size_fit(
    product_size_m: list[float],
    *,
    candidate: PlacementCandidate | None = None,
    scene: SceneResponse | None = None,
    estimated_query_size: list[float] | None = None,
) -> str:
    """
    Return fits | tight | unknown.

    Priority:
    1) candidate.size as target slot
    2) estimated_query_size as soft reference
    3) room bounds coarse check if scene provided
    """
    if len(product_size_m) < 3:
        return "unknown"

    pw, ph, pd = (float(product_size_m[0]), float(product_size_m[1]), float(product_size_m[2]))

    target: list[float] | None = None
    if candidate is not None and len(candidate.size) >= 3:
        target = [float(candidate.size[0]), float(candidate.size[1]), float(candidate.size[2])]
    elif estimated_query_size and len(estimated_query_size) >= 3:
        target = [float(estimated_query_size[0]), float(estimated_query_size[1]), float(estimated_query_size[2])]

    if target is not None:
        return _compare_dims(pw, ph, pd, target[0], target[1], target[2])

    if scene is not None:
        # Coarse: product footprint must fit inside room (with wall margin)
        margin = 0.2
        max_w = max(0.1, float(scene.room.width) - margin)
        max_d = max(0.1, float(scene.room.depth) - margin)
        max_h = max(0.1, float(scene.room.height) - 0.05)
        if pw <= max_w and pd <= max_d and ph <= max_h:
            # Near room limits → tight
            if pw > max_w * 0.85 or pd > max_d * 0.85 or ph > max_h * 0.9:
                return "tight"
            return "fits"
        return "tight"

    return "unknown"


def _compare_dims(pw: float, ph: float, pd: float, tw: float, th: float, td: float) -> str:
    # Allow 8% over for fits; 20% over for tight; else still tight (won't mark fail here)
    ratios = [
        pw / max(tw, 0.01),
        ph / max(th, 0.01),
        pd / max(td, 0.01),
    ]
    worst = max(ratios)
    if worst <= 1.08:
        return "fits"
    if worst <= 1.2:
        return "tight"
    return "tight"
