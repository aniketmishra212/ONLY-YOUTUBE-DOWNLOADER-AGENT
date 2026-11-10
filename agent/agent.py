import uuid
import logging
from typing import Callable, Optional, Dict, Any

from core.models import (
    DownloadRequest,
    DownloadResult,
    VideoMetadata,
    ProgressUpdate,
    TaskStatus,
    MediaType,
    ResolutionChoice,
)
from core.inspector import YouTubeInspector, is_valid_youtube_url
from core.downloader import YouTubeDownloader
from agent.prompts import IntentParser

logger = logging.getLogger("yt_agent")

class YouTubeDownloaderAgent:
    """
    Autonomous Production-Level YouTube Downloader Agent.
    Interprets user requirements, selects optimal parameters,
    validates constraints, and executes robust downloads.
    """

    def __init__(self, cookies_file: Optional[str] = None):
        self.inspector = YouTubeInspector(cookies_file=cookies_file)
        self.downloader = YouTubeDownloader(cookies_file=cookies_file)

    def run(
        self,
        user_input: str,
        custom_request: Optional[DownloadRequest] = None,
        progress_callback: Optional[Callable[[ProgressUpdate], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end autonomous agent workflow:
        1. Parse natural language intent & extract URL
        2. Query metadata & check resolutions
        3. Match requested resolution with available stream formats
        4. Execute download with real-time feedback
        5. Return structured result & summary
        """
        task_id = str(uuid.uuid4())[:8]

        def emit_log(msg: str):
            logger.info(f"[{task_id}] {msg}")
            if log_callback:
                log_callback(msg)

        emit_log(f"Agent activated for input: '{user_input}'")

        # 1. URL Extraction
        url = None
        if custom_request and custom_request.url:
            url = custom_request.url
        else:
            url = IntentParser.extract_url(user_input)

        if not url or not is_valid_youtube_url(url):
            err_msg = "Invalid or missing YouTube URL. Please provide a valid link."
            emit_log(f"Error: {err_msg}")
            return {
                "success": False,
                "task_id": task_id,
                "error": err_msg,
                "summary": "Agent could not find a valid YouTube URL in your prompt."
            }

        # 2. Parse Intent
        intent = IntentParser.parse_intent(user_input)
        if intent.get("is_info_only"):
            emit_log(f"Inspecting metadata for: {url}")
            try:
                meta = self.inspector.inspect(url)
                return {
                    "success": True,
                    "task_id": task_id,
                    "info_only": True,
                    "metadata": meta.model_dump(),
                    "summary": f"Video: {meta.title} by {meta.uploader} ({meta.duration_formatted})"
                }
            except Exception as e:
                return {
                    "success": False,
                    "task_id": task_id,
                    "error": str(e),
                    "summary": f"Failed to retrieve metadata: {e}"
                }

        # 3. Construct Final DownloadRequest & Inspect only if needed
        metadata = None
        if custom_request:
            # Skip inspection to start download instantly
            req = custom_request
            req.url = url
        else:
            emit_log(f"Resolving stream capabilities for {url}...")
            try:
                metadata = self.inspector.inspect(url)
                emit_log(f"Found: '{metadata.title}' by {metadata.uploader} ({metadata.duration_formatted})")
            except Exception as e:
                emit_log(f"Warning: Quick inspection skipped ({e}).")

            req = DownloadRequest(
                url=url,
                media_type=intent["media_type"],
                resolution=intent["resolution"],
                audio_format=intent["audio_format"],
                audio_quality=intent["audio_quality"],
                subtitles=intent["subtitles"],
                start_time=intent["start_time"],
                end_time=intent["end_time"],
                playlist_items=intent["playlist_items"]
            )

        emit_log(f"Strategy: Mode={req.media_type.value.upper()}, Resolution={req.resolution.value}, AudioFormat={req.audio_format.value}")

        # 5. Execute Download
        if progress_callback:
            progress_callback(ProgressUpdate(status=TaskStatus.DOWNLOADING, percent=0.0))

        result = self.downloader.download(
            request=req,
            task_id=task_id,
            progress_callback=progress_callback
        )

        # 6. Format Result Summary
        if result.success:
            emit_log(f"Download complete: {result.file_path} ({result.file_size_mb} MB)")
            summary = (
                f"Successfully downloaded '{result.title or metadata.title if metadata else 'Video'}'!\n"
                f"Format: {req.media_type.value.upper()} ({req.resolution.value if req.media_type == MediaType.VIDEO else req.audio_format.value})\n"
                f"File Size: {result.file_size_mb} MB\n"
                f"Path: {result.file_path}"
            )
            return {
                "success": True,
                "task_id": task_id,
                "result": result.model_dump(),
                "metadata": metadata.model_dump() if metadata else None,
                "summary": summary
            }
        else:
            emit_log(f"Download failed: {result.error}")
            return {
                "success": False,
                "task_id": task_id,
                "error": result.error,
                "summary": f"Download failed due to: {result.error}"
            }
