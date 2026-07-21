import os
from functools import lru_cache


class Settings:
    app_name: str = "Space Energy MVP Backend"
    detection_provider: str
    segmentation_provider: str
    model3d_provider: str
    grounded_sam2_api_key: str | None
    grounded_sam2_endpoint: str | None
    grounded_sam2_prompt: str
    grounded_sam2_max_objects: int
    grounded_sam2_min_confidence: float
    doubao_api_key: str | None
    doubao_endpoint: str | None
    doubao_model: str
    grounding_dino_endpoint: str | None
    grounding_dino_api_key: str | None
    grounding_dino_min_confidence: float
    grounding_dino_max_objects: int
    sam_endpoint: str | None
    sam_api_key: str | None
    sam3_api_key: str | None
    sam3_endpoint: str | None
    pixal3d_api_key: str | None
    pixal3d_endpoint: str | None
    meshy_api_key: str | None
    meshy_base_url: str
    cors_origins: list[str]

    def __init__(self) -> None:
        self.detection_provider = os.getenv("DETECTION_PROVIDER", "mock").lower()
        self.segmentation_provider = os.getenv("SEGMENTATION_PROVIDER", "mock").lower()
        self.model3d_provider = os.getenv("MODEL3D_PROVIDER", "mock").lower()
        self.grounded_sam2_api_key = os.getenv("GROUNDED_SAM2_API_KEY")
        self.grounded_sam2_endpoint = os.getenv("GROUNDED_SAM2_ENDPOINT")
        self.grounded_sam2_prompt = os.getenv(
            "GROUNDED_SAM2_PROMPT",
            "sofa . bed . chair . armchair . table . coffee table . dining table . desk . "
            "cabinet . wardrobe . tv stand . bookshelf . nightstand . chandelier . pendant light . "
            "floor lamp . table lamp . rug . curtain . plant . mirror . painting .",
        )
        self.grounded_sam2_max_objects = int(os.getenv("GROUNDED_SAM2_MAX_OBJECTS", "8"))
        self.grounded_sam2_min_confidence = float(os.getenv("GROUNDED_SAM2_MIN_CONFIDENCE", "0.35"))
        self.doubao_api_key = os.getenv("DOUBAO_API_KEY")
        self.doubao_endpoint = os.getenv("DOUBAO_ENDPOINT")
        self.doubao_model = os.getenv("DOUBAO_MODEL", "doubao-vision")
        self.grounding_dino_endpoint = os.getenv("GROUNDING_DINO_ENDPOINT")
        self.grounding_dino_api_key = os.getenv("GROUNDING_DINO_API_KEY")
        self.grounding_dino_min_confidence = float(os.getenv("GROUNDING_DINO_MIN_CONFIDENCE", "0.35"))
        self.grounding_dino_max_objects = int(os.getenv("GROUNDING_DINO_MAX_OBJECTS", "8"))
        self.sam_endpoint = os.getenv("SAM_ENDPOINT")
        self.sam_api_key = os.getenv("SAM_API_KEY")
        self.sam3_api_key = os.getenv("SAM3_API_KEY")
        self.sam3_endpoint = os.getenv("SAM3_ENDPOINT")
        self.pixal3d_api_key = os.getenv("PIXAL3D_API_KEY")
        self.pixal3d_endpoint = os.getenv("PIXAL3D_ENDPOINT")
        self.meshy_api_key = os.getenv("MESHY_API_KEY")
        self.meshy_base_url = os.getenv("MESHY_BASE_URL", "https://api.meshy.ai")
        raw_origins = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
        )
        self.cors_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
