"""The Lumi Swarm Engine: Decentralized 3-Node Multi-Agent Swarm Orchestrator."""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from src.governance.guardrails import guardrails_pipeline
from src.swarm.hive import AutonomousHiveNode, hive_node
from src.swarm.models import (
    CommentCategory,
    HiveResponse,
    PerceptionResult,
    RoomTemperature,
    SwarmDecision,
    VideoContext,
)
from src.swarm.perception import PerceptionNode, perception_node
from src.swarm.supervisor import SupervisorNode, supervisor_node
from src.telemetry.logger import audit_logger


class LumiSwarmEngine:
    """End-to-end multi-agent swarm orchestrator."""

    def __init__(
        self,
        supervisor: Optional[SupervisorNode] = None,
        perception: Optional[PerceptionNode] = None,
        hive: Optional[AutonomousHiveNode] = None,
    ) -> None:
        self.supervisor = supervisor or supervisor_node
        self.perception = perception or perception_node
        self.hive = hive or hive_node
        self.guardrails = guardrails_pipeline

    def reset_state(self) -> None:
        """Reset node memory and cache buffers between batch loop iterations."""
        if hasattr(self.hive, "reset_state"):
            self.hive.reset_state()

    def process_comment_through_swarm(
        self,
        comment_id: str,
        author_id: str,
        text: str,
        video_id: str = "default_video",
        trace_id: Optional[str] = None,
        video_title: Optional[str] = None,
        video_description: Optional[str] = None,
        pinned_comment: Optional[str] = None,
    ) -> SwarmDecision:
        """Execute full 3-node swarm decision loop on an inbound comment."""
        tid = trace_id or uuid.uuid4().hex

        # 1. Supervisor Node: Establish Video Room Context
        v_ctx = self.supervisor.get_video_context(
            video_id=video_id,
            title_override=video_title,
            description_override=video_description,
            pinned_comment_override=pinned_comment,
        )

        # 2. Perception Node: Semiotic & Emotional Intent Classification
        p_res = self.perception.analyze_comment(
            comment_id=comment_id,
            text=text,
            video_context=v_ctx,
        )

        # 3. Autonomous Hive: 1-Sentence Sovereign Response Generation
        h_res = self.hive.generate_response(
            perception=p_res,
            video_context=v_ctx,
        )

        # 4. Governance & Guardrail Safety Check
        gov_result = self.guardrails.govern_inbound_query(text)
        is_safe = not gov_result.is_blocked

        final_text = h_res.response_text
        dispatch_ready = is_safe

        if not is_safe:
            final_text = "Leaving unbothered vibes in the chat today."
            dispatch_ready = False

        audit_meta = {
            "trace_id": tid,
            "room_temperature": v_ctx.room_temperature.value,
            "category": p_res.category.value,
            "semiotic_intent": p_res.semiotic_intent,
            "energy_level": p_res.energy_level,
            "polarity": p_res.polarity,
            "slang_detected": p_res.slang_detected,
            "action": p_res.action.value,
            "lore_ids": h_res.retrieved_lore_ids,
            "generation_latency_ms": h_res.generation_latency_ms,
            "applied_vectors": h_res.applied_vectors,
            "cultural_alignment_flag": h_res.cultural_alignment_flag,
        }

        # Telemetry logging before HTTP 200 payload dispatch
        audit_logger.logger.info(
            f"Lumi Swarm Decision: room_temp={v_ctx.room_temperature.value} "
            f"cat={p_res.category.value} intent={p_res.semiotic_intent} energy={p_res.energy_level}",
            extra={"jsonPayload": audit_meta},
        )

        return SwarmDecision(
            trace_id=tid,
            comment_id=comment_id,
            author_id=author_id,
            video_context=v_ctx,
            perception=p_res,
            hive_response=h_res,
            final_output=final_text,
            dispatch_ready=dispatch_ready,
            audit_metadata=audit_meta,
        )


# Global swarm engine instance
swarm_engine = LumiSwarmEngine()
