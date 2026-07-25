from pydantic import BaseModel, Field


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
    glbUrl: str


class SceneSuggestion(BaseModel):
    type: str
    text: str


class SceneResponse(BaseModel):
    sceneId: str
    unit: str
    room: RoomSize
    objects: list[SceneObject]
    suggestions: list[SceneSuggestion]
