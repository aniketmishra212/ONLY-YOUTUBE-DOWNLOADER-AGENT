import re
from typing import Optional, List, Dict, Any
import yt_dlp

from config import settings
from core.models import VideoMetadata, FormatInfo
from core.storage import format_seconds

YOUTUBE_URL_REGEX = re.compile(
    r'^(https?://)?(www\.|m\.)?(youtube\.com|youtu\.be)/(watch\?v=|embed/|v/|shorts/)?([a-zA-Z0-9_-]{11}|[a-zA-Z0-9_\-?&=]+)'
)

def is_valid_youtube_url(url: str) -> bool:
    """Validates if given string is a valid YouTube video or playlist URL."""
    if not url or not isinstance(url, str):
        return False
    return bool(YOUTUBE_URL_REGEX.match(url.strip())) or "youtube.com" in url or "youtu.be" in url

# Cache for inspected URLs to avoid redundant network calls
_METADATA_CACHE: Dict[str, VideoMetadata] = {}

class YouTubeInspector:
    """
    Extracts deep metadata, stream options, subtitles, and resolutions
    from YouTube URLs without downloading media bytes.
    Features in-memory caching and optimized client headers for ultra-fast lookup.
    """
    
    def __init__(self, cookies_file: Optional[str] = None):
        self.cookies_file = cookies_file or (str(settings.COOKIES_FILE) if settings.COOKIES_FILE else None)
        
    def _get_base_opts(self) -> Dict[str, Any]:
        opts: Dict[str, Any] = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extract_flat': False,
            'socket_timeout': 15,
            'user_agent': settings.USER_AGENT,
            'lazy_playlist': True,
            'geo_bypass': True,
            'nocheckcertificate': True,
        }
        if self.cookies_file:
            opts['cookiefile'] = self.cookies_file
        return opts

    def inspect(self, url: str) -> VideoMetadata:
        """Inspects URL and returns structured VideoMetadata with caching."""
        url = url.strip()
        if url in _METADATA_CACHE:
            return _METADATA_CACHE[url]

        opts = self._get_base_opts()
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as e:
                # Fallback with flat extraction if standard fails (e.g. huge playlist)
                opts['extract_flat'] = 'in_playlist'
                with yt_dlp.YoutubeDL(opts) as ydl_flat:
                    info = ydl_flat.extract_info(url, download=False)

        if not info:
            raise ValueError(f"Could not retrieve video metadata for: {url}")

        is_playlist = 'entries' in info
        
        # If it's a playlist, extract first entry for sample metadata or return playlist info
        if is_playlist:
            entries = list(info.get('entries') or [])
            playlist_count = len(entries)
            sample_entry = entries[0] if entries else {}
            title = info.get('title') or "YouTube Playlist"
            uploader = info.get('uploader') or sample_entry.get('uploader', "Various")
            meta_result = VideoMetadata(
                id=str(info.get('id', 'playlist')),
                url=url,
                title=title,
                description=info.get('description', ''),
                duration=None,
                duration_formatted=f"Playlist ({playlist_count} videos)",
                uploader=uploader,
                uploader_url=info.get('uploader_url'),
                view_count=info.get('view_count'),
                thumbnail=info.get('thumbnail') or sample_entry.get('thumbnail'),
                is_playlist=True,
                playlist_count=playlist_count,
                available_resolutions=['best', '1080p', '720p', '480p', '360p'],
                subtitles=[]
            )
            _METADATA_CACHE[url] = meta_result
            return meta_result

        # Single video or shorts
        duration = info.get('duration', 0)
        resolutions_set = set()
        
        for fmt in info.get('formats', []):
            h = fmt.get('height')
            if h and isinstance(h, int) and h > 0:
                resolutions_set.add(f"{h}p")

        # Sorted by resolution descending
        def res_sort_key(r: str) -> int:
            try:
                return int(r.replace('p', ''))
            except Exception:
                return 0

        sorted_resolutions = sorted(list(resolutions_set), key=res_sort_key, reverse=True)
        if not sorted_resolutions:
            sorted_resolutions = ['best']

        # Extract available subtitle languages
        subs = []
        if info.get('subtitles'):
            subs.extend(list(info['subtitles'].keys()))
        if info.get('automatic_captions'):
            for lang in info['automatic_captions'].keys():
                if lang not in subs:
                    subs.append(f"{lang} (auto)")

        meta_result = VideoMetadata(
            id=str(info.get('id', '')),
            url=url,
            title=info.get('title', 'Unknown Title'),
            description=info.get('description', ''),
            duration=duration,
            duration_formatted=format_seconds(duration),
            uploader=info.get('uploader', 'Unknown Channel'),
            uploader_url=info.get('uploader_url'),
            view_count=info.get('view_count', 0),
            thumbnail=info.get('thumbnail'),
            upload_date=info.get('upload_date'),
            is_live=bool(info.get('is_live', False)),
            is_playlist=False,
            playlist_count=None,
            available_resolutions=sorted_resolutions,
            subtitles=subs[:15] # Top 15 subtitle options
        )
        _METADATA_CACHE[url] = meta_result
        return meta_result
