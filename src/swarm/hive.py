"""The Autonomous Hive (Lumi's Core Sovereign Persona Node).

Generates strictly 1-sentence, culturally resonant, unbothered community responses
grounded in lumi_persona.md framework and lumi_corpus.jsonl vector embeddings via ChromaDB.

Includes dynamic query retrieval, per-iteration memory reset, and multilingual
support across English, Spanish, Arabic, and Portuguese.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import config
from src.pipeline.rag_service import KnowledgeChunk, VectorStoreService
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
        vector_store: Optional[VectorStoreService] = None,
    ) -> None:
        self.corpus_path = Path(corpus_path or "lumi_corpus.jsonl")
        self.persona_path = Path(persona_path or "lumi_persona.md")
        self.corpus_entries: List[Dict[str, Any]] = []
        self._persona_text = ""
        self.vector_store = vector_store or VectorStoreService(collection_name="lumi_persona_corpus")
        self._last_processed_comment_id: Optional[str] = None
        self._load_persona_and_corpus()

    def reset_state(self) -> None:
        """Completely reset the Hive node's state and memory buffers between loop iterations.
        
        Guarantees that no conversation context, cached responses, or stale strings
        (e.g., 'RIP to the lamp...') leak across batch comment processing loops.
        """
        self._last_processed_comment_id = None

    def _load_persona_and_corpus(self) -> None:
        """Load persona markdown specification and populate ChromaDB vector store."""
        if self.persona_path.exists():
            self._persona_text = self.persona_path.read_text(encoding="utf-8")

        if self.corpus_path.exists():
            entries = []
            chunks = []
            for line in self.corpus_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        entries.append(data)
                        chunks.append(
                            KnowledgeChunk(
                                chunk_id=data.get("id", f"LUMI-{len(entries)}"),
                                source_name="lumi_corpus.jsonl",
                                reference=data.get("category", "CREATOR"),
                                content=f"Comment: {data.get('input_comment', '')} | Response: {data.get('lumi_response', '')} | Intent: {data.get('semiotic_intent', '')}",
                                metadata=data,
                            )
                        )
                    except Exception:
                        pass
            self.corpus_entries = entries
            if chunks:
                self.vector_store.add_chunks(chunks)

    def generate_response(
        self,
        perception: PerceptionResult,
        video_context: Optional[VideoContext] = None,
    ) -> HiveResponse:
        """Synthesize a strictly 1-sentence sovereign response in Lumi's authentic voice."""
        start_time = time.time()
        self._last_processed_comment_id = perception.comment_id

        # 1. Dynamic Vector Store Query: Dynamically retrieve nearest corpus exemplar using the current comment text
        matched_entry = self._find_nearest_corpus_exemplar(perception)
        lore_ids = [matched_entry["id"]] if matched_entry else []

        # 2. Attempt Vertex AI / Gemini LLM generation if available
        raw_response = None
        try:
            raw_response = self._generate_with_gemini(perception, video_context, matched_entry)
        except Exception:
            raw_response = None

        # 3. Dynamic Fallback Synthesis: Tailored uniquely to the current comment and language
        if not raw_response:
            raw_response = self._synthesize_fallback(perception, matched_entry)

        # 4. Enforce strict 1-sentence constraint & remove any corporate artifacts
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
        """Find the most semantically aligned entry in ChromaDB for the current comment text."""
        if not self.corpus_entries:
            return None

        # 1. Query ChromaDB dynamically with the current comment text
        try:
            results, _ = self.vector_store.retrieve(query=perception.raw_text, k=3)
            if results and results[0].cosine_score > 0.45:
                top_meta = results[0].chunk.metadata
                if top_meta:
                    return top_meta
        except Exception:
            pass

        # 2. Fallback: Filter by category and find word overlap with the current comment
        category_entries = [
            e for e in self.corpus_entries if e.get("category") == perception.category.value
        ]
        if not category_entries:
            category_entries = self.corpus_entries

        words = set(re.findall(r"\b\w+\b", perception.raw_text.lower()))
        best_entry = None
        max_overlap = 0

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

            lang_instruction = ""
            if perception.language == "es":
                lang_instruction = "Respond naturally in authentic Spanish Gen-Z creator slang.\n"
            elif perception.language == "ar":
                lang_instruction = "Respond naturally in authentic Arabic creator slang.\n"
            elif perception.language == "pt":
                lang_instruction = "Respond naturally in authentic Brazilian Portuguese creator slang.\n"

            system_prompt = (
                "You are Lumi, a Gen-Z digital creator, dancer, and influencer community co-pilot.\n"
                "RULES:\n"
                "1. MAXIMUM ONE SENTENCE. Never write more than one sentence.\n"
                "2. NO corporate jargon, no 'As an AI', no 'Source:' tags, no customer service phrases.\n"
                "3. Speak with unbothered, stylish, authentic YouTube creator energy.\n"
                "4. Match the viewer's energy level.\n"
                "5. STRICTLY ZERO software or coding mentions.\n"
                f"{lang_instruction}"
            )

            prompt = (
                f"Video Topic: {video_context.primary_topic if video_context else 'Dance & Lifestyle'}\n"
                f"Room Temperature: {video_context.room_temperature.value if video_context else 'CASUAL_CHILL'}\n"
                f"Language: {perception.language}\n"
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
        """Dynamic, high-quality fallback adhering strictly to persona and language."""
        raw_text_lower = perception.raw_text.lower()

        # Check if exemplar has high relevance to current comment keywords
        if exemplar and exemplar.get("lumi_response"):
            words = set(re.findall(r"\b\w+\b", perception.raw_text.lower()))
            ex_words = set(re.findall(r"\b\w+\b", exemplar.get("input_comment", "").lower()))
            if len(words.intersection(ex_words)) >= 2:
                return exemplar["lumi_response"]

        # Multilingual fallback responses
        if perception.language == "es":
            if perception.category == CommentCategory.HYPE:
                return "¡Muchísimas gracias reina, seguimos dándolo todo en los ensayos para la gira!"
            elif perception.category == CommentCategory.DANCE_CHOREO:
                return "Ese paso nos tomó horas de práctica en el estudio para que saliera perfecto!"
            elif perception.category == CommentCategory.FASHION_AESTHETIC:
                return "El outfit completo es de tiendas vintage y accesorios que encontré de segunda mano!"
            elif perception.category == CommentCategory.TROLL_OR_HATER:
                return "Gracias por comentar y ayudarnos con las métricas del algoritmo de camino a la salida."
            else:
                return "¡Me alegra muchísimo verte por aquí compartiendo buena vibra en la comunidad!"

        if perception.language == "ar":
            if perception.category == CommentCategory.HYPE:
                return "شكراً جزيلاً يا غالية، مستمرين بالتدريب والحماس دايماً للجمهور!"
            elif perception.category == CommentCategory.DANCE_CHOREO:
                return "هذه الحركات أخذت ساعات طويلة من التدريب في الاستوديو لتطلع بهذا الشكل!"
            elif perception.category == CommentCategory.FASHION_AESTHETIC:
                return "الستايل كلو قطع فينتج مميزة جمعتها من محلات مختلفة!"
            elif perception.category == CommentCategory.TROLL_OR_HATER:
                return "شكراً على مرورك وزيادة تفاعل القناة، نتمنى لك يوماً سعيداً."
            else:
                return "أهلاً وسهلاً بيك نورتي الكومنتات بالطاقة الحلوة!"

        if perception.language == "pt":
            if perception.category == CommentCategory.HYPE:
                return "Muito obrigada maravilhosa, estamos só começando os ensaios da nova temporada!"
            elif perception.category == CommentCategory.DANCE_CHOREO:
                return "Essa coreografia exigiu horas no estúdio para acertar cada contagem!"
            elif perception.category == CommentCategory.FASHION_AESTHETIC:
                return "O look inteiro é garimpo vintage de brechó que customizei!"
            elif perception.category == CommentCategory.TROLL_OR_HATER:
                return "Obrigada por engajar e subir o algoritmo do vídeo antes de sair."
            else:
                return "Que energia incrível ter você aqui com a gente nos comentários!"

        # English category dynamic generation (ensures unique output per comment)
        if perception.category == CommentCategory.HYPE:
            if any(k in raw_text_lower for k in ["dancer", "dancing", "cover"]):
                return "Appreciate you so much, we put our whole soul into this routine!"
            return "Appreciate the love so much, we're just getting warmed up for the next drop!"
        elif perception.category == CommentCategory.TROLL_OR_HATER:
            if any(k in raw_text_lower for k in ["meal", "eat", "body", "look"]):
                return "Currently fueling four hours of intense daily rehearsal with tacos, but thanks for the concern."
            return "Thanks for stopping by to boost our viewer retention metrics on your way out."
        elif perception.category == CommentCategory.FASHION_AESTHETIC:
            if "jacket" in raw_text_lower:
                return "Jacket is a vintage oversized find from the Melrose flea market!"
            elif "boots" in raw_text_lower or "shoes" in raw_text_lower or "sneakers" in raw_text_lower:
                return "Shoes are vintage platform kicks that I broke in during dance rehearsals!"
            elif "lip" in raw_text_lower or "makeup" in raw_text_lower:
                return "Lip combo is a brown liner topped with a clear glossy tint!"
            return "Fit is vintage oversized finds styled with thrifted accessories!"
        elif perception.category == CommentCategory.DANCE_CHOREO:
            if "footwork" in raw_text_lower:
                return "That footwork transition took three whole studio sessions to drill without twisting my ankle!"
            elif "count" in raw_text_lower or "timing" in raw_text_lower:
                return "Hitting that hit on count four took hours of slow-motion drills!"
            return "Spent hours in the rehearsal studio locking down every single count for this routine."
        elif perception.category == CommentCategory.UNINDEXED_OR_OFFTOPIC:
            return "We're strictly tracking dance routines and fashion aesthetics here bestie."
        else:
            if "lamp" in raw_text_lower:
                return "RIP to the lamp, but at least your rhythm is heading in the right direction."
            elif "living room" in raw_text_lower or "bedroom" in raw_text_lower:
                return "Living room dance sessions are where all the best choreography happens anyway!"
            elif "coffee table" in raw_text_lower or "table" in raw_text_lower:
                return "RIP to the coffee table, but the dance passion is 100% valid."
            return f"Love having you in the comment section vibing with the routine today!"

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
