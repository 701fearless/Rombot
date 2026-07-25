from app.schemas import RoomSize, SceneObject, SceneOpening, SceneResponse, SceneSuggestion


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
                position=[1.2, 0.45, 2.8],
                rotation=[0.0, 0.0, 0.0],
                size=[2.0, 0.9, 0.8],
                glbUrl="/sample_data/models/sofa.glb",
            ),
            SceneObject(
                id="coffee_table_1",
                label="coffee_table",
                name="茶几",
                position=[1.2, 0.225, 1.8],
                rotation=[0.0, 0.0, 0.0],
                size=[1.0, 0.45, 0.55],
                glbUrl="/sample_data/models/coffee_table.glb",
            ),
        ],
        openings=[
            SceneOpening(
                id="door_entry",
                type="door",
                name="入户门",
                position=[0.9, 1.05, 0.0],
                rotation=[0.0, 0.0, 0.0],
                size=[0.9, 2.1, 0.12],
                clearanceDepth=0.9,
            )
        ],
        suggestions=[
            SceneSuggestion(type="layout", text="沙发建议靠实墙放置，增强稳定感。"),
            SceneSuggestion(type="traffic", text="茶几与沙发保持 40-50cm 距离，动线更舒适。"),
        ],
    )
