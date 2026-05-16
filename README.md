# YT to MP3

Simple Python script to download a YouTube video's audio and convert it to MP3.

## Requirements

- Python 3.9+
- `ffmpeg` installed on your machine

## Install

```bash
pip install -r requirements.txt
```

## Usage

```bash
python yt_to_mp3.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Optional flags

- `--output-dir downloads` (default)
- `--quality 128|192|256|320` (default: `192`)
- `--filename "%(title)s.%(ext)s"` (default)

Example:

```bash
python yt_to_mp3.py "https://www.youtube.com/watch?v=VIDEO_ID" --output-dir music --quality 320
```
