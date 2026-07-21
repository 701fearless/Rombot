from app.schemas import DetectedObject, ObjectAnalysis, SelectObjectResponse, SelectedAsset
from app.services.model3d.base import Model3DProvider


GLB_BY_LABEL = {
    "sofa": "/sample_data/models/sofa.glb",
    "coffee_table": "/sample_data/models/coffee_table.glb",
    "chandelier": "/sample_data/models/chandelier.glb",
    "rug": "/sample_data/models/rug.glb",
}

DISPLAY_NAME_BY_LABEL = {
    "sofa": "浅色布艺沙发",
    "coffee_table": "圆角茶几",
    "chandelier": "客厅吊灯",
    "rug": "暖色地毯",
}

ANALYSIS_BY_LABEL = {
    "sofa": ObjectAnalysis(
        summary="浅色低矮沙发会降低空间压迫感，适合小户型客厅。",
        placementAdvice="建议靠墙摆放，前方保留 40-60cm 通行距离。",
    ),
    "coffee_table": ObjectAnalysis(
        summary="圆角茶几能弱化碰撞感，适合需要柔和动线的客厅。",
        placementAdvice="建议与沙发保持 40-50cm 距离，避免压缩通行空间。",
    ),
    "chandelier": ObjectAnalysis(
        summary="吊灯是空间视觉中心，会强化客厅的聚合感。",
        placementAdvice="建议位于茶几或客厅中心上方，避免过低影响视线。",
    ),
    "rug": ObjectAnalysis(
        summary="地毯可以把沙发区聚合成一个稳定的交流区域。",
        placementAdvice="建议至少压住沙发前脚，让视觉边界更完整。",
    ),
}


class MockModel3DProvider(Model3DProvider):
    async def generate_asset(
        self,
        frame_id: str,
        detected_object: DetectedObject,
        image_url: str | None = None,
    ) -> SelectObjectResponse:
        _ = image_url
        task_id = f"asset_{frame_id}_{detected_object.id}"
        label = detected_object.label
        return SelectObjectResponse(
            taskId=task_id,
            status="succeeded",
            object=SelectedAsset(
                id=detected_object.id,
                label=label,
                name=DISPLAY_NAME_BY_LABEL.get(label, detected_object.name),
                bbox=detected_object.bbox,
                cropUrl=f"/outputs/{task_id}/crop.png",
                maskUrl=f"/outputs/{task_id}/mask.png",
                glbUrl=GLB_BY_LABEL.get(label, "/sample_data/models/sofa.glb"),
            ),
            analysis=ANALYSIS_BY_LABEL.get(
                label,
                ObjectAnalysis(summary=f"{detected_object.name}适合作为空间风格参考。", placementAdvice="建议结合实际尺寸和动线再摆放。"),
            ),
        )
