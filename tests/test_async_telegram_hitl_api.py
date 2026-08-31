"""Tests for the Asynchronous FastAPI Backend & Mobile Telegram HITL Pipeline."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.db import HITLDatabase
from src.api.main import app
from src.api.models import HITLCommentRecord, HITLStatus, HITLVerdict
from src.api.telegram_service import TelegramService
from src.config import config


@pytest.fixture
def temp_hitl_db(tmp_path: Path) -> HITLDatabase:
    """Provide an isolated temporary SQLite database for test execution."""
    db_file = tmp_path / "test_hitl_state.db"
    test_db = HITLDatabase(db_path=db_file)
    return test_db


@pytest.fixture
def client(temp_hitl_db: HITLDatabase, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """TestClient configured with an isolated database and alignment log file."""
    import src.api.main as main_mod
    import src.api.db as db_mod

    # Patch global database instance
    monkeypatch.setattr(main_mod, "db", temp_hitl_db)
    monkeypatch.setattr(db_mod, "db", temp_hitl_db)

    # Patch alignment log file to temporary directory
    temp_alignment = temp_hitl_db.db_path.parent / "test_alignment.jsonl"
    monkeypatch.setattr(config, "hitl_alignment_path", temp_alignment)

    return TestClient(app)


# --------------------------------------------------------------------------
# 1. SQLite Database State Machine Tests
# --------------------------------------------------------------------------

def test_sqlite_db_crud_and_state_transitions(temp_hitl_db: HITLDatabase):
    """Verify SQLite database properly handles entity insertion, retrieval, and updates."""
    record = HITLCommentRecord(
        id="rec_001",
        comment_id="yt_c_001",
        video_id="dtvsnt1OMy4",
        video_title="Dance Cover Short",
        author_name="@dancer_dev",
        input_comment="that footwork on count 3 was insane!",
        category="DANCE_CHOREO",
        semiotic_intent="CHOREO_TECHNIQUE_INQUIRY",
        energy_level=4,
        polarity=0.85,
        model_draft_reply="That footwork took three studio sessions to lock in!",
        applied_vectors={"code_switch_alpha": 0.65, "sovereignty_beta": "ELEVATE", "frequency_gamma": 3},
        status=HITLStatus.PENDING_APPROVAL,
        created_at="2026-08-30T12:00:00Z",
        updated_at="2026-08-30T12:00:00Z",
    )

    # Insert
    temp_hitl_db.insert_hitl_comment(record)

    # Get by ID
    fetched = temp_hitl_db.get_hitl_comment("rec_001")
    assert fetched is not None
    assert fetched.comment_id == "yt_c_001"
    assert fetched.status == HITLStatus.PENDING_APPROVAL

    # Associate Telegram message ID
    temp_hitl_db.update_telegram_message_id("rec_001", 55501)
    by_msg = temp_hitl_db.get_comment_by_telegram_message_id(55501)
    assert by_msg is not None
    assert by_msg.id == "rec_001"

    # State Transition: Approve
    temp_hitl_db.update_hitl_comment_decision(
        record_id="rec_001",
        status=HITLStatus.APPROVED,
        human_verdict=HITLVerdict.YES,
        final_reply=fetched.model_draft_reply,
        human_score=5.0,
    )
    approved = temp_hitl_db.get_hitl_comment("rec_001")
    assert approved.status == HITLStatus.APPROVED
    assert approved.human_verdict == HITLVerdict.YES

    # Stats check
    stats = temp_hitl_db.get_hitl_stats()
    assert stats.total_records == 1
    assert stats.approved == 1
    assert stats.pending_approval == 0


# --------------------------------------------------------------------------
# 2. Telegram Parsing & Formatting Tests
# --------------------------------------------------------------------------

def test_telegram_user_input_parsing():
    """Verify natural language and shorthand command parsing."""
    svc = TelegramService(bot_token="mock_token", default_chat_id="12345")

    assert svc.parse_telegram_user_input("a")[0] == "approve"
    assert svc.parse_telegram_user_input("APPROVE")[0] == "approve"
    assert svc.parse_telegram_user_input("/approve")[0] == "approve"
    assert svc.parse_telegram_user_input("yes")[0] == "approve"

    assert svc.parse_telegram_user_input("s")[0] == "skip"
    assert svc.parse_telegram_user_input("/skip")[0] == "skip"
    assert svc.parse_telegram_user_input("no")[0] == "skip"

    action, edit_text = svc.parse_telegram_user_input("e: That transition was actually 4 takes!")
    assert action == "edit"
    assert edit_text == "That transition was actually 4 takes!"

    action2, edit_text2 = svc.parse_telegram_user_input("edit: Dropping the breakdown in Discord!")
    assert action2 == "edit"
    assert edit_text2 == "Dropping the breakdown in Discord!"

    assert svc.parse_telegram_user_input("status")[0] == "status"
    assert svc.parse_telegram_user_input("help")[0] == "help"


def test_telegram_notification_formatting():
    """Verify HTML notification formatting contains all required telemetry metrics."""
    svc = TelegramService(bot_token="mock_token", default_chat_id="12345")
    record = HITLCommentRecord(
        id="rec_test_123",
        comment_id="c_999",
        video_id="dtvsnt1OMy4",
        video_title="Hootie Frutti Practice",
        author_name="@lumi_fan",
        input_comment="Love the fit and energy!",
        category="HYPE",
        semiotic_intent="HIGH_ENERGY_PRAISE",
        energy_level=5,
        polarity=0.9,
        model_draft_reply="Appreciate you hyping me up, we are just warming up!",
        applied_vectors={"code_switch_alpha": 0.85, "sovereignty_beta": "CELEBRATE", "frequency_gamma": 4},
        created_at="2026-08-30T12:00:00Z",
        updated_at="2026-08-30T12:00:00Z",
    )
    formatted = svc.format_hitl_notification_html(record)
    assert "Hootie Frutti Practice" in formatted
    assert "@lumi_fan" in formatted
    assert "Gemini 3.7 Flash Draft:" in formatted
    assert "α=0.85" in formatted
    assert "Approve" in formatted


# --------------------------------------------------------------------------
# 3. REST API Endpoint Tests
# --------------------------------------------------------------------------

def test_api_health_endpoint(client: TestClient):
    """Verify GET /api/health returns 200 with service metadata."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "YT-AyoChat" in data["service"]
    assert "database" in data
    assert "telegram" in data


def test_api_poll_comments_endpoint(client: TestClient):
    """Verify POST /api/poll-comments runs Swarm, saves drafts to SQLite, and alerts Telegram."""
    payload = {
        "video_id": "dtvsnt1OMy4",
        "limit": 3,
        "send_telegram": True,
        "auto_approve": False,
        "dry_run": True,
    }
    res = client.post("/api/poll-comments", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["total_polled"] >= 1
    assert len(data["records"]) >= 1

    first_record = data["records"][0]
    assert first_record["status"] == "PENDING_APPROVAL"
    assert len(first_record["model_draft_reply"]) > 0

    # Verify record is queryable via GET /api/hitl/pending
    pending_res = client.get("/api/hitl/pending")
    assert pending_res.status_code == 200
    pending_data = pending_res.json()
    assert len(pending_data) >= 1


def test_api_telegram_webhook_approval_flow(client: TestClient, temp_hitl_db: HITLDatabase):
    """Verify Telegram webhook 'a' command approves the pending comment and updates SQLite."""
    # Seed pending record
    rec = HITLCommentRecord(
        id="rec_seed_1",
        comment_id="c_seed_1",
        video_id="dtvsnt1OMy4",
        video_title="Dance Practice",
        author_name="@hype_user",
        input_comment="How many takes did this take?",
        category="BANTER",
        semiotic_intent="COMMUNITY_BANTER",
        energy_level=3,
        polarity=0.6,
        model_draft_reply="Locked in for 40 takes before catching the cleanest drop!",
        applied_vectors={"code_switch_alpha": 0.8, "sovereignty_beta": "BANTER", "frequency_gamma": 3},
        telegram_message_id=9901,
        created_at="2026-08-30T12:00:00Z",
        updated_at="2026-08-30T12:00:00Z",
    )
    temp_hitl_db.insert_hitl_comment(rec)

    webhook_payload = {
        "update_id": 10001,
        "message": {
            "message_id": 1002,
            "chat": {"id": 123456789, "type": "private"},
            "text": "a",
            "reply_to_message": {"message_id": 9901, "text": "Draft notification"},
        },
    }

    res = client.post("/api/telegram-webhook", json=webhook_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["action"] == "approved"
    assert data["dispatched"] is True

    # Verify DB record updated
    updated = temp_hitl_db.get_hitl_comment("rec_seed_1")
    assert updated.status == HITLStatus.APPROVED
    assert updated.human_verdict == HITLVerdict.YES


def test_api_telegram_webhook_edit_and_vector_delta(client: TestClient, temp_hitl_db: HITLDatabase):
    """Verify Telegram webhook 'e: <text>' command edits the draft and computes vector delta."""
    rec = HITLCommentRecord(
        id="rec_seed_2",
        comment_id="c_seed_2",
        video_id="dtvsnt1OMy4",
        video_title="Dance Practice",
        author_name="@critic_user",
        input_comment="Why spend time on 15 sec videos?",
        category="TROLL_OR_HATER",
        semiotic_intent="TROLL_ATTACK",
        energy_level=4,
        polarity=-0.5,
        model_draft_reply="Fueling our rehearsal with tacos while touring the world!",
        applied_vectors={"code_switch_alpha": 0.95, "sovereignty_beta": "CLAPBACK", "frequency_gamma": 2},
        telegram_message_id=9902,
        created_at="2026-08-30T12:00:00Z",
        updated_at="2026-08-30T12:00:00Z",
    )
    temp_hitl_db.insert_hitl_comment(rec)

    edited_text = "Using my degree to calculate algorithmic revenue from this hate comment while hitting the 8-count."
    webhook_payload = {
        "update_id": 10002,
        "message": {
            "message_id": 1003,
            "chat": {"id": 123456789, "type": "private"},
            "text": f"e: {edited_text}",
            "reply_to_message": {"message_id": 9902, "text": "Draft notification"},
        },
    }

    res = client.post("/api/telegram-webhook", json=webhook_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["action"] == "edited"
    assert data["reply_text"] == edited_text
    assert data["alignment_delta"] is not None

    # Verify DB record updated
    updated = temp_hitl_db.get_hitl_comment("rec_seed_2")
    assert updated.status == HITLStatus.EDITED
    assert updated.human_verdict == HITLVerdict.YES_WITH_EDITS
    assert updated.final_dispatched_reply == edited_text
    assert updated.diff_json is not None


def test_api_telegram_webhook_skip_and_status(client: TestClient, temp_hitl_db: HITLDatabase):
    """Verify Telegram webhook 's' (skip) and 'status' commands."""
    rec = HITLCommentRecord(
        id="rec_seed_3",
        comment_id="c_seed_3",
        video_id="dtvsnt1OMy4",
        video_title="Dance Practice",
        author_name="@spam_bot",
        input_comment="Buy crypto here!",
        category="UNINDEXED_OR_OFFTOPIC",
        semiotic_intent="SPAM",
        energy_level=1,
        polarity=0.0,
        model_draft_reply="Out of scope deflection.",
        telegram_message_id=9903,
        created_at="2026-08-30T12:00:00Z",
        updated_at="2026-08-30T12:00:00Z",
    )
    temp_hitl_db.insert_hitl_comment(rec)

    # 1. Skip
    res_skip = client.post(
        "/api/telegram-webhook",
        json={
            "update_id": 10003,
            "message": {
                "message_id": 1004,
                "chat": {"id": 123456789, "type": "private"},
                "text": "s",
                "reply_to_message": {"message_id": 9903},
            },
        },
    )
    assert res_skip.status_code == 200
    assert res_skip.json()["action"] == "skipped"
    assert temp_hitl_db.get_hitl_comment("rec_seed_3").status == HITLStatus.SKIPPED

    # 2. Status command
    res_status = client.post(
        "/api/telegram-webhook",
        json={
            "update_id": 10004,
            "message": {
                "message_id": 1005,
                "chat": {"id": 123456789, "type": "private"},
                "text": "status",
            },
        },
    )
    assert res_status.status_code == 200
    assert res_status.json()["action"] == "status"


def test_api_rest_hitl_manual_actions(client: TestClient, temp_hitl_db: HITLDatabase):
    """Verify REST endpoints for manual approval, editing, and stats."""
    rec = HITLCommentRecord(
        id="rec_manual_1",
        comment_id="c_man_1",
        video_id="dtvsnt1OMy4",
        video_title="Choreo",
        author_name="@user_manual",
        input_comment="Clean choreo!",
        category="HYPE",
        semiotic_intent="PRAISE",
        model_draft_reply="Appreciate the love!",
        applied_vectors={"code_switch_alpha": 0.85, "sovereignty_beta": "CELEBRATE", "frequency_gamma": 4},
        created_at="2026-08-30T12:00:00Z",
        updated_at="2026-08-30T12:00:00Z",
    )
    temp_hitl_db.insert_hitl_comment(rec)

    # Approve
    res_app = client.post(f"/api/hitl/approve/{rec.id}")
    assert res_app.status_code == 200
    assert res_app.json()["action"] == "approved"

    # Stats
    res_stats = client.get("/api/hitl/stats")
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert stats["approved"] == 1
    assert stats["total_records"] == 1
