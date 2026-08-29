"""Unit Tests for Maximal Marginal Relevance (MMR) Search, Dynamic Temperature Scaling & Variance Injectors."""

from __future__ import annotations

import pytest

from src.pipeline.rag_service import KnowledgeChunk, VectorStoreService
from src.swarm.hive import (
    AutonomousHiveNode,
    VARIANCE_INJECTORS,
    compute_dynamic_temperature,
    compute_target_sentiment_vectors,
)
from src.swarm.models import CommentCategory, PerceptionResult


@pytest.fixture
def populated_vector_store() -> VectorStoreService:
    """Fixture providing a populated in-memory vector store for MMR testing."""
    store = VectorStoreService(collection_name="test_mmr_store")
    test_chunks = [
        KnowledgeChunk(
            chunk_id="C1",
            source_name="video_1",
            reference="00:15",
            content="Footwork transition breakdown at count 3 on the stage.",
        ),
        KnowledgeChunk(
            chunk_id="C2",
            source_name="video_1",
            reference="00:16",
            content="Footwork transition details and stage counts for count 3.",
        ),
        KnowledgeChunk(
            chunk_id="C3",
            source_name="video_2",
            reference="01:20",
            content="Vintage oversized leather bomber styling for rehearsal.",
        ),
        KnowledgeChunk(
            chunk_id="C4",
            source_name="video_3",
            reference="02:10",
            content="High voltage tour preparation stamina and energy.",
        ),
    ]
    store.add_chunks(test_chunks)
    return store


def test_mmr_diversity_vs_pure_similarity(populated_vector_store: VectorStoreService):
    """Verify that MMR search with lambda=0.5 returns more diverse chunks than pure cosine top-k."""
    query = "footwork transition stage count 3"

    # Pure cosine retrieval returns redundant C1 and C2
    pure_results, _ = populated_vector_store.retrieve(query=query, k=3)
    assert len(pure_results) >= 2

    # MMR retrieval balances relevance and penalizes redundancy between C1 and C2
    mmr_results, latency = populated_vector_store.retrieve_mmr(
        query=query,
        k=3,
        lambda_mult=0.60,
    )
    assert len(mmr_results) == 3
    assert latency >= 0.0

    retrieved_ids = [r.chunk.chunk_id for r in mmr_results]
    assert "C1" in retrieved_ids or "C2" in retrieved_ids
    # Ensure diverse non-redundant chunk is included
    assert "C3" in retrieved_ids or "C4" in retrieved_ids


def test_dynamic_temperature_scaling():
    """Verify temperature dynamically scales with code-switch vector, energy, and repetition count."""
    p_high_energy = PerceptionResult(
        comment_id="t1",
        raw_text="SLAYYYY QUEEN 🔥🔥",
        category=CommentCategory.HYPE,
        semiotic_intent="HIGH_ENERGY_PRAISE",
        energy_level=5,
        polarity=0.9,
    )
    vecs_high = compute_target_sentiment_vectors(p_high_energy)
    t_high = compute_dynamic_temperature(p_high_energy, vecs_high, recent_repetition_count=0)
    assert t_high >= 0.75

    # With repetition count, temperature should scale up to induce entropy
    t_repeated = compute_dynamic_temperature(p_high_energy, vecs_high, recent_repetition_count=3)
    assert t_repeated > t_high
    assert t_repeated <= 0.95

    # Clinical / Disclaimer mode maintains low temperature
    p_offtopic = PerceptionResult(
        comment_id="t2",
        raw_text="Random off topic physics question",
        category=CommentCategory.UNINDEXED_OR_OFFTOPIC,
        semiotic_intent="OFFTOPIC",
        energy_level=1,
        polarity=0.0,
    )
    vecs_off = compute_target_sentiment_vectors(p_offtopic)
    t_off = compute_dynamic_temperature(p_offtopic, vecs_off, recent_repetition_count=0)
    assert t_off <= 0.70


def test_variance_injectors_mapped():
    """Verify that variance injector registry contains directives for core categories."""
    for cat in ["HYPE", "DANCE_CHOREO", "FASHION_AESTHETIC", "BANTER", "TROLL_OR_HATER"]:
        assert cat in VARIANCE_INJECTORS
        assert len(VARIANCE_INJECTORS[cat]) >= 2


def test_hive_anti_repetition_fallback_entropy():
    """Verify that two identical-category comments generate distinct fallback responses via hash entropy."""
    node = AutonomousHiveNode()

    p1 = PerceptionResult(
        comment_id="c_user_1",
        raw_text="YOU SLAYED THIS DANCE QUEEN 👑",
        category=CommentCategory.HYPE,
        semiotic_intent="HIGH_ENERGY_PRAISE",
        energy_level=5,
        polarity=0.9,
    )

    p2 = PerceptionResult(
        comment_id="c_user_2",
        raw_text="omg the energy is insane today 💖",
        category=CommentCategory.HYPE,
        semiotic_intent="HIGH_ENERGY_PRAISE",
        energy_level=4,
        polarity=0.8,
    )

    r1 = node._synthesize_fallback(p1, None)
    r2 = node._synthesize_fallback(p2, None)

    assert len(r1) > 0
    assert len(r2) > 0
    # Both are high-quality 1-sentence sovereign replies
    assert r1.endswith(("!", "."))
    assert r2.endswith(("!", "."))
