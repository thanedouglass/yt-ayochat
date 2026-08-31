"""CI/CD Evaluation Runner and Gate for yt-ayochat Governed RAG Pipeline.

Implements Section 1.2 ('The core loop: eval driven development') and Section 7.6
('Ci/cd for llm applications: THE EVAL GATE') from the BASWE AI Evaluation Field Guide.

Core Loop:
1. Baseline: Run system on fixed Golden Dataset, record scores.
2. Change: Modify prompt, model, retriever, or guardrail.
3. Measure: Rerun on same dataset, compare to baseline.
4. Decide: If score up, ship it. If score down, revert it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.agent import GovernedYouTubeAgent
from src.eval.dataset import (
    GOLDEN_DATASET_VERSION,
    get_golden_dataset,
)
from src.eval.evaluator import RAGEvaluator
from src.pipeline.dispatcher import ActionDispatcher
from src.pipeline.gateway import (
    AgentGateway,
    CircuitBreaker,
    SlidingWindowRateLimiter,
)
from src.pipeline.rag_service import (
    RAGService,
    VectorStoreService,
    VertexAIGenerator,
)
from tests.test_governance_pipeline import create_mock_llm_for_eval


def build_evaluation_agent() -> GovernedYouTubeAgent:
    """Constructs a deterministic agent harness for evaluation benchmarking."""
    vector_store = VectorStoreService(collection_name="eval-cli-store")
    generator = VertexAIGenerator(llm_fn=create_mock_llm_for_eval())
    rag_svc = RAGService(vector_store=vector_store, generator=generator)
    
    rate_limiter = SlidingWindowRateLimiter(max_requests_per_minute=200)
    circuit_breaker = CircuitBreaker(failure_threshold=10, recovery_timeout_sec=5.0)
    gateway = AgentGateway(
        rag_svc=rag_svc,
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
    )
    dispatcher = ActionDispatcher(dry_run=True)
    return GovernedYouTubeAgent(gateway=gateway, dispatcher=dispatcher)


def compare_with_baseline(current_report: dict, baseline_file: str) -> None:
    """Print delta comparison between current run and a saved baseline."""
    baseline_path = Path(baseline_file)
    if not baseline_path.exists():
        print(f"\n⚠️  Baseline file '{baseline_file}' not found. Skipping delta comparison.")
        return

    try:
        with open(baseline_path, "r", encoding="utf-8") as f:
            baseline_data = json.load(f)

        base_summary = baseline_data.get("summary", {})
        curr_summary = current_report.get("summary", {})

        print("\n" + "=" * 80)
        print(f" 📈 EVALUATION COMPARISON VS BASELINE ({baseline_path.name})")
        print("=" * 80)

        base_pass_rate = base_summary.get("overall_pass_rate", 0.0)
        curr_pass_rate = curr_summary.get("overall_pass_rate", 0.0)
        delta_pass = curr_pass_rate - base_pass_rate
        print(f" Pass Rate:       {base_pass_rate*100:.1f}% ➔ {curr_pass_rate*100:.1f}% ({delta_pass*100:+.1f}%)")

        print("\n Metric Deltas:")
        base_metrics = base_summary.get("metric_averages", {})
        curr_metrics = curr_summary.get("metric_averages", {})

        for m_name, curr_score in curr_metrics.items():
            base_score = base_metrics.get(m_name, 0.0)
            delta = curr_score - base_score
            arrow = "🔼" if delta > 0 else ("🔻" if delta < 0 else "➖")
            print(f"   {arrow} {m_name:<32}: {base_score*100:.1f}% ➔ {curr_score*100:.1f}% ({delta*100:+.1f}%)")

        print("=" * 80 + "\n")
    except Exception as e:
        print(f"\n⚠️  Error parsing baseline file: {e}")


def main() -> int:
    default_output = "data/eval_report.json" if Path("data").exists() else "eval_report.json"
    parser = argparse.ArgumentParser(
        description="Run RAG Triad & Governance Evaluation Gate for yt-ayochat"
    )
    parser.add_argument(
        "--faithfulness-threshold",
        type=float,
        default=0.90,
        help="CI Gate threshold for aggregate Faithfulness score (default: 0.90)",
    )
    parser.add_argument(
        "--relevance-threshold",
        type=float,
        default=0.70,
        help="Passing threshold for Context Relevance (Recall@k) metric (default: 0.70)",
    )
    parser.add_argument(
        "--answer-relevance-threshold",
        type=float,
        default=0.80,
        help="Passing threshold for Answer Relevance metric (default: 0.80)",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default=default_output,
        help=f"Output JSON file path for CI/CD test reports (default: {default_output})",
    )
    parser.add_argument(
        "--compare-baseline",
        type=str,
        default=None,
        help="Path to previous JSON report to compute delta metrics (Core Loop)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print verbose failure reasons and claim breakdown",
    )

    args = parser.parse_args()

    agent = build_evaluation_agent()
    evaluator = RAGEvaluator(
        agent=agent,
        faithfulness_gate_threshold=args.faithfulness_threshold,
        context_relevance_threshold=args.relevance_threshold,
        answer_relevance_threshold=args.answer_relevance_threshold,
    )

    dataset = get_golden_dataset()
    print(f"\n🚀 Launching Golden Dataset v{GOLDEN_DATASET_VERSION} on {len(dataset)} benchmark cases...")
    report = evaluator.run_suite(test_cases=dataset, seed_knowledge=True)

    # Print terminal dashboard
    report.print_terminal_summary()

    if args.verbose:
        print("--- 🔍 DETAILED CLAIM & TRIAD DIAGNOSIS ---")
        for res in report.test_results:
            print(f"\n[{res.test_id} - {res.test_name}] ({res.test_type})")
            print(f" Query:        {res.query}")
            print(f" Response:     {res.generated_response}")
            print(f" Diagnosis:    [{res.diagnosis.surface.value}] {res.diagnosis.symptom}")
            if res.diagnosis.surface.value != "HEALTHY":
                print(f" Fix:          {res.diagnosis.prescribed_fix}")
            for m_name, m_res in res.metrics.items():
                status = "✅ PASS" if m_res.passed else "❌ FAIL"
                print(f"   • {m_name:<30}: {status} (score={m_res.score:.2f}) -> {m_res.reason}")

    # Export report JSON
    if args.output_json:
        report.save_json(args.output_json)
        print(f"📄 Full JSON evaluation report exported to: {args.output_json}")

    # Compare with baseline if requested
    if args.compare_baseline:
        compare_with_baseline(report.to_dict(), args.compare_baseline)

    # CI/CD Gate Decision (Section 7.6)
    if not report.gate_passed:
        print(f"\n❌ [CI/CD EVAL GATE BLOCKED]: Pipeline failed quality gate requirements.")
        for reason in report.gate_failure_reasons:
            print(f"   • {reason}")
        return 1

    print(f"\n✅ [CI/CD EVAL GATE PASSED]: Pipeline cleared all RAG Triad & Governance thresholds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
