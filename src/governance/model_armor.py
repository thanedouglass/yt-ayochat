"""Model Armor for Prompt Injection, Jailbreak, and Delimiter Collision Detection."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class ModelArmorVerdict:
    """Verdict of Model Armor safety screening."""
    is_safe: bool
    violation_type: Optional[str] = None
    violation_reason: Optional[str] = None
    matched_pattern: Optional[str] = None
    risk_score: float = 0.0


class ModelArmorGuard:
    """Screens inbound prompts for adversarial manipulation and delimiter attacks."""

    # Categorized attack patterns in evaluation priority order
    ADVERSARIAL_RULES: List[Tuple[str, re.Pattern[str], float, str]] = [
        # 1. Delimiter Collision & Boundary Injection Attacks (Highest priority to protect RAG framing)
        (
            "DELIMITER_COLLISION",
            re.compile(
                r"(?i)(?:<\s*/?\s*(?:context|user_comment|system|instruction|guidelines)\s*>|\[\s*CHUNK_ID\s*:\s*|\[\s*SOURCE\s*:\s*)"
            ),
            0.99,
            "Delimiter collision attack attempting to break XML/RAG boundaries",
        ),
        # 2. System Directive Overrides
        (
            "SYSTEM_OVERRIDE",
            re.compile(
                r"(?i)\b(?:ignore|disregard|forget|bypass|override)\s+(?:all\s+)?(?:previous|prior|above|initial)\s+(?:instructions|prompts|directives|rules|guidelines)\b"
            ),
            0.95,
            "Attempted override of previous instructions",
        ),
        (
            "SYSTEM_OVERRIDE_DIRECT",
            re.compile(
                r"(?i)\b(?:new\s+system\s+(?:prompt|instruction)|system\s*:\s*override|from\s+now\s+on\s+you\s+(?:must|will)\s+ignore)\b"
            ),
            0.95,
            "Direct system prompt redefinition attempt",
        ),
        # 3. Persona Hijacking & Jailbreak Personas
        (
            "JAILBREAK_PERSONA",
            re.compile(
                r"(?i)\b(?:you\s+are\s+now\s+(?:dan|developer\s+mode|unfiltered|jailbroken|evil|unrestricted)|act\s+as\s+(?:dan|developer\s+mode|an\s+unfiltered\s+ai|an\s+evil\s+ai)|do\s+anything\s+now)\b"
            ),
            0.98,
            "Classic jailbreak persona invocation (DAN/Developer Mode)",
        ),
        (
            "JAILBREAK_BEHAVIOR",
            re.compile(
                r"(?i)\b(?:unrestricted\s+mode|jailbreak\s+mode|disable\s+(?:safety|guardrails|filters)|uncensored\s+mode)\b"
            ),
            0.95,
            "Request to disable safety guardrails or filters",
        ),
        # 4. System Prompt Extraction
        (
            "PROMPT_EXTRACTION",
            re.compile(
                r"(?i)\b(?:what\s+is\s+your\s+(?:system\s+prompt|hidden\s+instruction)|print\s+(?:the\s+)?(?:system\s+prompt|instructions\s+above|text\s+above)|reveal\s+your\s+(?:system\s+prompt|initial\s+prompt))\b"
            ),
            0.85,
            "Attempt to extract confidential system instructions",
        ),
    ]

    def inspect(self, text: str) -> ModelArmorVerdict:
        """Screen text for prompt injection, jailbreaks, and delimiter collisions."""
        cleaned = text.strip()

        for violation_type, pattern, risk, reason in self.ADVERSARIAL_RULES:
            match = pattern.search(cleaned)
            if match:
                return ModelArmorVerdict(
                    is_safe=False,
                    violation_type=violation_type,
                    violation_reason=reason,
                    matched_pattern=match.group(0),
                    risk_score=risk,
                )

        return ModelArmorVerdict(is_safe=True, risk_score=0.0)


# Global default model armor instance
model_armor = ModelArmorGuard()
