"""Command-line runner for yt-ayochat Governed YouTube Comment RAG Agent."""

from __future__ import annotations

import argparse
import sys
from src.agent import youtube_agent
from src.config import config
from src.pipeline.listener import InboundComment
from src.pipeline.rag_service import KnowledgeChunk, rag_service
from src.telemetry.logger import audit_logger


def seed_sample_knowledge() -> None:
    """Seed sample video transcript chunks for demo/local evaluation."""
    chunks = [
        KnowledgeChunk(
            chunk_id="C-101",
            source_name="Building Local RAG with Ollama",
            reference="04:12",
            content="We recommend using nomic-embed-text for local embeddings because it has an 8192 token context window and runs smoothly on 8GB of RAM.",
        ),
        KnowledgeChunk(
            chunk_id="C-201",
            source_name="Docker Deployment 101",
            reference="01:30",
            content="To build your Docker container, run `docker build -t my-app .` from the project root.",
        ),
        KnowledgeChunk(
            chunk_id="C-301",
            source_name="Top 5 VS Code Extensions",
            reference="06:45",
            content="Error Lens is essential because it displays diagnostic messages directly inline on the line where the error occurs.",
        ),
        KnowledgeChunk(
            chunk_id="C-401",
            source_name="SaaS Pricing Strategy",
            reference="02:10",
            content="The Starter tier is priced at $19/month and includes 5 project seats.",
        ),
        KnowledgeChunk(
            chunk_id="C-402",
            source_name="SaaS Pricing Strategy",
            reference="05:50",
            content="All tiers come with standard 24-hour email support included at no extra cost.",
        ),
        KnowledgeChunk(
            chunk_id="C-501",
            source_name="Why We Switched to SQLite",
            reference="08:15",
            content="While most people default to PostgreSQL for web apps, we specifically advise against PostgreSQL for early prototypes because it adds unnecessary operational overhead.",
        ),
    ]
    rag_service.vector_store.add_chunks(chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description="yt-ayochat Governed RAG Execution Runner")
    parser.add_argument("--query", type=str, help="Single comment text to process through the pipeline")
    parser.add_argument("--author", type=str, default="User123", help="Author username or channel ID")
    parser.add_argument("--poll", action="store_true", help="Run YouTube Data API v3 polling loop")
    parser.add_argument("--seed", action="store_true", default=True, help="Seed sample knowledge base")

    args = parser.parse_args()

    if args.seed:
        seed_sample_knowledge()

    if args.query:
        print(f"\n--- Processing Inbound Comment ---")
        print(f"Raw Input: {args.query}")
        comment = InboundComment(
            comment_id="cli_cmt_001",
            video_id="cli_demo_video",
            author_name=args.author,
            author_channel_id=f"UC_{args.author}",
            text_original=args.query,
            published_at="2026-08-25T12:00:00Z",
        )
        result = youtube_agent.process_single_comment(comment)

        print("\n--- Pipeline Execution Result ---")
        print(f"Trace ID:          {result.trace_id}")
        print(f"Sanitized Query:   {result.sanitized_text}")
        print(f"Is Blocked:        {result.is_blocked}")
        print(f"Dispatch Status:   {result.dispatch_status.value}")
        print(f"Final Reply:\n{result.final_reply or '[BLOCKED / NO REPLY]'}\n")
        return

    if args.poll:
        print("Starting YouTube Data API v3 polling cycle...")
        results = youtube_agent.run_polling_cycle()
        print(f"Completed cycle. Processed {len(results)} comments.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
