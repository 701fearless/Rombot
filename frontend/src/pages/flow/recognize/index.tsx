// 识别流：双入口汇入（入口A 上传 / 入口B 带 sourceId）
// ★锚点1：识别完成立即 addAsset 落库（绑 ownerId，退出不丢）
// 低置信度 → 兜底通用模板，永不空结果；入口B 落库 = 轻提示，无飞入动画（PRD 2.4④）
import { Text, View } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import { useEffect, useState } from 'react'
import AppHeader from '@/components/AppHeader'
import CoverImage from '@/components/CoverImage'
import EmbossCard from '@/components/EmbossCard'
import { mockFurniture, mockUser } from '@/mock'
import { recognizeBySourceId, recognizeByUpload } from '@/services/recognize'
import { useAssetStore, useHomeStore } from '@/store'
import type { Asset, Furniture } from '@/types/models'
import { genId } from '@/utils/id'
import './index.scss'

// 置信度阈值：低于此值展示"通用模板"提示（与 services 保持一致）
const CONFIDENCE_THRESHOLD = 0.6

type Phase = 'idle' | 'scanning' | 'done'

export default function RecognizePage() {
  const { params } = useRouter()
  const addAsset = useAssetStore((s) => s.addAsset)
  const { homes, rooms } = useHomeStore()

  const [phase, setPhase] = useState<Phase>('idle')
  const [result, setResult] = useState<{ asset: Asset; furniture: Furniture; confidence: number }>()
  const [showHomePicker, setShowHomePicker] = useState(false)
  const [selectedRoomId, setSelectedRoomId] = useState('')

  // 入口B：页面参数带 sourceId（抖音挂车/评论链接跳入）→ 自动开始识别
  useEffect(() => {
    if (params.sourceId) {
      runRecognize('B_link', params.sourceId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const runRecognize = async (source: Asset['source'], sourceRefId?: string) => {
    setPhase('scanning')
    setResult(undefined)
    const r = sourceRefId
      ? await recognizeBySourceId(sourceRefId)
      : await recognizeByUpload()
    // ★锚点1：立即落库，绑 unionId，此后杀掉小程序重进资产仍在
    const asset: Asset = {
      id: genId('asset'),
      ownerId: mockUser.unionId,
      furnitureId: r.furnitureId,
      source,
      sourceRefId,
      status: 'recognized',
      createdAt: Date.now(),
    }
    addAsset(asset)
    const furniture = mockFurniture.find((f) => f.id === r.furnitureId) ?? mockFurniture[0]
    setResult({ asset, furniture, confidence: r.confidence })
    setPhase('done')
    // 入口B：直接落库 + 轻提示，不做飞入动画
    if (source === 'B_link') {
      Taro.showToast({ title: '已存入我的家', icon: 'none' })
    }
  }

  // 入口A：上传截图（选不到图片也走模拟识别流程，保证骨架可跑通）
  const handleUpload = () => {
    Taro.chooseImage({
      count: 1,
      success: () => runRecognize('A_upload'),
      fail: () => runRecognize('A_upload'),
    })
  }

  const handleMockLink = () => runRecognize('B_link', `dy_${Date.now().toString(36)}`)

  const handlePlace = () => {
    if (!result || !selectedRoomId) return
    Taro.navigateTo({
      url: `/pages/flow/place/index?roomId=${selectedRoomId}&assetId=${result.asset.id}`,
    })
  }

  return (
    <View className='recognize'>
      <AppHeader title='QQ House' />
      {phase === 'idle' && (
        <View className='recognize__entries animate-fade-rise'>
          <Text className='recognize__hint'>刷到喜欢的家具？两种方式把它变成你的资产</Text>
          <EmbossCard className='recognize__entry' onClick={handleUpload}>
            <Text className='recognize__entry-title'>上传截图识别</Text>
            <Text className='recognize__entry-desc'>相册/截图中的家具，AI 帮你找出来</Text>
          </EmbossCard>
          <EmbossCard className='recognize__entry' onClick={handleMockLink}>
            <Text className='recognize__entry-title'>模拟抖音链接进入</Text>
            <Text className='recognize__entry-desc'>挂车/评论链接携带 sourceId 直达识别</Text>
          </EmbossCard>
        </View>
      )}

      {phase === 'scanning' && (
        // 识别中：liquid-glass 浮层 + 扫描动效（PRD 2.4①），禁白屏
        <View className='recognize__scanning liquid-glass'>
          <View className='recognize__scan-pulse' />
          <Text className='recognize__scan-text'>AI 识别中…</Text>
          <Text className='recognize__scan-sub'>正在匹配家具 SKU 库</Text>
        </View>
      )}

      {phase === 'done' && result && (
        <View className='recognize__result animate-fade-rise'>
          {/* 低置信度兜底提示（PRD 5.1：永不空结果） */}
          {result.confidence < CONFIDENCE_THRESHOLD && (
            <View className='recognize__fallback'>
              <Text className='recognize__fallback-text'>
                未精确识别，已为你匹配通用模板（可继续摆放）
              </Text>
            </View>
          )}

          <EmbossCard className='recognize__card'>
            <CoverImage src={result.furniture.coverUrl} title={result.furniture.title} ratio='4 / 3' />
            <View className='recognize__card-body'>
              <Text className='recognize__card-title'>{result.furniture.title}</Text>
              <Text className='recognize__card-meta'>
                {result.furniture.category} · 置信度 {(result.confidence * 100).toFixed(0)}% ·
                已存入我的家
              </Text>
            </View>
          </EmbossCard>

          {/* 放进我家：选择房间 → 摆放流 */}
          {!showHomePicker ? (
            <View className='recognize__actions'>
              <View className='recognize__cta' onClick={() => setShowHomePicker(true)}>
                <Text className='recognize__cta-text'>放进我家</Text>
              </View>
              <View className='recognize__back' onClick={() => Taro.navigateBack()}>
                <Text className='recognize__back-text'>再看看</Text>
              </View>
            </View>
          ) : (
            <View className='recognize__picker'>
              <Text className='recognize__picker-title'>选择要放入的房间</Text>
              {homes.map((h) => (
                <View key={h.id} className='recognize__picker-group'>
                  <Text className='recognize__picker-home'>{h.name}</Text>
                  <View className='recognize__picker-rooms'>
                    {rooms
                      .filter((r) => r.homeId === h.id)
                      .map((r) => (
                        <View
                          key={r.id}
                          className={`recognize__room-pill ${
                            selectedRoomId === r.id ? 'is-active' : ''
                          }`}
                          onClick={() => setSelectedRoomId(r.id)}
                        >
                          <Text
                            className={`recognize__room-pill-text ${
                              selectedRoomId === r.id ? 'is-active' : ''
                            }`}
                          >
                            {r.name}
                          </Text>
                        </View>
                      ))}
                  </View>
                </View>
              ))}
              {selectedRoomId && (
                <View className='recognize__cta' onClick={handlePlace}>
                  <Text className='recognize__cta-text'>去摆放</Text>
                </View>
              )}
            </View>
          )}
        </View>
      )}
    </View>
  )
}
