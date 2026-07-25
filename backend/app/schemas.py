import math

from pydantic import BaseModel, Field, field_validator


class EstimatedDimensions(BaseModel):
    widthM: float = Field(gt=0, le=20)
    depthM: float = Field(gt=0, le=20)
    heightM: float = Field(gt=0, le=20)
    unit: str = "m"
    source: str = "ark_category_prior"
    isMeasured: bool = False
    selectionRule: str = "range_min_plus_0.10m_capped_at_max"


class DetectedObject(BaseModel):
    id: str
    label: str
    name: str
    confidence: float = Field(ge=0, le=1)
    bbox: list[int] = Field(min_length=4, max_length=4)
    tagPosition: list[float] = Field(min_length=2, max_length=2)
    cropUrl: str | None = None
    maskUrl: str | None = None
    deduplicatedObjectId: str | None = None
    deduplicatedCropUrl: str | None = None
    prebuiltGlbUrl: str | None = None
    estimatedDimensions: EstimatedDimensions | None = None
    visualFeatures: dict = Field(default_factory=dict)
    generationHints: dict = Field(default_factory=dict)


class DetectRequest(BaseModel):
    videoId: str
    time: float = Field(ge=0)
    frameImage: str | None = None
    frameHash: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{16}$")


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
    estimatedDimensions: EstimatedDimensions | None = None
    glbUrl: str


class ObjectAnalysis(BaseModel):
    summary: str
    placementAdvice: str


class GenerationArtifact(BaseModel):
    type: str
    url: str | None = None
    path: str | None = None
    note: str | None = None


class FurnitureGenerationBrief(BaseModel):
    objectId: str
    category: str
    observed: dict = Field(default_factory=dict)
    inferred: dict = Field(default_factory=dict)
    symmetryPrior: dict = Field(default_factory=dict)
    textureFeatures: dict = Field(default_factory=dict)
    constraints: dict = Field(default_factory=dict)
    prompt: str
    negativePrompt: str
    confidence: dict = Field(default_factory=dict)


class FurnitureGenerationTrace(BaseModel):
    briefUrl: str | None = None
    sourceImageUrl: str | None = None
    referenceImages: list[GenerationArtifact] = Field(default_factory=list)
    textureReferences: list[GenerationArtifact] = Field(default_factory=list)
    provider: str
    notes: list[str] = Field(default_factory=list)


class SelectObjectResponse(BaseModel):
    taskId: str
    status: str
    object: SelectedAsset
    analysis: ObjectAnalysis
    generation: FurnitureGenerationTrace | None = None


class PrebuiltAssetResponse(BaseModel):
    frameId: str
    objectId: str
    label: str
    name: str
    deduplicatedObjectId: str
    glbUrl: str
    estimatedDimensions: EstimatedDimensions | None = None


class MockProductSearchRequest(BaseModel):
    objectId: str
    label: str
    name: str | None = None
    estimatedDimensions: EstimatedDimensions | None = None


class ProductMatch(BaseModel):
    productId: str
    name: str
    category: str
    score: float = Field(ge=0, le=1)
    priceCny: int = Field(gt=0)
    sizeText: str
    reason: str


class ProductSearchResponse(BaseModel):
    objectId: str
    queryLabel: str
    source: str = "mock_catalog"
    isMock: bool = True
    matches: list[ProductMatch] = Field(default_factory=list)


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
    maxFrames: int | None = Field(default=None, gt=0, le=120)
    reuseExistingFrames: bool = False


class VideoAnalysisFrame(BaseModel):
    frameId: str
    time: float = Field(ge=0)
    frameImageUrl: str
    objects: list[DetectedObject]
    perceptualHash: str | None = None


class DeduplicatedObject(BaseModel):
    id: str
    label: str
    name: str
    representativeFrameId: str
    representativeObjectId: str
    annotatedImageUrl: str
    cropUrl: str
    maskUrl: str | None = None
    bbox: list[int] = Field(min_length=4, max_length=4)
    confidence: float = Field(ge=0, le=1)
    duplicateCount: int = Field(ge=1)
    estimatedDimensions: EstimatedDimensions | None = None


class VideoAnalysis(BaseModel):
    videoId: str
    status: str
    sampleIntervalSec: float
    frames: list[VideoAnalysisFrame]
    deduplicatedObjects: list[DeduplicatedObject] = Field(default_factory=list)
    dedupeWarning: str | None = None


class VideoPreprocessResponse(BaseModel):
    videoId: str
    status: str
    frameCount: int
    detectedObjectCount: int = 0
    deduplicatedObjectCount: int = 0
    analysisUrl: str


class VideoUploadResponse(BaseModel):
    videoId: str
    fileName: str
    videoUrl: str
    sizeBytes: int = Field(ge=1)


class ManualFrameSaveRequest(BaseModel):
    videoId: str
    sourceFileName: str
    durationSec: float = Field(gt=0)
    timeSec: float = Field(ge=0)
    frameImage: str


class ManualFrameItem(BaseModel):
    timeSec: float = Field(ge=0)
    timeMs: int = Field(ge=0)
    fileName: str
    imageUrl: str


class ManualFramesResponse(BaseModel):
    videoId: str
    sourceFileName: str | None = None
    durationSec: float | None = None
    samplingMode: str | None = None
    frames: list[ManualFrameItem] = Field(default_factory=list)


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


class UserProfile(BaseModel):
    """Optional lifestyle context for multi-agent advice."""

    familyMembers: list[str] = Field(default_factory=list)
    hasChildren: bool = False
    hasElderly: bool = False
    pets: list[str] = Field(default_factory=list)
    dailyHabits: list[str] = Field(default_factory=list)
    storageHabits: str | None = None
    fengShuiPreference: bool = False
    preferPrivacy: bool = True
    preferComfort: bool = True


class SpatialCheckRequest(BaseModel):
    """拖拽落位后的基础空间可行性检测请求（兼容旧名）。"""

    candidate: PlacementCandidate
    sceneId: str | None = None
    scene: SceneResponse | None = None
    userProfile: UserProfile | None = None
    enableAgents: bool = True


# 单家具摆放模式
PlacementCheckRequest = SpatialCheckRequest


class RoomLayoutRequest(BaseModel):
    """全屋布局优化请求（不绑定单件家具）。"""

    sceneId: str | None = None
    scene: SceneResponse | None = None
    userProfile: UserProfile | None = None
    enableAgents: bool = True


class CheckDetail(BaseModel):
    ruleId: str
    name: str
    status: str  # pass | fail | warn
    message: str
    suggestion: str | None = None
    details: dict = Field(default_factory=dict)


class ObjectCheckBundle(BaseModel):
    """全屋模式下单件家具的几何检测摘要。"""

    objectId: str
    name: str
    label: str
    overallStatus: str
    checks: list[CheckDetail] = Field(default_factory=list)


class FurnitureMove(BaseModel):
    """建议移动后的家具位姿（米）。"""

    objectId: str
    name: str
    fromPosition: list[float] = Field(min_length=3, max_length=3)
    toPosition: list[float] = Field(min_length=3, max_length=3)
    fromRotation: list[float] | None = Field(default=None, min_length=3, max_length=3)
    toRotation: list[float] | None = Field(default=None, min_length=3, max_length=3)
    reason: str
    source: str = "geometry"  # geometry | layout_agent


class LayoutAdviceItem(BaseModel):
    id: str
    priority: str  # 高 | 中 | 低
    title: str
    problem: str
    suggestion: str
    relatedObjectIds: list[str] = Field(default_factory=list)


class LayoutModule(BaseModel):
    moves: list[FurnitureMove] = Field(default_factory=list)
    advices: list[LayoutAdviceItem] = Field(default_factory=list)
    summary: str = ""


class ScenarioOption(BaseModel):
    id: str  # elder | infant | pet | fengshui
    name: str
    description: str


class ScenarioAdviceItem(BaseModel):
    id: str
    scenarioId: str
    priority: str  # 高 | 中 | 低
    title: str
    reason: str
    action: str
    relatedObjectIds: list[str] = Field(default_factory=list)
    targetPosition: list[float] | None = Field(default=None, min_length=3, max_length=3)


class ScenarioAdviceRequest(BaseModel):
    """用户选择场景后的深化建议请求。"""

    scenarios: list[str] = Field(min_length=1)
    mode: str = "placement"  # placement | room
    candidate: PlacementCandidate | None = None
    sceneId: str | None = None
    scene: SceneResponse | None = None
    layout: LayoutModule | None = None
    geometryChecks: list[CheckDetail] = Field(default_factory=list)
    userProfile: UserProfile | None = None


class ScenarioAdviceResponse(BaseModel):
    selectedScenarios: list[str]
    mode: str = "placement"
    advicesByScenario: dict[str, list[ScenarioAdviceItem]] = Field(default_factory=dict)
    summary: str


class AgentSuggestionModel(BaseModel):
    id: str
    category: str
    priority: str
    title: str
    reason: str
    action: str
    confidence: float = Field(ge=0, le=1, default=0.8)


class AgentOutputModel(BaseModel):
    agent: str
    suggestions: list[AgentSuggestionModel] = Field(default_factory=list)


class ScoreDimensionsModel(BaseModel):
    layout: int = Field(ge=0, le=100)
    comfort: int = Field(ge=0, le=100)
    functionality: int = Field(ge=0, le=100)
    lifestyleCompatibility: int = Field(ge=0, le=100)


class AgentReportModel(BaseModel):
    score: int = Field(ge=0, le=100)
    scoreDimensions: ScoreDimensionsModel
    summary: str
    highlights: list[str] = Field(default_factory=list)
    suggestions: list[AgentSuggestionModel] = Field(default_factory=list)
    agentOutputs: list[AgentOutputModel] = Field(default_factory=list)


class SpatialCheckResponse(BaseModel):
    """单家具摆放检测响应（亦用于 /placement-check）。"""

    mode: str = "placement"
    overallStatus: str  # pass | fail | warn
    checks: list[CheckDetail]
    feedback: str
    layout: LayoutModule | None = None
    scenarioOptions: list[ScenarioOption] = Field(default_factory=list)
    agentReport: AgentReportModel | None = None  # debug only


PlacementCheckResponse = SpatialCheckResponse


class RoomLayoutResponse(BaseModel):
    """全屋布局优化响应。"""

    mode: str = "room"
    overallStatus: str  # pass | fail | warn
    objectChecks: list[ObjectCheckBundle] = Field(default_factory=list)
    feedback: str
    layout: LayoutModule | None = None
    scenarioOptions: list[ScenarioOption] = Field(default_factory=list)


class ProductHints(BaseModel):
    category: str
    queryTags: list[str] = Field(default_factory=list)
    recommendApi: str = "/api/product/recommend"


class ProductAttributes(BaseModel):
    color: str | None = None
    material: str | None = None
    style: str | None = None


class ProductRecognizeRequest(BaseModel):
    objectId: str | None = None
    frameId: str | None = None
    cropUrl: str | None = None
    image: str | None = None
    label: str | None = None
    sceneId: str | None = None


class ProductRecognizeResponse(BaseModel):
    category: str
    name: str
    attributes: ProductAttributes
    estimatedSize_m: list[float] = Field(min_length=3, max_length=3)
    sizeConfidence: str = "low"
    queryTags: list[str] = Field(default_factory=list)
    source: str = "mock"


class ProductRecommendItem(BaseModel):
    productId: str
    title: str
    matchType: str
    score: float = Field(ge=0, le=1)
    price: float = Field(ge=0)
    currency: str = "CNY"
    size_m: list[float] = Field(min_length=3, max_length=3)
    imageUrl: str | None = None
    glbUrl: str | None = None
    buyUrl: str | None = None
    reason: str
    sizeFit: str = "unknown"
    category: str
    tags: list[str] = Field(default_factory=list)


class ProductRecommendRequest(ProductRecognizeRequest):
    query: ProductRecognizeResponse | None = None
    budget: float | None = Field(default=None, gt=0)
    preferSame: bool = False
    limit: int = Field(default=6, ge=1, le=20)
    scene: SceneResponse | None = None
    candidate: PlacementCandidate | None = None


class ProductRecommendResponse(BaseModel):
    query: ProductRecognizeResponse
    items: list[ProductRecommendItem] = Field(default_factory=list)


class ProductRecognizeAndRecommendRequest(ProductRecommendRequest):
    pass


class ProductRecognizeAndRecommendResponse(BaseModel):
    recognition: ProductRecognizeResponse
    items: list[ProductRecommendItem] = Field(default_factory=list)


class SnapshotSource(BaseModel):
    type: str = "feed"
    videoId: str | None = None
    time: float | None = Field(default=None, ge=0)
    frameId: str | None = None
    objectId: str | None = None


class SnapshotSemantic(BaseModel):
    label: str
    name: str
    category: str
    colors: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    styles: list[str] = Field(default_factory=list)
    functions: list[str] = Field(default_factory=list)


class SnapshotGeometry(BaseModel):
    size: list[float] = Field(min_length=3, max_length=3)
    glbUrl: str | None = None
    cropUrl: str | None = None

    @field_validator("size")
    @classmethod
    def validate_size(cls, value: list[float]) -> list[float]:
        if any(not math.isfinite(item) or item <= 0 for item in value):
            raise ValueError("Furniture size values must be finite and greater than zero")
        return value


class SnapshotTransform(BaseModel):
    position: list[float] = Field(min_length=3, max_length=3)
    rotation: list[float] = Field(min_length=3, max_length=3)
    scale: list[float] = Field(min_length=3, max_length=3)

    @field_validator("position", "rotation")
    @classmethod
    def validate_finite_vector(cls, value: list[float]) -> list[float]:
        if any(not math.isfinite(item) for item in value):
            raise ValueError("Transform values must be finite")
        return value

    @field_validator("scale")
    @classmethod
    def validate_scale(cls, value: list[float]) -> list[float]:
        if any(not math.isfinite(item) or item <= 0 for item in value):
            raise ValueError("Scale values must be finite and greater than zero")
        return value


class SnapshotPlacement(BaseModel):
    isExisting: bool = False
    locked: bool = False
    zone: str = "living_area"


class SnapshotObject(BaseModel):
    instanceId: str
    source: SnapshotSource
    semantic: SnapshotSemantic
    geometry: SnapshotGeometry
    transform: SnapshotTransform
    placement: SnapshotPlacement = Field(default_factory=SnapshotPlacement)


class SnapshotRoom(BaseModel):
    name: str
    floorPolygon: list[list[float]]
    walls: list[dict] = Field(default_factory=list)
    openings: list[dict] = Field(default_factory=list)

    @field_validator("floorPolygon")
    @classmethod
    def validate_floor_polygon(cls, value: list[list[float]]) -> list[list[float]]:
        if len(value) < 3 or any(
            len(point) != 2 or any(not math.isfinite(item) for item in point)
            for point in value
        ):
            raise ValueError("floorPolygon must contain at least three finite [x, z] points")
        return value


class SceneSnapshot(BaseModel):
    schemaVersion: str = "1.0"
    snapshotId: str
    revision: int = Field(default=0, ge=0)
    sceneId: str
    unit: str = "meter"
    coordinateSystem: str = "threejs-xz-ground-y-up"
    room: SnapshotRoom
    objects: list[SnapshotObject] = Field(default_factory=list)
    userContext: UserProfile = Field(default_factory=UserProfile)
    updatedAt: str
