FROM python:3.11-slim

# Install system dependencies including yt-dlp
RUN apt-get update && apt-get install -y \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Install yt-dlp
RUN uv pip install yt-dlp

# Set working directory
WORKDIR /app

# Copy the project files
COPY pyproject.toml .
COPY . .

# Create downloads directory
RUN mkdir -p downloads

# Install dependencies using uv
RUN uv pip install --no-cache .

# Run the script
ENTRYPOINT ["python", "main.py"]