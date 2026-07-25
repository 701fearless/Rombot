# Space Energy MVP Backend

FastAPI backend for the hackathon MVP.

## Run

```powershell
cd backend
E:\Anaconda3\envs\ml2025\python.exe -m pip install -r requirements.txt
E:\Anaconda3\envs\ml2025\python.exe -m uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/health
```

## APIs

### Preprocess a video before users pause

```http
POST /api/video/preprocess
```

```json
{
  "videoId": "living_room_001",
  "videoUrl": "/sample_data/videos/living_room_001.mp4",
  "sampleIntervalSec": 1.0,
  "mode": "mock",
  "maxFrames": 6
}
```

Modes:

```text
mock: no model call; generates demo frames/tags for frontend integration
ark_grounding: Ark Doubao visual grounding returns furniture bbox directly
grounded_sam2: calls the configured Grounded-SAM-2 Lite service
doubao_grounding_sam: Doubao labels -> Grounding DINO bbox -> SAM mask -> analysis.json
manual: keeps the same output shape for manually corrected analysis files
```

The generated file is:

```text
outputs/videos/<videoId>/analysis.json
```

Inspect analysis:

```http
GET /api/video/analysis/{videoId}
GET /api/video/analysis/{videoId}/nearest?time=12.4
```

### Detect paused furniture tags

```http
POST /api/feed/detect
```

```json
{
  "videoId": "living_room_001",
  "time": 12.4,
  "frameImage": "data:image/jpeg;base64,..."
}
```

If `outputs/videos/<videoId>/analysis.json` exists, this endpoint reads the nearest preprocessed frame and returns immediately. Otherwise it uses the configured realtime provider, including `ark_grounding`, `grounded_sam2`, or `mock`.

### Select, segment, and generate a furniture model

```http
POST /api/feed/select-object
```

```json
{
  "frameId": "frame_living_room_001_12_40",
  "objectId": "obj_sofa_001",
  "frameImage": "data:image/jpeg;base64,..."
}
```

This runs:

```text
selected furniture tag -> segmentation crop/mask -> 3D model provider
```

### One-call pipeline test

```http
POST /api/feed/run-pipeline
```

```json
{
  "videoId": "living_room_001",
  "time": 12.4,
  "frameImage": "data:image/jpeg;base64,...",
  "objectId": "obj_sofa_001"
}
```

`objectId` is optional. If omitted, the backend selects the first detected object.

### Mock room scan

```http
POST /api/room/scan
```

```json
{
  "scanId": "demo_living_room"
}
```

### 两种布局模式 API

系统提供两套主接口：

| 模式 | 接口 | 用途 |
|------|------|------|
| 单家具摆放 | `POST /api/room/placement-check` | 拖拽一件家具后的可行性与移动建议 |
| 全屋布局 | `POST /api/room/room-layout` | 不绑定单件，对整屋家具做系统优化 |
| 场景深化 | `POST /api/room/scenario-advice` | 用户选择养老/育婴/养宠/风水后的专项建议 |

> 旧接口 `POST /api/room/spatial-check` 仍可用，等价于 `placement-check`（已标记 deprecated）。

#### 模式一：单家具摆放 `placement-check`

```http
POST /api/room/placement-check
```

```json
{
  "enableAgents": true,
  "sceneId": "demo_living_room",
  "candidate": {
    "id": "candidate_sofa",
    "label": "sofa",
    "name": "沙发",
    "position": [1.2, 0.0, 2.1],
    "rotation": [0.0, 0.0, 0.0],
    "size": [2.0, 0.9, 0.8]
  }
}
```

响应：

- `mode`: `"placement"`
- `checks` / `feedback`：针对该 candidate 的几何硬约束
- `layout.moves`：该家具建议移动位姿
- `layout.advices`：中文布局建议
- `scenarioOptions`：可选生活场景

#### 模式二：全屋布局 `room-layout`

```http
POST /api/room/room-layout
```

```json
{
  "enableAgents": true,
  "sceneId": "demo_living_room"
}
```

也可直接传完整 `scene`（含 `objects` + `openings`）。**不需要 candidate。**

响应：

- `mode`: `"room"`
- `objectChecks`：逐件家具几何摘要
- `layout.moves`：多件家具建议移动
- `layout.advices`：全屋中文布局建议
- `scenarioOptions`：可选生活场景

#### 场景深化（两模式共用）

```http
POST /api/room/scenario-advice
```

```json
{
  "mode": "placement",
  "scenarios": ["elder", "pet"],
  "sceneId": "demo_living_room",
  "candidate": {
    "id": "candidate_sofa",
    "label": "sofa",
    "name": "沙发",
    "position": [1.2, 0.0, 2.1],
    "rotation": [0.0, 0.0, 0.0],
    "size": [2.0, 0.9, 0.8]
  },
  "layout": { "moves": [], "advices": [], "summary": "" },
  "geometryChecks": []
}
```

全屋模式示例：

```json
{
  "mode": "room",
  "scenarios": ["fengshui", "elder"],
  "sceneId": "demo_living_room",
  "layout": { "moves": [], "advices": [], "summary": "" }
}
```

`scenarios` 可选：`elder`（养老）、`infant`（育婴）、`pet`（养宠）、`fengshui`（风水），支持多选。

活动空间阈值见：

```text
app/services/layout_reasoning/rules/clearance_rules.json
```

Agent 开关：

```powershell
$env:SPATIAL_AGENT_PROVIDER="mock"   # 或 ark（无 ARK_API_KEY 时自动回退 mock）
$env:ARK_TEXT_MODEL="GLM-4-Flash"
```

本地验证：

```powershell
$env:SPATIAL_AGENT_PROVIDER="mock"
python scripts/test_spatial_check.py
```

案例效果文档：

```text
docs/spatial_modular_scenario_cases.md
```

## Provider switches

Defaults are mock providers.

```powershell
$env:DETECTION_PROVIDER="mock"
$env:SEGMENTATION_PROVIDER="mock"
$env:MODEL3D_PROVIDER="mock"
```

Ark Doubao visual grounding:

```powershell
$env:DETECTION_PROVIDER="ark_grounding"
$env:ARK_API_KEY="your_key"
$env:ARK_BASE_URL="https://ark.cn-beijing.volces.com/api/v3"
$env:ARK_VISION_MODEL="doubao-seed-2-1-pro-260628"
```

The same Ark call returns bbox, visible geometry/material/texture features, clutter
state, cleanup actions, and conservative symmetry/occlusion/pattern completion hints.
These fields are stored in `detection.json`/`analysis.json` and reused by image generation.

Preprocess with Ark Grounding:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/video/preprocess" `
  -ContentType "application/json" `
  -Body (@{
    videoId = "dining_room_001"
    videoUrl = "/sample_data/videos/dining_room_001.mp4"
    sampleIntervalSec = 1.0
    mode = "ark_grounding"
    maxFrames = 15
  } | ConvertTo-Json)
```

Ark returns bbox coordinates normalized to a 1000 x 1000 coordinate space. The backend converts them to pixel bbox, saves crop/mask files, and writes `analysis.json`.

Tripo Turbo full 3D generation:

```powershell
$env:MODEL3D_PROVIDER="feature_tripo"
$env:TRIPO_API_KEY="your_key"
$env:TRIPO_BASE_URL="https://api.tripo3d.com"
$env:TRIPO_MODEL_VERSION="v3.0-20250812"
$env:TRIPO_TEXTURE="true"
$env:TRIPO_PBR="false"
$env:TRIPO_TEXTURE_QUALITY="standard"
$env:TRIPO_TEXTURE_ALIGNMENT="geometry"
$env:TRIPO_EXPORT_UV="false"
$env:TRIPO_ENABLE_IMAGE_AUTOFIX="false"
$env:TRIPO_POLL_INTERVAL_SEC="5"
$env:TRIPO_POLL_ATTEMPTS="72"
```

`feature_tripo` keeps the same Ark feature brief and one 45-degree Seedream
reference image, then submits that reference to Tripo Turbo. `TRIPO_EXPORT_UV=false`
is the speed-first setting; enable it only when UV editing is needed later.
Use `https://api.tripo3d.com` for the v2 Turbo OpenAPI endpoint in the current
China network. The provider also accepts `https://openapi.tripo3d.com/v3` and
switches to the v3 payload shape automatically.

Open the local pipeline test page after starting the backend:

```text
http://127.0.0.1:8000/static/pipeline-test.html
```

The page accepts an image, displays `/api/feed/detect` results, shows generated
reference/material images returned by `/api/feed/select-object`, and previews the
final GLB in the embedded viewer.

Hunyuan full 3D generation:

```powershell
$env:MODEL3D_PROVIDER="feature_hunyuan"
$env:HUNYUAN_API_KEY="your_key"
$env:HUNYUAN_BASE_URL="https://tokenhub.tencentmaas.com"
$env:HUNYUAN_MODEL="hy-3d-express"
$env:HUNYUAN_ENABLE_PBR="false"
$env:HUNYUAN_ENABLE_GEOMETRY="false"
$env:HUNYUAN_RESULT_FORMAT="GLB"
$env:HUNYUAN_POLL_INTERVAL_SEC="5"
$env:HUNYUAN_POLL_ATTEMPTS="120"
```

`hy-3d-express` follows the Rapid API contract. It does not send the professional
model fields `generate_type`, `face_count`, or `polygon_type`.

Ark Seedream reference image before Hunyuan 3D:

```powershell
$env:ARK_IMAGE_MODEL="doubao-seedream-5-0-lite-260128"
$env:ARK_IMAGE_SIZE="2048x2048"
```

`feature_hunyuan` creates one 45-degree reference image, then submits it to Hunyuan.
Set `SEGMENTATION_PROVIDER=mock` to use the bbox crop/mask. Set it to `sam3` with a
valid endpoint to refine the mask; SAM failure falls back to the bbox result.

Grounded-SAM-2 detection + segmentation endpoint:

```powershell
$env:DETECTION_PROVIDER="grounded_sam2"
$env:GROUNDED_SAM2_ENDPOINT="https://your-grounded-sam2-service.example.com"
$env:GROUNDED_SAM2_API_KEY="your_key"
```

Optional tuning:

```powershell
$env:GROUNDED_SAM2_MIN_CONFIDENCE="0.35"
$env:GROUNDED_SAM2_MAX_OBJECTS="8"
$env:GROUNDED_SAM2_PROMPT="sofa . bed . chair . coffee table . chandelier . rug . curtain . plant ."
```

The backend calls:

```http
POST {GROUNDED_SAM2_ENDPOINT}/detect-and-segment
```

Request:

```json
{
  "image": "data:image/jpeg;base64,...",
  "prompt": "sofa . bed . chair . coffee table . chandelier . rug .",
  "box_threshold": 0.35,
  "text_threshold": 0.35,
  "max_objects": 8
}
```

Expected response:

```json
{
  "objects": [
    {
      "label": "sofa",
      "confidence": 0.91,
      "bbox": [118, 420, 690, 850],
      "mask": "data:image/png;base64,..."
    }
  ]
}
```

`bbox` can be pixel coordinates `[x1, y1, x2, y2]` or normalized coordinates `[0.1, 0.2, 0.5, 0.8]`. The backend maps English labels to Chinese tags and saves `cropUrl` / `maskUrl` under `outputs/<frameId>/`.

Doubao + Grounding DINO + SAM offline preprocessing:

```powershell
$env:DOUBAO_ENDPOINT="https://your-doubao-vision-endpoint"
$env:DOUBAO_API_KEY="your_key"
$env:DOUBAO_MODEL="your_vision_model"
$env:GROUNDING_DINO_ENDPOINT="http://your-4090-host:8001"
$env:GROUNDING_DINO_API_KEY="optional"
$env:SAM_ENDPOINT="http://your-4090-host:8002"
$env:SAM_API_KEY="optional"
```

`SAM_ENDPOINT` is optional. If it is missing or fails, preprocessing falls back to a rectangular bbox mask so the video analysis can still be generated.

Preprocess one video:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/video/preprocess" `
  -ContentType "application/json" `
  -Body (@{
    videoId = "dining_room_001"
    videoUrl = "/sample_data/videos/dining_room_001.mp4"
    sampleIntervalSec = 1.0
    mode = "doubao_grounding_sam"
    maxFrames = 15
  } | ConvertTo-Json)
```

This mode runs:

```text
extract frames -> Doubao furniture labels -> Grounding DINO short prompt boxes -> SAM masks -> analysis.json
```

SAM 3 compatible segmentation-only endpoint:

```powershell
$env:SEGMENTATION_PROVIDER="sam3"
$env:SAM3_ENDPOINT="https://your-sam3-service.example.com"
$env:SAM3_API_KEY="your_key"
```

Meshy Image-to-3D:

```powershell
$env:MODEL3D_PROVIDER="meshy"
$env:MESHY_API_KEY="your_key"
```

Pixal3D compatible Image-to-3D endpoint:

```powershell
$env:MODEL3D_PROVIDER="pixal3d"
$env:PIXAL3D_ENDPOINT="https://your-pixal3d-service.example.com"
$env:PIXAL3D_API_KEY="your_key"
```

The real API adapters are isolated behind providers. When a key or endpoint is missing, the app falls back to mock providers so the H5 flow remains testable.

## Test with a local paused-frame image

```powershell
cd F:\DREAME\Qiuliying\lucky\backend
E:\Anaconda3\envs\ml2025\python.exe .\scripts\test_image_flow.py "F:\path\to\your\room.jpg"
```

Use Meshy for the selected segmented crop:

```powershell
$env:MODEL3D_PROVIDER="meshy"
$env:MESHY_API_KEY="your_key"
E:\Anaconda3\envs\ml2025\python.exe .\scripts\test_image_flow.py "F:\path\to\your\room.jpg" --object-id obj_sofa_001
```

## Test offline video preprocessing with mock data

```powershell
cd F:\DREAME\Qiuliying\lucky\backend
E:\Anaconda3\envs\ml2025\python.exe .\scripts\test_video_preprocess_flow.py
```

This creates:

```text
outputs/videos/living_room_demo/analysis.json
```

Then it verifies:

```text
preprocess -> /api/feed/detect nearest-frame lookup -> /api/feed/select-object
```
