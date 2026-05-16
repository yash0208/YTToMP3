#!/usr/bin/env python3
"""Interactive CLI to download YouTube audio as MP3."""

from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any, Callable
from urllib.parse import urlparse

import yt_dlp
from yt_dlp.utils import DownloadError

DEFAULT_OUTPUT_DIR = Path("downloads")
VALID_QUALITIES = {"128", "192", "256", "320"}
DEFAULT_TRUST_NETWORK = True
ProgressHook = Callable[[dict[str, Any]], None]


def is_valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def ask_choice() -> str:
    print("\nSelect download type:")
    print("1. Single video")
    print("2. Playlist")
    while True:
        choice = input("Enter your choice (1 or 2): ").strip()
        if choice in {"1", "2"}:
            return choice
        print("Invalid choice. Please enter 1 or 2.")


def ask_url(choice: str) -> str:
    prompt = "Enter video URL: " if choice == "1" else "Enter playlist URL: "
    while True:
        url = input(prompt).strip()
        if not url:
            print("URL cannot be empty.")
            continue
        if not is_valid_url(url):
            print("Invalid URL. Please paste a full link starting with http:// or https://")
            continue
        print(f"URL entered: {url}")
        return url


def ask_quality() -> str:
    while True:
        quality = input("Enter MP3 quality (128/192/256/320) [192]: ").strip()
        if not quality:
            return "192"
        if quality in VALID_QUALITIES:
            return quality
        print("Invalid quality. Use one of: 128, 192, 256, 320.")


def ask_ffmpeg_location() -> str | None:
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    if ffmpeg_path and ffprobe_path:
        return None

    print("\nMP3 conversion requires ffmpeg and ffprobe, but they were not found.")
    print("Install with Homebrew: brew install ffmpeg")
    print("Or provide a folder path that contains both binaries.")
    while True:
        custom_path = input("Enter ffmpeg folder path (or press Enter to exit): ").strip()
        if not custom_path:
            return None

        folder = Path(custom_path).expanduser()
        has_ffmpeg = (folder / "ffmpeg").exists()
        has_ffprobe = (folder / "ffprobe").exists()
        if has_ffmpeg and has_ffprobe:
            return str(folder)
        print("Invalid folder. It must contain both 'ffmpeg' and 'ffprobe'.")


def download_single_video(
    url: str,
    output_dir: Path,
    quality: str,
    no_check_certificate: bool = DEFAULT_TRUST_NETWORK,
    ffmpeg_location: str | None = None,
    progress_hook: ProgressHook | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
        "noplaylist": True,
        "nocheckcertificate": no_check_certificate,
        "ffmpeg_location": ffmpeg_location,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": quality,
            }
        ],
    }
    if progress_hook is not None:
        ydl_opts["progress_hooks"] = [progress_hook]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def download_playlist(
    url: str,
    output_dir: Path,
    quality: str,
    no_check_certificate: bool = DEFAULT_TRUST_NETWORK,
    ffmpeg_location: str | None = None,
    progress_hook: ProgressHook | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "format": "bestaudio/best",
        # Keep each playlist in its own folder.
        "outtmpl": str(output_dir / "%(playlist_title)s" / "%(playlist_index)s - %(title)s.%(ext)s"),
        "noplaylist": False,
        "nocheckcertificate": no_check_certificate,
        "ffmpeg_location": ffmpeg_location,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": quality,
            }
        ],
    }
    if progress_hook is not None:
        ydl_opts["progress_hooks"] = [progress_hook]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def main() -> None:
    print("YouTube to MP3 Downloader")
    if DEFAULT_TRUST_NETWORK:
        print("Network SSL verification: trusted mode (nocheckcertificate enabled)")

    ffmpeg_location = ask_ffmpeg_location()
    if ffmpeg_location is None and (shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None):
        print("\nCannot continue without ffmpeg/ffprobe because output must be MP3.")
        return

    choice = ask_choice()
    url = ask_url(choice)
    quality = ask_quality()

    try:
        if choice == "1":
            download_single_video(
                url=url,
                output_dir=DEFAULT_OUTPUT_DIR,
                quality=quality,
                no_check_certificate=DEFAULT_TRUST_NETWORK,
                ffmpeg_location=ffmpeg_location,
            )
        else:
            download_playlist(
                url=url,
                output_dir=DEFAULT_OUTPUT_DIR,
                quality=quality,
                no_check_certificate=DEFAULT_TRUST_NETWORK,
                ffmpeg_location=ffmpeg_location,
            )
        print("\nDownload completed.")
    except DownloadError as error:
        print("\nDownload failed.")
        print(f"Reason: {error}")
        print("Please check the URL and try again.")
        print("If SSL still fails on macOS Python, run:")
        print("open '/Applications/Python 3.13/Install Certificates.command'")
    except Exception as error:  # Defensive fallback to avoid raw tracebacks.
        print("\nSomething went wrong during download.")
        print(f"Reason: {error}")


if __name__ == "__main__":
    main()
