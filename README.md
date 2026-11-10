# 🚀 YouTube Production Downloader Agent (Python)

Ek robust, resilient aur **Production-Level YouTube Downloader Agent** jo Python, `yt-dlp` aur `FFmpeg` par tayyar kiya gaya hai. 

Isme standard downloaders ke muqable advanced intelligence, anti-bot resilience, retry mechanisms, timestamp clipping, subtitles embedding, background API task queue aur interactive Web & Terminal UIs shamil hain.

---

## 🌟 Key Features (Production Grade)

1. **🤖 Autonomous Natural Language Agent:**
   - Hindi / Hinglish aur English natural language instructions samajhta hai.
   - Example: *"Bhai ye video 1080p me download karo with english subtitles"* ya *"Is link se sirf high quality mp3 nikal do"*.
2. **🎬 High Resolution Video Pipeline (FFmpeg Powered):**
   - 4K (2160p), 2K (1440p), 1080p, 720p, 480p, 360p support.
   - YouTube ke separate high-definition video aur audio streams ko automatically merge karke crystal clear `.mp4` me save karta hai.
3. **🎵 Studio Audio Extraction (MP3 / M4A / FLAC / WAV):**
   - Upto 320 kbps high bitrate extraction.
   - Metadata (Artist, Title, Album) aur Album Cover Art thumbnail automatically embed karta hai.
4. **⏱️ Smart Clipping / Trim Download:**
   - Bina poora video download kiye sirf required timestamp range (e.g. `00:01:20` to `00:02:45`) download kar sakta hai.
5. **🛡️ Anti-Throttling & Resilience:**
   - Exponential backoff retry mechanism (network error aane par fail nahi hota).
   - User-Agent header rotation aur browser `cookies.txt` support (Age-restricted ya Member-only videos ke liye).
   - Disk space pre-check taaki download beech me disk full hone par crash na ho.
6. **💻 Multiple Interfaces:**
   - **Interactive Rich CLI:** Color-coded terminal UI with live progress bar and speed tracking.
   - **Production REST API (FastAPI):** Asynchronous background download task queue aur real-time polling endpoints.
   - **Streamlit Web UI:** One-click visual dashboard for thumbnail preview, quality selector, and downloading.

---

## 📁 Project Architecture

```
youtube_downloader_agent/
├── agent/
│   ├── __init__.py
│   ├── agent.py            # Autonomous Downloader Agent (Planning & execution)
│   └── prompts.py          # Intent parser for Hindi/English commands
├── core/
│   ├── __init__.py
│   ├── downloader.py       # Core resilient yt-dlp & FFmpeg pipeline
│   ├── inspector.py        # Video/playlist metadata and stream analyzer
│   ├── storage.py          # Cross-platform filename sanitizer & disk monitor
│   └── models.py           # Pydantic schemas and types
├── config.py               # Central configuration (paths, timeouts, retries)
├── cli.py                  # Rich terminal agent & command line tool
├── api.py                  # FastAPI production REST service with background workers
├── app.py                  # Streamlit Web UI
├── requirements.txt        # Python dependencies
└── README.md
```

---

## ⚡ Installation & Setup

System me **Python 3.10+** aur **FFmpeg** hona zaroori hai. (FFmpeg aapke system me pehle se successfully installed hai).

### Step 1: Install Dependencies
```bash
pip install -r youtube_downloader_agent/requirements.txt
```

---

## 🛠️ Usage Modes

### 1️⃣ Interactive Terminal Agent (CLI)

Sabse asaan aur fast tareeqa terminal se run karna hai:

```bash
python youtube_downloader_agent/cli.py
```
Isme aapko interactive menu milega jisme URL daalke quality, format, subtitles choose kar sakte hain.

#### Directly Command-Line se Run karna:
```bash
# 1080p Video Download
python youtube_downloader_agent/cli.py "https://www.youtube.com/watch?v=VIDEO_ID" --quality 1080p

# Sirf Audio (MP3 320kbps + Album Art)
python youtube_downloader_agent/cli.py "https://www.youtube.com/watch?v=VIDEO_ID" --audio

# Video ki Information / Metadata check karna (bina download kiye)
python youtube_downloader_agent/cli.py "https://www.youtube.com/watch?v=VIDEO_ID" --info

# Natural Language Agent Mode:
python youtube_downloader_agent/cli.py --prompt "Bhai ye video 720p me download karo with english subtitles https://www.youtube.com/watch?v=VIDEO_ID"
```

---

### 2️⃣ Web Dashboard (Streamlit GUI)

Agar aapko browser me visually use karna hai:

```bash
streamlit run youtube_downloader_agent/app.py
```
Isme aap:
- Video URL paste karke live **Thumbnail & Details** dekh sakte hain.
- Single click me Video ya Audio download kar sakte hain.
- Trim / Clip range set kar sakte hain.
- Hindi / English prompt likh kar Agent se download karwa sakte hain.

---

### 3️⃣ Production REST API (FastAPI)

Production server ya microservice ke roop me run karne ke liye:

```bash
python youtube_downloader_agent/api.py
```
Server `http://localhost:8000` par start ho jayega.
Interactive Swagger documentation dekhne ke liye browser me kholein:
👉 **`http://localhost:8000/docs`**

#### Key API Endpoints:
- `POST /api/inspect?url=...` — Video metadata, resolutions aur thumbnails nikalta hai.
- `POST /api/download` — Background download task start karta hai aur `task_id` deta hai.
- `GET /api/tasks/{task_id}` — Real-time progress %, speed, ETA check karta hai.
- `GET /api/files/{task_id}` — Downloaded file stream ya download karta hai.

---

## 📂 Downloaded Files Location

- 🎥 **Videos:** `youtube_downloader_agent/downloads/videos/`
- 🎵 **Audio Files:** `youtube_downloader_agent/downloads/audio/`
- 📑 **Playlists:** `youtube_downloader_agent/downloads/playlists/`
