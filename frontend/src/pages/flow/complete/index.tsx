// 整屋补全流：以锚点单品为基准，AI 配齐整屋 → 批量 Asset + Placement 落库
import { Text, View } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import { useEffect, useState } from 'react'
import AppHeader from '@/components/AppHeader'
import CoverImage from '@/components/CoverImage'
import { mockFurniture, mockUser } from '@/mock'
import { fetchCompleteRoom } from '@/services/ai'
import { useAssetStore, useHomeStore } from '@/store'
import type { Furniture } from '@/types/models'
import { genId } from '@/utils/id'
import './index.scss'

export default function CompletePage() {
  const { params } = useRouter()
  const addAsset = useAssetStore((s) => s.addAsset)
  const addPlacement = useHomeStore((s) => s.addPlacement)

  const [loading, setLoading] = useState(true)
  const [items, setItems] = useState<Furniture[]>([])
  // 可勾选剔除（默认全选）
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set())

  useEffect(() => {
    fetchCompleteRoom(params.roomId ?? '', params.assetId ?? '').then((ids) => {
      const list = ids
        .map((id) => mockFurniture.find((f) => f.id === id))
        .filter((f): f is Furniture => Boolean(f))
      setItems(list)
      setCheckedIds(new Set(list.map((f) => f.id)))
      setLoading(false)
    })
  }, [params.roomId, params.assetId])

  const toggle = (id: string) => {
    setCheckedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const handleConfirm = () => {
    const picked = items.filter((f) => checkedIds.has(f.id))
    // 批量落库：每件 = 1 个 Asset + 1 个 Placement（网格均分坐标，避免重叠）
    picked.forEach((f, i) => {
      const assetId = genId('asset')
      addAsset({
        id: assetId,
        ownerId: mockUser.unionId,
        furnitureId: f.id,
        source: 'A_upload', // 补全产物沿用上传入口语义
        status: 'placed',
        createdAt: Date.now(),
      })
      addPlacement({
        id: genId('placement'),
        roomId: params.roomId ?? '',
        assetId,
        transform: { x: 40 + (i % 3) * 110, y: 40 + Math.floor(i / 3) * 110, rotate: 0, scale: 1 },
        isExisting: false,
      })
    })
    Taro.showToast({ title: `已配齐 ${picked.length} 件`, icon: 'none' })
    setTimeout(() => Taro.navigateBack(), 600)
  }

  const minPrice = (f: Furniture) => Math.min(...f.priceRefs.map((p) => p.price))

  return (
    <View className='complete'>
      <AppHeader title='QQ House' />
      <View className='complete__header'>
        <Text className='complete__title'>AI 为你配齐整屋</Text>
        <Text className='complete__subtitle'>以锚点单品为基准的搭配推荐，可勾选剔除</Text>
      </View>

      {loading ? (
        <View className='complete__list'>
          {Array.from({ length: 4 }).map((_, i) => (
            <View key={i} className='complete__skel emboss' />
          ))}
        </View>
      ) : (
        <View className='complete__list'>
          {items.map((f) => (
            <View key={f.id} className='complete__item emboss' onClick={() => toggle(f.id)}>
              <View className='complete__item-cover'>
                <CoverImage src={f.coverUrl} title={f.title} ratio='1 / 1' />
              </View>
              <View className='complete__item-info'>
                <Text className='complete__item-title'>{f.title}</Text>
                <Text className='complete__item-meta'>
                  {f.category} · ¥{minPrice(f).toLocaleString()} 起
                </Text>
              </View>
              <View
                className={`complete__checkbox ${checkedIds.has(f.id) ? 'is-checked' : ''}`}
              >
                <Text className='complete__checkbox-text'>
                  {checkedIds.has(f.id) ? '✓' : ''}
                </Text>
              </View>
            </View>
          ))}
        </View>
      )}

      {!loading && (
        <View className='complete__confirm' onClick={handleConfirm}>
          <Text className='complete__confirm-text'>
            确认配齐（{checkedIds.size} 件）
          </Text>
        </View>
      )}
    </View>
  )
}
