import { ArrowLeft, Baby, Box, Check, Compass, Copy, LoaderCircle, MessageSquareText, PawPrint, Plus, RotateCcw, RotateCw, Save, Scale, ShoppingBag, Sparkles, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { SceneEditor3D } from '@/components/SceneEditor3D'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { useToast } from '@/components/ToastProvider'
import { getSceneSnapshot, listGeneratedFurniture, putSceneSnapshot, requestSkillAdvice, resetSceneSnapshot } from '@/services/backend'
import { useSceneStore } from '@/store'
import type { GeneratedFurniture, SceneSnapshot, SkillAdviceResponse, SkillAdviceScenario, SkillAdviceSuggestion, SnapshotObject, Vector3 } from '@/types/scene'

function id(prefix = 'furniture') { return `${prefix}_${Date.now().toString(36)}_${crypto.randomUUID().slice(0, 6)}` }
function normalizedDegrees(radians: number) {
  const degrees = radians * 180 / Math.PI
  return Math.round(((degrees + 180) % 360 + 360) % 360 - 180)
}
function effectiveSize(item: SnapshotObject): Vector3 {
  return item.geometry.effectiveSize
    ?? item.geometry.size.map((value, index) => value * item.transform.scale[index]) as Vector3
}

const adviceScenarios: Array<{ id: SkillAdviceScenario; label: string; Icon: typeof Baby }> = [
  { id: 'children', label: '儿童', Icon: Baby },
  { id: 'pets', label: '宠物', Icon: PawPrint },
  { id: 'fengshui', label: '风水动线', Icon: Compass },
  { id: 'other', label: '其他', Icon: MessageSquareText },
]

const furnitureKeywords: Array<{ key: string; aliases: string[] }> = [
  { key: 'sofa', aliases: ['sofa', '沙发'] },
  { key: 'bed', aliases: ['bed', '床', '睡床'] },
  { key: 'chair', aliases: ['chair', 'armchair', '椅', '座椅', '单椅'] },
  { key: 'table', aliases: ['table', 'coffee_table', 'dining_table', '桌', '餐桌', '茶几', '边几'] },
  { key: 'desk', aliases: ['desk', '书桌', '办公桌'] },
  { key: 'cabinet', aliases: ['cabinet', 'wardrobe', 'bookshelf', 'tv_stand', 'nightstand', '柜', '衣柜', '书架', '电视柜', '床头柜', '收纳'] },
  { key: 'lamp', aliases: ['lamp', 'chandelier', 'pendant_light', 'floor_lamp', 'table_lamp', '灯', '吊灯', '落地灯', '台灯', '照明'] },
  { key: 'rug', aliases: ['rug', '地毯', '地垫'] },
  { key: 'curtain', aliases: ['curtain', '窗帘'] },
  { key: 'plant', aliases: ['plant', '绿植', '植物'] },
  { key: 'mirror', aliases: ['mirror', '镜', '镜子'] },
  { key: 'painting', aliases: ['painting', '挂画', '装饰画'] },
  { key: 'vase', aliases: ['vase', '花瓶'] },
]

function recommendationTerms(suggestion: SkillAdviceSuggestion) {
  const text = `${suggestion.title} ${suggestion.reason} ${suggestion.action}`.toLowerCase()
  const supplement = /增加|新增|添加|补充|添置|购置|采购|选购|加入|配置|增设|可考虑|建议放置|建议摆放/.test(text)
  if (!supplement) return []
  return furnitureKeywords.filter((group) => group.aliases.some((alias) => text.includes(alias))).flatMap((group) => group.aliases)
}

function recommendationMatches(suggestion: SkillAdviceSuggestion, catalog: GeneratedFurniture[]) {
  const terms = recommendationTerms(suggestion)
  if (!terms.length) return { requested: false, items: [] as GeneratedFurniture[] }
  const scored = catalog.map((item) => {
    const text = `${item.label} ${item.category} ${item.name}`.toLowerCase()
    const score = terms.reduce((total, term) => total + (text.includes(term) ? 1 : 0), 0)
    return { item, score }
  }).filter((entry) => entry.score > 0)
  scored.sort((a, b) => b.score - a.score || a.item.name.localeCompare(b.item.name))
  return { requested: true, items: scored.slice(0, 3).map((entry) => entry.item) }
}

export function SceneEditorPage() {
  const [params] = useSearchParams(); const navigate = useNavigate(); const toast = useToast(); const activeSceneId = useSceneStore((s) => s.activeSceneId); const requestedSceneId = params.get('sceneId'); const sceneId = requestedSceneId === 'room1' || requestedSceneId === 'room2' ? requestedSceneId : activeSceneId
  const pending = useSceneStore((s) => s.pendingAsset); const clearPending = useSceneStore((s) => s.setPendingAsset); const library = useSceneStore((s) => s.furnitureLibrary); const addFurnitureToLibrary = useSceneStore((s) => s.addFurnitureToLibrary); const removeFurnitureFromLibrary = useSceneStore((s) => s.removeFurnitureFromLibrary); const stored = useSceneStore((s) => s.snapshot); const setStored = useSceneStore((s) => s.setSnapshot); const setSaveMode = useSceneStore((s) => s.setSaveMode)
  const initialStored = useRef(stored).current
  const [snapshot, setSnapshot] = useState<SceneSnapshot | null>(stored?.sceneId === sceneId ? stored : null); const [selectedId, setSelectedId] = useState(''); const [busy, setBusy] = useState(!snapshot); const [saving, setSaving] = useState(false); const [analyzing, setAnalyzing] = useState(false); const [advice, setAdvice] = useState<SkillAdviceResponse | null>(null); const [adviceError, setAdviceError] = useState('')
  const [scenario, setScenario] = useState<SkillAdviceScenario | null>(null); const [ageRange, setAgeRange] = useState('3-6岁'); const [mobilityStage, setMobilityStage] = useState('walking'); const [species, setSpecies] = useState('cat'); const [behaviors, setBehaviors] = useState(''); const [fengshuiFocus, setFengshuiFocus] = useState('客厅动线')
  const [extraGoal, setExtraGoal] = useState(''); const [modeledCatalog, setModeledCatalog] = useState<GeneratedFurniture[]>([]); const [pendingLibraryDelete, setPendingLibraryDelete] = useState<GeneratedFurniture | null>(null)
  const update = useCallback((fn: (value: SceneSnapshot) => SceneSnapshot) => setSnapshot((current) => { if (!current) return current; const next = fn(current); setStored(next); return next }), [setStored])
  useEffect(() => { let live = true; setBusy(true); getSceneSnapshot(sceneId).then((data) => { if (!live) return; const cached = initialStored?.sceneId === sceneId && initialStored.revision >= data.revision ? initialStored : data; setSnapshot(cached); setStored(cached); setSaveMode('server') }).catch(() => { if (initialStored?.sceneId === sceneId) { setSnapshot(initialStored); setSaveMode('local'); toast.show('后端不可用，已打开本地快照') } else toast.show(`${sceneId} 快照读取失败`) }).finally(() => live && setBusy(false)); return () => { live = false } }, [initialStored, sceneId, setSaveMode, setStored, toast])
  useEffect(() => {
    let live = true
    listGeneratedFurniture()
      .then((items) => { if (live) setModeledCatalog(items.filter((item) => Boolean(item.glbUrl))) })
      .catch(() => { if (live) setModeledCatalog([]) })
    return () => { live = false }
  }, [])
  useEffect(() => { if (!snapshot || !pending || pending.prebuilt.frameId !== params.get('frameId') || pending.prebuilt.objectId !== params.get('objectId')) return; const exists = snapshot.objects.find((item) => item.source.frameId === pending.frameId && item.source.objectId === pending.prebuilt.objectId); if (exists) { setSelectedId(exists.instanceId); clearPending(null); return } const dims = pending.prebuilt.estimatedDimensions ?? pending.detected.estimatedDimensions; const size: Vector3 = dims ? [dims.widthM, dims.heightM, dims.depthM] : [1, 1, 1]; const roomXs = snapshot.room.floorPolygon.map(([x]) => x); const roomZs = snapshot.room.floorPolygon.map(([, z]) => z); const next: SnapshotObject = { instanceId: id(pending.prebuilt.label), source: { type: 'feed', videoId: pending.videoId, time: pending.time, frameId: pending.frameId, objectId: pending.prebuilt.objectId }, semantic: { label: pending.prebuilt.label, name: pending.prebuilt.name, category: pending.prebuilt.label, colors: [], materials: [], styles: [], functions: [] }, geometry: { size, glbUrl: pending.prebuilt.glbUrl, cropUrl: pending.detected.cropUrl }, transform: { position: [(Math.min(...roomXs) + Math.max(...roomXs)) / 2, size[1] / 2, (Math.min(...roomZs) + Math.max(...roomZs)) / 2], rotation: [0, 0, 0], scale: [1, 1, 1] }, placement: { isExisting: false, locked: false, zone: 'living_area' } }; update((value) => ({ ...value, objects: [...value.objects, next], updatedAt: new Date().toISOString() })); setSelectedId(next.instanceId); clearPending(null); toast.show(`家具已加入 ${sceneId}`) }, [snapshot, pending, params, clearPending, update, toast, sceneId])
  const selected = snapshot?.objects.find((item) => item.instanceId === selectedId)
  const mutateSelected = (fn: (item: SnapshotObject) => SnapshotObject) => update((value) => ({ ...value, objects: value.objects.map((item) => item.instanceId === selectedId ? fn(item) : item), updatedAt: new Date().toISOString() }))
  const addFromLibrary = (item: GeneratedFurniture) => {
    const dims = item.estimatedDimensions; const size: Vector3 = dims ? [dims.widthM, dims.heightM, dims.depthM] : [1, 1, 1]
    const xs = snapshot?.room.floorPolygon.map(([x]) => x) ?? [0, 6]; const zs = snapshot?.room.floorPolygon.map(([, z]) => z) ?? [0, 4.2]
    const next: SnapshotObject = { instanceId: id(item.label), source: { type: 'library', videoId: item.videoId, time: 0, frameId: item.representativeFrameId, objectId: item.representativeObjectId }, semantic: { label: item.label, name: item.name, category: item.category, colors: [], materials: [], styles: [], functions: [] }, geometry: { size, glbUrl: item.glbUrl, cropUrl: item.previewUrl }, transform: { position: [(Math.min(...xs) + Math.max(...xs)) / 2, size[1] / 2, (Math.min(...zs) + Math.max(...zs)) / 2], rotation: [0, 0, 0], scale: [1, 1, 1] }, placement: { isExisting: false, locked: false, zone: 'living_area', surface: 'floor', supportObjectId: null } }
    update((value) => ({ ...value, objects: [...value.objects, next], updatedAt: new Date().toISOString() })); setSelectedId(next.instanceId); toast.show(`${item.name} 已加入当前空间`)
  }
  const setSelectedRotation = (degrees: number) => mutateSelected((item) => ({
    ...item,
    transform: {
      ...item.transform,
      rotation: [item.transform.rotation[0], degrees * Math.PI / 180, item.transform.rotation[2]],
    },
  }))
  const setSelectedScale = (scale: number) => mutateSelected((item) => ({
    ...item,
    geometry: {
      ...item.geometry,
      effectiveSize: item.geometry.size.map((value) => Number((value * scale).toFixed(4))) as Vector3,
    },
    transform: { ...item.transform, scale: [scale, scale, scale] },
  }))
  const duplicateSelected = () => {
    if (!selected) return
    const clone = structuredClone(selected)
    clone.instanceId = id(selected.semantic.label)
    clone.transform.position = [Math.min(5.5, clone.transform.position[0] + .3), clone.transform.position[1], clone.transform.position[2]]
    update((value) => ({ ...value, objects: [...value.objects, clone], updatedAt: new Date().toISOString() }))
    setSelectedId(clone.instanceId)
    toast.show(`已复制 ${selected.semantic.name}`)
  }
  const deleteSelected = () => {
    if (!selected) return
    update((value) => ({ ...value, objects: value.objects.filter((item) => item.instanceId !== selectedId), updatedAt: new Date().toISOString() }))
    setSelectedId('')
    toast.show(`已删除 ${selected.semantic.name}`)
  }
  const onObjectTransform = useCallback((instanceId: string, transform: Pick<SnapshotObject['transform'], 'position' | 'rotation'>, placement: Pick<SnapshotObject['placement'], 'surface' | 'supportObjectId'>) => update((value) => ({ ...value, objects: value.objects.map((item) => item.instanceId === instanceId ? { ...item, transform: { ...item.transform, ...transform }, placement: { ...item.placement, ...placement } } : item), updatedAt: new Date().toISOString() })), [update])
  const save = async (value = snapshot) => { if (!value) return null; setSaving(true); try { const saved = await putSceneSnapshot(value); setSnapshot(saved); setStored(saved); setSaveMode('server'); toast.show(`方案已保存 · revision ${saved.revision}`); return saved } catch { setStored(value); setSaveMode('local'); toast.show('后端不可用，已保存到本地'); return value } finally { setSaving(false) } }
  const analyze = async () => {
    if (!scenario) {
      toast.show('请先选择一个建议目标')
      return
    }
    if (scenario === 'other' && !extraGoal.trim()) {
      toast.show('请填写其他需求')
      return
    }
    const saved = await save()
    if (!saved) return
    const scenarioProfile = scenario === 'children'
      ? { ageRange, mobilityStage }
      : scenario === 'pets'
        ? { species, behaviors }
        : scenario === 'fengshui'
          ? { focus: fengshuiFocus }
          : { extraRequest: extraGoal.trim() }
    setAnalyzing(true)
    setAdvice(null)
    setAdviceError('')
    try {
      setAdvice(await requestSkillAdvice(saved.sceneId, scenario, scenarioProfile))
    } catch (error) {
      const message = error instanceof Error ? error.message : 'AI 建议生成失败'
      setAdviceError(message)
      toast.show(message)
    } finally {
      setAnalyzing(false)
    }
  }
  const reset = async () => { setSaving(true); try { const restored = await resetSceneSnapshot(sceneId); setSnapshot(restored); setStored(restored); setAdvice(null); setSelectedId(''); toast.show(`已恢复 ${sceneId} 模板`) } catch { toast.show('重置失败') } finally { setSaving(false) } }
  const recommendationCatalog = [
    ...library,
    ...modeledCatalog.filter((item) => !library.some((saved) => saved.id === item.id)),
  ]
  if (busy || !snapshot) return <div className='editor-loading'><LoaderCircle className='spin' />正在加载 {sceneId}</div>
  return <div className='editor-page'>
    <ConfirmDialog
      open={Boolean(pendingLibraryDelete)}
      title={`删除“${pendingLibraryDelete?.name ?? ''}”？`}
      description='删除后它会从家具库移除，但已经放进当前空间的家具实例不会受到影响。'
      onCancel={() => setPendingLibraryDelete(null)}
      onConfirm={() => {
        if (!pendingLibraryDelete) return
        removeFurnitureFromLibrary(pendingLibraryDelete.id)
        toast.show(`${pendingLibraryDelete.name} 已从家具库删除`)
        setPendingLibraryDelete(null)
      }}
    />
    <header className='editor-header'><button type='button' onClick={() => navigate(-1)} aria-label='返回'><ArrowLeft /></button><div><strong>{sceneId} 空间编辑器</strong><span>revision {snapshot.revision} · {snapshot.objects.length} 件家具</span></div><div className='editor-header__actions'><button type='button' aria-label='重置方案' onClick={() => void reset()}><RotateCcw /><span>重置</span></button><button className='is-primary' type='button' aria-label='保存方案' disabled={saving} onClick={() => void save()}><Save /><span>保存方案</span></button></div></header>
    <main className='editor-workspace'><section className='editor-stage'><SceneEditor3D snapshot={snapshot} selectedId={selectedId} onSelect={setSelectedId} onObjectTransform={onObjectTransform} /><div className='scene-legend'>拖动移动 · 拖动空白处旋转视角 · 滚轮缩放 · 10cm 网格吸附</div></section>
      <aside className='editor-panel'>
        {selected ? <section className='selected-object-card' aria-live='polite'>
          <div className='selected-object-card__summary'>
            {selected.geometry.cropUrl
              ? <img src={selected.geometry.cropUrl} alt={`${selected.semantic.name} 预览`} />
              : <span className='selected-object-card__placeholder'><Box aria-hidden='true' /></span>}
            <div>
              <span className='eyebrow'>已选中家具</span>
              <h2>{selected.semantic.name}</h2>
              <p>{selected.semantic.category || selected.semantic.label} · {selected.source.type === 'feed' ? `视频 ${selected.source.videoId ?? '-'}` : selected.source.type === 'library' ? '家具库' : '场景模板'}</p>
            </div>
          </div>
          <dl className='selected-object-meta'>
            <div><dt>当前尺寸</dt><dd>{effectiveSize(selected)[0].toFixed(2)} × {effectiveSize(selected)[2].toFixed(2)} × {effectiveSize(selected)[1].toFixed(2)}m</dd></div>
            <div><dt>空间位置</dt><dd>X {selected.transform.position[0].toFixed(1)} · Z {selected.transform.position[2].toFixed(1)}</dd></div>
          </dl>
          <div className='selected-object-actions'>
            <button type='button' onClick={duplicateSelected}><Copy />复制</button>
            <button className='is-danger' type='button' onClick={deleteSelected}><Trash2 />删除</button>
          </div>
          <div className='transform-sliders'>
            <label htmlFor='selected-rotation'>
              <span><span><RotateCw />旋转</span><output>{normalizedDegrees(selected.transform.rotation[1])}°</output></span>
              <input id='selected-rotation' type='range' min='-180' max='180' step='5' value={normalizedDegrees(selected.transform.rotation[1])} onChange={(event) => setSelectedRotation(Number(event.target.value))} />
              <small><span>-180°</span><span>0°</span><span>180°</span></small>
            </label>
            <label htmlFor='selected-scale'>
              <span><span><Scale />缩放</span><output>{Math.round(selected.transform.scale[0] * 100)}%</output></span>
              <input id='selected-scale' type='range' min='.5' max='2' step='.05' value={selected.transform.scale[0]} onChange={(event) => setSelectedScale(Number(event.target.value))} />
              <small><span>缩小 50%</span><span>原始</span><span>放大 200%</span></small>
            </label>
          </div>
        </section> : <section className='selected-object-empty'><Box /><div><h2>点击场景中的家具</h2><p>选中后，这里只显示该家具的信息与编辑控制。</p></div></section>}
        <section className='editor-library'><div className='section-title'><div><span className='eyebrow'>MY FURNITURE</span><h3>家具库素材</h3></div><span className='editor-library__hint'>左右滑动选择</span></div>{library.length ? <div className='editor-library__rail'>{library.map((item) => <article key={item.id}><button className='editor-library__add' type='button' aria-label={`添加 ${item.name} 到当前空间`} onClick={() => addFromLibrary(item)}><span className='editor-library__image'><img src={item.previewUrl} alt='' loading='lazy' /><Plus aria-hidden='true' /></span><strong>{item.name}</strong><small>{item.category}</small></button><button className='editor-library__delete' type='button' aria-label={`从家具库删除 ${item.name}`} onClick={() => setPendingLibraryDelete(item)}><Trash2 /></button></article>)}</div> : <div className='editor-library__empty'><p>家具库还是空的，请先从灵感页收藏模型。</p><Link to='/'>浏览家具灵感</Link></div>}</section>
        <section className='advice-actions'>
          <span className='eyebrow'>ADVICE GOAL</span>
          <h3>这次想改善什么</h3>
          <div className='scenario-tabs'>
            {adviceScenarios.map(({ id: option, label, Icon }) => <button className={scenario === option ? 'is-active' : ''} type='button' key={option} onClick={() => setScenario(option)}><Icon />{label}</button>)}
          </div>
          {scenario === 'children' && <div className='scenario-fields'>
            <label>年龄段<select value={ageRange} onChange={(event) => setAgeRange(event.target.value)}><option>0-1岁</option><option>1-3岁</option><option>3-6岁</option><option>6岁以上</option></select></label>
            <label>行动阶段<select value={mobilityStage} onChange={(event) => setMobilityStage(event.target.value)}><option value='crawling'>爬行</option><option value='pulling-to-stand'>扶站</option><option value='walking'>行走</option><option value='climbing'>攀爬</option><option value='school-age'>学龄</option></select></label>
          </div>}
          {scenario === 'pets' && <div className='scenario-fields'>
            <label>宠物<select value={species} onChange={(event) => setSpecies(event.target.value)}><option value='cat'>猫</option><option value='dog'>狗</option><option value='rabbit'>兔类</option><option value='bird'>鸟类</option></select></label>
            <label>行为<input value={behaviors} onChange={(event) => setBehaviors(event.target.value)} placeholder='如抓挠、啃咬、跳窗' /></label>
          </div>}
          {scenario === 'fengshui' && <div className='scenario-fields'>
            <label>关注方向<select value={fengshuiFocus} onChange={(event) => setFengshuiFocus(event.target.value)}><option>客厅动线</option><option>入户体验</option><option>睡眠休息</option><option>采光与整洁</option></select></label>
          </div>}
          {scenario === 'other' && <label className='custom-advice-goal'>
            <span>填写其他需求</span>
            <textarea autoFocus value={extraGoal} maxLength={300} rows={3} onChange={(event) => setExtraGoal(event.target.value)} placeholder='例如：希望增加阅读角、家庭办公区或临时客卧。' />
            <small>{extraGoal.length}/300 · 必填</small>
          </label>}
          {!scenario && <p className='advice-goal-hint'>请选择一个建议目标</p>}
          <button className='primary-button' type='button' disabled={saving || analyzing || !scenario || (scenario === 'other' && !extraGoal.trim())} onClick={() => void analyze()}>{analyzing ? <LoaderCircle className='spin' /> : <Sparkles />}{analyzing ? '正在生成建议' : '完成摆放并生成建议'}</button>
        </section>
        {adviceError && <section className='advice-error'><strong>建议暂未生成</strong><p>{adviceError}</p></section>}
        {advice && <section className='advice-panel'>
          <div className='section-title'><div><span className='eyebrow'>{advice.skillName}</span><h3>{advice.scenarioName}建议</h3></div><span>{advice.model}</span></div>
          <p>{advice.summary}</p>
          {advice.suggestions.map((item) => {
            const recommendation = recommendationMatches(item, recommendationCatalog)
            return <article key={item.id}>
              <span className='advice-priority'>{item.priority}</span>
              <strong>{item.title}</strong>
              {item.reason && <p>{item.reason}</p>}
              <p className='advice-action'>{item.action}</p>
              {recommendation.requested && recommendation.items.length > 0 && <div className='advice-furniture-recommendations'>
                <div className='advice-furniture-recommendations__title'><ShoppingBag /><span>家具推荐</span></div>
                <div className='advice-furniture-recommendations__rail'>
                  {recommendation.items.map((furniture) => {
                    const saved = library.some((candidate) => candidate.id === furniture.id)
                    return <div className='advice-furniture-card' key={furniture.id}>
                      <img src={furniture.previewUrl} alt={`${furniture.name} 推荐图`} loading='lazy' />
                      <span><strong>{furniture.name}</strong><small>{furniture.category} · GLB</small></span>
                      <button type='button' disabled={saved} onClick={() => {
                        addFurnitureToLibrary(furniture)
                        toast.show(`${furniture.name} 已加入家具库`)
                      }}>{saved ? <Check /> : <Plus />}{saved ? '已加入' : '加入'}</button>
                    </div>
                  })}
                </div>
              </div>}
              {recommendation.requested && !recommendation.items.length && <p className='advice-commerce-fallback'><ShoppingBag />家具库暂未找到合适款式，后续可以在抖音商城进行选购。</p>}
            </article>
          })}
          {!!advice.missingFields.length && <div className='missing-data'><strong>仍缺少的信息</strong>{advice.missingFields.map((item) => <span key={item}>{item}</span>)}</div>}
        </section>}
        <Link className='editor-complete' to='/complete'>完成当前方案</Link>
      </aside>
    </main>
  </div>
}
