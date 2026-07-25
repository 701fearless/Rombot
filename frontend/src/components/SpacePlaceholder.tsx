import {
  AlertTriangle,
  ArrowLeft,
  Box,
  Clock3,
  Download,
  FileJson,
  Image as ImageIcon,
  LoaderCircle,
  ScanLine,
  Upload,
  X,
} from "lucide-react"
import { type ChangeEvent, useEffect, useMemo, useRef, useState } from "react"

import {
  apiUrl,
  getFloorplanPreset,
  getPrebuiltAsset,
  listFloorplanPresets,
} from "../lib/api"
import { sha256File } from "../lib/sha256"
import type { FloorplanPreset, PrebuiltAsset } from "../types"
import { FloorplanViewer } from "./FloorplanViewer"

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
  wardrobe: "衣柜",
}

type PageState = "idle" | "ready" | "matching" | "loading" | "success" | "error"

export function SpacePlaceholder() {
  const query = useMemo(() => new URLSearchParams(window.location.search), [])
  const sceneId = query.get("sceneId")
  const videoId = query.get("videoId")
  const time = query.get("time")
  const sceneType = query.get("sceneType")
  const frameId = query.get("frameId")
  const objectId = query.get("objectId")
  const objectLabel = query.get("objectLabel")
  const hasSelection = Boolean(videoId && time && frameId && objectId)

  const inputRef = useRef<HTMLInputElement>(null)
  const abortRef = useRef<AbortController | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState("")
  const [state, setState] = useState<PageState>(sceneId ? "loading" : "idle")
  const [preset, setPreset] = useState<FloorplanPreset | null>(null)
  const [asset, setAsset] = useState<PrebuiltAsset | null>(null)
  const [errorMessage, setErrorMessage] = useState("")

  useEffect(() => {
    if (!sceneId) return
    const controller = new AbortController()
    abortRef.current = controller
    setState("loading")
    setErrorMessage("")

    Promise.all([
      getFloorplanPreset(sceneId, controller.signal),
      frameId && objectId
        ? getPrebuiltAsset(frameId, objectId, controller.signal)
        : Promise.resolve(null),
    ])
      .then(([nextPreset, nextAsset]) => {
        setPreset(nextPreset)
        setAsset(nextAsset)
        setState("success")
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return
        setErrorMessage(error instanceof Error ? error.message : "预处理资源读取失败")
        setState("error")
      })
    return () => controller.abort()
  }, [frameId, objectId, sceneId])

  useEffect(
    () => () => {
      abortRef.current?.abort()
      if (previewUrl) URL.revokeObjectURL(previewUrl)
    },
    [previewUrl],
  )

  const chooseFile = (event: ChangeEvent<HTMLInputElement>) => {
    const nextFile = event.target.files?.[0]
    if (!nextFile) return
    if (!["image/jpeg", "image/png", "image/webp"].includes(nextFile.type)) {
      setState("error")
      setErrorMessage("请选择 room1–7 对应的 JPEG、PNG 或 WebP 户型图")
      return
    }
    if (nextFile.size > 15 * 1024 * 1024) {
      setState("error")
      setErrorMessage("户型图不能超过 15 MB")
      return
    }
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    setFile(nextFile)
    setPreviewUrl(URL.createObjectURL(nextFile))
    setErrorMessage("")
    setState("ready")
  }

  const enterMatchedPreset = (matched: FloorplanPreset) => {
    if (hasSelection) {
      const nextQuery = new URLSearchParams(query)
      nextQuery.set("sceneId", matched.sceneId)
      window.location.assign(`/space?${nextQuery.toString()}`)
      return
    }
    window.location.assign(
      `/feed?${new URLSearchParams({ sceneId: matched.sceneId }).toString()}`,
    )
  }

  const matchPreset = async () => {
    if (!file) {
      inputRef.current?.click()
      return
    }
    const controller = new AbortController()
    abortRef.current?.abort()
    abortRef.current = controller
    setState("matching")
    setErrorMessage("")
    try {
      const [hash, presets] = await Promise.all([
        sha256File(file),
        listFloorplanPresets(controller.signal),
      ])
      const matched = presets.find(
        (item) => item.sourceSha256.toLowerCase() === hash.toLowerCase(),
      )
      if (!matched) {
        throw new Error("这张图片不在比赛预处理户型中，请选择 room1–7 的原图")
      }
      enterMatchedPreset(matched)
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return
      setErrorMessage(error instanceof Error ? error.message : "户型预设匹配失败")
      setState("error")
    } finally {
      if (abortRef.current === controller) abortRef.current = null
    }
  }

  const clearFile = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    if (inputRef.current) inputRef.current.value = ""
    setFile(null)
    setPreviewUrl("")
    setErrorMessage("")
    setState("idle")
  }

  const uploadUrl = () => {
    const next = new URLSearchParams(query)
    next.delete("sceneId")
    return `/space${next.size ? `?${next.toString()}` : ""}`
  }

  const selectedName =
    asset?.name || LABELS[objectLabel ?? ""] || objectLabel || "家具"

  return (
    <main className="space-page">
      <div className="space-glow space-glow--one" aria-hidden="true" />
      <div className="space-glow space-glow--two" aria-hidden="true" />
      <header className="space-header">
        <a
          href={sceneId ? `/feed?sceneId=${encodeURIComponent(sceneId)}` : "/feed"}
          className="back-link"
        >
          <ArrowLeft aria-hidden="true" />
          返回灵感
        </a>
        <div className="space-brand">
          <span>R</span>
          ROMBOT SPACE
        </div>
      </header>

      <div className="space-workspace">
        <section className="space-intro">
          <div className="space-orbit" aria-hidden="true">
            <div className="space-cube"><Box /></div>
            <span /><span /><span />
          </div>
          <div className="eyebrow">
            {preset
              ? asset
                ? "家具已进入预处理户型"
                : "预处理户型已就绪"
              : hasSelection
                ? "先为选中的家具指定户型"
                : "比赛演示 · 模拟上传户型"}
          </div>
          <h1>
            {preset
              ? asset
                ? `${selectedName}，已经放进 ${preset.title}`
                : `${preset.title} 已准备好，去 Feed 选择家具`
              : hasSelection
                ? `${LABELS[objectLabel ?? ""] ?? objectLabel ?? "家具"}，正在等待它的房间`
                : "上传预处理户型，再去 Feed 寻找家具"}
          </h1>
          <p>
            {preset
              ? "当前只读取比赛预生成资产，不调用 Ark、Seedream 或现场生 3D。"
              : "请选择 room1–7 的原始户型图。页面只计算图片指纹并匹配白模，不上传图片。"}
          </p>

          {hasSelection && (
            <dl className="selection-grid">
              <div>
                <dt><ScanLine aria-hidden="true" />来源视频</dt>
                <dd>#{videoId}</dd>
              </div>
              <div>
                <dt><Clock3 aria-hidden="true" />暂停时间</dt>
                <dd>{time}s</dd>
              </div>
              <div><dt>场景</dt><dd>{sceneType?.replaceAll("_", " ")}</dd></div>
              <div><dt>对象 ID</dt><dd>{objectId}</dd></div>
            </dl>
          )}

          {preset && (
            <div className="preset-summary">
              <img src={preset.sourceImageUrl} alt={`${preset.title}原图`} />
              <div>
                <span>{preset.quality === "ark" ? "ARK WHITEBOX" : "PLACEHOLDER WHITEBOX"}</span>
                <strong>{preset.title}</strong>
                <small>sceneId: {preset.sceneId}</small>
              </div>
            </div>
          )}
        </section>

        <section className="floorplan-panel" aria-label="户型与家具组合预览">
          {!sceneId && (
            <>
              <input
                ref={inputRef}
                className="sr-only"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                capture="environment"
                onChange={chooseFile}
              />

              {!file && (
                <button
                  className="floorplan-dropzone"
                  type="button"
                  onClick={() => inputRef.current?.click()}
                >
                  <span><Upload aria-hidden="true" /></span>
                  <strong>选择或拍摄 room1–7 户型图</strong>
                  <small>图片仅用于本地指纹匹配，不会调用识别 API</small>
                </button>
              )}

              {file && (
                <div className="floorplan-input-card">
                  <img src={previewUrl} alt="待匹配的户型图" />
                  <div>
                    <span>待匹配预处理户型</span>
                    <strong>{file.name}</strong>
                    <small>{(file.size / 1024 / 1024).toFixed(2)} MB</small>
                  </div>
                  <button type="button" onClick={clearFile} aria-label="移除户型图">
                    <X />
                  </button>
                </div>
              )}

              {state === "matching" && (
                <div className="floorplan-loading" role="status">
                  <LoaderCircle className="spin" />
                  <strong>正在匹配预处理户型</strong>
                  <p>只比较 SHA-256，不上传图片，也不会调用 Ark。</p>
                </div>
              )}

              {state === "error" && (
                <div className="floorplan-error" role="alert">
                  <AlertTriangle />
                  <div><strong>没有找到可用预设</strong><p>{errorMessage}</p></div>
                </div>
              )}

              {file && state !== "matching" && (
                <div className="floorplan-actions">
                  <button
                    type="button"
                    className="floorplan-primary"
                    onClick={() => void matchPreset()}
                  >
                    <ScanLine />
                    {state === "error" ? "重新匹配户型" : "使用这个预处理户型"}
                  </button>
                  <button type="button" onClick={() => inputRef.current?.click()}>
                    更换图片
                  </button>
                </div>
              )}
            </>
          )}

          {sceneId && state === "loading" && (
            <div className="floorplan-loading" role="status">
              <LoaderCircle className="spin" />
              <strong>正在加载预处理资产</strong>
              <p>户型与家具模型均从本地缓存读取。</p>
            </div>
          )}

          {sceneId && state === "error" && (
            <div className="floorplan-error" role="alert">
              <AlertTriangle />
              <div><strong>预处理资产不可用</strong><p>{errorMessage}</p></div>
              <a href={uploadUrl()}>重新选择户型</a>
            </div>
          )}

          {sceneId && state === "success" && preset && (
            <div className="floorplan-result">
              <header>
                <div>
                  <span>{asset ? "ROOM + FURNITURE READY" : "ROOM READY"}</span>
                  <h2>{asset ? `${preset.sceneId} · ${asset.name}` : preset.sceneId}</h2>
                </div>
                <a href={uploadUrl()}>更换户型</a>
              </header>

              <FloorplanViewer
                modelUrl={preset.whiteboxGlbUrl}
                furniture={asset}
              />

              {!asset && (
                <a
                  className="floorplan-primary floorplan-feed-action"
                  href={`/feed?sceneId=${encodeURIComponent(preset.sceneId)}`}
                >
                  去 Feed 暂停并选择家具
                </a>
              )}

              <div className="floorplan-artifacts">
                <a href={apiUrl(preset.sourceImageUrl)} target="_blank" rel="noreferrer">
                  <ImageIcon />原始户型图
                </a>
                <a href={apiUrl(preset.sceneUrl)} target="_blank" rel="noreferrer">
                  <FileJson />结构 JSON
                </a>
                <a href={apiUrl(preset.whiteboxGlbUrl)} download>
                  <Download />下载户型 GLB
                </a>
              </div>
            </div>
          )}
        </section>

        <a
          className="space-secondary-link"
          href={sceneId ? `/feed?sceneId=${encodeURIComponent(sceneId)}` : "/feed"}
        >
          浏览家装灵感
        </a>
      </div>
    </main>
  )
}
