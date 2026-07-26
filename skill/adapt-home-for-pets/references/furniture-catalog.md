# 适宠化家具目录选品

## 目录定位

依次使用用户指定路径、`meta.furnitureCatalogPath`、`backend/sample_data/furniture/catalog.json`。只读取 JSON，格式参照项目 Schema。

## 筛选顺序

1. 排除缺货和 `petSuitability.species` 不包含目标物种的商品；
2. 匹配实际问题与行为，不按品种刻板选择；
3. 优先有完整尺寸、稳定/承重信息、耐抓/耐咬、可洗、防滑、可替换外套和材料声明的商品；
4. 检查食水、排泄、休息、活动、躲藏、清洁或家具保护用途；
5. 输出 1-2 件功能互补商品。

“宠物家具”标题不能替代物种、体型、承重、材料、稳定和耐久核验。未知字段必须进入 `verificationRequired`。

## 命令

```powershell
python scripts/recommend_furniture.py <catalog.json> --domain pet --species <物种> --need <风险或场景> --max-items 2 --pretty
```

## 回写

商品状态为 `proposed-unpurchased`，包含商品 ID、JSON Pointer、物种匹配证据、推荐理由、核验项、尺寸可落位状态和价格。目录空时数组保持空并写 `catalog_empty`。

不自动购买、不替换家具、不把商品写成已摆放。用户确认后才创建资产和坐标，并重新验证物理、安全、退路与资源分区。
