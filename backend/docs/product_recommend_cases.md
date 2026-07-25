# 商品识别与推荐案例

基于本地 mock 商品库（`sample_data/products/catalog.json`）与 Ark 视觉属性抽取（无 `ARK_API_KEY` 或无图时回退 mock）。

## 流程

```text
feed detect / select-object
  → POST /api/product/recognize（属性）
  → POST /api/product/recommend（同款/相似 + 价格 + sizeFit）
  → 可选：将 size_m 作为 PlacementCandidate 走 /api/room/placement-check
```

一键联调：`POST /api/product/recognize-and-recommend`

`select-object` 响应可选字段 `productHints`（不破坏旧字段），提示前端可调推荐 API。

## 案例 1：沙发标签识别 + 推荐（mock）

### 输入 — recognize

```http
POST /api/product/recognize
```

```json
{
  "label": "sofa",
  "objectId": "obj_sofa_001"
}
```

### 输出 — recognize（示例）

```json
{
  "category": "sofa",
  "name": "布艺沙发",
  "attributes": {
    "color": "米色",
    "material": "布艺",
    "style": "现代",
    "extra": {}
  },
  "estimatedSize_m": [2.0, 0.85, 0.9],
  "sizeConfidence": "low",
  "queryTags": ["sofa", "米色", "布艺", "现代", "beige", "fabric"],
  "source": "mock"
}
```

### 输入 — recommend

```http
POST /api/product/recommend
```

```json
{
  "query": {
    "category": "sofa",
    "name": "布艺沙发",
    "attributes": { "color": "米色", "material": "布艺", "style": "现代", "extra": {} },
    "estimatedSize_m": [2.0, 0.85, 0.9],
    "sizeConfidence": "low",
    "queryTags": ["sofa", "beige", "fabric", "modern"],
    "source": "mock"
  },
  "budget": 2000,
  "preferSame": true,
  "limit": 5,
  "candidate": {
    "id": "slot_sofa",
    "label": "sofa",
    "name": "沙发空位",
    "position": [1.2, 0.0, 2.1],
    "rotation": [0.0, 0.0, 0.0],
    "size": [2.0, 0.9, 0.9]
  }
}
```

### 输出 — recommend（摘要示例）

```json
{
  "query": { "...": "同上" },
  "items": [
    {
      "productId": "sku_sofa_001",
      "title": "三人米色布艺沙发",
      "matchType": "same",
      "score": 0.91,
      "price": 1299,
      "currency": "CNY",
      "size_m": [2.0, 0.85, 0.9],
      "imageUrl": "/sample_data/videos/sample.png",
      "glbUrl": "/sample_data/models/sofa.glb",
      "buyUrl": null,
      "reason": "同品类「sofa」；标签重合：sofa、beige、fabric；价格¥1299在预算内",
      "sizeFit": "fits"
    }
  ]
}
```

`sizeFit`：`fits` / `tight` / `unknown`。有 `candidate` 或 `scene` 时按尺寸粗判。

## 案例 2：cropUrl / image

有 crop 时优先走 Ark 视觉（需 `ARK_API_KEY`）：

```json
{
  "cropUrl": "/outputs/<frameId>/<objectId>/crop.png",
  "label": "sofa"
}
```

或直接传 `image` data URL。无 key / 调用失败时自动 mock。

## 本地脚本

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\test_product_recommend.py
```
