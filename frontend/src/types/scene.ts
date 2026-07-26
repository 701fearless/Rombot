export type Vector3 = [number, number, number]

export interface EstimatedDimensions { widthM: number; depthM: number; heightM: number; unit: string; source: string; isMeasured: boolean }
export interface DetectedObject {
  id: string
  label: string
  name: string
  confidence: number
  bbox: [number, number, number, number]
  tagPosition: [number, number]
  cropUrl?: string | null
  deduplicatedObjectId?: string | null
  deduplicatedCropUrl?: string | null
  prebuiltGlbUrl?: string | null
  estimatedDimensions?: EstimatedDimensions | null
  visualFeatures?: Record<string, unknown>
}
export interface DetectResponse { frameId: string; frameImageUrl?: string | null; objects: DetectedObject[] }
export interface PrebuiltAsset { frameId: string; objectId: string; label: string; name: string; deduplicatedObjectId: string; glbUrl: string; previewUrl: string; estimatedDimensions?: EstimatedDimensions | null }
export interface SnapshotSource { type: 'feed' | 'preset' | 'upload' | 'library'; videoId?: string; time?: number; frameId?: string; objectId?: string }
export interface SnapshotObject {
  instanceId: string
  source: SnapshotSource
  semantic: { label: string; name: string; category: string; colors: string[]; materials: string[]; styles: string[]; functions: string[] }
  geometry: { size: Vector3; effectiveSize?: Vector3 | null; glbUrl?: string | null; cropUrl?: string | null }
  transform: { position: Vector3; rotation: Vector3; scale: Vector3 }
  placement: { isExisting: boolean; locked: boolean; zone: string; surface?: 'floor' | 'wall' | 'object'; supportObjectId?: string | null }
}
export interface SnapshotWall { id: string; start: [number, number]; end: [number, number]; height: number; thickness?: number; [key: string]: unknown }
export interface SceneSnapshot {
  schemaVersion: '1.0'; snapshotId: string; revision: number; sceneId: string; unit: 'meter'; coordinateSystem: 'threejs-xz-ground-y-up'
  room: { name: string; whiteboxGlbUrl: string; floorPolygon: [number, number][]; walls: SnapshotWall[]; openings: Array<Record<string, unknown>> }
  objects: SnapshotObject[]; userContext: Record<string, unknown>; updatedAt: string
}
export interface PendingFeedAsset { videoId: string; time: number; frameId: string; detected: DetectedObject; prebuilt: PrebuiltAsset }
export interface FurnitureMove { objectId: string; name: string; fromPosition: Vector3; toPosition: Vector3; fromRotation?: Vector3 | null; toRotation?: Vector3 | null; reason: string; source: 'mock' | 'geometry' | 'layout_agent' }
export interface LayoutAdviceItem { id: string; priority: '高' | '中' | '低'; title: string; problem: string; suggestion: string; relatedObjectIds: string[] }
export interface RoomLayoutAdvice { mode: 'room'; overallStatus: 'pass' | 'fail' | 'warn'; objectChecks: unknown[]; feedback: string; layout: { moves: FurnitureMove[]; advices: LayoutAdviceItem[]; summary: string }; scenarioOptions: unknown[] }
export type SkillAdviceScenario = 'children' | 'pets' | 'fengshui' | 'other'
export interface SkillAdviceSuggestion { id: string; priority: string; title: string; reason: string; action: string; relatedObjectIds: string[] }
export interface SkillAdviceResponse {
  scenarioId: SkillAdviceScenario; scenarioName: string; skillName: string; provider: string; model: string
  summary: string; suggestions: SkillAdviceSuggestion[]; missingFields: string[]; followUpQuestions: string[]; generatedAt: string
}
export interface UploadedFurniture { id: string; name: string; glbUrl: string; sizeBytes: number; uploadedAt: string }
export interface GeneratedFurniture {
  id: string
  videoId: string
  candidateId: string
  representativeFrameId: string
  representativeObjectId: string
  label: string
  category: string
  name: string
  previewUrl: string
  glbUrl: string
  sizeBytes: number
  estimatedDimensions?: EstimatedDimensions | null
}
export interface PendingFeedAsset { videoId: string; time: number; frameId: string; detected: DetectedObject; prebuilt: PrebuiltAsset }
export interface FurnitureMove { objectId: string; name: string; fromPosition: Vector3; toPosition: Vector3; fromRotation?: Vector3 | null; toRotation?: Vector3 | null; reason: string; source: 'mock' | 'geometry' | 'layout_agent' }
export interface LayoutAdviceItem { id: string; priority: '高' | '中' | '低'; title: string; problem: string; suggestion: string; relatedObjectIds: string[] }
export interface RoomLayoutAdvice { mode: 'room'; overallStatus: 'pass' | 'fail' | 'warn'; objectChecks: unknown[]; feedback: string; layout: { moves: FurnitureMove[]; advices: LayoutAdviceItem[]; summary: string }; scenarioOptions: unknown[] }
export interface UploadedFurniture { id: string; name: string; glbUrl: string; sizeBytes: number; uploadedAt: string }
