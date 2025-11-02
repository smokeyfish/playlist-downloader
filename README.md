# YouTube Playlist Downloader & Manager

```
    /\___/\
   (  o o  )
   (  =^=  ) 
    (--m-m-)
```

A Python tool that downloads videos from a YouTube playlist and optionally removes them from the playlist afterwards. Videos are automatically organized into subdirectories by channel name.

## Features

- 📥 Downloads videos from YouTube playlists using yt-dlp
- 📁 Organizes downloads by YouTube channel name
- 🗑️ Optional playlist cleanup after download
- 🔐 Secure OAuth2 authentication with YouTube API
- 🐋 Docker support for containerized execution

## Prerequisites

- Python 3.11 or higher
- `yt-dlp` installed on your system
- A Google Cloud project with YouTube Data API v3 enabled (for the video removal process)
- OAuth 2.0 credentials (`client_secret.json`)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/smokeyfish/playlist-downloader.git
cd playlist-downloader
```

2. Create and activate a virtual environment:
```bash
uv venv
source .venv/bin/activate  # On macOS/Linux
```

3. Install the package:
```bash
uv pip install -e ".[dev]"
```

## Configuration

1. Create a project in the [Google Cloud Console](https://console.cloud.google.com)
2. Enable the YouTube Data API v3
3. Create OAuth 2.0 credentials and download as `client_secret.json`
4. Place `client_secret.json` in the project root directory

## Usage

### Command Line

```bash
python -m playlist_downloader
```

### Docker

```bash
docker-compose up --build
```

## Configuration Options

Edit `main()` in `__init__.py` to customize:

```python
config = YouTubeConfig(
    client_secrets_file="client_secret.json",
    token_pickle_file="token.pickle",
    playlist_url="YOUR_PLAYLIST_URL",
    playlist_id="YOUR_PLAYLIST_ID",
    download_dir="downloads"
)
```

## Project Structure

```
playlist_downloader/
├── src/
│   └── playlist_downloader/
│       └── __init__.py
├── downloads/           # Downloaded videos go here
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## Development

This project uses:
- `uv` for dependency management
- `black` for code formatting
- `pre-commit` hooks for code quality

Setup development environment:
```bash
uv pip install -e ".[dev]"
pre-commit install
```

## License

MIT License - See LICENSE file for details.