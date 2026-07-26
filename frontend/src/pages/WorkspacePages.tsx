import {
  ArrowLeft,
  Bookmark,
  Box,
  Check,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Clipboard,
  ImagePlus,
  Move3D,
  Play,
  Search,
  Share2,
  Sparkles,
  Trash2,
  UserRound,
  Users,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import douyinEntryImage from '@/assets/reference/douyin-entry.png'
import heroRoomImage from '@/assets/reference/hero-room.jpg'
import spaceImage from '@/assets/reference/space-3d-living.png'
import babyScene from '@/assets/reference/scenes/scene-baby.png'
import fengshuiScene from '@/assets/reference/scenes/scene-fengshui.png'
import flowScene from '@/assets/reference/scenes/scene-flow.png'
import petScene from '@/assets/reference/scenes/scene-pet.png'
import chairImage from '@/assets/reference/furniture/chair-01.jpg'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { FurnitureModelCarousel } from '@/components/FurnitureModelCarousel'
import { useToast } from '@/components/ToastProvider'
import { listGeneratedFurniture } from '@/services/backend'
import { useSceneStore } from '@/store'
import type { GeneratedFurniture } from '@/types/scene'

function PageHeader({ title }: { title: string }) {
  const navigate = useNavigate()
  return <header className='flow-header'>
    <button type='button' onClick={() => navigate(-1)} aria-label='返回'><ArrowLeft /></button>
    <strong>{title}</strong>
    <Link to='/'>QQ House</Link>
  </header>
}

const scenes = [
  { id: 'pet', name: '养宠友好', copy: '给毛孩子留活动区与专属收纳，动线避开食盆水碗。', image: petScene, tag: '养宠' },
  { id: 'baby', name: '亲子成长', copy: '圆角防护、视线通透，留出亲子活动与爬行空间。', image: babyScene, tag: '养娃' },
  { id: 'flow', name: '顺畅动线', copy: '梳理行走路径，减少绕行与容易磕碰的位置。', image: flowScene, tag: '动线' },
  { id: 'fengshui', name: '安居风水', copy: '床位朝向、门窗关系与空间留白一并调整。', image: fengshuiScene, tag: '风水' },
]

const homeLayouts = [
  { id: 'room1', name: 'room1 全屋空间', description: '明亮客餐厅 · 家具已匹配' },
  { id: 'room2', name: 'room2 全屋空间', description: '纵深复合户型 · 家具已匹配' },
] as const

export function HomePage() {
  const toast = useToast()
  const library = useSceneStore((state) => state.furnitureLibrary)
  const removeFurniture = useSceneStore((state) => state.removeFurnitureFromLibrary)
  const activeSceneId = useSceneStore((state) => state.activeSceneId)
  const setActiveSceneId = useSceneStore((state) => state.setActiveSceneId)
  const [layoutPickerOpen, setLayoutPickerOpen] = useState(false)
  const [pendingDelete, setPendingDelete] = useState<GeneratedFurniture | null>(null)
  const activeLayout = homeLayouts.find((layout) => layout.id === activeSceneId) ?? homeLayouts[0]
  return <div className='surface-page home-page'>
    <section className='page-intro'>
      <div><span className='eyebrow'>MY HOME</span><h1>我的家</h1></div>
      <div className='page-actions'>
        <button type='button' aria-label='邀请共建' onClick={() => toast.show('共建入口已准备好')}><Users /><span>共建</span></button>
        <button type='button' aria-label='分享方案' onClick={() => toast.show('分享入口已准备好')}><Share2 /><span>分享</span></button>
      </div>
    </section>

    <div className={`home-layout-picker ${layoutPickerOpen ? 'is-open' : ''}`}>
      <button
        className='home-switch'
        type='button'
        aria-expanded={layoutPickerOpen}
        aria-controls='home-layout-options'
        onClick={() => setLayoutPickerOpen((open) => !open)}
      >
        <span><strong>{activeLayout.name}</strong><small>{activeLayout.description}</small></span>
        <span>选择户型 {layoutPickerOpen ? <ChevronUp /> : <ChevronDown />}</span>
      </button>
      {layoutPickerOpen && <div className='home-layout-options' id='home-layout-options' role='listbox' aria-label='选择户型'>
        {homeLayouts.map((layout) => <button
          className={layout.id === activeSceneId ? 'is-active' : ''}
          type='button'
          role='option'
          aria-selected={layout.id === activeSceneId}
          key={layout.id}
          onClick={() => {
            setActiveSceneId(layout.id)
            setLayoutPickerOpen(false)
            toast.show(`已切换到 ${layout.name}`)
          }}
        >
          <span><strong>{layout.name}</strong><small>{layout.description}</small></span>
          {layout.id === activeSceneId && <Check aria-hidden='true' />}
        </button>)}
      </div>}
    </div>

    <Link className='home-canvas' to={`/space?sceneId=${activeSceneId}`}>
      <img src={spaceImage} alt={`${activeSceneId} 全屋空间预览`} />
      <span className='home-canvas__badge'>3D 空间</span>
      <span className='home-canvas__cta'><Move3D />进入摆放</span>
      <span className='home-canvas__meta'>6.0 × 4.2m · {useSceneStore.getState().snapshot?.objects.length ?? 0} 件家具</span>
    </Link>

    <div className='section-heading'><div><h2>家具库</h2><p>点击家具进入空间试摆</p></div><Link to='/recognize'>添加家具 <ChevronRight /></Link></div>
    {library.length ? <div className='furniture-rail'>
      {library.map((item) => <article className='furniture-tile-shell' key={item.id}>
        <Link to={`/product/${encodeURIComponent(item.id)}`} className='furniture-tile'><img src={item.previewUrl} alt={`${item.name} 生成参考图`} loading='lazy' /><strong>{item.name}</strong><small>{item.category}</small></Link>
        <button
          className='furniture-tile-delete'
          type='button'
          aria-label={`从家具库删除 ${item.name}`}
          onClick={() => setPendingDelete(item)}
        ><Trash2 /></button>
      </article>)}
    </div> : <Link className='library-empty' to='/'><Bookmark /><span><strong>家具库还是空的</strong><small>从灵感页收藏喜欢的模型</small></span><ChevronRight /></Link>}
    <Link className='accent-cta' to='/suggest'><Sparkles />查看 AI 空间建议</Link>
    <ConfirmDialog
      open={Boolean(pendingDelete)}
      title={`删除“${pendingDelete?.name ?? ''}”？`}
      description='删除后它会从家具库移除，但已经放进空间的家具实例不会受到影响。'
      onCancel={() => setPendingDelete(null)}
      onConfirm={() => {
        if (!pendingDelete) return
        removeFurniture(pendingDelete.id)
        toast.show(`${pendingDelete.name} 已从家具库删除`)
        setPendingDelete(null)
      }}
    />
  </div>
}

export function DiscoverPage() {
  const [direction, setDirection] = useState('养宠')
  const active = scenes.find((scene) => scene.tag === direction) ?? scenes[0]
  return <div className='surface-page discover-page'>
    <section className='page-intro'><div><span className='eyebrow'>DISCOVER</span><h1>发现</h1><p>选一个生活方向，建议、单品和改造一次给齐。</p></div></section>
    <section className='community-panel'>
      <div className='section-heading'><div><h2>其他人的家</h2><p>看看大家怎么把房间改舒服</p></div></div>
      <div className='community-mosaic'>
        {scenes.slice(0, 3).map((scene) => <Link to={`/scene/${scene.id}`} key={scene.id}><img src={scene.image} alt={scene.name} /><span><strong>{scene.name}</strong><small>{scene.tag} · 已试改</small></span></Link>)}
      </div>
    </section>
    <div className='direction-tabs' role='tablist' aria-label='生活方向'>
      {scenes.map((scene) => <button role='tab' aria-selected={direction === scene.tag} className={direction === scene.tag ? 'is-active' : ''} type='button' key={scene.id} onClick={() => setDirection(scene.tag)}>{scene.tag}</button>)}
    </div>
    <section className='direction-result'>
      <div><span className='eyebrow'>为你整理</span><h2>{active.name}</h2><p>{active.copy}</p></div>
      <img src={active.image} alt={active.name} />
      <div className='direction-actions'>
        <Link to={`/scene/${active.id}`}><Sparkles />看建议</Link>
        <Link to='/recommend'><Search />推单品</Link>
        <Link className='is-primary' to={`/space?direction=${active.id}`}><Move3D />直接改</Link>
      </div>
    </section>
  </div>
}

export function MePage() {
  const toast = useToast()
  const navigate = useNavigate()
  const activeSceneId = useSceneStore((s) => s.activeSceneId)
  const openSelectedRoom = () => {
    toast.show(`扫描建模完成，正在打开 ${activeSceneId}`)
    navigate(`/space?sceneId=${activeSceneId}`)
  }
  return <div className='surface-page profile-page'>
    <section className='profile-card'>
      <span className='profile-avatar'><UserRound /></span>
      <div><h1>空间体验官</h1><p>把喜欢的家，一件件变成现实。</p></div>
      <strong>12<small>空间资产</small></strong>
    </section>
    <Link className='profile-asset-heading' to='/home'>
      <strong>添加个人资产</strong>
      <span>房间、户型与心动单品都会收进这里</span>
      <ChevronRight />
    </Link>
    <div className='profile-entry-hero'>
      <button className='profile-entry profile-entry--scan' type='button' onClick={openSelectedRoom}>
        <img src={heroRoomImage} alt='复古房间扫描入口' />
        <span className='profile-entry__veil' />
        <span className='profile-entry__copy'><strong>拍一下房间，先把真实的家装进来。</strong><small>扫描我的房间</small></span>
      </button>
      <div className='profile-entry__row'>
        <button className='profile-entry profile-entry--floorplan' type='button' onClick={openSelectedRoom}>
          <span className='profile-entry__copy'><strong>已有户型图，从平面图直接建空间。</strong><small>上传平面图</small></span>
        </button>
        <Link className='profile-entry profile-entry--template' to={`/space?sceneId=${activeSceneId}`}>
          <span className='profile-entry__copy'><strong>先用相似模板，也能马上试摆。</strong><small>使用模板空间</small></span>
        </Link>
      </div>
      <Link className='profile-entry profile-entry--recognize' to='/recognize'>
        <img src={douyinEntryImage} alt='家居链接识别入口' />
        <span className='profile-entry__veil' />
        <span className='profile-entry__copy'><strong>刷到心动家具？一张截图就能放进家。</strong><small>识别心动家具</small></span>
      </Link>
    </div>
  </div>
}

export function ProductPage() {
  const { id } = useParams()
  const toast = useToast()
  const library = useSceneStore((state) => state.furnitureLibrary)
  const addFurniture = useSceneStore((state) => state.addFurnitureToLibrary)
  const [item, setItem] = useState<GeneratedFurniture | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let live = true
    listGeneratedFurniture()
      .then((catalog) => {
        if (live) setItem(catalog.find((candidate) => candidate.id === id) ?? null)
      })
      .finally(() => live && setLoading(false))
    return () => { live = false }
  }, [id])

  const saveToLibrary = () => {
    if (!item) return
    addFurniture(item)
    toast.show('已加入家具库')
  }

  if (loading) return <div className='flow-page'><PageHeader title='单品详情' /><main className='product-loading'><span className='spin' /><p>正在加载模型资料</p></main></div>
  if (!item) return <div className='flow-page'><PageHeader title='单品详情' /><main className='product-loading'><Box /><h1>模型不存在</h1><Link className='secondary-link' to='/'>返回灵感</Link></main></div>

  const dimensions = item.estimatedDimensions
  const saved = library.some((candidate) => candidate.id === item.id)
  return <div className='flow-page product-page'>
    <PageHeader title='单品详情' />
    <main className='product-detail'>
      <FurnitureModelCarousel item={item} />
      <section className='product-copy'>
        <span className='eyebrow'>{item.category.toUpperCase()} · VIDEO {item.videoId}</span>
        <h1>{item.name}</h1>
        <div className='detail-specs'>
          <span>{item.category}</span>
          <span>{(item.sizeBytes / 1024 / 1024).toFixed(1)} MB</span>
          {dimensions && <span>{dimensions.widthM.toFixed(2)} × {dimensions.depthM.toFixed(2)} × {dimensions.heightM.toFixed(2)}m</span>}
        </div>
        <button className={`primary-button product-place ${saved ? 'is-saved' : ''}`} type='button' onClick={saveToLibrary} disabled={saved}>{saved ? <Check /> : <Bookmark />}{saved ? '已加入家具库' : '收藏到家具库'}</button>
        {saved && <Link className='secondary-link product-library-link' to='/home'>查看家具库 <ChevronRight /></Link>}
      </section>
    </main>
  </div>
}

export function ScenePage() {
  const { id } = useParams()
  const scene = scenes.find((item) => item.id === id) ?? scenes[0]
  return <div className='flow-page'><PageHeader title='场景详情' /><main className='detail-layout scene-detail'><div className='detail-visual'><img src={scene.image} alt={scene.name} /></div><div><span className='eyebrow'>SCENE DIRECTION · {scene.tag}</span><h1>{scene.name}</h1><p>{scene.copy}</p><div className='advice-list'><span><Check />释放主要通道，保留连续活动区</span><span><Check />家具边缘保持舒适通过距离</span><span><Check />用材质和照明降低空间噪声</span></div><Link className='primary-link' to={`/space?direction=${scene.id}`}><Sparkles />按此方向试改</Link></div></main></div>
}

export function RecognizePage() {
  const input = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()
  const activeSceneId = useSceneStore((state) => state.activeSceneId)
  const [selected, setSelected] = useState(false)
  return <div className='flow-page'><PageHeader title='识别家具' /><main className='recognize-flow'><header><span className='eyebrow'>ADD FURNITURE</span><h1>把喜欢的家具<br />变成你的资产</h1><p>上传截图，或从 Feed 暂停识别。</p></header><input ref={input} hidden type='file' accept='image/*' onChange={() => setSelected(true)} />{!selected ? <div className='recognize-options'><button type='button' onClick={() => input.current?.click()}><ImagePlus /><span><strong>上传截图识别</strong><small>相册中的家具，AI 帮你找出来</small></span><ChevronRight /></button><button type='button' onClick={() => navigate('/')}><Play /><span><strong>从 Feed 暂停识别</strong><small>点击画面中的家具标签</small></span><ChevronRight /></button></div> : <section className='recognize-result'><img src={chairImage} alt='识别出的亚麻休闲椅' /><span className='recognize-result__check'><Check /></span><div><span className='eyebrow'>识别完成 · 92%</span><h2>亚麻休闲椅</h2><p>椅 · 暖灰色 · 已存入我的家</p></div><button type='button' className='secondary-button' onClick={() => input.current?.click()}>重新选择</button><button type='button' className='primary-button' onClick={() => navigate(`/space?sceneId=${activeSceneId}`)}><Move3D />放进 {activeSceneId}</button></section>}</main></div>
}

export function SuggestPage() {
  return <div className='flow-page'><PageHeader title='布局建议' /><main className='suggest-page'><header><span className='eyebrow'>AI SPACE ADVICE</span><h1>空间建议已整理</h1><p>主通道、尺寸适配和材质语义建议会继续由 3D 编辑器中的原有接口生成并应用。</p></header><div className='suggest-list'><article><span>01</span><div><h2>先留出连续通道</h2><p>沙发和边几之间保留舒适距离，减少进入客厅后的绕行。</p></div></article><article><span>02</span><div><h2>降低视觉重心</h2><p>把高柜靠墙组织，阅读灯靠近单椅形成独立功能角。</p></div></article><article><span>03</span><div><h2>统一材质语义</h2><p>保留原木与亚麻作为主材质，少量暖色金属作为强调。</p></div></article></div><Link className='accent-cta' to='/space'><Sparkles />回到空间</Link></main></div>
}

export function RecommendPage() {
  const activeSceneId = useSceneStore((state) => state.activeSceneId)
  return <div className='flow-page'><PageHeader title='搜同款' /><main className='recommend-page'><header><span className='eyebrow'>VISUAL SEARCH</span><h1>相似家具</h1><p>从 Feed 识别家具并选择一键室用后，将在灵感页查看模型并收藏到家具库。</p></header><div className='catalog-empty'><Move3D /><strong>前往灵感页查看建模家具</strong><p>这里不再展示写死的演示商品。</p></div><Link className='primary-link' to='/'>打开灵感页</Link><Link className='secondary-link' to={`/space?sceneId=${activeSceneId}`}>返回空间</Link></main></div>
}

export function CompletePage() {
  const activeSceneId = useSceneStore((state) => state.activeSceneId)
  return <div className='flow-page'><PageHeader title='方案完成' /><main className='complete-page'><span className='complete-mark'><Check /></span><span className='eyebrow'>SAVED TO MY HOME</span><h1>方案已保存</h1><p>家具坐标、尺寸、语义和墙体已写入 {activeSceneId} SceneSnapshot。</p><div className='complete-preview'><img src={spaceImage} alt={`已保存的 ${activeSceneId} 空间`} /><span><strong>法式复古客厅</strong><small>{activeSceneId} · 实时快照</small></span></div><Link className='accent-cta' to='/home'>回到我的家</Link><Link className='secondary-link' to='/'>继续看灵感 Feed</Link></main></div>
}

export function DashboardPage() {
  const toast = useToast()
  const activeSceneId = useSceneStore((state) => state.activeSceneId)
  return <div className='flow-page'><PageHeader title='开发看板' /><main className='dashboard'><h1>接口与演示入口</h1><div className='endpoint-list'>{[`GET /api/room/snapshots/${activeSceneId}`, `PUT /api/room/snapshots/${activeSceneId}`, `PUT /api/room/snapshots/${activeSceneId}/whitebox`, 'POST /api/room/room-layout', 'POST /api/feed/detect'].map((path) => <button type='button' key={path} onClick={() => navigator.clipboard?.writeText(path).then(() => toast.show('已复制接口')).catch(() => toast.show(path))}><Clipboard />{path}</button>)}</div><Link className='primary-link' to='/'><Play />开始演示</Link></main></div>
}
