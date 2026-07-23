"""
Generate a GLB from a local image via Ark (brief + Seedream refs) + Hunyuan 3D.
Records per-stage and total wall-clock time.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import sys
import time
from io import BytesIO
from pathlib import Path

import httpx
from dotenv import load_dotenv
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from app.config import get_settings
from app.schemas import DetectedObject
from app.services.model3d.feature_hunyuan_provider import FeatureHunyuanModel3DProvider
from app.storage.local_store import OUTPUTS_ROOT, path_to_output_url


def prepare_image_data_url(path: Path, max_side: int = 1280, quality: int = 90) -> str:
    image = Image.open(path).convert("RGB")
    width, height = image.size
    # Drop common short-video UI strip on the right for portrait frames.
    if width / max(height, 1) < 0.85:
        image = image.crop((0, 0, int(width * 0.88), height))
    width, height = image.size
    scale = min(1.0, max_side / max(width, height))
    if scale < 1.0:
        image = image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def path_to_compressed_data_url(path: Path, max_side: int = 1024, quality: int = 88) -> str:
    image = Image.open(path).convert("RGB")
    width, height = image.size
    scale = min(1.0, max_side / max(width, height))
    if scale < 1.0:
        image = image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def build_provider() -> FeatureHunyuanModel3DProvider:
    settings = get_settings()
    if not settings.hunyuan_api_key or not settings.hunyuan_base_url:
        raise SystemExit("HUNYUAN_API_KEY and HUNYUAN_BASE_URL are required")
    if not settings.ark_api_key:
        raise SystemExit("ARK_API_KEY is required")
    return FeatureHunyuanModel3DProvider(
        ark_api_key=settings.ark_api_key,
        ark_base_url=settings.ark_base_url,
        ark_vision_model=settings.ark_vision_model,
        ark_image_model=settings.ark_image_model,
        ark_image_size=settings.ark_image_size,
        hunyuan_api_key=settings.hunyuan_api_key,
        hunyuan_base_url=settings.hunyuan_base_url,
        hunyuan_model=settings.hunyuan_model,
        hunyuan_generate_type=settings.hunyuan_generate_type,
        hunyuan_face_count=settings.hunyuan_face_count,
        hunyuan_enable_pbr=settings.hunyuan_enable_pbr,
        hunyuan_poll_interval_sec=settings.hunyuan_poll_interval_sec,
        hunyuan_poll_attempts=settings.hunyuan_poll_attempts,
    )


def make_object(object_id: str, label: str, name: str) -> DetectedObject:
    return DetectedObject(
        id=object_id,
        label=label,
        name=name,
        confidence=0.99,
        bbox=[80, 220, 980, 1480],
        tagPosition=[0.5, 0.52],
    )


async def download_glb(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=180, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        content = response.content
        if content[:4] != b"glTF" and b"glTF" not in content[:16]:
            # Some signed URLs may still be zip; refuse silent wrong asset.
            if content[:2] == b"PK":
                raise RuntimeError("Downloaded ZIP instead of GLB; check _extract_glb_url selection.")
        dest.write_bytes(content)
    return dest


async def run(image_path: Path, label: str, name: str, out_name: str) -> Path:
    timings: dict[str, float] = {}
    total_t0 = time.perf_counter()

    provider = build_provider()
    settings = get_settings()
    work_dir = OUTPUTS_ROOT / "demos" / out_name
    work_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    source = prepare_image_data_url(image_path)
    (work_dir / "source.jpg").write_bytes(image_path.read_bytes())
    detected = make_object(f"obj_{out_name}", label, name)
    image_inputs = [source]
    timings["prepare_image_sec"] = round(time.perf_counter() - t0, 3)

    print(f"[ark] vision={settings.ark_vision_model}", flush=True)
    print(f"[ark] image={settings.ark_image_model} size={settings.ark_image_size}", flush=True)
    print(f"[hunyuan] model={settings.hunyuan_model}", flush=True)

    t0 = time.perf_counter()
    print("[ark] creating generation brief...", flush=True)
    try:
        brief = await provider._create_generation_brief(detected, source)
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        print(f"[ark] HTTP {status}: {exc}", flush=True)
        if status == 404:
            raise SystemExit("Ark returned 404 — stopping.") from exc
        raise SystemExit(f"Ark brief failed with HTTP {status}.") from exc
    timings["ark_brief_sec"] = round(time.perf_counter() - t0, 3)
    print(f"[ark] brief done in {timings['ark_brief_sec']}s", flush=True)
    print(f"[ark] subject prompt: {brief.prompt[:220]}...", flush=True)

    t0 = time.perf_counter()
    print("[ark] creating Seedream reference views...", flush=True)
    try:
        refs = await provider._create_reference_views(brief, work_dir, source_image=source)
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        print(f"[ark] HTTP {status}: {exc}", flush=True)
        if status == 404:
            raise SystemExit("Ark Seedream returned 404 — stopping.") from exc
        raise SystemExit(f"Ark Seedream failed with HTTP {status}.") from exc
    for ref in refs:
        print(f"  - {ref.type}: {ref.url}", flush=True)
        if ref.path:
            image_inputs.append(path_to_compressed_data_url(Path(ref.path)))
    image_inputs = image_inputs[:4]
    timings["ark_reference_views_sec"] = round(time.perf_counter() - t0, 3)
    print(f"[ark] references done in {timings['ark_reference_views_sec']}s", flush=True)

    (work_dir / "FurnitureGenerationBrief.json").write_text(
        brief.model_dump_json(indent=2),
        encoding="utf-8",
    )

    t0 = time.perf_counter()
    print(f"[hunyuan] submitting with {len(image_inputs)} image(s)...", flush=True)
    try:
        task_id = await provider._create_3d_task(image_inputs, brief)
    except Exception as exc:
        print(f"[hunyuan] multi-image submit failed ({exc}); retry primary only...", flush=True)
        task_id = await provider._create_3d_task(image_inputs[:1], brief)
    timings["hunyuan_submit_sec"] = round(time.perf_counter() - t0, 3)
    print(f"[hunyuan] task_id={task_id} submit={timings['hunyuan_submit_sec']}s", flush=True)

    t0 = time.perf_counter()
    result = await provider._poll_3d_task(task_id)
    timings["hunyuan_poll_sec"] = round(time.perf_counter() - t0, 3)
    status = provider._normalize_status(result)
    glb_url = provider._extract_glb_url(result)

    (work_dir / "hunyuan_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[hunyuan] status={status} poll={timings['hunyuan_poll_sec']}s", flush=True)

    if not glb_url:
        raise RuntimeError(f"No GLB URL in Hunyuan result: {result}")

    t0 = time.perf_counter()
    local_glb = work_dir / f"{out_name}.glb"
    print(f"[download] {glb_url[:120]}...", flush=True)
    await download_glb(glb_url, local_glb)
    timings["download_glb_sec"] = round(time.perf_counter() - t0, 3)
    timings["total_sec"] = round(time.perf_counter() - total_t0, 3)

    print(f"[done] {local_glb} ({local_glb.stat().st_size} bytes)", flush=True)
    print("[timing]", json.dumps(timings, ensure_ascii=False), flush=True)

    meta = {
        "taskId": task_id,
        "status": status,
        "remoteGlbUrl": glb_url,
        "localGlb": str(local_glb),
        "outputUrl": path_to_output_url(local_glb),
        "inputImage": str(image_path),
        "label": label,
        "name": name,
        "models": {
            "ark_vision": settings.ark_vision_model,
            "ark_image": settings.ark_image_model,
            "hunyuan": settings.hunyuan_model,
        },
        "timings": timings,
    }
    (work_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # Ensure a viewer exists beside the new asset.
    viewer_src = OUTPUTS_ROOT / "demos" / "mupan" / "viewer.html"
    viewer_dst = work_dir / "viewer.html"
    if viewer_src.exists() and not viewer_dst.exists():
        text = viewer_src.read_text(encoding="utf-8")
        text = text.replace("木盘茶果套装", name).replace("./mupan.glb", f"./{out_name}.glb")
        viewer_dst.write_text(text, encoding="utf-8")
    elif viewer_dst.exists():
        text = viewer_dst.read_text(encoding="utf-8")
        text = text.replace("./mupan.glb", f"./{out_name}.glb")
        viewer_dst.write_text(text, encoding="utf-8")

    return local_glb


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--label", default="picture_frame_vase")
    parser.add_argument("--name", default="相框花瓶")
    parser.add_argument("--out-name", default="xiangkuang_huaping")
    args = parser.parse_args()
    image = args.image.resolve()
    if not image.exists():
        raise FileNotFoundError(image)
    get_settings.cache_clear()
    asyncio.run(run(image, args.label, args.name, args.out_name))


if __name__ == "__main__":
    main()
