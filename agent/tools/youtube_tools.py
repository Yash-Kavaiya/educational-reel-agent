"""YouTube publishing tool. Cloud Run cannot run an interactive OAuth flow."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from agent.config import get_settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

DEFAULT_TAGS = [
    "AI Agents",
    "Agentic AI",
    "Oracle",
    "Generative AI",
    "Machine Learning",
    "Artificial Intelligence",
    "Tech Education",
]


def _load_credentials() -> Any:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    settings = get_settings()
    token_file = Path(settings.youtube_token_file)
    credentials_file = Path(settings.youtube_credentials_file)

    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(creds.to_json(), encoding="utf-8")
        return creds

    raise RuntimeError(
        "YouTube OAuth token is missing or expired. "
        f"Place an authorized user token at {token_file} "
        f"(client secrets expected at {credentials_file}). "
        "Interactive OAuth is disabled in this service."
    )


def get_youtube_service() -> Any:
    """Get an authenticated YouTube Data API client."""
    from googleapiclient.discovery import build

    creds = _load_credentials()
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload_video_to_youtube(
    video_path: str,
    title: str,
    description: str,
    tags: list[str] | None = None,
    category_id: str = "28",
    privacy_status: str = "private",
    thumbnail_path: str | None = None,
) -> dict[str, Any]:
    """Upload a video to YouTube. Never starts a local browser OAuth flow."""
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    path = Path(video_path)
    if not path.is_file():
        return {"status": "error", "error": f"video not found: {video_path}"}
    if path.suffix.lower() != ".mp4":
        return {"status": "error", "error": "only .mp4 uploads are supported"}
    if privacy_status not in {"private", "unlisted", "public"}:
        return {"status": "error", "error": f"invalid privacy_status: {privacy_status}"}

    try:
        youtube = get_youtube_service()
        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags or [],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }
        media = MediaFileUpload(str(path), mimetype="video/mp4", chunksize=-1, resumable=True)
        request = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)

        response = None
        while response is None:
            _status, response = request.next_chunk()

        video_id = response["id"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        if thumbnail_path and Path(thumbnail_path).is_file():
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path),
            ).execute()

        return {
            "status": "success",
            "video_id": video_id,
            "url": video_url,
            "title": title,
        }
    except HttpError as exc:
        logger.exception("YouTube API error")
        return {"status": "error", "error": f"YouTube API error: {exc}"}
    except Exception as exc:  # noqa: BLE001 — tool contract returns error dicts
        logger.exception("YouTube upload failed")
        return {"status": "error", "error": str(exc)}


def publish_reel_to_youtube(
    video_path: str,
    title: str,
    description: str,
    tags: list[str] | None = None,
    privacy_status: str = "unlisted",
) -> dict[str, Any]:
    """Publish a reel with default educational tags merged in."""
    all_tags = list(dict.fromkeys(DEFAULT_TAGS + (tags or [])))[:30]
    return upload_video_to_youtube(
        video_path=video_path,
        title=title,
        description=description,
        tags=all_tags,
        privacy_status=privacy_status,
    )
