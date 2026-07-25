# 离线商品视觉检索（CLIP + FAISS）

不接在线电商、不改现有 `/api/product`。先在本地验证「截图/crop → TopK 相似 IKEA 商品」。

## 数据

- 小样本（旧）：[crawlfeeds/IKEA-Home-Decor-Furniture-Dataset](https://huggingface.co/datasets/crawlfeeds/IKEA-Home-Decor-Furniture-Dataset)（约 464 条，偏 Home Decor）
- **全量推荐**：[jeffreyszhou/ikea-us-products-2025](https://huggingface.co/datasets/jeffreyszhou/ikea-us-products-2025)（约 3 万条 US 全品类，含沙发/桌/床等；图片约 5–8GB）
- 本地目录：`backend/data/product_index/`（图片与索引默认不入库）

### 下载全量 US 目录

```powershell
# 国内建议镜像
$env:HF_ENDPOINT='https://hf-mirror.com'
# 推荐：每个品类抽 10%（约 3k 条，快很多）
python scripts\product_retrieval\download_ikea_us_full.py --sample-ratio 0.1 --workers 20
# 全量（较久，数 GB）
python scripts\product_retrieval\download_ikea_us_full.py --workers 20
# 然后重建索引
python scripts\product_retrieval\build_index.py --pretrained data\product_index\ViT-B-32.pt
```

## 环境说明

项目固定使用 Conda `ml2025`，不要创建额外虚拟环境：

```powershell
conda activate ml2025
cd F:\DREAME\Qiuliying\lucky\backend
python -m pip install -r requirements-product-retrieval.txt
```

`download_ikea.py` 只用 httpx/Pillow，同样在 `ml2025` 中执行。

## 三步

### 1) 下载 CSV + 商品图

```powershell
python scripts\product_retrieval\download_ikea.py
# 或先小样本：
python scripts\product_retrieval\download_ikea.py --limit 50
```

产出：

- `data/product_index/ikea_raw.csv`
- `data/product_index/catalog.jsonl`
- `data/product_index/images/*.jpg`

### 2) OpenCLIP 编码 + FAISS 索引

首次会下载 ViT-B-32/openai 权重。若 Hugging Face 直连失败：

```powershell
# 用 HF 镜像把权重落到本地（约 600MB），再指向该文件
$url = 'https://hf-mirror.com/timm/vit_base_patch32_clip_224.openai/resolve/main/open_clip_pytorch_model.bin'
python -c "import httpx; from pathlib import Path; p=Path(r'data/product_index/ViT-B-32.pt'); r=httpx.get('$url', follow_redirects=True, timeout=600.0); r.raise_for_status(); p.write_bytes(r.content); print(p, p.stat().st_size)"
python scripts\product_retrieval\build_index.py --pretrained data\product_index\ViT-B-32.pt
```

也可设 `$env:HF_ENDPOINT='https://hf-mirror.com'` 后直接跑 `build_index.py`（部分环境仍可能因 Hub HEAD 校验失败）。

```powershell
python scripts\product_retrieval\build_index.py
# 或（本地权重）：
python scripts\product_retrieval\build_index.py --pretrained data\product_index\ViT-B-32.pt
```

产出：

- `embeddings.npy`
- `index.faiss`（若装了 faiss；否则检索自动回退 numpy 余弦）
- `catalog_indexed.jsonl`
- `meta.json`

说明：Windows 路径含中文时，脚本用 `faiss.serialize_index` 读写，避免 FAISS C++ FileIO 失败。
### 3) 用现有 crop 检索

```powershell
$env:PYTHONIOENCODING='utf-8'   # 避免 Windows 控制台 GBK 打印商品名报错
python scripts\product_retrieval\search.py `
  --image outputs\1_000003\obj_chandelier_001_002_crop.jpg `
  --top-k 10 --pretrained data\product_index\ViT-B-32.pt
```

JSON 输出：

```powershell
python scripts\product_retrieval\search.py `
  --image outputs\1_000003\obj_chandelier_001_002_crop.jpg `
  --top-k 5 --pretrained data\product_index\ViT-B-32.pt --json
```

## 预期效果

- 吊灯 / 镜子 / 花瓶等装饰类 crop：容易对上数据集类别  
- 沙发 / 茶几：该 HF 样本偏装饰，相似度可能一般（后续可换更大家具库）

## Demo：视频物体 → 本地商品缓存

对 `vedios/<id>/deduplicated/*/crop.jpg` 离线批匹配，写入 `outputs/videos/<id>/product_matches.json`（展示只读缓存，不现场 CLIP）：

```powershell
$env:PYTHONIOENCODING='utf-8'
python scripts\product_retrieval\batch_match_products.py `
  --videos-root ..\vedios --video-ids 1,2,3,4,5 --top-k 3 `
  --pretrained data\product_index\ViT-B-32.pt
```

- API：`GET /api/video/{videoId}/product-matches`
- 静态商品图：`/product_index/images/<id>.jpg`
- 页面：`/static/pipeline-test.html` 选中物体后展示 Top3

说明：HF Home Decor 库偏镜子/画框，沙发/茶几可能对上装饰类——demo 按视觉相似展示。

## 下一步（未做）

接到 `/api/product/recommend`：Vision 属性 + CLIP Top20 + Shopping Agent → Top3。
