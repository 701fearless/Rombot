// 单品详情页：轮播大图 + 描述 + 颜色/材质色卡 + 收藏 + 「放进我家」唤起识别流
// 视频复现：图片轮播圆点、颜色/材质可选色卡、右上 AR 摆放入口（后端未就绪，先做占位）
// 埋点（PRD 第 6 节）：收藏婴儿床 → fav_babybed；宠物家具浏览 ≥3 次 → view_pet_furniture
// 2026-07-25：多渠道比价区块随比价线下线删除，变现出口收敛为「直达抖音商城外跳」
import { Text, View } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import { useEffect, useMemo, useState } from 'react'
import AppHeader from '@/components/AppHeader'
import CoverImage from '@/components/CoverImage'
import { fetchFurnitureById } from '@/services/furniture'
import type { Furniture } from '@/types/models'
import { logSignal } from '@/utils/signal'
import './index.scss'

// 宠物家具浏览计数的 Storage key（≥3 次触发画像信号）
const PET_VIEW_KEY = 'pet_view_count'

export default function DetailPage() {
  const { params } = useRouter()
  const [furniture, setFurniture] = useState<Furniture | undefined>()
  const [faved, setFaved] = useState(false)
  // 轮播当前帧 / 颜色、材质当前选中项（默认第一个）
  const [imgIndex, setImgIndex] = useState(0)
  const [colorIndex, setColorIndex] = useState(0)
  const [materialIndex, setMaterialIndex] = useState(0)

  useEffect(() => {
    if (!params.id) return
    fetchFurnitureById(params.id).then((f) => {
      setFurniture(f)
      // 埋点：反复浏览宠物家具（≥3 次）
      if (f?.category === '宠物家具') {
        const count = Number(Taro.getStorageSync(PET_VIEW_KEY) || 0) + 1
        Taro.setStorageSync(PET_VIEW_KEY, count)
        if (count >= 3) logSignal('view_pet_furniture', { furnitureId: f.id, count })
      }
    })
  }, [params.id])

  const handleFav = () => {
    if (!furniture) return
    setFaved((v) => !v)
    // 埋点：收藏婴儿床/儿童家具
    if (!faved && furniture.category === '婴儿床') {
      logSignal('fav_babybed', { furnitureId: furniture.id })
    }
    Taro.showToast({ title: faved ? '已取消收藏' : '已收藏', icon: 'none' })
  }

  // 轮播图集：优先 images，空则退回 coverUrl 单张
  const images = useMemo(
    () => furniture?.images?.length ? furniture.images : [furniture?.coverUrl ?? ''],
    [furniture],
  )

  const handleAR = () => {
    // AR 摆放：后端未实现，先做入口占位（与「放进我家」同链路，唤起识别流）
    if (!furniture) return
    Taro.navigateTo({ url: `/pages/flow/recognize/index?furnitureId=${furniture.id}` })
  }

  if (!furniture) {
    // 加载骨架，禁白屏
    return (
      <View className='detail'>
        <AppHeader title='QQ House' />
        <View className='detail__skel-img' />
        <View className='detail__skel-line' />
        <View className='detail__skel-line detail__skel-line--short' />
      </View>
    )
  }

  return (
    <View className='detail'>
      <AppHeader title='QQ House' />
      {/* 大图轮播区：图 + 轮播圆点 + 右上 AR 摆放入口（占位） */}
      <View className='detail__hero'>
        <CoverImage
          key={imgIndex}
          src={images[imgIndex]}
          title={furniture.title}
          ratio='4 / 3'
        />
        <View className='detail__ar' onClick={handleAR}>
          <Text className='detail__ar-text'>AR 摆放</Text>
        </View>
        {images.length > 1 && (
          <View className='detail__dots'>
            {images.map((_, i) => (
              <View
                key={i}
                className={`detail__dot ${i === imgIndex ? 'is-active' : ''}`}
                onClick={() => setImgIndex(i)}
              />
            ))}
          </View>
        )}
      </View>

      <View className='detail__header'>
        <Text className='detail__title'>{furniture.title}</Text>
        <Text className='detail__category'>{furniture.category}</Text>
      </View>

      {/* 描述（视频复现） */}
      {furniture.description && (
        <Text className='detail__desc'>{furniture.description}</Text>
      )}

      {/* 颜色色卡（视频复现：一排圆形色块，可点选） */}
      {!!furniture.colors?.length && (
        <View className='detail__section'>
          <Text className='detail__section-title'>颜色</Text>
          <View className='detail__swatches'>
            {furniture.colors.map((c, i) => (
              <View
                key={c.name}
                className={`detail__swatch ${i === colorIndex ? 'is-active' : ''}`}
                onClick={() => setColorIndex(i)}
              >
                <View className='detail__swatch-inner' style={{ background: c.hex }} />
              </View>
            ))}
          </View>
          <Text className='detail__swatch-name'>{furniture.colors[colorIndex]?.name}</Text>
        </View>
      )}

      {/* 材质色卡（视频复现：一排圆形材质块，可点选） */}
      {!!furniture.materials?.length && (
        <View className='detail__section'>
          <Text className='detail__section-title'>材质</Text>
          <View className='detail__swatches'>
            {furniture.materials.map((m, i) => (
              <View
                key={m.name}
                className={`detail__swatch ${i === materialIndex ? 'is-active' : ''}`}
                onClick={() => setMaterialIndex(i)}
              >
                <View
                  className='detail__swatch-inner'
                  style={{ background: m.hex ?? 'var(--color-bg-secondary)' }}
                />
              </View>
            ))}
          </View>
          <Text className='detail__swatch-name'>
            {furniture.materials[materialIndex]?.name}
          </Text>
        </View>
      )}

      {/* 操作栏：收藏 + 放进我家（主 CTA，对比度 ≥ 4.5:1） */}
      <View className='detail__actions'>
        <View className='detail__fav' onClick={handleFav}>
          <Text className={`detail__fav-text ${faved ? 'is-faved' : ''}`}>
            {faved ? '♥ 已收藏' : '♡ 收藏'}
          </Text>
        </View>
        <View
          className='detail__cta'
          onClick={() =>
            Taro.navigateTo({
              url: `/pages/flow/recognize/index?furnitureId=${furniture.id}`,
            })
          }
        >
          <Text className='detail__cta-text'>放进我家</Text>
        </View>
      </View>
    </View>
  )
}
