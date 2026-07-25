// Tab4 个人资产：用户信息 + 四个空间/家具建模入口
// = 开屏动画（只播一次）+ 四端口 Hero：
//   立即扫描 → 接相机 → 识别流；上传平面图 → 选择照片/拍照 → 建空屋进摆放流；
//   选择模板空间 → switchTab「我的家」（空间资产库已挪到该 Tab）；
//   粘贴抖音链接识别 → 读剪贴板 → 识别流（入口B，sourceId 直达）
import { Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useMemo, useState } from 'react'
import AppHeader from '@/components/AppHeader'
import CoverShelf from '@/components/CoverShelf'
import type { ShelfItem, ShelfRowData } from '@/components/CoverShelf'
import EntryHero from '@/components/EntryHero'
import { mockSpaceTemplates, mockUser } from '@/mock'
import { spaceTemplateImages } from '@/mock/images'
import { useAssetStore, useHomeStore, useSceneStore } from '@/store'
import type { Home } from '@/types/models'
import { genId } from '@/utils/id'
import './index.scss'

const SPACE_FILTERS = ['模板空间', '扫描所得', '平面图所得']

const ADD_SPACE_CARD: ShelfItem = {
  id: 'add_space',
  title: '添加空间',
  variant: 'add',
}

/** 上传平面图拿到图后：建 type=new 的空屋，直接进摆放流 */
function createEmptyHomeAndEnter() {
  const { homes, addHome } = useHomeStore.getState()
  const home: Home = {
    id: genId('home'),
    ownerId: mockUser.unionId,
    type: 'new',
    name: `新家 ${homes.length + 1}`,
    isPrimary: homes.length === 0,
  }
  addHome(home)
  Taro.navigateTo({ url: `/pages/flow/place/index?homeId=${home.id}` })
}

export default function DesignPage() {
  const [showFloorplanSheet, setShowFloorplanSheet] = useState(false)
  const [showPersonalAssets, setShowPersonalAssets] = useState(false)
  const [spaceFilter, setSpaceFilter] = useState(SPACE_FILTERS[0])
  const homes = useHomeStore((state) => state.homes)
  const rooms = useHomeStore((state) => state.rooms)
  const homeCount = useHomeStore((state) => state.homes.length)
  const assetCount = useAssetStore((state) => state.assets.length)
  const displayName = mockUser.nickname ?? '我的空间'
  const activeSceneId = useSceneStore((state) => state.activeSceneId)
  const setActiveSceneId = useSceneStore((state) => state.setActiveSceneId)

  // ---------- 三端口动作 ----------
  // 立即扫描：接相机，拍完进识别流（取消则不跳转）
  const goScan = () => {
    Taro.chooseImage({
      count: 1,
      sourceType: ['camera'],
      success: () => Taro.navigateTo({ url: '/pages/flow/recognize/index' }),
      fail: () => {},
    })
  }
  // 上传平面图：先弹「选择照片 / 拍照」二选一
  const goFloorplan = () => setShowFloorplanSheet(true)
  // 选择模板空间：空间资产库在「我的家」Tab，滑选模板后进摆放流
  const goTemplate = () => {
    setSpaceFilter(SPACE_FILTERS[0])
    setShowPersonalAssets(true)
  }
  // 粘贴抖音链接识别：读剪贴板 → 识别流（入口B，sourceId 直达）；读不到走模拟链路
  const goDouyin = () => {
    const enter = (sourceId: string) =>
      Taro.navigateTo({
        url: `/pages/flow/recognize/index?sourceId=${encodeURIComponent(sourceId)}`,
      })
    Taro.getClipboardData({
      success: (res) => enter(res.data?.trim() || `dy_${Date.now().toString(36)}`),
      fail: () => enter(`dy_${Date.now().toString(36)}`),
    })
  }

  // 平面图取图：相册或拍照，拿到图 → 建空屋 → 摆放流
  const pickFloorplan = (source: 'album' | 'camera') => {
    setShowFloorplanSheet(false)
    setShowPersonalAssets(false)
    Taro.chooseImage({
      count: 1,
      sourceType: [source],
      success: () => createEmptyHomeAndEnter(),
      fail: () => {},
    })
  }

  const spaceRows: ShelfRowData[] = useMemo(() => {
    const currentItems: ShelfItem[] =
      spaceFilter === '模板空间'
        ? mockSpaceTemplates.map((tpl) => ({
            id: tpl.id,
            title: tpl.title,
            coverUrl: spaceTemplateImages[tpl.id],
            tag: '3D 空间',
            tone: tpl.tint,
          }))
        : homes
            .filter((home) => (spaceFilter === '扫描所得' ? home.type === 'old' : home.type === 'new'))
            .map((home) => ({
              id: home.id,
              title: home.name,
              tag: spaceFilter,
              tone:
                home.type === 'old'
                  ? 'var(--color-pastel-blue)'
                  : 'var(--color-pastel-green)',
            }))

    return [
      {
        id: 'spaces',
        title: '空间记录',
        filters: SPACE_FILTERS,
        activeFilter: spaceFilter,
        onFilterChange: setSpaceFilter,
        items: [ADD_SPACE_CARD, ...currentItems],
        emptyHint: '还没有空间记录，先添加一个空间吧',
      },
    ]
  }, [homes, spaceFilter])

  const enterHome = (homeId: string) => {
    const room = rooms.find((item) => item.homeId === homeId)
    if (!room) {
      Taro.showToast({ title: '这个空间还没有房间，先完成建模', icon: 'none' })
      return
    }
    setShowPersonalAssets(false)
    Taro.navigateTo({ url: `/pages/flow/place/index?homeId=${homeId}&roomId=${room.id}` })
  }

  const enterTemplateHome = () => {
    const templateHome = homes.find((home) => home.type === 'template')
    if (templateHome) enterHome(templateHome.id)
  }

  const handleSpaceRecordClick = (_rowId: string, item: ShelfItem) => {
    if (item.variant === 'add') return
    if (spaceFilter === '模板空间') {
      enterTemplateHome()
      return
    }
    enterHome(item.id)
  }

  const handleAssetScan = () => {
    setShowPersonalAssets(false)
    goScan()
  }

  const handleAssetFloorplan = () => {
    setShowPersonalAssets(false)
    setShowFloorplanSheet(true)
  }

  return (
    <View className="remodel">
      <AppHeader title="QQ House" />

      <View className="remodel__profile">
        <View className="remodel__avatar">
          <Text className="remodel__avatar-text">{displayName.slice(0, 1)}</Text>
        </View>
        <View className="remodel__identity">
          <Text className="remodel__name">{displayName}</Text>
          <Text className="remodel__role">空间主理人</Text>
          <Text className="remodel__motto">把喜欢的家具，先放进自己的家</Text>
        </View>
        <View className="remodel__stats">
          <Text className="remodel__stat-value">{homeCount}</Text>
          <Text className="remodel__stat-label">个空间</Text>
          <View className="remodel__stat-divider" />
          <Text className="remodel__stat-value">{assetCount}</Text>
          <Text className="remodel__stat-label">件家具</Text>
        </View>
      </View>

      <View className='remodel__floorplan-select'>
        <View className='remodel__floorplan-copy'>
          <Text className='remodel__floorplan-title'>当前户型</Text>
          <Text className='remodel__floorplan-meta'>Feed 家具默认放入这里</Text>
        </View>
        <View className='remodel__floorplan-options'>
          {['room1', 'room6', 'room8'].map((sceneId) => {
            const enabled = sceneId === 'room6'
            return (
              <View
                key={sceneId}
                className={`remodel__floorplan-option ${activeSceneId === sceneId ? 'is-active' : ''} ${enabled ? '' : 'is-disabled'}`}
                onClick={() => {
                  if (enabled) setActiveSceneId(sceneId)
                  else Taro.showToast({ title: `${sceneId} 白模待接入`, icon: 'none' })
                }}
              >
                <Text>{sceneId.replace('room', 'R')}</Text>
              </View>
            )
          })}
        </View>
      </View>

      <View className="remodel__asset-heading" onClick={() => setShowPersonalAssets(true)}>
        <Text className="remodel__asset-title">个人资产</Text>
        <Text className="remodel__asset-subtitle">房间、户型与心动单品都会收进这里</Text>
      </View>

      {/* 四个添加入口使用紧凑布局，iPhone 16 Pro Max 首屏完整展示。 */}
      <EntryHero
        compact
        onScan={goScan}
        onFloorplan={goFloorplan}
        onTemplate={goTemplate}
        onDouyin={goDouyin}
      />

      {/* 上传平面图动作层：选择照片 / 拍照 */}
      {showFloorplanSheet && (
        <View className="add-sheet" onClick={() => setShowFloorplanSheet(false)}>
          <View className="add-sheet__panel" onClick={(e) => e.stopPropagation()}>
            <Text className="add-sheet__title">上传平面图</Text>
            <View className="add-sheet__option" onClick={() => pickFloorplan('album')}>
              <Text className="add-sheet__option-title">选择照片</Text>
              <Text className="add-sheet__option-desc">从相册挑一张户型图，AI 帮你建空屋</Text>
            </View>
            <View className="add-sheet__option" onClick={() => pickFloorplan('camera')}>
              <Text className="add-sheet__option-title">拍照</Text>
              <Text className="add-sheet__option-desc">直接拍下手边或屏幕上的户型图</Text>
            </View>
            <View className="add-sheet__cancel" onClick={() => setShowFloorplanSheet(false)}>
              <Text className="add-sheet__cancel-text">取消</Text>
            </View>
          </View>
        </View>
      )}

      {showPersonalAssets && (
        <View className="add-sheet add-sheet--assets" onClick={() => setShowPersonalAssets(false)}>
          <View
            className="add-sheet__panel add-sheet__panel--assets"
            onClick={(e) => e.stopPropagation()}
          >
            <Text className="add-sheet__title">个人资产</Text>
            <CoverShelf rows={spaceRows} onItemClick={handleSpaceRecordClick} />
            <View className="add-sheet__option" onClick={handleAssetScan}>
              <Text className="add-sheet__option-title">扫描我的房间</Text>
              <Text className="add-sheet__option-desc">用相机识别真实房间，把扫描所得收进个人资产。</Text>
            </View>
            <View className="add-sheet__option" onClick={handleAssetFloorplan}>
              <Text className="add-sheet__option-title">上传平面图</Text>
              <Text className="add-sheet__option-desc">从户型图建空间，生成后记录到平面图所得。</Text>
            </View>
            <View className="add-sheet__cancel" onClick={() => setShowPersonalAssets(false)}>
              <Text className="add-sheet__cancel-text">取消</Text>
            </View>
          </View>
        </View>
      )}
    </View>
  )
}
