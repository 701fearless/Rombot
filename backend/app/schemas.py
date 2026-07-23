from pydantic import BaseModel, Field


class DetectedObject(BaseModel):
    id: str
    label: str
    name: str
    confidence: float = Field(ge=0, le=1)
    bbox: list[int] = Field(min_length=4, max_length=4)
    tagPosition: list[float] = Field(min_length=2, max_length=2)
    cropUrl: str | None = None
    maskUrl: str | None = None


class DetectRequest(BaseModel):
    videoId: str
    time: float = Field(ge=0)
    frameImage: str | None = None


class DetectResponse(BaseModel):
    frameId: str
    objects: list[DetectedObject]
    frameImageUrl: str | None = None


class SelectObjectRequest(BaseModel):
    frameId: str
    objectId: str
    frameImage: str | None = None
    imageUrl: str | None = None
    cropImage: str | None = None


class SegmentationResult(BaseModel):
    frameId: str
    objectId: str
    cropUrl: str
    maskUrl: str
    cropImage: str | None = None


class SelectedAsset(BaseModel):
    id: str
    label: str
    name: str
    bbox: list[int] = Field(min_length=4, max_length=4)
    cropUrl: str | None = None
    maskUrl: str | None = None
    glbUrl: str


class ObjectAnalysis(BaseModel):
    summary: str
    placementAdvice: str


class SelectObjectResponse(BaseModel):
    taskId: str
    status: str
    object: SelectedAsset
    analysis: ObjectAnalysis


class FeedPipelineRequest(BaseModel):
    videoId: str
    time: float = Field(ge=0)
    frameImage: str
    objectId: str | None = None


class FeedPipelineResponse(BaseModel):
    detection: DetectResponse
    selected: SelectObjectResponse


class DebugImagePipelineRequest(BaseModel):
    imagePath: str = "/sample_data/videos/sample.png"
    objectIndex: int = Field(default=0, ge=0)


class VideoPreprocessRequest(BaseModel):
    videoId: str
    videoUrl: str | None = None
    sampleIntervalSec: float = Field(default=1.0, gt=0)
    mode: str = "mock"
    maxFrames: int = Field(default=6, gt=0, le=120)


class VideoAnalysisFrame(BaseModel):
    frameId: str
    time: float = Field(ge=0)
    frameImageUrl: str
    objects: list[DetectedObject]


class VideoAnalysis(BaseModel):
    videoId: str
    status: str
    sampleIntervalSec: float
    frames: list[VideoAnalysisFrame]


class VideoPreprocessResponse(BaseModel):
    videoId: str
    status: str
    frameCount: int
    analysisUrl: str


class RoomScanRequest(BaseModel):
    scanId: str | None = None


class RoomSize(BaseModel):
    width: float
    depth: float
    height: float


class SceneObject(BaseModel):
    id: str
    label: str
    name: str
    position: list[float] = Field(min_length=3, max_length=3)
    rotation: list[float] = Field(min_length=3, max_length=3)
    size: list[float] = Field(min_length=3, max_length=3)
    glbUrl: str | None = None


class SceneOpening(BaseModel):
    """门/窗开口。position 为开口中心，size 为 [宽, 高, 进深]。"""

    id: str
    type: str  # door | window
    name: str
    position: list[float] = Field(min_length=3, max_length=3)
    rotation: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0], min_length=3, max_length=3)
    size: list[float] = Field(min_length=3, max_length=3)
    # 门开启/窗前净空区域深度（米），沿开口朝向房间内侧延伸
    clearanceDepth: float = 0.9


class SceneSuggestion(BaseModel):
    type: str
    text: str


class SceneResponse(BaseModel):
    sceneId: str
    unit: str
    room: RoomSize
    objects: list[SceneObject]
    openings: list[SceneOpening] = Field(default_factory=list)
    suggestions: list[SceneSuggestion]


class PlacementCandidate(BaseModel):
    """待检测的家具摆放姿态。position 为包围盒中心，size 为 [宽, 高, 深]（米）。"""

    id: str
    label: str
    name: str
    position: list[float] = Field(min_length=3, max_length=3)
    rotation: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0], min_length=3, max_length=3)
    size: list[float] = Field(min_length=3, max_length=3)


class SpatialCheckRequest(BaseModel):
    """拖拽落位后的基础空间可行性检测请求。"""

    candidate: PlacementCandidate
    sceneId: str | None = None
    scene: SceneResponse | None = None


class CheckDetail(BaseModel):
    ruleId: str
    name: str
    status: str  # pass | fail | warn
    message: str
    suggestion: str | None = None
    details: dict = Field(default_factory=dict)


class SpatialCheckResponse(BaseModel):
    overallStatus: str  # pass | fail | warn
    checks: list[CheckDetail]
    feedback: str
