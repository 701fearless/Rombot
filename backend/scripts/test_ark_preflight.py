import argparse
import asyncio
import base64
import json
import mimetypes
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.services.detection.ark_grounding_provider import ArkGroundingProvider


def data_uri(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def post_json(url: str, api_key: str, payload: dict) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {error_body}") from exc


def test_grounding(image: str) -> None:
    settings = get_settings()
    provider = ArkGroundingProvider(
        api_key=settings.ark_api_key or "",
        base_url=settings.ark_base_url,
        model=settings.ark_vision_model,
    )
    objects = asyncio.run(provider.detect(image))
    if not objects:
        raise RuntimeError(
            "Ark grounding returned no supported furniture objects. "
            f"raw={provider.last_response_text[:1500]}"
        )
    if not any(item.visualFeatures for item in objects):
        raise RuntimeError("Ark grounding returned bbox but no visualFeatures")
    if not any(item.generationHints for item in objects):
        raise RuntimeError("Ark grounding returned bbox but no generationHints")

    print("ark grounding/features: OK")
    for item in objects:
        print(
            f"  - {item.label} bbox={item.bbox} "
            f"features={bool(item.visualFeatures)} hints={bool(item.generationHints)}"
        )


def test_seedream(image: str) -> None:
    settings = get_settings()
    payload = {
        "model": settings.ark_image_model,
        "prompt": (
            "Generate one clean 45-degree product reference image of the same furniture. "
            "Regularize temporary clutter, preserve materials and patterns, complete "
            "occluded parts conservatively, and use a plain light background."
        ),
        "image": [image],
        "size": settings.ark_image_size,
        "sequential_image_generation": "disabled",
        "stream": False,
        "response_format": "b64_json",
        "watermark": False,
    }
    data = post_json(
        f"{settings.ark_base_url.rstrip('/')}/images/generations",
        settings.ark_api_key or "",
        payload,
    )
    first = (data.get("data") or [{}])[0]
    if not (first.get("b64_json") or first.get("url")):
        raise RuntimeError(f"Seedream returned no image payload: {data}")
    print("seedream image generation: OK")


def main() -> None:
    parser = argparse.ArgumentParser(description="Preflight-test Ark grounding/features + Seedream.")
    parser.add_argument("image", type=Path, help="Local furniture or room image path.")
    args = parser.parse_args()

    settings = get_settings()
    if not settings.ark_api_key:
        raise RuntimeError("ARK_API_KEY is empty")

    image_path = args.image.resolve()
    if not image_path.exists():
        raise FileNotFoundError(image_path)

    image = data_uri(image_path)
    test_grounding(image)
    test_seedream(image)
    print("ark preflight: OK")


if __name__ == "__main__":
    main()
