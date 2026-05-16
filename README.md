# YT to MP3

Simple YouTube-to-MP3 app with:
- Interactive CLI (`yt_to_mp3.py`)
- Web frontend using Streamlit (`app.py`)

## Requirements

- Python 3.9+
- `ffmpeg` installed on your machine (includes `ffprobe`)

macOS install:

```bash
brew install ffmpeg
```

## Install

```bash
pip3 install -r requirements.txt
```

## Usage

### Web frontend (recommended)

```bash
python3 -m streamlit run app.py
```

This opens a simple web UI where you can:
- Choose single video or playlist
- Paste the URL
- Pick MP3 quality
- Download directly in browser (standard website behavior)
- See live progress bar + download animation while processing

Web download behavior:
- Single video: downloads `.mp3` file directly in browser
- Playlist: downloads a `.zip` containing all MP3 files
- Shows file-level progress (`x/y`) for playlist, speed, and ETA
- Includes a `Cancel Download` button for long downloads

### CLI

```bash
python3 yt_to_mp3.py
```

Then follow the prompt:
- Choose `1` for single video or `2` for playlist.
- Paste the link in terminal.
- Choose quality (`128/192/256/320`, default `192`).
- If `ffmpeg` is not in PATH, enter the folder path containing `ffmpeg` and `ffprobe`.
- SSL certificate checks are disabled by default (trusted-network mode).

## Output

- Single video: saved in `downloads/`
- Playlist: each playlist is saved in its own folder inside `downloads/`

## Deploy on Render (no separate API)

This repo includes `render.yaml` for one-click setup.

1. Push repo to GitHub
2. In Render, create a new Blueprint service from this repo
3. Render will use:
   - Build: `pip3 install -r requirements.txt`
   - Start: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
