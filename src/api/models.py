"""Domain schemas and Pydantic models for the Async API & Telegram HITL Pipeline."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HITLStatus(str, Enum):
    """Lifecycle status of a comment awaiting or undergoing HITL review."""
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    EDITED = "EDITED"
    SKIPPED = "SKIPPED"
    DISPATCHED = "DISPATCHED"
    FAILED = "FAILED"


class HITLVerdict(str, Enum):
    """Human-in-the-loop review decision."""
    YES = "YES"
    YES_WITH_EDITS = "YES_WITH_EDITS"
    NO = "NO"
    SKIP = "SKIP"


class HITLCommentRecord(BaseModel):
    """Stored SQLite database entity representing a comment in the HITL pipeline."""
    id: str = Field(..., description="Unique record identifier (UUID)")
    comment_id: str = Field(..., description="YouTube comment ID")
    video_id: str = Field(..., description="YouTube video ID")
    video_title: str = Field(default="YouTube Video", description="Target video title")
    author_name: str = Field(..., description="Comment author username or handle")
    input_comment: str = Field(..., description="Original comment text")
    language: str = Field(default="en", description="Detected language code (en, es, ar, pt)")
    category: str = Field(..., description="Perception category (HYPE, DANCE_CHOREO, BANTER, etc.)")
    semiotic_intent: str = Field(..., description="Inferred semiotic intent")
    energy_level: int = Field(default=3, description="Energy voltage rating (1 to 5)")
    polarity: float = Field(default=0.0, description="Sentiment polarity (-1.0 to 1.0)")
    model_draft_reply: str = Field(..., description="Gemini 3.7 Flash structured draft reply")
    applied_vectors: Dict[str, Any] = Field(default_factory=dict, description="4D sentiment vectors (alpha, beta, gamma, tau)")
    cultural_alignment_flag: bool = Field(default=True, description="Persona alignment verification status")
    rationale: Optional[str] = Field(default=None, description="Generation logic and grounding rationale")
    status: HITLStatus = Field(default=HITLStatus.PENDING_APPROVAL, description="Current workflow status")
    telegram_message_id: Optional[int] = Field(default=None, description="Telegram message ID for callback correlation")
    human_verdict: Optional[HITLVerdict] = Field(default=None, description="Creator verdict")
    human_score: Optional[float] = Field(default=None, description="Human score (1.0 - 5.0)")
    final_dispatched_reply: Optional[str] = Field(default=None, description="Final approved or edited text dispatched to YouTube")
    diff_json: Optional[Dict[str, Any]] = Field(default=None, description="Diff between draft and human edit")
    alignment_delta: Optional[float] = Field(default=None, description="Calculated vector distance delta Δ")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 update timestamp")


class PollCommentsRequest(BaseModel):
    """Payload to trigger video polling and Swarm processing."""
    video_id: str = Field(default="dtvsnt1OMy4", description="YouTube video ID or full URL")
    limit: int = Field(default=5, ge=1, le=50, description="Number of comments to poll and draft")
    send_telegram: bool = Field(default=True, description="Whether to dispatch alerts to Telegram Bot")
    auto_approve: bool = Field(default=False, description="Automatically approve without waiting for HITL")
    dry_run: bool = Field(default=True, description="Strict dry run (bypasses live YouTube API dispatch)")


class PollCommentsResponse(BaseModel):
    """Response returned from comment polling and draft synthesis."""
    status: str = Field(..., description="Execution status ('success' or 'error')")
    video_id: str = Field(..., description="Processed video ID")
    video_title: str = Field(..., description="Processed video title")
    total_polled: int = Field(..., description="Count of comments ingested")
    records: List[HITLCommentRecord] = Field(default_factory=list, description="Created or updated HITL records")
    telegram_notifications_sent: int = Field(default=0, description="Number of Telegram notifications dispatched")
    message: str = Field(..., description="Human-readable result summary")


class TelegramWebhookUpdate(BaseModel):
    """Telegram Bot API Update object structure."""
    update_id: int = Field(..., description="Unique update identifier")
    message: Optional[Dict[str, Any]] = Field(default=None, description="Incoming message object")
    callback_query: Optional[Dict[str, Any]] = Field(default=None, description="Incoming callback query object")


class TelegramActionResponse(BaseModel):
    """Response payload resulting from processing a Telegram command."""
    status: str = Field(..., description="'success' or 'ignored'")
    action: str = Field(..., description="'approved', 'edited', 'skipped', 'status', or 'help'")
    record_id: Optional[str] = Field(default=None, description="Associated database record ID")
    comment_id: Optional[str] = Field(default=None, description="Associated YouTube comment ID")
    reply_text: Optional[str] = Field(default=None, description="Final approved/edited reply string")
    alignment_delta: Optional[float] = Field(default=None, description="Vector alignment delta for edits")
    dispatched: bool = Field(default=False, description="Whether dispatched to YouTube / Dispatcher")
    message: str = Field(..., description="Action summary sent back to Telegram user")


class ManualActionRequest(BaseModel):
    """REST payload for manual approval or editing of a pending comment."""
    edited_reply: Optional[str] = Field(default=None, description="Calibrated reply if editing")
    author_alpha: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Author target code-switch vector")
    author_beta: Optional[str] = Field(default=None, description="Author target sovereignty strategy")
    author_gamma: Optional[int] = Field(default=None, ge=1, le=5, description="Author target frequency resonance")
    notes: Optional[str] = Field(default="Calibrated via REST API", description="Calibration notes")
    dry_run: bool = Field(default=True, description="Whether to execute dry-run dispatch")


class HITLStatsResponse(BaseModel):
    """Aggregate statistics of the HITL database."""
    total_records: int
    pending_approval: int
    approved: int
    edited: int
    skipped: int
    dispatched: int
