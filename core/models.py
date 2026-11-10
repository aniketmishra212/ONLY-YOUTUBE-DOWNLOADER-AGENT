from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class MediaType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"

class ResolutionChoice(str, Enum):
    BEST = "best"
    RES_2160P = "2160p" # 4K
    RES_1440P = "1440p" # 2K
    RES_1080P = "1080p" # FHD
    RES_720P = "720p"   # HD
    RES_480P = "480p"   # SD
    RES_360P = "360p"   # Low

class AudioFormatChoice(str, Enum):
    MP3 = "mp3"
    M4A = "m4a"
    WAV = "wav"
    FLAC = "flac"

class TaskStatus(str, Enum):
    PENDING = "pending"
    INSPECTING = "inspecting"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class FormatInfo(BaseModel):
    format_id: str
    ext: str
    resolution: Optional[str] = None
    filesize_approx: Optional[int] = None
    fps: Optional[float] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    note: Optional[str] = None

class VideoMetadata(BaseModel):
    id: str
    url: str
    title: str
    description: Optional[str] = ""
    duration: Optional[int] = 0
    duration_formatted: str = "00:00"
    uploader: Optional[str] = "Unknown"
    uploader_url: Optional[str] = None
    view_count: Optional[int] = 0
    thumbnail: Optional[str] = None
    upload_date: Optional[str] = None
    is_live: bool = False
    is_playlist: bool = False
    playlist_count: Optional[int] = None
    available_resolutions: List[str] = []
    subtitles: List[str] = []

class DownloadRequest(BaseModel):
    url: str
    media_type: MediaType = MediaType.VIDEO
    resolution: ResolutionChoice = ResolutionChoice.RES_1080P
    audio_format: AudioFormatChoice = AudioFormatChoice.MP3
    audio_quality: str = "320"  # kbps (320, 256, 192, 128)
    subtitles: List[str] = Field(default_factory=list)
    embed_subtitles: bool = True
    embed_thumbnail: bool = True
    start_time: Optional[str] = None  # e.g., "00:01:30" or seconds
    end_time: Optional[str] = None    # e.g., "00:03:00" or seconds
    playlist_items: Optional[str] = None  # e.g., "1-5", "1,3,5"
    rate_limit: Optional[str] = None      # e.g., "5M", "500K"
    output_filename: Optional[str] = None

class ProgressUpdate(BaseModel):
    status: TaskStatus
    percent: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: Optional[int] = None
    speed_str: Optional[str] = None
    eta_str: Optional[str] = None
    current_file: Optional[str] = None
    raw_info: Optional[Dict[str, Any]] = None

class DownloadResult(BaseModel):
    task_id: str
    success: bool
    title: Optional[str] = None
    file_path: Optional[str] = None
    file_size_mb: Optional[float] = None
    duration_seconds: Optional[int] = None
    resolution_downloaded: Optional[str] = None
    error: Optional[str] = None
