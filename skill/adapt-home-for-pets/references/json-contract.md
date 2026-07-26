# 适宠化 JSON 契约

## 输入扩展

```json
{
  "meta": {
    "furnitureCatalogPath": "backend/sample_data/furniture/catalog.json"
  },
  "petProfile": {
    "pets": [
      {
        "id": "pet-1",
        "species": "cat",
        "ageYears": 3,
        "weightKg": null,
        "sizeClass": "medium",
        "mobility": ["jumps", "climbs"],
        "behaviors": ["scratches-sofa"],
        "healthConstraints": [],
        "resourcePreferences": []
      }
    ],
    "multiPetConcerns": [],
    "caregiverConstraints": []
  }
}
```

推荐物种值使用明确英文或项目枚举，例如 `cat`、`dog`、`rabbit`、`bird`。不要用“毛孩子”替代机器可筛选物种。

家具和设施可增加：

```json
{
  "features": {
    "anchored": null,
    "climbable": null,
    "scratchTarget": null,
    "chewable": null,
    "washable": null,
    "waterproof": null,
    "antiSlip": null,
    "looseCord": null,
    "toxicToSpecies": [],
    "containsFood": false,
    "containsChemicals": false
  }
}
```

## 输出扩展

```json
{
  "petAdaptationAnalysis": {
    "analysisId": "pet-safe-001",
    "asOf": "2026-07-26T14:30:00+08:00",
    "profileCompleteness": "partial",
    "layoutCompleteness": "geometry-complete",
    "limitations": [],
    "risks": [],
    "recommendations": [],
    "resourceZones": [],
    "catalogStatus": "catalog_empty",
    "catalogFurnitureRecommendations": [],
    "proposedSafetyInstallations": [],
    "proposedMajorFurniturePlan": [],
    "appliedChanges": [],
    "rejectedCandidates": [],
    "jsonPatch": [],
    "validation": { "valid": true, "errors": [], "warnings": [] },
    "reviewTriggers": ["new_pet_added"]
  }
}
```

## 风险类型

建议使用：`escape`、`fall`、`tip-over`、`electrical-chew`、`foreign-body`、`toxic-exposure`、`burn`、`slip`、`entrapment`、`food-hygiene`、`waste-hygiene`、`resource-conflict`、`human-egress`、`furniture-damage`。

风险记录包含 `priority`、`status`、`confidence`、`speciesRefs`、`evidenceRefs`、`exposure`、`consequence` 和 `falsifiers`。

## 状态

- 已验证轻量变化：`applied`；
- 缺资料或待现场确认：`recommended`；
- 防逃与固定安装：`proposedSafetyInstallation`；
- 大件重排：`proposedMajorFurniturePlan`；
- 商品推荐：`proposed-unpurchased`；
- 物种不匹配或新增风险：`rejected`。

商品推荐必须包含 `productId`、`catalogPath`、`evidenceRefs`、`verificationRequired`、`placementEligible` 和物种匹配证据。
