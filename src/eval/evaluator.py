"""Unified RAG Evaluation Engine and Report Generator implementing EDD and the RAG Triad."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agent import GovernedYouTubeAgent, youtube_agent
from src.eval.dataset import (
    GOLDEN_DATASET_VERSION,
    GoldenTestCase,
    get_corpus_chunks,
    get_golden_dataset,
)
from src.eval.metrics.answer_relevance import AnswerRelevanceMetric
from src.eval.metrics.base import MetricResult
from src.eval.metrics.citation import CitationAccuracyMetric
from src.eval.metrics.context_relevance import ContextRelevanceMetric
from src.eval.metrics.faithfulness import FaithfulnessMetric
from src.eval.metrics.security import SecurityGovernanceMetric
from src.eval.metrics.triad import TriadDiagnosis, diagnose_rag_triad
from src.pipeline.listener import InboundComment
from src.pipeline.rag_service import KnowledgeChunk


@dataclass
class TestCaseEvaluationResult:
    """Evaluation output for an individual test case."""
    test_id: str
    test_name: str
    test_type: str
    query: str
    sanitized_query: str
    generated_response: Optional[str]
    is_blocked: bool
    retrieved_chunk_ids: List[str]
    expected_chunk_ids: List[str]
    latency_ms: float
    metrics: Dict[str, MetricResult]
    diagnosis: TriadDiagnosis
    passed: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "test_type": self.test_type,
            "query": self.query,
            "sanitized_query": self.sanitized_query,
            "generated_response": self.generated_response,
            "is_blocked": self.is_blocked,
            "retrieved_chunk_ids": self.retrieved_chunk_ids,
            "expected_chunk_ids": self.expected_chunk_ids,
            "latency_ms": round(self.latency_ms, 2),
            "passed": self.passed,
            "diagnosis": {
                "surface": self.diagnosis.surface.value,
                "symptom": self.diagnosis.symptom,
                "root_cause": self.diagnosis.root_cause_explanation,
                "prescribed_fix": self.diagnosis.prescribed_fix,
            },
            "metrics": {k: v.to_dict() for k, v in self.metrics.items()},
        }


@dataclass
class EvaluationReport:
    """Comprehensive evaluation summary report."""
    dataset_version: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    overall_pass_rate: float
    metric_averages: Dict[str, float]
    avg_latency_ms: float
    gate_passed: bool
    gate_failure_reasons: List[str]
    test_results: List[TestCaseEvaluationResult]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": {
                "dataset_version": self.dataset_version,
                "total_tests": self.total_tests,
                "passed_tests": self.passed_tests,
                "failed_tests": self.failed_tests,
                "overall_pass_rate": round(self.overall_pass_rate, 4),
                "gate_passed": self.gate_passed,
                "gate_failure_reasons": self.gate_failure_reasons,
                "metric_averages": {k: round(v, 4) for k, v in self.metric_averages.items()},
                "avg_latency_ms": round(self.avg_latency_ms, 2),
                "timestamp": self.timestamp,
            },
            "results": [r.to_dict() for r in self.test_results],
        }

    def save_json(self, output_path: str | Path) -> None:
        """Export report to a JSON file."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    def print_terminal_summary(self) -> None:
        """Print a structured terminal summary report."""
        separator = "=" * 88
        sub_sep = "-" * 88

        print(f"\n{separator}")
        print("          🧪 YT-AYOCHAT RAG TRIAD & GOVERNANCE EVALUATION REPORT")
        print(f"{separator}")
        print(f" Dataset Version:  {self.dataset_version}")
        print(f" Timestamp:        {self.timestamp}")
        print(f" Total Tests:      {self.total_tests}")
        print(f" Pass Rate:        {self.passed_tests} / {self.total_tests} ({self.overall_pass_rate * 100:.1f}%)")
        print(f" CI/CD Gate:       {'🟢 PASSED' if self.gate_passed else '🔴 FAILED'}")
        if self.gate_failure_reasons:
            for r in self.gate_failure_reasons:
                print(f"   ⚠️  Gate Block: {r}")
        print(f" Avg Latency:      {self.avg_latency_ms:.2f} ms")
        print(f"{sub_sep}")

        print(" 📊 RAG TRIAD & GOVERNANCE METRICS:")
        for metric, score in self.metric_averages.items():
            status_symbol = "✅ PASS" if score >= 0.8 else "❌ FAIL"
            print(f"   • {metric:<32}: {score * 100:>5.1f}%  [{status_symbol}]")
        print(f"{sub_sep}")

        print("\n 🔍 DETAILED TEST BREAKDOWN & RAG TRIAD DIAGNOSIS:")
        print(f" {'ID':<11} | {'TEST NAME':<34} | {'STATUS':<6} | {'RECALL':<7} | {'FAITH':<6} | {'REL':<6} | {'SURFACE':<14}")
        print(f" {'-'*11}-+-{'-'*34}-+-{'-'*6}-+-{'-'*7}-+-{'-'*6}-+-{'-'*6}-+-{'-'*14}")

        for res in self.test_results:
            status_str = "PASS" if res.passed else "FAIL"
            recall_score = f"{res.metrics['Context Relevance (Recall@k)'].score:.2f}" if "Context Relevance (Recall@k)" in res.metrics else "N/A"
            faith_score = f"{res.metrics['Faithfulness (Groundedness)'].score:.2f}" if "Faithfulness (Groundedness)" in res.metrics else "N/A"
            rel_score = f"{res.metrics['Answer Relevance'].score:.2f}" if "Answer Relevance" in res.metrics else "N/A"
            surface = res.diagnosis.surface.value

            print(
                f" {res.test_id:<11} | {res.test_name[:34]:<34} | {status_str:<6} | {recall_score:<7} | {faith_score:<6} | {rel_score:<6} | {surface:<14}"
            )

        print(f"{separator}\n")


class RAGEvaluator:
    """Orchestrates evaluation across the Golden Dataset and evaluates the RAG Triad."""

    def __init__(
        self,
        agent: Optional[GovernedYouTubeAgent] = None,
        faithfulness_gate_threshold: float = 0.90,
        context_relevance_threshold: float = 0.70,
        answer_relevance_threshold: float = 0.80,
    ) -> None:
        self.agent = agent or youtube_agent
        self.faithfulness_gate_threshold = faithfulness_gate_threshold
        self.context_relevance_threshold = context_relevance_threshold
        self.answer_relevance_threshold = answer_relevance_threshold

        self.context_relevance_metric = ContextRelevanceMetric(threshold=context_relevance_threshold)
        self.faithfulness_metric = FaithfulnessMetric(threshold=faithfulness_gate_threshold)
        self.answer_relevance_metric = AnswerRelevanceMetric(threshold=answer_relevance_threshold)
        self.security_metric = SecurityGovernanceMetric(threshold=1.0)
        self.citation_metric = CitationAccuracyMetric(threshold=1.0)

    def evaluate_test_case(self, test_case: GoldenTestCase) -> TestCaseEvaluationResult:
        """Run a single test case through the agent and evaluate against all metrics."""
        start_time = time.perf_counter()

        comment = InboundComment(
            comment_id=f"eval_cmt_{test_case.id.lower()}",
            video_id="eval_video_benchmark",
            author_name="EvalUser",
            author_channel_id=f"UC_eval_{test_case.id.lower()}",
            text_original=test_case.query,
            published_at="2026-08-25T12:00:00Z",
        )

        trace_id = f"eval-trace-{test_case.id.lower()}"
        agent_result = self.agent.process_single_comment(comment, trace_id=trace_id)
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        # Retrieve chunks for context relevance evaluation
        retrieved_chunks = []
        if not agent_result.is_blocked:
            retrieved_chunks, _ = self.agent.gateway.rag_svc.vector_store.retrieve(
                agent_result.sanitized_text, k=3
            )

        # 1. RAG Triad Metric 1: Context Relevance (Recall@k)
        cr_result = self.context_relevance_metric.evaluate(
            test_case=test_case,
            retrieved_chunks=retrieved_chunks,
            is_blocked=agent_result.is_blocked,
        )

        # 2. RAG Triad Metric 2: Faithfulness (Groundedness)
        faith_result = self.faithfulness_metric.evaluate(
            test_case=test_case,
            generated_response=agent_result.final_reply,
            retrieved_chunks=retrieved_chunks,
            is_blocked=agent_result.is_blocked,
        )

        # 3. RAG Triad Metric 3: Answer Relevance
        ar_result = self.answer_relevance_metric.evaluate(
            test_case=test_case,
            generated_response=agent_result.final_reply,
            is_blocked=agent_result.is_blocked,
        )

        # 4. Security & Governance Metric
        sec_result = self.security_metric.evaluate(
            test_case=test_case,
            is_blocked=agent_result.is_blocked,
            sanitized_query=agent_result.sanitized_text,
            audit_record=agent_result.audit_record,
        )

        # 5. Citation Accuracy Metric
        cite_result = self.citation_metric.evaluate(
            test_case=test_case,
            generated_response=agent_result.final_reply,
            is_blocked=agent_result.is_blocked,
        )

        metrics = {
            self.context_relevance_metric.name: cr_result,
            self.faithfulness_metric.name: faith_result,
            self.answer_relevance_metric.name: ar_result,
            self.security_metric.name: sec_result,
            self.citation_metric.name: cite_result,
        }

        # Root-cause diagnosis via RAG Triad
        diagnosis = diagnose_rag_triad(
            context_relevance=cr_result,
            faithfulness=faith_result,
            answer_relevance=ar_result,
            is_blocked=agent_result.is_blocked,
            expected_blocked=test_case.expected_blocked,
        )

        all_passed = all(m.passed for m in metrics.values())
        retrieved_ids = [r.chunk.chunk_id for r in retrieved_chunks]

        return TestCaseEvaluationResult(
            test_id=test_case.id,
            test_name=test_case.name,
            test_type=test_case.test_type.value,
            query=test_case.query,
            sanitized_query=agent_result.sanitized_text,
            generated_response=agent_result.final_reply,
            is_blocked=agent_result.is_blocked,
            retrieved_chunk_ids=retrieved_ids,
            expected_chunk_ids=test_case.expected_chunk_ids,
            latency_ms=latency_ms,
            metrics=metrics,
            diagnosis=diagnosis,
            passed=all_passed,
        )

    def run_suite(
        self,
        test_cases: Optional[List[GoldenTestCase]] = None,
        seed_knowledge: bool = True,
    ) -> EvaluationReport:
        """Run full evaluation across specified test cases."""
        if seed_knowledge:
            corpus = get_corpus_chunks()
            knowledge_chunks = [
                KnowledgeChunk(
                    chunk_id=c.chunk_id,
                    source_name=c.source_name,
                    reference=c.reference,
                    content=c.content,
                )
                for c in corpus
            ]
            self.agent.gateway.rag_svc.vector_store.add_chunks(knowledge_chunks)

        cases = test_cases or get_golden_dataset()
        results: List[TestCaseEvaluationResult] = []

        for case in cases:
            res = self.evaluate_test_case(case)
            results.append(res)

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        pass_rate = passed / total if total > 0 else 0.0

        # Aggregate metric averages
        metric_sums: Dict[str, float] = {}
        for r in results:
            for m_name, m_res in r.metrics.items():
                metric_sums[m_name] = metric_sums.get(m_name, 0.0) + m_res.score

        metric_averages = {
            m_name: (total_score / total) if total > 0 else 0.0
            for m_name, total_score in metric_sums.items()
        }

        avg_latency = sum(r.latency_ms for r in results) / total if total > 0 else 0.0

        # Evaluate CI/CD Gate Criteria
        gate_passed = True
        gate_failure_reasons = []

        faith_avg = metric_averages.get("Faithfulness (Groundedness)", 0.0)
        if faith_avg < self.faithfulness_gate_threshold:
            gate_passed = False
            gate_failure_reasons.append(
                f"Aggregate Faithfulness ({faith_avg:.2f}) dropped below CI gate threshold ({self.faithfulness_gate_threshold:.2f})"
            )

        if failed > 0:
            gate_passed = False
            gate_failure_reasons.append(f"{failed}/{total} test cases failed individual assertions.")

        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).isoformat()

        return EvaluationReport(
            dataset_version=GOLDEN_DATASET_VERSION,
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            overall_pass_rate=pass_rate,
            metric_averages=metric_averages,
            avg_latency_ms=avg_latency,
            gate_passed=gate_passed,
            gate_failure_reasons=gate_failure_reasons,
            test_results=results,
            timestamp=timestamp,
        )
