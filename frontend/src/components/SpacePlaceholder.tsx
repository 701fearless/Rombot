import { ArrowLeft, Box, Clock3, ScanLine } from "lucide-react"

const LABELS: Record<string, string> = {
  sofa: "沙发",
  coffee_table: "茶几",
  bed: "床",
  desk: "书桌",
  chair: "椅子",
  cabinet: "柜子",
  dining_table: "餐桌",
  rug: "地毯",
  table_lamp: "台灯",
}

export function SpacePlaceholder() {
  const query = new URLSearchParams(window.location.search)
  const videoId = query.get("videoId")
  const time = query.get("time")
  const sceneType = query.get("sceneType")
  const frameId = query.get("frameId")
  const objectId = query.get("objectId")
  const objectLabel = query.get("objectLabel")
  const hasSelection = Boolean(videoId && time && frameId && objectId)

  return (
    <main className="space-page">
      <div className="space-glow space-glow--one" aria-hidden="true" />
      <div className="space-glow space-glow--two" aria-hidden="true" />
      <header className="space-header">
        <a href="/feed" className="back-link">
          <ArrowLeft aria-hidden="true" />
          返回灵感
        </a>
        <div className="space-brand">
          <span>R</span>
          ROMBOT SPACE
        </div>
      </header>

      <section className="space-card">
        <div className="space-orbit" aria-hidden="true">
          <div className="space-cube">
            <Box />
          </div>
          <span />
          <span />
          <span />
        </div>
        <div className="eyebrow">{hasSelection ? "已从视频捕获家具" : "我的数字空间"}</div>
        <h1>
          {hasSelection
            ? `${LABELS[objectLabel ?? ""] ?? objectLabel ?? "家具"}，已经送到小屋门口`
            : "你的小屋正在等待第一件灵感家具"}
        </h1>
        <p>
          {hasSelection
            ? "空间编辑器接入后，会在这里生成家具资产并把它放入可编辑的 3D 房间。"
            : "回到家装灵感 Feed，暂停视频并选择一件家具。"}
        </p>

        {hasSelection && (
          <dl className="selection-grid">
            <div>
              <dt>
                <ScanLine aria-hidden="true" />
                来源视频
              </dt>
              <dd>#{videoId}</dd>
            </div>
            <div>
              <dt>
                <Clock3 aria-hidden="true" />
                暂停时间
              </dt>
              <dd>{time}s</dd>
            </div>
            <div>
              <dt>场景</dt>
              <dd>{sceneType?.replaceAll("_", " ")}</dd>
            </div>
            <div>
              <dt>对象 ID</dt>
              <dd>{objectId}</dd>
            </div>
          </dl>
        )}

        <a className="space-primary-action" href="/feed">
          {hasSelection ? "继续挑选家具" : "去浏览家装灵感"}
        </a>

        {hasSelection && (
          <details className="handoff-details">
            <summary>查看交接参数</summary>
            <pre>
              {JSON.stringify(
                { videoId, time, sceneType, frameId, objectId, objectLabel },
                null,
                2,
              )}
            </pre>
          </details>
        )}
      </section>
    </main>
  )
}
