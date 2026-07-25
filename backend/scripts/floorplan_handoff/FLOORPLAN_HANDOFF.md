# 户型图识别与白盒模型生成交接说明

## 1. 交接范围

本交接包整理自 Rombot 项目 `master` 分支，基线提交为：

```text
0fcb8a0a01d744aa081b7cef9e47c526c0206324
```

代码覆盖以下完整链路：

```text
户型图图片
  -> Ark 视觉模型识别
  -> 结构化 FloorplanWhiteboxScene JSON
  -> 固定建模规则归一化
  -> 独立墙体、地板、门窗构件
  -> 二进制 GLB
  -> Whitebox GLB Viewer 预览
```

压缩包不包含 `.env`、API Key、`backend/outputs`、缓存、依赖目录和历史 GLB 产物。

## 2. 当前实现状态

已完成：

- 户型图图片通过 Ark Chat Completions 视觉接口解析为 JSON。
- 识图 Prompt 包含尺寸、墙体拓扑、门窗图例、推拉门和旋转/平开门识别规则。
- 层高强制为 `3.0m`，墙厚强制为 `0.1m`；即使 AI 或调用方传入其他值也会归一化。
- 每段墙作为独立 GLB 节点/网格生成。
- 门窗位置会切分墙体，形成贯穿墙厚的真实开口，并生成可见构件，而不是只贴一张表面模型。
- 平开/旋转门支持门扇、门框、门套、把手；推拉门支持重叠面板、轨道、边框和拉手。
- 窗支持玻璃、框、竖梃、窗台和双面收口。
- 支持直接粘贴结构 JSON 生成 GLB，并在浏览器预览。

2026-07-25 本地验证结果：

```text
Python 编译检查：通过
离线 JSON -> GLB：通过
样例场景：5 段墙、4 个门窗构件
生成 GLB：75136 bytes
```

尚未完成或需继续加强：

- 当前环境对 Ark 外网请求曾返回连接失败，因此“真实图片 -> AI JSON”没有完成稳定的联网回归；离线建模链路已跑通。
- `knownLength` 当前只记录到 `ai_raw.json`，尚未参与比例校准。
- 几何校验主要依赖 Prompt 与 Pydantic，尚无闭合轮廓、墙体自交、门窗冲突的自动修复器。
- 图片会缩放到最长边 `768px` 后送 AI，复杂图纸的小尺寸标注可能丢失。
- 前端目前只有“上传/拍摄户型图”的入口交互，尚未接 `/api/floorplan/reconstruct`。

## 3. 核心文件

可直接作为新增文件合并：

```text
backend/app/routers/floorplan.py
backend/app/services/floorplan_whitebox/__init__.py
backend/app/services/floorplan_whitebox/ai_parser.py
backend/app/services/floorplan_whitebox/schemas.py
backend/app/services/floorplan_whitebox/whitebox_builder.py
backend/app/services/floorplan_whitebox/viewer/index.html
backend/scripts/test_floorplan_whitebox.py
backend/scripts/test_floorplan_ai_reconstruct.py
backend/sample_data/floorplans/*
```

共享文件快照，仅建议按差异手工合并：

```text
backend/app/main.py
backend/app/config.py
backend/app/storage/local_store.py
backend/app/schemas.py
backend/requirements.txt
```

可选前端参考：

```text
frontend/src/components/EntryHero/*
frontend/src/pages/remodel/*
frontend/src/pages/myhome/*
frontend/src/app.config.ts
```

这些前端文件用于展示户型图入口，不代表后端接口已接入。合并时应优先保留目标分支已有页面结构，只移植入口和上传逻辑。

## 4. 合并步骤

1. 将 `backend/app/services/floorplan_whitebox/`、`backend/app/routers/floorplan.py`、两个测试脚本和样例数据复制到目标分支对应路径。
2. 在目标分支 `backend/app/main.py` 中加入：

```python
from app.routers import floorplan

app.include_router(floorplan.router, prefix="/api/floorplan", tags=["floorplan"])
```

3. 确认 `backend/app/config.py` 的 `Settings` 中存在：

```python
ark_api_key
ark_base_url
ark_vision_model
```

4. 若单独运行 Viewer，在 CORS 白名单中加入：

```text
http://localhost:8787
http://127.0.0.1:8787
```

5. 确认 `local_store.py` 提供以下符号：

```text
BACKEND_ROOT
OUTPUTS_ROOT
file_to_data_url
path_to_output_url
save_data_url
```

6. 合并依赖，至少需要：

```text
fastapi
uvicorn[standard]
pydantic>=2
httpx
Pillow
python-dotenv
```

7. 在根 `.gitignore` 中加入：

```gitignore
backend/.env
backend/outputs/floorplans/
__pycache__/
*.py[cod]
```

不要直接覆盖目标分支的 `main.py`、`config.py`、`local_store.py` 或 `.gitignore`。

## 5. 环境变量

在 `backend/.env` 中配置，交接包不携带真实值：

```dotenv
ARK_API_KEY=replace_me
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
ARK_VISION_MODEL=replace_with_vision_model_endpoint
```

户型图识别使用的是 `ARK_VISION_MODEL`。家具参考图生成所用的 `ARK_IMAGE_MODEL` 不参与这条链路。

## 6. API

### 图片识别并建模

```http
POST /api/floorplan/reconstruct
Content-Type: application/json
```

使用后端样例图片：

```json
{
  "imagePath": "/sample_data/floorplans/ai_test_floorplan.jpg",
  "sceneId": "floorplan_ai_smoke"
}
```

也可以传入 `image`，值为完整的 `data:image/...;base64,...`。

成功后会写入：

```text
backend/outputs/floorplans/<scene_id>/original.png
backend/outputs/floorplans/<scene_id>/ai_input.jpg       # 发生缩放时
backend/outputs/floorplans/<scene_id>/ai_raw.json
backend/outputs/floorplans/<scene_id>/normalized_scene.json
backend/outputs/floorplans/<scene_id>/whitebox.glb
```

### 直接用 JSON 建模

```http
POST /api/floorplan/build-whitebox
Content-Type: application/json
```

请求体直接使用 `FloorplanWhiteboxScene`。完整样例见：

```text
backend/sample_data/floorplans/sample_whitebox_scene.json
backend/sample_data/floorplans/floorplan_ai_001_scene.json
```

## 7. 本地运行与测试

在 `backend` 目录运行：

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

离线验证 JSON 到 GLB：

```powershell
python .\scripts\test_floorplan_whitebox.py
```

联网验证图片识别到 GLB：

```powershell
python .\scripts\test_floorplan_ai_reconstruct.py .\sample_data\floorplans\ai_test_floorplan.jpg
```

另开终端，在 `backend` 目录启动预览静态服务：

```powershell
python -m http.server 8787 --bind 127.0.0.1
```

打开：

```text
http://127.0.0.1:8787/app/services/floorplan_whitebox/viewer/index.html
```

Viewer 使用 CDN 加载 Three.js，离线环境下需要改成本地依赖。

## 8. 数据约束

结构 JSON 的关键约束：

- 平面单位固定为米。
- `floorPolygon` 表示地板外轮廓。
- 每个 `walls[]` 元素是一段独立墙中心线，`start/end` 为平面坐标。
- `wallFixtures[].wallId` 必须引用真实墙段。
- `offset` 是从 `wall.start` 沿墙方向到构件中心的距离，不是距墙端的边缘距离。
- 门固定落地，常规高度 `2.1m`；窗常规窗台 `0.9m`、高度 `1.2m`。
- 构件宽度及收口必须能放入墙段，并尽量距墙端、转角或 T 接点至少 `0.15m`。
- 支持的门型样式主要为 `swing_panel_door`、`sliding_glass_door`、`minimal_panel_door`。

## 9. 建议的后续优先级

1. 增加 JSON 几何验证器：外轮廓闭合、墙相交、开口越界、构件重叠、悬空墙检测。
2. 把 `knownLength` 真正接入坐标比例校准，并允许 OCR 尺寸链对 AI 输出进行二次约束。
3. 对同一张图运行多次识别并做拓扑一致性投票，降低视觉模型随机误判。
4. 前端上传后接入 `/api/floorplan/reconstruct`，补充进度、失败重试、JSON 人工修正和 GLB 预览。
5. 为典型户型建立回归集，至少覆盖矩形、凹形、阳台、飘窗、推拉门、旋转/平开门和多 T 接点隔墙。

## 10. 合并注意事项

- `backend/app/services/floorplan_whitebox/README.md` 早期部分包含规划性接口描述；当前可执行接口以 `backend/app/routers/floorplan.py` 为准。
- 不要把 `backend/outputs/floorplans` 中的运行产物提交到 Git。
- 不要把协作者本机 `.env` 合并或提交。
- `whitebox_builder.py` 不依赖 Blender 或 trimesh，GLB 由 Python 标准库直接写出；修改网格逻辑后务必同时跑离线样例并在 Viewer 中目检。
