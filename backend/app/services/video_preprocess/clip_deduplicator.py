import math
import re
import shutil
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from PIL import Image, ImageDraw, ImageFilter, ImageStat

from app.schemas import DeduplicatedObject, DetectedObject, VideoAnalysisFrame
from app.services.detection.furniture_labels import normalize_label
from app.storage.local_store import output_url_to_path, path_to_output_url


class ImageEncoder(Protocol):
    def encode(self, image_paths: list[Path], batch_size: int) -> list[list[float]]: ...


class ClipImageEncoder:
    _instances: dict[tuple[str, str], "ClipImageEncoder"] = {}
    _instances_lock = threading.Lock()

    def __init__(self, model_name: str, device: str) -> None:
        import torch
        from transformers import CLIPModel, CLIPProcessor

        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        if device not in {"cpu", "cuda"}:
            raise ValueError("FURNITURE_DEDUPE_DEVICE must be auto, cpu, or cuda")
        if device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested for furniture deduplication but is unavailable")

        self._torch = torch
        self._device = device
        self._processor = CLIPProcessor.from_pretrained(model_name)
        self._model = CLIPModel.from_pretrained(model_name, use_safetensors=True).to(device)
        self._model.eval()
        self._inference_lock = threading.Lock()

    @classmethod
    def shared(cls, model_name: str, device: str) -> "ClipImageEncoder":
        key = (model_name, device)
        with cls._instances_lock:
            instance = cls._instances.get(key)
            if instance is None:
                instance = cls(model_name, device)
                cls._instances[key] = instance
            return instance

    def encode(self, image_paths: list[Path], batch_size: int) -> list[list[float]]:
        embeddings: list[list[float]] = []
        with self._inference_lock, self._torch.inference_mode():
            for start in range(0, len(image_paths), batch_size):
                paths = image_paths[start : start + batch_size]
                with_images = [Image.open(path).convert("RGB") for path in paths]
                try:
                    inputs = self._processor(images=with_images, return_tensors="pt", padding=True)
                    inputs = {key: value.to(self._device) for key, value in inputs.items()}
                    features = self._model.get_image_features(**inputs)
                    if not self._torch.is_tensor(features):
                        image_embeds = getattr(features, "image_embeds", None)
                        if image_embeds is not None:
                            features = image_embeds
                        else:
                            pooled_output = getattr(features, "pooler_output", None)
                            if pooled_output is None:
                                raise TypeError(
                                    f"Unsupported CLIP image feature output: {type(features).__name__}"
                                )
                            projection = self._model.visual_projection
                            feature_width = pooled_output.shape[-1]
                            if feature_width == projection.in_features:
                                features = projection(pooled_output)
                            elif feature_width == projection.out_features:
                                features = pooled_output
                            else:
                                raise ValueError(
                                    "Unexpected CLIP pooled feature width: "
                                    f"{feature_width}; expected {projection.in_features} or "
                                    f"{projection.out_features}"
                                )
                    features = features / features.norm(dim=-1, keepdim=True).clamp(min=1e-12)
                    embeddings.extend(features.cpu().tolist())
                finally:
                    for image in with_images:
                        image.close()
        return embeddings


@dataclass
class DetectionObservation:
    frame_id: str
    frame_path: Path
    detected_object: DetectedObject
    crop_path: Path
    has_crop: bool = True


@dataclass
class DetectionGroup:
    label: str
    members: list[DetectionObservation] = field(default_factory=list)
    embeddings: list[list[float]] = field(default_factory=list)
    centroid: list[float] = field(default_factory=list)

    def add(self, observation: DetectionObservation, embedding: list[float]) -> None:
        self.members.append(observation)
        self.embeddings.append(embedding)
        dimensions = len(embedding)
        mean = [sum(item[index] for item in self.embeddings) / len(self.embeddings) for index in range(dimensions)]
        self.centroid = _normalize(mean)


class ClipFurnitureDeduplicator:
    def __init__(
        self,
        threshold: float,
        batch_size: int,
        model_name: str,
        device: str,
        encoder: ImageEncoder | None = None,
    ) -> None:
        if not 0 <= threshold <= 1:
            raise ValueError("Furniture deduplication threshold must be between 0 and 1")
        self.threshold = threshold
        self.batch_size = batch_size
        self.model_name = model_name
        self.device = device
        self.encoder = encoder

    def deduplicate(
        self,
        video_id: str,
        frames: list[VideoAnalysisFrame],
        video_output_dir: Path,
        enabled: bool = True,
        fallback_on_error: bool = True,
    ) -> tuple[list[DeduplicatedObject], str | None]:
        observations, invalid = self._collect_observations(frames)
        warning: str | None = None

        if enabled and observations:
            try:
                encoder = self.encoder or ClipImageEncoder.shared(self.model_name, self.device)
                embeddings = encoder.encode([item.crop_path for item in observations], self.batch_size)
                if len(embeddings) != len(observations):
                    raise RuntimeError("CLIP returned an unexpected number of embeddings")
                groups = self._group(observations, embeddings)
            except Exception as exc:
                if not fallback_on_error:
                    raise
                warning = f"Furniture deduplication was skipped: {type(exc).__name__}: {exc}"
                groups = self._individual_groups(observations)
        else:
            groups = self._individual_groups(observations)

        groups.extend(self._individual_groups(invalid))
        candidates = self._render_candidates(video_id, groups, video_output_dir)
        return candidates, warning

    def _collect_observations(
        self,
        frames: list[VideoAnalysisFrame],
    ) -> tuple[list[DetectionObservation], list[DetectionObservation]]:
        valid: list[DetectionObservation] = []
        invalid: list[DetectionObservation] = []
        for frame in frames:
            frame_path = output_url_to_path(frame.frameImageUrl)
            if frame_path is None or not frame_path.exists():
                continue
            for detected_object in frame.objects:
                crop_path = output_url_to_path(detected_object.cropUrl or "")
                observation = DetectionObservation(
                    frame_id=frame.frameId,
                    frame_path=frame_path,
                    detected_object=detected_object,
                    crop_path=crop_path or frame_path,
                    has_crop=crop_path is not None and crop_path.exists(),
                )
                if observation.has_crop:
                    valid.append(observation)
                else:
                    invalid.append(observation)
        return valid, invalid

    def _group(
        self,
        observations: list[DetectionObservation],
        embeddings: list[list[float]],
    ) -> list[DetectionGroup]:
        groups: list[DetectionGroup] = []
        for observation, embedding in zip(observations, embeddings):
            normalized_embedding = _normalize(embedding)
            label = normalize_label(observation.detected_object.label)
            matching = [group for group in groups if group.label == label]
            best_group = max(matching, key=lambda group: _dot(normalized_embedding, group.centroid), default=None)
            if best_group is not None and _dot(normalized_embedding, best_group.centroid) >= self.threshold:
                best_group.add(observation, normalized_embedding)
            else:
                group = DetectionGroup(label=label)
                group.add(observation, normalized_embedding)
                groups.append(group)
        return groups

    def _individual_groups(self, observations: list[DetectionObservation]) -> list[DetectionGroup]:
        return [DetectionGroup(label=normalize_label(item.detected_object.label), members=[item]) for item in observations]

    def _render_candidates(
        self,
        video_id: str,
        groups: list[DetectionGroup],
        video_output_dir: Path,
    ) -> list[DeduplicatedObject]:
        output_root = video_output_dir / "deduplicated"
        if output_root.exists():
            shutil.rmtree(output_root)
        output_root.mkdir(parents=True, exist_ok=True)

        label_counts: dict[str, int] = {}
        candidates: list[DeduplicatedObject] = []
        for group in groups:
            label_counts[group.label] = label_counts.get(group.label, 0) + 1
            safe_label = re.sub(r"[^a-z0-9]+", "_", group.label).strip("_") or "object"
            candidate_id = f"candidate_{safe_label}_{label_counts[group.label]:03d}"
            representative = max(group.members, key=self._quality_score)
            candidate_dir = output_root / candidate_id
            candidate_dir.mkdir(parents=True, exist_ok=True)

            annotated_path = candidate_dir / "annotated.jpg"
            crop_path = candidate_dir / "crop.jpg"
            self._save_annotated(representative, candidate_id, annotated_path)
            with self._open_crop(representative) as crop:
                crop.save(crop_path, quality=92)

            detected = representative.detected_object
            candidate = DeduplicatedObject(
                id=candidate_id,
                label=group.label,
                name=detected.name,
                representativeFrameId=representative.frame_id,
                representativeObjectId=detected.id,
                annotatedImageUrl=path_to_output_url(annotated_path),
                cropUrl=path_to_output_url(crop_path),
                maskUrl=detected.maskUrl,
                bbox=detected.bbox,
                confidence=detected.confidence,
                duplicateCount=len(group.members),
            )
            candidate_crop_url = candidate.cropUrl
            for member in group.members:
                member.detected_object.deduplicatedObjectId = candidate_id
                member.detected_object.deduplicatedCropUrl = candidate_crop_url
            metadata_path = candidate_dir / "metadata.json"
            metadata_path.write_text(candidate.model_dump_json(indent=2), encoding="utf-8")
            candidates.append(candidate)
        return candidates

    def _quality_score(self, observation: DetectionObservation) -> float:
        detected = observation.detected_object
        with Image.open(observation.frame_path) as frame:
            width, height = frame.size
        left, top, right, bottom = detected.bbox
        area_ratio = max(0, right - left) * max(0, bottom - top) / max(1, width * height)
        touches_edge = left <= 1 or top <= 1 or right >= width - 1 or bottom >= height - 1
        with self._open_crop(observation) as crop:
            edges = crop.convert("L").filter(ImageFilter.FIND_EDGES)
            variance = ImageStat.Stat(edges).var[0]
        sharpness = variance / (variance + 100.0)
        edge_factor = 0.5 if touches_edge else 1.0
        return detected.confidence * math.sqrt(area_ratio) * (0.5 + 0.5 * sharpness) * edge_factor

    def _save_annotated(self, observation: DetectionObservation, candidate_id: str, output_path: Path) -> None:
        with Image.open(observation.frame_path) as source:
            image = source.convert("RGB")
        draw = ImageDraw.Draw(image)
        bbox = tuple(observation.detected_object.bbox)
        draw.rectangle(bbox, outline=(220, 45, 45), width=4)
        label = f"{observation.detected_object.label}  {candidate_id}"
        text_box = draw.textbbox((bbox[0], bbox[1]), label)
        text_height = text_box[3] - text_box[1]
        text_top = max(0, bbox[1] - text_height - 8)
        draw.rectangle((bbox[0], text_top, bbox[0] + text_box[2] - text_box[0] + 8, bbox[1]), fill=(220, 45, 45))
        draw.text((bbox[0] + 4, text_top + 2), label, fill="white")
        image.save(output_path, quality=92)

    def _open_crop(self, observation: DetectionObservation) -> Image.Image:
        if observation.has_crop:
            with Image.open(observation.crop_path) as crop:
                return crop.convert("RGB")
        with Image.open(observation.frame_path) as frame:
            return frame.convert("RGB").crop(tuple(observation.detected_object.bbox))


def _normalize(vector: list[float]) -> list[float]:
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude <= 1e-12:
        raise ValueError("Cannot normalize an empty CLIP embedding")
    return [value / magnitude for value in vector]


def _dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))
