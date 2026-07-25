// Tab2 我的家：常驻资产池（PRD 架构决策 2，留存核心）
// 结构（2026-07-25 修订）：
//   房屋选择条（一行收起，点开展开选取后收起）→ 方形 3D 空间展开（2D 贴图占位）
//   → 拖拽提示词 + 平铺横滑家具资产库 → AI 建议（黄底蓝字，整行）
//   → 空间资产库（从「设计」Tab 挪入，替代原方案清单；点模板空间进摆放流）
import { Text, View } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { useMemo, useState } from 'react'
import CoverImage from '@/components/CoverImage'
import CoverShelf from '@/components/CoverShelf'
import type { ShelfItem, ShelfRowData } from '@/components/CoverShelf'
import DouyinLinkSheet from '@/components/DouyinLinkSheet'
import FurnitureLibrary from '@/components/FurnitureLibrary'
import SectionTitle from '@/components/SectionTitle'
import { mockAssets, mockFurniture, mockUser } from '@/mock'
import { spaceTemplateImages } from '@/mock/images'
import { useAssetStore, useHomeStore } from '@/store'
import type { Home, Placement } from '@/types/models'
import { genId } from '@/utils/id'
// 方形画布底图：AI 生成单房间 3D 效果图（import 引用才会被 webpack 打包进 dist）
import space3dImg from '@/assets/space-3d-living.png'
import './index.scss'

// 六个 3D 空间模板：封面 = AI 生成的 3D 场景图，tone 作加载兜底底色
const SPACE_TEMPLATES: ShelfItem[] = [
  { id: 'space_french_living', title: '法式客厅', tag: '3D 空间', coverUrl: spaceTemplateImages.tpl_french_living, tone: 'var(--color-pastel-peach)' },
  { id: 'space_minimal_bedroom', title: '极简卧室', tag: '3D 空间', coverUrl: spaceTemplateImages.tpl_minimal_bedroom, tone: 'var(--color-pastel-cream)' },
  { id: 'space_new_chinese_study', title: '新中式书房', tag: '3D 空间', coverUrl: spaceTemplateImages.tpl_chinese_study, tone: 'var(--color-primary-light)' },
  { id: 'space_kids_room', title: '儿童房', tag: '3D 空间', coverUrl: spaceTemplateImages.tpl_kids_room, tone: 'var(--color-pastel-green)' },
  { id: 'space_pet_home', title: '养宠空间', tag: '3D 空间', coverUrl: spaceTemplateImages.tpl_pet_space, tone: 'var(--color-pastel-blue)' },
  { id: 'space_european_dining', title: '欧式餐厅', tag: '3D 空间', coverUrl: spaceTemplateImages.tpl_euro_dining, tone: 'var(--color-pastel-peach)' },
]

// 空间资产库三分类（模板空间有内容；扫描/平面图所得等用户产出落库）
const SPACE_FILTERS = ['模板空间', '扫描所得', '平面图所得']

// 「+」新建卡：空间行首位
const ADD_SPACE_CARD: ShelfItem = { id: '__add_space__', title: '添加空间', variant: 'add' }

/** 取/建一套 type=template 的样板间，进入摆放流（模板空间一键套用） */
function enterTemplateHome() {
  const { homes, rooms, addHome } = useHomeStore.getState()
  let home = homes.find((h) => h.type === 'template')
  if (!home) {
    home = {
      id: genId('home'),
      ownerId: mockUser.unionId,
      type: 'template',
      name: `模板家 ${homes.length + 1}`,
      isPrimary: homes.length === 0,
    }
    addHome(home)
  }
  const room = rooms.find((r) => r.homeId === home.id)
  const roomQuery = room ? `&roomId=${room.id}` : ''
  Taro.navigateTo({ url: `/pages/flow/place/index?homeId=${home.id}${roomQuery}` })
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

export default function MyHomePage() {
  const { homes, rooms, placements, removePlacement } = useHomeStore()
  const { assets } = useAssetStore()

  const [currentHomeId, setCurrentHomeId] = useState(homes[0]?.id ?? '')
  const [currentRoomId, setCurrentRoomId] = useState('')
  const [homesExpanded, setHomesExpanded] = useState(false)
  const [spaceFilter, setSpaceFilter] = useState('模板空间')
  const [showAddSheet, setShowAddSheet] = useState(false)
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

  // 空间资产库行（从「设计」Tab 挪入，替代原方案清单位）
  const spaceRows: ShelfRowData[] = useMemo(() => {
    const spaceItems: ShelfItem[] =
      spaceFilter === '模板空间' ? [ADD_SPACE_CARD, ...SPACE_TEMPLATES] : [ADD_SPACE_CARD]
    const spaceHint =
      spaceFilter === '扫描所得'
        ? '扫描你的房间后，会出现在这里'
        : spaceFilter === '平面图所得'
          ? '上传平面图建好的空屋，会出现在这里'
          : undefined
    return [
      {
        id: 'spaces',
        title: '空间资产库',
        items: spaceItems,
        filters: SPACE_FILTERS,
        activeFilter: spaceFilter,
        onFilterChange: setSpaceFilter,
        emptyHint: spaceHint,
      },
    ]
  }, [spaceFilter])

  const handleShelfClick = (_rowId: string, item: ShelfItem) => {
    if (item.variant === 'add') {
      setShowAddSheet(true)
      return
    }
    // 模板空间 → 一键套用，直接进摆放流
    enterTemplateHome()
  }

  // 「+」卡动作层：扫描房屋（接相机 → 识别流）/ 上传平面图（相册 → 建空屋 → 摆放流）
  const handleAddScan = () => {
    setShowAddSheet(false)
    Taro.chooseImage({
      count: 1,
      sourceType: ['camera'],
      success: () => Taro.navigateTo({ url: '/pages/flow/recognize/index' }),
      fail: () => {},
    })
  }
  const handleAddFloorplan = () => {
    setShowAddSheet(false)
    Taro.chooseImage({
      count: 1,
      sourceType: ['album', 'camera'],
      success: () => createEmptyHomeAndEnter(),
      fail: () => {},
    })
  }

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

  return (
    <View className='myhome'>
      {/* 页首：标题 + 右上「共建 / 分享」 */}
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
          <View className='myhome__canvas emboss-inset'>
            <img className='myhome__canvas-bg' src={space3dImg} alt='' />
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
                    className='myhome__sticker'
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
                        onClick={() => removePlacement(p.id)}
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
                onClick={() => removePet(pet.id)}
              >
                <Text className='myhome__pet-text'>{pet.kind === 'cat' ? '🐱' : '🐶'}</Text>
              </View>
            ))}

            {/* 左下角宠物菜单：往空间里放虚拟小猫小狗（养宠的感觉） */}
            <View className='myhome__pet-menu'>
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
          <FurnitureLibrary items={libraryItems} onAdd={() => setShowDouyinSheet(true)} />

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

      {/* ③ 空间资产库（从「设计」Tab 挪入，替代原方案清单）：滑选模板空间一键套用 */}
      <CoverShelf rows={spaceRows} onItemClick={handleShelfClick} />

      {/* 「+」卡动作层：扫描房屋 / 上传平面图 */}
      {showAddSheet && (
        <View className='add-sheet' onClick={() => setShowAddSheet(false)}>
          <View className='add-sheet__panel' onClick={(e) => e.stopPropagation()}>
            <Text className='add-sheet__title'>添加空间</Text>
            <View className='add-sheet__option' onClick={handleAddScan}>
              <Text className='add-sheet__option-title'>扫描房屋</Text>
              <Text className='add-sheet__option-desc'>拍摄房间照片，AI 识别现有家具</Text>
            </View>
            <View className='add-sheet__option' onClick={handleAddFloorplan}>
              <Text className='add-sheet__option-title'>上传平面图</Text>
              <Text className='add-sheet__option-desc'>上传户型图建空屋，从零开始摆放</Text>
            </View>
            <View className='add-sheet__cancel' onClick={() => setShowAddSheet(false)}>
              <Text className='add-sheet__cancel-text'>取消</Text>
            </View>
          </View>
        </View>
      )}

      {/* 粘贴抖音链接识别浮层（家具库「+」卡唤起） */}
      {showDouyinSheet && <DouyinLinkSheet onClose={() => setShowDouyinSheet(false)} />}
    </View>
  )
}
