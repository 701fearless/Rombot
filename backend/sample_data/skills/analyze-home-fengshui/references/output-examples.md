# 输出与缺字段示例

## 文字输出模板

```markdown
空间有效性摘要
- 输入达到 geometry-complete；未发现越界或家具重叠。
- 门扇开启区已提供；连续通道仅做二维近似校验。

优先建议
1. P1｜书桌背门且椅后紧邻主通道（置信度 0.94）
   最小动作：将书桌顺时针转 15°，不改变中心位置。
   现实收益：能看到入口，减少背后来人造成的干扰。
   传统解释：增加“有靠”和对入口的掌控感。
   JSON：已更新 desk-1.rotationDeg；门扇、碰撞、通道校验通过。
   观察：连续使用 7 天，记录专注和被打断感是否改善。

时间型小调整
- 当前为夏季近似阶段。在 entry-console-1 上使用现有浅色陶瓷托盘集中钥匙，有效期 30 天；这是季节性和五行象征辅助，不代表吉凶预测。

家具大改候选
- 无。

JSON 变更摘要
- 已应用 1 项；仅建议 1 项；拒绝 0 项。
```

## 自动回写示例

对 `small-movable` 书桌完成候选旋转、边界、碰撞、门扇和通道校验后，可把 `rotationDeg` 从 0 改为 15，并记录：

```json
[
  { "op": "test", "path": "/furniture/4/id", "value": "desk-1" },
  { "op": "replace", "path": "/furniture/4/footprint/rotationDeg", "value": 15 }
]
```

## 数据不足示例

```json
{
  "rooms": [{ "id": "bedroom", "type": "bedroom" }],
  "furniture": [{ "id": "bed", "type": "bed", "roomId": "bedroom", "relativePosition": "faces door" }]
}
```

正确处理：输出“床可能处于门线，但没有几何，置信度低”；建议确认床尾中心与门中心线；给不带坐标的轻量候选；不移动床、不新增屏风、不声称校验通过；`inputCompleteness` 为 `relational`。

## 家具大改候选示例

只有床侵入卧室唯一高频通道和门扇区、两种微移均无解时，才可能出现：

```json
{
  "id": "major-bed-reorientation-1",
  "state": "proposed",
  "requiresUserConfirmation": true,
  "reason": "当前床位同时侵入门扇开启区和唯一通道，局部微移无可行解",
  "evidenceRefs": ["/rooms/2/doors/0/swingPolygon", "/furniture/5/footprint"],
  "lightweightAlternativesEvaluated": [
    { "action": "横移 0.20 m", "result": "仍侵入门扇区" },
    { "action": "旋转 15°", "result": "通道净宽不足" }
  ],
  "affectedFurnitureIds": ["bed-1", "nightstand-1"],
  "validationPreview": { "valid": true, "errors": [] },
  "jsonPatch": [],
  "note": "未应用；确认后才生成实际坐标变更"
}
```

床头朝向、流年方位或单一传统规则不足以触发此方案。

## 拒绝候选示例

```json
{
  "id": "candidate-entry-plant",
  "state": "rejected",
  "action": "在入户门内侧放置植物",
  "reason": "占地侵入门扇区并使净通道低于 0.80 m",
  "rule": "door-and-egress-clearance",
  "fallback": "不新增物件；整理现有玄关托盘并增强照明"
}
```
