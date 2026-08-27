"""The Autonomous Hive (Lumi's Core Sovereign Persona Node).

Generates strictly 1-sentence, culturally resonant, unbothered community responses
grounded in lumi_persona.md framework and lumi_corpus.jsonl vector embeddings.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import config
from src.swarm.models import (
    CommentCategory,
    HiveResponse,
    PerceptionResult,
    SemioticIntentAction,
    VideoContext,
)


class AutonomousHiveNode:
    """Sovereign persona generation engine for Lumi."""

    def __init__(
        self,
        corpus_path: Optional[str] = None,
        persona_path: Optional[str] = None,
    ) -> None:
        self.corpus_path = Path(corpus_path or "lumi_corpus.jsonl")
        self.persona_path = Path(persona_path or "lumi_persona.md")
        self.corpus_entries: List[Dict[str, Any]] = []
        self._persona_text = ""
        self._load_persona_and_corpus()

    def _load_persona_and_corpus(self) -> None:
        """Load persona markdown specification and jsonl knowledge embeddings."""
        if self.persona_path.exists():
            self._persona_text = self.persona_path.read_text(encoding="utf-8")

        if self.corpus_path.exists():
            entries = []
            for line in self.corpus_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        pass
            self.corpus_entries = entries

    def generate_response(
        self,
        perception: PerceptionResult,
        video_context: Optional[VideoContext] = None,
    ) -> HiveResponse:
        """Synthesize a strictly 1-sentence sovereign response in Lumi's authentic voice."""
        start_time = time.time()

        # Retrieve nearest corpus exemplar
        matched_entry = self._find_nearest_corpus_exemplar(perception)
        lore_ids = [matched_entry["id"]] if matched_entry else []

        # Attempt Vertex AI / Gemini LLM generation if available
        raw_response = None
        try:
            raw_response = self._generate_with_gemini(perception, video_context, matched_entry)
        except Exception:
            raw_response = None

        # Fallback to direct corpus synthesis if offline/unconfigured
        if not raw_response:
            raw_response = self._synthesize_fallback(perception, matched_entry)

        # Enforce strict 1-sentence constraint & remove any corporate artifacts
        cleaned_response = self._enforce_one_sentence(raw_response)

        latency_ms = (time.time() - start_time) * 1000.0

        return HiveResponse(
            comment_id=perception.comment_id,
            response_text=cleaned_response,
            category=perception.category,
            is_refusal=(perception.category == CommentCategory.UNINDEXED_OR_OFFTOPIC),
            retrieved_lore_ids=lore_ids,
            generation_latency_ms=latency_ms,
        )

    def _find_nearest_corpus_exemplar(
        self,
        perception: PerceptionResult,
    ) -> Optional[Dict[str, Any]]:
        """Find the most semantically aligned entry in the Lumi corpus."""
        if not self.corpus_entries:
            return None

        # Filter by category first
        category_entries = [
            e for e in self.corpus_entries if e.get("category") == perception.category.value
        ]
        if not category_entries:
            category_entries = self.corpus_entries

        # Word-overlap matching for best few-shot match
        words = set(re.findall(r"\b\w+\b", perception.raw_text.lower()))
        best_entry = category_entries[0]
        max_overlap = -1

        for entry in category_entries:
            entry_words = set(re.findall(r"\b\w+\b", entry.get("input_comment", "").lower()))
            overlap = len(words.intersection(entry_words))
            if overlap > max_overlap:
                max_overlap = overlap
                best_entry = entry

        return best_entry

    def _generate_with_gemini(
        self,
        perception: PerceptionResult,
        video_context: Optional[VideoContext],
        exemplar: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        """Call Google GenAI / Vertex AI with strict persona constraints."""
        try:
            from google import genai
            from google.genai import types

            client = genai.Client()

            few_shot_prompt = ""
            if exemplar:
                few_shot_prompt = (
                    f"\nReference Exemplar:\n"
                    f"User: {exemplar.get('input_comment')}\n"
                    f"Lumi: {exemplar.get('lumi_response')}\n"
                )

            system_prompt = (
                "You are Lumi, a Gen-Z digital creator, dancer, and influencer community co-pilot.\n"
                "RULES:\n"
                "1. MAXIMUM ONE SENTENCE. Never write more than one sentence.\n"
                "2. NO corporate jargon, no 'As an AI', no 'Source:' tags, no customer service phrases.\n"
                "3. Speak with unbothered, stylish, authentic YouTube creator energy.\n"
                "4. Match the viewer's energy level.\n"
                "5. STRICTLY ZERO software or coding mentions.\n"
            )

            prompt = (
                f"Video Topic: {video_context.primary_topic if video_context else 'Dance & Lifestyle'}\n"
                f"Room Temperature: {video_context.room_temperature.value if video_context else 'CASUAL_CHILL'}\n"
                f"Comment Category: {perception.category.value}\n"
                f"Semiotic Intent: {perception.semiotic_intent}\n"
                f"Viewer Comment: \"{perception.raw_text}\"\n"
                f"{few_shot_prompt}\n"
                f"Respond as Lumi in exactly ONE punchy sentence:"
            )

            response = client.models.generate_content(
                model=config.gemini_model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7,
                    max_output_tokens=80,
                ),
            )
            return response.text.strip()
        except Exception:
            return None

    def _synthesize_fallback(
        self,
        perception: PerceptionResult,
        exemplar: Optional[Dict[str, Any]],
    ) -> str:
        """Deterministic high-quality fallback adhering strictly to persona."""
        if exemplar and exemplar.get("lumi_response"):
            return exemplar["lumi_response"]

        if perception.category == CommentCategory.HYPE:
            return "Appreciate you so much, we're just getting warmed up for the next drop!"
        elif perception.category == CommentCategory.TROLL_OR_HATER:
            return "Thanks for stopping by to boost our viewer retention metrics on your way out."
        elif perception.category == CommentCategory.FASHION_AESTHETIC:
            return "Fit is vintage oversized finds styled with thrifted accessories!"
        elif perception.category == CommentCategory.DANCE_CHOREO:
            return "Spent hours in the rehearsal studio locking down every single count for this routine."
        elif perception.category == CommentCategory.UNINDEXED_OR_OFFTOPIC:
            return "We're strictly tracking dance routines and fashion aesthetics here bestie."
        else:
            return "Appreciate you hanging out in the comment section with us today!"

    def _enforce_one_sentence(self, text: str) -> str:
        """Strictly truncate to the first complete sentence and strip corporate fluff."""
        # Strip quotes and corporate tags
        cleaned = text.strip().strip('"\'')
        cleaned = re.sub(r"^(lumi|response|reply):\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(
            r"📌\s*Source\s*:\s*[^(\n]+\s*\([^)]+\)", "", cleaned, flags=re.IGNORECASE
        ).strip()
        cleaned = re.sub(r"📌\s*Source\s*:.*?(?=[A-Z0-9]|$)", "", cleaned, flags=re.IGNORECASE).strip()

        # Truncate to first sentence if multiple sentences detected
        sentence_match = re.split(r"(?<=[.!?])\s+", cleaned)
        if sentence_match and sentence_match[0].strip():
            first_sentence = sentence_match[0].strip()
        else:
            first_sentence = cleaned

        # Ensure terminal punctuation
        if not re.search(r"[.!?]$", first_sentence):
            first_sentence += "!"

        return first_sentence


# Global Hive node instance
hive_node = AutonomousHiveNode()
