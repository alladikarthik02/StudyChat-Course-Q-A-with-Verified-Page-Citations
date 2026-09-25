from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="STUDYCHAT_", env_file=".env", extra="ignore")

    database_url: SecretStr = SecretStr(
        "postgresql://studychat:local-studychat@127.0.0.1:54329/studychat"
    )
    # Live mode is deliberately unavailable until its adapter is implemented in T4.
    provider_mode: Literal["fixture"] = "fixture"
    storage_dir: Path = Path("data/documents")
    embedding_dimensions: Literal[1536] = 1536
    max_upload_bytes: int = Field(default=20 * 1024 * 1024, gt=0)
    max_pages: int = Field(default=300, gt=0, le=1000)
    max_text_chars: int = Field(default=2_000_000, gt=0)
    parse_timeout_seconds: float = Field(default=60, gt=0, le=120)
    parse_memory_mb: int = Field(default=512, ge=128, le=2048)
    embedding_timeout_seconds: float = Field(default=60, gt=0)
