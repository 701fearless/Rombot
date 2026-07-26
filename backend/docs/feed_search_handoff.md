# Feed 搜同款 / 一键室用 — 交接文档

> 更新时间：2026-07-26  
> 范围：抖音式 Feed 暂停识物 → 搜同款商品卡 → 详情内嵌 → 一键放进 3D 空间；本地缓存与预热。

---

## 1. 产品行为（当前）

1. Feed 暂停视频 → `/api/feed/detect` 出家具 Tag  
2. 点击 Tag → 底部弹出商品卡（不再直接进 3D）  
3. 商品卡展示同款前 4 个；顶部文案 + **一键室用**  
4. 点商品 → **详情在卡片内展开**（不跳 `shop.html`）  
5. **一键室用** = 旧版点 Tag 逻辑：拉预建 GLB → `setPendingAsset` → 跳转 `/space`  
6. 卡片上**不显示匹配度百分比**

---

## 2. 搜同款检索链路

与打标识图页（`static/image-search.html`）对齐：

```
优先：GET /api/shop/feed-clip-cache?videoId=&candidateId=
未命中：
  1) POST /api/shop/resolve-reference  → generated/*/reference
  2) POST /api/video/clip-search
       cropUrl = referenceUrl
       textWeight ≈ 0.35（有 label 时）
       hint.label = 物体 label（如 rug）
       persist = true
  3) 落盘本地缓存（见下）
失败兜底：frontend/src/data/feedProductMatches.ts 写死 demo
```

前端入口：`frontend/src/services/backend.ts` → `searchFeedProducts`  
UI：`frontend/src/components/ProductRecognizeSheet.tsx`  
接入页：`frontend/src/pages/FeedPage.tsx`

---

## 3. 本地缓存（可无完整宜家库跑演示）

CLIP 成功后自动物化到：

| 路径 | 内容 |
|------|------|
| `outputs/shop/feed_clip_cache/<videoId>/<candidateId>.json` | 该物体 Top4 结果 |
| `static/mock-products/<productId>.jpg` | 商品图副本 |
| `outputs/shop/products/<productId>.json` | 商品详情 stub |

- API：`GET/PUT /api/shop/feed-clip-cache`  
- 实现：`app/services/shop_store.py`（`save_feed_clip_cache` / `localize_results_for_offline`）  
- `clip-search` persist 时会写上述缓存，并返回本地 `/static/mock-products/...` 图片 URL  

**演示机**只要带上：`feed_clip_cache` + `mock-products` + `products` stub，即可在不传完整 `data/product_index` 的情况下点 Tag 出同款（缓存命中时不跑 CLIP）。

---

## 4. 预热脚本（不必手点每个 Tag）

```bash
cd backend
# 需先启动 uvicorn :8010
python -u scripts/product_retrieval/warmup_feed_clip_cache.py --videos 1,2,3,4,5,6
# 强制重跑：
python -u scripts/product_retrieval/warmup_feed_clip_cache.py --force
```

- 脚本：`scripts/product_retrieval/warmup_feed_clip_cache.py`  
- 日志：`outputs/shop/warmup_feed_clip_cache.log`  
- 逻辑：遍历 `REFERENCE_VIDEOS_ROOT/<id>/generated/*/reference` → resolve → clip-search(persist)  
- 已有缓存会跳过  

**状态（2026-07-26）**：视频 1–6 共 94 个候选已预热完成（含视频 1 两个 plant 失败后补跑）。

---

## 5. 关键配置与依赖

| 项 | 说明 |
|----|------|
| Backend | `http://127.0.0.1:8010`（`uvicorn app.main:app`） |
| Frontend | `http://127.0.0.1:5173`，Vite 代理 `/api` `/outputs` `/static` `/vedios` 等 |
| `REFERENCE_VIDEOS_ROOT` | `.env` 中指向含 `generated/*/reference` 的 videos 根（打标管线输出） |
| `vedios/` | 暂停裁剪/去重图来源之一；reference 仍在 generated |
| CLIP | `.venv-retrieval` + `data/product_index`（**仅冷启动/首次检索需要**） |

注意：`main.py` SPA 兜底不得吞掉 `/api/*`（已排除），否则会出现 HTML 当 JSON 解析错误。

---

## 6. 主要改动文件

**前端**

- `frontend/src/pages/FeedPage.tsx` — Tag 开商品卡；一键室用进 `/space`  
- `frontend/src/components/ProductRecognizeSheet.tsx` — 商品卡 / 内嵌详情 / CTA  
- `frontend/src/services/backend.ts` — `searchFeedProducts`（缓存 → reference CLIP）  
- `frontend/src/data/feedProductMatches.ts` — 失败兜底写死数据  
- `frontend/src/types/shop.ts` / `scene.ts` — 类型补充  
- `frontend/src/app.css` — 商品卡样式  

**后端**

- `app/routers/shop.py` — `feed-clip-cache`、`resolve-reference`  
- `app/routers/video.py` — clip-search persist 时写 feed 缓存  
- `app/services/shop_store.py` — 物化图片与缓存读写  
- `app/services/reference_resolver.py` — reference 匹配（既有）  
- `app/main.py` — API 路径不被 SPA HTML 吞掉  
- `scripts/product_retrieval/warmup_feed_clip_cache.py` — 批预热  

---

## 7. 本地自测清单

1. 启 backend `8010` + frontend `5173`  
2. 暂停视频 1 → 点吊灯 Tag → 应几乎秒出缓存同款（有 `feed_clip_cache`）  
3. 点商品 → 详情在卡片内，不新开页  
4. 点「一键室用」→ 进入户型 3D（需该物体有预建 GLB）  
5. 删某个 `feed_clip_cache/...json` 再点 → 会走 reference+CLIP（需索引与 venv），并重新落盘  

---

## 8. 已知注意点

- **冷检索慢**：CLIP 首次约十几秒；预热后应走磁盘缓存。  
- **预热别和手测抢死后端**：大批量 warmup 时尽量别同时狂点 Feed；backend 挂掉会出现连不上 / 假 500。  
- **品类错配**：纯图 CLIP 可能偏；现用 `hint.label + textWeight=0.35` 纠偏。  
- **兜底写死数据**：仅 API/CLIP 全失败时使用，品类已对齐但质量低于真实 CLIP。  
- **一键室用**：依赖 detect 物体可 `getPrebuiltAsset`；无 GLB 会 toast 失败。  

---

## 9. 建议后续（未做）

- 把 `feed_clip_cache` + `mock-products` 打成演示包随仓库/网盘分发  
- warmup 写入 CI 或 `npm/pnpm` 一键脚本  
- 详情字段补全（尺寸多来自 catalog，stub 里常为空）  
- 内存缓存与磁盘缓存的失效策略（改 reference 后需 `--force` 预热）  
