#!/bin/bash

# A shell script to execute yt-dlp with the provided parameters
# Usage: ./run_yt_dlp.sh [yt-dlp options]

# Check if yt-dlp is installed
if ! command -v yt-dlp &> /dev/null; then
    echo "❌ yt-dlp is not installed or not found in PATH."
    echo "👉 Please install yt-dlp: https://github.com/yt-dlp/yt-dlp#installation"
    exit 1
fi

# Check if any arguments were provided
if [ "$#" -eq 0 ]; then
    echo "❌ No arguments provided."
    echo "👉 Usage: ./run_yt_dlp.sh [yt-dlp options]"
    exit 1
fi

# Execute yt-dlp with the provided arguments
echo "🔍 Running yt-dlp with the following arguments: $@"
uv add --dev ffmpeg-python yt-dlp
uv run yt-dlp "$@"

# Check the exit status of yt-dlp
if [ $? -eq 0 ]; then
    echo "✅ yt-dlp command executed successfully."
else
    echo "❌ yt-dlp command failed. Please check the output above for details."
    exit 1
fi