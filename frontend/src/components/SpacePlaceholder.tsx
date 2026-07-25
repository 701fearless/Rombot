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
import { type ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from "react"

import {
  apiUrl,
  getFloorplanPreset,
  getPrebuiltAsset,
  listFloorplanPresets,
  placementCheck,
} from "../lib/api"
import {
  type NormalizedScene,
  normalizedSceneToSceneResponse,
  upsertSceneObject,
} from "../lib/sceneAdapter"
import { sha256File } from "../lib/sha256"
import type {
  FloorplanPreset,
  FurnitureLayoutPose,
  FurnitureMove,
  FurnitureTransformChange,
  PlacementCheckResponse,
  PrebuiltAsset,
  SceneObject,
  SceneResponse,
} from "../types"
import { FloorplanViewer } from "./FloorplanViewer"
import { SpatialAdvicePanel } from "./SpatialAdvicePanel"

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

function assetToSceneObject(asset: PrebuiltAsset, room: SceneResponse["room"]): SceneObject {
  const size: [number, number, number] = asset.estimatedDimensions
    ? [
        asset.estimatedDimensions.widthM,
        asset.estimatedDimensions.heightM,
        asset.estimatedDimensions.depthM,
      ]
    : [1.2, 0.8, 0.8]
  return {
    id: asset.deduplicatedObjectId || asset.objectId,
    label: asset.label,
    name: asset.name || LABELS[asset.label] || asset.label,
    position: [room.width * 0.5, size[1] * 0.5, room.depth * 0.45],
    rotation: [0, 0, 0],
    size,
    glbUrl: asset.glbUrl,
  }
}

function poseFromObject(object: SceneObject): FurnitureLayoutPose {
  return {
    objectId: object.id,
    position: object.position,
    rotation: object.rotation,
    size: object.size,
  }
}

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
  const checkAbortRef = useRef<AbortController | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState("")
  const [state, setState] = useState<PageState>(sceneId ? "loading" : "idle")
  const [preset, setPreset] = useState<FloorplanPreset | null>(null)
  const [asset, setAsset] = useState<PrebuiltAsset | null>(null)
  const [scene, setScene] = useState<SceneResponse | null>(null)
  const [layoutPose, setLayoutPose] = useState<FurnitureLayoutPose | null>(null)
  const [suggestionPose, setSuggestionPose] = useState<FurnitureLayoutPose | null>(null)
  const [placementReport, setPlacementReport] = useState<PlacementCheckResponse | null>(null)
  const [checking, setChecking] = useState(false)
  const [checkError, setCheckError] = useState("")
  const [errorMessage, setErrorMessage] = useState("")

  useEffect(() => {
    if (!sceneId) return
    const controller = new AbortController()
    abortRef.current = controller
    setState("loading")
    setErrorMessage("")
    setPlacementReport(null)
    setSuggestionPose(null)

    Promise.all([
      getFloorplanPreset(sceneId, controller.signal),
      frameId && objectId
        ? getPrebuiltAsset(frameId, objectId, controller.signal)
        : Promise.resolve(null),
    ])
      .then(async ([nextPreset, nextAsset]) => {
        const sceneRes = await fetch(apiUrl(nextPreset.sceneUrl), {
          signal: controller.signal,
        })
        if (!sceneRes.ok) {
          throw new Error(`结构 JSON 读取失败（${sceneRes.status}）`)
        }
        const normalized = (await sceneRes.json()) as NormalizedScene
        let nextScene = normalizedSceneToSceneResponse(normalized)
        let nextPose: FurnitureLayoutPose | null = null
        if (nextAsset) {
          const object = assetToSceneObject(nextAsset, nextScene.room)
          nextScene = upsertSceneObject(nextScene, object)
          nextPose = poseFromObject(object)
        }
        setPreset(nextPreset)
        setAsset(nextAsset)
        setScene(nextScene)
        setLayoutPose(nextPose)
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
      checkAbortRef.current?.abort()
      if (previewUrl) URL.revokeObjectURL(previewUrl)
    },
    [previewUrl],
  )

  const runPlacementCheck = useCallback(
    async (pose: FurnitureLayoutPose, enableAgents = false) => {
      if (!scene || !asset) return
      checkAbortRef.current?.abort()
      const controller = new AbortController()
      checkAbortRef.current = controller
      setChecking(true)
      setCheckError("")
      try {
        const sceneForCheck: SceneResponse = {
          ...scene,
          // candidate is the dragged furniture; exclude it from obstacles
          objects: scene.objects.filter((item) => item.id !== pose.objectId),
        }
        const report = await placementCheck({
          sceneId: scene.sceneId,
          scene: sceneForCheck,
          enableAgents,
          candidate: {
            id: pose.objectId,
            label: asset.label,
            name: asset.name || LABELS[asset.label] || asset.label,
            position: pose.position,
            rotation: pose.rotation,
            size: pose.size,
          },
          signal: controller.signal,
        })
        setPlacementReport(report)
        const move = report.layout?.moves?.[0]
        if (move) {
          setSuggestionPose({
            objectId: pose.objectId,
            position: move.toPosition,
            rotation: move.toRotation ?? pose.rotation,
            size: pose.size,
          })
        } else {
          setSuggestionPose(null)
        }
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return
        setCheckError(error instanceof Error ? error.message : "空间检测失败")
        setPlacementReport(null)
        setSuggestionPose(null)
      } finally {
        if (checkAbortRef.current === controller) {
          checkAbortRef.current = null
          setChecking(false)
        }
      }
    },
    [asset, scene],
  )

  const handleTransformChange = useCallback(
    (change: FurnitureTransformChange) => {
      if (!scene) return
      const nextObject: SceneObject = {
        id: change.objectId,
        label: asset?.label || objectLabel || "furniture",
        name: asset?.name || LABELS[asset?.label || ""] || change.objectId,
        position: change.position,
        rotation: change.rotation,
        size: change.size,
        glbUrl: asset?.glbUrl,
      }
      const nextScene = upsertSceneObject(scene, nextObject)
      const nextPose = poseFromObject(nextObject)
      setScene(nextScene)
      setLayoutPose(nextPose)
      if (change.reason === "apply") {
        void runPlacementCheck(nextPose, false)
        return
      }
      void runPlacementCheck(nextPose, false)
    },
    [asset, objectLabel, runPlacementCheck, scene],
  )

  const handleApplyMove = useCallback(
    (move: FurnitureMove) => {
      if (!layoutPose) return
      handleTransformChange({
        objectId: layoutPose.objectId,
        position: move.toPosition,
        rotation: move.toRotation ?? layoutPose.rotation,
        size: layoutPose.size,
        reason: "apply",
      })
    },
    [handleTransformChange, layoutPose],
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
          className="back-link"
          href={sceneId ? `/feed?sceneId=${encodeURIComponent(sceneId)}` : "/feed"}
        >
          <ArrowLeft />
          返回 Feed
        </a>
        <div className="space-brand">
          <span>R</span>
          ROMBOT SPACE
        </div>
        <div className="space-header-spacer" />
      </header>

      <div className="space-workspace">
        <section className="space-intro">
          <div className="space-orbit" aria-hidden="true">
            <div className="space-cube">
              <Box />
            </div>
            <span />
            <span />
            <span />
          </div>
          <p className="eyebrow">GLB = 渲染 · Scene JSON = 推理事实</p>
          <h1>{hasSelection ? `把「${selectedName}」放进小屋` : "上传户型，进入空间沙盒"}</h1>
          <p>
            户型白模只负责显示；拖动家具后会把位姿转成布局坐标，写入 Scene JSON，并调用
            placement-check 做几何可行性检测。
          </p>

          {hasSelection ? (
            <div className="space-meta">
              <span>
                <Clock3 />
                {Number(time).toFixed(1)}s
              </span>
              <span>{sceneType?.replaceAll("_", " ")}</span>
              <span>{videoId}</span>
            </div>
          ) : null}
        </section>

        <section className="floorplan-panel">
          {!sceneId && (
            <>
              <input
                ref={inputRef}
                className="sr-only"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={chooseFile}
              />

              {(state === "idle" || state === "error") && !file && (
                <button type="button" className="floorplan-dropzone" onClick={() => inputRef.current?.click()}>
                  <Upload />
                  <strong>上传 room1–7 原图匹配户型</strong>
                  <span>JPEG / PNG / WebP · 最大 15MB</span>
                </button>
              )}

              {(state === "ready" || (state === "error" && file)) && file && (
                <div className="floorplan-input-card">
                  {previewUrl ? <img src={previewUrl} alt="户型预览" /> : <ScanLine />}
                  <div>
                    <strong>{file.name}</strong>
                    <span>{(file.size / 1024).toFixed(0)} KB</span>
                  </div>
                  <button type="button" className="icon-button" onClick={clearFile} aria-label="清除">
                    <X />
                  </button>
                </div>
              )}

              {state === "matching" && (
                <div className="floorplan-loading">
                  <LoaderCircle className="spin" />
                  <p>正在匹配预处理户型…</p>
                </div>
              )}

              {(state === "ready" || (state === "error" && file)) && (
                <div className="floorplan-actions">
                  <button type="button" className="floorplan-primary" onClick={() => void matchPreset()}>
                    匹配并进入
                  </button>
                </div>
              )}

              {state === "error" && errorMessage && (
                <div className="floorplan-error" role="alert">
                  <AlertTriangle />
                  <div>
                    <strong>匹配失败</strong>
                    <p>{errorMessage}</p>
                  </div>
                </div>
              )}
            </>
          )}

          {sceneId && state === "loading" && (
            <div className="floorplan-loading">
              <LoaderCircle className="spin" />
              <p>加载户型 Scene JSON 与白模…</p>
            </div>
          )}

          {sceneId && state === "error" && (
            <div className="floorplan-error" role="alert">
              <AlertTriangle />
              <div>
                <strong>预处理资产不可用</strong>
                <p>{errorMessage}</p>
              </div>
              <a href={uploadUrl()}>重新选择户型</a>
            </div>
          )}

          {sceneId && state === "success" && preset && scene && (
            <div className="floorplan-result">
              <header>
                <div>
                  <span>
                    {asset ? "SCENE JSON + FURNITURE" : "SCENE JSON READY"}
                  </span>
                  <h2>
                    {asset ? `${preset.sceneId} · ${asset.name}` : preset.sceneId}
                  </h2>
                </div>
                <a href={uploadUrl()}>更换户型</a>
              </header>

              <FloorplanViewer
                modelUrl={preset.whiteboxGlbUrl}
                furniture={asset}
                sceneId={preset.sceneId}
                roomWidth={scene.room.width}
                roomDepth={scene.room.depth}
                layoutPose={layoutPose}
                suggestionPose={suggestionPose}
                onTransformChange={handleTransformChange}
                defaultMode={asset ? "furniture" : "walls"}
              />

              {asset ? (
                <SpatialAdvicePanel
                  checking={checking}
                  report={placementReport}
                  error={checkError}
                  onApplyMove={handleApplyMove}
                  onRecheck={() => {
                    if (layoutPose) void runPlacementCheck(layoutPose, false)
                  }}
                  onRequestAgents={() => {
                    if (layoutPose) void runPlacementCheck(layoutPose, true)
                  }}
                />
              ) : (
                <a
                  className="floorplan-primary floorplan-feed-action"
                  href={`/feed?sceneId=${encodeURIComponent(preset.sceneId)}`}
                >
                  去 Feed 暂停并选择家具
                </a>
              )}

              <div className="floorplan-artifacts">
                <a href={apiUrl(preset.sourceImageUrl)} target="_blank" rel="noreferrer">
                  <ImageIcon />
                  原始户型图
                </a>
                <a href={apiUrl(preset.sceneUrl)} target="_blank" rel="noreferrer">
                  <FileJson />
                  结构 JSON
                </a>
                <a href={apiUrl(preset.whiteboxGlbUrl)} download>
                  <Download />
                  下载户型 GLB
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
