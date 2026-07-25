import {
  AlertTriangle,
  ArrowLeft,
  BedDouble,
  Box,
  Chair as Armchair,
  Clock3,
  Download,
  FileJson,
  Image as ImageIcon,
  Lamp,
  LoaderCircle,
  Plus,
  ScanLine,
  Sofa,
  Trash2,
  Upload,
  X,
} from "lucide-react"
import React, { type ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from "react"

import {
  apiUrl,
  getFloorplanPreset,
  getPrebuiltAsset,
  listFloorplanPresets,
  placementCheck,
  uploadFurnitureGlb,
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

// 预置家具库：包含默认尺寸和图标
interface FurnitureTemplate {
  id: string
  label: string
  name: string
  Icon: React.ComponentType<{ size?: number }>
  defaultSize: [number, number, number] // [宽, 高, 深] 米
  color: string // 用于显示的颜色标识
}

const FURNITURE_TEMPLATES: FurnitureTemplate[] = [
  { id: "sofa", label: "sofa", name: "沙发", Icon: Sofa, defaultSize: [2.2, 0.9, 1.0], color: "#8B5CF6" },
  { id: "bed", label: "bed", name: "床", Icon: BedDouble, defaultSize: [2.0, 0.6, 1.5], color: "#EC4899" },
  { id: "chair", label: "chair", name: "椅子", Icon: Armchair, defaultSize: [0.5, 0.85, 0.5], color: "#F59E0B" },
  { id: "desk", label: "desk", name: "书桌", Icon: Box, defaultSize: [1.4, 0.75, 0.7], color: "#10B981" },
  { id: "dining_table", label: "dining_table", name: "餐桌", Icon: Box, defaultSize: [1.6, 0.75, 0.9], color: "#3B82F6" },
  { id: "cabinet", label: "cabinet", name: "柜子", Icon: Box, defaultSize: [1.2, 1.8, 0.5], color: "#6366F1" },
  { id: "table_lamp", label: "table_lamp", name: "台灯", Icon: Lamp, defaultSize: [0.25, 0.5, 0.25], color: "#EAB308" },
]

type PageState = "idle" | "ready" | "matching" | "loading" | "success" | "error"

// 多家具项：包含资产信息和当前位姿
interface PlacedFurnitureItem {
  id: string // 唯一ID，格式: custom_xxx 或 prebuilt_xxx
  asset: PrebuiltAsset
  pose: FurnitureLayoutPose
}

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
  const [layoutPoseState, setLayoutPoseState] = useState<FurnitureLayoutPose | null>(null)
  const [suggestionPose, setSuggestionPose] = useState<FurnitureLayoutPose | null>(null)
  const [placementReport, setPlacementReport] = useState<PlacementCheckResponse | null>(null)
  const [checking, setChecking] = useState(false)
  const [checkError, setCheckError] = useState("")
  const [errorMessage, setErrorMessage] = useState("")

  // 自定义家具上传相关状态
  const [uploadingFurniture, setUploadingFurniture] = useState(false)
  const [uploadError, setUploadError] = useState("")
  const furnitureInputRef = useRef<HTMLInputElement>(null)
  
  // 多家具列表：所有已放置的家具
  const [placedFurnitureList, setPlacedFurnitureList] = useState<PlacedFurnitureItem[]>([])
  
  // 当前选中的家具ID（用于拖拽和操作）
  const [selectedFurnitureId, setSelectedFurnitureId] = useState<string | null>(null)
  
  // 拖拽状态
  const [isDraggingTemplate, setIsDraggingTemplate] = useState<string | null>(null) // 正在拖拽的模板ID
  
  // 获取当前选中的家具
  const selectedFurniture = useMemo(
    () => placedFurnitureList.find((item) => item.id === selectedFurnitureId) || null,
    [placedFurnitureList, selectedFurnitureId],
  )
  
  // 从列表获取当前活跃的 asset 和 pose（兼容原有逻辑）
  const activeAsset = selectedFurniture?.asset || asset
  const activeLayoutPose = selectedFurniture?.pose || layoutPoseState

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
        setLayoutPoseState(nextPose)
        setState("success")
        
        // 如果有预置家具，添加到多家具列表
        if (nextAsset && nextPose) {
          const prebuiltId = `prebuilt_${nextAsset.objectId}`
          setPlacedFurnitureList([{
            id: prebuiltId,
            asset: nextAsset,
            pose: nextPose,
          }])
          setSelectedFurnitureId(prebuiltId)
        } else {
          setPlacedFurnitureList([])
          setSelectedFurnitureId(null)
        }
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
      if (!scene || !activeAsset) return
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
            label: activeAsset.label,
            name: activeAsset.name || LABELS[activeAsset.label] || activeAsset.label,
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
    [activeAsset, scene],
  )

  const handleTransformChange = useCallback(
    (change: FurnitureTransformChange) => {
      if (!scene || !selectedFurnitureId) return
      
      // 更新多家具列表中对应家具的位姿
      setPlacedFurnitureList((prev) =>
        prev.map((item) => {
          if (item.id !== change.objectId) return item
          return {
            ...item,
            pose: {
              objectId: change.objectId,
              position: change.position,
              rotation: change.rotation,
              size: change.size,
            },
          }
        }),
      )
      
      // 同时更新 scene（用于碰撞检测等）
      const nextObject: SceneObject = {
        id: change.objectId,
        label: selectedFurniture?.asset.label || "furniture",
        name: selectedFurniture?.asset.name || change.objectId,
        position: change.position,
        rotation: change.rotation,
        size: change.size,
        glbUrl: selectedFurniture?.asset.glbUrl,
      }
      const nextScene = upsertSceneObject(scene, nextObject)
      setScene(nextScene)
      
      // 更新当前 pose
      const nextPose: FurnitureLayoutPose = {
        objectId: change.objectId,
        position: change.position,
        rotation: change.rotation,
        size: change.size,
      }
      setLayoutPoseState(nextPose)
      
      if (change.reason === "apply") {
        void runPlacementCheck(nextPose, false)
        return
      }
      void runPlacementCheck(nextPose, false)
    },
    [runPlacementCheck, scene, selectedFurniture, selectedFurnitureId],
  )

  const handleApplyMove = useCallback(
    (move: FurnitureMove) => {
      if (!activeLayoutPose) return
      handleTransformChange({
        objectId: activeLayoutPose.objectId,
        position: move.toPosition,
        rotation: move.toRotation ?? activeLayoutPose.rotation,
        size: activeLayoutPose.size,
        reason: "apply",
      })
    },
    [handleTransformChange, activeLayoutPose],
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

  // 上传自定义家具 GLB - 添加到多家具列表
  const handleFurnitureUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // 验证文件类型
    const filename = file.name.toLowerCase()
    if (!filename.endsWith(".glb") && !filename.endsWith(".gltf")) {
      setUploadError("只支持 .glb 或 .gltf 格式的文件")
      return
    }

    // 验证文件大小 (最大 50MB)
    if (file.size > 50 * 1024 * 1024) {
      setUploadError("文件大小不能超过 50MB")
      return
    }

    setUploadingFurniture(true)
    setUploadError("")

    try {
      const result = await uploadFurnitureGlb(file)
      
      // 构建为 PrebuiltAsset 格式
      const customAsset: PrebuiltAsset = {
        objectId: result.id,
        deduplicatedObjectId: result.id,
        label: "custom_furniture",
        name: result.name,
        glbUrl: result.glbUrl,
        estimatedDimensions: {
          widthM: 1.0,
          heightM: 0.8,
          depthM: 1.0,
        },
      }
      
      // 创建新的家具项，添加到列表
      const newFurnitureId = `custom_${result.id}`
      const defaultSize: [number, number, number] = [
        customAsset.estimatedDimensions.widthM,
        customAsset.estimatedDimensions.heightM,
        customAsset.estimatedDimensions.depthM,
      ]
      
      const newItem: PlacedFurnitureItem = {
        id: newFurnitureId,
        asset: customAsset,
        pose: {
          objectId: newFurnitureId,
          position: [2, defaultSize[1] * 0.5, 1], // 稍微偏移，避免重叠
          rotation: [0, 0, 0],
          size: defaultSize,
        },
      }
      
      setPlacedFurnitureList((prev) => [...prev, newItem])
      setSelectedFurnitureId(newFurnitureId)
      setUploadError("")
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "上传失败")
    } finally {
      setUploadingFurniture(false)
      if (furnitureInputRef.current) furnitureInputRef.current.value = ""
    }
  }

  // 选择家具（切换当前操作目标）
  const handleSelectFurniture = useCallback((furnitureId: string) => {
    setSelectedFurnitureId(furnitureId)
    const item = placedFurnitureList.find((i) => i.id === furnitureId)
    if (item) {
      setLayoutPoseState(item.pose)
      setAsset(item.asset)
    }
  }, [placedFurnitureList])

  // 删除家具
  const handleRemoveFurniture = useCallback((furnitureId: string) => {
    setPlacedFurnitureList((prev) => prev.filter((item) => item.id !== furnitureId))
    
    // 如果删除的是当前选中的，选中另一个或清空
    if (selectedFurnitureId === furnitureId) {
      const remaining = placedFurnitureList.filter((item) => item.id !== furnitureId)
      if (remaining.length > 0) {
        const nextSelected = remaining[remaining.length - 1]
        setSelectedFurnitureId(nextSelected.id)
        setLayoutPoseState(nextSelected.pose)
        setAsset(nextSelected.asset)
      } else {
        setSelectedFurnitureId(null)
        setLayoutPoseState(null)
        setAsset(null)
      }
    }
  }, [placedFurnitureList, selectedFurnitureId])

  // ========== 拖拽相关函数 ==========
  
  // 从预置家具库添加家具到空间
  const handleAddFurnitureFromTemplate = useCallback((template: FurnitureTemplate, position?: [number, number, number]) => {
    const newId = `${template.id}_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`
    const size = template.defaultSize
    
    // 计算放置位置：如果指定了位置就用指定的，否则根据已有家具数量偏移
    const pos: [number, number, number] = position || [
      1 + (placedFurnitureList.length % 3) * 1.5, // x: 错开排列
      size[1] * 0.5,                               // y: 高度一半
      1 + Math.floor(placedFurnitureList.length / 3) * 1.5, // z: 多行排列
    ]
    
    const newAsset: PrebuiltAsset = {
      objectId: newId,
      deduplicatedObjectId: template.id,
      label: template.label,
      name: `${template.name} ${placedFurnitureList.filter(f => f.asset.label === template.label).length + 1}`,
      glbUrl: "", // 预置家具使用占位符显示
      estimatedDimensions: { widthM: size[0], heightM: size[1], depthM: size[2] },
    }
    
    const newItem: PlacedFurnitureItem = {
      id: newId,
      asset: newAsset,
      pose: {
        objectId: newId,
        position: pos,
        rotation: [0, 0, 0],
        size: size,
      },
    }
    
    setPlacedFurnitureList((prev) => [...prev, newItem])
    setSelectedFurnitureId(newId)
    setLayoutPoseState(newItem.pose)
    setAsset(newAsset)
  }, [placedFurnitureList.length])

  // 拖拽开始
  const handleDragStart = useCallback((e: React.DragEvent, templateId: string) => {
    setIsDraggingTemplate(templateId)
    e.dataTransfer.setData("furnitureTemplate", templateId)
    e.dataTransfer.effectAllowed = "copy"
  }, [])

  // 拖拽结束
  const handleDragEnd = useCallback(() => {
    setIsDraggingTemplate(null)
  }, [])

  // 拖放到3D区域
  const handleDropOnViewer = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const templateId = e.dataTransfer.getData("furnitureTemplate")
    if (!templateId) return
    
    const template = FURNITURE_TEMPLATES.find(t => t.id === templateId)
    if (template) {
      handleAddFurnitureFromTemplate(template)
    }
    setIsDraggingTemplate(null)
  }, [handleAddFurnitureFromTemplate])

  // 允许拖放
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = "copy"
  }, [])

  const uploadUrl = () => {
    const next = new URLSearchParams(query)
    next.delete("sceneId")
    return `/space${next.size ? `?${next.toString()}` : ""}`
  }

  const selectedName =
    activeAsset?.name || LABELS[objectLabel ?? ""] || objectLabel || "家具"

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
                    {placedFurnitureList.length > 0 
                      ? `SCENE JSON + ${placedFurnitureList.length} 件家具` 
                      : "SCENE JSON READY"}
                  </span>
                  <h2>{preset.sceneId}</h2>
                </div>
                <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                  {/* 上传家具 GLB 按钮 - 叠加新家具 */}
                  <input
                    ref={furnitureInputRef}
                    type="file"
                    accept=".glb,.gltf"
                    onChange={handleFurnitureUpload}
                    style={{ display: "none" }}
                  />
                  <button
                    type="button"
                    className={`furniture-upload-btn ${uploadingFurniture ? "is-uploading" : ""}`}
                    onClick={() => furnitureInputRef.current?.click()}
                    disabled={uploadingFurniture}
                    title="上传并添加家具到空间"
                  >
                    {uploadingFurniture ? (
                      <>
                        <LoaderCircle className="spin" size={16} />
                        上传中...
                      </>
                    ) : (
                      <>
                        <Plus size={16} />
                        上传GLB
                      </>
                    )}
                  </button>
                  <a href={uploadUrl()}>更换户型</a>
                </div>
              </header>

              {/* 上传错误提示 */}
              {uploadError && (
                <div className="furniture-upload-error" role="alert">
                  <AlertTriangle size={14} />
                  <span>{uploadError}</span>
                  <button onClick={() => setUploadError("")}><X size={12} /></button>
                </div>
              )}

              {/* 主内容区：左侧家具库 + 右侧3D视图 */}
              <div className="space-layout">
                {/* 左侧：预置家具库 + 已放置列表 */}
                <aside className="furniture-sidebar">
                  {/* 预置家具库 */}
                  <div className="furniture-library">
                    <h4>📦 家具库</h4>
                    <p className="library-hint">拖拽或点击添加到空间</p>
                    <div className="furniture-template-grid">
                      {FURNITURE_TEMPLATES.map((template) => (
                        <div
                          key={template.id}
                          className={`furniture-template-item ${isDraggingTemplate === template.id ? 'is-dragging' : ''}`}
                          draggable
                          onDragStart={(e) => handleDragStart(e, template.id)}
                          onDragEnd={handleDragEnd}
                          onClick={() => handleAddFurnitureFromTemplate(template)}
                          title={`点击或拖拽添加${template.name}`}
                        >
                          <div 
                            className="template-icon" 
                            style={{ backgroundColor: `${template.color}20`, color: template.color }}
                          >
                            <template.Icon size={20} />
                          </div>
                          <span className="template-name">{template.name}</span>
                          <span className="template-size">
                            {template.defaultSize[0]}×{template.defaultSize[2]}m
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 已放置的家具列表 */}
                  {placedFurnitureList.length > 0 && (
                    <div className="placed-furniture-list">
                      <h4>🏠 已摆放 ({placedFurnitureList.length})</h4>
                      <div className="placed-furniture-items">
                        {placedFurnitureList.map((item) => (
                          <div
                            key={item.id}
                            className={`placed-item ${selectedFurnitureId === item.id ? 'is-selected' : ''}`}
                            onClick={() => handleSelectFurniture(item.id)}
                          >
                            <Box size={14} style={{ color: item.asset.glbUrl ? '#8B5CF6' : '#6B7280' }} />
                            <span className="placed-item-name">{item.asset.name}</span>
                            <button
                              type="button"
                              className="placed-item-remove"
                              onClick={(e) => {
                                e.stopPropagation()
                                handleRemoveFurniture(item.id)
                              }}
                              title="移除"
                            >
                              <Trash2 size={11} />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </aside>

                {/* 右侧：3D视图区域（支持拖放） */}
                <main 
                  className={`viewer-container ${isDraggingTemplate ? 'drag-over' : ''}`}
                  onDrop={handleDropOnViewer}
                  onDragOver={handleDragOver}
                >
                  {isDraggingTemplate && (
                    <div className="drop-indicator">
                      <Box size={32} />
                      <span>松开鼠标将家具放到这里</span>
                    </div>
                  )}
                  
                  <FloorplanViewer
                    modelUrl={preset.whiteboxGlbUrl}
                    furniture={activeAsset}
                    sceneId={preset.sceneId}
                    roomWidth={scene.room.width}
                    roomDepth={scene.room.depth}
                    layoutPose={activeLayoutPose}
                    suggestionPose={suggestionPose}
                    onTransformChange={handleTransformChange}
                    defaultMode={placedFurnitureList.length > 0 ? "furniture" : "walls"}
                  />

                  {activeAsset ? (
                    <SpatialAdvicePanel
                      checking={checking}
                      report={placementReport}
                      error={checkError}
                      onApplyMove={handleApplyMove}
                      onRecheck={() => {
                        if (activeLayoutPose) void runPlacementCheck(activeLayoutPose, false)
                      }}
                      onRequestAgents={() => {
                        if (activeLayoutPose) void runPlacementCheck(activeLayoutPose, true)
                      }}
                    />
                  ) : placedFurnitureList.length === 0 ? (
                    <a
                      className="floorplan-primary floorplan-feed-action"
                      href={`/feed?sceneId=${encodeURIComponent(preset.sceneId)}`}
                    >
                      去 Feed 暂停并选择家具
                    </a>
                  ) : (
                    <div className="select-furniture-hint">
                      <p>从左侧选择一件家具进行操作，或添加新家具</p>
                    </div>
                  )}
                </main>
              </div>

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
