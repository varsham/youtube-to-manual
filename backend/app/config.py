from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    # NVIDIA
    nvidia_api_key: str = Field(default="", env="NVIDIA_API_KEY")
    nvidia_model: str = Field(default="nvidia/nemotron-3-ultra-550b-a55b", env="NVIDIA_MODEL")
    nvidia_vision_model: str = Field(default="meta/llama-3.2-90b-vision-instruct", env="NVIDIA_VISION_MODEL")
    nvidia_base_url: str = Field(default="https://integrate.api.nvidia.com/v1", env="NVIDIA_BASE_URL")

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./ytmanual.db",
        env="DATABASE_URL",
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

    # YouTube auth (optional — needed for sign-in-gated videos)
    youtube_cookies_file: Optional[str] = Field(default=None, env="YOUTUBE_COOKIES_FILE")

    # Storage
    frames_dir: str = Field(default="./frames", env="FRAMES_DIR")
    max_frame_extraction_fps: float = Field(default=1.0, env="MAX_FRAME_EXTRACTION_FPS")
    max_video_duration_seconds: int = Field(default=3600, env="MAX_VIDEO_DURATION_SECONDS")

    # App
    secret_key: str = Field(default="dev-secret-key", env="SECRET_KEY")
    frontend_url: str = Field(default="http://localhost:5173", env="FRONTEND_URL")
    backend_url: str = Field(default="http://localhost:8000", env="BACKEND_URL")
    debug: bool = Field(default=True, env="DEBUG")

    class Config:
        env_file = ".env"
        extra = "ignore"

    def get_frames_path(self, job_id: str) -> str:
        path = os.path.join(self.frames_dir, job_id)
        os.makedirs(path, exist_ok=True)
        return path


settings = Settings()
