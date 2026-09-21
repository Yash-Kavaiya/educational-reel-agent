"""Educational Reel Agent FastAPI application."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from agent.config import get_settings
from agent.models import (
    BatchRenderRequest,
    HealthResponse,
    PipelineRequest,
    RenderRequest,
    SocialCopyRequest,
    StoryboardRequest,
    YouTubeUploadRequest,
)
from agent.paths import resolve_existing_under, safe_under, slugify
from agent.tools.reel_tools import (
    ORACLE_PALETTE,
    SARVAM_VOICES,
    batch_render_reels,
    create_storyboard,
    generate_social_copy,
    render_reel,
)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

ADK_AVAILABLE = False
runner = None
session_service = None

try:
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService

    ADK_AVAILABLE = True
except ImportError:
    logger.warning("google-adk is not installed; /chat-style ADK runner is disabled")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global runner, session_service
    settings = get_settings()
    settings.ensure_directories()
    logger.info("Starting Educational Reel Agent v%s", settings.app_version)

    if ADK_AVAILABLE:
        from agent.agent import root_agent

        session_service = InMemorySessionService()
        runner = Runner(
            agent=root_agent,
            app_name=settings.adk_app_name,
            session_service=session_service,
        )
        logger.info("ADK runner ready (model=%s)", settings.adk_model)
    else:
        logger.info("ADK runner skipped")

    yield
    logger.info("Shutting down Educational Reel Agent")


settings = get_settings()
app = FastAPI(
    title="Educational Reel Agent API",
    description="ADK educational reel generation with Sarvam AI voiceovers",
    version=settings.app_version,
    lifespan=lifespan,
)

_origins = settings.cors_origin_list()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials="*" not in _origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _tool_or_http(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error") or "tool error")
    return result


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    cfg = get_settings()
    return HealthResponse(
        status="healthy",
        timestamp=_utc_now(),
        version=cfg.app_version,
        environment={
            "project": cfg.google_cloud_project,
            "region": cfg.google_cloud_region,
            "sarvam_configured": bool(cfg.sarvam_api_key),
            "adk_available": ADK_AVAILABLE,
            "output_dir": str(cfg.output_dir),
            "storyboards_dir": str(cfg.storyboards_dir),
        },
    )


@app.get("/")
async def root() -> dict[str, Any]:
    cfg = get_settings()
    return {
        "name": "Educational Reel Agent API",
        "version": cfg.app_version,
        "description": "AI-powered educational reel generation with Sarvam AI voiceovers",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "create_storyboard": "/api/v1/storyboards",
            "render_reel": "/api/v1/render",
            "batch_render": "/api/v1/batch-render",
            "social_copy": "/api/v1/social-copy",
            "youtube_upload": "/api/v1/youtube/upload",
            "list_outputs": "/api/v1/outputs",
            "pipeline": "/api/v1/pipeline",
        },
    }


@app.get("/api/v1/info")
async def get_info() -> dict[str, Any]:
    cfg = get_settings()
    return {
        "oracle_palette": ORACLE_PALETTE,
        "sarvam_voices": SARVAM_VOICES,
        "default_series": cfg.default_series_title,
        "output_resolution": "1080x1920",
        "preview_resolution": "540x960",
        "supported_formats": ["mp4"],
        "adk_model": cfg.adk_model,
    }


@app.post("/api/v1/storyboards")
async def create_storyboard_endpoint(request: StoryboardRequest) -> dict[str, Any]:
    result = create_storyboard(
        topic=request.topic,
        content=request.content,
        reel_number=request.reel_number,
        total_reels=request.total_reels,
        voice=request.voice,
        series_title=request.series_title,
    )
    return _tool_or_http(result)


@app.get("/api/v1/storyboards")
async def list_storyboards(series: str | None = None) -> dict[str, Any]:
    cfg = get_settings()
    root = cfg.storyboards_dir
    if series:
        series_dir = root / slugify(series)
        files = series_dir.glob("*.json") if series_dir.exists() else []
    else:
        files = root.rglob("*.json") if root.exists() else []

    storyboards = []
    for sb_file in files:
        try:
            data = json.loads(sb_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning("Skipping unreadable storyboard %s", sb_file)
            continue
        storyboards.append(
            {
                "file": sb_file.name,
                "title": data.get("title"),
                "voice": data.get("voice"),
                "scenes": len(data.get("scenes", [])),
                "series": sb_file.parent.name,
            }
        )
    return {"storyboards": sorted(storyboards, key=lambda item: item["file"])}


@app.get("/api/v1/storyboards/{series}/{filename}")
async def get_storyboard(series: str, filename: str) -> dict[str, Any]:
    cfg = get_settings()
    try:
        filepath = safe_under(cfg.storyboards_dir, Path(slugify(series)) / Path(filename).name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if filepath.suffix != ".json" or not filepath.is_file():
        raise HTTPException(status_code=404, detail="Storyboard not found")
    return json.loads(filepath.read_text(encoding="utf-8"))


@app.post("/api/v1/render")
async def render_reel_endpoint(request: RenderRequest) -> dict[str, Any]:
    return _tool_or_http(
        render_reel(
            storyboard_path=request.storyboard_path,
            output_filename=request.output_filename,
            preview=request.preview,
        )
    )


@app.post("/api/v1/batch-render")
async def batch_render_endpoint(request: BatchRenderRequest) -> dict[str, Any]:
    return batch_render_reels(
        series_title=request.series_title,
        topics=[item.model_dump() for item in request.topics],
        preview=request.preview,
    )


@app.post("/api/v1/social-copy")
async def generate_social_copy_endpoint(request: SocialCopyRequest) -> dict[str, Any]:
    return _tool_or_http(
        generate_social_copy(
            topic=request.topic,
            reel_number=request.reel_number,
            total_reels=request.total_reels,
            series_title=request.series_title,
            voice=request.voice,
            duration=request.duration,
        )
    )


@app.post("/api/v1/youtube/upload")
async def upload_to_youtube_endpoint(request: YouTubeUploadRequest) -> dict[str, Any]:
    from agent.tools.youtube_tools import upload_video_to_youtube

    cfg = get_settings()
    try:
        video_path = resolve_existing_under(cfg.output_dir, request.video_path)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=f"video not found: {exc}") from exc
    result = upload_video_to_youtube(
        video_path=str(video_path),
        title=request.title,
        description=request.description,
        tags=request.tags,
        category_id=request.category_id,
        privacy_status=request.privacy_status,
    )
    return _tool_or_http(result)


@app.get("/api/v1/outputs")
async def list_outputs(series: str | None = Query(default=None)) -> dict[str, Any]:
    cfg = get_settings()
    root = cfg.output_dir
    if series:
        output_dir = root / slugify(series)
        files = output_dir.glob("*.mp4") if output_dir.exists() else []
    else:
        files = root.rglob("*.mp4") if root.exists() else []

    outputs = []
    for video_file in files:
        stat = video_file.stat()
        outputs.append(
            {
                "filename": video_file.name,
                "path": str(video_file),
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "series": series or video_file.parent.name,
            }
        )
    return {"outputs": sorted(outputs, key=lambda item: item["filename"])}


@app.get("/api/v1/outputs/{series}/{filename}")
async def download_output(series: str, filename: str) -> FileResponse:
    cfg = get_settings()
    try:
        filepath = safe_under(cfg.output_dir, Path(slugify(series)) / Path(filename).name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if filepath.suffix.lower() != ".mp4" or not filepath.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath, media_type="video/mp4", filename=filepath.name)


@app.post("/api/v1/pipeline")
async def run_pipeline(request: PipelineRequest) -> dict[str, Any]:
    if request.upload_youtube and not request.render:
        raise HTTPException(
            status_code=400,
            detail="upload_youtube requires render=true",
        )

    results: dict[str, Any] = {
        "series": request.series_title,
        "storyboards": [],
        "renders": [],
        "social_copy": [],
        "youtube_uploads": [],
        "status": "started",
    }

    try:
        for index, topic_info in enumerate(request.topics, 1):
            sb_result = create_storyboard(
                topic=topic_info.topic,
                content=topic_info.content,
                reel_number=index,
                total_reels=len(request.topics),
                voice=topic_info.voice,
                series_title=request.series_title,
            )
            results["storyboards"].append(sb_result)

        if request.render:
            for storyboard in results["storyboards"]:
                if storyboard.get("status") != "success":
                    continue
                output_name = (
                    f"{slugify(request.series_title)}-"
                    f"{storyboard['reel_number']:02d}-"
                    f"{slugify(storyboard['topic'])}-hd.mp4"
                )
                render_result = render_reel(
                    storyboard_path=storyboard["storyboard_path"],
                    output_filename=output_name,
                    preview=request.preview,
                )
                render_result["topic"] = storyboard["topic"]
                results["renders"].append(render_result)

        if request.generate_social:
            for index, topic_info in enumerate(request.topics, 1):
                duration = "60s"
                for item in results["renders"]:
                    if item.get("topic") == topic_info.topic and item.get("duration"):
                        duration = item["duration"]
                        break
                results["social_copy"].append(
                    generate_social_copy(
                        topic=topic_info.topic,
                        reel_number=index,
                        total_reels=len(request.topics),
                        series_title=request.series_title,
                        voice=topic_info.voice,
                        duration=duration,
                    )
                )

        if request.upload_youtube:
            from agent.tools.youtube_tools import upload_video_to_youtube

            for item in results["renders"]:
                if item.get("status") != "success":
                    continue
                social = next(
                    (row for row in results["social_copy"] if row.get("topic") == item["topic"]),
                    None,
                )
                yt_data = (
                    social["social_copy"]["youtube"]
                    if social and social.get("status") == "success"
                    else {"title": item["topic"], "description": item["topic"], "tags": []}
                )
                yt_result = upload_video_to_youtube(
                    video_path=item["output_path"],
                    title=yt_data["title"],
                    description=yt_data["description"],
                    tags=yt_data.get("tags", []),
                    privacy_status=request.youtube_privacy,
                )
                yt_result["topic"] = item["topic"]
                results["youtube_uploads"].append(yt_result)

        results["status"] = "completed"
        return results
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Pipeline failed")
        results["status"] = "failed"
        results["error"] = str(exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    import os

    import uvicorn

    uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8080")))
