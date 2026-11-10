import os
import uuid
from typing import Dict, Any, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import settings
from core.models import (
    DownloadRequest,
    DownloadResult,
    VideoMetadata,
    ProgressUpdate,
    TaskStatus,
)
from core.inspector import YouTubeInspector, is_valid_youtube_url
from core.downloader import YouTubeDownloader

app = FastAPI(
    title="YouTube Production Downloader Agent API",
    description="High-performance, resilient API for inspecting and downloading YouTube media.",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory Task Storage (In real enterprise multi-node, Redis/DB can be used)
TASKS_DB: Dict[str, Dict[str, Any]] = {}

inspector = YouTubeInspector()
downloader = YouTubeDownloader()

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "YouTube Production Downloader Agent",
        "docs": "/docs",
        "version": "1.0.0"
    }

@app.post("/api/inspect", response_model=VideoMetadata)
def inspect_video(url: str = Query(..., description="YouTube video or playlist URL")):
    """Inspects video metadata, duration, creator, and available resolutions."""
    if not is_valid_youtube_url(url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL provided.")
    try:
        metadata = inspector.inspect(url)
        return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _background_download_worker(task_id: str, request: DownloadRequest):
    TASKS_DB[task_id]["status"] = TaskStatus.DOWNLOADING
    
    def on_progress(p: ProgressUpdate):
        TASKS_DB[task_id]["progress"] = p.percent
        TASKS_DB[task_id]["speed"] = p.speed_str
        TASKS_DB[task_id]["eta"] = p.eta_str
        TASKS_DB[task_id]["current_file"] = p.current_file
        TASKS_DB[task_id]["status"] = p.status

    try:
        result = downloader.download(
            request=request,
            task_id=task_id,
            progress_callback=on_progress
        )
        if result.success:
            TASKS_DB[task_id]["status"] = TaskStatus.COMPLETED
            TASKS_DB[task_id]["result"] = result.model_dump()
        else:
            TASKS_DB[task_id]["status"] = TaskStatus.FAILED
            TASKS_DB[task_id]["error"] = result.error
    except Exception as e:
        TASKS_DB[task_id]["status"] = TaskStatus.FAILED
        TASKS_DB[task_id]["error"] = str(e)

@app.post("/api/download")
def enqueue_download(request: DownloadRequest, background_tasks: BackgroundTasks):
    """Enqueues an asynchronous download job."""
    if not is_valid_youtube_url(request.url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL.")

    task_id = str(uuid.uuid4())[:8]
    TASKS_DB[task_id] = {
        "task_id": task_id,
        "url": request.url,
        "media_type": request.media_type,
        "status": TaskStatus.PENDING,
        "progress": 0.0,
        "speed": "0 KB/s",
        "eta": "N/A",
        "current_file": None,
        "result": None,
        "error": None
    }

    background_tasks.add_task(_background_download_worker, task_id, request)

    return {
        "message": "Download task enqueued successfully.",
        "task_id": task_id,
        "check_status_url": f"/api/tasks/{task_id}"
    }

@app.get("/api/tasks/{task_id}")
def get_task_status(task_id: str):
    """Retrieves real-time status and progress of a download task."""
    if task_id not in TASKS_DB:
        raise HTTPException(status_code=404, detail="Task ID not found.")
    return TASKS_DB[task_id]

@app.get("/api/files/{task_id}")
def serve_downloaded_file(task_id: str):
    """Downloads or streams the completed media file."""
    if task_id not in TASKS_DB:
        raise HTTPException(status_code=404, detail="Task ID not found.")
    
    task = TASKS_DB[task_id]
    if task.get("status") != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail=f"Task is not completed. Current status: {task.get('status')}")

    file_path = task.get("result", {}).get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Media file not found on disk.")

    return FileResponse(
        path=file_path,
        filename=os.path.basename(file_path),
        media_type="application/octet-stream"
    )

if __name__ == "__main__":
    uvicorn.run("api:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)
