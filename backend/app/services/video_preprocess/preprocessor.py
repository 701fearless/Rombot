from pathlib import Path

from app.schemas import DetectRequest, DetectedObject, VideoAnalysis, VideoAnalysisFrame, VideoPreprocessRequest
from app.services.detection.grounded_sam2_provider import GroundedSAM2DetectionProvider
from app.services.detection.mock_provider import MockDetectionProvider
from app.services.segmentation.mock_provider import MockSegmentationProvider
from app.services.video_preprocess.doubao_grounding_sam_pipeline import DoubaoGroundingSamPipeline
from app.services.video_preprocess.analysis_store import video_output_dir, write_analysis
from app.services.video_preprocess.extractor import extract_frames
from app.storage.local_store import file_to_data_url, path_to_output_url


class VideoPreprocessor:
    def __init__(
        self,
        grounded_sam2_provider: GroundedSAM2DetectionProvider | None = None,
        doubao_grounding_sam_pipeline: DoubaoGroundingSamPipeline | None = None,
    ) -> None:
        self.grounded_sam2_provider = grounded_sam2_provider
        self.doubao_grounding_sam_pipeline = doubao_grounding_sam_pipeline

    async def preprocess(self, request: VideoPreprocessRequest) -> VideoAnalysis:
        output_dir = video_output_dir(request.videoId)
        frame_dir = output_dir / "frames"
        allow_placeholder = request.mode in {"mock", "manual"}
        frame_paths = extract_frames(
            video_url=request.videoUrl,
            output_dir=frame_dir,
            sample_interval_sec=request.sampleIntervalSec,
            max_frames=request.maxFrames,
            allow_placeholder=allow_placeholder,
        )

        frames: list[VideoAnalysisFrame] = []
        for index, (frame_path, timestamp) in enumerate(frame_paths, start=1):
            frame_id = f"{request.videoId}_{index:06d}"
            objects = await self._detect_frame(request, frame_id, frame_path, timestamp)
            frames.append(
                VideoAnalysisFrame(
                    frameId=frame_id,
                    time=timestamp,
                    frameImageUrl=path_to_output_url(frame_path),
                    objects=objects,
                )
            )

        analysis = VideoAnalysis(
            videoId=request.videoId,
            status="succeeded",
            sampleIntervalSec=request.sampleIntervalSec,
            frames=frames,
        )
        write_analysis(analysis)
        return analysis

    async def _detect_frame(
        self,
        request: VideoPreprocessRequest,
        frame_id: str,
        frame_path: Path,
        timestamp: float,
    ) -> list[DetectedObject]:
        frame_data_url = file_to_data_url(frame_path)
        detect_request = DetectRequest(videoId=request.videoId, time=timestamp, frameImage=frame_data_url)

        if request.mode == "grounded_sam2" and self.grounded_sam2_provider:
            response = await self.grounded_sam2_provider.detect(detect_request)
            objects = response.objects
        elif request.mode == "doubao_grounding_sam" and self.doubao_grounding_sam_pipeline:
            return await self.doubao_grounding_sam_pipeline.process_frame(frame_id, frame_path, frame_data_url)
        elif request.mode in {"mock", "manual"}:
            response = await MockDetectionProvider().detect(detect_request)
            objects = response.objects
        else:
            raise ValueError(f"Unsupported preprocess mode: {request.mode}")

        normalized_objects: list[DetectedObject] = []
        segmentation_provider = MockSegmentationProvider()
        for item in objects:
            object_id = self._normalize_object_id(item.id, len(normalized_objects) + 1)
            detected = item.model_copy(update={"id": object_id})
            if not detected.cropUrl or not detected.maskUrl:
                segmentation = await segmentation_provider.segment(
                    frame_id=frame_id,
                    detected_object=detected,
                    frame_image_path=frame_path,
                    frame_image_data_url=frame_data_url,
                )
                detected = detected.model_copy(update={"cropUrl": segmentation.cropUrl, "maskUrl": segmentation.maskUrl})
            normalized_objects.append(detected)
        return normalized_objects

    def _normalize_object_id(self, raw_id: str, index: int) -> str:
        label_part = raw_id
        if raw_id.startswith("obj_"):
            label_part = raw_id[4:]
        return f"obj_{label_part}_{index:03d}"
