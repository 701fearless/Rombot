import { useEffect, useRef, useState } from "react"

import { feedVideos } from "../data/feedVideos"
import { VideoFeedItem } from "./VideoFeedItem"

export function VideoFeed() {
  const containerRef = useRef<HTMLElement>(null)
  const [activeIndex, setActiveIndex] = useState(0)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const items = Array.from(container.querySelectorAll<HTMLElement>(".feed-item"))
    const observer = new IntersectionObserver(
      (entries) => {
        const mostVisible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0]
        if (!mostVisible || mostVisible.intersectionRatio < 0.65) return
        const nextIndex = Number((mostVisible.target as HTMLElement).dataset.feedIndex)
        if (Number.isInteger(nextIndex)) setActiveIndex(nextIndex)
      },
      { root: container, threshold: [0.65, 0.8, 0.95] },
    )

    items.forEach((item) => observer.observe(item))
    return () => observer.disconnect()
  }, [])

  return (
    <main ref={containerRef} className="video-feed" aria-label="家装视频 Feed">
      {feedVideos.map((video, index) => (
        <VideoFeedItem
          key={video.id}
          video={video}
          index={index}
          isActive={index === activeIndex}
          shouldPreload={Math.abs(index - activeIndex) <= 1}
        />
      ))}
    </main>
  )
}
