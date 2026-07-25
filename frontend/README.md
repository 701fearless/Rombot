# home-ai-miniapp · 家居 AI 小程序

「抖音刷到家具 → 识别 → 放进我家 → AI 出整屋方案 → 比价下单」的家居 AI 小程序前端。
技术栈：**Taro 4 + React 18 + TypeScript（strict）+ Zustand + SCSS Tokens + NutUI-React-Taro**。

## 启动步骤

前置要求：**Node.js 18+**，包管理器推荐 pnpm。

```bash
# 1. 安装依赖
pnpm i

# 2. 微信小程序开发模式（watch 编译到 dist/）
pnpm dev:weapp

# 3. 用微信开发者工具打开项目根目录
#    project.config.json 已配置 miniprogramRoot = dist/，appid = touristappid（测试号）
```

其他命令：

```bash
pnpm dev:h5        # H5 开发模式
pnpm build:weapp   # 微信小程序生产构建
pnpm build:h5      # H5 生产构建
pnpm lint          # ESLint 检查（PRD 要求提交前无 lint error）
```

## 目录说明

- `src/app.config.ts` — 全局路由表（4 个 Tab + 5 个全屏动作流页）
- `src/styles/tokens.scss` — 视觉 Design Token（莫兰蒂色板 / 圆角 / 字号阶梯 / 浮雕阴影变量）
- `src/styles/effects.scss` — 特效（`.liquid-glass` / 入场动效 / `.emboss` 浮雕 / 减弱动效兜底）
- `src/types/models.ts` — 数据模型（PRD 第 4 节，严格照建）
- `src/mock/` — Mock 数据（家具 SKU 库 / 用户 / 房屋 / 建议列表）
- `src/services/` — 接口服务层（真实接口路径已按契约用 JSDoc 预留，内部返回 Mock）
- `src/store/` — Zustand 全局状态 + Taro Storage 持久化（资产 / 家 / 方案 / 订单）
- `src/utils/` — 工具（id 生成 / ProfileSignal 埋点 / persist 适配器）
- `src/assets/` — 静态资源（Hero 图需自行放入，见 `src/assets/README.md`）

## ⚠️ 构建未验证声明

开发本骨架的机器**未安装 Node.js**，以上依赖版本**未经实际安装与构建验证**，
首次 `pnpm i` / `pnpm dev:weapp` 时如遇版本兼容问题，请按报错微调版本号
（重点是 `@tarojs/*` 全家桶保持同一版本线）。

## 页面开发约定

页面文件（`src/pages/**`）与业务组件（`src/components/**`）由页面组并行开发，
本骨架只提供路由表与地基。页面开发时请遵循：

- 颜色 / 圆角 / 间距一律使用 `tokens.scss` 的 CSS 变量，**禁止硬编码色值**。
- 动作流产出物必须写入 `src/store/` 对应 store（已持久化，退出不丢）。
- 埋点调用 `logSignal(type, context)`（见 `src/utils/signal.ts`）。
