#!/usr/bin/env python3
"""Streamlit web UI for YouTube to MP3 downloads."""

from __future__ import annotations

import io
from pathlib import Path
import shutil
import tempfile
import threading
import time
from typing import Any, Callable
import zipfile

import streamlit as st
from yt_dlp.utils import DownloadError

from yt_to_mp3 import (
    DEFAULT_TRUST_NETWORK,
    download_playlist,
    download_single_video,
    is_valid_url,
)


def detect_ffmpeg_location() -> str | None:
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    if ffmpeg_path and ffprobe_path:
        return None
    return ""


def run_download(
    *,
    mode: str,
    url: str,
    quality: str,
    output_dir: Path,
    ffmpeg_location: str | None,
    progress_hook: Callable[[dict[str, Any]], None] | None = None,
) -> None:
    if mode == "Single video":
        download_single_video(
            url=url,
            output_dir=output_dir,
            quality=quality,
            no_check_certificate=DEFAULT_TRUST_NETWORK,
            ffmpeg_location=ffmpeg_location,
            progress_hook=progress_hook,
        )
        return

    download_playlist(
        url=url,
        output_dir=output_dir,
        quality=quality,
        no_check_certificate=DEFAULT_TRUST_NETWORK,
        ffmpeg_location=ffmpeg_location,
        progress_hook=progress_hook,
    )


def collect_mp3_files(output_dir: Path) -> list[Path]:
    return sorted(output_dir.rglob("*.mp3"))


def sanitize_download_name(name: str, fallback: str) -> str:
    cleaned = "".join(ch for ch in name if ch.isalnum() or ch in {" ", "-", "_"}).strip()
    normalized = cleaned.replace(" ", "_")
    return normalized or fallback


def build_playlist_zip(mp3_files: list[Path], base_dir: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for mp3_file in mp3_files:
            zip_file.write(mp3_file, arcname=str(mp3_file.relative_to(base_dir)))
    return buffer.getvalue()


def render_download_animation(target) -> None:
    target.markdown(
        """
        <style>
        .yt-loader {
            display: inline-flex;
            align-items: flex-end;
            gap: 4px;
            height: 24px;
            margin-top: 6px;
        }
        .yt-loader span {
            width: 5px;
            border-radius: 2px;
            background: #1DB954;
            animation: yt-eq 1s ease-in-out infinite;
        }
        .yt-loader span:nth-child(2) { animation-delay: 0.15s; }
        .yt-loader span:nth-child(3) { animation-delay: 0.3s; }
        .yt-loader span:nth-child(4) { animation-delay: 0.45s; }
        @keyframes yt-eq {
            0%, 100% { height: 6px; opacity: 0.5; }
            50% { height: 24px; opacity: 1; }
        }
        </style>
        <div class="yt-loader"><span></span><span></span><span></span><span></span></div>
        """,
        unsafe_allow_html=True,
    )


def format_eta(seconds: int | None) -> str:
    if not seconds or seconds < 0:
        return "--:--"
    minutes, remaining = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{remaining:02d}"
    return f"{minutes:02d}:{remaining:02d}"


def build_status_line(job: dict[str, Any]) -> str:
    file_label = job.get("current_title") or "Preparing..."
    current = job.get("playlist_index")
    total = job.get("playlist_count")
    progress_part = f"File {current}/{total} | " if current and total else ""
    speed = job.get("speed_text") or "calculating..."
    eta = format_eta(job.get("eta_seconds"))
    phase = job.get("phase") or "Starting..."
    return f"{phase} | {progress_part}{file_label} | Speed: {speed} | ETA: {eta}"


def create_progress_hook(job: dict[str, Any]) -> Callable[[dict[str, Any]], None]:
    def hook(data: dict[str, Any]) -> None:
        if job.get("cancel_requested"):
            raise DownloadError("Download cancelled by user.")

        state = data.get("status", "")
        info = data.get("info_dict") or {}
        if info.get("title"):
            job["current_title"] = info["title"]
        if info.get("playlist_index"):
            job["playlist_index"] = str(info["playlist_index"])
        playlist_total = info.get("playlist_count") or info.get("n_entries")
        if playlist_total:
            job["playlist_count"] = str(playlist_total)

        if state == "downloading":
            downloaded = float(data.get("downloaded_bytes", 0))
            total = float(data.get("total_bytes") or data.get("total_bytes_estimate") or 0)
            percent = int((downloaded / total) * 100) if total > 0 else 0
            job["progress"] = min(max(percent, 0), 100)
            speed = data.get("speed")
            job["speed_text"] = f"{(speed / (1024 * 1024)):.2f} MB/s" if speed else "calculating..."
            job["eta_seconds"] = int(data["eta"]) if data.get("eta") else None
            job["phase"] = "Downloading audio"
        elif state == "finished":
            job["progress"] = 100
            job["phase"] = "Converting to MP3"
            job["eta_seconds"] = None

    return hook


def initialize_job(mode: str, url: str, quality: str, ffmpeg_location: str | None) -> dict[str, Any]:
    return {
        "mode": mode,
        "url": url,
        "quality": quality,
        "ffmpeg_location": ffmpeg_location,
        "running": True,
        "status": "running",
        "progress": 0,
        "phase": "Starting download",
        "speed_text": None,
        "eta_seconds": None,
        "playlist_index": None,
        "playlist_count": None,
        "current_title": None,
        "cancel_requested": False,
        "payload": None,
        "error": None,
    }


def run_job_worker(job: dict[str, Any]) -> None:
    output_dir = Path(tempfile.mkdtemp(prefix="yt_to_mp3_"))
    try:
        run_download(
            mode=job["mode"],
            url=job["url"],
            quality=job["quality"],
            output_dir=output_dir,
            ffmpeg_location=job["ffmpeg_location"],
            progress_hook=create_progress_hook(job),
        )

        mp3_files = collect_mp3_files(output_dir)
        if not mp3_files:
            raise DownloadError("Download finished but no MP3 file was generated.")

        if job["mode"] == "Single video":
            mp3_file = mp3_files[0]
            job["payload"] = {
                "label": "Download MP3",
                "file_name": sanitize_download_name(mp3_file.stem, "audio") + ".mp3",
                "mime": "audio/mpeg",
                "data": mp3_file.read_bytes(),
                "success": "MP3 is ready. Click below to save it in browser Downloads.",
            }
        else:
            zip_data = build_playlist_zip(mp3_files, output_dir)
            job["payload"] = {
                "label": "Download MP3",
                "file_name": "playlist_mp3.zip",
                "mime": "application/zip",
                "data": zip_data,
                "success": "Playlist ZIP is ready. Click below to save it in browser Downloads.",
            }
        job["status"] = "success"
    except DownloadError as error:
        if job.get("cancel_requested"):
            job["status"] = "cancelled"
            job["error"] = "Download cancelled."
        else:
            job["status"] = "error"
            job["error"] = str(error)
    except Exception as error:  # Defensive fallback.
        job["status"] = "error"
        job["error"] = str(error)
    finally:
        job["running"] = False
        shutil.rmtree(output_dir, ignore_errors=True)


def main() -> None:
    st.set_page_config(page_title="YT to MP3", page_icon="🎵", layout="centered")
    st.title("YouTube to MP3 Downloader")
    st.caption("No separate API required. This UI runs directly with Python + yt-dlp.")

    if "download_job" not in st.session_state:
        st.session_state.download_job = None

    job = st.session_state.download_job
    job_running = bool(job and job.get("running"))

    mode = st.radio("Download type", ["Single video", "Playlist"], horizontal=True, disabled=job_running)
    url_label = "Video URL" if mode == "Single video" else "Playlist URL"
    url = st.text_input(url_label, placeholder="https://youtube.com/...", disabled=job_running)
    quality = st.selectbox("MP3 quality", ["128", "192", "256", "320"], index=1, disabled=job_running)

    ffmpeg_location = None
    if detect_ffmpeg_location() == "":
        st.warning("ffmpeg/ffprobe not found in PATH. Install with `brew install ffmpeg`.")

    if not job_running and st.button("Generate MP3", type="primary"):
        clean_url = url.strip()
        if not clean_url:
            st.error("Please enter a URL.")
            return
        if not is_valid_url(clean_url):
            st.error("Invalid URL. Use a full link starting with http:// or https://")
            return

        new_job = initialize_job(mode=mode, url=clean_url, quality=quality, ffmpeg_location=ffmpeg_location)
        st.session_state.download_job = new_job
        worker = threading.Thread(target=run_job_worker, args=(new_job,), daemon=True)
        worker.start()
        st.rerun()

    job = st.session_state.download_job
    if not job:
        return

    status_text = st.empty()
    animation_slot = st.empty()
    progress_bar = st.progress(int(job.get("progress", 0)))
    render_download_animation(animation_slot)
    status_text.caption(build_status_line(job))

    if job.get("running"):
        if st.button("Cancel Download"):
            job["cancel_requested"] = True
            job["phase"] = "Cancelling..."
        if job.get("cancel_requested"):
            st.warning("Cancellation requested. Waiting for current step to stop...")
        time.sleep(0.5)
        st.rerun()

    animation_slot.empty()

    if job.get("status") == "success":
        payload = job.get("payload")
        if payload:
            st.success(payload["success"])
            st.download_button(
                label=payload["label"],
                data=payload["data"],
                file_name=payload["file_name"],
                mime=payload["mime"],
                type="primary",
            )
    elif job.get("status") == "cancelled":
        st.warning(job.get("error", "Download cancelled."))
    elif job.get("status") == "error":
        st.error(f"Download failed: {job.get('error', 'Unknown error')}")
        st.info(
            "If SSL fails on macOS Python, run: "
            "`open '/Applications/Python 3.13/Install Certificates.command'`"
        )

    if st.button("Start New Download"):
        st.session_state.download_job = None
        st.rerun()


if __name__ == "__main__":
    main()
