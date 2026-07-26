# 适儿化家具目录选品

## 目录定位

依次使用用户指定路径、`meta.furnitureCatalogPath`、`backend/sample_data/furniture/catalog.json`。只读取 JSON。商品格式参照 `backend/sample_data/furniture/catalog.schema.json`。

## 筛选顺序

1. 排除缺货、年龄不匹配、JSON 标注高小零件/夹困/绳线/攀爬风险的商品；
2. 匹配本次最高风险和房间用途；
3. 优先有完整尺寸、倾倒/承重信息、圆角、可洗、防滑和可追溯认证的商品；
4. 再比较照护便利、成长适配、清洁、家具保护、价格和风格；
5. 输出 1-2 件功能互补商品。

未知字段不等于安全。标题含“儿童/婴儿”也不能替代年龄、尺寸、间隙、承重、固定、材料和认证核验。

## 命令

```powershell
python scripts/recommend_furniture.py <catalog.json> --domain child --age-months <月龄> --need <风险或场景> --max-items 2 --pretty
```

## 输出与回写

每件包含商品 ID、标题、JSON Pointer、匹配问题、证据理由、未知核验项、尺寸可落位状态和价格。状态为 `proposed-unpurchased`。目录空时返回 `catalog_empty`，商品数组保持空。

不自动购买、不替换现有家具、不把商品写成已经摆放。用户确认采用后才创建资产和坐标，并重新运行物理与适儿风险审计。
