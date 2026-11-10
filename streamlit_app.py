import os
import streamlit as st
from pathlib import Path

from agent.agent import YouTubeDownloaderAgent
from core.inspector import YouTubeInspector, is_valid_youtube_url
from core.models import (
    DownloadRequest,
    MediaType,
    ResolutionChoice,
    AudioFormatChoice,
    ProgressUpdate,
    TaskStatus,
)
from core.storage import format_seconds

st.set_page_config(
    page_title="YouTube Production Downloader Agent",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 YouTube Production Downloader Agent")
st.caption("⚡ Powered by yt-dlp & FFmpeg | Production-Grade Speed, Quality & Resilience")

# Initialize session state
if "metadata" not in st.session_state:
    st.session_state.metadata = None
if "current_url" not in st.session_state:
    st.session_state.current_url = ""

# Sidebar settings
with st.sidebar:
    st.header("⚙️ Configuration")
    rate_limit = st.selectbox("Speed Limit", ["Unlimited", "10M", "5M", "2M", "1M"], index=0)
    embed_subs = st.checkbox("Auto-embed Subtitles", value=True)
    embed_thumb = st.checkbox("Embed Thumbnail / Cover Art", value=True)
    st.markdown("---")
    with st.expander("🍪 Cloud 403 Bypass (Cookies)"):
        st.caption("Agar Streamlit Cloud par 403 Forbidden aaye, toh apne browser ke cookies yahan paste karein:")
        cookies_input = st.text_area("Netscape cookies.txt content", height=100)
        cookies_path = None
        if cookies_input.strip():
            c_file = Path("cookies.txt")
            c_file.write_text(cookies_input.strip(), encoding="utf-8")
            cookies_path = str(c_file.resolve())
            st.success("Cookies applied!")
    st.markdown("---")
    st.info("💡 **Folder Locations:**\n- Videos: `downloads/videos`\n- Audio: `downloads/audio`")

# Main URL Input
url_input = st.text_input("🔗 Enter YouTube Video or Playlist URL:", placeholder="https://www.youtube.com/watch?v=...")

col1, col2 = st.columns([1, 4])
with col1:
    inspect_btn = st.button("🔍 Inspect URL", use_container_width=True)

if inspect_btn and url_input.strip():
    if not is_valid_youtube_url(url_input):
        st.error("Please enter a valid YouTube URL.")
    else:
        with st.spinner("Fetching video stream data..."):
            try:
                inspector = YouTubeInspector(cookies_file=cookies_path)
                st.session_state.metadata = inspector.inspect(url_input)
                st.session_state.current_url = url_input
                st.success("Metadata loaded successfully!")
            except Exception as e:
                st.error(f"Failed to inspect URL: {e}")

# If metadata is loaded
meta = st.session_state.metadata
if meta and st.session_state.current_url == url_input:
    with st.container():
        m_col1, m_col2 = st.columns([1, 2])
        with m_col1:
            if meta.thumbnail:
                st.image(meta.thumbnail, use_container_width=True)
        with m_col2:
            st.subheader(meta.title)
            st.write(f"👤 **Channel:** {meta.uploader}")
            st.write(f"⏱️ **Duration:** {meta.duration_formatted}")
            if meta.view_count:
                st.write(f"👁️ **Views:** {meta.view_count:,}")
            if meta.is_playlist:
                st.write(f"📑 **Playlist Videos:** {meta.playlist_count}")

    st.markdown("---")
    tab_video, tab_audio, tab_agent = st.tabs(["🎥 Video Download", "🎵 Audio Only (MP3/M4A)", "🤖 Natural Language Agent"])

    # 1. Video Download Tab
    with tab_video:
        v_col1, v_col2 = st.columns(2)
        with v_col1:
            res_options = meta.available_resolutions if meta.available_resolutions else ["best", "1080p", "720p", "480p", "360p"]
            selected_res = st.selectbox("Resolution Target", options=res_options, index=0)
        with v_col2:
            selected_sub = st.selectbox("Subtitles (if available)", options=["None"] + meta.subtitles, index=0)

        clip_video = st.checkbox("Trim / Clip Segment", key="v_clip")
        start_t, end_t = None, None
        if clip_video:
            c_col1, c_col2 = st.columns(2)
            with c_col1:
                start_t = st.text_input("Start Time (e.g. 00:01:00)", "00:00:00")
            with c_col2:
                end_t = st.text_input("End Time (e.g. 00:02:30)", "00:01:00")

        if st.button("🚀 Start Video Download", type="primary", use_container_width=True):
            sub_list = [selected_sub.split(' ')[0]] if selected_sub != "None" else []
            req = DownloadRequest(
                url=url_input,
                media_type=MediaType.VIDEO,
                resolution=ResolutionChoice(selected_res) if selected_res in ResolutionChoice._value2member_map_ else ResolutionChoice.BEST,
                subtitles=sub_list,
                embed_subtitles=embed_subs,
                embed_thumbnail=embed_thumb,
                start_time=start_t if clip_video else None,
                end_time=end_t if clip_video else None,
                rate_limit=rate_limit if rate_limit != "Unlimited" else None
            )

            prog_bar = st.progress(0, text="Initializing download pipeline...")
            status_text = st.empty()

            def progress_callback(p: ProgressUpdate):
                if p.status == TaskStatus.DOWNLOADING:
                    prog_bar.progress(int(p.percent), text=f"Downloading {p.current_file or ''} ({p.speed_str} | ETA: {p.eta_str})")
                elif p.status == TaskStatus.PROCESSING:
                    prog_bar.progress(100, text="Processing & Merging audio/video with FFmpeg...")

            agent = YouTubeDownloaderAgent(cookies_file=cookies_path)
            result = agent.run(url_input, custom_request=req, progress_callback=progress_callback)

            if result.get("success"):
                st.success("🎉 Download Completed Successfully!")
                res_data = result.get("result", {})
                fp = res_data.get('file_path')
                st.info(f"📁 **Server File:** `{fp}` ({res_data.get('file_size_mb')} MB)")
                if fp and os.path.exists(fp):
                    with open(fp, "rb") as f:
                        st.download_button(
                            label="⬇️ Save Video to Device (Phone/PC)",
                            data=f.read(),
                            file_name=os.path.basename(fp),
                            mime="video/mp4",
                            use_container_width=True
                        )
            else:
                st.error(f"Download failed: {result.get('error')}")

    # 2. Audio Download Tab
    with tab_audio:
        a_col1, a_col2 = st.columns(2)
        with a_col1:
            a_fmt = st.selectbox("Audio Codec", ["mp3", "m4a", "wav", "flac"], index=0)
        with a_col2:
            a_bitrate = st.selectbox("Bitrate (kbps)", ["320", "256", "192", "128"], index=0)

        if st.button("🎵 Extract Audio", type="primary", use_container_width=True):
            req = DownloadRequest(
                url=url_input,
                media_type=MediaType.AUDIO,
                audio_format=AudioFormatChoice(a_fmt),
                audio_quality=a_bitrate,
                embed_thumbnail=embed_thumb,
                rate_limit=rate_limit if rate_limit != "Unlimited" else None
            )

            prog_bar = st.progress(0, text="Extracting high-quality audio...")

            def a_progress_callback(p: ProgressUpdate):
                if p.status == TaskStatus.DOWNLOADING:
                    prog_bar.progress(int(p.percent), text=f"Downloading audio stream ({p.speed_str})")
                elif p.status == TaskStatus.PROCESSING:
                    prog_bar.progress(100, text="Encoding ID3 tags & Album Cover Art...")

            agent = YouTubeDownloaderAgent(cookies_file=cookies_path)
            result = agent.run(url_input, custom_request=req, progress_callback=a_progress_callback)

            if result.get("success"):
                st.success("🎉 Audio Extraction Complete!")
                res_data = result.get("result", {})
                fp = res_data.get('file_path')
                st.info(f"📁 **Server File:** `{fp}` ({res_data.get('file_size_mb')} MB)")
                if fp and os.path.exists(fp):
                    with open(fp, "rb") as f:
                        st.download_button(
                            label="⬇️ Save Audio (MP3) to Device",
                            data=f.read(),
                            file_name=os.path.basename(fp),
                            mime="audio/mpeg",
                            use_container_width=True
                        )
            else:
                st.error(f"Extraction failed: {result.get('error')}")

    # 3. Agent Tab
    with tab_agent:
        st.write("🗣️ **Command the agent in Hindi or English:**")
        agent_instruction = st.text_area(
            "Agent Prompt",
            placeholder="e.g. 'Bhai ye video 1080p me download kar do with english subtitles' ya 'sirf audio mp3 me extract karo'"
        )
        if st.button("🤖 Let Agent Execute", type="primary", use_container_width=True):
            full_prompt = f"{agent_instruction} {url_input}"
            prog_bar = st.progress(0, text="Agent analyzing intent & planning execution...")

            def ag_progress_callback(p: ProgressUpdate):
                if p.status == TaskStatus.DOWNLOADING:
                    prog_bar.progress(int(p.percent), text=f"Downloading: {p.speed_str}")
                elif p.status == TaskStatus.PROCESSING:
                    prog_bar.progress(100, text="Finalizing file with FFmpeg...")

            agent = YouTubeDownloaderAgent(cookies_file=cookies_path)
            result = agent.run(full_prompt, progress_callback=ag_progress_callback)

            if result.get("success"):
                st.success("🎉 Agent executed successfully!")
                st.markdown(f"**Agent Summary:**\n```\n{result.get('summary')}\n```")
                res_data = result.get("result", {})
                fp = res_data.get('file_path') if res_data else None
                if fp and os.path.exists(fp):
                    with open(fp, "rb") as f:
                        st.download_button(
                            label="⬇️ Save Media to Device",
                            data=f.read(),
                            file_name=os.path.basename(fp),
                            use_container_width=True
                        )
            else:
                st.error(f"Agent execution failed: {result.get('error')}")
