from app.schemas import DetectRequest, DetectResponse, DetectedObject
from app.services.detection.base import DetectionProvider
from app.storage.local_store import load_detected_object


def _frame_id(video_id: str, timestamp: float) -> str:
    normalized_time = f"{timestamp:.2f}".replace(".", "_")
    return f"frame_{video_id}_{normalized_time}"


MOCK_OBJECTS: list[DetectedObject] = [
    DetectedObject(
        id="obj_sofa_001",
        label="sofa",
        name="沙发",
        confidence=0.91,
        bbox=[118, 420, 690, 850],
        tagPosition=[0.43, 0.61],
    ),
    DetectedObject(
        id="obj_chandelier_001",
        label="chandelier",
        name="吊灯",
        confidence=0.84,
        bbox=[350, 80, 520, 230],
        tagPosition=[0.52, 0.18],
    ),
    DetectedObject(
        id="obj_coffee_table_001",
        label="coffee_table",
        name="茶几",
        confidence=0.78,
        bbox=[260, 700, 580, 910],
        tagPosition=[0.45, 0.76],
    ),
    DetectedObject(
        id="obj_rug_001",
        label="rug",
        name="地毯",
        confidence=0.73,
        bbox=[190, 760, 760, 1030],
        tagPosition=[0.50, 0.84],
    ),
]


class MockDetectionProvider(DetectionProvider):
    async def detect(self, request: DetectRequest) -> DetectResponse:
        return DetectResponse(frameId=_frame_id(request.videoId, request.time), objects=MOCK_OBJECTS)

    async def get_object(self, frame_id: str, object_id: str) -> DetectedObject | None:
        stored_object = load_detected_object(frame_id, object_id)
        if stored_object:
            return stored_object
        return next((item for item in MOCK_OBJECTS if item.id == object_id), None)
