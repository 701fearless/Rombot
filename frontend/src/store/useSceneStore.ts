import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import type { GeneratedFurniture, PendingFeedAsset, SceneSnapshot, SnapshotObject } from '@/types/scene'
import type { ShopProduct } from '@/types/shop'
import { browserStorage } from '@/utils/persist'

export interface FurnitureLibraryPreview {
  item: GeneratedFurniture
  product?: ShopProduct | null
}

interface SceneState {
  activeSceneId: string
  snapshot: SceneSnapshot | null
  pendingAsset: PendingFeedAsset | null
  furnitureLibraryPreview: FurnitureLibraryPreview | null
  furnitureLibrary: GeneratedFurniture[]
  selectedInstanceId: string
  saveMode: 'server' | 'local'
  setActiveSceneId: (sceneId: string) => void
  setSnapshot: (snapshot: SceneSnapshot) => void
  setPendingAsset: (asset: PendingFeedAsset | null) => void
  setFurnitureLibraryPreview: (preview: FurnitureLibraryPreview | null) => void
  addFurnitureToLibrary: (item: GeneratedFurniture) => void
  removeFurnitureFromLibrary: (id: string) => void
  setSelectedInstanceId: (id: string) => void
  setSaveMode: (mode: 'server' | 'local') => void
  upsertObject: (object: SnapshotObject) => void
  updateObject: (id: string, transform: SnapshotObject['transform']) => void
}

export const useSceneStore = create<SceneState>()(persist((set) => ({
  activeSceneId: 'room1', snapshot: null, pendingAsset: null, furnitureLibraryPreview: null, furnitureLibrary: [], selectedInstanceId: '', saveMode: 'server',
  setActiveSceneId: (activeSceneId) => set({ activeSceneId }),
  setSnapshot: (snapshot) => set({ snapshot }),
  setPendingAsset: (pendingAsset) => set({ pendingAsset }),
  setFurnitureLibraryPreview: (furnitureLibraryPreview) => set({ furnitureLibraryPreview }),
  addFurnitureToLibrary: (item) => set((state) => ({
    furnitureLibrary: state.furnitureLibrary.some((candidate) => candidate.id === item.id)
      ? state.furnitureLibrary.map((candidate) => candidate.id === item.id ? item : candidate)
      : [item, ...state.furnitureLibrary],
  })),
  removeFurnitureFromLibrary: (id) => set((state) => ({
    furnitureLibrary: state.furnitureLibrary.filter((item) => item.id !== id),
  })),
  setSelectedInstanceId: (selectedInstanceId) => set({ selectedInstanceId }),
  setSaveMode: (saveMode) => set({ saveMode }),
  upsertObject: (object) => set((state) => {
    if (!state.snapshot) return state
    const exists = state.snapshot.objects.some((item) => item.instanceId === object.instanceId)
    return { snapshot: { ...state.snapshot, updatedAt: new Date().toISOString(), objects: exists ? state.snapshot.objects.map((item) => item.instanceId === object.instanceId ? object : item) : [...state.snapshot.objects, object] } }
  }),
  updateObject: (id, transform) => set((state) => state.snapshot ? ({ snapshot: { ...state.snapshot, updatedAt: new Date().toISOString(), objects: state.snapshot.objects.map((item) => item.instanceId === id ? { ...item, transform } : item) } }) : state),
}), {
  name: 'store_scene_snapshot_v2',
  version: 5,
  storage: createJSONStorage(() => browserStorage),
  migrate: (persisted) => {
    const state = persisted as Partial<SceneState>
    const snapshot = state.snapshot?.sceneId === 'room1' || state.snapshot?.sceneId === 'room2' ? state.snapshot : null
    const furnitureLibrary = (state.furnitureLibrary ?? []).map((item) => {
      const isLegacyCrop = /\/(?:deduplicated|frames?)\/|crop\.(?:png|jpe?g|webp)(?:$|\?)/i.test(item.previewUrl)
      return isLegacyCrop && item.videoId && item.candidateId
        ? { ...item, previewUrl: `/outputs/videos/${item.videoId}/generated/${item.candidateId}/reference_oblique_3quarter.png` }
        : item
    })
    return { ...state, activeSceneId: state.activeSceneId === 'room2' ? 'room2' : 'room1', snapshot, furnitureLibrary }
  },
}))
