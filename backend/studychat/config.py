from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="STUDYCHAT_", env_file=".env", extra="ignore")

    database_url: SecretStr = SecretStr(
        "postgresql://studychat:local-studychat@127.0.0.1:54329/studychat"
    )
    provider_mode: Literal["fixture", "live"] = "fixture"
    openai_api_key: SecretStr | None = None
    chat_model: str = Field(
        default="gpt-4.1-mini-2025-04-14", pattern=r"^gpt-[a-zA-Z0-9.-]+-\d{4}-\d{2}-\d{2}$"
    )
    similarity_threshold: float = Field(default=0.25, ge=-1, le=1, allow_inf_nan=False)
    threshold_label: str = "untuned"
    chat_timeout_seconds: float = Field(default=60, gt=0, le=180)
    max_output_tokens: int = Field(default=1200, ge=64, le=4000)
    max_concurrent_chats: int = Field(default=2, ge=1, le=8)

    @model_validator(mode="after")
    def require_live_credentials(self):
        if self.provider_mode == "live" and not self.openai_api_key:
            raise ValueError("live_mode_requires_server_key")
        return self

    storage_dir: Path = Path("data/documents")
    embedding_dimensions: Literal[1536] = 1536
    max_upload_bytes: int = Field(default=20 * 1024 * 1024, gt=0)
    max_pages: int = Field(default=300, gt=0, le=1000)
    max_text_chars: int = Field(default=2_000_000, gt=0)
    parse_timeout_seconds: float = Field(default=60, gt=0, le=120)
    parse_memory_mb: int = Field(default=512, ge=128, le=2048)
    embedding_timeout_seconds: float = Field(default=60, gt=0)
