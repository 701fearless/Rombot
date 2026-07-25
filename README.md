# QQ House 家居空间演示

这是一个从家装视频灵感进入真实户型编辑，再得到空间布局建议的 H5 演示。当前技术栈统一为 **FastAPI + Vite + React 18 + TypeScript + React Router + Three.js**，前后端由 FastAPI 同域托管。

## 当前可体验链路

打开 `http://127.0.0.1:8000/` 后直接进入视频 Feed：

1. 浏览视频 1-6，暂停当前视频。
2. 浏览器计算画面 dHash，`POST /api/feed/detect` 命中离线 `analysis.json`。
3. 只有已经预生成 GLB 的家具 Tag 可以点击。
4. 点击 Tag 后读取预处理资产，并进入 `/space?sceneId=room6`。
5. room6 Three.js 编辑器同时加载户型白模和快照中的全部家具。
6. 家具支持选中、地面拖动、10cm 网格吸附、边界限制、旋转、缩放、复制和删除；单件 GLB 失败时显示占位盒。
7. 墙体模式支持选中、拖动吸附、删除，并将编辑结果保存为运行版白模。
8. “保存方案”持久化完整 `SceneSnapshot`；后端不可用时写入浏览器 `localStorage` 并显示“本地保存”。
9. “完成摆放并查看建议”把快照转换为 `SceneResponse`，调用 `/api/room/room-layout` 且 `enableAgents=false`。
10. 只有空间接口失败时才回退确定性 Mock；“应用全部建议”会更新家具位姿并再次保存。

当前正式户型只有 room6（6.0m × 4.2m）。room1 和 room8 只在“我的”中显示为后续接入，不伪装为可用。Ark 户型重建、实时 AI 和实时生 3D 接口保留，但不进入比赛演示热路径。

## 运行环境

Python 统一使用 Conda `ml2025`。不要创建或引用 `.venv`、`venv`、`.venv-retrieval`。

```powershell
conda activate ml2025
cd F:\DREAME\Qiuliying\lucky\frontend
npm ci --legacy-peer-deps
npm run build

cd ..\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

开发时可分别启动：

```powershell
# 终端 1
conda activate ml2025
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 终端 2
cd frontend
npm run dev
```

Vite 会把 `/api`、`/outputs`、`/sample_data`、`/static` 代理到 8000；生产构建始终使用同域相对 URL。

## 页面路由

| 路由 | 作用 |
| --- | --- |
| `/` | 视频 1-6 Feed，暂停识别入口 |
| `/home` | 我的家和 room6 方案入口 |
| `/discover` | 场景方向与生活方式建议 |
| `/me` | 户型选择和建模入口 |
| `/space` | room6 多家具 Three.js 编辑器 |
| `/product/:id`、`/scene/:id` | 单品和场景详情 |
| `/recognize`、`/suggest`、`/recommend`、`/complete` | 动作流页面 |
| `/dashboard` | 接口与开发入口 |

`/feed` 和原 `/pages/...` 地址会重定向到新路由。前端不再包含 Taro、NutUI Taro、微信项目配置或小程序构建目标。

## SceneSnapshot

`SceneSnapshot` 是前端唯一场景状态，单位为米，坐标系固定为 `threejs-xz-ground-y-up`。核心内容包括：

- 快照身份：`snapshotId`、`sceneId`、`revision`、`updatedAt`。
- 户型：`floorPolygon`、墙体、门窗、`whiteboxGlbUrl`。
- 家具：Feed 来源、语义、真实尺寸、GLB/crop URL、position/rotation/scale、锁定和区域状态。
- 用户上下文：家庭成员、儿童/老人/宠物、生活习惯和偏好。

运行时数据位置：

```text
backend/outputs/scenes/room6/snapshot.json
backend/outputs/scenes/room6/whitebox.glb
```

预设模板位于 `backend/sample_data/floorplans/preprocessed/room6/`，运行版保存不会覆盖预设。reset 会同时删除运行时快照和运行版白模。

主要接口：

```text
GET  /api/room/snapshots/room6
PUT  /api/room/snapshots/room6
POST /api/room/snapshots/room6/reset
PUT  /api/room/snapshots/room6/whitebox
POST /api/room/room-layout
POST /api/feed/detect
GET  /api/feed/prebuilt-asset
GET/POST/DELETE /api/furniture/...
```

## 验证命令

```powershell
cd frontend
npm test
npm run typecheck
npm run lint
npm run build

cd ..\backend
E:\Anaconda3\envs\ml2025\python.exe -m unittest discover -s tests -v
```

当前前端测试覆盖 dHash、Tag 坐标、墙体磁吸、SHA-256 和 3×3 射线自动剖面；后端覆盖 Feed 资产、家具上传、全屋建议、快照和运行版白模。
