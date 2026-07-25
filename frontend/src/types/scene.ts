export interface EstimatedDimensions {
  widthM: number
  depthM: number
  heightM: number
  unit: string
  source: string
  isMeasured: boolean
}

export interface DetectedObject {
  id: string
  label: string
  name: string
  confidence: number
  bbox: [number, number, number, number]
  tagPosition: [number, number]
  cropUrl?: string | null
  prebuiltGlbUrl?: string | null
  estimatedDimensions?: EstimatedDimensions | null
  visualFeatures?: Record<string, unknown>
}

export interface DetectResponse {
  frameId: string
  frameImageUrl?: string | null
  objects: DetectedObject[]
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

export interface SnapshotSource {
  type: 'feed' | 'preset'
  videoId?: string
  time?: number
  frameId?: string
  objectId?: string
}

export interface SnapshotObject {
  instanceId: string
  source: SnapshotSource
  semantic: {
    label: string
    name: string
    category: string
    colors: string[]
    materials: string[]
    styles: string[]
    functions: string[]
  }
  geometry: {
    size: [number, number, number]
    glbUrl?: string | null
    cropUrl?: string | null
  }
  transform: {
    position: [number, number, number]
    rotation: [number, number, number]
    scale: [number, number, number]
  }
  placement: {
    isExisting: boolean
    locked: boolean
    zone: string
  }
}

export interface SceneSnapshot {
  schemaVersion: '1.0'
  snapshotId: string
  revision: number
  sceneId: string
  unit: 'meter'
  coordinateSystem: 'threejs-xz-ground-y-up'
  room: {
    name: string
    floorPolygon: [number, number][]
    walls: Array<Record<string, unknown>>
    openings: Array<Record<string, unknown>>
  }
  objects: SnapshotObject[]
  userContext: Record<string, unknown>
  updatedAt: string
}

export interface PendingFeedAsset {
  videoId: string
  time: number
  frameId: string
  detected: DetectedObject
  prebuilt: PrebuiltAsset
}

export interface FurnitureMove {
  objectId: string
  name: string
  fromPosition: [number, number, number]
  toPosition: [number, number, number]
  fromRotation: [number, number, number]
  toRotation: [number, number, number]
  reason: string
  source: 'mock'
}

export interface LayoutAdviceItem {
  id: string
  priority: '高' | '中' | '低'
  title: string
  problem: string
  suggestion: string
  relatedObjectIds: string[]
}

export interface RoomLayoutAdvice {
  mode: 'room'
  overallStatus: 'warn'
  objectChecks: unknown[]
  feedback: string
  layout: {
    moves: FurnitureMove[]
    advices: LayoutAdviceItem[]
    summary: string
  }
  scenarioOptions: unknown[]
}
