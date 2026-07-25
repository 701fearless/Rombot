// ============================================================
// 「我的家」store：房屋 / 房间 / 摆放（PRD 铁律：产物写 store + Storage）
// ============================================================

import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import type { Home, ID, Placement, Room } from '@/types/models'
import { mockHomes, mockPlacements, mockRooms } from '@/mock'
import { taroStorage } from '@/utils/persist'

interface HomeState {
  homes: Home[]
  rooms: Room[]
  placements: Placement[]
  /** 三入口建房/选房（new/old/template） */
  addHome: (h: Home) => void
  /** 摆放/替换流产物落库（含整屋补全的批量 Placement，循环调用即可） */
  addPlacement: (p: Placement) => void
  /** 移除摆放；旧房"移除旧家具"= 删 isExisting=true 的 Placement（PRD 4 设计意图 2） */
  removePlacement: (id: ID) => void
  /** 拖拽结束后更新坐标/旋转/缩放 */
  updatePlacement: (id: ID, transform: Placement['transform']) => void
}

export const useHomeStore = create<HomeState>()(
  persist(
    (set) => ({
      // 初始从 mock 灌入（首启动播种；之后以 Storage 持久化数据为准）
      homes: mockHomes,
      rooms: mockRooms,
      placements: mockPlacements,
      addHome: (h) => set((state) => ({ homes: [...state.homes, h] })),
      addPlacement: (p) => set((state) => ({ placements: [...state.placements, p] })),
      removePlacement: (id) =>
        set((state) => ({ placements: state.placements.filter((p) => p.id !== id) })),
      updatePlacement: (id, transform) =>
        set((state) => ({
          placements: state.placements.map((p) => (p.id === id ? { ...p, transform } : p)),
        })),
    }),
    {
      name: 'store_home',
      storage: createJSONStorage(() => taroStorage),
    },
  ),
)
