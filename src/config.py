"""Configuration settings for yt-ayochat governed RAG pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AppConfig:
    """Application and pipeline configuration."""

    # Google Cloud & Vertex AI settings
    google_cloud_project: str = field(
        default_factory=lambda: os.getenv("GOOGLE_CLOUD_PROJECT", "yt-ayochat-prod")
    )
    google_cloud_location: str = field(
        default_factory=lambda: os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    )
    gemini_model_name: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-pro")
    )
    gemini_temperature: float = 0.0
    gemini_top_p: float = 0.8
    gemini_max_output_tokens: int = 256

    # Vector store & embeddings
    embedding_model_name: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-3-small")
    )
    chroma_persist_directory: Path = field(
        default_factory=lambda: Path(os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db"))
    )
    chroma_collection_name: str = field(
        default_factory=lambda: os.getenv("CHROMA_COLLECTION_NAME", "youtube-rag-knowledge")
    )
    retrieval_k: int = 3
    similarity_threshold: float = 0.15

    # Rate limiting & circuit breaker
    rate_limit_max_requests_per_minute: int = 60
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout_sec: float = 30.0

    # YouTube API
    youtube_api_key: str = field(
        default_factory=lambda: os.getenv("YOUTUBE_API_KEY", "")
    )
    target_video_ids: list[str] = field(
        default_factory=lambda: [
            v.strip() for v in os.getenv("TARGET_VIDEO_IDS", "").split(",") if v.strip()
        ]
    )

    # Closed-Domain Refusal Response String
    refusal_message: str = (
        "Thanks for reaching out! I don't have information on that in our current "
        "video coverage or docs yet, but I'll make note of it for future content! 👍"
    )

    # Citation Format
    citation_prefix: str = "📌 Source: "


# Global default configuration instance
config = AppConfig()
