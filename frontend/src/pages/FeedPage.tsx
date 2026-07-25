import { AlertCircle, Bookmark, Heart, Home, Inbox, LoaderCircle, MessageCircle, Music2, Pause, Plus, Share2, UserRound, UsersRound, Volume2, VolumeX } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useToast } from '@/components/ToastProvider'
import { feedVideos } from '@/data/feedVideos'
import { computeVideoDHash } from '@/lib/dhash'
import { containTagPosition } from '@/lib/geometry'
import { detectPausedFrame, getPrebuiltAsset, listGeneratedFurniture } from '@/services/backend'
import { useSceneStore } from '@/store'
import type { FeedVideo } from '@/types/feed'
import type { DetectResponse, DetectedObject } from '@/types/scene'

interface Size { width: number; height: number }

function FeedCard({ video, active, index }: { video: FeedVideo; active: boolean; index: number }) {
  const toast = useToast(); const activeSceneId = useSceneStore((s) => s.activeSceneId); const addFurniture = useSceneStore((s) => s.addFurnitureToLibrary)
  const rootRef = useRef<HTMLElement>(null); const videoRef = useRef<HTMLVideoElement>(null); const abortRef = useRef<AbortController | null>(null); const serialRef = useRef(0)
  const [paused, setPaused] = useState(true); const [muted, setMuted] = useState(true); const [liked, setLiked] = useState(false); const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'empty' | 'error'>('idle'); const [message, setMessage] = useState(''); const [detection, setDetection] = useState<DetectResponse | null>(null); const [containerSize, setContainerSize] = useState<Size>({ width: 0, height: 0 }); const [sourceSize, setSourceSize] = useState<Size>({ width: 0, height: 0 })
  const cancelRecognition = useCallback(() => { serialRef.current += 1; abortRef.current?.abort(); abortRef.current = null; setDetection(null); setStatus('idle') }, [])
  useEffect(() => { const root = rootRef.current; if (!root) return; const resize = () => setContainerSize({ width: root.clientWidth, height: root.clientHeight }); resize(); const observer = new ResizeObserver(resize); observer.observe(root); return () => observer.disconnect() }, [])
  useEffect(() => { const element = videoRef.current; if (!element) return; if (active) void element.play().catch(() => setPaused(true)); else { element.pause(); cancelRecognition() } }, [active, cancelRecognition])
  useEffect(() => () => abortRef.current?.abort(), [])
  const recognize = useCallback(async () => {
    const element = videoRef.current; if (!element || !active || element.readyState < 2) return
    const time = element.currentTime; const serial = ++serialRef.current; abortRef.current?.abort(); const controller = new AbortController(); abortRef.current = controller
    setDetection(null); setStatus('loading'); setMessage('')
    let hash: string | undefined; try { hash = computeVideoDHash(element) } catch { hash = undefined }
    try { const result = await detectPausedFrame(video.id, time, hash, controller.signal); if (serial !== serialRef.current || !element.paused) return; setDetection(result); setStatus(result.objects.length ? 'success' : 'empty') }
    catch (reason) { if (controller.signal.aborted || serial !== serialRef.current) return; setMessage(reason instanceof Error ? reason.message : '识别暂时不可用'); setStatus('error') }
  }, [active, video.id])
  const chooseObject = async (object: DetectedObject) => {
    if (!object.prebuiltGlbUrl || !detection) return
    try { const [prebuilt, catalog] = await Promise.all([getPrebuiltAsset(detection.frameId, object.id), listGeneratedFurniture()]); const item = catalog.find((candidate) => candidate.videoId === video.id && candidate.candidateId === prebuilt.deduplicatedObjectId); if (!item) throw new Error('模型目录中没有找到对应家具'); addFurniture(item); toast.show(`${item.name} 已加入家具库`) }
    catch (reason) { toast.show(reason instanceof Error ? reason.message : '家具暂时不可用') }
  }
  return <article ref={rootRef} className='feed-card' data-feed-index={index}>
    <video ref={videoRef} className='feed-card__video' src={video.videoUrl} poster={video.coverUrl} muted={muted} playsInline loop preload={active ? 'auto' : 'metadata'} onLoadedMetadata={(event) => setSourceSize({ width: event.currentTarget.videoWidth, height: event.currentTarget.videoHeight })} onCanPlay={(event) => { if (active && event.currentTarget.paused) void event.currentTarget.play().catch(() => undefined) }} onPause={() => { setPaused(true); if (active) void recognize() }} onPlay={() => { setPaused(false); cancelRecognition() }} onSeeking={cancelRecognition} />
    <button className='feed-card__tap' type='button' aria-label={paused ? '继续播放' : '暂停识别'} onClick={() => { const element = videoRef.current; if (!element) return; if (element.paused) void element.play(); else element.pause() }} />
    <div className='feed-card__shade' />
    <header className='feed-card__header'><strong>QQ HOUSE</strong><div><span>关注</span><b>推荐</b></div><small>{activeSceneId.toUpperCase()}</small></header>
    {paused && status === 'idle' && <div className='feed-card__pause'><Pause /></div>}
    {status === 'loading' && <div className='feed-status'><LoaderCircle className='spin' />正在匹配家具</div>}
    {(status === 'empty' || status === 'error') && <button className='feed-status is-action' type='button' onClick={() => void recognize()}>{status === 'error' && <AlertCircle />}{message || '当前画面没有可用家具'} · 重试</button>}
    {paused && detection?.objects.map((object) => {
      const point = containTagPosition(object.tagPosition, sourceSize, containerSize)
      const left = Math.min(Math.max(point.x, 16), Math.max(16, containerSize.width - 132))
      const top = Math.min(Math.max(point.y, 76), Math.max(76, containerSize.height - 150))
      return <button key={object.id} className={`feed-tag ${object.prebuiltGlbUrl ? '' : 'is-disabled'}`} type='button' disabled={!object.prebuiltGlbUrl} style={{ left, top }} onClick={() => void chooseObject(object)}><span className='feed-tag__dot' /><span>{object.name}</span><small>{object.prebuiltGlbUrl ? '收藏到家具库' : '模型未缓存'}</small></button>
    })}
    <aside className='feed-social' aria-label='视频操作'>
      <button type='button' className='feed-avatar' aria-label={`查看 ${video.author} 的主页`}><span>{video.author.slice(0, 1)}</span><Plus /></button>
      <button type='button' className={liked ? 'is-liked' : ''} aria-label='点赞' onClick={() => setLiked((value) => !value)}><Heart fill={liked ? 'currentColor' : 'none'} /><small>{liked ? '12.9w' : '12.8w'}</small></button>
      <button type='button' aria-label='评论'><MessageCircle /><small>238</small></button>
      <button type='button' aria-label='收藏'><Bookmark /><small>4.2w</small></button>
      <button type='button' aria-label='分享'><Share2 /><small>分享</small></button>
      <button type='button' className='feed-record' aria-label={muted ? '打开声音' : '静音'} onClick={() => setMuted((value) => !value)}>{muted ? <VolumeX /> : <Volume2 />}<Music2 /></button>
    </aside>
    <footer className='feed-card__copy'><strong>@{video.author}</strong><h1>{video.title}</h1><p>暂停视频，收藏喜欢的家具模型</p><div>{video.furnitureHints.map((hint) => <span key={hint}>#{hint}</span>)}</div></footer>
    <span className='feed-card__counter'>{index + 1}/{feedVideos.length}</span>
  </article>
}

function FeedDock() {
  return <nav className='feed-dock' aria-label='Feed 底栏'>
    <NavLink to='/' className='is-active' aria-label='灵感'><Home /><span>灵感</span></NavLink>
    <NavLink to='/home' aria-label='我的家'><UsersRound /><span>我的家</span></NavLink>
    <NavLink to='/recognize' className='feed-dock__create' aria-label='识别家具'><Plus /></NavLink>
    <NavLink to='/discover' aria-label='发现'><Inbox /><span>发现</span></NavLink>
    <NavLink to='/me' aria-label='我的'><UserRound /><span>我的</span></NavLink>
  </nav>
}

export function FeedPage() {
  const rootRef = useRef<HTMLDivElement>(null); const [activeIndex, setActiveIndex] = useState(0)
  useEffect(() => { const root = rootRef.current; if (!root) return; const observer = new IntersectionObserver((entries) => { const current = entries.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]; const index = Number((current?.target as HTMLElement | undefined)?.dataset.feedIndex); if (current?.intersectionRatio && current.intersectionRatio > .62 && Number.isInteger(index)) setActiveIndex(index) }, { root, threshold: [.62, .82] }); root.querySelectorAll('.feed-card').forEach((item) => observer.observe(item)); return () => observer.disconnect() }, [])
  return <div className='feed-experience'><div ref={rootRef} className='feed-page'>{feedVideos.map((video, index) => <FeedCard key={video.id} video={video} active={index === activeIndex} index={index} />)}</div><FeedDock /></div>
}
