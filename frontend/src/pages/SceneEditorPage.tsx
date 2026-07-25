import { ArrowLeft, Box, BrickWall, Check, Copy, LoaderCircle, Plus, RotateCcw, RotateCw, Save, Scale, Sparkles, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import type * as THREE from 'three'
import { GLTFExporter } from 'three/examples/jsm/exporters/GLTFExporter.js'
import { SceneEditor3D } from '@/components/SceneEditor3D'
import { useToast } from '@/components/ToastProvider'
import { snapshotToSceneResponse } from '@/lib/snapshotSceneAdapter'
import { buildMockLayoutAdvice } from '@/services/layoutAdvice'
import { getSceneSnapshot, putSceneSnapshot, requestRoomLayout, resetSceneSnapshot, saveRuntimeWhitebox } from '@/services/backend'
import { useSceneStore } from '@/store'
import type { GeneratedFurniture, RoomLayoutAdvice, SceneSnapshot, SnapshotObject, SnapshotWall, Vector3 } from '@/types/scene'

const copy3 = (value: Vector3): Vector3 => [...value] as Vector3
function id(prefix = 'furniture') { return `${prefix}_${Date.now().toString(36)}_${crypto.randomUUID().slice(0, 6)}` }

export function SceneEditorPage() {
  const [params] = useSearchParams(); const navigate = useNavigate(); const toast = useToast(); const sceneId = params.get('sceneId') || 'room6'
  const pending = useSceneStore((s) => s.pendingAsset); const clearPending = useSceneStore((s) => s.setPendingAsset); const library = useSceneStore((s) => s.furnitureLibrary); const stored = useSceneStore((s) => s.snapshot); const setStored = useSceneStore((s) => s.setSnapshot); const setSaveMode = useSceneStore((s) => s.setSaveMode)
  const initialStored = useRef(stored).current
  const [snapshot, setSnapshot] = useState<SceneSnapshot | null>(stored?.sceneId === sceneId ? stored : null); const [selectedId, setSelectedId] = useState(''); const [wallMode, setWallMode] = useState(false); const [busy, setBusy] = useState(!snapshot); const [saving, setSaving] = useState(false); const [advice, setAdvice] = useState<RoomLayoutAdvice | null>(null); const [adviceSource, setAdviceSource] = useState<'空间接口' | 'Mock' | ''>(''); const wallRootRef = useRef<THREE.Group | null>(null)
  const update = useCallback((fn: (value: SceneSnapshot) => SceneSnapshot) => setSnapshot((current) => { if (!current) return current; const next = fn(current); setStored(next); return next }), [setStored])
  useEffect(() => { let live = true; setBusy(true); getSceneSnapshot(sceneId).then((data) => { if (!live) return; const cached = initialStored?.sceneId === sceneId && initialStored.revision >= data.revision ? initialStored : data; setSnapshot(cached); setStored(cached); setSaveMode('server') }).catch(() => { if (initialStored?.sceneId === sceneId) { setSnapshot(initialStored); setSaveMode('local'); toast.show('后端不可用，已打开本地快照') } else toast.show('room6 快照读取失败') }).finally(() => live && setBusy(false)); return () => { live = false } }, [initialStored, sceneId, setSaveMode, setStored, toast])
  useEffect(() => { if (!snapshot || !pending || pending.prebuilt.frameId !== params.get('frameId') || pending.prebuilt.objectId !== params.get('objectId')) return; const exists = snapshot.objects.find((item) => item.source.frameId === pending.frameId && item.source.objectId === pending.prebuilt.objectId); if (exists) { setSelectedId(exists.instanceId); clearPending(null); return } const dims = pending.prebuilt.estimatedDimensions ?? pending.detected.estimatedDimensions; const size: Vector3 = dims ? [dims.widthM, dims.heightM, dims.depthM] : [1, 1, 1]; const next: SnapshotObject = { instanceId: id(pending.prebuilt.label), source: { type: 'feed', videoId: pending.videoId, time: pending.time, frameId: pending.frameId, objectId: pending.prebuilt.objectId }, semantic: { label: pending.prebuilt.label, name: pending.prebuilt.name, category: pending.prebuilt.label, colors: [], materials: [], styles: [], functions: [] }, geometry: { size, glbUrl: pending.prebuilt.glbUrl, cropUrl: pending.detected.cropUrl }, transform: { position: [3, size[1] / 2, 2.1], rotation: [0, 0, 0], scale: [1, 1, 1] }, placement: { isExisting: false, locked: false, zone: 'living_area' } }; update((value) => ({ ...value, objects: [...value.objects, next], updatedAt: new Date().toISOString() })); setSelectedId(next.instanceId); clearPending(null); toast.show('家具已加入 room6') }, [snapshot, pending, params, clearPending, update, toast])
  const selected = snapshot?.objects.find((item) => item.instanceId === selectedId)
  const mutateSelected = (fn: (item: SnapshotObject) => SnapshotObject) => update((value) => ({ ...value, objects: value.objects.map((item) => item.instanceId === selectedId ? fn(item) : item), updatedAt: new Date().toISOString() }))
  const addFromLibrary = (item: GeneratedFurniture) => {
    const dims = item.estimatedDimensions
    const size: Vector3 = dims ? [dims.widthM, dims.heightM, dims.depthM] : [1, 1, 1]
    const next: SnapshotObject = {
      instanceId: id(item.label),
      source: {
        type: 'library',
        videoId: item.videoId,
        time: 0,
        frameId: item.representativeFrameId,
        objectId: item.representativeObjectId,
      },
      semantic: {
        label: item.label,
        name: item.name,
        category: item.category,
        colors: [],
        materials: [],
        styles: [],
        functions: [],
      },
      geometry: { size, glbUrl: item.glbUrl, cropUrl: item.previewUrl },
      transform: { position: [3, size[1] / 2, 2.1], rotation: [0, 0, 0], scale: [1, 1, 1] },
      placement: { isExisting: false, locked: false, zone: 'living_area' },
    }
    update((value) => ({ ...value, objects: [...value.objects, next], updatedAt: new Date().toISOString() }))
    setSelectedId(next.instanceId)
    toast.show(`${item.name} 已加入当前空间`)
  }
  const onObjectTransform = useCallback((instanceId: string, position: Vector3) => update((value) => ({ ...value, objects: value.objects.map((item) => item.instanceId === instanceId ? { ...item, transform: { ...item.transform, position } } : item), updatedAt: new Date().toISOString() })), [update])
  const onWallChange = useCallback((wall: SnapshotWall) => update((value) => ({ ...value, room: { ...value.room, walls: value.room.walls.map((item) => item.id === wall.id ? wall : item) }, updatedAt: new Date().toISOString() })), [update])
  const onReady = useCallback((root: THREE.Group) => { wallRootRef.current = root }, [])
  const save = async (value = snapshot) => { if (!value) return null; setSaving(true); try { const saved = await putSceneSnapshot(value); setSnapshot(saved); setStored(saved); setSaveMode('server'); toast.show(`方案已保存 · revision ${saved.revision}`); return saved } catch { setStored(value); setSaveMode('local'); toast.show('后端不可用，已保存到本地'); return value } finally { setSaving(false) } }
  const analyze = async () => { const saved = await save(); if (!saved) return; try { const result = await requestRoomLayout(snapshotToSceneResponse(saved)); setAdvice(result); setAdviceSource('空间接口') } catch { setAdvice(buildMockLayoutAdvice(saved, selectedId)); setAdviceSource('Mock') } }
  const applyAdvice = async () => { if (!snapshot || !advice) return; const moves = new Map(advice.layout.moves.map((move) => [move.objectId, move])); const next = { ...snapshot, objects: snapshot.objects.map((item) => { const move = moves.get(item.instanceId); return move ? { ...item, transform: { ...item.transform, position: copy3(move.toPosition), rotation: move.toRotation ? copy3(move.toRotation) : item.transform.rotation } } : item }), updatedAt: new Date().toISOString() }; setSnapshot(next); setStored(next); await save(next); toast.show(`已应用 ${moves.size} 条移动建议`) }
  const exportWalls = async () => { if (!snapshot || !wallRootRef.current) return; setSaving(true); try { const exporter = new GLTFExporter(); const result = await exporter.parseAsync(wallRootRef.current.clone(true), { binary: true, onlyVisible: false }); if (!(result instanceof ArrayBuffer)) throw new Error('GLB 导出失败'); const saved = await saveRuntimeWhitebox(snapshot, new Blob([result], { type: 'model/gltf-binary' })); setSnapshot(saved); setStored(saved); toast.show('运行版白模已保存') } catch (error) { toast.show(error instanceof Error ? error.message : '白模保存失败') } finally { setSaving(false) } }
  const reset = async () => { setSaving(true); try { const restored = await resetSceneSnapshot(sceneId); setSnapshot(restored); setStored(restored); setAdvice(null); setSelectedId(''); toast.show('已恢复 room6 模板') } catch { toast.show('重置失败') } finally { setSaving(false) } }
  if (busy || !snapshot) return <div className='editor-loading'><LoaderCircle className='spin' />正在加载 room6</div>
  return <div className='editor-page'>
    <header className='editor-header'><button type='button' onClick={() => navigate(-1)} aria-label='返回'><ArrowLeft /></button><div><strong>room6 空间编辑器</strong><span>revision {snapshot.revision} · {snapshot.objects.length} 件家具</span></div><div className='editor-header__actions'><button type='button' aria-label='重置方案' onClick={() => void reset()}><RotateCcw /><span>重置</span></button><button className='is-primary' type='button' aria-label='保存方案' disabled={saving} onClick={() => void save()}><Save /><span>保存方案</span></button></div></header>
    <main className='editor-workspace'><section className='editor-stage'><SceneEditor3D snapshot={snapshot} selectedId={selectedId} wallMode={wallMode} onSelect={setSelectedId} onObjectTransform={onObjectTransform} onWallChange={onWallChange} onReady={onReady} /><div className='mode-switch'><button type='button' className={!wallMode ? 'is-active' : ''} onClick={() => { setWallMode(false); setSelectedId('') }}><Box />家具</button><button type='button' className={wallMode ? 'is-active' : ''} onClick={() => { setWallMode(true); setSelectedId('') }}><BrickWall />墙体</button></div><div className='scene-legend'>拖动移动 · 拖动空白处旋转视角 · 滚轮缩放 · 10cm 网格吸附</div></section>
      <aside className='editor-panel'>
        {!wallMode ? <><section><span className='eyebrow'>SELECTED OBJECT</span><h2>{selected?.semantic.name ?? '选择一件家具'}</h2>{selected ? <div className='object-tools'><button type='button' onClick={() => mutateSelected((item) => ({ ...item, transform: { ...item.transform, rotation: [item.transform.rotation[0], item.transform.rotation[1] + Math.PI / 12, item.transform.rotation[2]] } }))}><RotateCw />旋转 15°</button><button type='button' onClick={() => mutateSelected((item) => ({ ...item, transform: { ...item.transform, scale: item.transform.scale.map((n) => Math.min(2, n + .1)) as Vector3 } }))}><Scale />放大</button><button type='button' onClick={() => { const clone = structuredClone(selected); clone.instanceId = id(selected.semantic.label); clone.transform.position = [Math.min(5.5, clone.transform.position[0] + .3), clone.transform.position[1], clone.transform.position[2]]; update((v) => ({ ...v, objects: [...v.objects, clone] })); setSelectedId(clone.instanceId) }}><Copy />复制</button><button className='is-danger' type='button' onClick={() => { update((v) => ({ ...v, objects: v.objects.filter((item) => item.instanceId !== selectedId) })); setSelectedId('') }}><Trash2 />删除</button></div> : <p>点击家具后可拖动、旋转、缩放、复制或删除。</p>}</section><section className='editor-library'><div className='section-title'><div><span className='eyebrow'>MY FURNITURE</span><h3>家具库素材</h3></div><Box /></div>{library.length ? <div className='editor-library__grid'>{library.map((item) => <button type='button' key={item.id} onClick={() => addFromLibrary(item)}><img src={item.previewUrl} alt={`${item.name} 生成参考图`} loading='lazy' /><span><strong>{item.name}</strong><small>{item.category}</small></span><Plus /></button>)}</div> : <div className='editor-library__empty'><p>家具库还是空的，请先从灵感页收藏模型。</p><Link to='/'>浏览家具灵感</Link></div>}</section><section><div className='section-title'><div><span className='eyebrow'>SCENE OBJECTS</span><h3>当前场景家具</h3></div><Box /></div><div className='scene-object-list'>{snapshot.objects.map((item, index) => <button className={item.instanceId === selectedId ? 'is-active' : ''} type='button' key={item.instanceId} onClick={() => setSelectedId(item.instanceId)}><span>{item.semantic.name}</span><small>{item.source.type === 'feed' || item.source.type === 'library' ? `家具库 · #${index + 1}` : `场景家具 · #${index + 1}`}</small></button>)}{!snapshot.objects.length && <p>从家具库选择素材后，即可加入 room6。</p>}</div></section></> : <section><span className='eyebrow'>WALL EDITOR</span><h2>{selectedId || '选择墙体'}</h2><p>拖动墙体时自动吸附墙端点和 10cm 网格。运行版保存不会覆盖预设白模。</p>{selectedId && <button className='danger-wide' type='button' onClick={() => { update((v) => ({ ...v, room: { ...v.room, walls: v.room.walls.filter((w) => w.id !== selectedId) } })); setSelectedId('') }}><Trash2 />删除墙体</button>}<button className='primary-button' type='button' onClick={() => void exportWalls()}><Save />保存运行版白模</button></section>}
        <section className='advice-actions'><button className='primary-button' type='button' onClick={() => void analyze()}><Sparkles />完成摆放并查看建议</button></section>
        {advice && <section className='advice-panel'><div className='section-title'><div><span className='eyebrow'>{adviceSource}</span><h3>布局建议</h3></div><span>{advice.overallStatus}</span></div><p>{advice.layout.summary}</p>{advice.layout.advices.map((item) => <article key={item.id}><strong>{item.title}</strong><p>{item.suggestion}</p></article>)}{!!advice.layout.moves.length && <button className='primary-button' type='button' onClick={() => void applyAdvice()}><Check />应用全部 {advice.layout.moves.length} 条建议</button>}</section>}
        <Link className='editor-complete' to='/complete'>完成当前方案</Link>
      </aside>
    </main>
  </div>
}
