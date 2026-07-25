// Tab2 我的家：常驻资产池（PRD 架构决策 2，留存核心）
// 结构（2026-07-25 修订）：
//   房屋选择条（一行收起，点开展开选取后收起）→ 方形 3D 空间展开（2D 贴图占位）
//   → 拖拽提示词 + 平铺横滑家具资产库 → AI 建议（黄底蓝字，整行）
//   → 空间资产库（从「设计」Tab 挪入，替代原方案清单；点模板空间进摆放流）
import { Text, View } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { useMemo, useState } from 'react'
import AppHeader from '@/components/AppHeader'
import CoverImage from '@/components/CoverImage'
import DouyinLinkSheet from '@/components/DouyinLinkSheet'
import FurnitureLibrary from '@/components/FurnitureLibrary'
import SectionTitle from '@/components/SectionTitle'
import { mockAssets, mockFurniture } from '@/mock'
import { useAssetStore, useHomeStore } from '@/store'
import type { Home, Placement } from '@/types/models'
import { genId } from '@/utils/id'
// 方形画布底图：AI 生成单房间 3D 效果图（import 引用才会被 webpack 打包进 dist）
import space3dImg from '@/assets/space-3d-living.png'
import './index.scss'

export default function MyHomePage() {
  const { homes, rooms, placements, addPlacement, removePlacement, updatePlacement } =
    useHomeStore()
  const { assets } = useAssetStore()

  const [currentHomeId, setCurrentHomeId] = useState(homes[0]?.id ?? '')
  const [currentRoomId, setCurrentRoomId] = useState('')
  const [homesExpanded, setHomesExpanded] = useState(false)
  const [editingFullscreen, setEditingFullscreen] = useState(false)
  const [selectedPlacementId, setSelectedPlacementId] = useState('')
  const [libraryExpanded, setLibraryExpanded] = useState(false)
  // 家具库「+」卡 → 粘贴抖音链接识别浮层
  const [showDouyinSheet, setShowDouyinSheet] = useState(false)
  // 画布左下角宠物菜单 + 虚拟猫狗（氛围层，不进 Placement、不落库）
  const [petMenuOpen, setPetMenuOpen] = useState(false)
  const [pets, setPets] = useState<Array<{ id: string; kind: 'cat' | 'dog'; x: number; y: number }>>([])

  // 每次回到本 Tab 刷新当前选中（资产可能已在动作流中变更）
  useDidShow(() => {
    if (!homes.find((h) => h.id === currentHomeId)) {
      setCurrentHomeId(homes[0]?.id ?? '')
    }
  })

  const currentHome = homes.find((h) => h.id === currentHomeId)
  const homeRooms = rooms.filter((r) => r.homeId === currentHomeId)
  const currentRoom =
    homeRooms.find((r) => r.id === currentRoomId) ?? homeRooms[0]
  const roomPlacements = placements.filter((p) => p.roomId === currentRoom?.id)
  const selectedPlacement = roomPlacements.find((p) => p.id === selectedPlacementId)

  // 解析 Placement 对应家具：先查用户资产 store，再查 mock 预置资产
  const furnitureOf = (p: Placement) => {
    const asset =
      assets.find((a) => a.id === p.assetId) ?? mockAssets.find((a) => a.id === p.assetId)
    return mockFurniture.find((f) => f.id === asset?.furnitureId) ?? mockFurniture[0]
  }

  // 家具资产库（平铺横滑）：用户资产 + mock 预置，按 furnitureId 解析封面
  const libraryItems = useMemo(() => {
    const all = [...assets, ...mockAssets.filter((m) => !assets.some((a) => a.id === m.id))]
    return all.slice(0, 12).map((item) => {
      const f = mockFurniture.find((mf) => mf.id === item.furnitureId)
      return { id: item.id, coverUrl: f?.coverUrl ?? '', title: f?.title ?? '家具' }
    })
  }, [assets])

  const homeTypeName = (t: Home['type']) => (t === 'new' ? '新房' : t === 'old' ? '旧房' : '样板')

  // 顶部操作（MVP 占位，与摆放页邀请/分享同一 toast 语义）
  const handleCobuild = () =>
    Taro.showToast({ title: '邀请家人一起摆放，共建入口已准备好', icon: 'none' })
  const handleShare = () => Taro.showToast({ title: '分享我的家，入口已准备好', icon: 'none' })

  // 虚拟宠物：随机落位；点贴纸「抱走」移除
  const addPet = (kind: 'cat' | 'dog') => {
    setPetMenuOpen(false)
    setPets((prev) => [
      ...prev,
      {
        id: genId('pet'),
        kind,
        x: 24 + Math.round(Math.random() * 200),
        y: 24 + Math.round(Math.random() * 200),
      },
    ])
  }
  const removePet = (id: string) => {
    setPets((prev) => prev.filter((p) => p.id !== id))
    Taro.showToast({ title: '已抱走', icon: 'none' })
  }

  const enterEditing = () => {
    setEditingFullscreen(true)
  }

  const exitEditing = () => {
    setEditingFullscreen(false)
    setSelectedPlacementId('')
  }

  const handleLibrarySelect = (assetId: string) => {
    if (!currentRoom) return
    const existing = roomPlacements.find((p) => p.assetId === assetId)
    if (existing) {
      setSelectedPlacementId(existing.id)
      setEditingFullscreen(true)
      return
    }

    const placement: Placement = {
      id: genId('placement'),
      roomId: currentRoom.id,
      assetId,
      transform: { x: 150, y: 142, rotate: 0, scale: 1 },
      isExisting: false,
    }
    addPlacement(placement)
    setSelectedPlacementId(placement.id)
    setEditingFullscreen(true)
  }

  const handleExpandedLibrarySelect = (assetId: string) => {
    setLibraryExpanded(false)
    handleLibrarySelect(assetId)
  }

  const updateSelectedPlacement = (patch: Partial<Placement['transform']>) => {
    if (!selectedPlacement) return
    updatePlacement(selectedPlacement.id, { ...selectedPlacement.transform, ...patch })
  }

  const nudgeSelectedPlacement = (dx: number, dy: number) => {
    if (!selectedPlacement) return
    updateSelectedPlacement({
      x: Math.max(0, Math.min(320, selectedPlacement.transform.x + dx)),
      y: Math.max(0, Math.min(260, selectedPlacement.transform.y + dy)),
    })
  }

  const removeSelectedPlacement = () => {
    if (!selectedPlacement) return
    removePlacement(selectedPlacement.id)
    setSelectedPlacementId('')
  }

  return (
    <View className={`myhome ${editingFullscreen ? 'myhome--editing' : ''}`}>
      <AppHeader title='QQ House' />

      <View className='myhome__topbar'>
        <View className='myhome__topbar-title'>
          <SectionTitle title='我的家' subtitle='所有动作流的产物都沉淀在这里' />
        </View>
        <View className='myhome__top-actions'>
          <View className='myhome__top-btn' onClick={handleCobuild}>
            <Text className='myhome__top-btn-text'>✦ 共建</Text>
          </View>
          <View className='myhome__top-btn' onClick={handleShare}>
            <Text className='myhome__top-btn-text'>↗ 分享</Text>
          </View>
        </View>
      </View>

      {/* ① 房屋选择条：一行收起；点「切换」以浮层下拉展开（覆盖在内容上方，不挤压下方空间） */}
      <View className='myhome__home-switch'>
        <View
          className='myhome__home-bar emboss'
          onClick={() => setHomesExpanded((v) => !v)}
        >
          <View className='myhome__home-bar-info'>
            <Text className='myhome__home-bar-name'>
              {currentHome?.name ?? '还没有家，先添加一个空间'}
            </Text>
            {currentHome && (
              <Text className='myhome__home-bar-meta'>
                {homeTypeName(currentHome.type)} · {homeRooms.length} 间房
              </Text>
            )}
          </View>
          <Text className='myhome__home-bar-toggle'>{homesExpanded ? '收起 ▴' : '切换 ▾'}</Text>
        </View>
        {homesExpanded && (
          <View className='myhome__homes animate-fade-rise'>
            {homes.map((h) => (
              <View
                key={h.id}
                className={`myhome__home-card emboss ${currentHomeId === h.id ? 'is-active' : ''}`}
                onClick={() => {
                  setCurrentHomeId(h.id)
                  setCurrentRoomId('')
                  setHomesExpanded(false)
                }}
              >
                <Text className='myhome__home-name'>{h.name}</Text>
                <Text className='myhome__home-meta'>
                  {homeTypeName(h.type)} · {rooms.filter((r) => r.homeId === h.id).length} 间房
                </Text>
              </View>
            ))}
          </View>
        )}
      </View>

      {/* ② 房间视图 */}
      {currentHome && (
        <>
          <View className='myhome__room-pills'>
            {homeRooms.map((r) => (
              <View
                key={r.id}
                className={`myhome__room-pill ${currentRoom?.id === r.id ? 'is-active' : ''}`}
                onClick={() => setCurrentRoomId(r.id)}
              >
                <Text
                  className={`myhome__room-pill-text ${
                    currentRoom?.id === r.id ? 'is-active' : ''
                  }`}
                >
                  {r.name}
                </Text>
              </View>
            ))}
          </View>

          {/* 方形 3D 空间展开（底图 = AI 生成单房间 3D 效果图；坐标系 = Placement.transform；3D 引擎后续接入） */}
          <View
            className={`myhome__canvas emboss-inset ${editingFullscreen ? 'is-editing' : ''}`}
            onClick={() => {
              enterEditing()
              setSelectedPlacementId('')
            }}
          >
            <img className='myhome__canvas-bg' src={space3dImg} alt='' />
            {editingFullscreen && (
              <View
                className='myhome__edit-exit'
                onClick={(e) => {
                  e.stopPropagation()
                  exitEditing()
                }}
              >
                <Text className='myhome__edit-exit-text'>退出</Text>
              </View>
            )}
            {roomPlacements.length === 0 ? (
              <View className='myhome__canvas-empty'>
                <Text className='myhome__canvas-empty-text'>
                  这个房间还是空的，从下面家具库拖一件进来吧
                </Text>
              </View>
            ) : (
              roomPlacements.map((p) => {
                const f = furnitureOf(p)
                return (
                  <View
                    key={p.id}
                    className={`myhome__sticker ${
                      selectedPlacementId === p.id ? 'is-selected' : ''
                    }`}
                    onClick={(e) => {
                      e.stopPropagation()
                      setEditingFullscreen(true)
                      setSelectedPlacementId(p.id)
                    }}
                    style={{
                      left: `${p.transform.x}px`,
                      top: `${p.transform.y}px`,
                      transform: `rotate(${p.transform.rotate}deg) scale(${p.transform.scale})`,
                    }}
                  >
                    <CoverImage src={f.coverUrl} title={f.title} ratio='1 / 1' />
                    <Text className='myhome__sticker-name'>{f.title}</Text>
                    {/* 旧房现有家具：「旧」角标 + 可移除（PRD 4 设计意图 2） */}
                    {p.isExisting && (
                      <View
                        className='myhome__sticker-remove'
                        onClick={(e) => {
                          e.stopPropagation()
                          removePlacement(p.id)
                        }}
                      >
                        <Text className='myhome__sticker-remove-text'>旧 ✕</Text>
                      </View>
                    )}
                  </View>
                )
              })
            )}

            {/* 虚拟宠物贴纸（氛围层；点贴纸抱走） */}
            {pets.map((pet) => (
              <View
                key={pet.id}
                className='myhome__pet'
                style={{ left: `${pet.x}px`, top: `${pet.y}px` }}
                onClick={(e) => {
                  e.stopPropagation()
                  removePet(pet.id)
                }}
              >
                <Text className='myhome__pet-text'>{pet.kind === 'cat' ? '🐱' : '🐶'}</Text>
              </View>
            ))}

            {/* 左下角宠物菜单：往空间里放虚拟小猫小狗（养宠的感觉） */}
            <View className='myhome__pet-menu' onClick={(e) => e.stopPropagation()}>
              {petMenuOpen && (
                <View className='myhome__pet-options animate-fade-rise'>
                  <View className='myhome__pet-option' onClick={() => addPet('cat')}>
                    <Text className='myhome__pet-option-text'>🐱</Text>
                  </View>
                  <View className='myhome__pet-option' onClick={() => addPet('dog')}>
                    <Text className='myhome__pet-option-text'>🐶</Text>
                  </View>
                </View>
              )}
              <View className='myhome__pet-fab' onClick={() => setPetMenuOpen((v) => !v)}>
                <Text className='myhome__pet-fab-text'>🐾</Text>
              </View>
            </View>
          </View>

          {/* 拖拽提示词（替代原「开始摆放」按钮） */}
          <Text className='myhome__hint'>从家具库中拖拽家具到空间中摆放即可</Text>

          {/* 家具资产库：平铺横滑；架首「+」卡 = 粘贴抖音链接识别家具 */}
          {editingFullscreen && selectedPlacement ? (
            <View className='myhome__physics-panel'>
              <View className='myhome__physics-head'>
                <Text className='myhome__physics-title'>形态调整</Text>
                <Text className='myhome__physics-meta'>
                  旋转 {selectedPlacement.transform.rotate}° · 缩放{' '}
                  {selectedPlacement.transform.scale.toFixed(1)}
                </Text>
              </View>
              <View className='myhome__physics-grid'>
                <View
                  className='myhome__physics-btn'
                  onClick={() =>
                    updateSelectedPlacement({
                      scale: Math.min(1.8, selectedPlacement.transform.scale + 0.1),
                    })
                  }
                >
                  <Text className='myhome__physics-btn-text'>放大</Text>
                </View>
                <View
                  className='myhome__physics-btn'
                  onClick={() =>
                    updateSelectedPlacement({
                      scale: Math.max(0.6, selectedPlacement.transform.scale - 0.1),
                    })
                  }
                >
                  <Text className='myhome__physics-btn-text'>缩小</Text>
                </View>
                <View
                  className='myhome__physics-btn'
                  onClick={() =>
                    updateSelectedPlacement({
                      rotate: selectedPlacement.transform.rotate - 15,
                    })
                  }
                >
                  <Text className='myhome__physics-btn-text'>左转</Text>
                </View>
                <View
                  className='myhome__physics-btn'
                  onClick={() =>
                    updateSelectedPlacement({
                      rotate: selectedPlacement.transform.rotate + 15,
                    })
                  }
                >
                  <Text className='myhome__physics-btn-text'>右转</Text>
                </View>
                <View className='myhome__physics-btn' onClick={() => nudgeSelectedPlacement(0, -12)}>
                  <Text className='myhome__physics-btn-text'>上移</Text>
                </View>
                <View className='myhome__physics-btn' onClick={() => nudgeSelectedPlacement(0, 12)}>
                  <Text className='myhome__physics-btn-text'>下移</Text>
                </View>
                <View className='myhome__physics-btn' onClick={() => nudgeSelectedPlacement(-12, 0)}>
                  <Text className='myhome__physics-btn-text'>左移</Text>
                </View>
                <View className='myhome__physics-btn' onClick={() => nudgeSelectedPlacement(12, 0)}>
                  <Text className='myhome__physics-btn-text'>右移</Text>
                </View>
                <View
                  className='myhome__physics-btn'
                  onClick={() => updateSelectedPlacement({ x: 150, y: 142 })}
                >
                  <Text className='myhome__physics-btn-text'>居中</Text>
                </View>
                <View className='myhome__physics-btn is-danger' onClick={removeSelectedPlacement}>
                  <Text className='myhome__physics-btn-text is-danger'>移除</Text>
                </View>
              </View>
            </View>
          ) : (
            <FurnitureLibrary
              items={libraryItems}
              selectedId={selectedPlacementId}
              onAdd={() => setShowDouyinSheet(true)}
              onOpen={() => setLibraryExpanded(true)}
              onSelect={handleLibrarySelect}
            />
          )}

          {/* AI 建议：整行黄底蓝字（唯一 CTA） */}
          <View
            className='myhome__cta-ai'
            onClick={() =>
              currentRoom &&
              Taro.navigateTo({
                url: `/pages/flow/suggest/index?roomId=${currentRoom.id}`,
              })
            }
          >
            <Text className='myhome__cta-ai-text'>AI 建议</Text>
          </View>
        </>
      )}

      {/* 粘贴抖音链接识别浮层（家具库「+」卡唤起） */}
      {libraryExpanded && (
        <View className='myhome__library-subpage'>
          <View className='myhome__library-subpage-head'>
            <View>
              <Text className='myhome__library-subpage-title'>家具库</Text>
              <Text className='myhome__library-subpage-meta'>{libraryItems.length} 件可试摆</Text>
            </View>
            <View
              className='myhome__library-subpage-back'
              onClick={() => setLibraryExpanded(false)}
            >
              <Text className='myhome__library-subpage-back-text'>返回</Text>
            </View>
          </View>

          <View className='myhome__library-grid'>
            <View
              className='myhome__library-grid-card myhome__library-grid-card--add'
              onClick={() => setShowDouyinSheet(true)}
            >
              <View className='myhome__library-grid-add'>
                <Text className='myhome__library-grid-plus'>＋</Text>
              </View>
              <Text className='myhome__library-grid-name'>截图建模</Text>
            </View>
            {libraryItems.map((item) => (
              <View
                key={item.id}
                className='myhome__library-grid-card'
                onClick={() => handleExpandedLibrarySelect(item.id)}
              >
                <View className='myhome__library-grid-cover'>
                  <CoverImage src={item.coverUrl} title={item.title} ratio='1 / 1' />
                </View>
                <Text className='myhome__library-grid-name'>{item.title}</Text>
              </View>
            ))}
          </View>
        </View>
      )}

      {showDouyinSheet && <DouyinLinkSheet onClose={() => setShowDouyinSheet(false)} />}
    </View>
  )
}
