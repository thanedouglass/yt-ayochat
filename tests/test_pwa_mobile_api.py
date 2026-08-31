"""Tests for the Mobile PWA companion endpoints (/api/queue and /api/resolve)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.db import HITLDatabase
from src.api.main import app
from src.api.models import HITLCommentRecord, HITLStatus, HITLVerdict
from src.config import config


@pytest.fixture
def temp_hitl_db(tmp_path: Path) -> HITLDatabase:
    """Provide an isolated temporary SQLite database for test execution."""
    return HITLDatabase(db_path=tmp_path / "test_pwa_state.db")


@pytest.fixture
def client(temp_hitl_db: HITLDatabase, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """TestClient bound to an isolated database and alignment log file."""
    import src.api.db as db_mod
    import src.api.main as main_mod

    monkeypatch.setattr(main_mod, "db", temp_hitl_db)
    monkeypatch.setattr(db_mod, "db", temp_hitl_db)
    monkeypatch.setattr(config, "hitl_alignment_path", temp_hitl_db.db_path.parent / "test_alignment.jsonl")
    monkeypatch.setattr(config, "pwa_api_key", "s3cret")
    monkeypatch.setattr(config, "pwa_allow_unauthenticated", False)

    return TestClient(app, headers={"X-API-Key": "s3cret"})


def _seed_record(db: HITLDatabase, record_id: str = "rec_pwa_1") -> HITLCommentRecord:
    record = HITLCommentRecord(
        id=record_id,
        comment_id=f"cmt_{record_id}",
        video_id="dtvsnt1OMy4",
        video_title="Dance Practice",
        author_name="@hype_user",
        input_comment="That transition was clean!",
        category="HYPE",
        semiotic_intent="PRAISE",
        energy_level=4,
        polarity=0.9,
        model_draft_reply="Took 40 takes to lock that transition in!",
        applied_vectors={
            "code_switch_alpha": 0.85,
            "sovereignty_beta": "CLAPBACK",
            "frequency_gamma": 4,
            "token_economy_tau": "Pass (1 Sentence)",
        },
        created_at="2026-08-30T12:00:00Z",
        updated_at="2026-08-30T12:00:00Z",
    )
    return db.insert_hitl_comment(record)


def test_queue_endpoint_reads_query_parameters(client: TestClient, temp_hitl_db: HITLDatabase):
    """GET /api/queue binds limit and video_id from the query string without a body."""
    _seed_record(temp_hitl_db)

    res = client.get("/api/queue?limit=20")
    assert res.status_code == 200
    assert [item["id"] for item in res.json()] == ["rec_pwa_1"]

    res_filtered = client.get("/api/queue", params={"limit": 5, "video_id": "other_video"})
    assert res_filtered.status_code == 200
    assert res_filtered.json() == []

    assert client.get("/api/queue?limit=500").status_code == 422


def test_pwa_endpoints_require_api_key(client: TestClient, temp_hitl_db: HITLDatabase):
    """PWA_API_KEY gates both the queue and resolve endpoints."""
    _seed_record(temp_hitl_db)

    assert client.get("/api/queue", headers={"X-API-Key": ""}).status_code == 401
    assert client.get("/api/queue", headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.get("/api/queue").status_code == 200

    unauthorized = client.post(
        "/api/resolve",
        headers={"X-API-Key": "wrong"},
        json={"record_id": "rec_pwa_1", "action": "approve"},
    )
    assert unauthorized.status_code == 401
    assert temp_hitl_db.get_hitl_comment("rec_pwa_1").status == HITLStatus.PENDING_APPROVAL


def test_pwa_endpoints_fail_closed_without_configured_key(
    client: TestClient, temp_hitl_db: HITLDatabase, monkeypatch: pytest.MonkeyPatch
):
    """An unset PWA_API_KEY blocks access instead of silently disabling auth."""
    _seed_record(temp_hitl_db)
    monkeypatch.setattr(config, "pwa_api_key", "")

    assert client.get("/api/queue").status_code == 503

    monkeypatch.setattr(config, "pwa_allow_unauthenticated", True)
    assert client.get("/api/queue").status_code == 200


def test_resolve_approve_dispatches_and_blocks_duplicates(client: TestClient, temp_hitl_db: HITLDatabase):
    """Approve dispatches the draft once and rejects retries on a resolved record."""
    _seed_record(temp_hitl_db)

    res = client.post("/api/resolve", json={"record_id": "rec_pwa_1", "action": "approve"})
    assert res.status_code == 200
    body = res.json()
    assert body["action"] == "approved"
    assert body["dispatched"] is True

    updated = temp_hitl_db.get_hitl_comment("rec_pwa_1")
    assert updated.status == HITLStatus.APPROVED
    assert updated.human_verdict == HITLVerdict.YES

    retry = client.post("/api/resolve", json={"record_id": "rec_pwa_1", "action": "approve"})
    assert retry.status_code == 409


def test_resolve_edit_honours_zero_target_alpha(client: TestClient, temp_hitl_db: HITLDatabase):
    """A target_alpha of 0.0 is used verbatim instead of falling back to 0.90."""
    _seed_record(temp_hitl_db, record_id="rec_pwa_2")

    res = client.post(
        "/api/resolve",
        json={
            "record_id": "rec_pwa_2",
            "action": "edit",
            "edited_reply": "Locked that transition in after 40 takes!",
            "target_alpha": 0.0,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["action"] == "edited"
    assert body["alignment_delta"] == pytest.approx(0.85, abs=1e-4)
    assert temp_hitl_db.get_hitl_comment("rec_pwa_2").status == HITLStatus.EDITED

    training_row = json.loads(config.hitl_alignment_path.read_text().splitlines()[-1])
    assert training_row["human_score"] == 4.5


def test_resolve_rejects_oversized_payloads(client: TestClient, temp_hitl_db: HITLDatabase):
    """Edited replies and notes are length bounded."""
    _seed_record(temp_hitl_db, record_id="rec_pwa_3")

    res = client.post(
        "/api/resolve",
        json={"record_id": "rec_pwa_3", "action": "edit", "edited_reply": "x" * 5000},
    )
    assert res.status_code == 422
    assert temp_hitl_db.get_hitl_comment("rec_pwa_3").status == HITLStatus.PENDING_APPROVAL


def test_resolve_failed_dispatch_keeps_record_pending(
    client: TestClient, temp_hitl_db: HITLDatabase, monkeypatch: pytest.MonkeyPatch
):
    """A failed dispatch releases the claim so the comment stays reviewable."""
    import src.api.main as main_mod
    from src.pipeline.dispatcher import DispatchResult
    from src.telemetry.schema import DispatchStatus

    _seed_record(temp_hitl_db, record_id="rec_pwa_4")

    def failing_dispatch(self, comment_id: str, reply_text: str, **kwargs) -> DispatchResult:
        return DispatchResult(
            status=DispatchStatus.FAILED,
            comment_id=comment_id,
            error_message="YouTube API unavailable",
        )

    monkeypatch.setattr(main_mod.ActionDispatcher, "dispatch_reply", failing_dispatch)

    res = client.post("/api/resolve", json={"record_id": "rec_pwa_4", "action": "approve"})
    assert res.status_code == 502

    record = temp_hitl_db.get_hitl_comment("rec_pwa_4")
    assert record.status == HITLStatus.PENDING_APPROVAL
    assert record.human_verdict is None
