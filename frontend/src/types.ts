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
}

export interface DetectResponse {
  frameId: string
  frameImageUrl?: string | null
  objects: DetectedObject[]
}

export interface SpaceEntryParams {
  videoId: string
  time: string
  sceneType: SceneType
  frameId: string
  objectId: string
  objectLabel: string
}
