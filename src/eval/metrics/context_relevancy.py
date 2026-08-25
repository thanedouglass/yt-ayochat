"""Context Relevancy metric evaluating vector search retrieval precision & recall."""

from __future__ import annotations

from typing import List

from src.eval.dataset import EvalTestCase
from src.eval.metrics.base import BaseMetric, MetricResult
from src.pipeline.rag_service import RetrievedResult


class ContextRelevancyMetric(BaseMetric):
    """Evaluates whether ChromaDB vector retrieval pulled chunks relevant to the user query."""

    def __init__(self, threshold: float = 0.7) -> None:
        super().__init__(name="Context Relevancy", threshold=threshold)

    def evaluate(
        self,
        test_case: EvalTestCase,
        retrieved_chunks: List[RetrievedResult],
        is_blocked: bool = False,
    ) -> MetricResult:
        """Evaluate retrieval relevance against expected gold chunks and query intent."""
        if test_case.expected_blocked:
            return MetricResult(
                name=self.name,
                score=1.0,
                threshold=self.threshold,
                passed=True,
                reason="Context retrieval appropriately skipped for blocked adversarial query.",
            )

        if test_case.expected_refusal and not test_case.expected_relevant_chunk_ids:
            # For pure out-of-scope query, retrieval having low relevance or no relevant chunks is expected
            return MetricResult(
                name=self.name,
                score=1.0,
                threshold=self.threshold,
                passed=True,
                reason="Out-of-scope query correctly lacks relevant chunks in knowledge base.",
                details={"retrieved_chunk_ids": [r.chunk.chunk_id for r in retrieved_chunks]},
            )

        retrieved_ids = [r.chunk.chunk_id for r in retrieved_chunks]
        expected_ids = set(test_case.expected_relevant_chunk_ids)

        if not expected_ids:
            return MetricResult(
                name=self.name,
                score=1.0,
                threshold=self.threshold,
                passed=True,
                reason="No specific gold chunks required for this test case.",
            )

        # Calculate Recall of expected chunks
        matched_ids = [cid for cid in expected_ids if cid in retrieved_ids]
        recall = len(matched_ids) / len(expected_ids)

        # Calculate average similarity score of retrieved chunks
        avg_score = (
            sum(r.cosine_score for r in retrieved_chunks) / len(retrieved_chunks)
            if retrieved_chunks
            else 0.0
        )

        passed = recall >= self.threshold
        reason = (
            f"Retrieved {len(matched_ids)}/{len(expected_ids)} target chunks ({matched_ids}). "
            f"Average cosine similarity: {avg_score:.2f}."
        )

        return MetricResult(
            name=self.name,
            score=recall,
            threshold=self.threshold,
            passed=passed,
            reason=reason,
            details={
                "retrieved_chunk_ids": retrieved_ids,
                "expected_chunk_ids": list(expected_ids),
                "matched_chunk_ids": matched_ids,
                "avg_cosine_score": round(avg_score, 4),
            },
        )
