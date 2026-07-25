import { Swiper, SwiperItem, Text, Video, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useCallback, useEffect, useRef, useState } from 'react'
import { feedVideos } from '@/data/feedVideos'
import { computeVideoDHash } from '@/lib/dhash'
import { detectPausedFrame, getPrebuiltAsset } from '@/services/backend'
import { useSceneStore } from '@/store'
import type { DetectedObject, DetectResponse } from '@/types/scene'
import type { FeedVideo } from '@/types'
import './index.scss'

interface FeedItemProps {
  video: FeedVideo
  active: boolean
  index: number
}

interface H5VideoHost extends HTMLElement {
  currentTime: number
}

function FeedItem({ video, active, index }: FeedItemProps) {
  const activeSceneId = useSceneStore((state) => state.activeSceneId)
  const setPendingAsset = useSceneStore((state) => state.setPendingAsset)
  const [paused, setPaused] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'empty' | 'error'>('idle')
  const [detection, setDetection] = useState<DetectResponse | null>(null)
  const [message, setMessage] = useState('')
  const requestId = useRef(0)
  const abortRef = useRef<AbortController | null>(null)
  const manuallyHandledPause = useRef(false)
  const videoElementId = `inspiration-video-${video.id}`

  const getH5VideoHost = () => document.getElementById(videoElementId) as H5VideoHost | null

  const cancelRecognition = useCallback(() => {
    requestId.current += 1
    abortRef.current?.abort()
    abortRef.current = null
  }, [])

  useEffect(() => {
    const context = Taro.createVideoContext(videoElementId)
    if (active) {
      context.play()
    } else {
      cancelRecognition()
      context.pause()
      setPaused(false)
      setDetection(null)
      setStatus('idle')
    }
  }, [active, cancelRecognition, videoElementId])

  useEffect(() => () => cancelRecognition(), [cancelRecognition])

  const recognize = async (time: number) => {
    const serial = ++requestId.current
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setStatus('loading')
    setDetection(null)
    setMessage('')
    let hash: string | undefined
    if (process.env.TARO_ENV === 'h5') {
      try {
        const element = getH5VideoHost()?.querySelector('video')
        if (element) hash = computeVideoDHash(element)
      } catch {
        hash = undefined
      }
    }
    try {
      const result = await detectPausedFrame(video.id, time, hash, controller.signal)
      if (serial !== requestId.current) return
      setDetection(result)
      setStatus(result.objects.length ? 'success' : 'empty')
    } catch (error) {
      if (controller.signal.aborted || serial !== requestId.current) return
      setMessage(error instanceof Error ? error.message : '识别暂时不可用')
      setStatus('error')
    } finally {
      if (serial === requestId.current) abortRef.current = null
    }
  }

  const togglePlayback = () => {
    const context = Taro.createVideoContext(videoElementId)
    if (paused) {
      context.play()
      return
    }

    if (process.env.TARO_ENV === 'h5') {
      const host = getH5VideoHost()
      if (host) {
        const time = host.currentTime || currentTime
        manuallyHandledPause.current = true
        context.pause()
        setPaused(true)
        void recognize(time)
        return
      }
    }
    context.pause()
  }

  const chooseObject = async (object: DetectedObject) => {
    if (!object.prebuiltGlbUrl || !detection) return
    try {
      Taro.showLoading({ title: '正在打开户型' })
      const prebuilt = await getPrebuiltAsset(detection.frameId, object.id)
      setPendingAsset({ videoId: video.id, time: currentTime, frameId: detection.frameId, detected: object, prebuilt })
      await Taro.navigateTo({
        url: `/pages/flow/place/index?sceneId=${encodeURIComponent(activeSceneId)}&frameId=${encodeURIComponent(detection.frameId)}&objectId=${encodeURIComponent(object.id)}`,
      })
    } catch (error) {
      Taro.showToast({ title: error instanceof Error ? error.message : '家具暂时不可用', icon: 'none' })
    } finally {
      Taro.hideLoading()
    }
  }

  return (
    <View className='feed-item'>
      <Video
        id={videoElementId}
        className='feed-item__video'
        src={video.videoUrl}
        autoplay={active}
        muted
        loop
        controls={false}
        showCenterPlayBtn={false}
        objectFit='cover'
        onTimeUpdate={(event) => setCurrentTime(Number(event.detail.currentTime || 0))}
        onPause={(event) => {
          setPaused(true)
          if (manuallyHandledPause.current) {
            manuallyHandledPause.current = false
            return
          }
          const host = process.env.TARO_ENV === 'h5' ? getH5VideoHost() : null
          const time = host?.currentTime ?? Number(event.detail.currentTime || currentTime)
          if (active) void recognize(time)
        }}
        onPlay={() => {
          manuallyHandledPause.current = false
          cancelRecognition()
          setPaused(false)
          setDetection(null)
          setStatus('idle')
        }}
      />
      <View className='feed-item__tap-layer' onClick={togglePlayback} />
      <View className='feed-item__shade' />

      <View className='feed-item__topline'>
        <Text className='feed-item__brand'>QQ House</Text>
        <Text className='feed-item__scene'>{activeSceneId.toUpperCase()}</Text>
      </View>

      {paused && status === 'loading' && (
        <View className='feed-item__recognition'><Text>识别中</Text></View>
      )}
      {paused && status === 'empty' && (
        <View className='feed-item__recognition' onClick={() => void recognize(currentTime)}>
          <Text>当前画面没有可用家具 · 重试</Text>
        </View>
      )}
      {paused && status === 'error' && (
        <View className='feed-item__recognition is-error' onClick={() => void recognize(currentTime)}>
          <Text>{message} · 重试</Text>
        </View>
      )}

      {paused && detection?.objects.map((object) => {
        const enabled = Boolean(object.prebuiltGlbUrl)
        return (
          <View
            key={object.id}
            className={`feed-tag ${enabled ? 'is-enabled' : 'is-disabled'}`}
            style={{ left: `${object.tagPosition[0] * 100}%`, top: `${object.tagPosition[1] * 100}%` }}
            onClick={() => enabled && void chooseObject(object)}
          >
            <View className='feed-tag__dot' />
            <Text className='feed-tag__label'>{object.name}</Text>
            {!enabled && <Text className='feed-tag__state'>模型未缓存</Text>}
          </View>
        )
      })}

      <View className='feed-item__copy'>
        <Text className='feed-item__author'>@{video.author}</Text>
        <Text className='feed-item__title'>{video.title}</Text>
        <View className='feed-item__meta'>
          <Text>离线识别</Text><View className='feed-item__meta-dot' /><Text>预生成 3D</Text>
        </View>
      </View>
      <View className='feed-item__counter'><Text>{index + 1}/{feedVideos.length}</Text></View>
    </View>
  )
}

export default function DiscoverPage() {
  const [current, setCurrent] = useState(0)
  return (
    <View className='video-feed-page'>
      <Swiper
        className='video-feed-page__swiper'
        vertical
        circular
        current={current}
        onChange={(event) => setCurrent(event.detail.current)}
      >
        {feedVideos.map((video, index) => (
          <SwiperItem key={video.id}>
            <FeedItem video={video} index={index} active={index === current} />
          </SwiperItem>
        ))}
      </Swiper>
    </View>
  )
}
