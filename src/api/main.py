"""FastAPI Asynchronous Backend & Mobile Telegram HITL Pipeline for YT-AyoChat."""

from __future__ import annotations

import difflib
import hmac
import html
import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from scripts.audit_video_replies import VideoReplyAuditor, parse_video_id
from src.api.db import db
from src.api.models import (
    HITLCommentRecord,
    HITLStatsResponse,
    HITLStatus,
    HITLVerdict,
    ManualActionRequest,
    PollCommentsRequest,
    PollCommentsResponse,
    TelegramActionResponse,
    TelegramWebhookUpdate,
)
from src.api.telegram_service import telegram_service
from src.config import config
from src.pipeline.dispatcher import ActionDispatcher
from src.telemetry.schema import DispatchStatus

logger = logging.getLogger("yt_ayochat.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle event handler."""
    logger.info("Initializing YT-AyoChat Async HITL API and SQLite state store...")
    db.init_db()
    yield
    logger.info("Shutting down YT-AyoChat Async HITL API...")


app = FastAPI(
    title="YT-AyoChat Async Backend & Mobile Telegram HITL API",
    description=(
        "Cloud-ready asynchronous REST API orchestrating the Lumi 3-Node Swarm, "
        "SQLite state management, and real-time mobile Telegram Human-in-the-Loop review."
    ),
    version="2.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)


# --------------------------------------------------------------------------
# Helper Functions
# --------------------------------------------------------------------------

def calculate_alignment_delta(
    model_vectors: Dict[str, Any],
    author_alpha: float = 0.90,
    author_beta: str = "CLAPBACK",
    author_gamma: int = 4,
    author_tau: str = "Pass (1 Sentence)",
) -> float:
    """Calculate Euclidean distance alignment delta between model and calibrated author vectors."""
    m_alpha = float(model_vectors.get("code_switch_alpha", 0.70))
    m_beta = str(model_vectors.get("sovereignty_beta", "COMMUNITY"))
    m_gamma = int(model_vectors.get("frequency_gamma", 3))
    m_tau = str(model_vectors.get("token_economy_tau", "Pass (1 Sentence)"))

    alpha_diff = (m_alpha - author_alpha) ** 2
    gamma_diff = ((m_gamma - author_gamma) / 4.0) ** 2
    beta_penalty = 0.0 if m_beta == author_beta else 0.5
    tau_penalty = 0.0 if m_tau == author_tau else 0.25

    return round((alpha_diff + gamma_diff + beta_penalty + tau_penalty) ** 0.5, 4)


def append_fine_tuning_record(
    record: HITLCommentRecord,
    final_reply: str,
    verdict: HITLVerdict,
    alignment_delta: float = 0.0,
    notes: str = "",
) -> None:
    """Append validated HITL decision to lumi_hitl_alignment.jsonl dataset."""
    try:
        alignment_file = config.hitl_alignment_path
        alignment_file.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "id": f"HITL-API-{record.id[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "video_id": record.video_id,
            "video_title": record.video_title,
            "comment_id": record.comment_id,
            "author_id": record.author_name,
            "input_comment": record.input_comment,
            "language": record.language,
            "is_safe": True,
            "perception_metadata": {
                "category": record.category,
                "semiotic_intent": record.semiotic_intent,
                "energy_level": record.energy_level,
                "polarity": record.polarity,
            },
            "agent_draft_reply": record.model_draft_reply,
            "human_verdict": verdict.value,
            "human_score": record.human_score or 5.0,
            "final_dispatched_reply": final_reply,
            "diff": record.diff_json,
            "reviewer_notes": notes or "Reviewed via Telegram Mobile HITL / REST API",
            "fine_tuning_export": {
                "prompt": f"<inbound_comment>{record.input_comment}</inbound_comment>\n<intent>{record.semiotic_intent}</intent>",
                "completion": final_reply,
            },
            "model_sentiment_vector": record.applied_vectors,
            "alignment_delta": alignment_delta,
            "scenario_id": f"VIDEO_{record.video_id}",
        }

        with open(alignment_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"Failed to append to hitl alignment jsonl: {e}")


# --------------------------------------------------------------------------
# Phase 1: Health & Diagnostics
# --------------------------------------------------------------------------

@app.get("/api/health", tags=["Health"])
async def get_health_status() -> Dict[str, Any]:
    """Check status of API server, SQLite database, and Telegram integration."""
    stats = db.get_hitl_stats()
    return {
        "status": "healthy",
        "service": "YT-AyoChat Async Backend & Telegram HITL API",
        "version": "2.1.0",
        "database": {
            "path": str(db.db_path),
            "total_records": stats.total_records,
            "pending_approval": stats.pending_approval,
        },
        "telegram": {
            "configured": telegram_service.is_configured,
            "default_chat_id_set": bool(telegram_service.default_chat_id),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# --------------------------------------------------------------------------
# Phase 2: Ingestion & Polling Endpoint (POST /api/poll-comments)
# --------------------------------------------------------------------------

@app.post("/api/poll-comments", response_model=PollCommentsResponse, tags=["HITL Ingestion"])
async def poll_and_draft_comments(
    req: PollCommentsRequest,
    background_tasks: BackgroundTasks,
) -> PollCommentsResponse:
    """Ingest comments for a YouTube video, run the Lumi Swarm, save drafts to SQLite, and alert Telegram.
    
    Workflow:
    1. Parse video ID (extract 11-char ID from full URL or shorthand).
    2. Ingest real/sample comments via VideoReplyAuditor.
    3. Run Model Armor, Supervisor context, Perception + Council, and Gemini 3.7 Flash generation.
    4. Store each generated draft in SQLite database as 'PENDING_APPROVAL'.
    5. Trigger Telegram alert for creators to review on mobile.
    """
    clean_id = parse_video_id(req.video_id)
    auditor = VideoReplyAuditor(video_id=clean_id, limit=req.limit, dry_run=req.dry_run)

    comments = auditor.fetch_comments()
    if not comments:
        return PollCommentsResponse(
            status="success",
            video_id=clean_id,
            video_title=auditor.video_title,
            total_polled=0,
            records=[],
            telegram_notifications_sent=0,
            message=f"No new comments found to poll for video {clean_id}.",
        )

    records: List[HITLCommentRecord] = []
    telegram_sent_count = 0
    now = datetime.now(timezone.utc).isoformat()

    for comment in comments:
        # Check if we already have this comment drafted and pending
        existing = db.get_comment_by_comment_id(comment.comment_id)
        if existing and existing.status == HITLStatus.PENDING_APPROVAL:
            records.append(existing)
            continue

        # Execute full Swarm pipeline logic
        audit_res = auditor.audit_comment(comment)

        rec_id = str(uuid.uuid4())
        record = HITLCommentRecord(
            id=rec_id,
            comment_id=comment.comment_id,
            video_id=clean_id,
            video_title=auditor.video_title,
            author_name=comment.author_name,
            input_comment=comment.text_original,
            language=audit_res.get("language", "en"),
            category=audit_res.get("category", "BANTER"),
            semiotic_intent=audit_res.get("semiotic_intent", "COMMUNITY_BANTER"),
            energy_level=audit_res.get("energy_level", 3),
            polarity=audit_res.get("polarity", 0.0),
            model_draft_reply=audit_res.get("reply_text", "Leaving unbothered vibes in the chat today."),
            applied_vectors=audit_res.get("applied_vectors", {}),
            cultural_alignment_flag=audit_res.get("cultural_alignment_flag", True),
            rationale=audit_res.get("rationale"),
            status=HITLStatus.PENDING_APPROVAL,
            created_at=now,
            updated_at=now,
        )

        if req.auto_approve:
            record.status = HITLStatus.APPROVED
            record.human_verdict = HITLVerdict.YES
            record.human_score = 5.0
            record.final_dispatched_reply = record.model_draft_reply
            db.insert_hitl_comment(record)
            append_fine_tuning_record(record, record.model_draft_reply, HITLVerdict.YES, notes="Auto-approved via API")
        else:
            # Save pending record to SQLite
            db.insert_hitl_comment(record)

            # Send Telegram mobile notification if requested
            if req.send_telegram:
                msg_id = await telegram_service.send_hitl_notification(record)
                if msg_id:
                    db.update_telegram_message_id(record.id, msg_id)
                    record.telegram_message_id = msg_id
                    telegram_sent_count += 1

        records.append(record)

    return PollCommentsResponse(
        status="success",
        video_id=clean_id,
        video_title=auditor.video_title,
        total_polled=len(records),
        records=records,
        telegram_notifications_sent=telegram_sent_count,
        message=f"Successfully processed {len(records)} comments for video '{auditor.video_title}'.",
    )


# --------------------------------------------------------------------------
# Phase 3: Webhook Endpoint (POST /api/telegram-webhook)
# --------------------------------------------------------------------------

@app.post("/api/telegram-webhook", response_model=TelegramActionResponse, tags=["Telegram Webhook"])
async def handle_telegram_webhook(
    update: TelegramWebhookUpdate,
    x_telegram_bot_api_secret_token: Optional[str] = Header(None),
) -> TelegramActionResponse:
    """Handle incoming Telegram Bot webhook updates.
    
    Processes creator replies:
    - 'a' / 'approve' -> Approves pending draft and triggers dispatch.
    - 's' / 'skip'    -> Skips the comment without posting.
    - 'e: <text>'     -> Edits the reply, computes vector delta, and dispatches.
    - 'status'        -> Returns live state statistics.
    - 'help'          -> Returns command syntax.
    """
    # Optional webhook secret verification
    if config.telegram_webhook_secret and x_telegram_bot_api_secret_token != config.telegram_webhook_secret:
        logger.warning("Unauthorized webhook request with invalid secret token.")
        raise HTTPException(status_code=403, detail="Invalid secret token.")

    message = update.message or (update.callback_query.get("message") if update.callback_query else None)
    if not message:
        return TelegramActionResponse(
            status="ignored",
            action="none",
            message="No actionable message content found in update.",
        )

    chat_id = str(message.get("chat", {}).get("id", config.telegram_chat_id))
    incoming_text = message.get("text", "").strip()
    reply_to = message.get("reply_to_message")
    reply_to_msg_id = reply_to.get("message_id") if reply_to else None

    action, extra_payload = telegram_service.parse_telegram_user_input(incoming_text)

    # 1. Handle Status Query
    if action == "status":
        stats = db.get_hitl_stats()
        text_out = (
            f"📊 <b>YT-AyoChat HITL State:</b>\n"
            f"• Total Records: <b>{stats.total_records}</b>\n"
            f"• ⏳ Pending Approval: <b>{stats.pending_approval}</b>\n"
            f"• ✅ Approved: <b>{stats.approved}</b>\n"
            f"• ✏️ Edited: <b>{stats.edited}</b>\n"
            f"• ⏩ Skipped: <b>{stats.skipped}</b>\n"
            f"• 🚀 Dispatched: <b>{stats.dispatched}</b>"
        )
        await telegram_service.send_message(text=text_out, chat_id=chat_id)
        return TelegramActionResponse(status="success", action="status", message="Status emitted.")

    # 2. Handle Help Query
    if action == "help":
        text_out = (
            "🎛️ <b>YT-AyoChat Telegram HITL Commands:</b>\n\n"
            "• <code>a</code> ➔ <b>Approve</b> current draft and dispatch.\n"
            "• <code>s</code> ➔ <b>Skip</b> comment.\n"
            "• <code>e: &lt;your reply&gt;</code> ➔ <b>Edit</b> &amp; calibrate delta.\n"
            "• <code>status</code> ➔ View pending queue counts.\n"
            "• <code>help</code> ➔ Show this guide."
        )
        await telegram_service.send_message(text=text_out, chat_id=chat_id)
        return TelegramActionResponse(status="success", action="help", message="Help emitted.")

    # 3. Locate Target HITL Record
    target_record: Optional[HITLCommentRecord] = None
    if reply_to_msg_id:
        target_record = db.get_comment_by_telegram_message_id(reply_to_msg_id)

    if not target_record:
        # Fall back to FIFO queue (oldest pending comment)
        target_record = db.get_latest_pending_comment()

    if not target_record:
        await telegram_service.send_message(
            text="✨ No comments currently pending in the HITL approval queue!",
            chat_id=chat_id,
        )
        return TelegramActionResponse(
            status="ignored",
            action="none",
            message="No pending comments available.",
        )

    dispatcher = ActionDispatcher(dry_run=True)

    # 4. Process APPROVE Action ('a')
    if action == "approve":
        final_reply = target_record.model_draft_reply
        db.update_hitl_comment_decision(
            record_id=target_record.id,
            status=HITLStatus.APPROVED,
            human_verdict=HITLVerdict.YES,
            final_reply=final_reply,
            human_score=5.0,
            alignment_delta=0.0,
        )

        append_fine_tuning_record(
            record=target_record,
            final_reply=final_reply,
            verdict=HITLVerdict.YES,
            alignment_delta=0.0,
            notes="Approved via Telegram Bot",
        )

        dispatch_res = dispatcher.dispatch_reply(
            comment_id=target_record.comment_id,
            reply_text=final_reply,
            require_citation=False,
        )

        confirm_msg = (
            f"✅ <b>Approved & Dispatched</b> (ID: <code>{target_record.comment_id}</code>)\n"
            f"💬 \"<i>{html.escape(final_reply)}</i>\"\n"
            f"🚀 Dispatch: <code>{dispatch_res.status.value} (HTTP 200)</code>"
        )
        await telegram_service.send_message(text=confirm_msg, chat_id=chat_id, reply_to_message_id=reply_to_msg_id)

        return TelegramActionResponse(
            status="success",
            action="approved",
            record_id=target_record.id,
            comment_id=target_record.comment_id,
            reply_text=final_reply,
            alignment_delta=0.0,
            dispatched=True,
            message="Comment approved and dispatched.",
        )

    # 5. Process SKIP Action ('s')
    if action == "skip":
        db.update_hitl_comment_decision(
            record_id=target_record.id,
            status=HITLStatus.SKIPPED,
            human_verdict=HITLVerdict.SKIP,
            final_reply=None,
            human_score=3.0,
            alignment_delta=0.0,
        )

        confirm_msg = f"⏩ <b>Skipped comment</b> (ID: <code>{target_record.comment_id}</code>)."
        await telegram_service.send_message(text=confirm_msg, chat_id=chat_id, reply_to_message_id=reply_to_msg_id)

        return TelegramActionResponse(
            status="success",
            action="skipped",
            record_id=target_record.id,
            comment_id=target_record.comment_id,
            reply_text=None,
            alignment_delta=0.0,
            dispatched=False,
            message="Comment skipped.",
        )

    # 6. Process EDIT Action ('e: <text>')
    if action == "edit" and extra_payload:
        edited_reply = extra_payload.strip()

        # Compute diff and vector alignment delta
        matcher = difflib.SequenceMatcher(None, target_record.model_draft_reply, edited_reply)
        diff_payload = {
            "original": target_record.model_draft_reply,
            "edited": edited_reply,
            "char_delta": len(edited_reply) - len(target_record.model_draft_reply),
            "edit_ratio": round(matcher.ratio(), 4),
        }
        delta = calculate_alignment_delta(target_record.applied_vectors)

        db.update_hitl_comment_decision(
            record_id=target_record.id,
            status=HITLStatus.EDITED,
            human_verdict=HITLVerdict.YES_WITH_EDITS,
            final_reply=edited_reply,
            diff_json=diff_payload,
            alignment_delta=delta,
            human_score=4.5,
        )

        append_fine_tuning_record(
            record=target_record,
            final_reply=edited_reply,
            verdict=HITLVerdict.YES_WITH_EDITS,
            alignment_delta=delta,
            notes="Calibrated via Telegram Bot edit",
        )

        dispatch_res = dispatcher.dispatch_reply(
            comment_id=target_record.comment_id,
            reply_text=edited_reply,
            require_citation=False,
        )

        confirm_msg = (
            f"✏️ <b>Calibrated & Dispatched!</b> (ID: <code>{target_record.comment_id}</code>)\n"
            f"💬 <b>Final:</b> \"<i>{html.escape(edited_reply)}</i>\"\n"
            f"📐 <b>Vector Delta Δ:</b> <code>{delta}</code>\n"
            f"🚀 Dispatch: <code>{dispatch_res.status.value} (HTTP 200)</code>"
        )
        await telegram_service.send_message(text=confirm_msg, chat_id=chat_id, reply_to_message_id=reply_to_msg_id)

        return TelegramActionResponse(
            status="success",
            action="edited",
            record_id=target_record.id,
            comment_id=target_record.comment_id,
            reply_text=edited_reply,
            alignment_delta=delta,
            dispatched=True,
            message="Comment edited, calibrated, and dispatched.",
        )

    # 7. Unrecognized input
    await telegram_service.send_message(
        text=(
            f"❓ Unrecognized command: <code>{html.escape(incoming_text)}</code>\n"
            "Reply with <code>a</code> (Approve), <code>s</code> (Skip), or <code>e: &lt;text&gt;</code> (Edit)."
        ),
        chat_id=chat_id,
        reply_to_message_id=reply_to_msg_id,
    )
    return TelegramActionResponse(
        status="ignored",
        action="unknown",
        message="Unrecognized command syntax.",
    )


# --------------------------------------------------------------------------
# State Management & REST HITL Inspection Endpoints
# --------------------------------------------------------------------------

@app.get("/api/hitl/pending", response_model=List[HITLCommentRecord], tags=["HITL State"])
async def list_pending_hitl_comments(video_id: Optional[str] = None) -> List[HITLCommentRecord]:
    """Retrieve all comments awaiting creator review."""
    return db.list_hitl_comments(status="PENDING_APPROVAL", video_id=video_id)


@app.get("/api/hitl/records", response_model=List[HITLCommentRecord], tags=["HITL State"])
async def list_all_hitl_records(
    status: Optional[str] = Query(None, description="Filter by status (PENDING_APPROVAL, APPROVED, EDITED, SKIPPED)"),
    video_id: Optional[str] = Query(None, description="Filter by video ID"),
    limit: int = Query(50, ge=1, le=200),
) -> List[HITLCommentRecord]:
    """List historical records with optional status and video filtering."""
    return db.list_hitl_comments(status=status, video_id=video_id, limit=limit)


@app.get("/api/hitl/stats", response_model=HITLStatsResponse, tags=["HITL State"])
async def get_hitl_state_statistics() -> HITLStatsResponse:
    """Get real-time counts across the HITL state machine."""
    return db.get_hitl_stats()


@app.post("/api/hitl/approve/{record_id}", response_model=TelegramActionResponse, tags=["HITL Actions"])
async def manual_approve_record(record_id: str) -> TelegramActionResponse:
    """Manually approve a pending comment via REST API."""
    record = db.get_hitl_comment(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found.")

    final_reply = record.model_draft_reply
    db.update_hitl_comment_decision(
        record_id=record.id,
        status=HITLStatus.APPROVED,
        human_verdict=HITLVerdict.YES,
        final_reply=final_reply,
        human_score=5.0,
        alignment_delta=0.0,
    )
    append_fine_tuning_record(record, final_reply, HITLVerdict.YES, notes="Approved via REST endpoint")

    return TelegramActionResponse(
        status="success",
        action="approved",
        record_id=record.id,
        comment_id=record.comment_id,
        reply_text=final_reply,
        alignment_delta=0.0,
        dispatched=True,
        message=f"Record {record.id} approved successfully.",
    )


@app.post("/api/hitl/edit/{record_id}", response_model=TelegramActionResponse, tags=["HITL Actions"])
async def manual_edit_record(record_id: str, req: ManualActionRequest) -> TelegramActionResponse:
    """Manually edit and calibrate a comment via REST API."""
    record = db.get_hitl_comment(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found.")

    edited_reply = (req.edited_reply or record.model_draft_reply).strip()
    matcher = difflib.SequenceMatcher(None, record.model_draft_reply, edited_reply)
    diff_payload = {
        "original": record.model_draft_reply,
        "edited": edited_reply,
        "char_delta": len(edited_reply) - len(record.model_draft_reply),
        "edit_ratio": round(matcher.ratio(), 4),
    }
    delta = calculate_alignment_delta(
        record.applied_vectors,
        author_alpha=req.author_alpha or 0.90,
        author_beta=req.author_beta or "CLAPBACK",
        author_gamma=req.author_gamma or 4,
    )

    db.update_hitl_comment_decision(
        record_id=record.id,
        status=HITLStatus.EDITED,
        human_verdict=HITLVerdict.YES_WITH_EDITS,
        final_reply=edited_reply,
        diff_json=diff_payload,
        alignment_delta=delta,
        human_score=4.5,
    )
    append_fine_tuning_record(record, edited_reply, HITLVerdict.YES_WITH_EDITS, alignment_delta=delta, notes=req.notes)

    return TelegramActionResponse(
        status="success",
        action="edited",
        record_id=record.id,
        comment_id=record.comment_id,
        reply_text=edited_reply,
        alignment_delta=delta,
        dispatched=True,
        message=f"Record {record.id} edited and calibrated with delta {delta}.",
    )


@app.post("/api/hitl/skip/{record_id}", response_model=TelegramActionResponse, tags=["HITL Actions"])
async def manual_skip_record(record_id: str) -> TelegramActionResponse:
    """Manually skip a comment via REST API."""
    record = db.get_hitl_comment(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found.")

    db.update_hitl_comment_decision(
        record_id=record.id,
        status=HITLStatus.SKIPPED,
        human_verdict=HITLVerdict.SKIP,
        final_reply=None,
        human_score=3.0,
        alignment_delta=0.0,
    )

    return TelegramActionResponse(
        status="success",
        action="skipped",
        record_id=record.id,
        comment_id=record.comment_id,
        reply_text=None,
        alignment_delta=0.0,
        dispatched=False,
        message=f"Record {record.id} skipped.",
    )


# --------------------------------------------------------------------------
# PWA Mobile Companion Endpoints
# --------------------------------------------------------------------------

MAX_EDITED_REPLY_CHARS = 2000
MAX_NOTES_CHARS = 500


class PWAResolveRequest(BaseModel):
    """Request model for PWA unified resolution endpoint."""
    record_id: str = Field(..., min_length=1, max_length=128, description="ID of the HITL record to resolve")
    action: str = Field(..., description="Action to take: 'approve', 'skip', or 'edit'")
    edited_reply: Optional[str] = Field(
        default=None,
        max_length=MAX_EDITED_REPLY_CHARS,
        description="Edited reply text (for edit action)",
    )
    target_alpha: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Target code-switch vector (for edit action)")
    notes: Optional[str] = Field(
        default="Resolved via Mobile PWA",
        max_length=MAX_NOTES_CHARS,
        description="Optional notes for the resolution",
    )


def require_pwa_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> None:
    """Authenticate mobile PWA callers against the configured shared API key."""
    if not config.pwa_api_key:
        logger.warning("PWA_API_KEY is not configured; mobile companion endpoints are unauthenticated.")
        return
    if not x_api_key or not hmac.compare_digest(x_api_key, config.pwa_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


@app.get("/api/queue", response_model=List[HITLCommentRecord], tags=["PWA Mobile"])
async def get_pwa_queue(
    limit: int = Query(20, ge=1, le=50, description="Maximum number of queue items to return"),
    video_id: Optional[str] = Query(None, description="Filter by specific video ID"),
    _: None = Depends(require_pwa_api_key),
) -> List[HITLCommentRecord]:
    """Get PENDING_APPROVAL comments for mobile PWA queue interface.

    This endpoint provides a streamlined interface for the mobile PWA to fetch
    the current queue of comments awaiting creator review.
    """
    return db.list_hitl_comments(status="PENDING_APPROVAL", video_id=video_id, limit=limit)


@app.post("/api/resolve", response_model=TelegramActionResponse, tags=["PWA Mobile"])
async def resolve_hitl_comment_pwa(
    req: PWAResolveRequest,
    _: None = Depends(require_pwa_api_key),
) -> TelegramActionResponse:
    """Unified endpoint for HITL resolution from mobile PWA.
    
    This consolidates approve, skip, and edit actions into a single endpoint
    optimized for the mobile PWA interface while maintaining backward compatibility
    with existing Telegram webhook and REST endpoints.
    """
    if req.action not in {"approve", "skip", "edit"}:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action: {req.action}. Must be 'approve', 'skip', or 'edit'.",
        )

    record = db.get_hitl_comment(req.record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found.")
    if record.status != HITLStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=409,
            detail=f"Record {record.id} is already resolved ({record.status.value}).",
        )

    if req.action == "skip":
        claimed = db.claim_pending_hitl_comment(
            record_id=record.id,
            status=HITLStatus.SKIPPED,
            human_verdict=HITLVerdict.SKIP,
            final_reply=None,
            human_score=3.0,
            alignment_delta=0.0,
        )
        if not claimed:
            raise HTTPException(status_code=409, detail=f"Record {record.id} is already resolved.")

        return TelegramActionResponse(
            status="success",
            action="skipped",
            record_id=record.id,
            comment_id=record.comment_id,
            reply_text=None,
            alignment_delta=0.0,
            dispatched=False,
            message="Comment skipped via Mobile PWA",
        )

    if req.action == "approve":
        final_reply = record.model_draft_reply
        verdict = HITLVerdict.YES
        status = HITLStatus.APPROVED
        human_score = 5.0
        delta = 0.0
        diff_payload = None
    else:
        edited_reply = (req.edited_reply or "").strip()
        if not edited_reply:
            raise HTTPException(status_code=400, detail="edited_reply is required for edit action")

        final_reply = edited_reply
        verdict = HITLVerdict.YES_WITH_EDITS
        status = HITLStatus.EDITED
        human_score = 4.5
        matcher = difflib.SequenceMatcher(None, record.model_draft_reply, edited_reply)
        diff_payload = {
            "original": record.model_draft_reply,
            "edited": edited_reply,
            "char_delta": len(edited_reply) - len(record.model_draft_reply),
            "edit_ratio": round(matcher.ratio(), 4),
        }
        delta = calculate_alignment_delta(
            record.applied_vectors,
            author_alpha=req.target_alpha if req.target_alpha is not None else 0.90,
            author_beta="CLAPBACK",
            author_gamma=4,
        )

    claimed = db.claim_pending_hitl_comment(
        record_id=record.id,
        status=status,
        human_verdict=verdict,
        final_reply=final_reply,
        diff_json=diff_payload,
        alignment_delta=delta,
        human_score=human_score,
    )
    if not claimed:
        raise HTTPException(status_code=409, detail=f"Record {record.id} is already resolved.")

    dispatcher = ActionDispatcher(dry_run=True)
    dispatch_res = dispatcher.dispatch_reply(
        comment_id=record.comment_id,
        reply_text=final_reply,
        require_citation=False,
    )
    if dispatch_res.status != DispatchStatus.SUCCESS:
        db.release_hitl_comment_claim(record.id)
        raise HTTPException(
            status_code=502,
            detail=f"Reply dispatch failed: {dispatch_res.error_message or dispatch_res.status.value}",
        )

    append_fine_tuning_record(record, final_reply, verdict, alignment_delta=delta, notes=req.notes)

    if req.action == "approve":
        return TelegramActionResponse(
            status="success",
            action="approved",
            record_id=record.id,
            comment_id=record.comment_id,
            reply_text=final_reply,
            alignment_delta=0.0,
            dispatched=True,
            message="Comment approved and dispatched via Mobile PWA",
        )

    return TelegramActionResponse(
        status="success",
        action="edited",
        record_id=record.id,
        comment_id=record.comment_id,
        reply_text=final_reply,
        alignment_delta=delta,
        dispatched=True,
        message=f"Comment edited and dispatched via Mobile PWA with delta {delta}",
    )
