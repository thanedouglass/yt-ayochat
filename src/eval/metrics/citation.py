"""Citation Accuracy metric evaluating source attribution compliance."""

from __future__ import annotations

from typing import Optional

from src.eval.dataset import GoldenTestCase
from src.eval.metrics.base import BaseMetric, MetricResult


class CitationAccuracyMetric(BaseMetric):
    """Evaluates whether citations strictly adhere to channel formatting and metadata."""

    def __init__(self, threshold: float = 1.0) -> None:
        super().__init__(name="Citation Accuracy", threshold=threshold)

    def evaluate(
        self,
        test_case: GoldenTestCase,
        generated_response: Optional[str],
        is_blocked: bool = False,
    ) -> MetricResult:
        """Evaluate citation presence and format against ground truth metadata."""
        if test_case.expected_blocked or is_blocked:
            return MetricResult(
                name=self.name,
                score=1.0,
                threshold=self.threshold,
                passed=True,
                reason="Citation check skipped for blocked request.",
            )

        if generated_response is None:
            return MetricResult(
                name=self.name,
                score=0.0,
                threshold=self.threshold,
                passed=False,
                reason="No response generated.",
            )

        # Refusal cases must NOT have citations
        if test_case.expected_refusal:
            has_citation = "📌 Source:" in generated_response or "📌 source:" in generated_response
            if not has_citation:
                return MetricResult(
                    name=self.name,
                    score=1.0,
                    threshold=self.threshold,
                    passed=True,
                    reason="Refusal response correctly omitted citation tag.",
                )
            else:
                return MetricResult(
                    name=self.name,
                    score=0.0,
                    threshold=self.threshold,
                    passed=False,
                    reason="Refusal response erroneously appended a citation.",
                )

        # Factual answers MUST have citations matching expected source
        if test_case.expected_citation:
            if test_case.expected_citation.lower() in generated_response.lower():
                return MetricResult(
                    name=self.name,
                    score=1.0,
                    threshold=self.threshold,
                    passed=True,
                    reason=f"Citation strictly matches expected source: {test_case.expected_citation}",
                )
            else:
                return MetricResult(
                    name=self.name,
                    score=0.0,
                    threshold=self.threshold,
                    passed=False,
                    reason=f"Citation missing or mismatched. Expected: {test_case.expected_citation}",
                )

        return MetricResult(
            name=self.name,
            score=1.0,
            threshold=self.threshold,
            passed=True,
            reason="Citation check satisfied.",
        )
