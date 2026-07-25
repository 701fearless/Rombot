// 场景详情页（MVP 四场景：养宠/养娃/风水/动线，结合具体场景需求做改造）
// 结构：场景大图 + 方向角标 → 标题收藏 → 场景需求解读 → 改造要点 → 家具元素 → 底部 CTA
// CTA「按这个场景改我的家」→ 摆放页（带 direction，place 页不再自动弹操作台浮窗）
import { Text, View } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import { useEffect, useState } from 'react'
import AppHeader from '@/components/AppHeader'
import CoverImage from '@/components/CoverImage'
import { fetchSceneById } from '@/services/scene'
import { fetchFurnitureById } from '@/services/furniture'
import { useHomeStore } from '@/store'
import type { Furniture, ID, Scene } from '@/types/models'
import './index.scss'

interface ResolvedItem {
  furniture: Furniture
  note?: string
}

export default function ScenePage() {
  const { params } = useRouter()
  const { homes, rooms } = useHomeStore()
  const [scene, setScene] = useState<Scene | undefined>()
  const [items, setItems] = useState<ResolvedItem[]>([])
  const [faved, setFaved] = useState(false)

  useEffect(() => {
    if (!params.id) return
    fetchSceneById(params.id).then(async (s) => {
      setScene(s)
      if (!s) return
      // 并发把每件家具元素解析成完整 Furniture（带 note）
      const resolved = await Promise.all(
        s.items.map(async (it) => ({
          furniture: (await fetchFurnitureById(it.furnitureId))!,
          note: it.note,
        })),
      )
      setItems(resolved.filter((r) => !!r.furniture))
    })
  }, [params.id])

  const goDetail = (id: ID) => {
    Taro.navigateTo({ url: `/pages/discover/detail/index?id=${id}` })
  }

  // CTA：按场景方向直接改（回落首要家第一个房间；place 页带 direction 不自动弹浮窗）
  const handleEdit = () => {
    if (!scene) return
    const home = homes.find((h) => h.isPrimary) ?? homes[0]
    const room = rooms.find((r) => r.homeId === home?.id)
    Taro.navigateTo({
      url: `/pages/flow/place/index?homeId=${home?.id ?? ''}&roomId=${room?.id ?? ''}&direction=${scene.direction}`,
    })
  }

  if (!scene) {
    // 加载骨架，禁白屏
    return (
      <View className='scene'>
        <AppHeader title='QQ House' />
        <View className='scene__skel-img' />
        <View className='scene__skel-line' />
        <View className='scene__skel-line scene__skel-line--short' />
      </View>
    )
  }

  return (
    <View className='scene'>
      <AppHeader title='QQ House' />
      {/* 场景大图 + 方向角标 */}
      <View className='scene__hero'>
        <CoverImage src={scene.coverUrl} title={scene.title} ratio='4 / 3' />
        <View className='scene__hero-tag'>
          <Text className='scene__hero-tag-text'>{scene.direction}场景</Text>
        </View>
      </View>

      {/* 标题 + 收藏 */}
      <View className='scene__header'>
        <Text className='scene__title'>{scene.title}</Text>
        <View className='scene__fav' onClick={() => setFaved((v) => !v)}>
          <Text className={`scene__fav-text ${faved ? 'is-faved' : ''}`}>
            {faved ? '♥' : '♡'}
          </Text>
        </View>
      </View>

      {/* 场景需求解读 */}
      {scene.description && <Text className='scene__desc'>{scene.description}</Text>}

      {/* 改造要点（序号陈列） */}
      <View className='scene__section'>
        <Text className='scene__section-title'>改造要点</Text>
        {scene.points.map((p, i) => (
          <View key={i} className='scene__point emboss'>
            <Text className='scene__point-num'>{i + 1}</Text>
            <Text className='scene__point-text'>{p}</Text>
          </View>
        ))}
      </View>

      {/* 家具元素列表 */}
      <View className='scene__section'>
        <Text className='scene__section-title'>家具元素</Text>
        {items.map(({ furniture, note }) => (
          <View
            key={furniture.id}
            className='scene__item'
            onClick={() => goDetail(furniture.id)}
          >
            <CoverImage
              src={furniture.coverUrl}
              title={furniture.title}
              ratio='1 / 1'
              className='scene__item-thumb'
            />
            <View className='scene__item-body'>
              <Text className='scene__item-title'>{furniture.title}</Text>
              {note && <Text className='scene__item-note'>{note}</Text>}
            </View>
            <Text className='scene__item-arrow'>›</Text>
          </View>
        ))}
      </View>

      {/* 底部 CTA：按这个场景改我的家（黄底蓝字，与全局 CTA 同语言） */}
      <View className='scene__cta' onClick={handleEdit}>
        <Text className='scene__cta-text'>按这个场景改我的家</Text>
      </View>
    </View>
  )
}
