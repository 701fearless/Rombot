import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.detection.ark_grounding_provider import ArkGroundingProvider


def main() -> None:
    provider = ArkGroundingProvider(api_key="test", base_url="https://example.com", model="test")
    bbox = provider._parse_bbox("<bbox>100 200 800 900</bbox>")
    print("ark_bbox:", bbox)
    print("pixel_bbox:", provider._scale_ark_bbox(bbox, image_width=1920, image_height=1080))


if __name__ == "__main__":
    main()
