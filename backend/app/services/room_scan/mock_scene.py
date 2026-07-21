from app.schemas import RoomSize, SceneObject, SceneResponse, SceneSuggestion


def build_mock_scene(scene_id: str) -> SceneResponse:
    return SceneResponse(
        sceneId=scene_id,
        unit="meter",
        room=RoomSize(width=4.2, depth=3.6, height=2.8),
        objects=[
            SceneObject(
                id="sofa_1",
                label="sofa",
                name="沙发",
                position=[1.2, 0.0, 2.8],
                rotation=[0.0, 0.0, 0.0],
                size=[2.0, 0.9, 0.8],
                glbUrl="/sample_data/models/sofa.glb",
            ),
            SceneObject(
                id="coffee_table_1",
                label="coffee_table",
                name="茶几",
                position=[1.2, 0.0, 1.8],
                rotation=[0.0, 0.0, 0.0],
                size=[1.0, 0.55, 0.38],
                glbUrl="/sample_data/models/coffee_table.glb",
            ),
            SceneObject(
                id="rug_1",
                label="rug",
                name="地毯",
                position=[1.2, 0.01, 1.9],
                rotation=[0.0, 0.0, 0.0],
                size=[2.4, 1.6, 0.02],
                glbUrl="/sample_data/models/rug.glb",
            ),
        ],
        suggestions=[
            SceneSuggestion(type="layout", text="沙发建议靠实墙放置，增强稳定感。"),
            SceneSuggestion(type="traffic", text="茶几与沙发保持 40-50cm 距离，动线更舒适。"),
            SceneSuggestion(type="lighting", text="主灯建议位于客厅活动中心上方，避免过低压迫视线。"),
        ],
    )
