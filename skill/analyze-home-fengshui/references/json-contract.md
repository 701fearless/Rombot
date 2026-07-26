# JSON 输入与回写契约

## 目录

1. 设计目标
2. 推荐输入模型
3. 字段容错与最低输入
4. 家具特征建议
5. 回写模型
6. JSON Patch 约定
7. 数据完整度等级

## 设计目标

接受项目已有 JSON，不强迫用户先迁移格式。先映射到内部规范模型，再在原结构上做最小改动。保留未知字段，不重命名用户字段，不改变坐标含义。

## 推荐输入模型

```json
{
  "schemaVersion": "1.0",
  "meta": {
    "timestamp": "2026-07-26T14:30:00+08:00",
    "timezone": "Asia/Shanghai",
    "units": "m",
    "coordinateSystem": {
      "origin": "southwest",
      "xAxis": "east",
      "yAxis": "north",
      "rotationDirection": "clockwise",
      "northAngleDeg": 0
    },
    "facingDeg": null
  },
  "shell": {
    "boundary": [[0, 0], [10, 0], [10, 8], [0, 8]],
    "walls": [],
    "columns": [],
    "beams": []
  },
  "rooms": [{
    "id": "bedroom-1",
    "type": "bedroom",
    "polygon": [[0, 4], [4, 4], [4, 8], [0, 8]],
    "doors": [{
      "id": "door-bedroom-1",
      "segment": [[4, 4.5], [4, 5.4]],
      "swingPolygon": [[3.1, 4.5], [4, 4.5], [4, 5.4]]
    }],
    "windows": [],
    "fixedFixtures": []
  }],
  "furniture": [{
    "id": "bed-1",
    "type": "bed",
    "roomId": "bedroom-1",
    "movability": "large-movable",
    "footprint": {
      "shape": "rectangle",
      "x": 1.6,
      "y": 6.4,
      "width": 1.8,
      "depth": 2.0,
      "rotationDeg": 0
    },
    "orientationDeg": 180,
    "features": {
      "headSide": "north",
      "hasSolidHeadboard": true,
      "reflective": false,
      "electrical": false,
      "water": false
    }
  }],
  "circulationPaths": [],
  "constraints": {
    "minPassage": 0.8,
    "bedSideClearance": 0.55,
    "immutableIds": [],
    "pets": [],
    "children": false,
    "accessibility": null,
    "rental": true,
    "budget": "low"
  }
}
```

所有点既可写成 `[x, y]`，也可写成 `{ "x": 1, "y": 2 }`。一个文件内保持一致。

## 字段容错与最低输入

### 仅能输出文字建议

最低需要房间类型、主要门口关系、家具类型和相对位置描述。没有数值几何时，不回写坐标，不新增占地实体。

### 可以自动回写轻量实体

至少需要明确单位、房间闭合多边形、待移动或新增物件的占地尺寸、相关门窗开启区或安全缓冲区、已有家具占地、物件可移动性和最小通道约束。

### 可以分析罗盘方位

还需要北向角、角度零点和顺逆时针定义。只有“左上角是北”之类模糊描述时，将方位置信度设为低，不做自动落位。

## 家具特征建议

未来扩充 JSON 时优先增加以下特征。未知值使用 `null` 或 `unknown`，不要让模型猜测。

| 类别 | 推荐字段 | 用途 |
| --- | --- | --- |
| 通用 | `movability`, `weightClass`, `height`, `useFrequency` | 判断能否轻量调整 |
| 占地 | `shape`, `x`, `y`, `width`, `depth`, `rotationDeg` | 边界、碰撞和通道校验 |
| 朝向 | `frontSide`, `headSide`, `seatFacingDeg` | 床头、桌椅和沙发分析 |
| 支撑 | `backing`, `hasSolidHeadboard`, `wallGap` | 判断“有靠” |
| 风险 | `electrical`, `water`, `heatSource`, `flammable` | 水火电与热源安全 |
| 表面 | `reflective`, `sharpCorners`, `transparent` | 镜面、尖角和暴露感 |
| 安装 | `mountType`, `loadKg`, `supportSurfaceId` | 区分落地、桌面、墙挂 |
| 环境 | `lightNeed`, `petSafe`, `childSafe` | 植物和小物件安全 |
| 状态 | `clutter`, `broken`, `leaking`, `inUse` | 优先修复和清理 |

推荐 `movability` 枚举：`fixed`、`large-movable`、`small-movable`、`decor`、`unknown`。固定设施即使现实可拆也一律不由本 Skill 修改。

## 回写模型

在顶层增加：

```json
{
  "fengshuiAnalysis": {
    "analysisId": "fs-20260726T143000+0800",
    "asOf": "2026-07-26T14:30:00+08:00",
    "inputCompleteness": "geometry-complete",
    "methods": ["physical", "form", "timing-year-level"],
    "limitations": [],
    "issues": [],
    "recommendations": [],
    "catalogFurnitureRecommendations": [],
    "catalogStatus": "ok",
    "appliedChanges": [],
    "proposedMajorFurniturePlan": [],
    "rejectedCandidates": [],
    "jsonPatch": [],
    "validation": {
      "valid": true,
      "errors": [],
      "warnings": [],
      "validator": "validate_layout.py"
    }
  }
}
```

`catalogFurnitureRecommendations` 中每件商品至少包含 `productId`、`title`、`category`、`state: proposed-unpurchased`、`catalogPath`、`evidenceRefs`、`reasons`、`verificationRequired`、`placementEligible` 和可选 `placementPreview`。目录为空时保持数组为空，并把 `catalogStatus` 写为 `catalog_empty`；不得用占位名称伪造商品。

每个问题记录 `id`、`priority`、`status`、`confidence`、`method`、`evidenceRefs`、`summary` 与 `falsifiers`。每条建议记录问题引用、应用状态、动作层级、原因、成本、工作量、可逆性、置信度、JSON 路径和验证方法。

示例：

```json
{
  "id": "rec-bed-micro-shift",
  "issueIds": ["issue-bed-door-line"],
  "state": "applied",
  "actionClass": "redirect",
  "action": "将床沿墙横移 0.20 m，保持床头靠墙",
  "reason": "减弱门线直冲并保留通道",
  "cost": "none",
  "effort": "low",
  "reversibility": "high",
  "confidence": 0.9,
  "jsonRefs": ["/furniture/0/footprint/x"],
  "verification": "门扇可完全开启，床侧净距不低于约束值"
}
```

## JSON Patch 约定

使用 RFC 6902 的 `add`、`remove`、`replace`、`move`、`copy`、`test` 语义。优先在修改前添加 `test`，防止索引变化误改对象。数组索引不稳定时先按 ID 定位。

```json
[
  { "op": "test", "path": "/furniture/0/id", "value": "chair-1" },
  { "op": "replace", "path": "/furniture/0/footprint/rotationDeg", "value": 15 }
]
```

不得用 Patch 修改墙体、门窗、固定设施、厨卫区域或管线相关路径。检测到此类路径时直接拒绝。

## 数据完整度等级

- `text-only`: 仅描述，无可靠几何；只给文字。
- `relational`: 有房间与相对关系；可分析，不落坐标。
- `geometry-partial`: 有坐标但缺尺寸或开启区；只改非占地状态。
- `geometry-complete`: 可做边界、碰撞和局部通行校验；允许轻量回写。
- `site-verified`: 另有现场测量或图像佐证；仍不代表工程安全认证。
