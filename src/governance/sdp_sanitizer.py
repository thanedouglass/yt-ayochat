"""Sensitive Data Protection (SDP) sanitizer for infoType inspection and redaction."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Pattern, Tuple


@dataclass
class SanitizationResult:
    """Result of SDP InfoType inspection and sanitization."""
    original_text: str
    sanitized_text: str
    detected_infotypes: List[str] = field(default_factory=list)
    redaction_counts: Dict[str, int] = field(default_factory=dict)

    @property
    def was_sanitized(self) -> bool:
        return len(self.detected_infotypes) > 0


class SensitiveDataProtectionSanitizer:
    """Inspects and de-identifies sensitive data (InfoTypes) in incoming YouTube comments."""

    # InfoType Regex Rules (ordered by specificity)
    INFOTYPE_RULES: List[Tuple[str, Pattern[str], str]] = [
        # Specific API Keys
        (
            "API_KEY_OPENAI",
            re.compile(r"\bsk-(?:proj-|live-)?[a-zA-Z0-9_\-]{20,}\b"),
            "[REDACTED_API_KEY]",
        ),
        (
            "API_KEY_GOOGLE",
            re.compile(r"\bAIza[0-9A-Za-z\-_]{30,40}\b"),
            "[REDACTED_API_KEY]",
        ),
        (
            "API_KEY_GITHUB",
            re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{30,}\b"),
            "[REDACTED_API_KEY]",
        ),
        (
            "API_KEY_AWS",
            re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
            "[REDACTED_API_KEY]",
        ),
        # Email Addresses (RFC 5322 pattern)
        (
            "EMAIL_ADDRESS",
            re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"),
            "[REDACTED_EMAIL]",
        ),
        # Phone Numbers (International, US, paren formats)
        (
            "PHONE_NUMBER",
            re.compile(
                r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
            ),
            "[REDACTED_PHONE]",
        ),
        # Social Security Numbers (US SSN)
        (
            "US_SSN",
            re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
            "[REDACTED_SSN]",
        ),
        # Credit Card Numbers (13-19 digits formatted)
        (
            "CREDIT_CARD_NUMBER",
            re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{15,16}\b"),
            "[REDACTED_PAYMENT_INFO]",
        ),
        # IPv4 Addresses
        (
            "IP_ADDRESS",
            re.compile(
                r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
            ),
            "[REDACTED_IP]",
        ),
        # Generic Secret / Token Patterns
        (
            "API_KEY_GENERIC",
            re.compile(
                r"(?i)\b(?:api[_-]?key|secret|token|bearer)\s*(?:is|:|=)\s*['\"]?([a-zA-Z0-9_\-\.]{20,})['\"]?"
            ),
            "[REDACTED_API_KEY]",
        ),
    ]

    def sanitize(self, text: str) -> SanitizationResult:
        """Inspect and replace sensitive infoTypes with de-identified tokens."""
        sanitized = text
        detected: List[str] = []
        counts: Dict[str, int] = {}

        for infotype, pattern, replacement in self.INFOTYPE_RULES:
            if infotype == "API_KEY_GENERIC":
                # Special handling: replace matched group value while keeping prefix or substituting cleanly
                matches = pattern.findall(sanitized)
                # Filter out already redacted tokens
                valid_matches = [m for m in matches if "[REDACTED_" not in m]
                if valid_matches:
                    detected.append(infotype)
                    counts[infotype] = len(valid_matches)
                    for m in valid_matches:
                        sanitized = sanitized.replace(m, replacement)
                continue

            matches = pattern.findall(sanitized)
            if matches:
                detected.append(infotype)
                counts[infotype] = len(matches)
                sanitized = pattern.sub(replacement, sanitized)

        return SanitizationResult(
            original_text=text,
            sanitized_text=sanitized,
            detected_infotypes=detected,
            redaction_counts=counts,
        )


# Global default sanitizer instance
sdp_sanitizer = SensitiveDataProtectionSanitizer()
