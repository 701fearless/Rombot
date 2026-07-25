// 摆放/替换流：2D 俯视房间 + 家具贴纸拖拽（吸附对齐 + 抬升阴影，PRD 2.4③）
// 首屏 CTA 按 Home.type 分叉（PRD 5.2）；摆放随拖拽松手自动落库（跟随空间持久化，无「保存方案」按钮）
import { Text, View } from '@tarojs/components'
import type { ITouchEvent } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import { useEffect, useMemo, useRef, useState } from 'react'
import AppHeader from '@/components/AppHeader'
import CoverImage from '@/components/CoverImage'
import DirectionActions from '@/components/DirectionActions'
import DirectionPicker from '@/components/DirectionPicker'
import FurnitureLibrary from '@/components/FurnitureLibrary'
import ReviewCard from '@/components/ReviewCard'
import SpaceCanvas, { type SpaceViewMode } from '@/components/SpaceCanvas'
import SnapshotPlacePage from './SnapshotPlacePage'
import TopActions from '@/components/TopActions'
import { mockAssets, mockFurniture } from '@/mock'
import { useAssetStore, useHomeStore } from '@/store'
import type { Placement } from '@/types/models'
import { hapticLight, hapticMedium } from '@/utils/haptics'
import { genId } from '@/utils/id'
import './index.scss'

// 吸附参数：8px 网格 + 邻近边缘 ±8px 阈值
const GRID = 8
const SNAP_THRESHOLD = 8

// PRD 5.2：三入口首屏 CTA 分叉（必须做出明显区别）
const CTA_BY_TYPE: Record<string, { main: string; sub: string }> = {
  new: { main: '开始摆放', sub: '从发现页选家具' },
  old: { main: '移除/替换旧家具', sub: '保留部分旧物' },
  template: { main: '换风格 / 换单品', sub: '微调布局' },
}

type AiIssueId = 'clearance' | 'fit' | 'style'

interface AiIssue {
  id: AiIssueId
  label: string
  tag: string
  detail: string
  tone: 'warning' | 'success' | 'info'
}

const AI_ISSUES: AiIssue[] = [
  {
    id: 'clearance',
    label: '主通道还可放宽',
    tag: '动线 68cm',
    detail: '茶几与沙发之间目前约 68cm，建议把边几左移 24cm，把主通道放宽到 82cm。',
    tone: 'warning',
  },
  {
    id: 'fit',
    label: '真实尺寸匹配',
    tag: '尺寸合适',
    detail: '当前沙发宽 220cm，右侧仍有 82cm 余量，开门和落地灯使用都不受影响。',
    tone: 'success',
  },
  {
    id: 'style',
    label: '材质与色调协调',
    tag: '色调协调',
    detail: '暖灰布艺与木地板明度接近，建议保留一处苔绿色软装作为空间焦点。',
    tone: 'info',
  },
]

interface DragState {
  placementId: string
  startX: number
  startY: number
  originX: number
  originY: number
}

function LegacyPlacePage() {
  const { params } = useRouter()
  const { homes, rooms, placements, addPlacement, removePlacement, updatePlacement } =
    useHomeStore()
  const { assets, updateAssetStatus } = useAssetStore()

  const home = homes.find((h) => h.id === params.homeId)
  const room = rooms.find((r) => r.id === params.roomId)
  const roomPlacements = useMemo(
    () => placements.filter((p) => p.roomId === params.roomId),
    [placements, params.roomId],
  )

  // 拖拽本地状态：拖动过程中实时移动，松手才落 store
  const [dragPos, setDragPos] = useState<{ id: string; x: number; y: number } | null>(null)
  const [snapped, setSnapped] = useState(false)
  const [removeMode, setRemoveMode] = useState(false)
  const [reviewOpen, setReviewOpen] = useState(true)
  const [viewMode, setViewMode] = useState<SpaceViewMode>('render')
  const [activeIssueId, setActiveIssueId] = useState<AiIssueId>('clearance')
  // 场景操作台由底部胶囊主动唤起，避免盖住刚生成的摆放结果和 AI 审查。
  const [consoleOpen, setConsoleOpen] = useState(false)
  // 带 direction 进入（发现页/场景页「直接改」）：预选方向，不再自动弹浮窗
  const [direction, setDirection] = useState<string | null>(params.direction ?? null)
  const dragRef = useRef<DragState | null>(null)
  // 吸附状态上一帧值：只在「未吸附 → 吸附」跳变瞬间震动，避免拖动中连震
  const snappedRef = useRef(false)
  // 待摆放资产是否已生成 Placement（只初始化一次）
  const [pendingPlacementId, setPendingPlacementId] = useState<string | null>(null)

  const furnitureOf = (p: Placement) => {
    const asset =
      assets.find((a) => a.id === p.assetId) ?? mockAssets.find((a) => a.id === p.assetId)
    return mockFurniture.find((f) => f.id === asset?.furnitureId) ?? mockFurniture[0]
  }

  // 带 assetId 进入：生成初始居中的待摆放 Placement（幂等，副作用放 useEffect）
  useEffect(() => {
    if (!params.assetId || pendingPlacementId) return
    const exists = placements.some((p) => p.assetId === params.assetId)
    if (!exists) {
      const p: Placement = {
        id: genId('placement'),
        roomId: params.roomId ?? '',
        assetId: params.assetId,
        transform: { x: 120, y: 120, rotate: 0, scale: 1 },
        isExisting: false,
      }
      addPlacement(p)
      setPendingPlacementId(p.id)
    } else {
      setPendingPlacementId(placements.find((p) => p.assetId === params.assetId)!.id)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.assetId])

  // 带方向进入：轻提示已进入试改（替代自动弹浮窗）
  useEffect(() => {
    if (!params.direction) return
    const t = setTimeout(() => {
      Taro.showToast({ title: `已按「${params.direction}」方向进入试改`, icon: 'none' })
    }, 400)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ---------- 拖拽（触摸事件；拖起抬升 + 网格/边缘吸附 + 轻反馈） ----------
  const onStickerTouchStart = (p: Placement, e: ITouchEvent) => {
    const t = e.touches[0]
    dragRef.current = {
      placementId: p.id,
      startX: t.clientX,
      startY: t.clientY,
      originX: p.transform.x,
      originY: p.transform.y,
    }
    setDragPos({ id: p.id, x: p.transform.x, y: p.transform.y })
  }

  const onStickerTouchMove = (e: ITouchEvent) => {
    const drag = dragRef.current
    if (!drag) return
    const t = e.touches[0]
    let x = drag.originX + (t.clientX - drag.startX)
    let y = drag.originY + (t.clientY - drag.startY)

    // ① 网格吸附（8px）
    const gx = Math.round(x / GRID) * GRID
    const gy = Math.round(y / GRID) * GRID
    let didSnap = Math.abs(gx - x) <= SNAP_THRESHOLD || Math.abs(gy - y) <= SNAP_THRESHOLD
    if (Math.abs(gx - x) <= SNAP_THRESHOLD) x = gx
    if (Math.abs(gy - y) <= SNAP_THRESHOLD) y = gy

    // ② 邻近家具边缘吸附（±8px 阈值）
    for (const other of roomPlacements) {
      if (other.id === drag.placementId) continue
      const ox = other.transform.x
      const oy = other.transform.y
      if (Math.abs(x - ox) <= SNAP_THRESHOLD) {
        x = ox
        didSnap = true
      }
      if (Math.abs(y - oy) <= SNAP_THRESHOLD) {
        y = oy
        didSnap = true
      }
    }

    // 画布边界约束
    x = Math.max(0, Math.min(x, 320))
    y = Math.max(0, Math.min(y, 260))

    // 吸附跳变瞬间：轻震动反馈（P1-1）
    if (didSnap && !snappedRef.current) hapticLight()
    snappedRef.current = didSnap

    setSnapped(didSnap)
    setDragPos({ id: drag.placementId, x, y })
  }

  const onStickerTouchEnd = () => {
    const drag = dragRef.current
    if (!drag || !dragPos) return
    // 松手落库（PRD 铁律：产物写 store + Storage）
    const origin = roomPlacements.find((p) => p.id === drag.placementId)
    updatePlacement(drag.placementId, {
      x: dragPos.x,
      y: dragPos.y,
      rotate: origin?.transform.rotate ?? 0,
      scale: origin?.transform.scale ?? 1,
    })
    // 吸附状态下落位成功：中震动确认（P1-1）
    if (snapped) hapticMedium()
    // 待摆放资产首次落位 → 状态机 recognized → placed
    if (params.assetId && drag.placementId === pendingPlacementId) {
      updateAssetStatus(params.assetId, 'placed')
    }
    dragRef.current = null
    setDragPos(null)
    setSnapped(false)
    snappedRef.current = false
  }

  const handleRemoveExisting = (p: Placement) => {
    // 旧房「移除旧家具」= 删 isExisting Placement（PRD 4 设计意图 2）
    removePlacement(p.id)
    Taro.showToast({ title: '已移除旧家具', icon: 'none' })
  }

  const handleInvite = () => Taro.showToast({ title: '邀请好友一起评方案', icon: 'none' })
  const handleShare = () => Taro.showToast({ title: '分享传播入口已准备好', icon: 'none' })

  const handleLibrarySelect = (assetId: string) => {
    const existing = roomPlacements.find((p) => p.assetId === assetId)
    if (existing) {
      setPendingPlacementId(existing.id)
      Taro.showToast({ title: '这件家具已在空间中', icon: 'none' })
      return
    }

    const positions = [
      { x: 128, y: 138 },
      { x: 224, y: 92 },
      { x: 72, y: 196 },
    ]
    const position = positions[roomPlacements.length % positions.length]
    const placement: Placement = {
      id: genId('placement'),
      roomId: params.roomId ?? '',
      assetId,
      transform: { x: position.x, y: position.y, rotate: 0, scale: 1 },
      isExisting: false,
    }
    addPlacement(placement)
    setPendingPlacementId(placement.id)
    setReviewOpen(true)
    setActiveIssueId('clearance')
    if (assets.some((asset) => asset.id === assetId)) updateAssetStatus(assetId, 'placed')
    Taro.showToast({ title: '已按真实尺寸放入空间', icon: 'none' })
  }

  const handleIssueSelect = (issueId: AiIssueId) => {
    setActiveIssueId(issueId)
    setReviewOpen(true)
    hapticLight()
  }

  const handleAiFix = () => {
    const target =
      roomPlacements.find((p) => p.id === pendingPlacementId) ??
      roomPlacements.find((p) => !p.isExisting) ??
      roomPlacements[0]
    if (!target) {
      Taro.showToast({ title: '先放入一件家具再试试', icon: 'none' })
      return
    }
    updatePlacement(target.id, {
      ...target.transform,
      x: Math.max(24, Math.min(target.transform.x - 24, 300)),
      y: Math.max(24, Math.min(target.transform.y + 12, 252)),
    })
    setActiveIssueId('fit')
    hapticMedium()
    Taro.showToast({ title: '已放宽主通道至 82cm', icon: 'none' })
  }

  const handleSearchSame = () =>
    Taro.navigateTo({
      url: `/pages/flow/recommend/index?roomId=${params.roomId ?? ''}&direction=${direction ?? '动线'}`,
    })

  // 主链路：AI 优化建议（改造之前）→「发现」Tab 选方向 → 三动作
  const goDirection = () => Taro.switchTab({ url: '/pages/direction/index' })
  // 浮窗内三动作：① 出方案（文本）② 荐单品（直达抖音）③ 直接改（试改，mock）
  const handleDirectionSuggest = () =>
    Taro.navigateTo({
      url: `/pages/flow/suggest/index?roomId=${params.roomId ?? ''}&direction=${direction}`,
    })
  const handleDirectionRecommend = () =>
    Taro.navigateTo({
      url: `/pages/flow/recommend/index?roomId=${params.roomId ?? ''}&direction=${direction}`,
    })
  const handleDirectEdit = () => {
    setConsoleOpen(false)
    Taro.showToast({ title: `按「${direction}」试改（mock）`, icon: 'none' })
  }
  const goComplete = () =>
    Taro.navigateTo({
      url: `/pages/flow/complete/index?roomId=${params.roomId}&assetId=${params.assetId ?? ''}`,
    })

  const libraryItems = useMemo(
    () =>
      mockAssets.slice(0, 8).map((item) => {
        const f = mockFurniture.find((mf) => mf.id === item.furnitureId)
        return { id: item.id, coverUrl: f?.coverUrl ?? '', title: f?.title ?? '家具' }
      }),
    [],
  )
  const activeIssue = AI_ISSUES.find((issue) => issue.id === activeIssueId) ?? AI_ISSUES[0]
  const selectedAssetId = roomPlacements.find((p) => p.id === pendingPlacementId)?.assetId

  if (!home || !room) {
    return (
      <View className='place'>
        <AppHeader title='QQ House' />
        <View className='place__missing emboss-inset'>
          <Text className='place__missing-text'>房间信息缺失，请从「发现」重新进入</Text>
        </View>
      </View>
    )
  }

  const cta = CTA_BY_TYPE[home.type] ?? CTA_BY_TYPE.new
  const existingPlacements = roomPlacements.filter((p) => p.isExisting)

  return (
    <View className='place'>
      <AppHeader title='QQ House' />
      <View className='place__topbar'>
        <View className='place__header'>
          <Text className='place__title'>
            {home.name} · {room.name}
          </Text>
          <Text className='place__subtitle'>
            {home.type === 'new' && '空间建模已完成 · 实尺试摆'}
            {home.type === 'old' && `已识别 ${existingPlacements.length} 件旧家具 · 可替换`}
            {home.type === 'template' && '模板空间已同步 · 可换单品与布局'}
          </Text>
        </View>
        <TopActions onInvite={handleInvite} onShare={handleShare} />
      </View>

      <View className='place__status-row'>
        <View className='place__status-chip is-strong'>
          <Text className='place__status-chip-text is-strong'>1:1 实尺</Text>
        </View>
        <View className='place__status-chip'>
          <Text className='place__status-chip-text'>{roomPlacements.length} 件家具</Text>
        </View>
        <View className='place__status-chip'>
          <Text className='place__status-chip-text'>自动保存</Text>
        </View>
      </View>

      {home.type === 'old' && (
        <View
          className={`place__remove-toggle ${removeMode ? 'is-active' : ''}`}
          onClick={() => setRemoveMode((v) => !v)}
        >
          <Text className={`place__remove-toggle-text ${removeMode ? 'is-active' : ''}`}>
            {removeMode ? '完成移除' : cta.main}
          </Text>
        </View>
      )}

      <SpaceCanvas mode={viewMode}>
        <View className='place__canvas-toolbar'>
          <View className='place__canvas-state'>
            <Text className='place__canvas-state-text'>3D 空间</Text>
          </View>
          <View className='place__view-switch'>
            <View
              className={`place__view-option ${viewMode === 'render' ? 'is-active' : ''}`}
              onClick={() => setViewMode('render')}
            >
              <Text
                className={`place__view-option-text ${viewMode === 'render' ? 'is-active' : ''}`}
              >
                45°
              </Text>
            </View>
            <View
              className={`place__view-option ${viewMode === 'plan' ? 'is-active' : ''}`}
              onClick={() => setViewMode('plan')}
            >
              <Text
                className={`place__view-option-text ${viewMode === 'plan' ? 'is-active' : ''}`}
              >
                俯视
              </Text>
            </View>
          </View>
        </View>

        {params.assetId && (
          <View className='place__pending'>
            <Text className='place__pending-text'>截图家具已完成建模，待确认位置</Text>
          </View>
        )}

        {roomPlacements.map((p) => {
          const f = furnitureOf(p)
          const dragging = dragPos?.id === p.id
          const pos = dragging ? dragPos! : { x: p.transform.x, y: p.transform.y }
          return (
            <View
              key={p.id}
              className={`place__sticker ${dragging ? 'is-dragging' : ''} ${
                dragging && snapped ? 'is-snapped' : ''
              } ${p.id === pendingPlacementId ? 'is-pending' : ''}`}
              style={{ left: `${pos.x}px`, top: `${pos.y}px` }}
              onTouchStart={(e) => onStickerTouchStart(p, e as ITouchEvent)}
              onTouchMove={(e) => onStickerTouchMove(e as ITouchEvent)}
              onTouchEnd={onStickerTouchEnd}
            >
              <CoverImage src={f.coverUrl} title={f.title} ratio='1 / 1' />
              <Text className='place__sticker-name'>{f.title}</Text>
              {p.isExisting && (
                <View className='place__sticker-badge'>
                  <Text className='place__sticker-badge-text'>旧</Text>
                </View>
              )}
              {p.isExisting && removeMode && (
                <View className='place__sticker-remove' onClick={() => handleRemoveExisting(p)}>
                  <Text className='place__sticker-remove-text'>✕</Text>
                </View>
              )}
            </View>
          )
        })}

        {reviewOpen &&
          AI_ISSUES.map((issue) => (
            <View
              key={issue.id}
              className={`place__ai-tag place__ai-tag--${issue.id} is-${issue.tone} ${
                activeIssueId === issue.id ? 'is-active' : ''
              }`}
              onClick={() => handleIssueSelect(issue.id)}
            >
              <View className='place__ai-tag-dot' />
              <Text className='place__ai-tag-text'>{issue.tag}</Text>
            </View>
          ))}
      </SpaceCanvas>

      <FurnitureLibrary
        items={libraryItems}
        selectedId={selectedAssetId}
        onSelect={handleLibrarySelect}
        onAdd={() => Taro.navigateTo({ url: '/pages/flow/recognize/index' })}
      />

      {/* AI 优化建议（改造之前）；方向/出方案等动作全部收进操作台浮窗 */}
      <ReviewCard
        open={reviewOpen}
        issueLabel={activeIssue.label}
        text={activeIssue.detail}
        score={activeIssue.id === 'clearance' ? 86 : 94}
        onToggle={() => setReviewOpen((v) => !v)}
        onFix={handleAiFix}
        onSearch={handleSearchSame}
      />

      {/* 悬浮胶囊：唤起操作台浮窗（首次摆放完成后浮窗已自动弹过一次） */}
      {!consoleOpen && (
        <View className='place__console-capsule' onClick={() => setConsoleOpen(true)}>
          <Text className='place__console-capsule-text'>场景改造</Text>
        </View>
      )}

      {/* 操作台浮窗：屏幕中间，方向 pills + 三动作 + 出方案 + 微调/换风格（摆放自动保存，跟随空间） */}
      {consoleOpen && (
        <View className='console-modal' onClick={() => setConsoleOpen(false)}>
          <View className='console-modal__panel' onClick={(e) => e.stopPropagation()}>
            <View className='console-modal__head'>
              <Text className='console-modal__title'>选方向 · 出方案</Text>
              <View className='console-modal__close' onClick={() => setConsoleOpen(false)}>
                <Text className='console-modal__close-text'>✕</Text>
              </View>
            </View>

            <DirectionPicker value={direction ?? undefined} onChange={setDirection} />
            {direction && (
              <View className='console-modal__direction'>
                <DirectionActions
                  onRecommend={handleDirectionSuggest}
                  onGenerate={handleDirectionRecommend}
                  onDirectEdit={handleDirectEdit}
                />
                <View className='console-modal__more' onClick={goDirection}>
                  <Text className='console-modal__more-text'>更多方向，去发现页 ›</Text>
                </View>
              </View>
            )}

            <View className='console-modal__actions'>
              <View className='console-modal__action-main' onClick={goComplete}>
                <Text className='console-modal__action-main-text'>出方案</Text>
              </View>
            </View>

            <View className='console-modal__links'>
              {(home.type === 'new' || home.type === 'template') && (
                <View
                  className='console-modal__link'
                  onClick={() => Taro.switchTab({ url: '/pages/discover/index' })}
                >
                  <Text className='console-modal__link-text'>{cta.sub} →</Text>
                </View>
              )}
              {home.type === 'template' && (
                <View
                  className='console-modal__link'
                  onClick={() =>
                    Taro.showToast({
                      title: '风格切换（mock）：整套 Placement 将按新风格重建',
                      icon: 'none',
                    })
                  }
                >
                  <Text className='console-modal__link-text'>{cta.main} →</Text>
                </View>
              )}
            </View>
          </View>
        </View>
      )}
    </View>
  )
}

export default function PlacePage() {
  const { params } = useRouter()
  if (params.sceneId) {
    return <SnapshotPlacePage sceneId={params.sceneId} frameId={params.frameId} objectId={params.objectId} />
  }
  return <LegacyPlacePage />
}
