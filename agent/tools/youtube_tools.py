"""
YouTube publishing tool for Oracle Reel Creator
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
CREDENTIALS_FILE = Path.home() / '.youtube_credentials.json'
TOKEN_FILE = Path.home() / '.youtube_token.json'


def get_youtube_service() -> Any:
    """Get authenticated YouTube service."""
    creds = None
    
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"YouTube credentials not found at {CREDENTIALS_FILE}. "
                    "Download from Google Cloud Console and save as .youtube_credentials.json"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    return build('youtube', 'v3', credentials=creds)


def upload_video_to_youtube(
    video_path: str,
    title: str,
    description: str,
    tags: list = None,
    category_id: str = "28",  # Science & Technology
    privacy_status: str = "private",
    thumbnail_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Upload a video to YouTube.
    
    Args:
        video_path: Path to video file
        title: Video title
        description: Video description
        tags: List of tags
        category_id: YouTube category ID (28 = Science & Technology)
        privacy_status: private, unlisted, or public
        thumbnail_path: Optional custom thumbnail
    
    Returns:
        Dict with video_id, url, and status
    """
    try:
        youtube = get_youtube_service()
        
        body = {
            'snippet': {
                'title': title[:100],  # YouTube limit
                'description': description[:5000],
                'tags': tags or [],
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False
            }
        }
        
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        
        request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"Upload progress: {int(status.progress() * 100)}%")
        
        video_id = response['id']
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Upload thumbnail if provided
        if thumbnail_path and Path(thumbnail_path).exists():
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()
        
        return {
            "status": "success",
            "video_id": video_id,
            "url": video_url,
            "title": title
        }
    
    except HttpError as e:
        return {"status": "error", "error": f"YouTube API error: {e}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def publish_reel_to_youtube(
    video_path: str,
    title: str,
    description: str,
    tags: list = None,
    privacy_status: str = "unlisted"
) -> Dict[str, Any]:
    """
    Publish an Oracle reel to YouTube with optimized metadata.
    
    Args:
        video_path: Path to the rendered reel MP4
        title: Reel title
        description: Full description
        tags: List of tags
        privacy_status: private, unlisted, or public
    
    Returns:
        Upload result
    """
    # Default Oracle AI tags
    default_tags = [
        "AI Agents", "Agentic AI", "Oracle", "Generative AI",
        "Machine Learning", "Artificial Intelligence", "Tech Education"
    ]
    
    all_tags = list(set(default_tags + (tags or [])))[:500]  # YouTube limit
    
    return upload_video_to_youtube(
        video_path=video_path,
        title=title,
        description=description,
        tags=all_tags,
        privacy_status=privacy_status
    )