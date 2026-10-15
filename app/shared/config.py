from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+pysqlite:///./storage/changeface.db"
    db_connect_attempts: int = 20
    redis_url: str = "redis://localhost:6379/0"
    storage_dir: str = "./storage"
    inference_backend: str = "hyperswap"
    hyperswap_weights: str = ""
    max_image_bytes: int = 10 * 1024 * 1024
    max_video_bytes: int = 100 * 1024 * 1024
    max_video_duration_sec: float = 30
    gpu_lock_ttl_sec: int = 600
    gpu_lock_wait_sec: float = 2
    celery_task_always_eager: bool = False
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    session_ttl_sec: int = 14 * 24 * 3600
    session_cookie_secure: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
