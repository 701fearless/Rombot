import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.schemas import FurnitureGenerationBrief
from app.services.model3d.feature_hunyuan_provider import FeatureHunyuanModel3DProvider
from app.storage.local_store import file_to_data_url


def build_provider() -> FeatureHunyuanModel3DProvider:
    settings = get_settings()
    if not settings.ark_api_key or not settings.hunyuan_api_key:
        raise RuntimeError("ARK_API_KEY and HUNYUAN_API_KEY are required")
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


def load_state(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


async def run(reference: Path, brief_path: Path, state_path: Path, submit_only: bool) -> None:
    provider = build_provider()
    state = load_state(state_path)
    task_id = state.get("taskId")
    brief = FurnitureGenerationBrief.model_validate_json(brief_path.read_text(encoding="utf-8"))

    if not task_id:
        task_id = await provider._create_3d_task([file_to_data_url(reference)], brief)
        state = {
            "provider": provider.provider_name,
            "model": provider.hunyuan_model,
            "taskId": task_id,
            "submittedAt": datetime.now(timezone.utc).isoformat(),
            "status": "SUBMITTED",
        }
        save_state(state_path, state)
        print(f"hunyuan submit: OK taskId={task_id}")
        if submit_only:
            return

    async with httpx.AsyncClient(timeout=60) as client:
        result = await provider._query_once(client, str(task_id))
    status = provider._normalize_status(result)
    glb_url = provider._extract_glb_url(result)
    local_glb = None
    if glb_url:
        local_path = reference.with_name("verified_hunyuan.glb")
        async with httpx.AsyncClient(timeout=180, follow_redirects=True) as download_client:
            response = await download_client.get(glb_url)
            response.raise_for_status()
        if response.content[:4] != b"glTF":
            raise RuntimeError("Hunyuan GLB download did not contain a binary glTF header")
        local_path.write_bytes(response.content)
        local_glb = str(local_path)
    state.update(
        {
            "status": status,
            "queriedAt": datetime.now(timezone.utc).isoformat(),
            "glbUrl": glb_url,
            "localGlb": local_glb,
            "result": result,
        }
    )
    save_state(state_path, state)
    print(f"hunyuan query: status={status} glb={bool(glb_url)} downloaded={bool(local_glb)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit/query one generated reference image with persisted state.")
    parser.add_argument("reference", type=Path)
    parser.add_argument("brief", type=Path)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--submit-only", action="store_true")
    args = parser.parse_args()

    reference = args.reference.resolve()
    brief = args.brief.resolve()
    state = (args.state or reference.with_name("hunyuan_verification.json")).resolve()
    if not reference.exists() or not brief.exists():
        raise FileNotFoundError(f"Missing reference or brief: {reference}, {brief}")
    asyncio.run(run(reference, brief, state, args.submit_only))


if __name__ == "__main__":
    main()
