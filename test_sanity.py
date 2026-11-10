import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agent.prompts import IntentParser
from core.models import MediaType, ResolutionChoice, AudioFormatChoice
from core.storage import sanitize_filename, format_seconds, format_size
from core.inspector import is_valid_youtube_url

def test_intent_parser():
    print("[1] Testing IntentParser...")
    
    # Test 1: Hindi/Hinglish audio prompt
    prompt1 = "Bhai is link se sirf audio mp3 me nikal lo https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    url1 = IntentParser.extract_url(prompt1)
    intent1 = IntentParser.parse_intent(prompt1)
    assert url1 == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert intent1["media_type"] == MediaType.AUDIO
    assert intent1["audio_format"] == AudioFormatChoice.MP3
    print("  -> Passed Hindi Audio Test")

    # Test 2: 1080p with subtitles prompt
    prompt2 = "Download this video in 1080p with english subtitles https://youtu.be/dQw4w9WgXcQ"
    intent2 = IntentParser.parse_intent(prompt2)
    assert intent2["media_type"] == MediaType.VIDEO
    assert intent2["resolution"] == ResolutionChoice.RES_1080P
    assert "en" in intent2["subtitles"]
    print("  -> Passed 1080p Subtitles Test")

    # Test 3: Trimming / section clipping
    prompt3 = "cut from 00:30 to 01:45 https://www.youtube.com/watch?v=test"
    intent3 = IntentParser.parse_intent(prompt3)
    assert intent3["start_time"] == "00:30"
    assert intent3["end_time"] == "01:45"
    print("  -> Passed Clipping Test")

def test_storage_helpers():
    print("[2] Testing Storage Helpers...")
    dirty_name = 'Video: "Best Song" (2025) / [Official] ? * |'
    cleaned = sanitize_filename(dirty_name)
    assert ":" not in cleaned and '"' not in cleaned and "/" not in cleaned
    print(f"  -> Cleaned filename: {cleaned}")
    
    assert format_seconds(3665) == "01:01:05"
    assert format_seconds(95) == "01:35"
    print("  -> Passed Formatting Tests")

if __name__ == "__main__":
    test_intent_parser()
    test_storage_helpers()
    print("\n✅ ALL UNIT & SANITY TESTS PASSED SUCCESSFULLY!")
