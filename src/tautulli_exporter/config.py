"""Configuration management for Tautulli Exporter."""

from functools import lru_cache

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Tautulli connection settings
    tautulli_url: HttpUrl = Field(
        ...,
        description="Tautulli base URL (e.g., http://localhost:8181)",
    )
    tautulli_api_key: str = Field(
        ...,
        description="Tautulli API key",
        min_length=1,
    )

    # Exporter settings
    exporter_port: int = Field(
        default=9487,
        description="Port for metrics endpoint",
        ge=1,
        le=65535,
    )
    exporter_host: str = Field(
        default="0.0.0.0",
        description="Host to bind the exporter",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
    )

    # Feature flags
    collect_user_stats: bool = Field(
        default=True,
        description="Enable per-user metrics collection",
    )
    collect_library_stats: bool = Field(
        default=True,
        description="Enable per-library metrics collection",
    )

    # Collection intervals (in seconds)
    activity_collection_interval: int = Field(
        default=15,
        description="Interval for activity metrics collection",
        ge=5,
    )
    stats_collection_interval: int = Field(
        default=300,
        description="Interval for library/user stats collection",
        ge=60,
    )

    @property
    def tautulli_base_url(self) -> str:
        """Get the Tautulli base URL as a string."""
        return str(self.tautulli_url).rstrip("/")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
