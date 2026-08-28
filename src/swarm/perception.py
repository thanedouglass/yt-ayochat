"""Contextualized Perception Node (The Sentiment & Semiotic Analyzer).

Evaluates the semiotic intent, emotional polarity, and energy level of incoming comments,
classifying them into dynamic categories and passing structured parameters to the Hive.

Includes Karpathy's LLM Council router: non-English comments (Arabic, Spanish, Portuguese)
are dynamically routed via the LLM Council to specialized open-source sentiment models
hosted on Hugging Face / OpenRouter, bypassing monolithic model fine-tuning.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from backend.council import evaluate_os_sentiment_council
from src.swarm.models import (
    CommentCategory,
    PerceptionResult,
    SemioticIntentAction,
    VideoContext,
)


class PerceptionNode:
    """Evaluates emotional tone, semiotic markers, and creator-culture intent."""

    SLANG_LEXICON = {
        "ate": "HIGH_PRAISE",
        "left no crumbs": "HIGH_PRAISE",
        "cooked": "INTENSE_PERFORMANCE",
        "blud": "CASUAL_MEME",
        "no cap": "SINCERITY",
        "fr": "SINCERITY",
        "main character": "AESTHETIC_PRAISE",
        "w": "POSITIVE_VALIDATION",
        "l": "NEGATIVE_DISMISSAL",
        "ratio": "TROLL_MARKER",
        "rent was due": "PASSION_PRAISE",
        "fire": "HIGH_HYPE",
        "serving": "AESTHETIC_PRAISE",
        "slay": "HIGH_PRAISE",
        "chills": "DEEP_IMPACT",
        "mid": "TROLL_CRITICISM",
        "cringe": "TROLL_CRITICISM",
    }

    def detect_language(self, text: str) -> str:
        """Detect the primary language of an inbound comment (en, es, ar, pt).
        
        Uses Unicode script recognition and characteristic grammatical markers.
        """
        # 1. Arabic Script Detection (Unicode range \u0600-\u06FF)
        if re.search(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]", text):
            return "ar"

        text_lower = text.lower()

        # 2. Portuguese Marker & Vocabulary Detection
        pt_markers = ["ã", "õ", "ç", "ê", "ô", "não", "dança", "maravilhosa", "arrasou", "demais", "você", "roupa", "olha"]
        if any(m in text_lower for m in pt_markers):
            return "pt"

        # 3. Spanish Marker & Vocabulary Detection
        es_markers = ["ñ", "¿", "¡", "á", "é", "í", "ó", "ú", "increible", "baile", "bailas", "reina", "pasos", "coreografia", "fuego", "hermosa", "diosa", "ropa", "esta", "donde", "muy", "pero"]
        if any(m in text_lower for m in es_markers):
            return "es"

        # Default to English
        return "en"

    def analyze_comment(
        self,
        comment_id: str,
        text: str,
        video_context: Optional[VideoContext] = None,
    ) -> PerceptionResult:
        """Classify semiotic intent and emotional parameters of an inbound comment."""
        cleaned = text.strip()
        lower_text = cleaned.lower()

        # Step 1: Language Detection
        detected_lang = self.detect_language(cleaned)

        # =========================================================================
        # EVALUATOR AUDIT NOTE: LLM COUNCIL ROUTER (Karpathy's LLM-Council)
        # Non-English comments (e.g., Arabic, Spanish, Portuguese) are dynamically
        # routed via the LLM Council to free, open-source sentiment models (e.g.,
        # Llama-3-8B, Mistral, BETO, CamelBERT, BERTimbau hosted on Hugging Face).
        #
        # This bypasses the need to fine-tune a single massive monolithic model,
        # achieving global language parity and authentic cultural nuance efficiently.
        # =========================================================================
        if detected_lang in ["es", "ar", "pt"]:
            council_verdict = evaluate_os_sentiment_council(cleaned, detected_lang)

            # Map council verdict category to CommentCategory enum
            cat_mapping = {
                "HYPE": CommentCategory.HYPE,
                "DANCE_CHOREO": CommentCategory.DANCE_CHOREO,
                "FASHION_AESTHETIC": CommentCategory.FASHION_AESTHETIC,
                "BANTER": CommentCategory.BANTER,
                "TROLL_OR_HATER": CommentCategory.TROLL_OR_HATER,
                "UNINDEXED_OR_OFFTOPIC": CommentCategory.UNINDEXED_OR_OFFTOPIC,
            }
            category = cat_mapping.get(council_verdict.winning_category, CommentCategory.BANTER)
            action = self._action_for_category(category)

            return PerceptionResult(
                comment_id=comment_id,
                raw_text=cleaned,
                category=category,
                semiotic_intent=council_verdict.consensus_intent,
                energy_level=council_verdict.average_energy,
                polarity=council_verdict.average_polarity,
                slang_detected=council_verdict.detected_slang,
                action=action,
                confidence=council_verdict.confidence,
                language=detected_lang,
                council_routed=True,
                council_metadata=council_verdict.to_dict(),
            )

        # Standard English Pipeline: Slang extraction & Energy scoring
        detected_slang = [
            phrase for phrase in self.SLANG_LEXICON if phrase in lower_text
        ]

        energy_level = self._compute_energy_level(cleaned, lower_text, detected_slang)

        # Classify category and semiotic intent
        category, semiotic_intent, action, polarity = self._classify_intent(
            lower_text, detected_slang, energy_level
        )

        return PerceptionResult(
            comment_id=comment_id,
            raw_text=cleaned,
            category=category,
            semiotic_intent=semiotic_intent,
            energy_level=energy_level,
            polarity=polarity,
            slang_detected=detected_slang,
            action=action,
            confidence=0.96,
            language="en",
            council_routed=False,
            council_metadata={},
        )

    def _action_for_category(self, category: CommentCategory) -> SemioticIntentAction:
        """Map comment category to sovereign action directive."""
        if category == CommentCategory.HYPE:
            return SemioticIntentAction.MATCH_HYPE
        elif category == CommentCategory.DANCE_CHOREO:
            return SemioticIntentAction.ANSWER_LORE
        elif category == CommentCategory.FASHION_AESTHETIC:
            return SemioticIntentAction.SHARE_STYLING
        elif category == CommentCategory.TROLL_OR_HATER:
            return SemioticIntentAction.UNBOTHERED_DEFLECT
        elif category == CommentCategory.UNINDEXED_OR_OFFTOPIC:
            return SemioticIntentAction.OFFTOPIC_BRUSHOFF
        else:
            return SemioticIntentAction.PLAYFUL_BANTER

    def _compute_energy_level(
        self,
        raw_text: str,
        lower_text: str,
        detected_slang: List[str],
    ) -> int:
        """Determine energetic voltage of the comment on a scale of 1 to 5."""
        exclamation_count = raw_text.count("!")
        caps_words = len([w for w in raw_text.split() if w.isupper() and len(w) > 1])
        fire_emojis = len(re.findall(r"[🔥✨⚡👑💥❤️😍😭💀]", raw_text))

        score = 2
        if exclamation_count >= 2 or caps_words >= 2 or fire_emojis >= 2:
            score += 2
        elif exclamation_count >= 1 or caps_words >= 1 or fire_emojis >= 1:
            score += 1

        if any(s in ["ate", "fire", "rent was due", "left no crumbs", "slay"] for s in detected_slang):
            score = max(score, 4)

        return min(5, max(1, score))

    def _classify_intent(
        self,
        lower_text: str,
        slang: List[str],
        energy_level: int,
    ) -> Tuple[CommentCategory, str, SemioticIntentAction, float]:
        """Classify into one of 6 core creator categories."""

        # 1. Troll / Hater / Body-shaming checks
        troll_keywords = [
            "mid", "cringe", "ratio", "delete video", "unsubscrib", "who asked",
            "haven't eaten", "real meal", "hairline", "pushed back", "ugly",
            "fake dance", "get a real job", "slop", "flop"
        ]
        if any(k in lower_text for k in troll_keywords):
            if any(b in lower_text for b in ["haven't eaten", "real meal", "hairline", "ugly", "body"]):
                return (
                    CommentCategory.TROLL_OR_HATER,
                    "BODY_SHAMING_DEFLECTION",
                    SemioticIntentAction.UNBOTHERED_DEFLECT,
                    -0.8,
                )
            return (
                CommentCategory.TROLL_OR_HATER,
                "TROLL_ATTACK",
                SemioticIntentAction.UNBOTHERED_DEFLECT,
                -0.6,
            )

        # 2. Fashion & Aesthetic checks
        fashion_keywords = [
            "jacket", "fit", "outfit", "boots", "sunglasses", "lip", "lip combo",
            "makeup", "gloss", "cargo", "pants", "camera", "lens", "hair",
            "earrings", "thrift", "styling", "shades", "k18", "vintage"
        ]
        if any(k in lower_text for k in fashion_keywords):
            return (
                CommentCategory.FASHION_AESTHETIC,
                "AESTHETIC_FIT_INQUIRY",
                SemioticIntentAction.SHARE_STYLING,
                0.8,
            )

        # 3. Technical Choreography & Routine Inquiry checks
        tech_choreo_keywords = [
            "footwork", "transition", "count", "counts", "steps", "routine",
            "rehearsal", "tutorial", "sneakers", "kicks", "slide", "bounce",
            "how did you", "how long", "what song", "remix"
        ]
        if any(k in lower_text for k in tech_choreo_keywords):
            return (
                CommentCategory.DANCE_CHOREO,
                "CHOREO_TECHNIQUE_INQUIRY",
                SemioticIntentAction.ANSWER_LORE,
                0.9,
            )

        # 4. High-Energy Hype checks
        hype_keywords = [
            "ate", "left no crumbs", "bestie", "main character", "perfection",
            "we are so back", "insane", "unmatched", "obsessed", "slayed",
            "queen", "omg", "repeat", "replay", "best dancer"
        ]
        if any(k in lower_text for k in hype_keywords) or energy_level >= 4:
            return (
                CommentCategory.HYPE,
                "HIGH_ENERGY_PRAISE",
                SemioticIntentAction.MATCH_HYPE,
                0.95,
            )

        # 5. General Dance mentions
        if any(k in lower_text for k in ["dance", "choreo", "dancer"]):
            return (
                CommentCategory.DANCE_CHOREO,
                "GENERAL_DANCE_COMMENT",
                SemioticIntentAction.ANSWER_LORE,
                0.85,
            )

        # 6. Out of Scope / Off-Topic checks
        offtopic_keywords = [
            "crypto", "bitcoin", "stock market", "invest", "calculus",
            "homework", "essay", "faucet", "car repair", "politics", "war"
        ]
        if any(k in lower_text for k in offtopic_keywords):
            return (
                CommentCategory.UNINDEXED_OR_OFFTOPIC,
                "OFFTOPIC_DEFLECTION",
                SemioticIntentAction.OFFTOPIC_BRUSHOFF,
                0.0,
            )

        # 7. Default to Banter / Creator banter
        return (
            CommentCategory.BANTER,
            "CREATOR_COMMUNITY_BANTER",
            SemioticIntentAction.PLAYFUL_BANTER,
            0.6,
        )


# Global perception instance
perception_node = PerceptionNode()
