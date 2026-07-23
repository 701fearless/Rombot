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
    visualFeatures: dict = Field(default_factory=dict)
    generationHints: dict = Field(default_factory=dict)


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
