
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = "dev"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    secret_key: str = "change-me-to-a-long-random-string"
    access_token_minutes: int = 30
    refresh_token_days: int = 7
    cors_origins: str = "*"

    database_url: str = "postgresql+asyncpg://vaayu:vaayu@localhost:5432/vaayu"
    database_url_sync: str = "postgresql+psycopg2://vaayu:vaayu@localhost:5432/vaayu"
    redis_url: str = "redis://localhost:6379/0"
    opensearch_url: str = "http://localhost:9200"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "vaayu"
    minio_secret_key: str = "vaayusecret"
    minio_secure: bool = False
    minio_bucket: str = "media"

    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_client_id: str = "vaayudrishti"

    imd_api_key: str = ""
    reddit_user_agent: str = "VaayuDrishti/1.0 (weather research)"
    simulator_enabled: bool = True
    simulator_rate_per_min: int = 60
    ingest_enabled: bool = True

    embeddings_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    ml_device: str = "cpu"
    artifacts_dir: str = "/app/ml/artifacts"

    media_max_image_bytes: int = 10 * 1024 * 1024
    media_max_video_bytes: int = 50 * 1024 * 1024
    citizen_rate_limit_per_hour: int = 10

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_prod(self) -> bool:
        return self.app_env == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
