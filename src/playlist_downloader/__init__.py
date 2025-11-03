"""
Youtube Playlist Downloader
"""

import os
import pickle
import shlex
import smtplib
import socket
import subprocess
import traceback
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# ---------------------------
# Configuration
# ---------------------------
@dataclass
class YouTubeConfig:
    scopes: List[str] = None
    client_secrets_file: str = ""
    token_pickle_file: str = "token.pickle"
    playlist_url: Optional[str] = None
    playlist_id: Optional[str] = None
    download_dir: str = "downloads"
    notification_email: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None

    def __post_init__(self):
        if self.scopes is None:
            self.scopes = ["https://www.googleapis.com/auth/youtube.force-ssl"]

        # Extract playlist_id from URL if not explicitly set
        if not self.playlist_id and self.playlist_url:
            import re

            if match := re.search(r"[?&]list=([^&]+)", self.playlist_url):
                self.playlist_id = match.group(1)


# ---------------------------
# Authentication
# ---------------------------
class YouTubeAuthenticator:
    def __init__(self, config: YouTubeConfig):
        self.config = config
        self._service = None
        self.email_notifier = EmailNotifier(config)

    def get_service(self):
        """Return an authenticated YouTube API client (cached)."""
        if self._service is not None:
            return self._service

        if not check_internet_connection():
            print("❌ No internet connection available. Cannot authenticate.")
            raise ConnectionError("No internet connection available")

        creds = None
        # Load cached credentials if available
        if os.path.exists(self.config.token_pickle_file):
            try:
                with open(self.config.token_pickle_file, "rb") as token:
                    creds = pickle.load(token)
            except Exception:
                # Corrupt or incompatible token file; ignore and re-auth
                creds = None

        # If no valid credentials, go through OAuth flow
        if not creds or not getattr(creds, "valid", False):
            if creds and getattr(creds, "expired", False) and getattr(creds, "refresh_token", None):
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.config.client_secrets_file,
                    self.config.scopes,
                )

                def handle_auth_url(auth_url):
                    print(f"🔐 Please authorize using this URL:\n{auth_url}")
                    self.email_notifier.send_auth_url(auth_url)

                creds = flow.run_local_server(
                    port=0,
                    authorization_prompt_message="Please check your email or terminal for the authorization URL.",
                    success_message="Authorization successful! You may close this window.",
                    open_browser=False,
                    authorization_url_callback=handle_auth_url,
                )

            # Save the credentials for future runs
            with open(self.config.token_pickle_file, "wb") as token:
                pickle.dump(creds, token)

        self._service = build("youtube", "v3", credentials=creds)
        return self._service


# ---------------------------
# Playlist operations
# ---------------------------
class YouTubePlaylistManager:
    def __init__(self, service, playlist_id: str):
        self.youtube = service
        self.playlist_id = playlist_id

    def list_items(self) -> List[Dict[str, Any]]:
        """Retrieve all items (videos) in the playlist."""
        items: List[Dict[str, Any]] = []
        next_page_token: Optional[str] = None

        while True:
            request = self.youtube.playlistItems().list(
                part="id,snippet",
                maxResults=50,
                playlistId=self.playlist_id,
                pageToken=next_page_token,
            )
            try:
                response = request.execute()
            except HttpError as e:
                print(f"❌ Failed to retrieve playlist items: {e}")
                break

            items.extend(response.get("items", []))
            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

        return items

    def delete_items(self, items: List[Dict[str, Any]]) -> None:
        """Delete the provided playlist items by their playlist item ID."""
        for item in items:
            playlist_item_id = item.get("id")
            title = item.get("snippet", {}).get("title", "Unknown Title")
            print(f"🗑️ Deleting: {title} (Item ID: {playlist_item_id})")

            try:
                self.youtube.playlistItems().delete(id=playlist_item_id).execute()
            except HttpError as e:
                print(f"❌ Failed to delete item {playlist_item_id}: {e}")


# ---------------------------
# Download operations
# ---------------------------
class PlaylistDownloader:
    def __init__(
        self,
        playlist_url: str,
        download_dir: str = "downloads",
        video_list: List[Dict[str, Any]] = [],
    ):
        self.playlist_url = playlist_url
        self.download_dir = download_dir
        self.video_list = video_list

    def download(self) -> None:
        """Download videos from the playlist using the external shell script run_yt_dlp.sh."""
        if not self.playlist_url:
            print("⚠️ No playlist URL provided; skipping download.")
            return

        if not check_internet_connection():
            print("❌ No internet connection available. Skipping download.")
            return

        # Create downloads directory if it doesn't exist
        os.makedirs(self.download_dir, exist_ok=True)

        for video_details in self.video_list:
            video_id = video_details["snippet"]["resourceId"]["videoId"]
            title = video_details["snippet"]["title"]
            print(f" - {title} (https://www.youtube.com/watch?v={video_id})")

            # Use the -f parameter with the specified format
            fmt_selector = "bestvideo[height<=1080]+bestaudio/best[height<=1080]"

            # Update output template to include channel name in path
            output_template = os.path.join(self.download_dir, "%(channel)s", "%(title)s.%(ext)s")

            video_url = f"https://www.youtube.com/watch?v={video_id}"

            # Call the external shell script
            command = f"./run_yt_dlp.sh -f {shlex.quote(fmt_selector)} -o {shlex.quote(output_template)} --restrict-filenames {shlex.quote(video_url)}"

            try:
                subprocess.run(command, shell=True, executable="/bin/bash", check=True)
                print("✅ Download completed successfully.")
            except subprocess.CalledProcessError as e:
                print(f"❌ yt-dlp error: {e}")
            except FileNotFoundError:
                print("❌ The shell script run_yt_dlp.sh is not found or not executable.")


# ---------------------------
# Email Notifications
# ---------------------------
class EmailNotifier:
    def __init__(self, config: YouTubeConfig):
        self.config = config

    def send_auth_url(self, auth_url: str) -> None:
        """Send authentication URL via email if email configuration is present."""
        if not self.config.notification_email:
            return

        if not (self.config.smtp_username and self.config.smtp_password):
            print("⚠️ SMTP credentials not configured; skipping email notification")
            return

        try:
            msg = EmailMessage()
            msg.set_content(
                f"""
            Your YouTube Playlist Downloader authentication URL is ready:

            {auth_url}

            Click the link above to authenticate the application.
            """
            )

            msg["Subject"] = "YouTube Playlist Downloader Authentication"
            msg["From"] = self.config.smtp_username
            msg["To"] = self.config.notification_email

            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.smtp_username, self.config.smtp_password)
                server.send_message(msg)
                print(f"✉️ Authentication URL sent to {self.config.notification_email}")
        except Exception as e:
            print(f"❌ Failed to send email: {e}")


# ---------------------------
# Facade / Orchestration
# ---------------------------
class PlaylistTruncator:
    """High-level workflow: optionally download, then delete items from a playlist."""

    def __init__(self, config: YouTubeConfig):
        self.config = config
        self.auth = YouTubeAuthenticator(config)

    def run(self, download_first: bool = True) -> None:
        try:
            if not check_internet_connection():
                print(
                    "❌ No internet connection available. Please check your connection and try again."
                )
                return

            # Step 2: Authenticate
            youtube = self.auth.get_service()

            manager = YouTubePlaylistManager(youtube, self.config.playlist_id)
            items = manager.list_items()
            print(f"🔍 Found {len(items)} videos in the playlist.")

            # Step 1: (Optional) Download videos
            if download_first and self.config.playlist_url:
                PlaylistDownloader(
                    playlist_url=self.config.playlist_url,
                    download_dir=self.config.download_dir,
                    video_list=items,
                ).download()

            # Step 3: List & delete items
            if not self.config.playlist_id:
                print("❌ No playlist_id configured; aborting deletion.")
                return

            if items:
                manager.delete_items(items)
                print("🧹 All videos deleted from the playlist.")
            else:
                print("📭 Playlist is already empty.")

        except ConnectionError as e:
            print(f"❌ Network error: {e}")
        except Exception as e:
            print(f"❗ An unexpected error occurred: {e}")
            traceback.print_exc()


# ---------------------------
# CLI Entrypoint
# ---------------------------
def main():
    config = YouTubeConfig(
        client_secrets_file="client_secret.json",
        token_pickle_file="token.pickle",
        playlist_url="https://www.youtube.com/playlist?list=PLpcF9uuJUqHs5Mu3subvLvAWkjyDtMfoH",
        # Email configuration (optional)
        notification_email=os.environ.get("YTDOWNLOADER_NOTIFICATION_EMAIL", None),
        smtp_username=os.environ.get("YTDOWNLOADER_SMTP_USERNAME", None),
        smtp_password=os.environ.get("YTDOWNLOADER_SMTP_PASSWORD", None),
    )

    truncator = PlaylistTruncator(config)
    truncator.run(download_first=True)


# ---------------------------
# Network Helper Functions
# ---------------------------
def check_internet_connection() -> bool:
    """Test if we have an active internet connection."""
    try:
        # Try to connect to Google's DNS server
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except (socket.timeout, socket.gaierror, OSError):
        return False


if __name__ == "__main__":
    main()
