# 页面链路与 Tab 跳转总览（2026-07-25 v7）

> 供检查用。与代码一一对应，行内标注源文件。
> 本轮变更：设计页四端口垂直居中；桌面端预览限宽 430px 手机画幅（容器/tabbar/全屏浮层/胶囊全部对齐）；
> 色板补 Burgundy `#6D1E21`（次级行动 = 淡蓝底红字：共建/分享、链接识别）；CoverShelf 删「N 件」标注；
> iPhone 视口截图自查通过（`scripts/screenshot.cjs` 路由已更新为现行 5 页）。

## 一、底部 TabBar（4 个，从左到右）

| 顺序 | Tab 名 | 页面路径 | 页面内容 | 选中态图标 |
|---|---|---|---|---|
| 1 | **设计** | `pages/remodel/index` | SplashScan 开屏（仅首次）→ EntryHero 四端口（立即扫描 / 上传平面图 / 选择模板空间 / **粘贴抖音链接识别**），页面**垂直居中**，**仅此** | 蓝圆底 + 黄线条 |
| 2 | **我的家** | `pages/myhome/index` | 页首「共建/分享」→ 房屋选择条（一行收起，点「切换」**浮层下拉**选取）→ 房间 pills → **方形 3D 空间画布**（左下角宠物菜单：虚拟猫狗）→ 拖拽提示词 → **平铺横滑家具资产库**（架首「+」卡=抖音链接识别）→ **AI 建议（黄底蓝字整行）** → **空间资产库**（平铺横滑） | 同上 |
| 3 | **发现** | `pages/direction/index` | 方向 pills（养宠/养娃/风水/动线）→ 选中同页顺序展开 ①建议 → ②单品 → ③直接改 → 下方「场景改造」四场景卡 | 同上（魔杖图标） |
| 4 | **灵感** | `pages/discover/index` | **家具资产库**（品类筛选，点上即详情）→ 灵感 Feed | 同上 |

配置位置：`src/app.config.ts`（tabBar.list 与 pages 顺序一致）。

## 二、每个 Tab 内的点击跳转

### Tab1 设计（remodel）——纯入口
- **立即扫描** → `Taro.chooseImage(sourceType:['camera'])` 接相机，拍完 → `navigateTo /pages/flow/recognize/index`
- **上传平面图** → 底部动作层二选一：**选择照片**（相册）/ **拍照**（相机）→ 拿图后建 `type=new` 空屋 → `navigateTo /pages/flow/place/index?homeId=...`
- **选择模板空间** → `switchTab /pages/myhome/index`（空间资产库在我的家，滑选模板）
- **粘贴抖音链接识别** → `Taro.getClipboardData` 读剪贴板 → `navigateTo /pages/flow/recognize/index?sourceId=...`（入口B 直达识别；读不到剪贴板走模拟 sourceId）

### Tab2 我的家（myhome）
- **共建 / 分享** → toast 占位（与摆放页邀请/分享同语义，未接真实分享卡）
- **房屋选择条** → 页内浮层下拉展开/收起（绝对定位覆盖内容上方，不挤压下方画布；无跳转）
- **画布左下角宠物菜单（🐾）** → 展开选 🐱/🐶 → 画布随机落位虚拟宠物贴纸（氛围层，不进 Placement、不落库）；点贴纸「抱走」移除
- **家具库架首「+」卡** → `DouyinLinkSheet` 粘贴浮层 → `navigateTo /pages/flow/recognize/index?sourceId=...`
- **AI 建议** → `navigateTo /pages/flow/suggest/index?roomId`
- **空间资产库 - 模板空间** → 取/建 `type=template` 样板间 → `navigateTo /pages/flow/place/index?homeId&roomId`
- **空间资产库 - 「+」卡** → 动作层：扫描房屋（相机→识别流）/ 上传平面图（相册/相机→建空屋→摆放页）
- 画布上旧家具「旧 ✕」→ 页内移除（无跳转）

### Tab3 发现（direction）——一页完成，不越跳越深
- 选中方向后同页顺序向下展开（切方向重播展开动画）：
  1. **给建议** → 页内建议卡（`sceneSuggestions` 按画像标签过滤，风水卡带 `view_fengshui` 埋点）
  2. **推单品** → 页内单品卡：「放进空间」toast 占位；「链接识别」→ `DouyinLinkSheet` 粘贴浮层 → 识别流（拍板：不做真外跳抖音）
  3. **是否直接改** → 黄底蓝字 CTA → `navigateTo /pages/flow/place/index?homeId&roomId&direction`（place 页带 direction 不弹浮窗）
- **场景改造四场景卡** → `navigateTo /pages/discover/scene/index?id=scene_pet/scene_baby/scene_fengshui/scene_flow`
- Tab 直开无参数时回落：首要家（isPrimary）的第一个房间

### Tab4 灵感（discover）
- **家具资产库单品** → `navigateTo /pages/discover/detail/index?id=...`
- **Feed 单品卡** → 同上详情页

## 三、动作流页（非 Tab）

### 摆放页 `flow/place`（核心页）
页面结构：顶部标题+邀请/分享 → 3D 空间（拖拽家具、旧房可移除旧家具）→ 家具库横滑 → **AI 优化建议卡**（改造之前给建议，可收起）→ 右下悬浮胶囊「选方向 · 出方案」→ 屏幕居中**操作台浮窗**（首次摆放完成自动弹一次）。
⚠️ 带 `direction` 参数进入（发现页/场景页「直接改」）时**不自动弹浮窗**，改为 toast「已按「X」方向进入试改」，且浮窗内方向已预选。
- 浮窗内：
  - 方向 pills 选中 → 三动作：① 出方案 → `suggest`；② 荐单品 → `recommend`；③ 直接改 → 关浮窗 mock 试改
  - **更多方向，去发现页 ›** → `switchTab /pages/direction/index`
  - **出方案** → `navigateTo /pages/flow/complete/index?roomId&assetId`（整屋补全）
- ~~保存方案按钮~~ **已删**：摆放随拖拽松手自动写 store + Storage（跟随空间持久化），切换空间再回来保持上次摆放
  - **微调布局 / 换风格换单品 →** → `switchTab /pages/discover/index`（灵感）
- 顶部：邀请 / 分享（toast 占位）

### 识别流 `flow/recognize`
- 识别完成（落库资产）→ `navigateTo /pages/flow/place/index?roomId&assetId`
- 返回 → `navigateBack`

### AI 建议 `flow/suggest`
- 「去摆放」→ `navigateTo /pages/flow/place/index?roomId`

### 荐单品 `flow/recommend`
- **放进空间** → （占位，无跳转）
- **直达抖音** → 当前实现为 `navigateTo /pages/discover/detail/index?id=...`（⚠️ 真外跳抖音商城未接，H5 上先跳详情页占位）

### 场景详情 `discover/scene`（MVP 四场景，入口=发现页场景卡）
- 结构：场景大图+方向角标 → 标题收藏 → 场景需求解读 → **改造要点**（序号陈列）→ **家具元素**列表 → 底部 CTA
- **家具元素** → `navigateTo /pages/discover/detail/index?id=...`
- **按这个场景改我的家** → `navigateTo /pages/flow/place/index?homeId&roomId&direction=场景方向`（回落首要家第一个房间）

### 单品详情 `discover/detail`
- **AR 摆放 / 放进我家** → `navigateTo /pages/flow/recognize/index?furnitureId`
- 收藏 → 页内状态 + 埋点
- ~~多渠道比价区块~~ **已删**

### 整屋补全 `flow/complete`
- 配齐 → toast + `navigateBack`

## 四、删除清单

**比价/下单线（上一轮）**：`pages/flow/order/`、`services/order.ts`、`store/useOrderStore.ts`、`fetchPriceCompare`、`Order` 类型、`Asset.status='ordered'`、详情页比价区块、我的家「已下单」统计。

**本轮（2026-07-25 v3）**：
- 设计页：「改造一个家」三入口卡片 + 户型确认区 + 双行资产架（空间/家具）+ 对应 scss
- 我的家：方案清单 UI、「开始摆放」主 CTA
- `.add-sheet` 动作层样式上移到 `src/styles/add-sheet.scss` 全局共用（设计页/我的家都用）

**本轮（2026-07-25 v4）**：
- 摆放页浮窗「保存方案」按钮 + `store/useSchemeStore.ts` 整个删除（该 store 原本就缺 import 且 `Scheme` 类型不存在，属不可编译死代码；摆放本就在拖拽松手时自动落库）
- 我的家：顶部「识别 X 件 · 已摆放 Y 件」统计条（含 scss/useMemo）
- place 页 scss 死样式（`.place__actions`/`.place__action-*`/`.place__sub-link`、`.console-modal__action-sub`）
- CoverShelf 3D 抽出体系：`perspective`/`rotateY(-28deg)`/负边距重叠/抽出与让位动画/滚动居中自动抽出/首卡脉冲演示 + `autoHintDelay` prop

**本轮（2026-07-25 v5）**：
- 发现页：`DirectionActions` 三动作跳页改为页内三段展开（suggest/recommend 两页现仅由摆放页浮窗三动作进入；AI 建议页另由我的家 CTA 进入）
- 方向「配色」「更多」下线（DirectionPicker 收敛 4 个 MVP 方向）
- 场景详情页：悬浮搜索占位（静态无逻辑）、旧 mock 场景（意式书房/法式客厅）→ 4 个 MVP 场景（含 direction/points 新字段）
- 场景页 `scene/index.scss` 搜索框样式、发现页 `__panel/__current/__desc` 旧样式

**本轮（2026-07-25 v6）**：
- 「直达抖音」假外跳全线下线，替换为 `DouyinLinkSheet`（粘贴链接 → 识别流）；设计页第四端口保留直读剪贴板快捷路径
- 四场景旧封面（复用空间模板图）→ 按场景功能单独绘制的 4 张底图（`src/assets/scenes/scene-*.png`，`mock/images.ts` 导出 `sceneImages`）
- 我的家：页首「共建/分享」、画布宠物菜单（虚拟猫狗氛围层）、家具库架首「+」卡（`FurnitureLibrary` 新增 `onAdd` prop）

## 五、待你拍板的遗留点

1. **相机/相册/剪贴板在 H5 预览里是降级实现**（文件选择器 / getClipboardData 可能失败走模拟 sourceId），真机小程序才是全量能力，属预期。
2. **Taro 4.2.1 的 webpack-dev-server 在本项目（中文路径）下白屏**（`Cannot GET /`），H5 预览固定走 `pnpm build:h5` + `pnpm preview:h5`；改完代码需重新 build 再刷新。

## 六、在手机上看 H5 效果

1. 电脑保持 `pnpm preview:h5`（10086 端口）运行，且**手机与电脑连同一 Wi-Fi**。
2. 查电脑局域网 IP：`ipconfig` → 无线网卡 IPv4（当前为 `192.168.43.169`）。
3. 手机浏览器访问 `http://192.168.43.169:10086/` 即可（预览服务已监听 0.0.0.0）。
4. 若打不开：Windows 防火墙首次会拦 node，点「允许」；公司/校园网有 AP 隔离时改用电脑开热点、手机连该热点。
5. 快速自查也可在 Chrome F12 → 设备工具栏选 iPhone 视口（桌面端 ≥600px 已限宽 430px 手机画幅，非必须）。
