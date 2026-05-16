#!/usr/bin/env python3
"""
Download audio from a YouTube URL and convert it to MP3.

Usage:
    python yt_to_mp3.py "https://www.youtube.com/watch?v=VIDEO_ID"
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yt_dlp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download a YouTube video as MP3 using yt-dlp."
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "-o",
        "--output-dir",
        default="downloads",
        help="Directory to save MP3 files (default: downloads)",
    )
    parser.add_argument(
        "-q",
        "--quality",
        default="192",
        choices=["128", "192", "256", "320"],
        help="MP3 bitrate in kbps (default: 192)",
    )
    parser.add_argument(
        "--filename",
        default="%(title)s.%(ext)s",
        help="Output filename template (default: %(title)s.%(ext)s)",
    )
    return parser.parse_args()


def download_mp3(url: str, output_dir: Path, quality: str, filename_template: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / filename_template),
        "noplaylist": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": quality,
            }
        ],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def main() -> None:
    args = parse_args()
    download_mp3(
        url=args.url,
        output_dir=Path(args.output_dir),
        quality=args.quality,
        filename_template=args.filename,
    )


if __name__ == "__main__":
    main()
