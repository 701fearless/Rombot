# Kimi Code 开发任务书 · 家居 AI 小程序（前端）

> **给 Kimi Code 的说明**：本文档是一份完整的前端开发任务书。技术栈、页面结构、组件规格、数据契约、状态机、验收标准均已在下方定义清楚，请严格遵循。
> 文档中所有以 `🟡【待填写】` 标记的区块，是产品负责人已填入的视觉/品牌决策，请把它们当作**强约束**执行（若某处仍为空，说明该项尚未定稿，请用"占位中性风格"实现并在代码注释标注 `// TODO: 待视觉稿确认`）。
>
> **本轮目标**：交付一个可跑通核心闭环的**高保真前端骨架**（数据用 Mock，接口按契约预留），不接真实后端。

---

## 0. 产品一句话背景

一个"抖音刷到家具 → 识别 → 放进我家 → AI 出整屋方案 → 比价下单"的家居 AI 小程序。
核心架构是**双中心循环**：左中心「发现 Feed」负责获客，右中心「我的家」负责留存。所有能力都是连接两中心的全屏动作流，用完即退回 Tab。

**三条已锁定的架构决策（不可推翻）：**
1. **双入口**：入口A=截图/相册上传识别；入口B=抖音挂车/评论链接带 `sourceId` 跳转。均落在小程序内。
2. **「我的家」是首页级常驻 Tab**，是所有动作流产物的沉淀地，跨会话持久。
3. **渐进式行为画像**：不填问卷，靠行为埋点（`ProfileSignal`）反推标签，仅在模糊时轻确认。

---

## 1. 技术栈（强制，不要替换）

| 维度 | 选型 | 说明 |
|------|------|------|
| 框架 | **Taro 4 + React 18** | 一套代码编译到微信小程序 + 抖音小程序 |
| 语言 | **TypeScript（strict 模式）** | 全项目禁用 `any`，数据模型必须有完整类型 |
| 状态管理 | **Zustand** | 「我的家」资产池 = 全局 store；动作流内部状态用局部 state |
| 样式 | **SCSS + CSS Variables（Design Token）** | Token 集中在 `src/styles/tokens.scss`（色板/圆角/字体），特效在 `src/styles/effects.scss`（liquid-glass/动效）；禁止硬编码色值/间距 |
| UI 组件库 | **NutUI-React-Taro** | 基础组件（按钮、输入、弹窗、骨架屏）优先用它，业务组件自研 |
| 3D/摆放 | **P0 先用 2D 俯视图 + 家具贴图拖拽占位** | Three.js 3D 留到后续；本轮不做真 3D |
| 图片 | **WebP + 懒加载 + 骨架屏** | 禁止白屏 |
| 代码规范 | ESLint + Prettier | 提交前必须无 lint error |

---

## 2. 视觉与品牌规范（已定稿，Kimi 严格执行）

> 本节已由产品负责人定稿。Kimi 请把 2.2–2.4 写进 `src/styles/tokens.scss` 与 `src/styles/effects.scss` 并全局套用；整体气质以 2.1 为准。**不要引入任何装饰性色块、径向渐变、发光光晕**——深度全部由光影浮雕与真实内容（图片/视频）提供。

### 2.1 整体视觉风格（定稿）
**关键词：浮雕（Neumorphism / soft emboss）· 光影 · 莫兰蒂色系。**
- 气质：复古、法式、油画质感的静谧高级感。低饱和、灰调、柔和。
- 卡片/按钮走**柔和浮雕**：靠一明一暗双向阴影塑造凹凸，而非重描边、重投影。
- 布局极简、电影感、竖向居中的 Hero；留白充足；**禁止**装饰性 blob、径向渐变、叠加光效。

### 2.2 主色板（Design Token · 定稿）

| 语义 | 变量 | 色值 |
|------|------|------|
| 主色（RED BUD） | `--color-primary` | `#962D49` |
| 主色-浅（MAUVEGLOW） | `--color-primary-light` | `#D18489` |
| 强调/CTA（RED BUD） | `--color-accent` | `#962D49` |
| 背景（WINTER WHITE） | `--color-bg-primary` | `#F5ECD2` |
| 背景-次级 | `--color-bg-secondary` | `#ECE0C2` |
| 正文文字 | `--color-text-primary` | `#332E28` |
| 次要文字 | `--color-text-secondary` | `#756C60` |
| 边框/分割线 | `--color-border` | `#D9CAA9` |
| 成功 | `--color-success` | `#71856A` |
| 警告 | `--color-warning` | `#B58A52` |
| 错误 | `--color-error` | `#9B5C55` |

### 2.3 圆角 / 字体 / 品牌资产（定稿）
- 卡片圆角：**16px**（`--radius-card`）；按钮圆角：**6px**（`--radius-btn`）。
- 主字体：**英文/数字 `Cormorant Garamond`，中文 `Noto Serif SC`（宋体族）**；`font-family` 兜底系统衬线。标题尤其用衬线以强化法式复古气质。
- Logo / 品牌插画风格：复古、法式、油画风。
- 深色模式：本轮**暂不需要**（Token 结构预留，但不实现切换）。

### 2.4 关键动效与特效（定稿，附实现代码）

**① Liquid Glass Effect** —— AI 生成瞬间 / 浮层容器使用，写进 `effects.scss`，class 名 `.liquid-glass`：

```scss
.liquid-glass {
  background: rgba(255, 255, 255, 0.01);
  background-blend-mode: luminosity;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  border: none;
  box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.1);
  position: relative;
  overflow: hidden;
}
.liquid-glass::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 1.4px;
  background: linear-gradient(180deg,
    rgba(255,255,255,0.45) 0%, rgba(255,255,255,0.15) 20%,
    rgba(255,255,255,0) 40%, rgba(255,255,255,0) 60%,
    rgba(255,255,255,0.15) 80%, rgba(255,255,255,0.45) 100%);
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}
```
> ⚠️ Taro/小程序注意：`backdrop-filter` 与伪元素 `::before` 在部分小程序基础库支持不全。请做**渐进增强**——不支持时降级为半透明莫兰蒂底 + 1px 内高光（`box-shadow: inset 0 1px 1px rgba(255,255,255,.1)`），视觉不塌。H5/Web 端保留完整效果。

**② 入场动效** —— 写进 `effects.scss`：

```scss
@keyframes fade-rise {
  from { opacity: 0; transform: translateY(24px); }
  to   { opacity: 1; transform: translateY(0); }
}
.animate-fade-rise         { animation: fade-rise .8s ease-out both; }
.animate-fade-rise-delay   { animation: fade-rise .8s ease-out .2s both; }
.animate-fade-rise-delay-2 { animation: fade-rise .8s ease-out .4s both; }
```
应用规则：**Hero H1 → `.animate-fade-rise`；副文案 → `.animate-fade-rise-delay`；Hero CTA 按钮 → `.animate-fade-rise-delay-2`**（形成 0 / .2s / .4s 的递进入场）。
> 无障碍：包一层 `@media (prefers-reduced-motion: reduce) { * { animation: none !important; } }`，尊重减弱动效偏好。

**③ 家具拖拽**：**要**吸附对齐 + 拖拽阴影（拖起时元素抬升投影，靠近网格/邻近家具边缘时吸附对齐并给轻反馈）。

**④ 入口B「资产飞入我的家」过渡动画**：**不要**（直接落库 + 轻提示即可，不做飞入动画）。

**Hero 布局定稿**：极简、电影感、竖向居中；无装饰 blob / 径向渐变 / 叠加层；视觉深度由背景图/视频本身提供。

---

## 3. 信息架构（页面结构，强制遵循）

### 3.1 底部导航 —— 固定 4 个 Tab，禁止增减

| Tab | 名称 | 路由 | 定位 |
|-----|------|------|------|
| 1 | 发现 | `/pages/discover/index` | 内容 Feed（瀑布流），获客钩子 |
| 2 | 改造 | `/pages/remodel/index` | 三入口建房/选房 |
| 3 | **我的家** | `/pages/myhome/index` | 常驻资产池，留存核心 |
| 4 | 我的 | `/pages/mine/index` | 订单/比价记录/设置 |

### 3.2 页面树

```
Tab1 发现
├── 家具/案例瀑布流
└── 单品详情页 ──[放进我家]──> 唤起【识别流】
Tab2 改造
├── 入口选择页（新房A / 旧房B / 模板C）
└── 户型确认页 ──> 唤起【摆放/替换流】
Tab3 我的家
├── 房屋列表（Home 卡片）
├── 房间视图（Room + 家具 Placement，2D 俯视占位）
└── 方案/收藏清单（Scheme）
Tab4 我的
├── 订单/比价记录
└── 设置
```

### 3.3 全屏动作流（覆盖式打开，退出回原 Tab，不占底部导航）

| 动作流 | 页面路由 | 触发点 | 产物落库 |
|--------|---------|--------|---------|
| 识别流 | `/pages/flow/recognize` | 双入口 / 单品"放进我家" | Asset（★锚点1） |
| 摆放/替换流 | `/pages/flow/place` | 户型确认后 / 点房间 | Placement |
| AI 建议流 | `/pages/flow/suggest` | 房间视图内 | 建议列表（通用→场景化降级） |
| 整屋补全流 | `/pages/flow/complete` | 单品摆放后"配齐整屋" | 批量 Placement |
| 比价/下单流 | `/pages/flow/order` | 方案确认 / 单品 | Order |

> **铁律**：任何动作流的产物都必须写入 Tab3「我的家」对应的 Zustand store 并持久化到 Storage。用户中途退出，资产不许丢。

---

## 4. 数据模型（TypeScript 类型定义，直接照建）

> 本轮无真实后端，请在 `src/mock/` 下用这些类型造 Mock 数据；接口调用统一走 `src/services/`，函数签名按契约留好，内部先返回 Mock。

```typescript
// src/types/models.ts

type ID = string;

interface User {
  unionId: ID;          // 主键，跨端身份
  nickname?: string;
  avatar?: string;
}

interface Furniture {          // 全局家具 SKU 库
  id: ID;
  category: string;            // 沙发/床/桌...
  title: string;
  coverUrl: string;
  modelUrl?: string;           // 3D 模型（本轮可空）
  priceRefs: PriceRef[];       // 多渠道比价
}
interface PriceRef { channel: string; price: number; url: string; }

interface Asset {              // 用户识别的一件家具实例（资产随人走的载体）
  id: ID;
  ownerId: ID;                 // = User.unionId
  furnitureId: ID;
  source: 'A_upload' | 'B_link';   // 入口A 还是 入口B
  sourceRefId?: string;        // 入口B 的 sourceId
  status: 'recognized' | 'placed' | 'ordered';
  createdAt: number;
}

interface Home {               // 一套房子
  id: ID;
  ownerId: ID;
  type: 'new' | 'old' | 'template';  // 决定三入口分叉
  name: string;
  layoutModelUrl?: string;
  isPrimary: boolean;
}

interface Room {
  id: ID;
  homeId: ID;
  name: string;                // 客厅/卧室...
  bounds?: unknown;            // 户型边界，本轮可占位
}

interface Placement {          // 某 Asset 摆在某 Room 的坐标
  id: ID;
  roomId: ID;
  assetId: ID;
  transform: { x: number; y: number; rotate: number; scale: number };
  isExisting: boolean;         // true=旧房预置的现有家具（可被移除/替换）
}

interface Scheme {             // 方案快照，可复访对比
  id: ID;
  homeId: ID;
  title: string;
  savedAt: number;
  placementSnapshot: Placement[];
}

interface ProfileSignal {      // 行为信号事件流，append-only，只 insert 不 update
  id: ID;
  userId: ID;
  type: 'view_fengshui' | 'fav_babybed' | 'view_pet_furniture' | string;
  context?: Record<string, unknown>;
  ts: number;
}

interface ProfileTag {         // 画像标签推断缓存（本轮前端可只读展示）
  userId: ID;
  tag: 'has_pet' | 'has_baby' | 'fengshui' | string;
  confidence: number;          // 0~1
  inferredAt: number;
}

interface Order {
  id: ID;
  userId: ID;
  assetId: ID;
  price: number;
  status: 'pending' | 'paid' | 'canceled';
}
```

**三个必须理解的设计意图（照此实现，别自作主张改）：**
1. `Asset` 一经识别立即落库并绑 `ownerId`，这是"资产随人走"的物理载体，**不靠页面传参**，靠 store + Storage。
2. 旧房场景 = 该 Home 的 Room 初始化时预置若干 `isExisting=true` 的 Placement；"移除旧家具"操作 = 删这些 Placement。
3. `ProfileSignal` **只 insert 不 update**；本轮前端只需在指定行为点埋点写入（见第 6 节），不做推断。

---

## 5. 关键状态机（照此实现流程控制）

### 5.1 主链路：双入口 → 识别 → 三入口分叉 → 沉淀

```
入口A(截图上传) ┐
入口B(带 sourceId) ┘→ 识别流(抠图匹配, 展示识别中动效)
   → ★锚点1: Asset 落库(绑 unionId, 此后退出不丢)
        └─识别置信度低 → 兜底:给通用家具模板, 永不空结果
   → 按 Home.type 分叉进入摆放流:
        A new  → 空屋, 从零摆放(无 isExisting)
        B old  → 现房, 首屏突出"移除/替换旧家具"(预置 isExisting=true)
        C tmpl → 样板间, 预置成套 Placement, 首屏突出"换风格/换单品"
   → 摆放/替换流 → 可触发"配齐整屋"(整屋补全流)
   → ★锚点2: Scheme 落库(方案快照, 可复访)
   → 沉淀进 Tab3「我的家」
        └→ 比价/下单流 → 生成 Order
```

> **两个落库锚点是防丢命脉**：过锚点1，退出不丢资产；过锚点2，方案可复访。请在这两处务必写入 store + Storage。

### 5.2 三入口首屏 CTA 分叉（断点3 的落地，必须做出区别）

| Home.type | 首屏主 CTA | 次要操作 |
|-----------|-----------|---------|
| new 新房 | 「开始摆放」 | 从发现页选家具 |
| old 旧房 | **「移除/替换旧家具」** | 保留部分旧物 |
| template 模板 | 「换风格 / 换单品」 | 微调布局 |

---

## 6. 埋点要求（P0 只埋不用，别省略）

在以下用户行为发生时，调用 `logSignal(type, context)` 写入一条 `ProfileSignal`（本轮存本地 Storage 即可，为将来画像推断攒数据）：

| 行为 | signal type |
|------|-------------|
| 点开"风水"类 AI 建议 | `view_fengshui` |
| 收藏婴儿床/儿童家具 | `fav_babybed` |
| 反复浏览宠物家具（≥3次） | `view_pet_furniture` |
| 浏览某品类家具 | `view_category` (context 带 category) |

---

## 7. 性能与无障碍底线（硬要求，验收会查）

- 首屏可交互 < 3s（3G），图片全部 WebP + 懒加载。
- 家具贴图/资源懒加载 + **骨架屏**，任何异步区域禁止白屏。
- 关键 CTA（比价/下单）对比度 ≥ WCAG AA 4.5:1。
- 所有可点区域 ≥ 44×44px。
- 列表长时用虚拟滚动（NutUI VirtualList 或自研）。

---

## 8. 交付物与验收标准

### 8.1 交付物
- 完整 Taro + React + TS 项目，`pnpm dev:weapp` 可在微信开发者工具跑起来。
- `src/styles/tokens.scss`（套用第 2 节视觉规范）。
- 4 个 Tab 页 + 5 个动作流页，全部可点通、可跳转。
- `src/store/`（Zustand，含「我的家」资产池 + Storage 持久化）。
- `src/mock/` + `src/services/`（Mock 数据 + 按契约留好的接口函数）。
- `src/types/models.ts`（第 4 节类型）。

### 8.2 验收清单（逐条自测）
- [ ] 4 个 Tab 切换正常，「我的家」为第 3 个。
- [ ] 入口A（上传图）和入口B（模拟带 sourceId 进入）都能走通识别流。
- [ ] 识别完成后 Asset 落 store，**杀掉小程序重进，资产仍在**（Storage 持久化生效）。
- [ ] 三入口（new/old/template）进入后**首屏 CTA 明显不同**（见 5.2）。
- [ ] 旧房场景能看到预置的 `isExisting` 家具，且能"移除"。
- [ ] AI 建议流：识别失败时**有兜底模板，不出空白页**。
- [ ] 完成一个方案能保存为 Scheme，回「我的家」能再次打开。
- [ ] 指定 4 类行为触发时，Storage 里能查到对应 ProfileSignal 记录。
- [ ] 所有列表/图片区域有骨架屏，无白屏闪烁。
- [ ] `pnpm lint` 无 error，TS 无 `any`。
- [ ] 全局套用第 2 节莫兰蒂 Token，**无任何硬编码色值**；卡片/按钮为柔和浮雕，非重描边。
- [ ] Hero 三级入场动效生效（H1 / 副文案 / CTA 依次 0/.2/.4s）；开启系统"减弱动效"时动画关闭。
- [ ] `.liquid-glass` 在 H5 生效；小程序不支持时**优雅降级不塌**。
- [ ] 家具拖拽有抬升阴影 + 吸附对齐；入口B 落库为**无飞入动画**的轻提示。

---

## 9. 建议的开发顺序（P0 优先）

1. **P0** 项目脚手架 + tokens.scss + 4 Tab 框架 + Zustand store + Storage 持久化。
2. **P0** 识别流（双入口汇入）+ Asset 落库（锚点1）+「我的家」展示资产。
3. **P1** 三入口分叉（Home.type + isExisting 预置）+ 摆放/替换流（2D 拖拽占位）。
4. **P1** AI 建议流（通用→场景化降级 + 兜底模板）。
5. **P2** 整屋补全流 + 比价下单流 + Order。
6. **全程** 在第 6 节的行为点埋 ProfileSignal（只埋不用）。

---

**文档版本**：v1.0
**承接**：《用户体验架构评审.md》《开发对照规格_信息架构与数据模型.md》
**前端工程师**：FrontendDeveloper
**日期**：2026-07-23

> 📌 **给产品负责人（你）的提醒**：交给 Kimi Code 前，请务必填写第 2 节（🟡 区块）。第 2 节是唯一留给你的"品味决策区"，其余全部已定稿。填完即可整份丢给 Kimi。
