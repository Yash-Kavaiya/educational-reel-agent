"""
Oracle Reel Agent - FastAPI Application
Main entry point for Cloud Run deployment
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

# Import our tools
from agent.tools.reel_tools import (
    create_storyboard,
    render_reel,
    batch_render_reels,
    generate_social_copy,
    register_tools,
    ORACLE_PALETTE,
    SARVAM_VOICES,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
GOOGLE_CLOUD_REGION = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/app/output"))
STORYBOARDS_DIR = Path(os.getenv("STORYBOARDS_DIR", "/app/storyboards"))
LOGS_DIR = Path(os.getenv("LOGS_DIR", "/app/logs"))

# Ensure directories exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
STORYBOARDS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Global state
runner = None
session_service = None
agent_instance = None


# =============================================================================
# Pydantic Models
# =============================================================================

class StoryboardRequest(BaseModel):
    topic: str = Field(..., description="Main topic/title of the reel")
    content: str = Field(..., description="Detailed content to cover")
    reel_number: int = Field(1, ge=1, description="Reel number in series")
    total_reels: int = Field(1, ge=1, description="Total reels in series")
    voice: str = Field("anushka", description="Sarvam AI voice to use")
    series_title: str = Field("Oracle AI Agents", description="Series title")


class RenderRequest(BaseModel):
    storyboard_path: str = Field(..., description="Path to storyboard JSON")
    output_filename: Optional[str] = Field(None, description="Custom output filename")
    preview: bool = Field(False, description="Render preview (540x960)")


class BatchRenderRequest(BaseModel):
    series_title: str = Field(..., description="Series title")
    topics: List[Dict[str, Any]] = Field(..., description="List of topic objects with topic, content, voice")
    preview: bool = Field(False, description="Render previews")


class SocialCopyRequest(BaseModel):
    topic: str = Field(..., description="Reel topic")
    reel_number: int = Field(1, ge=1)
    total_reels: int = Field(1, ge=1)
    series_title: str = Field("Oracle AI Agents")
    voice: str = Field("anushka")
    duration: str = Field("60s")


class YouTubeUploadRequest(BaseModel):
    video_path: str = Field(..., description="Path to video file")
    title: str = Field(..., description="Video title")
    description: str = Field(..., description="Video description")
    tags: List[str] = Field(default_factory=list)
    privacy_status: str = Field("unlisted", pattern="^(private|unlisted|public)$")
    category_id: str = Field("28")


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    environment: Dict[str, Any]


# =============================================================================
# Application Lifecycle
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global runner, session_service, agent_instance
    
    logger.info("Starting Oracle Reel Agent...")
    
    # Initialize ADK components
    session_service = InMemorySessionService()
    
    # Create agent with tools
    tools = register_tools()
    agent_instance = Agent(
        name="oracle_reel_creator",
        model="gemini-2.0-flash",
        description="Oracle-branded AI Reel Creator with Sarvam AI voiceovers",
        instruction="""You are an expert AI Reel Creator specializing in Oracle-branded educational content.
Create high-quality vertical reels (1080x1920) with Oracle Red (#E01C24) and Orange (#FF6600) theme.""",
        tools=tools,
    )
    
    runner = Runner(
        agent=agent_instance,
        app_name="oracle-reel-agent",
        session_service=session_service,
    )
    
    logger.info("Oracle Reel Agent started successfully")
    yield
    
    logger.info("Shutting down Oracle Reel Agent...")


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="Oracle Reel Agent API",
    description="AI-powered Oracle-branded reel generation with Sarvam AI voiceovers and YouTube publishing",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Health & Info Endpoints
# =============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for Cloud Run"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat() + "Z",
        version="1.0.0",
        environment={
            "project": GOOGLE_CLOUD_PROJECT,
            "region": GOOGLE_CLOUD_REGION,
            "sarvam_configured": bool(SARVAM_API_KEY),
            "output_dir": str(OUTPUT_DIR),
            "storyboards_dir": str(STORYBOARDS_DIR),
        }
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Oracle Reel Agent API",
        "version": "1.0.0",
        "description": "AI-powered Oracle-branded reel generation with Sarvam AI voiceovers",
        "endpoints": {
            "health": "/health",
            "create_storyboard": "/api/v1/storyboards",
            "render_reel": "/api/v1/render",
            "batch_render": "/api/v1/batch-render",
            "social_copy": "/api/v1/social-copy",
            "youtube_upload": "/api/v1/youtube/upload",
            "list_outputs": "/api/v1/outputs",
        }
    }


@app.get("/api/v1/info")
async def get_info():
    """Get agent configuration info"""
    return {
        "oracle_palette": ORACLE_PALETTE,
        "sarvam_voices": SARVAM_VOICES,
        "default_series": "Oracle AI Agents",
        "output_resolution": "1080x1920",
        "preview_resolution": "540x960",
        "supported_formats": ["mp4"],
    }


# =============================================================================
# Storyboard Endpoints
# =============================================================================

@app.post("/api/v1/storyboards", response_model=Dict[str, Any])
async def create_storyboard_endpoint(request: StoryboardRequest):
    """Create a new storyboard for a reel"""
    try:
        result = create_storyboard(
            topic=request.topic,
            content=request.content,
            reel_number=request.reel_number,
            total_reels=request.total_reels,
            voice=request.voice,
            series_title=request.series_title,
        )
        return result
    except Exception as e:
        logger.error(f"Storyboard creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/storyboards")
async def list_storyboards(series: Optional[str] = None):
    """List all storyboards"""
    try:
        if series:
            series_dir = STORYBOARDS_DIR / series.lower().replace(" ", "-")
        else:
            series_dir = STORYBOARDS_DIR
        
        if not series_dir.exists():
            return {"storyboards": []}
        
        storyboards = []
        for sb_file in series_dir.glob("*.json"):
            with open(sb_file) as f:
                data = json.load(f)
            storyboards.append({
                "file": sb_file.name,
                "title": data.get("title"),
                "voice": data.get("voice"),
                "scenes": len(data.get("scenes", [])),
                "series": series_dir.name,
            })
        
        return {"storyboards": sorted(storyboards, key=lambda x: x["file"])}
    except Exception as e:
        logger.error(f"List storyboards failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/storyboards/{series}/{filename}")
async def get_storyboard(series: str, filename: str):
    """Get a specific storyboard"""
    filepath = STORYBOARDS_DIR / series.lower().replace(" ", "-") / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Storyboard not found")
    
    with open(filepath) as f:
        return json.load(f)


# =============================================================================
# Render Endpoints
# =============================================================================

@app.post("/api/v1/render", response_model=Dict[str, Any])
async def render_reel_endpoint(request: RenderRequest, background_tasks: BackgroundTasks):
    """Render a single reel from storyboard"""
    try:
        result = render_reel(
            storyboard_path=request.storyboard_path,
            output_filename=request.output_filename,
            preview=request.preview,
        )
        return result
    except Exception as e:
        logger.error(f"Render failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/batch-render", response_model=Dict[str, Any])
async def batch_render_endpoint(request: BatchRenderRequest, background_tasks: BackgroundTasks):
    """Batch render multiple reels for a series"""
    try:
        result = batch_render_reels(
            series_title=request.series_title,
            topics=request.topics,
            preview=request.preview,
        )
        return result
    except Exception as e:
        logger.error(f"Batch render failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Social Copy Endpoints
# =============================================================================

@app.post("/api/v1/social-copy", response_model=Dict[str, Any])
async def generate_social_copy_endpoint(request: SocialCopyRequest):
    """Generate platform-optimized social media copy"""
    try:
        result = generate_social_copy(
            topic=request.topic,
            reel_number=request.reel_number,
            total_reels=request.total_reels,
            series_title=request.series_title,
            voice=request.voice,
            duration=request.duration,
        )
        return result
    except Exception as e:
        logger.error(f"Social copy generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# YouTube Endpoints
# =============================================================================

@app.post("/api/v1/youtube/upload", response_model=Dict[str, Any])
async def upload_to_youtube_endpoint(request: YouTubeUploadRequest):
    """Upload a video to YouTube"""
    try:
        from agent.tools.youtube_tools import upload_video_to_youtube
        
        result = upload_video_to_youtube(
            video_path=request.video_path,
            title=request.title,
            description=request.description,
            tags=request.tags,
            category_id=request.category_id,
            privacy_status=request.privacy_status,
        )
        return result
    except Exception as e:
        logger.error(f"YouTube upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Output Management
# =============================================================================

@app.get("/api/v1/outputs")
async def list_outputs(series: Optional[str] = None):
    """List all rendered outputs"""
    try:
        if series:
            output_dir = OUTPUT_DIR / series.lower().replace(" ", "-")
        else:
            output_dir = OUTPUT_DIR
        
        if not output_dir.exists():
            return {"outputs": []}
        
        outputs = []
        for video_file in output_dir.glob("*.mp4"):
            stat = video_file.stat()
            outputs.append({
                "filename": video_file.name,
                "path": str(video_file),
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "series": series or output_dir.name,
            })
        
        return {"outputs": sorted(outputs, key=lambda x: x["filename"])}
    except Exception as e:
        logger.error(f"List outputs failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/outputs/{series}/{filename}")
async def download_output(series: str, filename: str):
    """Download a rendered video"""
    filepath = OUTPUT_DIR / series.lower().replace(" ", "-") / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        filepath,
        media_type="video/mp4",
        filename=filename,
    )


# =============================================================================
# Pipeline Endpoint (Complete workflow)
# =============================================================================

class PipelineRequest(BaseModel):
    series_title: str = Field(..., description="Series title")
    topics: List[Dict[str, Any]] = Field(..., description="Topics with content")
    render: bool = Field(True, description="Render videos")
    generate_social: bool = Field(True, description="Generate social copy")
    upload_youtube: bool = Field(False, description="Upload to YouTube")
    youtube_privacy: str = Field("unlisted", pattern="^(private|unlisted|public)$")
    preview: bool = Field(False, description="Use preview quality")


@app.post("/api/v1/pipeline", response_model=Dict[str, Any])
async def run_pipeline(request: PipelineRequest, background_tasks: BackgroundTasks):
    """Run complete pipeline: storyboards -> render -> social copy -> youtube"""
    results = {
        "series": request.series_title,
        "storyboards": [],
        "renders": [],
        "social_copy": [],
        "youtube_uploads": [],
        "status": "started",
    }
    
    try:
        # 1. Create storyboards
        for i, topic_info in enumerate(request.topics, 1):
            sb_result = create_storyboard(
                topic=topic_info["topic"],
                content=topic_info.get("content", ""),
                reel_number=i,
                total_reels=len(request.topics),
                voice=topic_info.get("voice", "anushka"),
                series_title=request.series_title,
            )
            results["storyboards"].append(sb_result)
        
        # 2. Render reels
        if request.render:
            for sb in results["storyboards"]:
                if sb["status"] == "success":
                    output_name = f"{request.series_title.lower().replace(' ', '-')}-{sb.get('reel_number', 1):02d}-{sb['topic'].lower().replace(' ', '-')}-hd.mp4"
                    render_result = render_reel(
                        storyboard_path=sb["storyboard_path"],
                        output_filename=output_name,
                        preview=request.preview,
                    )
                    render_result["topic"] = sb["topic"]
                    results["renders"].append(render_result)
        
        # 3. Generate social copy
        if request.generate_social:
            for i, topic_info in enumerate(request.topics, 1):
                # Find corresponding render for duration
                duration = "60s"
                for r in results["renders"]:
                    if r.get("topic") == topic_info["topic"] and r.get("duration"):
                        duration = r["duration"]
                        break
                
                sc_result = generate_social_copy(
                    topic=topic_info["topic"],
                    reel_number=i,
                    total_reels=len(request.topics),
                    series_title=request.series_title,
                    voice=topic_info.get("voice", "anushka"),
                    duration=duration,
                )
                results["social_copy"].append(sc_result)
        
        # 4. Upload to YouTube (if requested and renders successful)
        if request.upload_youtube:
            for r in results["renders"]:
                if r["status"] == "success":
                    # Find social copy for this topic
                    sc = next((s for s in results["social_copy"] if s["topic"] == r["topic"]), None)
                    yt_data = sc["social_copy"]["youtube"] if sc else {"title": r["topic"], "description": "", "tags": []}
                    
                    yt_result = upload_video_to_youtube(
                        video_path=r["output_path"],
                        title=yt_data["title"],
                        description=yt_data["description"],
                        tags=yt_data.get("tags", []),
                        privacy_status=request.youtube_privacy,
                    )
                    yt_result["topic"] = r["topic"]
                    results["youtube_uploads"].append(yt_result)
        
        results["status"] = "completed"
        return results
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        results["status"] = "failed"
        results["error"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# YouTube Tool Import (lazy to avoid import errors)
# =============================================================================

def upload_video_to_youtube(
    video_path: str,
    title: str,
    description: str,
    tags: list = None,
    category_id: str = "28",
    privacy_status: str = "unlisted",
    thumbnail_path: str = None
) -> Dict[str, Any]:
    """Upload video to YouTube - wrapper for youtube_tools"""
    from agent.tools.youtube_tools import upload_video_to_youtube as yt_upload
    return yt_upload(
        video_path=video_path,
        title=title,
        description=description,
        tags=tags,
        category_id=category_id,
        privacy_status=privacy_status,
        thumbnail_path=thumbnail_path
    )


# =============================================================================
# Main entry point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)