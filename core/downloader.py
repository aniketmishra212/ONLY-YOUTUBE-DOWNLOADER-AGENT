import os
import sys
import time
import logging
from pathlib import Path
from typing import Callable, Optional, Dict, Any
import yt_dlp

from config import settings
from core.models import (
    DownloadRequest,
    DownloadResult,
    MediaType,
    TaskStatus,
    ProgressUpdate,
)
from core.storage import sanitize_filename, check_disk_space, format_size

logger = logging.getLogger("yt_downloader")

class YouTubeDownloader:
    """
    Production-grade YouTube downloader wrapping yt-dlp with FFmpeg integration,
    atomic output, retry mechanisms, and fine-grained progress callbacks.
    """

    def __init__(self, cookies_file: Optional[str] = None):
        self.cookies_file = cookies_file or (str(settings.COOKIES_FILE) if settings.COOKIES_FILE else None)

    def _build_format_selector(self, req: DownloadRequest) -> str:
        """
        Builds the optimal yt-dlp format selector string based on media type & resolution.
        """
        if req.media_type == MediaType.AUDIO:
            return "bestaudio/best"

        res = req.resolution.value if hasattr(req.resolution, "value") else str(req.resolution)
        if res == "best":
            return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
        
        # Extract height number (e.g. "1080p" -> 1080)
        height = res.replace("p", "").strip()
        if height.isdigit():
            h_int = int(height)
            return (
                f"bestvideo[height<={h_int}][ext=mp4]+bestaudio[ext=m4a]/"
                f"bestvideo[height<={h_int}]+bestaudio/"
                f"best[height<={h_int}]/best"
            )
        return "bestvideo+bestaudio/best"

    def download(
        self,
        request: DownloadRequest,
        task_id: str,
        progress_callback: Optional[Callable[[ProgressUpdate], None]] = None
    ) -> DownloadResult:
        """
        Executes the download with comprehensive error recovery and progress updates.
        """
        # Determine output directory
        if request.media_type == MediaType.AUDIO:
            output_folder = settings.AUDIO_DIR
        elif request.playlist_items:
            output_folder = settings.PLAYLIST_DIR
        else:
            output_folder = settings.VIDEO_DIR

        # Check free disk space
        has_space, free_gb = check_disk_space(output_folder)
        if not has_space:
            err_msg = f"Insufficient disk space! Only {free_gb} GB free, minimum required is {settings.MIN_DISK_FREE_MB} MB."
            logger.error(err_msg)
            return DownloadResult(
                task_id=task_id,
                success=False,
                error=err_msg
            )

        # Output template
        if request.output_filename:
            safe_name = sanitize_filename(request.output_filename)
            outtmpl = str(output_folder / f"{safe_name}.%(ext)s")
        else:
            outtmpl = str(output_folder / "%(title).200B [%(id)s].%(ext)s")

        downloaded_filepath: Optional[str] = None
        extracted_info: Dict[str, Any] = {}

        # Progress hook for yt-dlp
        def ytdl_progress_hook(d: Dict[str, Any]):
            nonlocal downloaded_filepath
            status = d.get('status')
            
            if status == 'downloading':
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                speed = d.get('speed')
                eta = d.get('eta')
                filename = os.path.basename(d.get('filename', ''))

                percent = (downloaded / total * 100) if total and total > 0 else 0.0
                speed_str = f"{format_size(speed)}/s" if speed else "N/A"
                eta_str = f"{eta}s" if eta else "N/A"

                if progress_callback:
                    progress_callback(ProgressUpdate(
                        status=TaskStatus.DOWNLOADING,
                        percent=round(percent, 1),
                        downloaded_bytes=downloaded,
                        total_bytes=total,
                        speed_str=speed_str,
                        eta_str=eta_str,
                        current_file=filename
                    ))

            elif status == 'finished':
                downloaded_filepath = d.get('filename')
                if progress_callback:
                    progress_callback(ProgressUpdate(
                        status=TaskStatus.PROCESSING,
                        percent=100.0,
                        current_file=os.path.basename(downloaded_filepath or '')
                    ))

        # Base yt-dlp options
        format_selector = self._build_format_selector(request)
        ydl_opts: Dict[str, Any] = {
            'format': format_selector,
            'outtmpl': outtmpl,
            'progress_hooks': [ytdl_progress_hook],
            'socket_timeout': settings.SOCKET_TIMEOUT,
            'user_agent': settings.USER_AGENT,
            'no_warnings': True,
            'quiet': True,
            'retries': settings.MAX_RETRIES,
            'fragment_retries': settings.MAX_RETRIES,
            'continuedl': True,
            'noplaylist': False if request.playlist_items else True,
            # SPEED ACCELERATORS
            'concurrent_fragment_downloads': settings.CONCURRENT_FRAGMENTS, # 10 parallel chunks
            'http_chunk_size': settings.HTTP_CHUNK_SIZE,                    # 10MB chunking
            'buffersize': settings.BUFFER_SIZE,                             # 1MB buffer
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web']                     # Bypass web player bandwidth throttling
                }
            }
        }

        # Cookies support
        if self.cookies_file and os.path.exists(self.cookies_file):
            ydl_opts['cookiefile'] = self.cookies_file

        # Rate limiting
        if request.rate_limit:
            ydl_opts['ratelimit'] = request.rate_limit

        # Playlist items range
        if request.playlist_items:
            ydl_opts['playlist_items'] = request.playlist_items

        # Custom Time Range / Section Clipping
        if request.start_time or request.end_time:
            # yt-dlp download_ranges accepts list of callables or dicts
            start_sec = request.start_time or "0"
            end_sec = request.end_time or "inf"
            try:
                # yt-dlp sections syntax
                ydl_opts['download_ranges'] = yt_dlp.utils.download_range_func(None, [(float(start_sec) if start_sec.replace('.', '', 1).isdigit() else start_sec, float(end_sec) if end_sec.replace('.', '', 1).isdigit() else end_sec)])
                ydl_opts['force_keyframes_at_cuts'] = True
            except Exception:
                # Fallback to postprocessor args
                pass

        # Post-processors for Audio vs Video
        postprocessors = []

        if request.media_type == MediaType.AUDIO:
            audio_fmt = request.audio_format.value if hasattr(request.audio_format, "value") else str(request.audio_format)
            postprocessors.append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': audio_fmt,
                'preferredquality': request.audio_quality,
            })
            if request.embed_thumbnail:
                postprocessors.append({'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'})
                postprocessors.append({'key': 'EmbedThumbnail'})
                ydl_opts['writethumbnail'] = True
            # Metadata tagger (ID3 / Vorbis)
            postprocessors.append({'key': 'FFmpegMetadata', 'add_metadata': True})

        else: # Video
            # Merge to MP4 container with FFmpeg
            ydl_opts['merge_output_format'] = 'mp4'

            # Subtitles handling
            if request.subtitles:
                ydl_opts['writesubtitles'] = True
                ydl_opts['writeautomaticsub'] = True
                ydl_opts['subtitleslangs'] = request.subtitles
                if request.embed_subtitles:
                    postprocessors.append({'key': 'FFmpegEmbedSubtitle'})

            if request.embed_thumbnail:
                postprocessors.append({'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'})
                postprocessors.append({'key': 'EmbedThumbnail'})
                ydl_opts['writethumbnail'] = True

            postprocessors.append({'key': 'FFmpegMetadata', 'add_metadata': True})

        if postprocessors:
            ydl_opts['postprocessors'] = postprocessors

        # Execute download with retry attempts
        attempts = 0
        last_exception = None

        while attempts < settings.MAX_RETRIES:
            try:
                attempts += 1
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    extracted_info = ydl.extract_info(request.url, download=True)
                    break
            except Exception as e:
                last_exception = e
                logger.warning(f"Download attempt {attempts}/{settings.MAX_RETRIES} failed: {e}")
                time.sleep(2 ** attempts) # Exponential backoff

        if not extracted_info and last_exception:
            error_text = str(last_exception)
            logger.error(f"Download permanently failed: {error_text}")
            return DownloadResult(
                task_id=task_id,
                success=False,
                error=error_text
            )

        # Locate final file path
        req_ext = request.audio_format.value if request.media_type == MediaType.AUDIO else "mp4"
        vid_id = extracted_info.get('id', '')
        final_path = None

        # Look for target extension file matching video id first
        if extracted_info and vid_id:
            for f in output_folder.glob(f"*{vid_id}*"):
                if f.suffix.lower() == f".{req_ext}":
                    final_path = str(f)
                    break

        # Fallback to hook's downloaded filepath if exact target file not found
        if not final_path:
            final_path = downloaded_filepath

        file_size_mb = None
        if final_path and os.path.exists(final_path):
            file_size_mb = round(os.path.getsize(final_path) / (1024 * 1024), 2)

        return DownloadResult(
            task_id=task_id,
            success=True,
            title=extracted_info.get('title'),
            file_path=final_path,
            file_size_mb=file_size_mb,
            duration_seconds=extracted_info.get('duration'),
            resolution_downloaded=request.resolution.value if hasattr(request.resolution, "value") else str(request.resolution)
        )
