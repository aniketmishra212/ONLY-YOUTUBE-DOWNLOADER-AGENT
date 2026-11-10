import os
import re
import shutil
from pathlib import Path
from typing import Tuple
from config import settings

# Windows reserved names
RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4",
    "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3",
    "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
}

def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Sanitizes string for safe cross-platform filesystem filename.
    Removes invalid characters, controls, and trims length.
    """
    # Replace illegal characters
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename)
    # Remove leading/trailing spaces and dots
    cleaned = cleaned.strip('. ')
    
    # Check reserved words in Windows
    base_name = cleaned.split('.')[0].upper()
    if base_name in RESERVED_NAMES:
        cleaned = f"safe_{cleaned}"
        
    if not cleaned:
        cleaned = "downloaded_file"
        
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
        
    return cleaned

def check_disk_space(target_path: Path, required_mb: int = settings.MIN_DISK_FREE_MB) -> Tuple[bool, float]:
    """
    Checks if target volume has enough free disk space.
    Returns (is_sufficient, free_gb).
    """
    try:
        usage = shutil.disk_usage(str(target_path.resolve()))
        free_mb = usage.free / (1024 * 1024)
        free_gb = free_mb / 1024
        return (free_mb >= required_mb, round(free_gb, 2))
    except Exception:
        # If check fails for any reason, don't block
        return (True, 999.0)

def format_size(bytes_num: int | float | None) -> str:
    """Formats bytes into human readable format."""
    if not bytes_num or bytes_num < 0:
        return "N/A"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_num < 1024.0:
            return f"{bytes_num:.2f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.2f} PB"

def format_seconds(seconds: int | float | None) -> str:
    """Converts seconds into HH:MM:SS or MM:SS."""
    if seconds is None or seconds < 0:
        return "00:00"
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
