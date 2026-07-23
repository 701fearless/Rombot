"""Resume Hunyuan 3D for shuangrenchuang using existing Ark brief + Seedream reference."""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from app.config import get_settings
from app.schemas import FurnitureGenerationBrief
from app.storage.local_store import path_to_output_url
from scripts.generate_image_to_3d import build_provider, download_glb, path_to_compressed_data_url


async def main() -> None:
    get_settings.cache_clear()
    settings = get_settings()
    out_name = "shuangrenchuang"
    work_dir = ROOT / "outputs" / "demos" / out_name
    brief_path = work_dir / "FurnitureGenerationBrief.json"
    ref_path = work_dir / "reference_oblique_3quarter.png"
    if not brief_path.exists() or not ref_path.exists():
        raise SystemExit(f"Missing Ark artifacts under {work_dir}")

    brief = FurnitureGenerationBrief.model_validate_json(brief_path.read_text(encoding="utf-8"))
    # Prefer isolated Seedream subject as primary (avoid cluttered source screenshot).
    image_inputs = [path_to_compressed_data_url(ref_path, max_side=1280)]

    provider = build_provider()
    print(
        f"[hunyuan] model={settings.hunyuan_model} "
        f"type={settings.hunyuan_generate_type} faces={settings.hunyuan_face_count} "
        f"pbr={settings.hunyuan_enable_pbr}",
        flush=True,
    )
    print(f"[hunyuan] primary={ref_path.name}", flush=True)

    total_t0 = time.perf_counter()
    t0 = time.perf_counter()
    task_id = await provider._create_3d_task(image_inputs, brief)
    submit_sec = round(time.perf_counter() - t0, 3)
    print(f"[hunyuan] task_id={task_id} submit={submit_sec}s", flush=True)

    t0 = time.perf_counter()
    result = await provider._poll_3d_task(task_id)
    poll_sec = round(time.perf_counter() - t0, 3)
    status = provider._normalize_status(result)
    glb_url = provider._extract_glb_url(result)
    (work_dir / "hunyuan_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[hunyuan] status={status} poll={poll_sec}s", flush=True)
    if not glb_url:
        raise SystemExit(f"No GLB URL: {result}")

    t0 = time.perf_counter()
    local_glb = work_dir / f"{out_name}.glb"
    await download_glb(glb_url, local_glb)
    download_sec = round(time.perf_counter() - t0, 3)
    resume_sec = round(time.perf_counter() - total_t0, 3)

    timings = {
        "ark_brief_sec": 86.73,
        "ark_reference_views_sec": 39.307,
        "hunyuan_submit_sec": submit_sec,
        "hunyuan_poll_sec": poll_sec,
        "download_glb_sec": download_sec,
        "hunyuan_resume_sec": resume_sec,
        "total_sec_approx": round(86.73 + 39.307 + submit_sec + poll_sec + download_sec, 3),
    }
    print(f"[done] {local_glb} ({local_glb.stat().st_size} bytes)", flush=True)
    print("[timing]", json.dumps(timings, ensure_ascii=False), flush=True)

    meta = {
        "taskId": task_id,
        "status": status,
        "remoteGlbUrl": glb_url,
        "localGlb": str(local_glb),
        "outputUrl": path_to_output_url(local_glb),
        "inputImage": r"D:\Users\016627\Desktop\微信图片_20260723090551_300_16.png",
        "label": "double_bed",
        "name": "双人床",
        "models": {
            "ark_vision": settings.ark_vision_model,
            "ark_image": settings.ark_image_model,
            "hunyuan": settings.hunyuan_model,
            "hunyuan_generate_type": settings.hunyuan_generate_type,
            "hunyuan_face_count": settings.hunyuan_face_count,
        },
        "timings": timings,
        "note": "Resumed Hunyuan from existing Seedream reference_oblique_3quarter.png",
    }
    (work_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    viewer_src = ROOT / "outputs" / "demos" / "mupan" / "viewer.html"
    viewer_dst = work_dir / "viewer.html"
    if viewer_src.exists():
        text = viewer_src.read_text(encoding="utf-8")
        text = text.replace("木盘茶果套装", "双人床").replace("./mupan.glb", f"./{out_name}.glb")
        viewer_dst.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
