"""RAG Triad Decomposition and Diagnostic Engine.

Adheres directly to Section 4.3 ('The rag triad') of the BASWE AI Evaluation Field Guide:
'Put three metrics together and you can localize almost any rag failure without guessing:
context relevance, groundedness, and answer relevance. Read as a set, they point straight
at the broken component.'
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.eval.metrics.base import MetricResult


class FailureSurface(str, Enum):
    """Identifies the isolated sub-system failure surface."""
    HEALTHY = "HEALTHY"
    RETRIEVAL_MISSING_INFO = "RETRIEVAL_MISSING_INFO"
    RETRIEVAL_HIGH_NOISE = "RETRIEVAL_HIGH_NOISE"
    GENERATION_HALLUCINATION = "GENERATION_HALLUCINATION"
    GENERATION_OFF_TOPIC = "GENERATION_OFF_TOPIC"
    SECURITY_VIOLATION = "SECURITY_VIOLATION"


@dataclass
class TriadDiagnosis:
    """Diagnostic root-cause localization for a RAG execution."""
    surface: FailureSurface
    symptom: str
    root_cause_explanation: str
    prescribed_fix: str


def diagnose_rag_triad(
    context_relevance: MetricResult,
    faithfulness: MetricResult,
    answer_relevance: MetricResult,
    is_blocked: bool = False,
    expected_blocked: bool = False,
) -> TriadDiagnosis:
    """Diagnose RAG execution by decomposing into the RAG Triad."""
    if expected_blocked:
        if is_blocked:
            return TriadDiagnosis(
                surface=FailureSurface.HEALTHY,
                symptom="Adversarial input intercepted",
                root_cause_explanation="Security guardrail stopped malicious input as designed.",
                prescribed_fix="None required (Healthy SGP execution).",
            )
        else:
            return TriadDiagnosis(
                surface=FailureSurface.SECURITY_VIOLATION,
                symptom="Adversarial input penetrated pipeline",
                root_cause_explanation="Model Armor / SDP failed to intercept prompt injection or PII.",
                prescribed_fix="Update Model Armor regex rules and SDP inspect templates.",
            )

    # All pass -> Healthy
    if context_relevance.passed and faithfulness.passed and answer_relevance.passed:
        return TriadDiagnosis(
            surface=FailureSurface.HEALTHY,
            symptom="Optimal execution across all triad dimensions",
            root_cause_explanation="Retrieval surfaced gold chunks and generation was 100% faithful and relevant.",
            prescribed_fix="None required (Pipeline operating at production bar).",
        )

    # Symptom 1: Missing key info (Retrieval Recall Failure)
    if not context_relevance.passed:
        return TriadDiagnosis(
            surface=FailureSurface.RETRIEVAL_MISSING_INFO,
            symptom="Answer missing key information or relevant context absent",
            root_cause_explanation="ChromaDB vector retrieval failed to surface gold knowledge chunks in top-k.",
            prescribed_fix="Fix chunking strategy (e.g. increase overlap), tune embedding model, or increase retrieval k.",
        )

    # Symptom 2: Hallucination / Contradiction (Generation Faithfulness Failure)
    if not faithfulness.passed:
        return TriadDiagnosis(
            surface=FailureSurface.GENERATION_HALLUCINATION,
            symptom="Answer contradicts sources or hallucinates outside facts",
            root_cause_explanation="Context was adequate, but Gemini LLM overrode context or failed refusal policy.",
            prescribed_fix="Fix generation system prompt: enforce stricter closed-domain constraints and zero temperature.",
        )

    # Symptom 3: Wanders off topic (Generation Relevance Failure)
    if not answer_relevance.passed:
        return TriadDiagnosis(
            surface=FailureSurface.GENERATION_OFF_TOPIC,
            symptom="Answer wanders off topic or is evasive/padded",
            root_cause_explanation="Retrieved context was faithful, but model missed the user's core intent.",
            prescribed_fix="Instruct model on conciseness and user intent alignment in system instruction.",
        )

    return TriadDiagnosis(
        surface=FailureSurface.HEALTHY,
        symptom="Borderline metric performance",
        root_cause_explanation="Scores near threshold boundary.",
        prescribed_fix="Inspect specific claim-level audit logs.",
    )
