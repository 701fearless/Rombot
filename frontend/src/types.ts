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
