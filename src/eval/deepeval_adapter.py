"""DeepEval adapter for integrating yt-ayochat with DeepEval framework."""

from __future__ import annotations

from typing import Any, List, Optional

try:
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams
    from deepeval.metrics import (
        FaithfulnessMetric as DeepEvalFaithfulnessMetric,
        ContextualRelevancyMetric as DeepEvalContextualRelevancyMetric,
    )
    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False

from src.eval.dataset import GoldenTestCase
from src.pipeline.rag_service import RetrievedResult


def convert_to_deepeval_test_case(
    test_case: GoldenTestCase,
    actual_output: str,
    retrieved_chunks: List[RetrievedResult],
) -> Optional[Any]:
    """Convert an internal GoldenTestCase into a DeepEval LLMTestCase."""
    if not DEEPEVAL_AVAILABLE:
        return None

    retrieval_context = [r.chunk.content for r in retrieved_chunks]

    return LLMTestCase(
        input=test_case.query,
        actual_output=actual_output or "",
        expected_output=test_case.expected_answer,
        retrieval_context=retrieval_context,
        context=retrieval_context,
    )
