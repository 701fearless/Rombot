// Tab1 设计（2026-07-25 修订：页面收敛为纯入口）
// = 开屏动画（只播一次）+ 四端口 Hero：
//   立即扫描 → 接相机 → 识别流；上传平面图 → 选择照片/拍照 → 建空屋进摆放流；
//   选择模板空间 → switchTab「我的家」（空间资产库已挪到该 Tab）；
//   粘贴抖音链接识别 → 读剪贴板 → 识别流（入口B，sourceId 直达）
import { Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useState } from 'react'
import type { DetectedItem } from '@/components/HeroScan'
import EntryHero from '@/components/EntryHero'
import SplashScan from '@/components/SplashScan'
import { mockUser } from '@/mock'
import { useHomeStore } from '@/store'
import type { Home } from '@/types/models'
import { genId } from '@/utils/id'
// 开屏底图：import 引用才会被 webpack 打包进 dist（字符串路径不拷贝，会 404/500）
// TODO: 待视觉稿确认 - 替换 src/assets/hero-room.jpg 为你的正式底图即可
import heroRoomImg from '@/assets/hero-room.jpg'
import './index.scss'

// 开屏检测框：参照古典室内画布局（rect 为容器百分比），仅作开屏视觉，不可点击
const SPLASH_ITEMS: DetectedItem[] = [
  { id: 'd_vase', label: 'VASE_01', score: 0.914, rect: { x: 6, y: 30, w: 16, h: 24 } },
  { id: 'd_screen', label: 'SCREEN_02', score: 0.876, rect: { x: 4, y: 18, w: 34, h: 46 } },
  { id: 'd_mirror', label: 'MIRROR_03', score: 0.952, rect: { x: 24, y: 42, w: 16, h: 18 } },
  { id: 'd_chair', label: 'ARMCHAIR_04', score: 0.982, rect: { x: 4, y: 58, w: 34, h: 36 } },
  { id: 'd_lady', label: 'FIGURE_05', score: 0.997, rect: { x: 44, y: 26, w: 40, h: 66 } },
  { id: 'd_table', label: 'CONSOLE_06', score: 0.931, rect: { x: 72, y: 44, w: 24, h: 26 } },
]

// 开屏动画每次启动只播一次（切 Tab 回来不重播）
let splashPlayed = false

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
  const [showSplash, setShowSplash] = useState(!splashPlayed)
  const [showFloorplanSheet, setShowFloorplanSheet] = useState(false)

  const handleSplashDone = () => {
    splashPlayed = true
    setShowSplash(false)
  }

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
  const goTemplate = () => Taro.switchTab({ url: '/pages/myhome/index' })
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
    Taro.chooseImage({
      count: 1,
      sourceType: [source],
      success: () => createEmptyHomeAndEnter(),
      fail: () => {},
    })
  }

  return (
    <View className='remodel'>
      {/* 四端口 Hero：扫描大卡 + 平面图/模板空间两小卡 + 抖音链接识别大卡（本页唯一内容） */}
      <EntryHero
        onScan={goScan}
        onFloorplan={goFloorplan}
        onTemplate={goTemplate}
        onDouyin={goDouyin}
      />

      {/* 上传平面图动作层：选择照片 / 拍照 */}
      {showFloorplanSheet && (
        <View className='add-sheet' onClick={() => setShowFloorplanSheet(false)}>
          <View className='add-sheet__panel' onClick={(e) => e.stopPropagation()}>
            <Text className='add-sheet__title'>上传平面图</Text>
            <View className='add-sheet__option' onClick={() => pickFloorplan('album')}>
              <Text className='add-sheet__option-title'>选择照片</Text>
              <Text className='add-sheet__option-desc'>从相册挑一张户型图，AI 帮你建空屋</Text>
            </View>
            <View className='add-sheet__option' onClick={() => pickFloorplan('camera')}>
              <Text className='add-sheet__option-title'>拍照</Text>
              <Text className='add-sheet__option-desc'>直接拍下手边或屏幕上的户型图</Text>
            </View>
            <View className='add-sheet__cancel' onClick={() => setShowFloorplanSheet(false)}>
              <Text className='add-sheet__cancel-text'>取消</Text>
            </View>
          </View>
        </View>
      )}

      {/* 开屏动画：盖在最上层，播完淡出卸载（每次启动只播一次） */}
      {showSplash && (
        <SplashScan
          imageUrl={heroRoomImg}
          items={SPLASH_ITEMS}
          title='让每件家具，找到它的房间'
          subtitle='截图识别 · 放进我家 · AI 配齐整屋'
          onDone={handleSplashDone}
        />
      )}
    </View>
  )
}
