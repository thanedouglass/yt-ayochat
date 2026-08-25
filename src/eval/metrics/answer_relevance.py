"""Answer Relevance Metric evaluating intent fulfillment and conciseness.

Adheres to Section 4.2 ('Answer relevance: did it answer the question')
of the BASWE AI Evaluation Field Guide.
"""

from __future__ import annotations

from typing import Optional

from src.eval.dataset import GoldenTestCase
from src.eval.judge import CalibratedLLMJudge, JudgeVerdict, llm_judge
from src.eval.metrics.base import BaseMetric, MetricResult


class AnswerRelevanceMetric(BaseMetric):
    """Evaluates whether the final response directly addresses the user's query intent."""

    def __init__(
        self,
        threshold: float = 0.80,
        judge: Optional[CalibratedLLMJudge] = None,
    ) -> None:
        super().__init__(name="Answer Relevance", threshold=threshold)
        self.judge = judge or llm_judge

    def evaluate(
        self,
        test_case: GoldenTestCase,
        generated_response: Optional[str],
        is_blocked: bool = False,
    ) -> MetricResult:
        """Evaluate how directly the generated answer addresses the user query."""
        if test_case.expected_blocked or is_blocked:
            return MetricResult(
                name=self.name,
                score=1.0,
                threshold=self.threshold,
                passed=True,
                reason="Answer relevance check skipped for blocked adversarial query.",
            )

        if not generated_response:
            return MetricResult(
                name=self.name,
                score=0.0,
                threshold=self.threshold,
                passed=False,
                reason="No response generated to evaluate for relevance.",
            )

        verdict: JudgeVerdict = self.judge.evaluate_answer_relevance(
            query=test_case.query,
            generated_answer=generated_response,
        )

        passed = verdict.normalized_score >= self.threshold
        return MetricResult(
            name=self.name,
            score=verdict.normalized_score,
            threshold=self.threshold,
            passed=passed,
            reason=f"Judge Rubric Score {verdict.score}/5: {verdict.reasoning}",
            details={
                "judge_score_raw": verdict.score,
                "normalized_score": verdict.normalized_score,
            },
        )
