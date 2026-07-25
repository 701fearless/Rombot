// DouyinLinkSheet：粘贴抖音链接识别浮层（拍板结论：「直达抖音」不做真外跳，
// 统一走「粘贴链接 → 识别流」；设计页第四端口/发现页单品卡/我的家家具库「+」卡共用）
import { Input, Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useEffect, useState } from 'react'
import './index.scss'

export interface DouyinLinkSheetProps {
  onClose: () => void
}

export default function DouyinLinkSheet({ onClose }: DouyinLinkSheetProps) {
  const [link, setLink] = useState('')

  // 打开即尝试读剪贴板预填（读不到留白手输；H5 降级属预期）
  useEffect(() => {
    Taro.getClipboardData({
      success: (res) => setLink(res.data?.trim() ?? ''),
      fail: () => {},
    })
  }, [])

  // 开始识别 → 识别流（入口B，sourceId 直达；空链接走模拟 sourceId 保证链路可跑通）
  const handleRecognize = () => {
    const sourceId = link.trim() || `dy_${Date.now().toString(36)}`
    onClose()
    Taro.navigateTo({
      url: `/pages/flow/recognize/index?sourceId=${encodeURIComponent(sourceId)}`,
    })
  }

  return (
    <View className='add-sheet' onClick={onClose}>
      <View className='add-sheet__panel' onClick={(e) => e.stopPropagation()}>
        <Text className='add-sheet__title'>粘贴抖音链接识别</Text>
        <View className='douyin-sheet__field emboss-inset'>
          <Input
            className='douyin-sheet__input'
            value={link}
            onInput={(e) => setLink(e.detail.value)}
            placeholder='把抖音视频/商品链接粘到这里'
          />
        </View>
        <View className='add-sheet__option' onClick={handleRecognize}>
          <Text className='add-sheet__option-title'>开始识别</Text>
          <Text className='add-sheet__option-desc'>AI 从链接里识别家具，识别完存入我的家</Text>
        </View>
        <View className='add-sheet__cancel' onClick={onClose}>
          <Text className='add-sheet__cancel-text'>取消</Text>
        </View>
      </View>
    </View>
  )
}
