# QQ House Taro 前端

完整任务背景、当前链路、后端接口、环境边界与进度统一见
[`../backend/README.md`](../backend/README.md)。新窗口先读该文件。

当前前端使用 Taro 4、React 18、TypeScript、Zustand 和 SCSS。H5 是本阶段唯一验收端，打开
根路径即进入全屏视频 Feed：

```text
Feed 暂停识别
  → 点击预生成家具 Tag
  → room6 2D 摆放
  → 保存 SceneSnapshot
  → Mock 建议
  → 一键应用并再次保存
```

## 安装与构建

Node.js 18+。当前锁文件已按 Taro 4.2.1 同步，使用 npm：

```powershell
cd F:\DREAME\Qiuliying\lucky\frontend
npm ci --legacy-peer-deps
npm run typecheck
npm run lint
npm run build:h5
```

前后端分离开发时，先在 Conda `ml2025` 中启动 FastAPI 8000，再运行：

```powershell
npm run dev:h5
```

开发服务器会代理 `/api`、`/sample_data` 和 `/outputs`。生产构建使用同域相对 URL。

## 当前入口

- `src/pages/discover/`：全屏视频 Feed 和暂停 Tag。
- `src/pages/flow/place/SnapshotPlacePage.tsx`：room6 快照摆放闭环。
- `src/services/backend.ts`：Taro 同域 API Client。
- `src/services/layoutAdvice.ts`：可被真实空间推理替换的 Mock 建议边界。
- `src/store/useSceneStore.ts`：当前户型、快照、待摆家具和本地持久化。
- `src/types/scene.ts`：SceneSnapshot 和布局建议协议。

旧 Vite/Three.js 文件仍保留为参考，但不参与 Taro 构建或类型检查。room1、room8 当前只显示待接入，
默认且唯一可体验户型为 room6。
