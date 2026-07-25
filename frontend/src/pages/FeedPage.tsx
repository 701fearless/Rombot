import { AlertCircle, LoaderCircle, Pause, Volume2, VolumeX } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useToast } from '@/components/ToastProvider'
import { feedVideos } from '@/data/feedVideos'
import { computeVideoDHash } from '@/lib/dhash'
import { coverTagPosition } from '@/lib/geometry'
import { detectPausedFrame, getPrebuiltAsset } from '@/services/backend'
import { useSceneStore } from '@/store'
import type { FeedVideo } from '@/types/feed'
import type { DetectResponse, DetectedObject } from '@/types/scene'

interface Size { width: number; height: number }
function FeedCard({ video, active, index }: { video: FeedVideo; active: boolean; index: number }) {
  const navigate = useNavigate(); const toast = useToast(); const activeSceneId = useSceneStore((s) => s.activeSceneId); const setPendingAsset = useSceneStore((s) => s.setPendingAsset)
  const rootRef = useRef<HTMLElement>(null); const videoRef = useRef<HTMLVideoElement>(null); const abortRef = useRef<AbortController | null>(null); const serialRef = useRef(0)
  const [paused, setPaused] = useState(true); const [muted, setMuted] = useState(true); const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'empty' | 'error'>('idle'); const [message, setMessage] = useState(''); const [detection, setDetection] = useState<DetectResponse | null>(null); const [pausedAt, setPausedAt] = useState(0); const [containerSize, setContainerSize] = useState<Size>({ width: 0, height: 0 }); const [sourceSize, setSourceSize] = useState<Size>({ width: 0, height: 0 })
  const cancelRecognition = useCallback(() => { serialRef.current += 1; abortRef.current?.abort(); abortRef.current = null; setDetection(null); setStatus('idle') }, [])
  useEffect(() => { const root = rootRef.current; if (!root) return; const resize = () => setContainerSize({ width: root.clientWidth, height: root.clientHeight }); resize(); const observer = new ResizeObserver(resize); observer.observe(root); return () => observer.disconnect() }, [])
  useEffect(() => { const element = videoRef.current; if (!element) return; if (active) void element.play().catch(() => setPaused(true)); else { element.pause(); cancelRecognition() } }, [active, cancelRecognition])
  useEffect(() => () => abortRef.current?.abort(), [])
  const recognize = useCallback(async () => {
    const element = videoRef.current; if (!element || !active || element.readyState < 2) return
    const time = element.currentTime; const serial = ++serialRef.current; abortRef.current?.abort(); const controller = new AbortController(); abortRef.current = controller
    setPausedAt(time); setDetection(null); setStatus('loading'); setMessage('')
    let hash: string | undefined; try { hash = computeVideoDHash(element) } catch { hash = undefined }
    try { const result = await detectPausedFrame(video.id, time, hash, controller.signal); if (serial !== serialRef.current || !element.paused) return; setDetection(result); setStatus(result.objects.length ? 'success' : 'empty') }
    catch (reason) { if (controller.signal.aborted || serial !== serialRef.current) return; setMessage(reason instanceof Error ? reason.message : '识别暂时不可用'); setStatus('error') }
  }, [active, video.id])
  const chooseObject = async (object: DetectedObject) => {
    if (!object.prebuiltGlbUrl || !detection) return
    try { const prebuilt = await getPrebuiltAsset(detection.frameId, object.id); setPendingAsset({ videoId: video.id, time: pausedAt, frameId: detection.frameId, detected: object, prebuilt }); navigate(`/space?${new URLSearchParams({ sceneId: activeSceneId, frameId: detection.frameId, objectId: object.id })}`) }
    catch (reason) { toast.show(reason instanceof Error ? reason.message : '家具暂时不可用') }
  }
  return <article ref={rootRef} className='feed-card' data-feed-index={index}>
    <video ref={videoRef} className='feed-card__video' src={video.videoUrl} poster={video.coverUrl} muted={muted} playsInline loop preload={active ? 'auto' : 'metadata'} onLoadedMetadata={(event) => setSourceSize({ width: event.currentTarget.videoWidth, height: event.currentTarget.videoHeight })} onCanPlay={(event) => { if (active && event.currentTarget.paused) void event.currentTarget.play().catch(() => undefined) }} onPause={() => { setPaused(true); if (active) void recognize() }} onPlay={() => { setPaused(false); cancelRecognition() }} onSeeking={cancelRecognition} />
    <button className='feed-card__tap' type='button' aria-label={paused ? '继续播放' : '暂停识别'} onClick={() => { const element = videoRef.current; if (!element) return; if (element.paused) void element.play(); else element.pause() }} />
    <div className='feed-card__shade' /><header className='feed-card__header'><strong>QQ HOUSE</strong><span>{activeSceneId.toUpperCase()}</span></header>
    <button className='feed-card__sound' type='button' onClick={() => setMuted((v) => !v)} aria-label={muted ? '打开声音' : '静音'}>{muted ? <VolumeX /> : <Volume2 />}</button>
    {paused && status === 'idle' && <div className='feed-card__pause'><Pause /></div>}
    {status === 'loading' && <div className='feed-status'><LoaderCircle className='spin' />正在匹配家具</div>}
    {(status === 'empty' || status === 'error') && <button className='feed-status is-action' type='button' onClick={() => void recognize()}>{status === 'error' && <AlertCircle />}{message || '当前画面没有可用家具'} · 重试</button>}
    {paused && detection?.objects.map((object) => {
      const point = coverTagPosition(object.tagPosition, sourceSize, containerSize)
      const visible = point.x >= 16 && point.x <= containerSize.width - 120 && point.y >= 76 && point.y <= containerSize.height - 120
      if (!visible) return null
      return <button key={object.id} className={`feed-tag ${object.prebuiltGlbUrl ? '' : 'is-disabled'}`} type='button' disabled={!object.prebuiltGlbUrl} style={{ left: point.x, top: point.y }} onClick={() => void chooseObject(object)}><span className='feed-tag__dot' /><span>{object.name}</span><small>{object.prebuiltGlbUrl ? '放进户型' : '模型未缓存'}</small></button>
    })}
    <footer className='feed-card__copy'><strong>@{video.author}</strong><h1>{video.title}</h1><p>暂停视频，点选喜欢的家具</p><div>{video.furnitureHints.map((hint) => <span key={hint}>#{hint}</span>)}</div></footer><span className='feed-card__counter'>{index + 1}/{feedVideos.length}</span>
  </article>
}
export function FeedPage() {
  const rootRef = useRef<HTMLDivElement>(null); const [activeIndex, setActiveIndex] = useState(0)
  useEffect(() => { const root = rootRef.current; if (!root) return; const observer = new IntersectionObserver((entries) => { const current = entries.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]; const index = Number((current?.target as HTMLElement | undefined)?.dataset.feedIndex); if (current?.intersectionRatio && current.intersectionRatio > .62 && Number.isInteger(index)) setActiveIndex(index) }, { root, threshold: [.62, .82] }); root.querySelectorAll('.feed-card').forEach((item) => observer.observe(item)); return () => observer.disconnect() }, [])
  return <div ref={rootRef} className='feed-page'>{feedVideos.map((video, index) => <FeedCard key={video.id} video={video} active={index === activeIndex} index={index} />)}</div>
}
