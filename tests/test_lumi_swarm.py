"""Comprehensive Unit & Integration Test Suite for The Lumi Multi-Agent Swarm Architecture."""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

try:
    from src.backend.council import evaluate_os_sentiment_council
except ImportError:
    from backend.council import evaluate_os_sentiment_council
from src.agent import GovernedYouTubeAgent
from src.pipeline.listener import InboundComment
from src.swarm.engine import LumiSwarmEngine
from src.swarm.hive import AutonomousHiveNode
from src.swarm.models import (
    CommentCategory,
    RoomTemperature,
    SemioticIntentAction,
    VideoContext,
)
from src.swarm.perception import PerceptionNode
from src.swarm.supervisor import SupervisorNode


def test_supervisor_room_temperature_evaluation():
    """Verify that SupervisorNode extracts appropriate room temperature from video metadata."""
    supervisor = SupervisorNode()

    # Dance Studio Video
    dance_ctx = supervisor.get_video_context(
        video_id="v_dance_1",
        title_override="NewJeans Hype Boy Dance Cover & Counts Rehearsal",
        description_override="Full dance choreo breakdown with studio counts!",
    )
    assert dance_ctx.room_temperature == RoomTemperature.DANCE_STUDIO
    assert "Choreography" in dance_ctx.primary_topic

    # Fashion Aesthetic Video
    fashion_ctx = supervisor.get_video_context(
        video_id="v_fashion_1",
        title_override="GRWM Street Style Fit Check & Flea Market Thrift Haul",
        description_override="OOTD styling tips, makeup lip combos, and vintage jackets.",
    )
    assert fashion_ctx.room_temperature == RoomTemperature.FASHION_AESTHETIC

    # Hyper Hype Video
    hype_ctx = supervisor.get_video_context(
        video_id="v_hype_1",
        title_override="WORLD TOUR VIRAL ANNOUNCEMENT!!",
        description_override="We are going on our first viral world tour let's go!",
    )
    assert hype_ctx.room_temperature == RoomTemperature.HYPER_HYPE


def test_perception_classification_taxonomy():
    """Verify PerceptionNode categorizes comments into the 6 core creator categories."""
    perception = PerceptionNode()

    # 1. Dance / Choreo
    p_dance = perception.analyze_comment("c1", "That footwork transition on count 4 was insane how did you hit that?!")
    assert p_dance.category == CommentCategory.DANCE_CHOREO
    assert p_dance.action == SemioticIntentAction.ANSWER_LORE

    # 2. Fashion / Aesthetic
    p_fashion = perception.analyze_comment("c2", "Where is the vintage leather jacket from I need the fit check!")
    assert p_fashion.category == CommentCategory.FASHION_AESTHETIC
    assert p_fashion.action == SemioticIntentAction.SHARE_STYLING

    # 3. High-Energy Hype
    p_hype = perception.analyze_comment("c3", "YOU ATE AND LEFT ZERO CRUMBS BEST DANCER ALIVE 🔥🔥🔥")
    assert p_hype.category == CommentCategory.HYPE
    assert p_hype.energy_level >= 4
    assert p_hype.action == SemioticIntentAction.MATCH_HYPE

    # 4. Troll / Hater / Body Shaming
    p_troll = perception.analyze_comment("c4", "mid dance cover anyone could do this in 5 minutes + ratio")
    assert p_troll.category == CommentCategory.TROLL_OR_HATER
    assert p_troll.action == SemioticIntentAction.UNBOTHERED_DEFLECT
    assert p_troll.polarity < 0.0

    p_body = perception.analyze_comment("c5", "you look like you haven't eaten a real meal in weeks honestly")
    assert p_body.category == CommentCategory.TROLL_OR_HATER
    assert p_body.semiotic_intent == "BODY_SHAMING_DEFLECTION"

    # 5. Banter
    p_banter = perception.analyze_comment("c6", "me trying this in my living room and breaking my coffee table 💀")
    assert p_banter.category == CommentCategory.BANTER
    assert p_banter.action == SemioticIntentAction.PLAYFUL_BANTER

    # 6. Off-Topic / Unindexed
    p_offtopic = perception.analyze_comment("c7", "What is the best cryptocurrency to buy today?")
    assert p_offtopic.category == CommentCategory.UNINDEXED_OR_OFFTOPIC
    assert p_offtopic.action == SemioticIntentAction.OFFTOPIC_BRUSHOFF


def test_llm_council_routing_spanish():
    """Verify Spanish comments are dynamically detected and routed via the LLM Council."""
    perception = PerceptionNode()
    comment_text = "¡Increíble coreografía reina, devoraste con esos pasos de baile! 🔥"

    result = perception.analyze_comment("c_es_001", comment_text)

    assert result.language == "es"
    assert result.council_routed is True
    assert result.category == CommentCategory.HYPE
    assert result.energy_level >= 4
    assert result.polarity > 0.5
    assert "council_votes_count" in result.council_metadata
    assert result.council_metadata["council_votes_count"] >= 2


def test_llm_council_routing_arabic():
    """Verify Arabic comments are dynamically detected and routed via the LLM Council."""
    perception = PerceptionNode()
    comment_text = "فنانة ما شاء الله عليك احسن راقصة وابداع لا يوصف نار 🔥👑"

    result = perception.analyze_comment("c_ar_001", comment_text)

    assert result.language == "ar"
    assert result.council_routed is True
    assert result.category == CommentCategory.HYPE
    assert result.energy_level >= 4
    assert result.polarity > 0.5
    assert result.council_metadata["routing_metadata"]["regional_council_language"] == "ar"


def test_llm_council_routing_portuguese():
    """Verify Portuguese comments are dynamically detected and routed via the LLM Council."""
    perception = PerceptionNode()
    comment_text = "Você arrasou demais nessa dança, maravilhosa e perfeita! ❤️"

    result = perception.analyze_comment("c_pt_001", comment_text)

    assert result.language == "pt"
    assert result.council_routed is True
    assert result.category == CommentCategory.HYPE
    assert result.energy_level >= 4


def test_batch_comments_state_reset_and_no_stale_lamp_cache():
    """Verify that batch processing clears state and never deploys stale 'RIP to the lamp' string to non-lamp comments."""
    agent = GovernedYouTubeAgent()

    test_comments = [
        "What shoes are you wearing in the studio rehearsal?",
        "Where did you buy that vintage jacket?",
        "I tried this move in my living room and dropped my water bottle!",
        "Your footwork transition timing on count 3 was so clean!",
        "YOU ATE THIS DANCE COVER SO HARD 🔥",
    ]

    replies = []
    for idx, text in enumerate(test_comments):
        # Reset state per turn
        agent.reset_state()
        cmt = InboundComment(
            comment_id=f"cmt_batch_{idx}",
            video_id="v_batch_01",
            author_name=f"Viewer_{idx}",
            author_channel_id=f"UC_viewer_{idx}",
            text_original=text,
            published_at="2026-08-27T12:00:00Z",
        )
        res = agent.process_single_comment(cmt)
        replies.append(res.final_reply)

    # 1. Ensure all replies are non-empty strings
    assert all(isinstance(r, str) and len(r) > 0 for r in replies)

    # 2. Ensure non-lamp comments DO NOT output the stale lamp quote
    for idx, reply in enumerate(replies):
        assert "RIP to the lamp" not in reply, f"Stale lamp quote found in reply for comment {idx}: '{reply}'"

    # 3. Ensure uniqueness across diverse batch inputs (no static repetition)
    assert len(set(replies)) >= 3, f"Expected varied dynamic responses across batch, got: {replies}"


def test_hive_one_sentence_strict_enforcement():
    """Verify that AutonomousHiveNode strictly guarantees exactly ONE sentence output."""
    hive = AutonomousHiveNode()

    # Multi-sentence inputs
    assert hive._enforce_one_sentence("First sentence here. Second sentence should be removed! Third sentence?") == "First sentence here."
    assert hive._enforce_one_sentence("Single sentence without punctuation") == "Single sentence without punctuation!"
    assert hive._enforce_one_sentence("📌 Source: Video Docs (Reference: 01) Great fit!") == "Great fit!"


def test_hive_corpus_loaded_and_valid():
    """Verify that lumi_corpus.jsonl contains at least 25 authentic creator entries."""
    hive = AutonomousHiveNode()
    assert len(hive.corpus_entries) >= 25, f"Expected at least 25 entries in lumi_corpus.jsonl, got {len(hive.corpus_entries)}"

    # Verify no software/coding jargon exists in the corpus
    tech_banned_terms = ["docker", "postgres", "sqlite", "api pricing", "vector retrieval", "chromadb"]
    for entry in hive.corpus_entries:
        resp = entry.get("lumi_response", "").lower()
        for term in tech_banned_terms:
            assert term not in resp, f"Banned technical term '{term}' found in response: {resp}"


def test_swarm_engine_pipeline_execution():
    """Verify end-to-end swarm execution through Supervisor, Perception, and Hive."""
    engine = LumiSwarmEngine()

    decision = engine.process_comment_through_swarm(
        comment_id="c_test_001",
        author_id="fan_99",
        text="that footwork transition at 0:15 was literally impossible how did you hit that?!",
        video_id="v_test_choreo",
        video_title="Studio Rehearsal Vlog & Choreo Breakdown",
    )

    assert decision.video_context.room_temperature == RoomTemperature.DANCE_STUDIO
    assert decision.perception.category == CommentCategory.DANCE_CHOREO
    assert decision.dispatch_ready is True
    assert len(decision.final_output.split(".")) <= 2  # Max 1 sentence + empty trailing split
    assert "transition" in decision.final_output.lower() or "studio" in decision.final_output.lower() or "footwork" in decision.final_output.lower()


def test_governed_youtube_agent_swarm_integration():
    """Verify GovernedYouTubeAgent correctly delegates to Lumi swarm engine."""
    agent = GovernedYouTubeAgent()

    comment = InboundComment(
        comment_id="cmt_hype_001",
        video_id="dance_vid_01",
        author_name="SuperFan",
        author_channel_id="UC_superfan",
        text_original="YOU ATE AND LEFT ZERO CRUMBS BEST DANCER ON THIS APP 🔥🔥🔥",
        published_at="2026-08-26T23:00:00Z",
    )

    result = agent.process_single_comment(comment)

    assert result.is_blocked is False
    assert result.swarm_decision is not None
    assert result.swarm_decision.perception.category == CommentCategory.HYPE
    assert result.audit_record is not None
    assert result.audit_record.room_temperature is not None
    assert result.audit_record.comment_category == "HYPE"
    assert result.audit_record.energy_level >= 4
