import {
  ArrowLeft,
  Check,
  ChevronDown,
  ChevronRight,
  Clipboard,
  FileImage,
  ImagePlus,
  Layers3,
  Link2,
  Move3D,
  Play,
  ScanLine,
  Search,
  Share2,
  Sparkles,
  UserRound,
  Users,
} from 'lucide-react'
import { useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import spaceImage from '@/assets/reference/space-3d-living.png'
import babyScene from '@/assets/reference/scenes/scene-baby.png'
import fengshuiScene from '@/assets/reference/scenes/scene-fengshui.png'
import flowScene from '@/assets/reference/scenes/scene-flow.png'
import petScene from '@/assets/reference/scenes/scene-pet.png'
import chairImage from '@/assets/reference/furniture/chair-01.jpg'
import lampImage from '@/assets/reference/furniture/lamp-01.jpg'
import sofaImage from '@/assets/reference/furniture/sofa-02.jpg'
import tableImage from '@/assets/reference/furniture/table-02.jpg'
import { useToast } from '@/components/ToastProvider'
import { useSceneStore } from '@/store'

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

const furniture = [
  { name: '亚麻休闲椅', category: '椅', image: chairImage },
  { name: '低矮模块沙发', category: '沙发', image: sofaImage },
  { name: '圆角原木边几', category: '桌', image: tableImage },
  { name: '暖光落地灯', category: '灯', image: lampImage },
]

export function HomePage() {
  const toast = useToast()
  return <div className='surface-page home-page'>
    <section className='page-intro'>
      <div><span className='eyebrow'>MY HOME</span><h1>我的家</h1><p>所有识别、试摆和空间建议，都沉淀在这里。</p></div>
      <div className='page-actions'>
        <button type='button' aria-label='邀请共建' onClick={() => toast.show('共建入口已准备好')}><Users /><span>共建</span></button>
        <button type='button' aria-label='分享方案' onClick={() => toast.show('分享入口已准备好')}><Share2 /><span>分享</span></button>
      </div>
    </section>

    <button className='home-switch' type='button' onClick={() => toast.show('当前演示户型：room6')}>
      <span><strong>法式复古之家</strong><small>样板 · 1 间房</small></span>
      <span>切换 <ChevronDown /></span>
    </button>

    <div className='room-pills'><button className='is-active' type='button'>客厅</button><button type='button' disabled>卧室</button><button type='button' disabled>书房</button></div>

    <Link className='home-canvas' to='/space?sceneId=room6'>
      <img src={spaceImage} alt='room6 客厅空间预览' />
      <span className='home-canvas__badge'>3D 空间</span>
      <span className='home-canvas__cta'><Move3D />进入摆放</span>
      <span className='home-canvas__meta'>6.0 × 4.2m · {useSceneStore.getState().snapshot?.objects.length ?? 0} 件家具</span>
    </Link>

    <div className='section-heading'><div><h2>家具库</h2><p>点击家具进入空间试摆</p></div><Link to='/recognize'>添加家具 <ChevronRight /></Link></div>
    <div className='furniture-rail'>
      {furniture.map((item) => <Link key={item.name} to='/space?sceneId=room6' className='furniture-tile'><img src={item.image} alt={item.name} /><strong>{item.name}</strong><small>{item.category}</small></Link>)}
    </div>
    <Link className='accent-cta' to='/suggest'><Sparkles />查看 AI 空间建议</Link>
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
        <Link className='is-primary' to={`/space?sceneId=room6&direction=${active.id}`}><Move3D />直接改</Link>
      </div>
    </section>
    <div className='section-heading'><div><h2>场景改造</h2><p>结合具体需求，整套思路给你</p></div></div>
    <div className='scene-grid'>
      {scenes.map((scene) => <Link to={`/scene/${scene.id}`} className='scene-card' key={scene.id}><img src={scene.image} alt={scene.name} /><div><span>{scene.tag}</span><h2>{scene.name}</h2><p>{scene.copy}</p></div></Link>)}
    </div>
  </div>
}

export function MePage() {
  const toast = useToast()
  const active = useSceneStore((s) => s.activeSceneId)
  const setActive = useSceneStore((s) => s.setActiveSceneId)
  const input = useRef<HTMLInputElement>(null)
  const acceptFile = () => {
    setActive('room6')
    toast.show('扫描素材已接收，演示模式已匹配 room6')
  }
  return <div className='surface-page profile-page'>
    <section className='profile-card'>
      <span className='profile-avatar'><UserRound /></span>
      <div><h1>空间体验官</h1><p>把喜欢的家，一件件变成现实。</p></div>
      <strong>12<small>空间资产</small></strong>
    </section>
    <div className='section-heading'><div><h2>开始建模</h2><p>选择一种方式创建空间或家具</p></div></div>
    <input ref={input} hidden type='file' accept='image/*,video/*' onChange={acceptFile} />
    <div className='entry-grid'>
      <button className='entry-card entry-card--dark' type='button' onClick={() => input.current?.click()}><ScanLine /><span><strong>立即扫描</strong><small>相机采集空间</small></span><ChevronRight /></button>
      <button className='entry-card' type='button' onClick={() => input.current?.click()}><FileImage /><span><strong>上传平面图</strong><small>创建空屋模型</small></span><ChevronRight /></button>
      <Link className='entry-card' to='/home'><Layers3 /><span><strong>选择模板空间</strong><small>从 room6 开始</small></span><ChevronRight /></Link>
      <Link className='entry-card entry-card--accent' to='/recognize'><Link2 /><span><strong>链接识别家具</strong><small>导入喜欢的单品</small></span><ChevronRight /></Link>
    </div>
    <section className='asset-summary'><div><span className='eyebrow'>CURRENT SPACE</span><h2>{active}</h2><p>6.0 × 4.2m · 可编辑快照</p></div><Link to='/space?sceneId=room6'>打开 <ChevronRight /></Link></section>
  </div>
}

export function ProductPage() {
  const { id } = useParams()
  return <div className='flow-page'><PageHeader title='单品详情' /><main className='detail-layout'><div className='detail-visual'><img src={chairImage} alt='识别家具' /></div><div><span className='eyebrow'>PRODUCT · {id}</span><h1>亚麻休闲椅</h1><p>柔和包裹感与低靠背比例适合客厅阅读角。这里继续承接现有商品、材质和尺寸信息接口。</p><div className='detail-specs'><span>亚麻</span><span>暖灰</span><span>78 × 74cm</span></div><Link className='primary-link' to='/space?sceneId=room6'><Move3D />放入 room6</Link></div></main></div>
}

export function ScenePage() {
  const { id } = useParams()
  const scene = scenes.find((item) => item.id === id) ?? scenes[0]
  return <div className='flow-page'><PageHeader title='场景详情' /><main className='detail-layout scene-detail'><div className='detail-visual'><img src={scene.image} alt={scene.name} /></div><div><span className='eyebrow'>SCENE DIRECTION · {scene.tag}</span><h1>{scene.name}</h1><p>{scene.copy}</p><div className='advice-list'><span><Check />释放主要通道，保留连续活动区</span><span><Check />家具边缘保持舒适通过距离</span><span><Check />用材质和照明降低空间噪声</span></div><Link className='primary-link' to={`/space?sceneId=room6&direction=${scene.id}`}><Sparkles />按此方向试改</Link></div></main></div>
}

export function RecognizePage() {
  const input = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()
  const [selected, setSelected] = useState(false)
  return <div className='flow-page'><PageHeader title='识别家具' /><main className='recognize-flow'><header><span className='eyebrow'>ADD FURNITURE</span><h1>把喜欢的家具<br />变成你的资产</h1><p>上传截图，或从 Feed 暂停识别。</p></header><input ref={input} hidden type='file' accept='image/*' onChange={() => setSelected(true)} />{!selected ? <div className='recognize-options'><button type='button' onClick={() => input.current?.click()}><ImagePlus /><span><strong>上传截图识别</strong><small>相册中的家具，AI 帮你找出来</small></span><ChevronRight /></button><button type='button' onClick={() => navigate('/')}><Play /><span><strong>从 Feed 暂停识别</strong><small>点击画面中的家具标签</small></span><ChevronRight /></button></div> : <section className='recognize-result'><img src={chairImage} alt='识别出的亚麻休闲椅' /><span className='recognize-result__check'><Check /></span><div><span className='eyebrow'>识别完成 · 92%</span><h2>亚麻休闲椅</h2><p>椅 · 暖灰色 · 已存入我的家</p></div><button type='button' className='secondary-button' onClick={() => input.current?.click()}>重新选择</button><button type='button' className='primary-button' onClick={() => navigate('/space?sceneId=room6')}><Move3D />放进 room6</button></section>}</main></div>
}

export function SuggestPage() {
  return <div className='flow-page'><PageHeader title='布局建议' /><main className='suggest-page'><header><span className='eyebrow'>AI SPACE ADVICE</span><h1>空间建议已整理</h1><p>主通道、尺寸适配和材质语义建议会继续由 3D 编辑器中的原有接口生成并应用。</p></header><div className='suggest-list'><article><span>01</span><div><h2>先留出连续通道</h2><p>沙发和边几之间保留舒适距离，减少进入客厅后的绕行。</p></div></article><article><span>02</span><div><h2>降低视觉重心</h2><p>把高柜靠墙组织，阅读灯靠近单椅形成独立功能角。</p></div></article><article><span>03</span><div><h2>统一材质语义</h2><p>保留原木与亚麻作为主材质，少量暖色金属作为强调。</p></div></article></div><Link className='accent-cta' to='/space?sceneId=room6'><Sparkles />回到空间应用建议</Link></main></div>
}

export function RecommendPage() {
  return <div className='flow-page'><PageHeader title='搜同款' /><main className='recommend-page'><header><span className='eyebrow'>MATCHED FOR ROOM6</span><h1>相似家具</h1><p>商品检索接口保持原位，这里以旧版的双列资产卡呈现。</p></header><div className='recommend-grid'>{furniture.slice(0, 3).map((item) => <article key={item.name}><img src={item.image} alt={item.name} /><div><span>{item.category}</span><strong>{item.name}</strong><small>适配 room6 尺寸</small><button type='button'>查看详情 <ChevronRight /></button></div></article>)}</div><Link className='secondary-link' to='/space?sceneId=room6'>返回空间</Link></main></div>
}

export function CompletePage() {
  return <div className='flow-page'><PageHeader title='方案完成' /><main className='complete-page'><span className='complete-mark'><Check /></span><span className='eyebrow'>SAVED TO MY HOME</span><h1>方案已保存</h1><p>家具坐标、尺寸、语义和墙体已写入 room6 SceneSnapshot。</p><div className='complete-preview'><img src={spaceImage} alt='已保存的 room6 空间' /><span><strong>法式复古客厅</strong><small>room6 · 实时快照</small></span></div><Link className='accent-cta' to='/home'>回到我的家</Link><Link className='secondary-link' to='/'>继续看灵感 Feed</Link></main></div>
}

export function DashboardPage() {
  const toast = useToast()
  return <div className='flow-page'><PageHeader title='开发看板' /><main className='dashboard'><h1>接口与演示入口</h1><div className='endpoint-list'>{['GET /api/room/snapshots/room6', 'PUT /api/room/snapshots/room6', 'PUT /api/room/snapshots/room6/whitebox', 'POST /api/room/room-layout', 'POST /api/feed/detect'].map((path) => <button type='button' key={path} onClick={() => navigator.clipboard?.writeText(path).then(() => toast.show('已复制接口')).catch(() => toast.show(path))}><Clipboard />{path}</button>)}</div><Link className='primary-link' to='/'><Play />开始演示</Link></main></div>
}
