"""Evaluation and measurement layer for yt-ayochat implementing Eval-Driven Development (EDD)."""

from src.eval.dataset import (
    GOLDEN_DATASET,
    GOLDEN_DATASET_VERSION,
    ExpectedContextChunk,
    GoldenTestCase,
    TestCaseType,
    get_corpus_chunks,
    get_golden_dataset,
)
from src.eval.evaluator import (
    EvaluationReport,
    RAGEvaluator,
    TestCaseEvaluationResult,
)
from src.eval.judge import (
    CalibratedLLMJudge,
    JudgeVerdict,
    llm_judge,
)
from src.eval.metrics import (
    AnswerRelevanceMetric,
    BaseMetric,
    CitationAccuracyMetric,
    ContextRelevanceMetric,
    FailureSurface,
    FaithfulnessMetric,
    MetricResult,
    SecurityGovernanceMetric,
    TriadDiagnosis,
    diagnose_rag_triad,
)

__all__ = [
    "AnswerRelevanceMetric",
    "BaseMetric",
    "CalibratedLLMJudge",
    "CitationAccuracyMetric",
    "ContextRelevanceMetric",
    "EvaluationReport",
    "ExpectedContextChunk",
    "FailureSurface",
    "FaithfulnessMetric",
    "GOLDEN_DATASET",
    "GOLDEN_DATASET_VERSION",
    "GoldenTestCase",
    "JudgeVerdict",
    "MetricResult",
    "RAGEvaluator",
    "SecurityGovernanceMetric",
    "TestCaseType",
    "TestCaseEvaluationResult",
    "TriadDiagnosis",
    "diagnose_rag_triad",
    "get_corpus_chunks",
    "get_golden_dataset",
    "llm_judge",
]
