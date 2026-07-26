# 适儿化 JSON 契约

## 输入扩展

在既有住宅 JSON 上允许增加：

```json
{
  "meta": {
    "furnitureCatalogPath": "backend/sample_data/furniture/catalog.json"
  },
  "childProfile": {
    "children": [
      {
        "id": "child-1",
        "ageMonths": 18,
        "mobilityStages": ["walking", "climbing"],
        "heightCm": null,
        "behaviors": ["opens-drawers"],
        "allergies": [],
        "accessibilityNeeds": []
      }
    ],
    "caregiverConstraints": [],
    "temporaryVisitors": false
  }
}
```

未知值用 `null`、空数组或 `unknown`，不要省略后让模型猜测。涉及可达性的家具可增加：

```json
{
  "features": {
    "anchored": null,
    "climbable": null,
    "sharpCorners": null,
    "glass": null,
    "looseCord": null,
    "smallDetachableParts": null,
    "heatSource": false,
    "electrical": false,
    "lockable": null,
    "cleanable": null
  }
}
```

## 输出扩展

```json
{
  "childAdaptationAnalysis": {
    "analysisId": "child-safe-001",
    "asOf": "2026-07-26T14:30:00+08:00",
    "profileCompleteness": "partial",
    "layoutCompleteness": "geometry-complete",
    "limitations": [],
    "risks": [],
    "recommendations": [],
    "catalogStatus": "catalog_empty",
    "catalogFurnitureRecommendations": [],
    "proposedSafetyInstallations": [],
    "proposedMajorFurniturePlan": [],
    "appliedChanges": [],
    "rejectedCandidates": [],
    "jsonPatch": [],
    "validation": {
      "valid": true,
      "errors": [],
      "warnings": []
    },
    "reviewTriggers": ["child_starts_climbing"]
  }
}
```

## 风险记录

每项风险包含 `id`、`priority`、`status`、`confidence`、`hazardType`、`evidenceRefs`、`exposure`、`consequence`、`affectedChildIds`、`falsifiers`。

`hazardType` 建议枚举：`tip-over`、`fall`、`entrapment`、`strangulation`、`choking`、`poisoning`、`burn`、`electrical`、`cut-impact`、`drowning`、`egress`、`supervision`、`ergonomics`、`maintenance`。

## 推荐与安装状态

- 普通建议：`applied` 或 `recommended`；
- 安全硬件：`proposedSafetyInstallation`，不得假装已安装；
- 大型家具重排：`proposedMajorFurniturePlan` 且 `requiresUserConfirmation: true`；
- 商品推荐：`proposed-unpurchased`，不得加入现有资产；
- 不安全候选：`rejected`，保留拒绝原因。

所有商品推荐都要含 `productId`、`catalogPath`、`evidenceRefs`、`verificationRequired` 和 `placementEligible`。
