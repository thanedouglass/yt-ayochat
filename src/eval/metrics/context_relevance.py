"""Context Relevance Metric evaluating ChromaDB retrieval Recall@k and Precision@k.

Adheres to Section 4.1 ('Retrieval evaluation: did we fetch the right context')
of the BASWE AI Evaluation Field Guide:
- Recall@k: Of all relevant gold chunks, how many appear in top-k.
- Precision@k: Of top-k chunks, how many are actually relevant.
- Hit Rate: Was at least one gold chunk retrieved.
"""

from __future__ import annotations

from typing import List

from src.eval.dataset import GoldenTestCase
from src.eval.metrics.base import BaseMetric, MetricResult
from src.pipeline.rag_service import RetrievedResult


class ContextRelevanceMetric(BaseMetric):
    """Measures retrieval surface quality by comparing retrieved chunks against expected gold chunks."""

    def __init__(self, threshold: float = 0.70) -> None:
        super().__init__(name="Context Relevance (Recall@k)", threshold=threshold)

    def evaluate(
        self,
        test_case: GoldenTestCase,
        retrieved_chunks: List[RetrievedResult],
        is_blocked: bool = False,
    ) -> MetricResult:
        """Calculate Recall@k, Precision@k, and Hit Rate for vector retrieval."""
        if test_case.expected_blocked or is_blocked:
            return MetricResult(
                name=self.name,
                score=1.0,
                threshold=self.threshold,
                passed=True,
                reason="Context retrieval appropriately bypassed for blocked adversarial request.",
            )

        expected_ids = set(test_case.expected_chunk_ids)
        retrieved_ids = [r.chunk.chunk_id for r in retrieved_chunks]

        # If test case has no expected chunks (e.g. pure out-of-scope query), lack of chunks is expected
        if not expected_ids:
            return MetricResult(
                name=self.name,
                score=1.0,
                threshold=self.threshold,
                passed=True,
                reason="Out-of-scope query correctly expected zero relevant chunks in corpus.",
                details={
                    "retrieved_chunk_ids": retrieved_ids,
                    "recall_at_k": 1.0,
                    "hit_rate": 1.0,
                },
            )

        matched_ids = [cid for cid in expected_ids if cid in retrieved_ids]
        recall_at_k = len(matched_ids) / len(expected_ids)
        precision_at_k = len(matched_ids) / (len(retrieved_ids) or 1)
        hit_rate = 1.0 if len(matched_ids) > 0 else 0.0

        avg_cosine = (
            sum(r.cosine_score for r in retrieved_chunks) / len(retrieved_chunks)
            if retrieved_chunks
            else 0.0
        )

        passed = recall_at_k >= self.threshold
        reason = (
            f"Recall@{len(retrieved_ids)}: {recall_at_k:.2f} ({len(matched_ids)}/{len(expected_ids)} gold chunks retrieved: {matched_ids}). "
            f"Precision@{len(retrieved_ids)}: {precision_at_k:.2f}, Avg Cosine: {avg_cosine:.2f}."
        )

        return MetricResult(
            name=self.name,
            score=recall_at_k,
            threshold=self.threshold,
            passed=passed,
            reason=reason,
            details={
                "recall_at_k": round(recall_at_k, 4),
                "precision_at_k": round(precision_at_k, 4),
                "hit_rate": hit_rate,
                "retrieved_chunk_ids": retrieved_ids,
                "expected_chunk_ids": list(expected_ids),
                "matched_chunk_ids": matched_ids,
                "avg_cosine_score": round(avg_cosine, 4),
            },
        )
