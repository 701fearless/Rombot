export type SceneType = "living_room" | "bedroom" | "study" | "dining_room"

export interface FeedVideo {
  id: string
  title: string
  author: string
  videoUrl: string
  coverUrl: string
  sceneType: SceneType
  furnitureHints: string[]
}

export interface DetectedObject {
  id: string
  label: string
  name: string
  confidence: number
  bbox: [number, number, number, number]
  tagPosition: [number, number]
  cropUrl?: string | null
  maskUrl?: string | null
  deduplicatedObjectId?: string | null
  deduplicatedCropUrl?: string | null
  prebuiltGlbUrl?: string | null
  estimatedDimensions?: EstimatedDimensions | null
}

export interface EstimatedDimensions {
  widthM: number
  depthM: number
  heightM: number
  unit: string
  source: string
  isMeasured: boolean
}

export interface DetectResponse {
  frameId: string
  frameImageUrl?: string | null
  objects: DetectedObject[]
}

export interface SpaceEntryParams {
  sceneId?: string
  videoId: string
  time: string
  sceneType: SceneType
  frameId: string
  objectId: string
  objectLabel: string
}

export interface FloorplanPreset {
  sceneId: string
  title: string
  sourceImageUrl: string
  sourceSha256: string
  sceneUrl: string
  whiteboxGlbUrl: string
  quality: "placeholder" | "ark"
}

export interface PrebuiltAsset {
  frameId: string
  objectId: string
  label: string
  name: string
  deduplicatedObjectId: string
  glbUrl: string
  estimatedDimensions?: EstimatedDimensions | null
}

export interface FloorplanReconstructResponse {
  sceneId: string
  status: "succeeded"
  sceneUrl: string
  whiteboxGlbUrl: string
  aiRawUrl: string
  originalImageUrl: string
  warnings: string[]
}

export interface RoomSize {
  width: number
  depth: number
  height: number
}

export interface SceneObject {
  id: string
  label: string
  name: string
  position: [number, number, number]
  rotation: [number, number, number]
  size: [number, number, number]
  glbUrl?: string | null
}

export interface SceneOpening {
  id: string
  type: string
  name: string
  position: [number, number, number]
  rotation: [number, number, number]
  size: [number, number, number]
  clearanceDepth: number
}

export interface SceneSuggestion {
  type: string
  text: string
}

export interface SceneResponse {
  sceneId: string
  unit: string
  room: RoomSize
  objects: SceneObject[]
  openings: SceneOpening[]
  suggestions: SceneSuggestion[]
}

export interface PlacementCandidate {
  id: string
  label: string
  name: string
  position: [number, number, number]
  rotation: [number, number, number]
  size: [number, number, number]
}

export interface CheckDetail {
  ruleId: string
  name: string
  status: "pass" | "fail" | "warn" | string
  message: string
  suggestion?: string | null
  details?: Record<string, unknown>
}

export interface FurnitureMove {
  objectId: string
  name: string
  fromPosition: [number, number, number]
  toPosition: [number, number, number]
  fromRotation?: [number, number, number] | null
  toRotation?: [number, number, number] | null
  reason: string
  source: string
}

export interface LayoutModule {
  moves: FurnitureMove[]
  advices: Array<{
    id: string
    priority: string
    title: string
    problem: string
    suggestion: string
    relatedObjectIds: string[]
  }>
  summary: string
}

export interface PlacementCheckResponse {
  mode: string
  overallStatus: "pass" | "fail" | "warn" | string
  checks: CheckDetail[]
  feedback: string
  layout: LayoutModule | null
  scenarioOptions: Array<{ id: string; name: string; description: string }>
}

export interface FurnitureLayoutPose {
  objectId: string
  position: [number, number, number]
  rotation: [number, number, number]
  size: [number, number, number]
}

export interface FurnitureTransformChange {
  objectId: string
  position: [number, number, number]
  rotation: [number, number, number]
  size: [number, number, number]
  reason: "drag" | "rotate" | "scale" | "reset" | "apply"
}
