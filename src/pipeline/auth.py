"""YouTube API OAuth 2.0 Authentication Helper."""

from __future__ import annotations

import os
from typing import Any, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from src.config import config

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

# Module-level cache for authenticated channel ID
_cached_channel_id: Optional[str] = None


def get_credentials() -> Credentials:
    """Load or request OAuth 2.0 credentials, caching to token.json."""
    creds = None
    token_path = config.token_path
    client_secret_path = config.client_secret_path

    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception:
            pass

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds:
            if not os.path.exists(client_secret_path):
                raise FileNotFoundError(
                    f"OAuth client secrets file '{client_secret_path}' is missing. "
                    "Please download client_secret.json from Google Cloud Console."
                )
            
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secret_path, SCOPES
            )
            # Open browser for local flow consent
            creds = flow.run_local_server(port=0)

        # Save credentials for the next run
        try:
            with open(token_path, "w") as token:
                token.write(creds.to_json())
        except Exception:
            pass

    return creds


def get_youtube_client() -> Any:
    """Build and return an authenticated YouTube Data API v3 client."""
    creds = get_credentials()
    return build("youtube", "v3", credentials=creds)


def get_authenticated_channel_id(client: Optional[Any] = None) -> str:
    """Retrieve and cache the channel ID of the authenticated user."""
    global _cached_channel_id
    if _cached_channel_id is not None:
        return _cached_channel_id

    yt_client = client or get_youtube_client()
    try:
        response = yt_client.channels().list(mine=True, part="id").execute()
        items = response.get("items", [])
        if not items:
            raise ValueError("No YouTube channels found for the authenticated user.")
        _cached_channel_id = items[0]["id"]
        return _cached_channel_id
    except Exception as e:
        raise RuntimeError(f"Failed to retrieve channel ID for authenticated user: {e}")
