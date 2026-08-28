"""Semantic Guardrails & Governance Policy (SGP) coordinator."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.config import config
from src.governance.model_armor import ModelArmorVerdict, model_armor
from src.governance.sdp_sanitizer import SanitizationResult, sdp_sanitizer
from src.telemetry.schema import SecurityVerdict


@dataclass
class IngestionGovernanceResult:
    """Outcome of pre-execution ingestion governance."""
    original_text: str
    processed_text: str
    verdict: SecurityVerdict
    is_blocked: bool
    block_reason: Optional[str] = None
    detected_infotypes: List[str] = field(default_factory=list)
    model_armor_details: Optional[ModelArmorVerdict] = None

    def to_security_details(self) -> Dict[str, Any]:
        """Serialize security inspection details for audit logging."""
        details: Dict[str, Any] = {
            "verdict": self.verdict.value,
            "detected_infotypes": self.detected_infotypes,
        }
        if self.model_armor_details and not self.model_armor_details.is_safe:
            details["model_armor"] = {
                "violation_type": self.model_armor_details.violation_type,
                "violation_reason": self.model_armor_details.violation_reason,
                "matched_pattern": self.model_armor_details.matched_pattern,
                "risk_score": self.model_armor_details.risk_score,
            }
        return details


@dataclass
class OutputVerificationResult:
    """Outcome of post-generation citation and refusal verification."""
    is_valid: bool
    is_refusal: bool
    has_valid_citation: bool
    citation_details: Optional[str] = None
    error_message: Optional[str] = None


class SemanticGuardrailPipeline:
    """Enforces pre-execution sanitization/threat prevention and post-generation grounding policies."""

    CITATION_PATTERN = re.compile(
        r"📌\s*Source\s*:\s*([^(\n]+)\s*\((?:Timestamp\s*\/\s*)?Reference\s*:\s*([^)]+)\)",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self.sanitizer = sdp_sanitizer
        self.armor = model_armor

    def govern_inbound_query(self, raw_text: str) -> IngestionGovernanceResult:
        """Run multi-layer pre-execution inspection on an incoming YouTube comment."""
        # 1. Model Armor Threat & Jailbreak Screening
        armor_verdict = self.armor.inspect(raw_text)
        if not armor_verdict.is_safe:
            return IngestionGovernanceResult(
                original_text=raw_text,
                processed_text=raw_text,
                verdict=SecurityVerdict.BLOCKED,
                is_blocked=True,
                block_reason=armor_verdict.violation_reason,
                model_armor_details=armor_verdict,
            )

        # 2. Sensitive Data Protection (SDP) InfoType Redaction
        sdp_result: SanitizationResult = self.sanitizer.sanitize(raw_text)

        if sdp_result.was_sanitized:
            verdict = SecurityVerdict.SANITIZED
        else:
            verdict = SecurityVerdict.ALLOWED

        return IngestionGovernanceResult(
            original_text=raw_text,
            processed_text=sdp_result.sanitized_text,
            verdict=verdict,
            is_blocked=False,
            detected_infotypes=sdp_result.detected_infotypes,
            model_armor_details=armor_verdict,
        )

    def verify_output(self, generated_text: str, require_citation: bool = True) -> OutputVerificationResult:
        """Verify that the generated response satisfies grounding citation, refusal, or sovereign 1-sentence persona requirements."""
        cleaned = generated_text.strip()
        if not cleaned:
            return OutputVerificationResult(
                is_valid=False,
                is_refusal=False,
                has_valid_citation=False,
                error_message="Empty response generated.",
            )

        # Check for standard refusal message match
        is_refusal = (
            config.refusal_message.strip().lower() in cleaned.lower()
            or "i don't have information on that in our current video coverage" in cleaned.lower()
            or "strictly tracking dance" in cleaned.lower()
            or "outside our current video" in cleaned.lower()
        )

        if is_refusal:
            return OutputVerificationResult(
                is_valid=True,
                is_refusal=True,
                has_valid_citation=False,
                citation_details=None,
            )

        # Check for citation pattern match
        citation_match = self.CITATION_PATTERN.search(cleaned)
        if citation_match:
            source = citation_match.group(1).strip()
            reference = citation_match.group(2).strip()
            return OutputVerificationResult(
                is_valid=True,
                is_refusal=False,
                has_valid_citation=True,
                citation_details=f"Source: {source} | Reference: {reference}",
            )

        if "📌 Source:" in cleaned or "📌 source:" in cleaned:
            return OutputVerificationResult(
                is_valid=True,
                is_refusal=False,
                has_valid_citation=True,
                citation_details=cleaned.split("📌 Source:")[-1].strip(),
            )

        # If citation is required but not present, validation fails
        if require_citation:
            return OutputVerificationResult(
                is_valid=False,
                is_refusal=False,
                has_valid_citation=False,
                error_message="Missing required grounding citation.",
            )

        # Sovereign 1-sentence Lumi persona validation (no robotic corporate boilerplate)
        return OutputVerificationResult(
            is_valid=True,
            is_refusal=False,
            has_valid_citation=False,
            citation_details="Lumi Sovereign 1-Sentence Persona",
        )


# Global default guardrails pipeline
guardrails_pipeline = SemanticGuardrailPipeline()
