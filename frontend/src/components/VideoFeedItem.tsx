import { AlertCircle, LoaderCircle, Pause, Play, ScanSearch } from "lucide-react"
import {
  type MouseEvent as ReactMouseEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react"

import { detectPausedFrame } from "../lib/api"
import { computeVideoDHash } from "../lib/dhash"
import { coverTagPosition } from "../lib/geometry"
import { buildSpaceUrl } from "../lib/navigation"
import type { DetectResponse, DetectedObject, FeedVideo } from "../types"
import { FeedActions } from "./FeedActions"

type RecognitionState = "idle" | "loading" | "success" | "empty" | "error"

interface VideoFeedItemProps {
  video: FeedVideo
  index: number
  isActive: boolean
  shouldPreload: boolean
}

interface Size {
  width: number
  height: number
}

export function VideoFeedItem({
  video,
  index,
  isActive,
  shouldPreload,
}: VideoFeedItemProps) {
  const itemRef = useRef<HTMLElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const abortRef = useRef<AbortController | null>(null)
  const requestSerialRef = useRef(0)
  const [muted, setMuted] = useState(true)
  const [paused, setPaused] = useState(true)
  const [recognitionState, setRecognitionState] = useState<RecognitionState>("idle")
  const [detection, setDetection] = useState<DetectResponse | null>(null)
  const [pausedAt, setPausedAt] = useState(0)
  const [errorMessage, setErrorMessage] = useState("")
  const [containerSize, setContainerSize] = useState<Size>({ width: 0, height: 0 })
  const [sourceSize, setSourceSize] = useState<Size>({ width: 0, height: 0 })

  const cancelRecognition = useCallback(() => {
    requestSerialRef.current += 1
    abortRef.current?.abort()
    abortRef.current = null
    setDetection(null)
    setRecognitionState("idle")
    setErrorMessage("")
  }, [])

  useEffect(() => {
    const item = itemRef.current
    if (!item) return

    const updateSize = () =>
      setContainerSize({ width: item.clientWidth, height: item.clientHeight })
    updateSize()
    const observer = new ResizeObserver(updateSize)
    observer.observe(item)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    const element = videoRef.current
    if (!element) return

    if (isActive) {
      const playPromise = element.play()
      playPromise?.catch(() => setPaused(true))
    } else {
      element.pause()
      setPaused(true)
      cancelRecognition()
    }
  }, [cancelRecognition, isActive])

  useEffect(() => () => abortRef.current?.abort(), [])

  const runRecognition = useCallback(async () => {
    const element = videoRef.current
    if (!element || !isActive || element.ended || element.readyState < 2) return

    const serial = ++requestSerialRef.current
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    const time = element.currentTime

    setPausedAt(time)
    setDetection(null)
    setErrorMessage("")
    setRecognitionState("loading")

    try {
      const frameHash = computeVideoDHash(element)
      const response = await detectPausedFrame({
        videoId: video.id,
        time,
        frameHash,
        signal: controller.signal,
      })

      if (
        serial !== requestSerialRef.current ||
        !element.paused ||
        !isActive ||
        Math.abs(element.currentTime - time) > 0.08
      ) {
        return
      }

      setDetection(response)
      setRecognitionState(response.objects.length ? "success" : "empty")
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return
      if (serial !== requestSerialRef.current) return
      setErrorMessage(error instanceof Error ? error.message : "识别暂时不可用")
      setRecognitionState("error")
    } finally {
      if (serial === requestSerialRef.current) abortRef.current = null
    }
  }, [isActive, video.id])

  const togglePlayback = (event: ReactMouseEvent<HTMLElement>) => {
    if ((event.target as HTMLElement).closest("button")) return
    const element = videoRef.current
    if (!element) return
    if (element.paused) {
      void element.play()
    } else {
      element.pause()
    }
  }

  const enterSpace = (event: ReactMouseEvent, object: DetectedObject) => {
    event.stopPropagation()
    if (!detection) return
    window.location.assign(
      buildSpaceUrl({
        video,
        time: pausedAt,
        frameId: detection.frameId,
        objectId: object.id,
        objectLabel: object.label,
      }),
    )
  }

  return (
    <article
      ref={itemRef}
      className="feed-item"
      data-feed-index={index}
      data-active={isActive}
      onClick={togglePlayback}
      aria-label={`${video.title}，${paused ? "已暂停" : "正在播放"}`}
    >
      <video
        ref={videoRef}
        className="feed-video"
        src={video.videoUrl}
        poster={video.coverUrl}
        muted={muted}
        playsInline
        loop
        preload={shouldPreload ? "auto" : "metadata"}
        onLoadedMetadata={(event) =>
          setSourceSize({
            width: event.currentTarget.videoWidth,
            height: event.currentTarget.videoHeight,
          })
        }
        onPause={() => {
          setPaused(true)
          if (isActive) void runRecognition()
        }}
        onPlay={() => {
          setPaused(false)
          cancelRecognition()
        }}
        onSeeking={cancelRecognition}
      />

      <div className="video-vignette" aria-hidden="true" />

      {paused && recognitionState === "idle" && isActive && (
        <div className="pause-indicator" aria-hidden="true">
          <Pause />
        </div>
      )}

      {recognitionState === "loading" && (
        <div className="scan-status" role="status">
          <LoaderCircle className="spin" aria-hidden="true" />
          <span>正在匹配画面里的家具</span>
        </div>
      )}

      {recognitionState === "empty" && (
        <div className="scan-status scan-status--message" role="status">
          <ScanSearch aria-hidden="true" />
          <span>这个暂停点还没有识别到家具</span>
          <button type="button" onClick={() => void runRecognition()}>
            重新识别
          </button>
        </div>
      )}

      {recognitionState === "error" && (
        <div className="scan-status scan-status--message" role="alert">
          <AlertCircle aria-hidden="true" />
          <span>{errorMessage || "识别暂时不可用"}</span>
          <button type="button" onClick={() => void runRecognition()}>
            再试一次
          </button>
        </div>
      )}

      {recognitionState === "success" && detection && (
        <div className="tag-layer" aria-label="识别到的家具">
          {detection.objects.map((object) => {
            const point = coverTagPosition(object.tagPosition, sourceSize, containerSize)
            return (
              <button
                key={object.id}
                className="furniture-tag"
                type="button"
                style={{ left: point.x, top: point.y }}
                onClick={(event) => enterSpace(event, object)}
                aria-label={`选择${object.name || object.label}，进入我的小屋`}
              >
                <span className="tag-dot" aria-hidden="true" />
                <span>{object.name || object.label}</span>
                <small>{Math.round(object.confidence * 100)}%</small>
              </button>
            )
          })}
        </div>
      )}

      <header className="feed-header">
        <div className="brand-mark" aria-label="Rombot">
          <span>R</span>
        </div>
        <nav aria-label="Feed 分类">
          <button type="button" className="header-tab">
            关注
          </button>
          <button type="button" className="header-tab header-tab--active">
            家装灵感
          </button>
        </nav>
        <a className="room-link" href="/space" onClick={(event) => event.stopPropagation()}>
          我的小屋
        </a>
      </header>

      <FeedActions muted={muted} onToggleMuted={() => setMuted((value) => !value)} />

      <footer className="feed-caption">
        <div className="caption-author">@{video.author}</div>
        <h1>{video.title}</h1>
        <p>
          暂停视频，点选你喜欢的家具
          <span className="caption-pulse" aria-hidden="true" />
        </p>
        <div className="hint-row">
          {video.furnitureHints.slice(0, 3).map((hint) => (
            <span key={hint}>#{hint.replaceAll("_", " ")}</span>
          ))}
        </div>
      </footer>

      <div className="progress-rail" aria-hidden="true">
        <span />
      </div>

      <div className="playback-state" aria-live="polite">
        {paused ? <Play aria-hidden="true" /> : null}
        <span className="sr-only">{paused ? "视频已暂停" : "视频正在播放"}</span>
      </div>
    </article>
  )
}
