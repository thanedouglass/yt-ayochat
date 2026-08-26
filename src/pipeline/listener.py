"""Ingestion Listener for polling YouTube Data API v3 and filtering comments."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set

from src.config import config


@dataclass
class InboundComment:
    """Normalized inbound YouTube comment item."""
    comment_id: str
    video_id: str
    author_name: str
    author_channel_id: str
    text_original: str
    published_at: str
    parent_id: Optional[str] = None


class CommentTriggerFilter:
    """Filters incoming YouTube comments for actionability and intent triggers."""

    DEFAULT_KEYWORDS = {"#ask", "@ai", "@bot", "help", "how", "what", "where", "when", "why", "which"}

    def __init__(self, keywords: Optional[Set[str]] = None, require_question: bool = False) -> None:
        self.keywords = {k.lower() for k in (keywords or self.DEFAULT_KEYWORDS)}
        self.require_question = require_question

    def should_process(self, text: str) -> bool:
        """Determine if comment contains a question or trigger keyword."""
        cleaned = text.strip().lower()
        if not cleaned:
            return False

        # If question mark is present, process
        if "?" in cleaned:
            return True

        # Check for keyword trigger match
        words = set(re.findall(r"\b\w+\b|[#@]\w+", cleaned))
        if any(kw in words for kw in self.keywords):
            return True

        return not self.require_question


class YouTubeCommentListener:
    """Dedicated worker to poll YouTube Data API v3 for target video comments."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        filter_fn: Optional[CommentTriggerFilter] = None,
        youtube_client: Optional[Any] = None,
    ) -> None:
        self.api_key = api_key or config.youtube_api_key
        self.filter = filter_fn or CommentTriggerFilter()
        self.processed_comment_ids: Set[str] = set()
        self._youtube_client = youtube_client

    def _get_client(self) -> Any:
        """Lazy-load YouTube Data API v3 client."""
        if self._youtube_client is not None:
            return self._youtube_client
        try:
            from src.pipeline.auth import get_youtube_client
            self._youtube_client = get_youtube_client()
            return self._youtube_client
        except Exception:
            if not self.api_key:
                return None
            try:
                from googleapiclient.discovery import build
                self._youtube_client = build("youtube", "v3", developerKey=self.api_key)
                return self._youtube_client
            except Exception:
                return None

    def _get_author_channel_id(self) -> Optional[str]:
        """Get the authenticated author's channel ID."""
        client = self._get_client()
        if client is None:
            return None
        try:
            from src.pipeline.auth import get_authenticated_channel_id
            return get_authenticated_channel_id(client)
        except Exception:
            return None

    def poll_video_comments(
        self,
        video_id: str,
        max_results: int = 20,
    ) -> List[InboundComment]:
        """Poll top-level comment threads for a given video ID and filter for actionable items."""
        client = self._get_client()
        if client is None:
            return []

        try:
            request = client.commentThreads().list(
                part="snippet",
                videoId=video_id,
                textFormat="plainText",
                maxResults=max_results,
                order="time",
            )
            response = request.execute()
            items = response.get("items", [])
        except Exception:
            return []

        author_channel_id = self._get_author_channel_id()

        inbound_comments: List[InboundComment] = []
        for item in items:
            snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
            cid = item.get("id")
            text = snippet.get("textDisplay") or snippet.get("textOriginal", "")
            author = snippet.get("authorDisplayName", "Unknown")
            channel_id = snippet.get("authorChannelId", {}).get("value", author)
            published = snippet.get("publishedAt", "")

            if not cid or cid in self.processed_comment_ids:
                continue

            # Skip if the channel author has already replied to this comment thread
            if author_channel_id:
                total_replies = item.get("snippet", {}).get("totalReplyCount", 0)
                if total_replies > 0:
                    try:
                        replies_request = client.comments().list(
                            part="snippet",
                            parentId=cid,
                            maxResults=100
                        )
                        replies_response = replies_request.execute()
                        has_author_reply = False
                        for reply in replies_response.get("items", []):
                            reply_author_id = reply.get("snippet", {}).get("authorChannelId", {}).get("value")
                            if reply_author_id == author_channel_id:
                                has_author_reply = True
                                break
                        if has_author_reply:
                            continue
                    except Exception:
                        pass

            if self.filter.should_process(text):
                inbound_comments.append(
                    InboundComment(
                        comment_id=cid,
                        video_id=video_id,
                        author_name=author,
                        author_channel_id=channel_id,
                        text_original=text,
                        published_at=published,
                    )
                )

        return inbound_comments

    def mark_processed(self, comment_id: str) -> None:
        """Mark a comment ID as processed to prevent duplicate replies."""
        self.processed_comment_ids.add(comment_id)
