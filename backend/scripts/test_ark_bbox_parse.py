import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.detection.ark_grounding_provider import ArkGroundingProvider


def main() -> None:
    provider = ArkGroundingProvider(api_key="test", base_url="https://example.com", model="test")
    bbox = provider._parse_bbox("<bbox>100 200 800 900</bbox>")
    assert bbox == [100, 200, 800, 900]
    items = provider._parse_items(
        """
        {
          "objects": [{
            "category": "sofa",
            "bbox": "<bbox>100 200 800 900</bbox>",
            "features": {"materials": ["fabric"]},
            "generationHints": {"clutterState": "messy"}
          }]
        }
        """
    )
    assert items[0]["features"]["materials"] == ["fabric"]
    assert items[0]["generationHints"]["clutterState"] == "messy"
    truncated = provider._parse_items(
        '{"objects":[{"category":"sofa","bbox":"<bbox>1 2 3 4</bbox>",'
        '"features":{"materials":["fabric"]}},{"category":"chair","bbox":"<bbox>5'
    )
    assert len(truncated) == 1
    assert truncated[0]["category"] == "sofa"
    print("ark_bbox:", bbox)
    print("pixel_bbox:", provider._scale_ark_bbox(bbox, image_width=1920, image_height=1080))
    print("ark_step1_contract: OK")


if __name__ == "__main__":
    main()
