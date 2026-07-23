"""Resume Hunyuan stage using already-generated Ark brief + Seedream references."""

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
from app.services.model3d.feature_hunyuan_provider import FeatureHunyuanModel3DProvider
from app.storage.local_store import path_to_output_url
from scripts.generate_image_to_3d import (
    build_provider,
    download_glb,
    path_to_compressed_data_url,
    prepare_image_data_url,
)


async def main() -> None:
    get_settings.cache_clear()
    out_name = "xiangkuang_huaping"
    work_dir = ROOT / "outputs" / "demos" / out_name
    source_path = Path(r"D:\Users\016627\Desktop\微信图片_20260721211936_17138_2.jpg")
    brief = FurnitureGenerationBrief.model_validate_json(
        (work_dir / "FurnitureGenerationBrief.json").read_text(encoding="utf-8")
    )

    # Prefer clean Seedream isolated subject as primary when available.
    primary_path = work_dir / "reference_front.png"
    if primary_path.exists():
        image_inputs = [path_to_compressed_data_url(primary_path, max_side=1280)]
    else:
        image_inputs = [prepare_image_data_url(source_path)]

    for name in ("reference_left_3quarter.png", "reference_back.png"):
        path = work_dir / name
        if path.exists():
            image_inputs.append(path_to_compressed_data_url(path, max_side=1024))

    # Cap to primary + 2 views for TokenHub left/back/right mapping.
    image_inputs = image_inputs[:3]

    provider = build_provider()
    timings: dict[str, float] = {}
    if (work_dir / "meta_partial.json").exists():
        timings.update(json.loads((work_dir / "meta_partial.json").read_text(encoding="utf-8")).get("timings", {}))
    else:
        timings = {
            "ark_brief_sec": 217.31,
            "ark_reference_views_sec": 91.536,
        }

    total_t0 = time.perf_counter()
    print(f"[hunyuan] submitting with {len(image_inputs)} image(s)...", flush=True)
    t0 = time.perf_counter()
    try:
        task_id = await provider._create_3d_task(image_inputs, brief)
    except Exception as exc:
        print(f"[hunyuan] multi-view failed ({exc}); retry single image...", flush=True)
        task_id = await provider._create_3d_task(image_inputs[:1], brief)
    timings["hunyuan_submit_sec"] = round(time.perf_counter() - t0, 3)
    print(f"[hunyuan] task_id={task_id}", flush=True)

    t0 = time.perf_counter()
    result = await provider._poll_3d_task(task_id)
    timings["hunyuan_poll_sec"] = round(time.perf_counter() - t0, 3)
    status = provider._normalize_status(result)
    glb_url = provider._extract_glb_url(result)
    (work_dir / "hunyuan_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[hunyuan] status={status} poll={timings['hunyuan_poll_sec']}s", flush=True)
    if not glb_url:
        raise SystemExit(f"No GLB: {result}")

    t0 = time.perf_counter()
    local_glb = work_dir / f"{out_name}.glb"
    await download_glb(glb_url, local_glb)
    timings["download_glb_sec"] = round(time.perf_counter() - t0, 3)
    # Approximate total = prior Ark stages + this resume segment.
    resume_sec = round(time.perf_counter() - total_t0, 3)
    timings["hunyuan_resume_sec"] = resume_sec
    timings["total_sec_approx"] = round(
        timings.get("ark_brief_sec", 0)
        + timings.get("ark_reference_views_sec", 0)
        + timings.get("hunyuan_submit_sec", 0)
        + timings.get("hunyuan_poll_sec", 0)
        + timings.get("download_glb_sec", 0),
        3,
    )
    print(f"[done] {local_glb} ({local_glb.stat().st_size} bytes)", flush=True)
    print("[timing]", json.dumps(timings, ensure_ascii=False), flush=True)

    settings = get_settings()
    meta = {
        "taskId": task_id,
        "status": status,
        "remoteGlbUrl": glb_url,
        "localGlb": str(local_glb),
        "outputUrl": path_to_output_url(local_glb),
        "inputImage": str(source_path),
        "label": "picture_frame_vase",
        "name": "相框花瓶",
        "models": {
            "ark_vision": settings.ark_vision_model,
            "ark_image": settings.ark_image_model,
            "hunyuan": settings.hunyuan_model,
        },
        "timings": timings,
        "note": "Hunyuan resumed after fixing multi-view view_type; Ark stages reused.",
    }
    (work_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    viewer_src = ROOT / "outputs" / "demos" / "mupan" / "viewer.html"
    viewer_dst = work_dir / "viewer.html"
    if viewer_src.exists():
        text = viewer_src.read_text(encoding="utf-8")
        text = text.replace("木盘茶果套装", "相框花瓶").replace("./mupan.glb", f"./{out_name}.glb")
        viewer_dst.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
