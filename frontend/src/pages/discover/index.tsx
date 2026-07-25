// Tab1 灵感：房屋记忆 + 家具资产架 + 可按家居类型筛选的 Feed
// Feed 单品 / 资产架家具 → 详情 → 放进我家（识别流），即从灵感页选家具跳转摆放链路
import { Image, ScrollView, Text, View } from '@tarojs/components'
import Taro, { useDidShow, usePullDownRefresh } from '@tarojs/taro'
import { useCallback, useMemo, useState } from 'react'
import AppHeader from '@/components/AppHeader'
import CoverImage from '@/components/CoverImage'
import Reveal from '@/components/Reveal'
import SectionTitle from '@/components/SectionTitle'
import { fetchFurnitureList } from '@/services/furniture'
import { useHomeStore } from '@/store'
import type { Furniture } from '@/types/models'
import { logSignal } from '@/utils/signal'
import spaceModelImg from '@/assets/space-3d-living.png'
import './index.scss'

const FURNITURE_FILTERS = [
  { label: '全部', value: '全部' },
  { label: '沙发', value: '沙发' },
  { label: '床', value: '床' },
  { label: '桌', value: '桌' },
  { label: '椅', value: '椅' },
  { label: '柜', value: '柜' },
  { label: '灯', value: '灯' },
  { label: '婴儿', value: '婴儿床' },
  { label: '宠物', value: '宠物家具' },
]

export default function DiscoverPage() {
  const [feed, setFeed] = useState<Furniture[]>([])
  const [feedLoading, setFeedLoading] = useState(true)
  const [activeFilter, setActiveFilter] = useState('全部')
  const homes = useHomeStore((state) => state.homes)
  const rooms = useHomeStore((state) => state.rooms)
  const placements = useHomeStore((state) => state.placements)

  const loadFeed = useCallback(async () => {
    setFeedLoading(true)
    const list = await fetchFurnitureList()
    setFeed(list)
    setFeedLoading(false)
  }, [])

  useDidShow(() => {
    loadFeed()
  })

  usePullDownRefresh(async () => {
    await loadFeed()
    Taro.stopPullDownRefresh()
  })

  const memory = useMemo(() => {
    const latestPlacement = placements[placements.length - 1]
    const historyRoom = rooms.find((room) => room.id === latestPlacement?.roomId)
    const exampleRoom = rooms.find((room) => {
      const home = homes.find((item) => item.id === room.homeId)
      return home?.type === 'template' && room.name === '客厅'
    })
    const room = historyRoom ?? exampleRoom ?? rooms[0]
    const home = homes.find((item) => item.id === room?.homeId)
    const itemCount = room
      ? placements.filter((placement) => placement.roomId === room.id).length
      : 0

    return {
      home,
      room,
      itemCount,
      isExample: !historyRoom,
    }
  }, [homes, placements, rooms])

  const goMemory = () => {
    if (!memory.home || !memory.room) {
      Taro.switchTab({ url: '/pages/myhome/index' })
      return
    }
    Taro.navigateTo({
      url: `/pages/flow/place/index?homeId=${memory.home.id}&roomId=${memory.room.id}`,
    })
  }

  const goDetail = (f: Furniture) => {
    logSignal('view_category', { category: f.category })
    Taro.navigateTo({ url: `/pages/discover/detail/index?id=${f.id}` })
  }

  // 家具资产架保留快速入口；家居类型筛选只控制下方 Feed，位置和反馈更直接。
  const minPrice = (f: Furniture) => Math.min(...f.priceRefs.map((p) => p.price))
  const filteredFeed = useMemo(
    () =>
      activeFilter === '全部'
        ? feed
        : feed.filter((furniture) => furniture.category === activeFilter),
    [activeFilter, feed],
  )

  return (
    <View className="discover">
      <AppHeader title="QQ House" />

      <View className="discover__memory-section">
        <SectionTitle title="房屋记忆" subtitle="从上次停下的地方继续布置" />
        <View className="discover__memory" onClick={goMemory}>
          <Image className="discover__memory-image" src={spaceModelImg} mode="aspectFill" />
          <View className="discover__memory-veil" />
          <View className="discover__memory-copy">
            <Text className="discover__memory-kicker">
              {memory.isExample ? '示例建模' : '上次布置'}
            </Text>
            <Text className="discover__memory-title">
              {memory.home && memory.room
                ? `${memory.home.name} · ${memory.room.name}`
                : '法式复古客厅'}
            </Text>
            <Text className="discover__memory-meta">
              {memory.itemCount > 0 ? `${memory.itemCount} 件家具` : '可自由试摆'} · 真实比例
            </Text>
          </View>
          <View className="discover__memory-action">
            <Text className="discover__memory-action-text">继续布置</Text>
          </View>
        </View>
      </View>

      {/* 灵感 Feed */}
      <View className="discover__section">
        <SectionTitle title="灵感 Feed" subtitle="刷到喜欢的，直接放进我家" />
        <View className="discover__filter-head">
          <Text className="discover__filter-label">家居类型</Text>
          <Text className="discover__filter-count">{filteredFeed.length} 件灵感</Text>
        </View>
        <ScrollView scrollX className="discover__filters" enhanced showScrollbar={false}>
          <View className="discover__filter-rail">
            {FURNITURE_FILTERS.map((filter) => (
              <View
                key={filter.value}
                className={`discover__filter ${activeFilter === filter.value ? 'is-active' : ''}`}
                onClick={() => setActiveFilter(filter.value)}
              >
                <Text
                  className={`discover__filter-text ${activeFilter === filter.value ? 'is-active' : ''}`}
                >
                  {filter.label}
                </Text>
              </View>
            ))}
          </View>
        </ScrollView>
        <View className="discover__feed">
          {feedLoading ? (
            // 骨架屏：加载期占位，禁白屏
            Array.from({ length: 4 }).map((_, i) => (
              <View key={`sk_${i}`} className="discover__card emboss">
                <View className="discover__card-skel-img" />
                <View className="discover__card-skel-line" />
              </View>
            ))
          ) : filteredFeed.length === 0 ? (
            <View className="discover__empty">
              <Text className="discover__empty-text">这个分类还没有内容，先看看其他灵感</Text>
            </View>
          ) : (
            filteredFeed.map((f, i) => (
              // 滚动进入视口 fade-rise（P1-3），同屏最多 4 张 stagger
              <Reveal
                key={f.id}
                className="discover__card emboss"
                delay={(i % 4) * 70}
                onClick={() => goDetail(f)}
              >
                <CoverImage src={f.coverUrl} title={f.title} ratio="4 / 3" />
                <View className="discover__card-body">
                  <View className="discover__card-title">{f.title}</View>
                  <View className="discover__card-price">¥{minPrice(f).toLocaleString()} 起</View>
                </View>
              </Reveal>
            ))
          )}
        </View>
      </View>
    </View>
  )
}
