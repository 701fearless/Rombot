import { useCallback, useEffect, useRef, useState } from "react"
import {
  type ChangeEvent,
  Upload,
  Trash2,
  Plus,
  LoaderCircle,
  Package,
  AlertCircle,
} from "lucide-react"

import {
  deleteFurniture,
  listUploadedFurniture,
  uploadFurnitureGlb,
} from "../lib/api"
import type { FurnitureUploadItem } from "../types"

interface FurnitureUploaderProps {
  onAddToScene?: (item: FurnitureUploadItem) => void
  isCompact?: boolean
}

export function FurnitureUploader({ onAddToScene, isCompact = false }: FurnitureUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const abortRef = useRef<AbortController | null>(null)
  
  const [furnitureList, setFurnitureList] = useState<FurnitureUploadItem[]>([])
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(true)

  // 加载已上传的家具列表
  const refreshList = useCallback(async () => {
    setLoading(true)
    try {
      const controller = new AbortController()
      abortRef.current = controller
      const list = await listUploadedFurniture(controller.signal)
      setFurnitureList(list)
      setError("")
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return
      setError(err instanceof Error ? err.message : "加载家具列表失败")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refreshList()
    return () => abortRef.current?.abort()
  }, [refreshList])

  // 处理文件选择
  const handleFileSelect = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // 验证文件类型
    if (!file.name.toLowerCase().endsWith(".glb") && !file.name.toLowerCase().endsWith(".gltf")) {
      setError("请选择 .glb 或 .gltf 格式的文件")
      return
    }

    // 验证文件大小
    if (file.size > 50 * 1024 * 1024) {
      setError("文件大小不能超过 50MB")
      return
    }

    setUploading(true)
    setError("")
    setUploadProgress(`正在上传 ${file.name}...`)

    try {
      const controller = new AbortController()
      abortRef.current = controller
      
      const result = await uploadFurnitureGlb(file, controller.signal)
      
      // 添加到列表
      setFurnitureList((prev) => [
        { id: result.id, name: result.name, glbUrl: result.glbUrl },
        ...prev,
      ])
      setUploadProgress("上传成功！")
      
      // 清空 input
      if (inputRef.current) inputRef.current.value = ""
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return
      setError(err instanceof Error ? err.message : "上传失败")
    } finally {
      setUploading(false)
      setTimeout(() => setUploadProgress(""), 2000)
    }
  }

  // 删除家具
  const handleDelete = async (id: string) => {
    try {
      await deleteFurniture(id)
      setFurnitureList((prev) => prev.filter((item) => item.id !== id))
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除失败")
    }
  }

  // 拖拽上传
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    
    const file = e.dataTransfer.files[0]
    if (!file) return
    
    // 模拟文件选择事件
    const dataTransfer = new DataTransfer()
    dataTransfer.items.add(file)
    if (inputRef.current) {
      inputRef.current.files = dataTransfer.files
      // 触发 change 事件
      const event = new Event("change", { bubbles: true })
      inputRef.current.dispatchEvent(event)
    }
  }

  if (isCompact) {
    return (
      <div className="furniture-uploader furniture-uploader--compact">
        <input
          ref={inputRef}
          type="file"
          accept=".glb,.gltf"
          onChange={handleFileSelect}
          className="sr-only"
        />
        
        <button
          type="button"
          className="furniture-upload-btn"
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          title="上传家具GLB"
        >
          {uploading ? <LoaderCircle className="spin" size={16} /> : <Plus size={16} />}
          上传家具
        </button>

        {furnitureList.length > 0 && (
          <div className="furniture-quick-list">
            {furnitureList.map((item) => (
              <button
                key={item.id}
                type="button"
                className="furniture-quick-item"
                onClick={() => onAddToScene?.(item)}
                title={`添加 ${item.name}`}
              >
                <Package size={14} />
                <span>{item.name}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div 
      className="furniture-uploader"
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* 头部 */}
      <div className="furniture-uploader__header">
        <h3>🪑 家具库</h3>
        <span className="furniture-count">{furnitureList.length} 件</span>
      </div>

      {/* 上传区域 */}
      <input
        ref={inputRef}
        type="file"
        accept=".glb,.gltf"
        onChange={handleFileSelect}
        className="sr-only"
      />

      <div
        className={`furniture-upload-zone ${uploading ? "is-uploading" : ""}`}
        onClick={() => !uploading && inputRef.current?.click()}
      >
        {uploading ? (
          <>
            <LoaderCircle className="spin" size={24} />
            <span>{uploadProgress}</span>
          </>
        ) : (
          <>
            <Upload size={24} />
            <strong>点击或拖拽上传 GLB</strong>
            <span>支持 .glb / .gltf · 最大 50MB</span>
          </>
        )}
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="furniture-error" role="alert">
          <AlertCircle size={14} />
          <span>{error}</span>
        </div>
      )}

      {/* 加载状态 */}
      {loading && (
        <div className="furniture-loading">
          <LoaderCircle className="spin" size={16} />
          <span>加载中...</span>
        </div>
      )}

      {/* 家具列表 */}
      {!loading && furnitureList.length > 0 && (
        <div className="furniture-list">
          <h4>已上传</h4>
          {furnitureList.map((item) => (
            <div key={item.id} className="furniture-list__item">
              <div className="furniture-list__icon">📦</div>
              <div className="furniture-list__info">
                <span className="name">{item.name}</span>
                <span className="url">{item.glbUrl.split("/").pop()}</span>
              </div>
              <div className="furniture-list__actions">
                {onAddToScene && (
                  <button
                    type="button"
                    className="action-btn action-btn--add"
                    onClick={() => onAddToScene(item)}
                    title="添加到场景"
                  >
                    <Plus size={14} />
                  </button>
                )}
                <button
                  type="button"
                  className="action-btn action-btn--delete"
                  onClick={() => handleDelete(item.id)}
                  title="删除"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 空状态 */}
      {!loading && furnitureList.length === 0 && !error && (
        <div className="furniture-empty">
          <Package size={32} opacity={0.3} />
          <p>还没有上传家具模型</p>
          <p className="hint">上传 GLB 文件后可在此处管理</p>
        </div>
      )}
    </div>
  )
}
