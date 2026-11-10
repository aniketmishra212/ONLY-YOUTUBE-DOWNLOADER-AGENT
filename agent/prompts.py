import re
from typing import Dict, Any, Optional
from core.models import MediaType, ResolutionChoice, AudioFormatChoice

class IntentParser:
    """
    Parses natural language prompts (in English, Hindi/Hinglish)
    into structured DownloadRequest parameters.
    """

    @staticmethod
    def extract_url(text: str) -> Optional[str]:
        """Extracts first YouTube URL found in text."""
        match = re.search(r'https?://[^\s<>"]+|www\.[^\s<>"]+', text)
        if match:
            url = match.group(0)
            if "youtube.com" in url or "youtu.be" in url:
                return url
        return None

    @staticmethod
    def parse_intent(user_prompt: str) -> Dict[str, Any]:
        """
        Parses user's natural language command into structured arguments.
        Supports Hindi, Hinglish, and English commands.
        """
        prompt_lower = user_prompt.lower()
        extracted: Dict[str, Any] = {
            "media_type": MediaType.VIDEO,
            "resolution": ResolutionChoice.RES_1080P,
            "audio_format": AudioFormatChoice.MP3,
            "audio_quality": "320",
            "subtitles": [],
            "start_time": None,
            "end_time": None,
            "playlist_items": None,
            "is_info_only": False,
        }

        # Check if user just wants info / metadata
        if any(w in prompt_lower for w in ["info", "inspect", "details", "check", "batao", "dikhao", "metadata"]):
            if not any(w in prompt_lower for w in ["download", "karo", "save", "khicho", "down load"]):
                extracted["is_info_only"] = True
                return extracted

        # Audio vs Video Detection
        if any(w in prompt_lower for w in ["audio", "mp3", "song", "gana", "gaana", "music", "m4a", "sound", "wav", "flac", "sirf audio"]):
            extracted["media_type"] = MediaType.AUDIO
            if "m4a" in prompt_lower:
                extracted["audio_format"] = AudioFormatChoice.M4A
            elif "wav" in prompt_lower:
                extracted["audio_format"] = AudioFormatChoice.WAV
            elif "flac" in prompt_lower:
                extracted["audio_format"] = AudioFormatChoice.FLAC
            else:
                extracted["audio_format"] = AudioFormatChoice.MP3
        else:
            extracted["media_type"] = MediaType.VIDEO

        # Resolution detection
        if "4k" in prompt_lower or "2160" in prompt_lower:
            extracted["resolution"] = ResolutionChoice.RES_2160P
        elif "2k" in prompt_lower or "1440" in prompt_lower:
            extracted["resolution"] = ResolutionChoice.RES_1440P
        elif "1080" in prompt_lower or "fhd" in prompt_lower:
            extracted["resolution"] = ResolutionChoice.RES_1080P
        elif "720" in prompt_lower or "hd" in prompt_lower:
            extracted["resolution"] = ResolutionChoice.RES_720P
        elif "480" in prompt_lower or "sd" in prompt_lower:
            extracted["resolution"] = ResolutionChoice.RES_480P
        elif "360" in prompt_lower:
            extracted["resolution"] = ResolutionChoice.RES_360P
        elif "best" in prompt_lower or "highest" in prompt_lower or "sabse achhi" in prompt_lower:
            extracted["resolution"] = ResolutionChoice.BEST

        # Subtitles detection
        subs = []
        if "subtitle" in prompt_lower or "sub" in prompt_lower or "caption" in prompt_lower:
            if "hindi" in prompt_lower or "hi" in prompt_lower:
                subs.append("hi")
            if "english" in prompt_lower or "en" in prompt_lower or not subs:
                subs.append("en")
        extracted["subtitles"] = subs

        # Playlist ranges: e.g. "first 5 videos", "1-5", "top 10"
        pl_match = re.search(r'(?:first|top|pehle)\s*(\d+)', prompt_lower)
        if pl_match:
            count = pl_match.group(1)
            extracted["playlist_items"] = f"1-{count}"
        else:
            range_match = re.search(r'(\d+)\s*to\s*(\d+)', prompt_lower)
            if range_match and "playlist" in prompt_lower:
                extracted["playlist_items"] = f"{range_match.group(1)}-{range_match.group(2)}"

        # Timestamp clipping detection: e.g. "from 01:00 to 02:30", "cut 00:30-01:45"
        time_matches = re.findall(r'(\d{1,2}:\d{2}(?::\d{2})?)', prompt_lower)
        if len(time_matches) >= 2:
            extracted["start_time"] = time_matches[0]
            extracted["end_time"] = time_matches[1]

        return extracted
