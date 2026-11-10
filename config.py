import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Base Directories
    BASE_DIR: Path = Path(__file__).resolve().parent
    DOWNLOAD_DIR: Path = BASE_DIR / "downloads"
    VIDEO_DIR: Path = DOWNLOAD_DIR / "videos"
    AUDIO_DIR: Path = DOWNLOAD_DIR / "audio"
    PLAYLIST_DIR: Path = DOWNLOAD_DIR / "playlists"
    LOGS_DIR: Path = BASE_DIR / "logs"
    
    # Network & Resilience Settings
    SOCKET_TIMEOUT: int = 30
    MAX_RETRIES: int = 5
    CHUNK_SIZE: int = 10 * 1024 * 1024  # 10 MB chunks
    MIN_DISK_FREE_MB: int = 500          # Require at least 500 MB free disk space
    DEFAULT_RATE_LIMIT: str | None = None  # e.g., '5M' for 5MB/s, None for unlimited

    # Speed & Concurrency Accelerators
    CONCURRENT_FRAGMENTS: int = 10       # Multi-threaded parallel stream chunk downloads (10x speedup)
    HTTP_CHUNK_SIZE: int = 10485760      # 10MB chunk size
    BUFFER_SIZE: int = 1048576           # 1MB buffer
    
    # Anti-bot and Browser Headers
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    COOKIES_FILE: Path | None = None  # Path to cookies.txt if provided
    
    # Server / API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    class Config:
        env_prefix = "YTDL_"
        case_sensitive = False

settings = Settings()

# Ensure directories exist
for folder in [
    settings.DOWNLOAD_DIR,
    settings.VIDEO_DIR,
    settings.AUDIO_DIR,
    settings.PLAYLIST_DIR,
    settings.LOGS_DIR,
]:
    folder.mkdir(parents=True, exist_ok=True)
