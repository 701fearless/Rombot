// ============================================================
// 资产池 store：识别即落库（PRD ★锚点1，资产随人走，退出不丢）
// ============================================================

import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import type { Asset, Furniture, ID } from '@/types/models'
import { mockFurniture } from '@/mock'
import { taroStorage } from '@/utils/persist'

/** Asset 关联 SKU 库家具信息后的视图类型 */
export type AssetWithFurniture = Asset & { furniture: Furniture | undefined }

interface AssetState {
  assets: Asset[]
  /** 识别完成立即落库（绑 ownerId），此后退出不丢 */
  addAsset: (a: Asset) => void
  /** 状态机流转：recognized → placed（下单已随比价线下线） */
  updateAssetStatus: (id: ID, status: Asset['status']) => void
  /** 取资产并关联 mock 家具信息（展示用） */
  getAssetWithFurniture: (id: ID) => AssetWithFurniture | undefined
}

export const useAssetStore = create<AssetState>()(
  persist(
    (set, get) => ({
      assets: [],
      addAsset: (a) => set((state) => ({ assets: [...state.assets, a] })),
      updateAssetStatus: (id, status) =>
        set((state) => ({
          assets: state.assets.map((a) => (a.id === id ? { ...a, status } : a)),
        })),
      getAssetWithFurniture: (id) => {
        const asset = get().assets.find((a) => a.id === id)
        if (!asset) return undefined
        return { ...asset, furniture: mockFurniture.find((f) => f.id === asset.furnitureId) }
      },
    }),
    {
      name: 'store_assets',
      storage: createJSONStorage(() => taroStorage),
    },
  ),
)
