// ============================================================
// 数据模型（PRD 第 4 节，严格照建；禁止 any）
// ============================================================

export type ID = string

export type Direction = 'pet' | 'baby' | 'flow' | 'fengshui' | 'color' | string

export interface User {
  unionId: ID // 主键，跨端身份
  nickname?: string
  avatar?: string
}

export interface Furniture {
  // 全局家具 SKU 库
  id: ID
  category: string // 沙发/床/桌...
  title: string
  coverUrl: string
  modelUrl?: string // 3D 模型（本轮可空）
  priceRefs: PriceRef[] // 渠道链接（现仅用于「直达抖音商城」外跳，比价 UI 已下线）
  description?: string // 单品描述（详情页正文，视频复现）
  images?: string[] // 详情页轮播图（空则用 coverUrl 单张）
  colors?: ColorOption[] // 可选颜色（详情页色卡）
  materials?: MaterialOption[] // 可选材质（详情页材质卡）
}
export interface PriceRef {
  channel: string
  price: number
  url: string
}

// 详情页「颜色」色卡（视频复现：一排圆形色块，可选）
export interface ColorOption {
  name: string // 颜色名，如 深绿 / 焦糖棕
  hex: string // 色值，如 #4a5d3a
}

// 详情页「材质」色卡（视频复现：一排圆形材质块，可选）
export interface MaterialOption {
  name: string // 材质名，如 头层牛皮 / 磨砂绒
  thumb?: string // 材质贴图（本轮可空，用色块兜底）
  hex?: string // 兜底色（无贴图时显示）
}

// 场景/方案详情（MVP 四场景：养宠/养娃/风水/动线，结合具体场景需求做改造）
export interface Scene {
  id: ID
  title: string // 如 养宠空间
  direction: string // 对应改造方向：养宠 / 养娃 / 风水 / 动线
  coverUrl: string // 场景大图
  description?: string // 场景需求解读
  points: string[] // 改造要点（按序陈列）
  items: SceneItem[] // 家具元素列表
}

export interface SceneItem {
  furnitureId: ID // 关联 Furniture.id
  note?: string // 该家具在此场景里的一句说明
}

export interface Asset {
  // 用户识别的一件家具实例（资产随人走的载体）
  id: ID
  ownerId: ID // = User.unionId
  furnitureId: ID
  source: 'A_upload' | 'B_link' // 入口A 还是 入口B
  sourceRefId?: string // 入口B 的 sourceId
  status: 'recognized' | 'placed' // 下单已随比价线下线，终态 = placed
  createdAt: number
}

export interface Home {
  // 一套房子
  id: ID
  ownerId: ID
  type: 'new' | 'old' | 'template' // 决定三入口分叉
  name: string
  layoutModelUrl?: string
  isPrimary: boolean
}

export interface RoomParams {
  usableArea?: number
  floorHeight?: number
  slabThickness?: number
  wallOpacity?: number
  slabOpacity?: number
  showBaseImage?: boolean
}

export interface Room {
  id: ID
  homeId: ID
  name: string // 客厅/卧室...
  bounds?: unknown // 户型边界，本轮可占位
  params?: RoomParams
}

export interface Placement {
  // 某 Asset 摆在某 Room 的坐标
  id: ID
  roomId: ID
  assetId: ID
  transform: { x: number; y: number; rotate: number; scale: number }
  isExisting: boolean // true=旧房预置的现有家具（可被移除/替换）
}

export interface ProfileSignal {
  // 行为信号事件流，append-only，只 insert 不 update
  id: ID
  userId: ID
  type: 'view_fengshui' | 'fav_babybed' | 'view_pet_furniture' | string
  context?: Record<string, unknown>
  ts: number
}

export interface ProfileTag {
  // 画像标签推断缓存（本轮前端可只读展示）
  userId: ID
  tag: 'has_pet' | 'has_baby' | 'fengshui' | string
  confidence: number // 0~1
  inferredAt: number
}
