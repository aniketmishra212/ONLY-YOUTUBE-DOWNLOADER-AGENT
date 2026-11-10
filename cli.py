import sys
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
)
from rich.prompt import Prompt, Confirm

from agent.agent import YouTubeDownloaderAgent
from core.inspector import YouTubeInspector
from core.models import (
    DownloadRequest,
    MediaType,
    ResolutionChoice,
    AudioFormatChoice,
    ProgressUpdate,
    TaskStatus,
)
from core.storage import format_seconds

console = Console()

def display_banner():
    banner = """
[bold cyan]╔════════════════════════════════════════════════════════════╗[/bold cyan]
[bold cyan]║[/bold cyan]   [bold white]🚀 YOUTUBE PRODUCTION DOWNLOADER AGENT[/bold white]                   [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]   [dim]Intelligent, Resilient & High-Speed Media Pipeline[/dim]      [bold cyan]║[/bold cyan]
[bold cyan]╚════════════════════════════════════════════════════════════╝[/bold cyan]
    """
    console.print(banner)

def show_video_info(url: str):
    inspector = YouTubeInspector()
    with console.status("[bold green]Inspecting video stream data..."):
        try:
            meta = inspector.inspect(url)
        except Exception as e:
            console.print(f"[bold red]❌ Error retrieving info:[/bold red] {e}")
            return

    table = Table(title="[bold yellow]🎬 Video Information[/bold yellow]", show_header=True, header_style="bold magenta")
    table.add_column("Property", style="cyan", width=20)
    table.add_column("Value", style="white")

    table.add_row("Title", meta.title)
    table.add_row("Channel / Creator", meta.uploader or "Unknown")
    table.add_row("Duration", meta.duration_formatted)
    table.add_row("Views", f"{meta.view_count:,}" if meta.view_count else "N/A")
    table.add_row("Available Resolutions", ", ".join(meta.available_resolutions))
    table.add_row("Subtitles", ", ".join(meta.subtitles) if meta.subtitles else "None")
    if meta.is_playlist:
        table.add_row("Playlist Total", str(meta.playlist_count))

    console.print(table)

def interactive_mode():
    display_banner()
    
    url = Prompt.ask("[bold green]👉 Enter YouTube Video or Playlist URL[/bold green]")
    if not url.strip():
        console.print("[red]URL cannot be empty![/red]")
        return

    # Inspect first
    show_video_info(url)

    mode = Prompt.ask(
        "\n[bold yellow]Select Download Mode[/bold yellow]",
        choices=["Video (MP4)", "Audio (MP3)", "Custom/Agent"],
        default="Video (MP4)"
    )

    agent = YouTubeDownloaderAgent()

    if mode == "Audio (MP3)":
        req = DownloadRequest(
            url=url,
            media_type=MediaType.AUDIO,
            audio_format=AudioFormatChoice.MP3,
            audio_quality="320"
        )
    elif mode == "Video (MP4)":
        res = Prompt.ask(
            "Select Target Resolution",
            choices=["best", "1080p", "720p", "480p", "360p"],
            default="1080p"
        )
        req = DownloadRequest(
            url=url,
            media_type=MediaType.VIDEO,
            resolution=ResolutionChoice(res),
            embed_subtitles=True
        )
    else:
        prompt_text = Prompt.ask("Give your instruction to the Agent (e.g. 'download in 720p with subtitles')")
        full_prompt = f"{prompt_text} {url}"
        run_agent_with_progress(agent, full_prompt)
        return

    run_custom_request_with_progress(agent, req)

def run_agent_with_progress(agent: YouTubeDownloaderAgent, prompt_text: str):
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Processing...", total=100)

        def progress_cb(up: ProgressUpdate):
            if up.status == TaskStatus.DOWNLOADING:
                progress.update(
                    task,
                    completed=up.percent,
                    description=f"[green]Downloading: {up.current_file or ''} ({up.speed_str})",
                )
            elif up.status == TaskStatus.PROCESSING:
                progress.update(
                    task,
                    completed=100,
                    description="[yellow]Merging audio/video with FFmpeg...",
                )

        def log_cb(msg: str):
            console.log(f"[dim]{msg}[/dim]")

        result = agent.run(prompt_text, progress_callback=progress_cb, log_callback=log_cb)

    if result.get("success"):
        console.print(Panel(result.get("summary", ""), title="[bold green]✅ Download Completed[/bold green]", border_style="green"))
    else:
        console.print(Panel(result.get("error", "Unknown error"), title="[bold red]❌ Download Failed[/bold red]", border_style="red"))

def run_custom_request_with_progress(agent: YouTubeDownloaderAgent, req: DownloadRequest):
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Starting download...", total=100)

        def progress_cb(up: ProgressUpdate):
            if up.status == TaskStatus.DOWNLOADING:
                progress.update(
                    task,
                    completed=up.percent,
                    description=f"[green]Downloading: {up.current_file or ''} ({up.speed_str})",
                )
            elif up.status == TaskStatus.PROCESSING:
                progress.update(
                    task,
                    completed=100,
                    description="[yellow]Processing media tags & FFmpeg...",
                )

        def log_cb(msg: str):
            console.log(f"[dim]{msg}[/dim]")

        result = agent.run(req.url, custom_request=req, progress_callback=progress_cb, log_callback=log_cb)

    if result.get("success"):
        console.print(Panel(result.get("summary", ""), title="[bold green]✅ Download Completed[/bold green]", border_style="green"))
    else:
        console.print(Panel(result.get("error", "Unknown error"), title="[bold red]❌ Download Failed[/bold red]", border_style="red"))

def main():
    parser = argparse.ArgumentParser(description="Production-Grade YouTube Downloader Agent")
    parser.add_argument("url", nargs="?", help="YouTube video or playlist URL")
    parser.add_argument("--prompt", "-p", help="Natural language command for the agent (e.g. 'download in 1080p with subs')")
    parser.add_argument("--info", "-i", action="store_true", help="Inspect video and show metadata only")
    parser.add_argument("--audio", "-a", action="store_true", help="Download audio only (MP3 320kbps)")
    parser.add_argument("--quality", "-q", choices=["best", "2160p", "1440p", "1080p", "720p", "480p", "360p"], default="1080p", help="Target resolution")

    args = parser.parse_args()

    if not args.url and not args.prompt:
        interactive_mode()
        return

    if args.info and args.url:
        show_video_info(args.url)
        return

    agent = YouTubeDownloaderAgent()

    if args.prompt:
        full_text = f"{args.prompt} {args.url or ''}".strip()
        run_agent_with_progress(agent, full_text)
    elif args.url:
        if args.audio:
            req = DownloadRequest(
                url=args.url,
                media_type=MediaType.AUDIO,
                audio_format=AudioFormatChoice.MP3,
                audio_quality="320"
            )
        else:
            req = DownloadRequest(
                url=args.url,
                media_type=MediaType.VIDEO,
                resolution=ResolutionChoice(args.quality)
            )
        run_custom_request_with_progress(agent, req)

if __name__ == "__main__":
    main()
