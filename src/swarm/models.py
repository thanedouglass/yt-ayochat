"""Data models and schemas for The Lumi Multi-Agent Swarm Architecture."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RoomTemperature(str, Enum):
    """Emotional and social atmosphere of the video room."""
    HYPER_HYPE = "HYPER_HYPE"
    CASUAL_CHILL = "CASUAL_CHILL"
    DANCE_STUDIO = "DANCE_STUDIO"
    FASHION_AESTHETIC = "FASHION_AESTHETIC"
    CONTROVERSIAL_ALERT = "CONTROVERSIAL_ALERT"


class CommentCategory(str, Enum):
    """Intent classification categories for inbound comments."""
    HYPE = "HYPE"
    DANCE_CHOREO = "DANCE_CHOREO"
    FASHION_AESTHETIC = "FASHION_AESTHETIC"
    BANTER = "BANTER"
    TROLL_OR_HATER = "TROLL_OR_HATER"
    UNINDEXED_OR_OFFTOPIC = "UNINDEXED_OR_OFFTOPIC"


class SemioticIntentAction(str, Enum):
    """Action directive emitted by the Perception node to the Hive."""
    MATCH_HYPE = "MATCH_HYPE"
    ANSWER_LORE = "ANSWER_LORE"
    SHARE_STYLING = "SHARE_STYLING"
    PLAYFUL_BANTER = "PLAYFUL_BANTER"
    UNBOTHERED_DEFLECT = "UNBOTHERED_DEFLECT"
    OFFTOPIC_BRUSHOFF = "OFFTOPIC_BRUSHOFF"
    DROP_SILENT = "DROP_SILENT"


class AppliedSentimentVectors(BaseModel):
    """Multi-vector 4D sentiment calibration applied during generation."""
    code_switch_alpha: float = Field(
        ...,
        description="Code-Switch Vector alpha_cs (0.0=Standard English, 1.0=Creator Vernacular)",
    )
    sovereignty_beta: str = Field(
        ...,
        description="Sovereignty Strategy beta_sf (e.g. DEFLECT, DISCLAIMER, CLAPBACK, ELEVATE, BANTER, CELEBRATE, SHARE_STYLING)",
    )
    frequency_gamma: int = Field(
        ...,
        description="Frequency Resonance gamma_fr (1=grounded reality, 5=reality crafting)",
    )
    token_economy_tau: str = Field(
        ...,
        description="Token Economy tau_max (e.g. 'Pass (1 Sentence)', 'Exception (2 Sentences)')",
    )


class SovereignReplyStructuredOutput(BaseModel):
    """Strict JSON schema enforcing structured output from the Gemini API."""
    reply_text: str = Field(
        ...,
        description="Strictly 1-sentence sovereign persona response in Lumi's authentic creator voice. No corporate boilerplate, no AI disclaimers.",
    )
    applied_vectors: AppliedSentimentVectors = Field(
        ...,
        description="4D sentiment vector calibrations applied to match the exact tone of the classification step.",
    )
    cultural_alignment_flag: bool = Field(
        ...,
        description="True if the response strictly adheres to creator authenticity, unbothered tone, and zero corporate artifacts.",
    )
    rationale: str = Field(
        default="",
        description="Brief explanation of how the semiotic intent and lore grounding guided the reply.",
    )


@dataclass
class VideoContext:
    """Holistic bird's eye view of the video established by the Supervisor Node."""
    video_id: str
    title: str = ""
    description: str = ""  # PI Blurb / overview
    pinned_comment: str = ""
    room_temperature: RoomTemperature = RoomTemperature.CASUAL_CHILL
    primary_topic: str = "Dance & Lifestyle"
    engagement_goal: str = "Cultivate authentic creator connection & celebrate energy"


@dataclass
class PerceptionResult:
    """Semiotic and emotional classification of an incoming user comment."""
    comment_id: str
    raw_text: str
    category: CommentCategory
    semiotic_intent: str
    energy_level: int  # 1 (low) to 5 (extreme hype)
    polarity: float  # -1.0 (toxic/negative) to 1.0 (positive)
    slang_detected: List[str] = field(default_factory=list)
    action: SemioticIntentAction = SemioticIntentAction.PLAYFUL_BANTER
    confidence: float = 0.95
    language: str = "en"
    council_routed: bool = False
    council_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HiveResponse:
    """Generated 1-sentence sovereign response from the Autonomous Hive."""
    comment_id: str
    response_text: str
    category: CommentCategory
    is_refusal: bool = False
    retrieved_lore_ids: List[str] = field(default_factory=list)
    generation_latency_ms: float = 0.0
    applied_vectors: Optional[Dict[str, Any]] = None
    cultural_alignment_flag: bool = True
    rationale: str = ""
    structured_payload: Optional[Dict[str, Any]] = None


@dataclass
class SwarmDecision:
    """Full end-to-end swarm routing transaction."""
    trace_id: str
    comment_id: str
    author_id: str
    video_context: VideoContext
    perception: PerceptionResult
    hive_response: HiveResponse
    final_output: str
    dispatch_ready: bool = True
    audit_metadata: Dict[str, Any] = field(default_factory=dict)
