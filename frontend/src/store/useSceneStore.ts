import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import type { PendingFeedAsset, SceneSnapshot, SnapshotObject } from '@/types/scene'
import { browserStorage } from '@/utils/persist'

interface SceneState {
  activeSceneId: string
  snapshot: SceneSnapshot | null
  pendingAsset: PendingFeedAsset | null
  selectedInstanceId: string
  saveMode: 'server' | 'local'
  setActiveSceneId: (sceneId: string) => void
  setSnapshot: (snapshot: SceneSnapshot) => void
  setPendingAsset: (asset: PendingFeedAsset | null) => void
  setSelectedInstanceId: (id: string) => void
  setSaveMode: (mode: 'server' | 'local') => void
  upsertObject: (object: SnapshotObject) => void
  updateObject: (id: string, transform: SnapshotObject['transform']) => void
}

export const useSceneStore = create<SceneState>()(persist((set) => ({
  activeSceneId: 'room6', snapshot: null, pendingAsset: null, selectedInstanceId: '', saveMode: 'server',
  setActiveSceneId: (activeSceneId) => set({ activeSceneId }),
  setSnapshot: (snapshot) => set({ snapshot }),
  setPendingAsset: (pendingAsset) => set({ pendingAsset }),
  setSelectedInstanceId: (selectedInstanceId) => set({ selectedInstanceId }),
  setSaveMode: (saveMode) => set({ saveMode }),
  upsertObject: (object) => set((state) => {
    if (!state.snapshot) return state
    const exists = state.snapshot.objects.some((item) => item.instanceId === object.instanceId)
    return { snapshot: { ...state.snapshot, updatedAt: new Date().toISOString(), objects: exists ? state.snapshot.objects.map((item) => item.instanceId === object.instanceId ? object : item) : [...state.snapshot.objects, object] } }
  }),
  updateObject: (id, transform) => set((state) => state.snapshot ? ({ snapshot: { ...state.snapshot, updatedAt: new Date().toISOString(), objects: state.snapshot.objects.map((item) => item.instanceId === id ? { ...item, transform } : item) } }) : state),
}), { name: 'store_scene_snapshot', storage: createJSONStorage(() => browserStorage) }))
