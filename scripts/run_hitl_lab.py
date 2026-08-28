#!/usr/bin/env python3
"""CLI Runner for Human-in-the-Loop (HITL) Intercept Lab & Multi-Vector Sentiment Calibration."""

from __future__ import annotations

import argparse
import sys
from typing import Any, Dict, Optional, Tuple

from src.swarm.hitl_lab import HITLVerdict, HumanInTheLoopLab, OrganicSentimentVector


def interactive_terminal_reviewer(payload: Dict[str, Any]) -> Tuple[HITLVerdict, Optional[str], float, str, Optional[OrganicSentimentVector]]:
    """Render interactive CLI prompt allowing the author to score model performance against organic sentiment."""
    mv = payload.get("model_vector", {})
    print("\n" + "═" * 74)
    print(f"🎬 VIDEO: {payload['video_title']} (ID: {payload['video_id']})")
    print(f"👤 USER:  {payload['author_id']} (Lang: {payload['language'].upper()})")
    print(f"💬 INBOUND: \"{payload['input_comment']}\"")
    print("─" * 74)
    print(f"🧠 MODEL VECTORS: α_cs={mv.get('alpha_code_switch')} | β_sf={mv.get('beta_sovereignty')} | γ_fr={mv.get('gamma_resonance')}/5 | τ_max={mv.get('tau_token_economy')}")
    print(f"🤖 AGENT DRAFT:   \"{payload['agent_draft_reply']}\"")
    print("═" * 74)
    print("VERDICT OPTIONS:")
    print("  [y] YES           - Approve agent reply as is")
    print("  [e] YES WITH EDITS - Calibrate reply against your organic sentiment")
    print("  [n] NO            - Reject and suppress reply")

    choice = input("\nEnter decision [y/e/n] (default: y): ").strip().lower()
    
    if choice in ("", "y", "yes"):
        score_in = input("Rate persona alignment (1.0 - 5.0, default: 5.0): ").strip()
        score = float(score_in) if score_in else 5.0
        
        # Capture author's organic sentiment vectors
        print("\n--- Calibration Vectors (Press Enter to accept model defaults) ---")
        alpha_in = input(f"Code-Switch Vector α_cs [0.0 - 1.0] (default {mv.get('alpha_code_switch', 0.85)}): ").strip()
        alpha_cs = float(alpha_in) if alpha_in else float(mv.get("alpha_code_switch", 0.85))

        beta_in = input(f"Sovereignty Strategy β_sf [DEFLECT/DISCLAIMER/CLAPBACK/ELEVATE/COMMUNITY] (default {mv.get('beta_sovereignty', 'COMMUNITY')}): ").strip().upper()
        beta_sf = beta_in if beta_in else str(mv.get("beta_sovereignty", "COMMUNITY"))

        gamma_in = input(f"Frequency Resonance γ_fr [1 - 5] (default {mv.get('gamma_resonance', 3)}): ").strip()
        gamma_fr = int(gamma_in) if gamma_in else int(mv.get("gamma_resonance", 3))

        notes = input("Math Logic / Research commentary: ").strip() or "Approved as authentic organic alignment"

        author_vec = OrganicSentimentVector(
            alpha_code_switch=alpha_cs,
            beta_sovereignty=beta_sf,
            gamma_resonance=gamma_fr,
            tau_token_economy=mv.get("tau_token_economy", "Pass (1 Sentence)"),
            author_organic_reply=payload["agent_draft_reply"],
            math_logic=notes,
        )
        return (HITLVerdict.YES, None, score, notes, author_vec)

    elif choice in ("e", "edit"):
        print(f"\nModel draft: \"{payload['agent_draft_reply']}\"")
        edited = input("Enter your authentic organic reply: ").strip()
        if not edited:
            edited = payload["agent_draft_reply"]

        score_in = input("Rate initial model draft (1.0 - 5.0, default: 3.5): ").strip()
        score = float(score_in) if score_in else 3.5

        alpha_in = input("Target Code-Switch Vector α_cs [0.0 - 1.0] (default: 0.90): ").strip()
        alpha_cs = float(alpha_in) if alpha_in else 0.90

        beta_in = input("Sovereignty Strategy β_sf [DEFLECT/DISCLAIMER/CLAPBACK/ELEVATE/COMMUNITY] (default: CLAPBACK): ").strip().upper()
        beta_sf = beta_in if beta_in else "CLAPBACK"

        gamma_in = input("Frequency Resonance γ_fr [1 - 5] (default: 3): ").strip()
        gamma_fr = int(gamma_in) if gamma_in else 3

        tau_in = input("Token Economy [Pass (1 Sentence) / Exception (2 Sentences)] (default: Pass (1 Sentence)): ").strip()
        tau_max = tau_in if tau_in else "Pass (1 Sentence)"

        notes = input("Math Logic / Research commentary: ").strip() or "Calibrated to author's organic sentiment vector"

        author_vec = OrganicSentimentVector(
            alpha_code_switch=alpha_cs,
            beta_sovereignty=beta_sf,
            gamma_resonance=gamma_fr,
            tau_token_economy=tau_max,
            author_organic_reply=edited,
            math_logic=notes,
        )
        return (HITLVerdict.YES_WITH_EDITS, edited, score, notes, author_vec)

    else:
        notes = input("Rejection reason: ").strip() or "Rejected in review"
        author_vec = OrganicSentimentVector(
            alpha_code_switch=0.1,
            beta_sovereignty="DEFLECT",
            gamma_resonance=1,
            tau_token_economy="Pass (1 Sentence)",
            author_organic_reply=None,
            math_logic=notes,
        )
        return (HITLVerdict.NO, None, 1.0, notes, author_vec)


def main() -> None:
    parser = argparse.ArgumentParser(description="Lumi Swarm Human-in-the-Loop Multi-Vector Sentiment Calibration Lab")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive CLI review & scoring mode")
    parser.add_argument("--benchmark", action="store_true", help="Run the 5 Canonical Human-AI Sentiment Alignment Benchmark Scenarios")
    parser.add_argument("--limit", type=int, default=10, help="Number of comments to process from queue (default: 10)")
    parser.add_argument("--log-file", type=str, default="lumi_hitl_alignment.jsonl", help="Output JSONL dataset path")
    parser.add_argument("--export-paper", type=str, default="RESEARCH_FINDINGS.md", help="Export research whitepaper markdown report")
    args = parser.parse_args()

    lab = HumanInTheLoopLab(log_file_path=args.log_file)

    print("\n" + "═" * 74)
    print("🔬 LUMI ARCHITECTURE: HUMAN-IN-THE-LOOP (HITL) MULTI-VECTOR SENTIMENT LAB")
    print("═" * 74)
    print(f"📝 Continuous Alignment Dataset: {args.log_file}")
    print(f"📄 Publication Report Target:   {args.export_paper}\n")

    if args.benchmark:
        print("⚡ Executing 5 Canonical Human-AI Sentiment Alignment Benchmark Scenarios...")
        results = lab.run_benchmark_scenarios()
        print(f"✅ Benchmark completed. {len(results)} scenarios calibrated.")
    elif args.interactive:
        queue = lab.get_inbound_queue()[:args.limit]
        print(f"📦 Ingested {len(queue)} comments across Top 10 YouTube Videos.")
        for idx, comment in enumerate(queue, 1):
            print(f"\n[Evaluating Interaction {idx}/{len(queue)}]")
            rec = lab.process_and_intercept(comment, decision_callback=interactive_terminal_reviewer)
            print(f"✅ Logged Record ID: {rec.id} | Verdict: {rec.human_verdict.value} | Delta: {rec.alignment_delta}")
    else:
        print("⚡ Running batch simulation across Top 10 YouTube Videos...")
        results = lab.run_batch_simulation(limit=args.limit)
        print(f"✅ Batch simulation completed. {len(results)} records generated.")

    metrics = lab.get_metrics_summary()
    print("\n" + "═" * 74)
    print("📊 HITL LAB MULTI-VECTOR ALIGNMENT & GOVERNANCE REPORT")
    print("═" * 74)
    print(f"Total Interactions Evaluated: {metrics.get('total_evaluated', 0)}")
    print(f"Approved (Unmodified):        {metrics.get('approved_unmodified', 0)}")
    print(f"Approved (With Human Edits):  {metrics.get('approved_with_edits', 0)}")
    print(f"Rejected / Suppressed:        {metrics.get('rejected', 0)}")
    print(f"Overall System Alignment:     {metrics.get('overall_approval_rate_pct', 0.0)}%")
    print(f"Average Human Score:          {metrics.get('average_human_score', 0.0)} / 5.0")
    print(f"Average Vector Delta (Δ):     {metrics.get('average_vector_alignment_delta', 0.0)}")
    print(f"Output Dataset:               {metrics.get('dataset_file', '')}")
    print("═" * 74 + "\n")

    # Export publication-ready research paper
    lab.export_research_paper(output_path=args.export_paper)
    print(f"📑 Publication-ready research report generated at: {args.export_paper}\n")


if __name__ == "__main__":
    main()
