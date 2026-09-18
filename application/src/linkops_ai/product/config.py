from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration with safe local defaults."""

    model_config = SettingsConfigDict(env_prefix="LINKOPS_", env_file=".env", extra="ignore")

    environment: str = "local"
    storage_backend: str = "memory"
    base_url: str = "http://localhost:8000"
    aws_region: str = "us-east-1"
    links_table_name: str = "linkops-links"
    analytics_table_name: str = "linkops-analytics"
    analytics_queue_url: str | None = None
    checkpoint_table_name: str = "linkops-checkpoints-dev"
    artifact_bucket: str | None = None
    agentcore_memory_id: str | None = None
    generated_slug_length: int = Field(default=8, ge=6, le=32)
    max_collision_retries: int = Field(default=5, ge=1, le=20)
    max_url_length: int = Field(default=2048, ge=256, le=8192)
    bedrock_model_id: str = ""
    bedrock_knowledge_base_id: str | None = None
    bedrock_data_source_id: str | None = None
    use_graph_interrupt: bool = False
    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
