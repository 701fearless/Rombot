// ============================================================
// Mock 数据（本轮无真实后端，全部走 src/services/ 返回）
// 图片资源暂缺：coverUrl 一律空串，由组件层做占位（骨架屏/色块）
// ============================================================

import type {
  Asset,
  Furniture,
  Home,
  ID,
  Placement,
  Room,
  Scene,
  User,
} from '@/types/models'
import { furnitureImages, sceneImages } from './images'

// ---------- AI 建议条目（PRD 无此模型，仅 mock/服务层使用，不进 models.ts） ----------
export interface SuggestionItem {
  id: ID
  roomType: string // 适用房间，如 客厅/卧室；'通用' 表示不限
  title: string
  content: string
  sceneTag?: 'fengshui' | 'baby' | 'pet' | 'move' // 场景化建议标记（对应画像标签）；通用建议无此字段
}

// ---------- 用户 ----------
export const mockUser: User = {
  unionId: 'u_mock_001', // 固定 mock 身份，跨端主键
  nickname: '复古爱好者',
  avatar: '',
}

// ---------- 家具 SKU 库（品类覆盖：沙发/床/桌/椅/柜/灯/婴儿床/宠物家具） ----------
export const mockFurniture: Furniture[] = [
  {
    id: 'f_sofa_01',
    category: '沙发',
    title: '法式天鹅绒三人沙发',
    coverUrl: '',
    description:
      '天鹅绒面料细腻挺括，高回弹海绵久坐不塌。低饱和复古色调，轻松撑起客厅的气场与温度。',
    colors: [
      { name: '勃艮第红', hex: '#962d49' },
      { name: '雾粉', hex: '#d18489' },
      { name: '燕麦米', hex: '#d8c8a8' },
      { name: '墨绿', hex: '#4a5d3a' },
    ],
    materials: [
      { name: '天鹅绒', hex: '#7a4a5a' },
      { name: '亚麻', hex: '#c8b898' },
      { name: '科技布', hex: '#9a8f80' },
    ],
    priceRefs: [
      { channel: '京东', price: 4299, url: '' },
      { channel: '天猫', price: 4199, url: '' },
      { channel: '抖音小店', price: 3999, url: '' },
    ],
  },
  {
    id: 'f_sofa_02',
    category: '沙发',
    title: '莫兰迪亚麻双人沙发',
    coverUrl: '',
    priceRefs: [
      { channel: '京东', price: 2899, url: '' },
      { channel: '天猫', price: 2799, url: '' },
    ],
  },
  {
    id: 'f_bed_01',
    category: '床',
    title: '复古实木雕花双人床',
    coverUrl: '',
    priceRefs: [
      { channel: '京东', price: 5699, url: '' },
      { channel: '天猫', price: 5499, url: '' },
      { channel: '抖音小店', price: 5299, url: '' },
    ],
  },
  {
    id: 'f_bed_02',
    category: '床',
    title: '法式软包布艺床',
    coverUrl: '',
    priceRefs: [
      { channel: '京东', price: 4599, url: '' },
      { channel: '天猫', price: 4399, url: '' },
    ],
  },
  {
    id: 'f_table_01',
    category: '桌',
    title: '做旧实木圆餐桌',
    coverUrl: '',
    priceRefs: [
      { channel: '京东', price: 1999, url: '' },
      { channel: '天猫', price: 1899, url: '' },
    ],
  },
  {
    id: 'f_table_02',
    category: '桌',
    title: '大理石台面边几',
    coverUrl: '',
    priceRefs: [
      { channel: '京东', price: 899, url: '' },
      { channel: '抖音小店', price: 799, url: '' },
    ],
  },
  {
    id: 'f_chair_01',
    category: '椅',
    title: '复古藤编餐椅',
    coverUrl: '',
    priceRefs: [
      { channel: '京东', price: 699, url: '' },
      { channel: '天猫', price: 659, url: '' },
    ],
  },
  {
    // 视频复现主样例：意式皮质单人沙发
    id: 'f_chair_02',
    category: '椅',
    title: '意式皮质单人沙发',
    coverUrl: '',
    description:
      '这款皮质沙发采用深绿沙发线条简约，遵循人体工学，贴合身体曲线，舒适自在。精选优质皮革面料，质感上乘，其简洁外观与沉稳色调，是意式简约舒适美学的体现。',
    colors: [
      { name: '深绿', hex: '#3f4a35' },
      { name: '焦糖棕', hex: '#8a5a34' },
      { name: '雾蓝', hex: '#7a8a99' },
      { name: '酒红', hex: '#7a3040' },
      { name: '驼色', hex: '#b8946f' },
    ],
    materials: [
      { name: '头层牛皮', hex: '#6b543e' },
      { name: '磨砂绒', hex: '#8a7f70' },
      { name: '布艺', hex: '#a89a86' },
    ],
    priceRefs: [
      { channel: '京东', price: 1599, url: '' },
      { channel: '天猫', price: 1499, url: '' },
      { channel: '抖音小店', price: 1399, url: '' },
    ],
  },
  {
    id: 'f_cabinet_01',
    category: '柜',
    title: '做旧五斗柜',
    coverUrl: '',
    priceRefs: [
      { channel: '京东', price: 2399, url: '' },
      { channel: '天猫', price: 2299, url: '' },
    ],
  },
  {
    id: 'f_cabinet_02',
    category: '柜',
    title: '实木开放式书柜',
    coverUrl: '',
    priceRefs: [
      { channel: '京东', price: 3299, url: '' },
      { channel: '天猫', price: 3199, url: '' },
    ],
  },
  {
    id: 'f_lamp_01',
    category: '灯',
    title: '黄铜复古落地灯',
    coverUrl: '',
    priceRefs: [
      { channel: '京东', price: 799, url: '' },
      { channel: '抖音小店', price: 729, url: '' },
    ],
  },
  {
    id: 'f_lamp_02',
    category: '灯',
    title: '手绘陶瓷台灯',
    coverUrl: '',
    priceRefs: [
      { channel: '天猫', price: 459, url: '' },
      { channel: '抖音小店', price: 399, url: '' },
    ],
  },
  // ---------- 各品类第 3 件（发现页品类模块：每品类 2-3 个 3D/AR 模板） ----------
  {
    id: 'f_sofa_03',
    category: '沙发',
    title: '意式极简模块沙发',
    coverUrl: '',
    priceRefs: [
      { channel: '京东', price: 3599, url: '' },
      { channel: '天猫', price: 3499, url: '' },
    ],
  },
  {
    id: 'f_bed_03',
    category: '床',
    title: '日式原木榻榻米床',
    coverUrl: '',
    priceRefs: [
      { channel: '京东', price: 3299, url: '' },
      { channel: '抖音小店', price: 3099, url: '' },
    ],
  },
  {
    id: 'f_table_03',
    category: '桌',
    title: '新中式胡桃木书桌',
    coverUrl: '',
    priceRefs: [
      { channel: '京东', price: 2599, url: '' },
      { channel: '天猫', price: 2499, url: '' },
    ],
  },
  {
    id: 'f_chair_03',
    category: '椅',
    title: '法式雕花扶手椅',
    coverUrl: '',
    priceRefs: [
      { channel: '天猫', price: 1299, url: '' },
      { channel: '抖音小店', price: 1199, url: '' },
    ],
  },
  {
    id: 'f_cabinet_03',
    category: '柜',
    title: '藤编门厅玄关柜',
    coverUrl: '',
    priceRefs: [
      { channel: '京东', price: 1799, url: '' },
      { channel: '天猫', price: 1699, url: '' },
    ],
  },
  {
    id: 'f_lamp_03',
    category: '灯',
    title: '极简蚕丝吊灯',
    coverUrl: '',
    priceRefs: [
      { channel: '京东', price: 999, url: '' },
      { channel: '抖音小店', price: 899, url: '' },
    ],
  },
  {
    // 埋点场景准备：收藏婴儿床 → fav_babybed
    id: 'f_babybed_01',
    category: '婴儿床',
    title: '实木可拼接婴儿床',
    coverUrl: '',
    priceRefs: [
      { channel: '京东', price: 1899, url: '' },
      { channel: '天猫', price: 1799, url: '' },
    ],
  },
  {
    // 埋点场景准备：反复浏览宠物家具 → view_pet_furniture
    id: 'f_pet_01',
    category: '宠物家具',
    title: '复古绒面宠物沙发窝',
    coverUrl: '',
    priceRefs: [
      { channel: '京东', price: 599, url: '' },
      { channel: '天猫', price: 549, url: '' },
    ],
  },
]

// ---------- 注入 AI 生成的 3D 物件图（接真实后端后由接口返回 coverUrl，删除此段） ----------
mockFurniture.forEach((f) => {
  f.coverUrl = furnitureImages[f.id] ?? ''
})

// ---------- 识别兜底模板（PRD 5.1：置信度低 → 通用家具模板，永不空结果） ----------
export const fallbackTemplateFurnitureId: ID = 'f_sofa_01'

// ---------- 房屋（new / old / template 各一，PRD 5.2 三入口分叉） ----------
export const mockHomes: Home[] = [
  { id: 'home_new', ownerId: mockUser.unionId, type: 'new', name: '新家', isPrimary: true },
  { id: 'home_old', ownerId: mockUser.unionId, type: 'old', name: '现在的家', isPrimary: false },
  {
    id: 'home_tmpl',
    ownerId: mockUser.unionId,
    type: 'template',
    name: '法式复古样板间',
    isPrimary: false,
  },
]

export const mockRooms: Room[] = [
  { id: 'r_new_living', homeId: 'home_new', name: '客厅' },
  { id: 'r_new_bedroom', homeId: 'home_new', name: '主卧' },
  { id: 'r_old_living', homeId: 'home_old', name: '客厅' },
  { id: 'r_old_bedroom', homeId: 'home_old', name: '卧室' },
  { id: 'r_tmpl_living', homeId: 'home_tmpl', name: '客厅' },
  { id: 'r_tmpl_bedroom', homeId: 'home_tmpl', name: '卧室' },
]

// ---------- 预置资产（旧房现有家具 + 样板间成套家具的载体） ----------
const NOW = 1735689600000 // 2025-01-01，固定时间戳保证 mock 稳定

export const mockAssets: Asset[] = [
  // 旧房预置（source 记为 A_upload 仅占位，语义上为"现有家具"）
  {
    id: 'a_old_1',
    ownerId: mockUser.unionId,
    furnitureId: 'f_sofa_02',
    source: 'A_upload',
    status: 'placed',
    createdAt: NOW,
  },
  {
    id: 'a_old_2',
    ownerId: mockUser.unionId,
    furnitureId: 'f_cabinet_01',
    source: 'A_upload',
    status: 'placed',
    createdAt: NOW,
  },
  {
    id: 'a_old_3',
    ownerId: mockUser.unionId,
    furnitureId: 'f_lamp_02',
    source: 'A_upload',
    status: 'placed',
    createdAt: NOW,
  },
  // 样板间成套预置
  {
    id: 'a_tmpl_1',
    ownerId: mockUser.unionId,
    furnitureId: 'f_sofa_01',
    source: 'A_upload',
    status: 'placed',
    createdAt: NOW,
  },
  {
    id: 'a_tmpl_2',
    ownerId: mockUser.unionId,
    furnitureId: 'f_table_02',
    source: 'A_upload',
    status: 'placed',
    createdAt: NOW,
  },
  {
    id: 'a_tmpl_3',
    ownerId: mockUser.unionId,
    furnitureId: 'f_lamp_01',
    source: 'A_upload',
    status: 'placed',
    createdAt: NOW,
  },
  {
    id: 'a_tmpl_4',
    ownerId: mockUser.unionId,
    furnitureId: 'f_bed_01',
    source: 'A_upload',
    status: 'placed',
    createdAt: NOW,
  },
]

// ---------- 预置 Placement ----------
export const mockPlacements: Placement[] = [
  // 旧房：预置 3 件 isExisting=true（PRD 4 设计意图 2，"移除旧家具"= 删这些 Placement）
  {
    id: 'p_old_1',
    roomId: 'r_old_living',
    assetId: 'a_old_1',
    transform: { x: 120, y: 180, rotate: 0, scale: 1 },
    isExisting: true,
  },
  {
    id: 'p_old_2',
    roomId: 'r_old_living',
    assetId: 'a_old_2',
    transform: { x: 320, y: 60, rotate: 0, scale: 1 },
    isExisting: true,
  },
  {
    id: 'p_old_3',
    roomId: 'r_old_bedroom',
    assetId: 'a_old_3',
    transform: { x: 60, y: 220, rotate: 0, scale: 1 },
    isExisting: true,
  },
  // 样板间：预置成套 Placement（isExisting=false，首屏突出"换风格/换单品"）
  {
    id: 'p_tmpl_1',
    roomId: 'r_tmpl_living',
    assetId: 'a_tmpl_1',
    transform: { x: 140, y: 160, rotate: 0, scale: 1 },
    isExisting: false,
  },
  {
    id: 'p_tmpl_2',
    roomId: 'r_tmpl_living',
    assetId: 'a_tmpl_2',
    transform: { x: 150, y: 300, rotate: 0, scale: 1 },
    isExisting: false,
  },
  {
    id: 'p_tmpl_3',
    roomId: 'r_tmpl_living',
    assetId: 'a_tmpl_3',
    transform: { x: 340, y: 80, rotate: 0, scale: 1 },
    isExisting: false,
  },
  {
    id: 'p_tmpl_4',
    roomId: 'r_tmpl_bedroom',
    assetId: 'a_tmpl_4',
    transform: { x: 100, y: 100, rotate: 0, scale: 1 },
    isExisting: false,
  },
]

// ---------- AI 建议（PRD 3.3：通用 → 场景化降级） ----------
export const genericSuggestions: SuggestionItem[] = [
  {
    id: 'sg_gen_1',
    roomType: '客厅',
    title: '留白与呼吸感',
    content: '沙发与茶几之间保留 40cm 以上的通道，让视觉与动线都有呼吸感。',
  },
  {
    id: 'sg_gen_2',
    roomType: '客厅',
    title: '主灯 + 点光源',
    content: '用落地灯/台灯做分层照明，暖光更贴合复古法式气质。',
  },
  {
    id: 'sg_gen_3',
    roomType: '卧室',
    title: '低饱和床品',
    content: '床品选择与莫兰迪色板同族的大地色系，避免高饱和撞色。',
  },
  {
    id: 'sg_gen_4',
    roomType: '通用',
    title: '同色系递进',
    content: '大件家具保持同色系明度递进，空间更静谧统一。',
  },
]

export const sceneSuggestions: SuggestionItem[] = [
  {
    // PRD 第 6 节埋点：点开此类建议 → view_fengshui
    id: 'sg_scene_fengshui',
    roomType: '卧室',
    title: '风水：床不正对门',
    content: '床头靠实墙、避免正对房门，传统上利于安稳入睡。',
    sceneTag: 'fengshui',
  },
  {
    id: 'sg_scene_fengshui_2',
    roomType: '客厅',
    title: '风水：财位留白',
    content: '进门对角线位置保持干净通透、不堆杂物，传统上视为聚财位。',
    sceneTag: 'fengshui',
  },
  {
    id: 'sg_scene_baby',
    roomType: '通用',
    title: '有娃家庭：圆角优先',
    content: '茶几与柜体优先选圆角款，婴儿床远离窗帘绳与电源。',
    sceneTag: 'baby',
  },
  {
    id: 'sg_scene_baby_2',
    roomType: '客厅',
    title: '有娃家庭：视线通透',
    content: '沙发朝向尽量覆盖活动区，抬眼就能看到孩子；高柜务必上墙固定。',
    sceneTag: 'baby',
  },
  {
    id: 'sg_scene_pet',
    roomType: '客厅',
    title: '有宠家庭：耐磨面料',
    content: '沙发选科技布/磨砂绒等耐抓耐磨面料，宠物窝放在通风角落。',
    sceneTag: 'pet',
  },
  {
    id: 'sg_scene_pet_2',
    roomType: '通用',
    title: '有宠家庭：食盆让开主动线',
    content: '食盆水碗放在厨房或阳台一角，避开沙发到门口的行走路线，减少打翻。',
    sceneTag: 'pet',
  },
  {
    id: 'sg_scene_move_1',
    roomType: '通用',
    title: '动线：主通道 ≥80cm',
    content: '门口到阳台/卧室的主通道保持 80cm 以上，边几角几不探头。',
    sceneTag: 'move',
  },
  {
    id: 'sg_scene_move_2',
    roomType: '客厅',
    title: '动线：少走回头路',
    content: '高频路径（沙发↔餐桌↔厨房）之间不放障碍物，减少绕行与磕碰点。',
    sceneTag: 'move',
  },
]

// ---------- 空间模板（发现页「空间模板」行：3D 生成的成套空间，不下挂具体家具品类） ----------
// tint = 封面占位底色，取值来自 tokens.scss 点缀色/主色-浅（此处为数据层，只能写色值）
export interface SpaceTemplate {
  id: ID
  title: string
  tint: string
}

export const mockSpaceTemplates: SpaceTemplate[] = [
  { id: 'tpl_french_living', title: '法式客厅', tint: '#fcceb4' }, // --color-pastel-peach
  { id: 'tpl_minimal_bedroom', title: '极简卧室', tint: '#f9f2ef' }, // --color-pastel-cream
  { id: 'tpl_chinese_study', title: '新中式书房', tint: '#23438b' }, // --color-primary-light
  { id: 'tpl_kids_room', title: '儿童房', tint: '#d2e0aa' }, //       --color-pastel-green
  { id: 'tpl_pet_space', title: '养宠空间', tint: '#eef5fd' }, //     --color-bg-secondary
  { id: 'tpl_euro_dining', title: '欧式餐厅', tint: '#abd7fb' }, //   --color-pastel-blue
]

// ---------- 场景/方案（MVP 四场景：养宠/养娃/风水/动线，结合具体场景需求做改造） ----------
export const mockScenes: Scene[] = [
  {
    id: 'scene_pet',
    title: '养宠空间',
    direction: '养宠',
    coverUrl: sceneImages.scene_pet,
    description:
      '毛孩子也是家庭成员：给它留专属活动区与收纳位，人的动线避开食盆水碗，面料经得起爪子和掉毛。',
    points: [
      '沙发旁留出宠物活动区，人宠互不干扰',
      '食盆水碗归置到角落，避开主动线',
      '面料选耐磨耐抓款，掉毛好打理',
    ],
    items: [
      { furnitureId: 'f_pet_01', note: '复古绒面宠物沙发窝，给毛孩子一个专属位。' },
      { furnitureId: 'f_sofa_02', note: '亚麻面料耐磨好打理，和人宠共处合拍。' },
      { furnitureId: 'f_cabinet_01', note: '五斗柜收宠物粮与玩具，客厅不乱。' },
    ],
  },
  {
    id: 'scene_baby',
    title: '养娃空间',
    direction: '养娃',
    coverUrl: sceneImages.scene_baby,
    description:
      '有娃之后，安全与视线是第一优先级：圆角防护、少尖角少绳线，留一块爬得开的亲子活动区。',
    points: [
      '茶几柜体优先圆角，尖角加防护',
      '沙发朝向覆盖活动区，抬眼可见',
      '留出整块爬行/玩耍空地',
    ],
    items: [
      { furnitureId: 'f_babybed_01', note: '实木可拼接婴儿床，远离窗帘绳与电源。' },
      { furnitureId: 'f_table_02', note: '大理石边几替换尖角茶几，降低磕碰风险。' },
      { furnitureId: 'f_sofa_02', note: '双人沙发居中，视线覆盖整个活动区。' },
    ],
  },
  {
    id: 'scene_fengshui',
    title: '风水布局',
    direction: '风水',
    coverUrl: sceneImages.scene_fengshui,
    description:
      '不问玄学问心安：床位朝向、门窗对冲、财位留白一次理顺，睡得好是最大的风水。',
    points: [
      '床头靠实墙，不正对房门',
      '镜不对床，门窗不对冲',
      '进门对角线财位留白不堆物',
    ],
    items: [
      { furnitureId: 'f_bed_02', note: '软包布艺床调转朝向，床头靠实墙。' },
      { furnitureId: 'f_lamp_02', note: '陶瓷台灯暖光助眠，替代直射顶灯。' },
      { furnitureId: 'f_cabinet_01', note: '斗柜移到财位一侧，收纳整齐不压财。' },
    ],
  },
  {
    id: 'scene_flow',
    title: '动线优化',
    direction: '动线',
    coverUrl: sceneImages.scene_flow,
    description:
      '每天走一百遍的路，值得顺一点：梳理主通道、减少绕行与磕碰，小户型也能走出大平层的顺。',
    points: [
      '主通道保持 80cm 以上不卡人',
      '高频路径不放障碍物，少绕行',
      '边角家具收进线内，不探头',
    ],
    items: [
      { furnitureId: 'f_sofa_01', note: '三人沙发贴墙定位，把通道让出来。' },
      { furnitureId: 'f_table_02', note: '边几收到沙发线内，不再绊腿。' },
      { furnitureId: 'f_lamp_01', note: '落地灯照亮转角，夜里不磕碰。' },
    ],
  },
]
