"""Runtime configuration. All secrets and paths come from the environment."""

from __future__ import annotations

from pathlib import Path
import sys

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    google_cloud_project: str = ""
    google_cloud_region: str = "us-central1"
    sarvam_api_key: str = ""

    output_dir: Path = Field(default=Path("output"))
    storyboards_dir: Path = Field(default=Path("storyboards"))
    logs_dir: Path = Field(default=Path("logs"))

    adk_model: str = "gemini-2.0-flash"
    adk_app_name: str = "educational-reel-agent"
    port: int = 8080
    host: str = "0.0.0.0"
    log_level: str = "INFO"
    cors_origins: str = "*"

    reelgen_python: str = ""
    reelgen_module: str = "reelgen"
    render_timeout_seconds: int = 600

    youtube_credentials_file: Path = Field(
        default_factory=lambda: Path.home() / ".youtube_credentials.json"
    )
    youtube_token_file: Path = Field(
        default_factory=lambda: Path.home() / ".youtube_token.json"
    )

    default_series_title: str = "Oracle AI Agents"
    default_handle: str = "@genai_guru"
    default_theme: str = "oracle"
    default_voice: str = "anushka"
    app_version: str = "1.1.0"

    def ensure_directories(self) -> None:
        for path in (self.output_dir, self.storyboards_dir, self.logs_dir):
            path.mkdir(parents=True, exist_ok=True)

    def reelgen_executable(self) -> str:
        return self.reelgen_python or sys.executable

    def cors_origin_list(self) -> list[str]:
        raw = [part.strip() for part in self.cors_origins.split(",") if part.strip()]
        return raw or ["*"]


def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings


def reset_settings() -> None:
    """Kept for tests that previously cleared a settings cache."""
    return None
