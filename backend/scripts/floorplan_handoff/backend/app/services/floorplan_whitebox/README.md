# Floorplan Whitebox 技术路径

目标：输入一张户型图，稳定识别房屋结构，输出可编辑的结构化房屋数据，并生成带独立墙体、门窗构件的 3D 白屋 GLB。

核心原则：AI 负责理解图纸，代码负责几何建模。不要让 AI 直接生成 3D 模型；白屋必须由结构化 JSON 通过确定性几何算法生成。层高统一为 3m，墙体厚度统一为 0.1m，每面墙都作为独立 mesh 建模，门窗作为独立建筑组件贯穿对应墙体两面。

## 1. 总体链路

```text
户型图图片/PDF
-> 图像预处理
-> AI 结构识别
-> 几何规则校验与修复
-> 尺度恢复
-> 2D 房屋结构 JSON
-> 代码生成 3D 白屋 mesh
-> 导出 GLB + 调试图
```

推荐第一版只支持 `jpg/png`。PDF 分两类后续处理：矢量 PDF 直接抽线，扫描 PDF 先转图片。

## 2. 稳健 AI 识图方案

采用三层 AI，而不是单次识别：

1. 视觉结构解析器
   - 输入原始户型图。
   - 输出墙、门、窗、房间边界、尺寸标注、房间名称的结构化候选。
   - 适合使用强多模态视觉模型，要求输出严格 JSON。

2. 像素级辅助识别器
   - 输出 `wall_mask`、`door_mask`、`window_mask`、`text_mask`。
   - MVP 可先用 OpenCV + 形态学；后续可训练/微调 segmentation 模型。
   - 作用是给 AI 结果提供可验证的像素证据。

3. 几何审校器
   - 输入 AI JSON + mask + 原图。
   - 检查墙是否闭合、门窗是否落在墙上、房间轮廓是否自交、尺寸是否冲突。
   - 不直接“相信”AI，而是把 AI 结果修成几何上合法的结构。

## 3. AI 输出 Schema

AI 不输出 3D，只输出如下结构：

```json
{
  "schemaVersion": "0.1.0",
  "sourceType": "floorplan_image",
  "unit": "pixel",
  "scaleCandidates": [
    {
      "source": "ocr_dimension",
      "pixelLength": 420,
      "realLengthMeters": 4.2,
      "confidence": 0.82
    }
  ],
  "outerWalls": [
    {
      "id": "wall_outer_001",
      "start": [120, 80],
      "end": [720, 80],
      "thicknessPx": 18,
      "confidence": 0.94
    }
  ],
  "innerWalls": [],
  "wallFixtures": [
    {
      "id": "door_001",
      "type": "door",
      "wallId": "wall_inner_003",
      "center": [340, 260],
      "widthPx": 76,
      "swing": "left_in",
      "confidence": 0.78
    },
    {
      "id": "window_001",
      "type": "window",
      "wallId": "wall_outer_002",
      "center": [690, 300],
      "widthPx": 130,
      "sillHeightMeters": 0.9,
      "heightMeters": 1.2,
      "confidence": 0.81
    }
  ],
  "rooms": [
    {
      "id": "room_living_001",
      "label": "living_room",
      "name": "客厅",
      "polygon": [[120, 80], [720, 80], [720, 420], [120, 420]],
      "confidence": 0.72
    }
  ],
  "warnings": []
}
```

关键约束：
- 每个门窗必须附着到某条墙。
- 墙体用线段 + 厚度描述，不用像素块描述。
- 所有点先保留在图像坐标系，尺度恢复后再转成米。
- 每个识别对象必须有 `confidence`，低置信结果进入人工校正队列。

## 4. 几何校验与修复

使用确定性几何库处理：

- OpenCV：二值化、线段检测、轮廓提取、mask 生成。
- Shapely：线段吸附、拓扑检查、polygonize、墙体合并。
- networkx：墙线拓扑图，检查连通性和闭合区域。

必须做的修复：
- 近似水平/垂直墙线吸附到统一方向。
- 距离很近的端点合并。
- 重叠墙线合并。
- 开口中心投影到最近墙线。
- 门窗宽度不能超过所在墙段。
- 外轮廓必须闭合；不闭合时找最近端点补边。

输出一个规范化结构：

```json
{
  "unit": "meter",
  "wallHeight": 3.0,
  "defaultWallThickness": 0.1,
  "floorPolygon": [[0, 0], [4.2, 0], [4.2, 3.6], [0, 3.6]],
  "walls": [
    {
      "id": "wall_001",
      "start": [0, 0],
      "end": [4.2, 0],
      "thickness": 0.1,
      "height": 3.0,
      "meshPolicy": "independent_wall"
    }
  ],
  "wallFixtures": [
    {
      "id": "door_001",
      "type": "door",
      "wallId": "wall_001",
      "offset": 1.1,
      "width": 0.85,
      "bottom": 0,
      "height": 2.1,
      "style": "minimal_panel_door"
    },
    {
      "id": "window_001",
      "type": "window",
      "wallId": "wall_002",
      "offset": 0.8,
      "width": 1.5,
      "bottom": 0.9,
      "height": 1.2,
      "style": "simple_framed_window"
    }
  ]
}
```

## 5. 尺度恢复

优先级：

1. OCR 识别图中尺寸标注，比如 `3600`、`3.6m`、`客厅 4.2m`。
2. 用户在图上点选一条已知长度并输入米数。
3. 没有尺度时用相对单位，并提示需要校准。

第一版建议直接让用户输入一个已知长度，这比 OCR 稳定很多。

## 6. 3D 白屋生成

推荐用 Python 生成 GLB：

- `trimesh`：创建 mesh、导出 GLB。
- `shapely`：生成墙体 2D footprint。
- `mapbox_earcut` 或 `triangle`：复杂地面多边形三角化。

建模规则：

1. 地面
   - 根据 `floorPolygon` 生成一个薄地板，厚度 0.03m。

2. 墙体
   - 每条墙根据 `start/end/thickness/height` 独立生成长方体。
   - 层高固定为 3m。
   - 墙厚固定为 0.1m。
   - 每面墙保留独立 `wallId`、独立材质 slot、独立 mesh name，方便后续选中、隐藏、编辑、挂载门窗。
   - 墙之间允许端部轻微重叠或做端点吸附，优先保证视觉闭合。

3. 门窗构件
   - 门窗区域必须在墙体中形成贯通空间，不能只贴在墙的一面。
   - AI 负责识别门窗在墙上的位置、宽度、高度、类型和朝向。
   - 代码会把对应墙体切分成多个墙块，避开门窗区域，避免穿模。
   - 代码在对应墙体中心线生成独立门窗模型，让门窗从墙体两面都可见。
   - 门默认由门框、门板、门套、把手组成。
   - 窗默认由窗框、横竖分隔条、浅蓝半透明玻璃、窗台组成。
   - 门窗组件独立命名，例如 `door_001_frame`、`door_001_panel`、`window_001_glass`。
   - 门窗宽度会被限制在所在墙段内，过宽时自动夹取，避免伸出墙段。

4. 门窗与墙体关系
   - 每个门窗记录 `wallId` 和沿墙偏移 `offset`。
   - 根据墙体方向计算门窗局部坐标系：沿墙方向、墙厚方向、竖直方向。
   - 门窗构件放在墙体厚度中线，门框/窗框贯穿 0.1m 墙厚。
   - 生成前会夹取门窗中心点和宽度，避免门窗与墙端或相邻墙发生明显穿模。

## 7. 调试产物

每次重建都保存：

```text
outputs/floorplans/<scene_id>/
  original.png
  preprocessed.png
  wall_mask.png
  ai_raw.json
  normalized_scene.json
  vector_preview.svg
  whitebox.glb
  report.json
```

`report.json` 记录所有自动修复和不确定项：

```json
{
  "status": "needs_review",
  "warnings": [
    "door_003 confidence below 0.6",
    "outer wall polygon repaired by closing 14px gap"
  ]
}
```

## 8. 后端接口

建议新增：

```http
POST /api/floorplan/reconstruct
GET  /api/floorplan/scenes/{scene_id}
GET  /api/floorplan/scenes/{scene_id}/artifacts/{name}
```

第一版请求：

```json
{
  "image": "data:image/png;base64,...",
  "knownLength": {
    "pixelStart": [120, 80],
    "pixelEnd": [720, 80],
    "meters": 4.2
  },
  "wallHeight": 3.0
}
```

第一版响应：

```json
{
  "sceneId": "floorplan_abc123",
  "status": "succeeded",
  "sceneUrl": "/api/floorplan/scenes/floorplan_abc123",
  "whiteboxGlbUrl": "/api/floorplan/scenes/floorplan_abc123/artifacts/whitebox.glb",
  "vectorPreviewUrl": "/api/floorplan/scenes/floorplan_abc123/artifacts/vector_preview.svg",
  "warnings": []
}
```

## 9. 开发里程碑

### M1：确定性白屋生成

先不接 AI。手写一个 `normalized_scene.json`，生成带独立墙体和美观门窗构件的 GLB。

验收：
- 能生成地面和独立墙体。
- 每面墙都是单独 mesh。
- 所有墙高 3m、墙厚 0.1m。
- 门有门框、门板、门套、把手。
- 窗有窗框、玻璃、分隔条、窗台。
- 门窗区域贯通墙体两面。
- 门窗不会伸出所属墙段。
- GLB 能被 Three.js 加载。

### M2：OpenCV 墙体识别

从样例户型图提取墙体 mask 和候选线段。

验收：
- 输出 `wall_mask.png`。
- 输出候选墙线 JSON。
- 能处理浅色背景、截图压缩、轻微倾斜。

### M3：AI 结构识别

接入多模态 AI，输出 `ai_raw.json`。

验收：
- 墙、门、窗都有置信度。
- 门窗能关联到墙。
- 识别失败时返回 warnings，而不是生成错误房屋。

### M4：几何审校器

把 AI 结果和 OpenCV 候选合并，输出 `normalized_scene.json`。

验收：
- 外墙闭合。
- 墙段吸附和合并稳定。
- 门窗不会漂浮在墙外。

### M5：人工校正闭环

前端展示原图、识别线框、2D 平面、3D 白屋，允许用户拖动墙线、门窗和尺度线。

验收：
- AI 不确定时可人工修。
- 修改后重新生成 GLB。

## 10. 推荐优先实现顺序

1. `whitebox_builder.py`：从规范 JSON 生成 GLB。
2. `schemas.py`：定义 FloorplanScene / Wall / WallFixture。
3. `debug_renderer.py`：输出 2D SVG 预览。
4. `wall_extractor.py`：OpenCV 墙体候选。
5. `ai_parser.py`：多模态 AI 严格 JSON 识别。
6. `geometry_repair.py`：吸附、合并、校验、修复。
7. API router：串起完整链路。

第一步先做白屋生成器，因为这是后续所有识别结果的验收终点。白屋生成器必须先满足固定层高、固定墙厚、独立墙体、独立门窗构件这四个约束。
