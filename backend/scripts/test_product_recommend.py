"""本地 mock：商品识别 + 推荐链路验证。"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# 强制走 mock 属性（无 key 时本就会 mock；有 key 且无图时也用 label）
os.environ.setdefault("SPATIAL_AGENT_PROVIDER", "mock")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.schemas import PlacementCandidate, ProductRecognizeRequest, ProductRecommendRequest
from app.services.product.catalog import load_catalog
from app.services.product.recognize import recognize_product
from app.services.product.recommend import recommend_products
from app.services.room_scan.mock_scene import build_mock_scene


async def main() -> None:
    catalog = load_catalog()
    print(f"catalog size: {len(catalog)}")
    assert len(catalog) >= 12, "catalog should have 12+ SKUs"

    print("\n===== recognize (label=sofa, no image → mock) =====")
    recognition = await recognize_product(ProductRecognizeRequest(label="sofa", objectId="obj_sofa_001"))
    print(json.dumps(recognition.model_dump(), ensure_ascii=False, indent=2))

    print("\n===== recommend (preferSame + budget) =====")
    scene = build_mock_scene("demo_living_room")
    candidate = PlacementCandidate(
        id="slot_sofa",
        label="sofa",
        name="沙发空位",
        position=[1.2, 0.0, 2.1],
        rotation=[0.0, 0.0, 0.0],
        size=[2.0, 0.9, 0.9],
    )
    result = await recommend_products(
        ProductRecommendRequest(
            query=recognition,
            budget=2000,
            preferSame=True,
            limit=5,
            scene=scene,
            candidate=candidate,
        )
    )
    print(f"items: {len(result.items)}")
    for item in result.items:
        print(
            f"- {item.productId} | {item.matchType} | score={item.score:.2f} | "
            f"¥{item.price:.0f} | sizeFit={item.sizeFit} | {item.reason}"
        )

    print("\n===== recognize-and-recommend style (coffee_table) =====")
    result2 = await recommend_products(
        ProductRecommendRequest(label="coffee_table", limit=3)
    )
    print("query:", result2.query.name, result2.query.category, result2.query.source)
    print("top:", [i.title for i in result2.items])
    assert result2.items, "should return recommendations"
    print("\nOK")


if __name__ == "__main__":
    asyncio.run(main())
