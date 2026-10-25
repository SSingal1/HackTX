import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    guardian_database_path: str = Field(
        default_factory=lambda: (
            "/tmp/guardian.sqlite3" if os.environ.get("VERCEL") else "data/guardian.sqlite3"
        )
    )
    guardian_provider_cache_ttl_seconds: int = 21600
    guardian_market_cache_ttl_seconds: int = 21600
    nextmove_frontend_dir: str = "../toyota-frontend/dist"

    nextmove_env: str = "development"
    nextmove_debug: bool = False
    nextmove_cors_origins: str = "http://localhost:3000,http://localhost:5173"

    snowflake_account: str | None = None
    snowflake_user: str | None = None
    snowflake_password: str | None = Field(default=None, repr=False)
    snowflake_authenticator: str = "externalbrowser"
    snowflake_role: str = "NEXTMOVE_APP_ROLE"
    snowflake_warehouse: str = "COMPUTE_WH"
    snowflake_database: str = "TFS_NEXT_MOVE"
    snowflake_schema: str = "CORE"

    serpapi_api_key: str | None = Field(default=None, repr=False)
    gemini_api_key: str | None = Field(default=None, repr=False)
    gemini_model: str = "gemini-3.8-flash"
    guardian_gemini_timeout_seconds: float = 15.0
    # Set this to a supported fast Gemini model for Guardian without changing other features.
    guardian_gemini_model: str | None = "gemini-3.5-flash-lite"
    guardian_gemini_max_output_tokens: int = Field(default=450, ge=100, le=700)

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip() for origin in self.nextmove_cors_origins.split(",") if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
