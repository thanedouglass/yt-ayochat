"""Pytest test suite implementing Eval-Driven Development (EDD) and the RAG Triad.

Adheres directly to the BASWE AI Evaluation Field Guide:
- Golden Dataset v1.2.0 (Section 1.4)
- RAG Triad: Context Relevance, Faithfulness, Answer Relevance (Section 4.3)
- Calibrated LLM Judge (Section 3.2)
- CI/CD Eval Gate (Section 7.6)
"""

from __future__ import annotations

import pytest
from src.eval.dataset import (
    GOLDEN_DATASET,
    GOLDEN_DATASET_VERSION,
    get_golden_dataset,
)
from src.eval.evaluator import RAGEvaluator
from src.eval.metrics.triad import FailureSurface
from scripts.run_evals import build_evaluation_agent


@pytest.fixture
def eval_harness() -> RAGEvaluator:
    agent = build_evaluation_agent()
    return RAGEvaluator(
        agent=agent,
        faithfulness_gate_threshold=0.90,
        context_relevance_threshold=0.70,
        answer_relevance_threshold=0.80,
    )


def test_golden_dataset_versioning_and_structure():
    """Verify the Golden Dataset adheres to Section 1.4 schema requirements."""
    dataset = get_golden_dataset()
    assert len(dataset) == 7, "Expected 7 Golden test cases (5 core + 2 adversarial/privacy)"
    assert GOLDEN_DATASET_VERSION == "1.2.0"

    for tc in dataset:
        assert tc.id.startswith("GOLDEN-")
        assert len(tc.query) > 0
        if not tc.expected_blocked:
            assert len(tc.expected_answer) > 0
            # Ensure expected context chunks are provided to isolate retrieval from generation
            if not tc.expected_refusal:
                assert len(tc.expected_context_chunks) > 0


def test_rag_triad_and_governance_full_golden_suite(eval_harness: RAGEvaluator):
    """Run full Golden Dataset through RAG Triad evaluation harness."""
    dataset = get_golden_dataset()
    report = eval_harness.run_suite(test_cases=dataset, seed_knowledge=True)

    assert report.total_tests == 7
    assert report.passed_tests == 7
    assert report.failed_tests == 0
    assert report.overall_pass_rate == 1.0
    assert report.gate_passed is True

    # Validate RAG Triad metric averages
    metrics = report.metric_averages
    assert metrics["Faithfulness (Groundedness)"] >= 0.90, "Faithfulness failed CI gate"
    assert metrics["Context Relevance (Recall@k)"] >= 0.70, "Context Relevance failed threshold"
    assert metrics["Answer Relevance"] >= 0.80, "Answer Relevance failed threshold"
    assert metrics["Security & Governance"] == 1.0, "Security failed threshold"
    assert metrics["Citation Accuracy"] == 1.0, "Citation accuracy failed threshold"


def test_rag_triad_diagnostics_healthy_status(eval_harness: RAGEvaluator):
    """Verify that all passing test cases yield a HEALTHY failure surface diagnosis."""
    dataset = get_golden_dataset()
    report = eval_harness.run_suite(test_cases=dataset, seed_knowledge=True)

    for result in report.test_results:
        assert result.diagnosis.surface == FailureSurface.HEALTHY
        assert "Optimal execution" in result.diagnosis.symptom or "Adversarial input intercepted" in result.diagnosis.symptom


def test_ci_eval_gate_blocks_on_faithfulness_drop(eval_harness: RAGEvaluator):
    """Verify the CI gate trips and returns False if the faithfulness threshold is set impossibly high."""
    strict_evaluator = RAGEvaluator(
        agent=eval_harness.agent,
        faithfulness_gate_threshold=1.01,  # Impossible threshold to verify gate tripping
    )
    report = strict_evaluator.run_suite(test_cases=get_golden_dataset(), seed_knowledge=True)
    assert report.gate_passed is False
    assert any("dropped below CI gate threshold" in r for r in report.gate_failure_reasons)
