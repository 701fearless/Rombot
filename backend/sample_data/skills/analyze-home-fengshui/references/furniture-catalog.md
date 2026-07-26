# 家具 JSON 目录选品规则

## 目录来源

按以下优先级定位目录：

1. 用户明确提供的商品 JSON 路径；
2. 户型 JSON 的 `meta.furnitureCatalogPath`；
3. 项目默认 `backend/sample_data/furniture/catalog.json`。

只读取 JSON，不从商品图片、标题常识、网页或模型记忆补全缺失属性。目录结构优先遵循 `backend/sample_data/furniture/catalog.schema.json`，也允许顶层直接是数组，或使用 `furniture`/`products` 数组。

## 推荐数量

- 目录有合格候选时，推荐 1 到 2 件，不多于 2 件。
- 目录为空时，输出 `catalog_empty` 和待补字段，不虚构商品。
- 没有适用候选时，输出 `no_eligible_products`，说明筛除原因。
- 两件商品应解决不同问题；除非用户明确要比较同品类，不推荐功能重复的两件。

## 证据规则

每件推荐必须包含商品 ID、标题、品类、目录路径、JSON Pointer、匹配问题、选择原因、缺失核验项、尺寸可落位状态和价格引用（若有）。

只能把 `verified` 声明写成“已验证”。`manufacturer`、`seller` 与 `unverified` 分别写明来源等级。缺少圆角、承重、尺寸、环保、阻燃、耐抓、可洗等字段时必须说“未知/购买前核验”，不得改写成肯定特征。

## 执行

```powershell
python scripts/recommend_furniture.py <catalog.json> --domain fengshui --need <问题关键词> --max-items 2 --pretty
```

需要多个关键词时重复 `--need`。脚本结果只是有证据的排序，不替代空间判断。

## 布局回写

把推荐写入 `fengshuiAnalysis.catalogFurnitureRecommendations`，状态固定为 `proposed-unpurchased`。推荐商品不等于现有家具：

- 不把它直接加入 `furniture` 或 `placements`；
- 不删除现有家具为它腾位；
- 尺寸完整时可以生成 `placementPreview`，但仍不应用；
- 尺寸不全时只给适合的房间/区域和必须补齐的数据；
- 用户确认购买或明确要求采用后，才新建资产与落位记录并重新做物理校验。
