"""Resolve uploaded crop/object image names to generated reference images."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from app.storage.local_store import BACKEND_ROOT, OUTPUTS_ROOT, path_to_output_url

# Default: WeChat-exported pipeline outputs (override with REFERENCE_VIDEOS_ROOT).
DEFAULT_REFERENCE_VIDEOS_ROOT = Path(
    r"E:\xwechat_files\wxid_ps4rsn2rgwzt22_d445\msg\file\2026-07\backend\backend\outputs\videos"
)

REFERENCE_NAME_CANDIDATES = (
    "reference_oblique_3quarter.png",
    "reference_oblique_3quarter.jpg",
    "reference.png",
    "reference.jpg",
    "reference.jpeg",
    "reference.webp",
)


def reference_videos_root() -> Path:
    env = (os.getenv("REFERENCE_VIDEOS_ROOT") or "").strip()
    if env:
        return Path(env)
    if DEFAULT_REFERENCE_VIDEOS_ROOT.exists():
        return DEFAULT_REFERENCE_VIDEOS_ROOT
    local = BACKEND_ROOT / "outputs" / "videos"
    return local


def _stem(name: str) -> str:
    return Path(name).stem.lower()


def parse_parent_folder_from_image_name(image_name: str) -> str | None:
    """Leading digits in filename are the video folder id, e.g. 1_000022_obj_sofa_001_crop.jpg -> 1."""
    stem = Path(image_name).name
    match = re.match(r"^(\d+)(?:[_-]|$)", stem)
    if not match:
        return None
    return match.group(1)


def parse_label_index(name: str) -> tuple[str | None, int | None]:
    text = _stem(name)
    for pattern in (
        r"candidate_([a-z0-9]+(?:_[a-z0-9]+)*)_(\d+)",
        r"obj_([a-z0-9]+(?:_[a-z0-9]+)*)_(\d+)",
        r"(?:^|_)(([a-z]+)(?:_[a-z]+)*)_(\d+)$",
    ):
        match = re.search(pattern, text, flags=re.I)
        if match:
            groups = match.groups()
            if len(groups) == 2:
                return groups[0].lower(), int(groups[1])
            if len(groups) == 3:
                return groups[1].lower(), int(groups[2])
    # fallback: last token-ish label without index
    match = re.search(r"(sofa|bed|chair|table|rug|lamp|cabinet|wardrobe|desk|armchair|bookshelf|curtain|mirror|plant|tv_stand|coffee_table|dining_table|nightstand|chandelier)", text)
    if match:
        return match.group(1).lower(), None
    return None, None


def _score_folder(folder_name: str, image_stem: str, label: str | None, index: int | None) -> float:
    folder = folder_name.lower()
    stem = image_stem.lower()
    score = 0.0
    if folder == stem or folder in stem or stem in folder:
        score += 100.0
    folder_label, folder_index = parse_label_index(folder_name)
    if label and folder_label == label:
        score += 50.0
        if index is not None and folder_index == index:
            score += 40.0
        elif index is not None and folder_index is not None:
            score += max(0.0, 20.0 - abs(folder_index - index) * 3.0)
        else:
            score += 10.0
    if label and label in folder:
        score += 15.0
    return score


def find_reference_file(folder: Path) -> Path | None:
    for name in REFERENCE_NAME_CANDIDATES:
        path = folder / name
        if path.exists():
            return path
    # any reference* image
    for path in sorted(folder.glob("reference*")):
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} and path.is_file():
            return path
    return None


def resolve_reference(
    *,
    parent_folder: str | None,
    image_name: str,
    videos_root: Path | None = None,
) -> dict:
    """
    Map upload image filename to a generated/*/reference_* image.

    parent_folder: optional; if missing, parse leading digits from image_name (1_xxx -> 1).
    image_name: e.g. "1_000022_obj_sofa_001_crop.jpg"
    """
    root = videos_root or reference_videos_root()
    parent = (parent_folder or "").strip().replace("\\", "/")
    parent = Path(parent).name if parent else ""
    if not parent:
        inferred = parse_parent_folder_from_image_name(image_name)
        if not inferred:
            raise ValueError(
                "Cannot infer video folder from image name; expected leading digits like 1_000022_obj_sofa_001_crop.jpg"
            )
        parent = inferred
    if parent in {".", ".."}:
        raise ValueError("Invalid parent folder name")

    generated = root / parent / "generated"
    if not generated.is_dir():
        raise FileNotFoundError(f"generated folder not found: {generated}")

    stem = _stem(image_name)
    label, index = parse_label_index(image_name)
    candidates = [p for p in generated.iterdir() if p.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"No candidate folders under {generated}")

    ranked = sorted(
        candidates,
        key=lambda path: _score_folder(path.name, stem, label, index),
        reverse=True,
    )
    best = ranked[0]
    best_score = _score_folder(best.name, stem, label, index)
    if best_score < 15.0:
        raise FileNotFoundError(
            f"No fuzzy match for image={image_name!r} under {generated} "
            f"(best={best.name} score={best_score:.1f})"
        )

    reference = find_reference_file(best)
    if reference is None:
        raise FileNotFoundError(f"No reference image in {best}")

    # Stage into local outputs so the demo can load via /outputs URL.
    staged_dir = OUTPUTS_ROOT / "shop" / "resolved" / parent / best.name
    staged_dir.mkdir(parents=True, exist_ok=True)
    staged = staged_dir / reference.name
    if not staged.exists() or staged.stat().st_mtime < reference.stat().st_mtime:
        shutil.copy2(reference, staged)

    return {
        "parentFolder": parent,
        "imageName": Path(image_name).name,
        "imageStem": stem,
        "parsedLabel": label,
        "parsedIndex": index,
        "matchedFolder": best.name,
        "matchScore": round(best_score, 2),
        "referencePath": str(reference),
        "referenceUrl": path_to_output_url(staged),
        "videosRoot": str(root),
        "alternatives": [
            {
                "folder": path.name,
                "score": round(_score_folder(path.name, stem, label, index), 2),
            }
            for path in ranked[:5]
        ],
    }
