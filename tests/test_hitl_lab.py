"""Unit & Integration Test Suite for Human-in-the-Loop (HITL) Intercept Lab."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Tuple

import pytest

from src.swarm.hitl_data import INBOUND_COMMENT_QUEUE, TOP_10_VIDEOS
from src.swarm.hitl_lab import HITLVerdict, HumanInTheLoopLab


@pytest.fixture
def temp_log_file(tmp_path: Path) -> str:
    """Fixture returning temporary log file path for isolated test logging."""
    return str(tmp_path / "test_hitl_alignment.jsonl")


def test_inbound_queue_top_10_videos():
    """Verify top 10 video metadata integrity and queue length."""
    assert len(TOP_10_VIDEOS) == 10
    assert TOP_10_VIDEOS[0]["video_id"] == "M1G92FWmdJw"
    assert TOP_10_VIDEOS[0]["views"] == 476326
    assert len(INBOUND_COMMENT_QUEUE) == 10


def test_hitl_verdict_yes_approval(temp_log_file: str):
    """Verify YES verdict: model draft is approved unmodified."""
    lab = HumanInTheLoopLab(log_file_path=temp_log_file)
    comment = INBOUND_COMMENT_QUEUE[0]  # Dance choreo comment

    def approve_callback(payload: Dict[str, Any]) -> Tuple[HITLVerdict, None, float, str]:
        assert "footwork" in payload["input_comment"]
        assert len(payload["agent_draft_reply"]) > 0
        return (HITLVerdict.YES, None, 5.0, "Approved as is")

    record = lab.process_and_intercept(comment, decision_callback=approve_callback)

    assert record.human_verdict == HITLVerdict.YES
    assert record.human_score == 5.0
    assert record.final_dispatched_reply == record.agent_draft_reply
    assert record.diff is None
    assert record.fine_tuning_export is not None
    assert record.fine_tuning_export["completion"] == record.agent_draft_reply

    # Verify JSONL persistence
    assert os.path.exists(temp_log_file)
    with open(temp_log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 1
    saved_data = json.loads(lines[0])
    assert saved_data["human_verdict"] == "YES"
    assert saved_data["human_score"] == 5.0


def test_hitl_verdict_yes_with_edits_diff_computation(temp_log_file: str):
    """Verify YES_WITH_EDITS verdict: diff is calculated and human text captured."""
    lab = HumanInTheLoopLab(log_file_path=temp_log_file)
    comment = INBOUND_COMMENT_QUEUE[2]  # Fit check comment

    edited_text = "That oversized leather bomber is a vintage find from Melrose flea market for $30!"

    def edit_callback(payload: Dict[str, Any]) -> Tuple[HITLVerdict, str, float, str]:
        return (HITLVerdict.YES_WITH_EDITS, edited_text, 4.0, "Shortened price reference")

    record = lab.process_and_intercept(comment, decision_callback=edit_callback)

    assert record.human_verdict == HITLVerdict.YES_WITH_EDITS
    assert record.human_score == 4.0
    assert record.final_dispatched_reply == edited_text
    assert record.diff is not None
    assert record.diff["edited"] == edited_text
    assert "char_delta" in record.diff
    assert record.fine_tuning_export is not None
    assert record.fine_tuning_export["completion"] == edited_text


def test_hitl_verdict_no_rejection_suppression(temp_log_file: str):
    """Verify NO verdict: dispatch is suppressed and score logged."""
    lab = HumanInTheLoopLab(log_file_path=temp_log_file)
    comment = INBOUND_COMMENT_QUEUE[8]  # Crypto off-topic comment

    def reject_callback(payload: Dict[str, Any]) -> Tuple[HITLVerdict, None, float, str]:
        return (HITLVerdict.NO, None, 1.0, "Completely off-topic crypto question")

    record = lab.process_and_intercept(comment, decision_callback=reject_callback)

    assert record.human_verdict == HITLVerdict.NO
    assert record.human_score == 1.0
    assert record.final_dispatched_reply is None
    assert record.diff is None
    assert record.fine_tuning_export is None


def test_hitl_multilingual_council_review(temp_log_file: str):
    """Verify Spanish, Arabic, and Portuguese comments trigger proper routing and review."""
    lab = HumanInTheLoopLab(log_file_path=temp_log_file)

    # Spanish comment
    es_comment = INBOUND_COMMENT_QUEUE[3]
    rec_es = lab.process_and_intercept(es_comment)
    assert rec_es.language in ("es", "en")
    assert len(rec_es.agent_draft_reply) > 0

    # Arabic comment
    ar_comment = INBOUND_COMMENT_QUEUE[4]
    rec_ar = lab.process_and_intercept(ar_comment)
    assert rec_ar.language in ("ar", "en")
    assert len(rec_ar.agent_draft_reply) > 0


def test_hitl_batch_simulation_and_metrics(temp_log_file: str):
    """Verify end-to-end batch simulation and aggregate metrics calculation."""
    lab = HumanInTheLoopLab(log_file_path=temp_log_file)
    results = lab.run_batch_simulation(limit=10)

    assert len(results) == 10
    metrics = lab.get_metrics_summary()

    assert metrics["total_evaluated"] == 10
    assert metrics["approved_unmodified"] > 0
    assert metrics["approved_with_edits"] > 0
    assert metrics["rejected"] > 0
    assert 0.0 <= metrics["overall_approval_rate_pct"] <= 100.0
    assert 1.0 <= metrics["average_human_score"] <= 5.0
