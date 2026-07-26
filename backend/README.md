# Rombot 项目总览与开发入口

> 新开开发窗口或交接给新的协作者时，先读本文。本文是当前任务背景、产品链路、技术边界、
> 运行方式和进度的单一入口；更细的历史与接口说明见文末文档索引。

## 1. 项目目标

Rombot 是一个家装空间体验原型。用户先选择自己的户型，再从家装视频中挑选家具，将家具
放入同一个 3D 空间；后续继续提供相似商品候选和摆放合理性建议。

当前主运行栈：

```text
FastAPI
  + Taro 4 / React 18 / TypeScript
  + Zustand / Taro Storage
  + 本地静态资产与离线分析缓存
```

比赛部署采用同域架构：FastAPI 同时提供 `/api/*`、`/outputs`、`/sample_data`、`/static`
和 `frontend/dist` SPA。统一入口为 `http://127.0.0.1:8000`。

## 2. 新窗口必须遵守的边界

1. Python 环境固定使用 Conda 的 `ml2025`：先执行 `conda activate ml2025`。
2. 不创建或使用 `.venv`、`venv`、`.venv-retrieval`，也不要在文档中重新引入这些方案。
3. 比赛热路径优先使用预处理户型、离线 `analysis.json` 和预生成家具 GLB，不现场调用 AI。
4. 当前商品候选是明确标记的 Mock 数据；不能称为真实 IKEA、CLIP 或同款检索结果。
5. 当前空间测试使用 Mock 房间，但越界、碰撞、门窗净空和活动空间检查是真实几何规则。
6. 当前可体验闭环固定使用 `room6`；`room1` 和 `room8` 只保留后续选择框架，不能称为已接入。
7. 不提交 `.env`、密钥、带签名结果、大模型索引或无白名单的大型 GLB。
8. 手机端测试暂时停用；桌面测试通过不代表移动端已经验收。

## 3. 当前演示主链路

```text
打开 /
  → Taro 全屏视频 Feed（视频 1–6，默认视频 1）
  → 播放并暂停
  → videoId + time + 64-bit frameHash
  → POST /api/feed/detect
  → 命中 outputs/videos/<videoId>/analysis.json
  → 只有 prebuiltGlbUrl 存在的家具 Tag 可点击
  → GET /api/feed/prebuilt-asset
  → 携带 sceneId=room6 + frameId + objectId 进入 flow/place
  → GET /api/room/snapshots/room6
  → 3D 户型中按真实尺寸加入、拖动、旋转、缩放家具
  → PUT 完整 SceneSnapshot JSON
  → 生成结构化布局建议
  → 一键应用目标坐标并再次保存
```

这条链路不会调用 Ark、Seedream、Tripo、Hunyuan 或实时空间 Agent。稳定性取决于：

- `sample_data/floorplans/presets.json`
- `outputs/videos/<videoId>/analysis.json`
- `outputs/videos/<videoId>/generated/<candidateId>/generated_model.glb`
- `outputs/videos/<videoId>/glb/<candidateId>.glb`（兼容导入目录，旧路径不存在时回退）
- `sample_data/floorplans/preprocessed/room6/demo_snapshot.json`
- `outputs/scenes/room6/snapshot.json`（首次保存后产生）
- `frontend/dist`

## 4. 当前可体验入口

测试入口：

```text
http://127.0.0.1:8000/
```

推荐演示步骤：

1. 首屏视频 1 自动静音播放；Feed 按 1–6 排列，点击画面暂停。
2. 等待离线识别 Tag；灰色 Tag 表示没有预生成 GLB，不能进入摆放。
3. 点击可用 Tag，自动进入 room6。
4. 拖动家具，使用旋转和缩放按钮微调。
5. 点击“完成摆放并查看建议”，整份场景快照保存到后端；失败时标记为本地保存。
6. 查看动线、尺寸、材质三类 Mock 建议。
7. 点击“一键应用动线建议”，确认家具实际移动且新坐标再次保存。

测试页中的数据边界：

| 阶段 | 当前实现 | 是否调用外部 AI |
|------|----------|------------------|
| 暂停家具识别 | 离线 `analysis.json` + dHash 前后帧匹配 | 否 |
| 家具 3D | 优先读取预生成 GLB | 否 |
| 户型场景 | room6 初始快照 + 运行时完整快照 | 否 |
| 布局建议 | 前端确定性 Mock，响应形状对齐 `RoomLayoutResponse` | 否 |
| 一键应用 | 使用建议中的目标米制位姿修改快照 | 否 |

快照接口：

| 接口 | 用途 |
|------|------|
| `GET /api/room/snapshots/room6` | 读取运行时快照；不存在则读取初始模板 |
| `PUT /api/room/snapshots/room6` | 保存整份快照，由后端递增 revision |
| `POST /api/room/snapshots/room6/reset` | 删除运行时快照并恢复模板 |

## 5. 遗留 Vite / Three.js 能力

旧 `App.tsx`、`VideoFeed`、`SpacePlaceholder` 和 `FloorplanViewer` 源码仍保留作能力参考，但不参与
当前 Taro 构建，也不是当前体验入口。它们曾支持：

- 上传/拍摄 JPEG、PNG、WebP 户型图，最大 15 MB。
- 在浏览器计算 SHA-256，匹配 `room1–7` 预设。
- 使用 `sceneId` 恢复户型，使用 `frameId + objectId` 恢复缓存家具。
- 根据 `estimatedDimensions` 对家具 GLB 做宽、高、深三轴归一。
- 沿 X/Z 移动、绕 Y 轴旋转、等比缩放，家具落地并限制在户型包围盒内。
- OrbitControls 环绕观察。
- 屏幕 3×3 共 9 条射线选择遮挡墙，约 180 ms 淡出；俯视时恢复全部墙体。
- 新白模读取 `extras.rombotKind/wallId`；旧比赛白模兼容 `wall_*_block_*` 节点名。

当前限制：

- `room1–7` 的 `quality` 仍为 `placeholder`，七套目前使用相同占位白模。
- Space 只加载一次选择的一件家具，变换保存在组件内存中，刷新后不恢复摆放状态。
- Space 尚未调用 `/api/room/placement-check`。
- 上传户型与空间推理之间还没有 Scene 数据适配器。

## 6. 空间布局能力

后端已提供：

| 模式 | 接口 | 作用 |
|------|------|------|
| 单家具 | `POST /api/room/placement-check` | 检查当前摆放并给出该家具移动建议 |
| 旧兼容名 | `POST /api/room/spatial-check` | 等价于 placement-check，已 deprecated |
| 多家具 | `POST /api/room/room-layout` | 逐件检查并给出全屋移动与布局建议 |
| 场景深化 | `POST /api/room/scenario-advice` | 养老、育婴、养宠、风水专项建议 |

单家具几何检查包括：

- `fit`：是否越过房间边界或超过层高。
- `collision`：是否与其他实体家具重叠。
- `accessibility`：是否侵入门窗开启/使用净空。
- `clearance`：品类活动空间是否满足规则。

规则位于 `app/services/layout_reasoning/rules/clearance_rules.json`。坐标约定为 Y-up、米制、
地面使用 XZ 平面，`rotation[1]` 是绕 Y 轴的弧度。

`enableAgents=false` 时不调用文本模型，但仍返回真实几何 `checks` 和确定性
`layout.moves`。`enableAgents=true` 时再由 `SPATIAL_AGENT_PROVIDER=ark|mock` 补充中文建议。

当前“全屋”实际上是一个矩形房间中的多家具，不是带内墙拓扑的多房间住宅。

### 尚未连接的关键适配层

正常全屋 GLB 不能直接交给空间 Agent。后续需要把渲染模型转换为 `SceneResponse`：

```text
户型结构 JSON / GLB extras
  → room 边界和高度
  → openings 门窗位置、朝向和净空
  → objects 家具类别、尺寸、位置和旋转
  → 统一 Y-up 米制布局坐标
  → placement-check / room-layout
```

Viewer 会将户型居中到原点，而当前几何引擎使用 `(0,0) → (width,depth)`，因此还必须维护
`viewerToLayout` / `layoutToViewer` 坐标转换。建议先完成单家具闭环：

```text
拖动结束
  → onTransformChange
  → PlacementCandidate
  → placement-check(enableAgents=false)
  → 半透明预览建议位置
  → 用户确认应用
  → 再检查一次
```

## 7. 商品候选能力

当前已经挂载：

```http
POST /api/product/mock-search
```

请求使用识别对象的 `objectId + label + name + estimatedDimensions`，按类别返回 3 个固定候选。
响应明确包含：

```json
{
  "source": "mock_catalog",
  "isMock": true,
  "matches": []
}
```

当前仓库没有离线 IKEA/OpenCLIP/FAISS 的服务、索引、图片或 `clip-search` 路由。续篇中相关
内容是来源分支能力说明，不是当前可运行能力。未来接真实检索时应保持与 Mock 响应字段兼容，
并区分“视觉相似”与“真实同款”。

## 8. 冷路径：实时识别与生成 3D

以下能力仍保留，但不属于比赛热路径：

```text
图片/无缓存暂停帧
  → DETECTION_PROVIDER
  → segmentation crop/mask
  → Ark 视觉 brief 或复用 visualFeatures
  → Seedream 单张 45° 左前参考图
  → Hunyuan / Tripo Image-to-3D
  → generated_model.glb
```

常用 Provider：

| 配置 | 常用值 |
|------|--------|
| `DETECTION_PROVIDER` | `ark_grounding` / `grounded_sam2` / `mock` |
| `SEGMENTATION_PROVIDER` | `mock` / `sam3` |
| `MODEL3D_PROVIDER` | `feature_tripo` / `feature_hunyuan` / `mock` |
| `SPATIAL_AGENT_PROVIDER` | `ark` / `mock` |
| `ARK_VISION_MODEL` | `doubao-seed-2-1-pro-260628` |
| `ARK_IMAGE_MODEL` | `doubao-seedream-5-0-lite-260128` |
| `HUNYUAN_MODEL` | `hy-3d-3.1` |

完整变量见 `.env.example`。Provider 调试细节见 `交接说明.md`，不要让冷路径配置阻塞比赛缓存链。

## 9. 户型重建能力

比赛热路径使用 SHA-256 预设匹配。真实户型重建作为冷路径保留：

| 接口 | 作用 |
|------|------|
| `GET /api/floorplan/presets` | 获取 `room1–7` manifest |
| `GET /api/floorplan/presets/{sceneId}` | Space 刷新恢复预设 |
| `POST /api/floorplan/reconstruct` | Ark 解析户型图并由本地 Builder 生成白模 |
| `POST /api/floorplan/build-whitebox` | 从结构 JSON 离线生成白模，不调用 Ark |

Builder 新生成的 GLB 会写墙体和门窗元数据，供 Three.js 自动剖面使用。

## 10. 目录职责

| 路径 | 作用 |
|------|------|
| `app/main.py` | FastAPI 路由、静态资源和 SPA 同域托管 |
| `app/routers/feed.py` | 暂停识别、选物、预生成家具解析 |
| `app/routers/video.py` | 视频上传、人工帧、预处理、analysis 读取 |
| `app/routers/floorplan.py` | 户型预设、Ark 重建、白模 Builder 接口 |
| `app/routers/room.py` | mock scan、placement、room-layout、scenario |
| `app/routers/product.py` | Mock 商品候选接口 |
| `app/services/video_preprocess/` | 抽帧、dHash、CLIP 去重、尺寸估算 |
| `app/services/floorplan_whitebox/` | 户型 Schema、Ark 解析、纯 Python GLB Builder |
| `app/services/layout_reasoning/` | 几何规则、建议移动、布局与场景 Agent |
| `static/pipeline-test.html` | 当前无 AI 全链路联调页 |
| `static/frame-selector.html` | 人工筛帧工具 |
| `sample_data/floorplans/` | 比赛户型图、manifest、预处理白模 |
| `outputs/videos/<videoId>/` | 帧、analysis、去重候选和预生成家具 |
| `../frontend/src/pages/discover/` | 当前全屏视频 Feed |
| `../frontend/src/pages/flow/place/SnapshotPlacePage.tsx` | room6 快照摆放、保存、建议应用 |
| `../frontend/src/store/useSceneStore.ts` | 当前户型、快照、Feed 选中家具与本地降级 |
| `../frontend/src/components/FloorplanViewer.tsx` | 遗留 Three.js 渲染参考，不参与 Taro 构建 |

## 11. 环境与启动

### 首次安装

```powershell
conda activate ml2025

cd F:\DREAME\Qiuliying\lucky\backend
python -m pip install -r requirements.txt

cd ..\frontend
npm ci --legacy-peer-deps
```

### 比赛同域模式

```powershell
cd F:\DREAME\Qiuliying\lucky\frontend
npm run build:h5

cd ..\backend
conda activate ml2025
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

常用入口：

- `http://127.0.0.1:8000/`：当前 Feed → room6 → 建议闭环。
- `http://127.0.0.1:8000/api/room/snapshots/room6`：当前场景快照 JSON。
- `http://127.0.0.1:8000/static/pipeline-test.html`：全链路测试页。
- `http://127.0.0.1:8000/static/frame-selector.html`：人工筛帧。
- `http://127.0.0.1:8000/dashboard`：API 状态页。
- `http://127.0.0.1:8000/docs`：OpenAPI。
- `http://127.0.0.1:8000/health`：健康检查。

### 前后端分离开发

保持 FastAPI 在 8000 端口，另开终端：

```powershell
cd F:\DREAME\Qiuliying\lucky\frontend
npm run dev:h5
```

只执行 `npm run dev:h5`。Taro 开发服务器会代理 `/api`、`/outputs` 和 `/sample_data` 到
FastAPI 8000；生产构建全部使用同域相对 URL。

## 12. 验证命令与当前基线

Python 命令均在 `conda ml2025` 中执行：

```powershell
conda activate ml2025

cd F:\DREAME\Qiuliying\lucky\backend
python -m unittest discover -s tests -p "test_scene_snapshot.py" -v
python scripts/test_product_recommend.py

cd ..\frontend
npx tsc --noEmit
npm run build:h5
```

当前已知基线：

- room6 快照 API：读取、保存、revision、reset、校验共 2 项标准库测试通过。
- 商品识别与规则推荐脚本通过，当前仍为离线/Mock 数据边界。
- Taro TypeScript 检查和 H5 生产构建通过。
- 旧 Three.js 自动剖面测试是历史基线，不属于当前 Taro 闭环验收。
- 手机端测试暂时停用。

本机 `conda run -n ml2025` 可能打印 OpenCL `temp.txt` 警告；当前测试仍能完成。日常开发优先先
`conda activate ml2025`，再直接执行 `python`。

## 13. 当前优先级

1. 用真实 `room-layout` 服务替换 `layoutAdvice.ts` 的 Mock，保持页面响应契约不变。
2. 将 room6 的 2D 快照对象接入 Three.js，同时继续保存同一米制 transform。
3. 注册并验证 room1、room8 的 manifest、结构 JSON 和白模后再开放“我的”户型选择。
4. 将商品检索结果接到 Feed 家具详情，不改变主摆放链。
5. 恢复手机端视频暂停、Tag 和触控手势验收。

## 14. 文档索引

| 文档 | 用途 |
|------|------|
| `README.md` | 当前项目总入口，新窗口先读 |
| `交接说明.md` | 比赛主链路、完整接口与历史 Provider 细节 |
| `交接说明-续.md` | 来源分支的空间布局与商品检索说明；顶部有当前合并状态 |
| `docs/spatial_modular_scenario_cases.md` | 空间布局和场景建议案例 |
| `docs/spatial_agent_case_results.md` | 空间 Agent 案例结果 |
| `.env.example` | 所有环境变量模板 |

遇到文档冲突时，以本文“当前边界”和实际代码/测试为准；不要根据续篇中尚未合并的 IKEA、
CLIP、FAISS 或虚拟环境说明改变当前运行方式。
