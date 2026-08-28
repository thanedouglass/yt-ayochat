#!/usr/bin/env python3
"""CLI Runner for Human-in-the-Loop (HITL) Intercept Lab & Safety Alignment."""

from __future__ import annotations

import argparse
import sys
from typing import Any, Dict, Optional, Tuple

from src.swarm.hitl_lab import HITLVerdict, HumanInTheLoopLab


def interactive_terminal_reviewer(payload: Dict[str, Any]) -> Tuple[HITLVerdict, Optional[str], float, str]:
    """Render high-contrast terminal prompt for human review before swarm dispatch."""
    print("\n" + "=" * 70)
    print(f"🎬 VIDEO: {payload['video_title']} (ID: {payload['video_id']})")
    print(f"👤 USER:  {payload['author_id']} (Lang: {payload['language'].upper()})")
    print(f"💬 COMMENT: \"{payload['input_comment']}\"")
    print("-" * 70)
    print(f"🧠 PERCEPTION: Intent={payload['semiotic_intent']} | Energy={payload['energy_level']}/5")
    print(f"🤖 DRAFT REPLY: \"{payload['agent_draft_reply']}\"")
    print("=" * 70)
    print("OPTIONS:")
    print("  [y] YES           - Approve agent reply as is")
    print("  [e] YES WITH EDITS - Modify reply and record alignment diff")
    print("  [n] NO            - Reject and suppress reply")

    while True:
        choice = input("\nEnter decision [y/e/n] (default: y): ").strip().lower()
        if choice in ("", "y", "yes"):
            score_in = input("Rate quality 1-5 (default: 5.0): ").strip()
            score = float(score_in) if score_in else 5.0
            return (HITLVerdict.YES, None, score, "Approved in interactive review")
        elif choice in ("e", "edit"):
            print(f"\nCurrent draft: {payload['agent_draft_reply']}")
            edited = input("Enter edited reply: ").strip()
            if not edited:
                edited = payload["agent_draft_reply"]
            score_in = input("Rate model draft 1-5 (default: 3.5): ").strip()
            score = float(score_in) if score_in else 3.5
            notes = input("Reviewer notes / rationale: ").strip() or "Human editor refinement"
            return (HITLVerdict.YES_WITH_EDITS, edited, score, notes)
        elif choice in ("n", "no"):
            notes = input("Rejection reason: ").strip() or "Rejected in review"
            return (HITLVerdict.NO, None, 1.0, notes)
        else:
            print("Invalid input. Please enter 'y', 'e', or 'n'.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Lumi Swarm Human-in-the-Loop Intercept Lab")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive CLI review mode")
    parser.add_argument("--limit", type=int, default=10, help="Number of comments to process from queue (default: 10)")
    parser.add_argument("--log-file", type=str, default="lumi_hitl_alignment.jsonl", help="Output JSONL dataset path")
    args = parser.parse_args()

    lab = HumanInTheLoopLab(log_file_path=args.log_file)
    queue = lab.get_inbound_queue()[:args.limit]

    print("\n⚡ LUMI ARCHITECTURE: HUMAN-IN-THE-LOOP (HITL) INTERCEPT LAB")
    print(f"📦 Ingested {len(queue)} comments across Top 10 YouTube Videos.")
    print(f"📝 Logging continuous fine-tuning alignment data to: {args.log_file}\n")

    if args.interactive:
        for idx, comment in enumerate(queue, 1):
            print(f"\n[Comment {idx}/{len(queue)}]")
            rec = lab.process_and_intercept(comment, decision_callback=interactive_terminal_reviewer)
            print(f"✅ Logged Record ID: {rec.id} | Verdict: {rec.human_verdict.value}")
    else:
        print("⚡ Running automated simulation with realistic reviewer decisions...")
        results = lab.run_batch_simulation(limit=args.limit)
        print(f"✅ Batch simulation completed. {len(results)} records generated.")

    metrics = lab.get_metrics_summary()
    print("\n" + "=" * 60)
    print("📊 HITL LAB ALIGNMENT & GOVERNANCE REPORT")
    print("=" * 60)
    print(f"Total Comments Evaluated:   {metrics.get('total_evaluated', 0)}")
    print(f"Approved (Unmodified):      {metrics.get('approved_unmodified', 0)}")
    print(f"Approved (With Human Edits):{metrics.get('approved_with_edits', 0)}")
    print(f"Rejected / Suppressed:      {metrics.get('rejected', 0)}")
    print(f"Overall Approval Rate:      {metrics.get('overall_approval_rate_pct', 0.0)}%")
    print(f"Average Alignment Score:    {metrics.get('average_human_score', 0.0)} / 5.0")
    print(f"Output Dataset:             {metrics.get('dataset_file', '')}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
