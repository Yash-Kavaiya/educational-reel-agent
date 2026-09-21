"""Shared domain models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from agent.config import get_settings

SARVAM_VOICES = {
    "anushka": "Professional female - general tech, announcements",
    "arvind": "Professional male - technical tutorials",
    "meera": "Warm female - educational content",
    "kabir": "Deep male - serious/technical",
    "diya": "Energetic female - social media",
    "arya": "Neutral - international",
    "pavithra": "Tamil/English - South India",
}

VoiceName = Literal[
    "anushka", "arvind", "meera", "kabir", "diya", "arya", "pavithra"
]

ORACLE_PALETTE = {
    "bg": "#0D0D0D",
    "bg_accent": "#1A0A0A",
    "text": "#F5F0F0",
    "muted": "#A08080",
    "accent": "#E01C24",
    "accent2": "#FF6600",
    "highlight": "#FF9900",
    "node": "#1A0A0A",
    "node_edge": "#E01C24",
}

PrivacyStatus = Literal["private", "unlisted", "public"]


class Scene(BaseModel):
    id: int
    layout: str
    narration: str
    visual: dict[str, Any]


class Storyboard(BaseModel):
    title: str
    handle: str
    theme: str
    voice: str
    tts_provider: str = "sarvam"
    scenes: list[Scene]


class TopicItem(BaseModel):
    topic: str = Field(..., min_length=1)
    content: str = ""
    voice: VoiceName = "anushka"


class StoryboardRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    reel_number: int = Field(1, ge=1)
    total_reels: int = Field(1, ge=1)
    voice: VoiceName = "anushka"
    series_title: str = ""

    @field_validator("series_title")
    @classmethod
    def default_series(cls, value: str) -> str:
        return value or get_settings().default_series_title


class RenderRequest(BaseModel):
    storyboard_path: str = Field(..., min_length=1)
    output_filename: str | None = None
    preview: bool = False


class BatchRenderRequest(BaseModel):
    series_title: str = Field(..., min_length=1)
    topics: list[TopicItem] = Field(..., min_length=1)
    preview: bool = False


class SocialCopyRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    reel_number: int = Field(1, ge=1)
    total_reels: int = Field(1, ge=1)
    series_title: str = ""
    voice: VoiceName = "anushka"
    duration: str = "60s"

    @field_validator("series_title")
    @classmethod
    def default_series(cls, value: str) -> str:
        return value or get_settings().default_series_title


class YouTubeUploadRequest(BaseModel):
    video_path: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)
    privacy_status: PrivacyStatus = "unlisted"
    category_id: str = "28"


class PipelineRequest(BaseModel):
    series_title: str = Field(..., min_length=1)
    topics: list[TopicItem] = Field(..., min_length=1)
    render: bool = True
    generate_social: bool = True
    upload_youtube: bool = False
    youtube_privacy: PrivacyStatus = "unlisted"
    preview: bool = False


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    environment: dict[str, Any]
