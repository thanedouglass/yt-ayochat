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
    client_secret_path: str = field(
        default_factory=lambda: os.getenv("YOUTUBE_CLIENT_SECRET_PATH", "client_secret.json")
    )
    token_path: str = field(
        default_factory=lambda: os.getenv("YOUTUBE_TOKEN_PATH", "token.json")
    )
    target_video_ids: list[str] = field(
        default_factory=lambda: [
            v.strip() for v in os.getenv("TARGET_VIDEO_IDS", "").split(",") if v.strip()
        ]
    )

    # Telegram Bot & Mobile HITL Pipeline
    telegram_bot_token: str = field(
        default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", "")
    )
    telegram_chat_id: str = field(
        default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", "")
    )
    telegram_webhook_secret: str = field(
        default_factory=lambda: os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    )
    hitl_db_path: Path = field(
        default_factory=lambda: Path(os.getenv("HITL_DB_PATH", "data/hitl_state.db"))
    )
    hitl_alignment_path: Path = field(
        default_factory=lambda: Path(os.getenv("HITL_ALIGNMENT_PATH", "data/lumi_hitl_alignment.jsonl"))
    )

    # Mobile PWA companion API
    pwa_api_key: str = field(
        default_factory=lambda: os.getenv("PWA_API_KEY", "")
    )
    pwa_allow_unauthenticated: bool = field(
        default_factory=lambda: os.getenv("PWA_ALLOW_UNAUTHENTICATED", "false").lower() == "true"
    )
    dispatch_dry_run: bool = field(
        default_factory=lambda: os.getenv("DISPATCH_DRY_RUN", "true").lower() == "true"
    )
    cors_allowed_origins: list[str] = field(
        default_factory=lambda: [
            o.strip()
            for o in os.getenv(
                "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
            ).split(",")
            if o.strip()
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
