"""Telemetry and structured audit logging schemas for yt-ayochat."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SecurityVerdict(str, Enum):
    """Verdict of the Semantic Guardrails & Policy (SGP) inspection."""
    ALLOWED = "ALLOWED"
    SANITIZED = "SANITIZED"
    BLOCKED = "BLOCKED"


class DispatchStatus(str, Enum):
    """Dispatch status to external YouTube Comment thread."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    BLOCKED = "BLOCKED"


class VectorRetrievalMetrics(BaseModel):
    """Metrics captured during vector search retrieval."""
    retrieved_chunk_ids: List[str] = Field(default_factory=list)
    cosine_scores: List[float] = Field(default_factory=list)
    retrieval_latency_ms: float = 0.0


class GenerationMetrics(BaseModel):
    """Metrics captured during LLM inference."""
    token_count: int = 0
    generation_latency_ms: float = 0.0
    refusal_triggered: bool = False


class AuditLogRecord(BaseModel):
    """Full lifecycle telemetry record emitted to Google Cloud Logging."""
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    trace_id: str
    author_hash: str
    comment_id: str
    sanitized_query: str
    raw_query_length: int
    security_verdict: SecurityVerdict
    security_details: Optional[Dict[str, Any]] = None
    vector_retrieval_metrics: Optional[VectorRetrievalMetrics] = None
    generation_metrics: Optional[GenerationMetrics] = None
    dispatch_status: DispatchStatus
    http_status: Optional[int] = None
    error_message: Optional[str] = None
    room_temperature: Optional[str] = None
    comment_category: Optional[str] = None
    semiotic_intent: Optional[str] = None
    energy_level: Optional[int] = None

    @classmethod
    def create(
        cls,
        trace_id: str,
        author_id: str,
        comment_id: str,
        sanitized_query: str,
        raw_query_length: int,
        security_verdict: SecurityVerdict,
        security_details: Optional[Dict[str, Any]] = None,
        vector_retrieval_metrics: Optional[VectorRetrievalMetrics] = None,
        generation_metrics: Optional[GenerationMetrics] = None,
        dispatch_status: DispatchStatus = DispatchStatus.SKIPPED,
        http_status: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> AuditLogRecord:
        """Helper to create an AuditLogRecord with automatic author hashing."""
        author_hash = hashlib.sha256(author_id.encode("utf-8")).hexdigest()
        return cls(
            trace_id=trace_id,
            author_hash=author_hash,
            comment_id=comment_id,
            sanitized_query=sanitized_query,
            raw_query_length=raw_query_length,
            security_verdict=security_verdict,
            security_details=security_details,
            vector_retrieval_metrics=vector_retrieval_metrics,
            generation_metrics=generation_metrics,
            dispatch_status=dispatch_status,
            http_status=http_status,
            error_message=error_message,
        )
