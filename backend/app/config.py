import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env")


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
    ark_api_key: str | None
    ark_base_url: str
    ark_vision_model: str
    ark_text_model: str
    ark_image_model: str
    ark_image_size: str
    enable_ark_reference_image: bool
    openai_api_key: str | None
    openai_base_url: str
    openai_vision_model: str
    openai_image_model: str
    openai_image_size: str
    spatial_agent_provider: str
    spatial_agent_provider: str
    hunyuan_api_key: str | None
    hunyuan_base_url: str
    hunyuan_model: str
    hunyuan_generate_type: str
    hunyuan_face_count: int | None
    hunyuan_enable_pbr: bool
    hunyuan_enable_geometry: bool
    hunyuan_result_format: str
    hunyuan_poll_interval_sec: float
    hunyuan_poll_attempts: int
    meshy_ai_model: str
    meshy_poll_interval_sec: float
    meshy_poll_attempts: int
    tripo_api_key: str | None
    tripo_base_url: str
    tripo_model_version: str
    tripo_texture: bool
    tripo_pbr: bool
    tripo_texture_quality: str
    tripo_texture_alignment: str
    tripo_export_uv: bool
    tripo_enable_image_autofix: bool
    tripo_poll_interval_sec: float
    tripo_poll_attempts: int
    sam3_api_key: str | None
    sam3_endpoint: str | None
    pixal3d_api_key: str | None
    pixal3d_endpoint: str | None
    meshy_api_key: str | None
    meshy_base_url: str
    cors_origins: list[str]
    furniture_dedupe_enabled: bool
    furniture_dedupe_model: str
    furniture_dedupe_device: str
    furniture_dedupe_threshold: float
    furniture_dedupe_batch_size: int
    floorplan_ai_timeout_sec: float
    floorplan_ai_input_max_side: int
    floorplan_max_upload_mb: int

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
        self.ark_api_key = os.getenv("ARK_API_KEY")
        self.ark_base_url = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")
        self.ark_vision_model = os.getenv("ARK_VISION_MODEL", "doubao-seed-2-1-pro-260628")
        self.ark_text_model = os.getenv("ARK_TEXT_MODEL", self.ark_vision_model)
        self.ark_image_model = os.getenv("ARK_IMAGE_MODEL", "doubao-seedream-5-0-lite-260128")
        self.ark_image_size = os.getenv("ARK_IMAGE_SIZE", "2048x2048")
        self.enable_ark_reference_image = os.getenv("ENABLE_ARK_REFERENCE_IMAGE", "false").lower() == "true"
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")
        self.openai_vision_model = os.getenv("OPENAI_VISION_MODEL", "gpt-5.1")
        self.openai_image_model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
        self.openai_image_size = os.getenv("OPENAI_IMAGE_SIZE", "1024x1024")
        # ark | mock; falls back to mock automatically when ARK_API_KEY is missing.
        self.spatial_agent_provider = os.getenv("SPATIAL_AGENT_PROVIDER", "ark").lower()
        self.hunyuan_api_key = os.getenv("HUNYUAN_API_KEY")
        self.hunyuan_base_url = os.getenv("HUNYUAN_BASE_URL", "https://tokenhub.tencentmaas.com").rstrip("/")
        self.hunyuan_model = os.getenv("HUNYUAN_MODEL", "hy-3d-express")
        default_hunyuan_generate_type = "Normal" if self.hunyuan_model == "hy-3d-3.1" else "LowPoly"
        self.hunyuan_generate_type = os.getenv("HUNYUAN_GENERATE_TYPE", default_hunyuan_generate_type)
        raw_hunyuan_face_count = os.getenv("HUNYUAN_FACE_COUNT", "").strip()
        self.hunyuan_face_count = (
            int(raw_hunyuan_face_count) if raw_hunyuan_face_count else None
        )
        if (
            self.hunyuan_face_count is not None
            and not 3000 <= self.hunyuan_face_count <= 1500000
        ):
            raise ValueError("HUNYUAN_FACE_COUNT must be between 3000 and 1500000")
        self.hunyuan_enable_pbr = os.getenv("HUNYUAN_ENABLE_PBR", "false").lower() in {"1", "true", "yes", "on"}
        self.hunyuan_enable_geometry = os.getenv("HUNYUAN_ENABLE_GEOMETRY", "false").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.hunyuan_result_format = os.getenv("HUNYUAN_RESULT_FORMAT", "GLB").upper()
        self.hunyuan_poll_interval_sec = float(os.getenv("HUNYUAN_POLL_INTERVAL_SEC", "5"))
        self.hunyuan_poll_attempts = int(os.getenv("HUNYUAN_POLL_ATTEMPTS", "120"))
        self.sam3_api_key = os.getenv("SAM3_API_KEY")
        self.sam3_endpoint = os.getenv("SAM3_ENDPOINT")
        self.pixal3d_api_key = os.getenv("PIXAL3D_API_KEY")
        self.pixal3d_endpoint = os.getenv("PIXAL3D_ENDPOINT")
        self.meshy_api_key = os.getenv("MESHY_API_KEY")
        self.meshy_base_url = os.getenv("MESHY_BASE_URL", "https://api.meshy.ai")
        self.meshy_ai_model = os.getenv("MESHY_AI_MODEL", "meshy-6")
        self.meshy_poll_interval_sec = float(os.getenv("MESHY_POLL_INTERVAL_SEC", "5"))
        self.meshy_poll_attempts = int(os.getenv("MESHY_POLL_ATTEMPTS", "72"))
        self.tripo_api_key = os.getenv("TRIPO_API_KEY")
        self.tripo_base_url = os.getenv("TRIPO_BASE_URL", "https://api.tripo3d.com").rstrip("/")
        self.tripo_model_version = os.getenv("TRIPO_MODEL_VERSION", "v3.0-20250812")
        self.tripo_texture = os.getenv("TRIPO_TEXTURE", "true").lower() in {"1", "true", "yes", "on"}
        self.tripo_pbr = os.getenv("TRIPO_PBR", "false").lower() in {"1", "true", "yes", "on"}
        self.tripo_texture_quality = os.getenv("TRIPO_TEXTURE_QUALITY", "standard")
        self.tripo_texture_alignment = os.getenv("TRIPO_TEXTURE_ALIGNMENT", "geometry")
        self.tripo_export_uv = os.getenv("TRIPO_EXPORT_UV", "false").lower() in {"1", "true", "yes", "on"}
        self.tripo_enable_image_autofix = os.getenv("TRIPO_ENABLE_IMAGE_AUTOFIX", "false").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.tripo_poll_interval_sec = float(os.getenv("TRIPO_POLL_INTERVAL_SEC", "5"))
        self.tripo_poll_attempts = int(os.getenv("TRIPO_POLL_ATTEMPTS", "72"))
        self.furniture_dedupe_enabled = os.getenv("FURNITURE_DEDUPE_ENABLED", "true").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.furniture_dedupe_model = os.getenv(
            "FURNITURE_DEDUPE_MODEL",
            "openai/clip-vit-base-patch32",
        )
        self.furniture_dedupe_device = os.getenv("FURNITURE_DEDUPE_DEVICE", "auto").lower()
        self.furniture_dedupe_threshold = float(os.getenv("FURNITURE_DEDUPE_THRESHOLD", "0.88"))
        self.furniture_dedupe_batch_size = max(1, int(os.getenv("FURNITURE_DEDUPE_BATCH_SIZE", "16")))
        self.floorplan_ai_timeout_sec = max(1.0, float(os.getenv("FLOORPLAN_AI_TIMEOUT_SEC", "180")))
        self.floorplan_ai_input_max_side = max(
            256,
            min(2048, int(os.getenv("FLOORPLAN_AI_INPUT_MAX_SIDE", "768"))),
        )
        self.floorplan_max_upload_mb = max(1, int(os.getenv("FLOORPLAN_MAX_UPLOAD_MB", "15")))
        raw_origins = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
        )
        self.cors_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
