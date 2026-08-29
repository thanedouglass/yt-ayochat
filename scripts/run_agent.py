"""Command-line runner for The Lumi Multi-Agent Swarm Framework."""

from __future__ import annotations

import argparse
import sys
from src.agent import youtube_agent
from src.config import config
from src.pipeline.listener import InboundComment
from src.swarm.hive import hive_node
from src.telemetry.logger import audit_logger


def main() -> None:
    parser = argparse.ArgumentParser(
        description="The Lumi Architecture · Autonomous Creator Multi-Agent Swarm Runner"
    )
    parser.add_argument("--query", type=str, help="Single viewer comment text to process through the swarm")
    parser.add_argument("--author", type=str, default="hype_fan_24", help="Author username or channel handle")
    parser.add_argument("--video-id", type=str, default="choreo_vlog_01", help="Target YouTube Video ID")
    parser.add_argument("--blurb", type=str, default=None, help="Video overview description / PI Blurb")
    parser.add_argument("--title", type=str, default=None, help="Video title")
    parser.add_argument("--pinned", type=str, default=None, help="Pinned comment text")
    parser.add_argument("--poll", action="store_true", help="Run YouTube Data API v3 polling loop")
    parser.add_argument("--all-channel", action="store_true", help="Run polling cycle on all videos of the authenticated channel")

    args = parser.parse_args()

    if args.query:
        print("\n" + "=" * 60)
        print("⚡ THE LUMI ARCHITECTURE · 3-NODE AGENT SWARM EXECUTION")
        print("=" * 60)
        print(f"🎬 Video ID:       {args.video_id}")
        print(f"👤 Author:         @{args.author}")
        print(f"💬 Viewer Comment: \"{args.query}\"")
        print("-" * 60)

        comment = InboundComment(
            comment_id="cli_cmt_001",
            video_id=args.video_id,
            author_name=args.author,
            author_channel_id=f"UC_{args.author}",
            text_original=args.query,
            published_at="2026-08-26T23:00:00Z",
        )

        result = youtube_agent.process_single_comment(
            comment=comment,
            video_title=args.title,
            video_description=args.blurb,
            pinned_comment=args.pinned,
        )

        decision = result.swarm_decision
        if decision:
            council_tag = " [Karpathy LLM Council · Open-Source Models]" if decision.perception.council_routed else ""
            print(f"1️⃣ SUPERVISOR NODE:")
            print(f"   • Room Temperature: {decision.video_context.room_temperature.value}")
            print(f"   • Primary Topic:    {decision.video_context.primary_topic}")
            print(f"   • Engagement Goal:  {decision.video_context.engagement_goal}")
            print(f"\n2️⃣ PERCEPTION NODE:")
            print(f"   • Language:         {decision.perception.language.upper()}{council_tag}")
            print(f"   • Category:         {decision.perception.category.value}")
            print(f"   • Semiotic Intent:  {decision.perception.semiotic_intent}")
            print(f"   • Energy Level:     {decision.perception.energy_level}/5")
            print(f"   • Polarity Score:   {decision.perception.polarity:+.2f}")
            print(f"   • Slang Detected:   {decision.perception.slang_detected or ['None']}")
            print(f"   • Action Directive: {decision.perception.action.value}")
            print(f"\n3️⃣ AUTONOMOUS HIVE (LUMI'S SOVEREIGN PERSONA):")
            print(f"   • Lore Attribution: {decision.hive_response.retrieved_lore_ids or ['Zero-Shot Swarm Synth']}")
            print(f"   • Latency:          {decision.hive_response.generation_latency_ms:.1f}ms")
            print(f"   • 1-Sentence Reply: \"{result.final_reply}\"")
        else:
            print(f"Final Reply:\n{result.final_reply or '[BLOCKED / NO REPLY]'}\n")

        print("-" * 60)
        print(f"🔒 Dispatch Status:  {result.dispatch_status.value}")
        print(f"📋 Trace ID:        {result.trace_id}")
        print("=" * 60 + "\n")
        return

    if args.poll:
        try:
            from src.pipeline.auth import get_authenticated_channel_id, get_youtube_client
            print("Authenticating with YouTube API (OAuth 2.0)...")
            client = get_youtube_client()
            channel_id = get_authenticated_channel_id(client)
            print(f"Authenticated successfully. Channel ID: {channel_id}")
        except Exception as e:
            print(f"Warning: OAuth authentication failed: {e}. Polling might run in sandbox or fail.")

        video_ids = None
        if args.video_id and not args.all_channel:
            video_ids = [args.video_id]
            print(f"Starting YouTube Data API v3 swarm polling cycle for video: {args.video_id}...")
        elif args.all_channel:
            print("Fetching all video IDs from your channel uploads...")
            video_ids = youtube_agent.listener.get_channel_video_ids()
            if video_ids:
                print(f"Found {len(video_ids)} videos. Starting polling cycle for all videos: {video_ids}...")
            else:
                print("No videos found on the channel or failed to retrieve channel uploads.")
                return
        else:
            print("Starting YouTube Data API v3 swarm polling cycle...")
        results = youtube_agent.run_polling_cycle(video_ids=video_ids)
        print(f"Completed cycle. Processed {len(results)} comments through Lumi swarm.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
