import { Bookmark, Heart, MessageCircle, Volume2, VolumeX } from "lucide-react"

interface FeedActionsProps {
  muted: boolean
  onToggleMuted: () => void
}

export function FeedActions({ muted, onToggleMuted }: FeedActionsProps) {
  return (
    <aside className="feed-actions" aria-label="视频操作">
      <button className="action-button" type="button" aria-label="喜欢">
        <span className="action-icon">
          <Heart aria-hidden="true" />
        </span>
        <small>1.8k</small>
      </button>
      <button className="action-button" type="button" aria-label="评论">
        <span className="action-icon">
          <MessageCircle aria-hidden="true" />
        </span>
        <small>灵感</small>
      </button>
      <button className="action-button" type="button" aria-label="收藏">
        <span className="action-icon">
          <Bookmark aria-hidden="true" />
        </span>
        <small>收藏</small>
      </button>
      <button
        className="action-button"
        type="button"
        aria-label={muted ? "打开声音" : "静音"}
        onClick={(event) => {
          event.stopPropagation()
          onToggleMuted()
        }}
      >
        <span className="action-icon action-icon--muted">
          {muted ? <VolumeX aria-hidden="true" /> : <Volume2 aria-hidden="true" />}
        </span>
        <small>{muted ? "静音" : "声音"}</small>
      </button>
    </aside>
  )
}
