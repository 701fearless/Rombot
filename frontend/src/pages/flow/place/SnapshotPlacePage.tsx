import { Image, Text, View } from '@tarojs/components'
import type { ITouchEvent } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useEffect, useMemo, useRef, useState } from 'react'
import AppHeader from '@/components/AppHeader'
import { canvasToWorld, worldToCanvas } from '@/lib/sceneCoordinates'
import { getPrebuiltAsset, getSceneSnapshot, putSceneSnapshot } from '@/services/backend'
import { buildMockLayoutAdvice } from '@/services/layoutAdvice'
import { useSceneStore } from '@/store'
import type { PendingFeedAsset, RoomLayoutAdvice, SceneSnapshot, SnapshotObject } from '@/types/scene'
import './snapshot.scss'

const CANVAS_WIDTH = 336
const CANVAS_HEIGHT = 360
const GRID = 8

interface Props {
  sceneId: string
  frameId?: string
  objectId?: string
}

interface DragState { id: string; startX: number; startY: number; originX: number; originY: number; halfWidth: number; halfHeight: number }

function listValue(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String) : value ? [String(value)] : []
}

function snapshotObjectFromFeed(asset: PendingFeedAsset): SnapshotObject {
  const dims = asset.prebuilt.estimatedDimensions ?? asset.detected.estimatedDimensions
  const width = dims?.widthM ?? 1
  const depth = dims?.depthM ?? 0.7
  const height = dims?.heightM ?? 0.8
  const features = asset.detected.visualFeatures ?? {}
  return {
    instanceId: `feed_${asset.frameId}_${asset.detected.id}`,
    source: { type: 'feed', videoId: asset.videoId, time: asset.time, frameId: asset.frameId, objectId: asset.detected.id },
    semantic: {
      label: asset.detected.label,
      name: asset.detected.name,
      category: asset.detected.label,
      colors: listValue(features.colors),
      materials: listValue(features.materials),
      styles: listValue(features.style),
      functions: [],
    },
    geometry: { size: [width, height, depth], glbUrl: asset.prebuilt.glbUrl, cropUrl: asset.detected.cropUrl },
    transform: { position: [3, height / 2, 2.1], rotation: [0, 0, 0], scale: [1, 1, 1] },
    placement: { isExisting: false, locked: false, zone: 'living_area' },
  }
}

export default function SnapshotPlacePage({ sceneId, frameId, objectId }: Props) {
  const { snapshot, pendingAsset, selectedInstanceId, saveMode, setSnapshot, setPendingAsset, setSelectedInstanceId, setSaveMode, upsertObject, updateObject } = useSceneStore()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [advice, setAdvice] = useState<RoomLayoutAdvice | null>(null)
  const [saving, setSaving] = useState(false)
  const [dragPreview, setDragPreview] = useState<{ id: string; x: number; y: number } | null>(null)
  const dragRef = useRef<DragState | null>(null)
  const initializedRef = useRef('')

  useEffect(() => {
    let alive = true
    const local = snapshot?.sceneId === sceneId ? snapshot : null
    if (local) setLoading(false)
    getSceneSnapshot(sceneId)
      .then((remote) => {
        if (!alive) return
        const remoteIsNewer = !local
          || remote.revision > local.revision
          || (remote.revision === local.revision && Date.parse(remote.updatedAt) >= Date.parse(local.updatedAt))
        if (remoteIsNewer) setSnapshot(remote)
        setLoading(false)
      })
      .catch((reason) => {
        if (!alive) return
        if (!local) setError(reason instanceof Error ? reason.message : '快照读取失败')
        setSaveMode('local')
        setLoading(false)
      })
    return () => { alive = false }
    // snapshot is intentionally read once as the local fallback.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sceneId])

  useEffect(() => {
    if (!snapshot || snapshot.sceneId !== sceneId || !frameId || !objectId) return
    const sourceKey = `${frameId}:${objectId}`
    if (initializedRef.current === sourceKey) return
    const existing = snapshot.objects.find((item) => item.source.frameId === frameId && item.source.objectId === objectId)
    if (existing) {
      setSelectedInstanceId(existing.instanceId)
      initializedRef.current = sourceKey
      return
    }

    const add = (asset: PendingFeedAsset) => {
      const object = snapshotObjectFromFeed(asset)
      upsertObject(object)
      setSelectedInstanceId(object.instanceId)
      setPendingAsset(null)
      initializedRef.current = sourceKey
    }
    if (pendingAsset?.frameId === frameId && pendingAsset.detected.id === objectId) {
      add(pendingAsset)
      return
    }
    getPrebuiltAsset(frameId, objectId)
      .then((prebuilt) => add({ videoId: frameId.split('_')[0], time: 0, frameId, prebuilt, detected: { id: objectId, label: prebuilt.label, name: prebuilt.name, confidence: 1, bbox: [0, 0, 1, 1], tagPosition: [0.5, 0.5], prebuiltGlbUrl: prebuilt.glbUrl, estimatedDimensions: prebuilt.estimatedDimensions } }))
      .catch((reason) => setError(reason instanceof Error ? reason.message : '家具加载失败'))
  }, [frameId, objectId, pendingAsset, sceneId, setPendingAsset, setSelectedInstanceId, snapshot, upsertObject])

  const selected = snapshot?.objects.find((item) => item.instanceId === selectedInstanceId)
  const objectViews = useMemo(() => snapshot?.objects.map((item) => {
    const point = worldToCanvas(snapshot, item.transform.position, CANVAS_WIDTH, CANVAS_HEIGHT)
    const width = Math.max(42, Math.min(126, item.geometry.size[0] / 6 * CANVAS_WIDTH))
    const height = Math.max(38, Math.min(104, item.geometry.size[2] / 4.2 * CANVAS_HEIGHT))
    return { item, point: dragPreview?.id === item.instanceId ? dragPreview : point, width, height }
  }) ?? [], [dragPreview, snapshot])

  const touchStart = (item: SnapshotObject, event: ITouchEvent) => {
    if (item.placement.locked) return
    const touch = event.touches[0]
    const point = worldToCanvas(snapshot!, item.transform.position, CANVAS_WIDTH, CANVAS_HEIGHT)
    const halfWidth = Math.max(21, Math.min(63, item.geometry.size[0] / 6 * CANVAS_WIDTH / 2)) * item.transform.scale[0]
    const halfHeight = Math.max(19, Math.min(52, item.geometry.size[2] / 4.2 * CANVAS_HEIGHT / 2)) * item.transform.scale[2]
    dragRef.current = { id: item.instanceId, startX: touch.clientX, startY: touch.clientY, originX: point.x, originY: point.y, halfWidth, halfHeight }
    setSelectedInstanceId(item.instanceId)
    setDragPreview({ id: item.instanceId, ...point })
  }

  const touchMove = (event: ITouchEvent) => {
    const drag = dragRef.current
    if (!drag) return
    const touch = event.touches[0]
    const x = Math.max(drag.halfWidth, Math.min(CANVAS_WIDTH - drag.halfWidth, Math.round((drag.originX + touch.clientX - drag.startX) / GRID) * GRID))
    const y = Math.max(drag.halfHeight, Math.min(CANVAS_HEIGHT - drag.halfHeight, Math.round((drag.originY + touch.clientY - drag.startY) / GRID) * GRID))
    setDragPreview({ id: drag.id, x, y })
  }

  const touchEnd = () => {
    const drag = dragRef.current
    const preview = dragPreview
    const item = snapshot?.objects.find((candidate) => candidate.instanceId === drag?.id)
    if (drag && preview && item && snapshot) {
      updateObject(item.instanceId, { ...item.transform, position: canvasToWorld(snapshot, preview, item.geometry.size[1], CANVAS_WIDTH, CANVAS_HEIGHT) })
    }
    dragRef.current = null
    setDragPreview(null)
  }

  const changeSelected = (rotateDelta = 0, scaleDelta = 0) => {
    if (!selected) return
    const scale = Math.max(0.6, Math.min(1.8, selected.transform.scale[0] + scaleDelta))
    updateObject(selected.instanceId, {
      ...selected.transform,
      rotation: [0, selected.transform.rotation[1] + rotateDelta * Math.PI / 180, 0],
      scale: [scale, scale, scale],
    })
  }

  const persist = async (value: SceneSnapshot) => {
    try {
      const saved = await putSceneSnapshot(value)
      setSnapshot(saved)
      setSaveMode('server')
      return saved
    } catch {
      const local = { ...value, revision: value.revision + 1, updatedAt: new Date().toISOString() }
      setSnapshot(local)
      setSaveMode('local')
      return local
    }
  }

  const saveAndReview = async () => {
    if (!snapshot) return
    setSaving(true)
    const saved = await persist(snapshot)
    setAdvice(buildMockLayoutAdvice(saved, selectedInstanceId))
    setSaving(false)
  }

  const applyMove = async () => {
    const move = advice?.layout.moves[0]
    if (!snapshot || !move) return
    const next: SceneSnapshot = {
      ...snapshot,
      updatedAt: new Date().toISOString(),
      objects: snapshot.objects.map((item) => item.instanceId === move.objectId ? { ...item, transform: { ...item.transform, position: move.toPosition, rotation: move.toRotation } } : item),
    }
    setSnapshot(next)
    setSaving(true)
    const saved = await persist(next)
    setAdvice(buildMockLayoutAdvice(saved, move.objectId))
    setSaving(false)
    Taro.showToast({ title: '建议已应用并保存', icon: 'none' })
  }

  if (loading) return <View className='snapshot-place'><AppHeader title='ROOM6' /><View className='snapshot-place__state'><Text>正在载入户型快照</Text></View></View>
  if (!snapshot || error) return <View className='snapshot-place'><AppHeader title='ROOM6' /><View className='snapshot-place__state'><Text>{error || '快照不可用'}</Text><View className='snapshot-place__back' onClick={() => Taro.navigateBack()}><Text>返回 Feed</Text></View></View></View>

  return (
    <View className='snapshot-place'>
      <AppHeader title='ROOM6 布置方案' />
      <View className='snapshot-place__summary'>
        <View><Text className='snapshot-place__title'>room6 · 客厅</Text><Text className='snapshot-place__meta'>6.0m × 4.2m · {snapshot.objects.length} 件家具</Text></View>
        <Text className={`snapshot-place__save-state ${saveMode === 'local' ? 'is-local' : ''}`}>{saveMode === 'server' ? `云端版本 ${snapshot.revision}` : '本地保存'}</Text>
      </View>

      <View className='snapshot-place__canvas' style={{ width: `${CANVAS_WIDTH}px`, height: `${CANVAS_HEIGHT}px` }}>
        <View className='snapshot-place__grid' />
        <View className='snapshot-place__door'><Text>门</Text></View>
        <View className='snapshot-place__window'><Text>窗</Text></View>
        {objectViews.map(({ item, point, width, height }) => (
          <View
            key={item.instanceId}
            className={`snapshot-object ${item.instanceId === selectedInstanceId ? 'is-selected' : ''} ${item.placement.isExisting ? 'is-existing' : 'is-new'}`}
            style={{ left: `${point.x}px`, top: `${point.y}px`, width: `${width}px`, height: `${height}px`, transform: `translate(-50%, -50%) rotate(${item.transform.rotation[1] * 180 / Math.PI}deg) scale(${item.transform.scale[0]})` }}
            onTouchStart={(event) => touchStart(item, event as ITouchEvent)}
            onTouchMove={(event) => touchMove(event as ITouchEvent)}
            onTouchEnd={() => touchEnd()}
            onClick={() => setSelectedInstanceId(item.instanceId)}
          >
            {item.geometry.cropUrl ? <Image className='snapshot-object__image' src={item.geometry.cropUrl} mode='aspectFill' /> : <View className='snapshot-object__placeholder' />}
            <Text className='snapshot-object__name'>{item.semantic.name}</Text>
          </View>
        ))}
      </View>

      {selected && (
        <View className='snapshot-place__controls'>
          <View className='snapshot-place__control' onClick={() => changeSelected(-15, 0)}><Text>↶</Text></View>
          <View className='snapshot-place__control' onClick={() => changeSelected(15, 0)}><Text>↷</Text></View>
          <View className='snapshot-place__control' onClick={() => changeSelected(0, -0.1)}><Text>−</Text></View>
          <View className='snapshot-place__control' onClick={() => changeSelected(0, 0.1)}><Text>＋</Text></View>
          <View className='snapshot-place__selection'><Text>{selected.semantic.name}</Text><Text>{selected.transform.position[0].toFixed(2)}m, {selected.transform.position[2].toFixed(2)}m</Text></View>
        </View>
      )}

      <View className='snapshot-place__save' onClick={() => !saving && void saveAndReview()}><Text>{saving ? '正在保存' : '完成摆放并查看建议'}</Text></View>

      {advice && (
        <View className='snapshot-advice'>
          <View className='snapshot-advice__head'><Text className='snapshot-advice__title'>空间优化建议</Text><Text className='snapshot-advice__mock'>MOCK</Text></View>
          <Text className='snapshot-advice__summary'>{advice.layout.summary}</Text>
          <View className='snapshot-advice__list'>
            {advice.layout.advices.map((item) => <View key={item.id} className='snapshot-advice__item'><Text className='snapshot-advice__priority'>{item.priority}</Text><View><Text className='snapshot-advice__item-title'>{item.title}</Text><Text className='snapshot-advice__item-copy'>{item.suggestion}</Text></View></View>)}
          </View>
          {advice.layout.moves.length > 0 && <View className='snapshot-advice__apply' onClick={() => !saving && void applyMove()}><Text>一键应用动线建议</Text></View>}
        </View>
      )}
    </View>
  )
}
