import os
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

router = APIRouter()

# 上传文件存储目录
UPLOAD_DIR = Path("outputs") / "uploaded_furniture"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class FurnitureUploadResponse(BaseModel):
    id: str
    name: str
    glbUrl: str
    sizeBytes: int
    message: str


class FurnitureItem(BaseModel):
    id: str
    name: str
    glbUrl: str


# 内存存储（生产环境应使用数据库）
uploaded_furniture: list[FurnitureItem] = []


@router.post("/upload", response_model=FurnitureUploadResponse)
async def upload_furniture_glb(file: UploadFile = File(...)):
    """上传家具 GLB 模型文件"""
    # 验证文件类型
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    
    filename = file.filename.lower()
    if not (filename.endswith(".glb") or filename.endswith(".gltf")):
        raise HTTPException(status_code=400, detail="只支持 .glb 或 .gltf 格式的文件")
    
    # 限制文件大小 (最大 50MB)
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过 50MB")
    
    # 生成唯一ID和存储路径
    furniture_id = f"furniture_{uuid.uuid4().hex[:12]}"
    safe_name = file.filename.replace(" ", "_").replace("/", "_")
    stored_name = f"{furniture_id}_{safe_name}"
    storage_path = UPLOAD_DIR / stored_name
    
    # 写入文件
    with open(storage_path, "wb") as f:
        f.write(content)
    
    # 构建访问URL
    glb_url = f"/outputs/uploaded_furniture/{stored_name}"
    
    # 创建家具记录
    item = FurnitureItem(
        id=furniture_id,
        name=file.filename.rsplit(".", 1)[0],
        glbUrl=glb_url,
    )
    uploaded_furniture.append(item)
    
    return FurnitureUploadResponse(
        id=item.id,
        name=item.name,
        glbUrl=glb_url,
        sizeBytes=len(content),
        message="上传成功",
    )


@router.get("/list", response_model=list[FurnitureItem])
async def list_uploaded_furniture():
    """获取已上传的家具列表"""
    return uploaded_furniture


@router.delete("/{furniture_id}")
async def delete_furniture(furniture_id: str):
    """删除已上传的家具"""
    global uploaded_furniture
    
    item = None
    for i, f in enumerate(uploaded_furniture):
        if f.id == furniture_id:
            item = f
            break
    
    if not item:
        raise HTTPException(status_code=404, detail="家具不存在")
    
    # 删除物理文件
    filename = item.glbUrl.split("/")[-1]
    file_path = UPLOAD_DIR / filename
    if file_path.exists():
        file_path.unlink()
    
    # 从列表移除
    uploaded_furniture = [f for f in uploaded_furniture if f.id != furniture_id]
    
    return {"message": "删除成功", "id": furniture_id}
