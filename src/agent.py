"""End-to-end Orchestrator for Governed YouTube Comment RAG Agent."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import List, Optional

from src.config import config
from src.pipeline.dispatcher import ActionDispatcher, DispatchResult, action_dispatcher
from src.pipeline.gateway import (
    AgentGateway,
    GatewayRequest,
    GatewayResponse,
    agent_gateway,
)
from src.pipeline.listener import (
    InboundComment,
    YouTubeCommentListener,
)
from src.swarm.engine import LumiSwarmEngine, swarm_engine
from src.swarm.models import SwarmDecision
from src.telemetry.logger import audit_logger
from src.telemetry.schema import AuditLogRecord, DispatchStatus, SecurityVerdict


@dataclass
class AgentTransactionResult:
    """End-to-end outcome of processing a single YouTube comment."""
    trace_id: str
    comment_id: str
    author_id: str
    input_text: str
    sanitized_text: str
    final_reply: Optional[str]
    is_blocked: bool
    dispatch_status: DispatchStatus
    audit_record: Optional[AuditLogRecord]
    swarm_decision: Optional[SwarmDecision] = None


class GovernedYouTubeAgent:
    """Full-lifecycle Governed Multi-Agent Swarm for YouTube Comments."""

    def __init__(
        self,
        gateway: Optional[AgentGateway] = None,
        dispatcher: Optional[ActionDispatcher] = None,
        listener: Optional[YouTubeCommentListener] = None,
        swarm: Optional[LumiSwarmEngine] = None,
    ) -> None:
        self.gateway = gateway or agent_gateway
        self.dispatcher = dispatcher or action_dispatcher
        self.listener = listener or YouTubeCommentListener()
        if swarm is not None:
            self.swarm = swarm
        elif gateway is not None:
            self.swarm = None
        else:
            self.swarm = swarm_engine

    def process_single_comment(
        self,
        comment: InboundComment,
        trace_id: Optional[str] = None,
        video_title: Optional[str] = None,
        video_description: Optional[str] = None,
        pinned_comment: Optional[str] = None,
        use_swarm: Optional[bool] = None,
    ) -> AgentTransactionResult:
        """Process an inbound comment through the 3-node Lumi swarm or gateway pipeline."""
        tid = trace_id or uuid.uuid4().hex
        author_id = comment.author_channel_id or comment.author_name

        # If use_swarm is False or swarm is not configured, execute gateway RAG pipeline
        if use_swarm is False or (use_swarm is None and self.swarm is None):
            request = GatewayRequest(
                comment_id=comment.comment_id,
                author_id=author_id,
                raw_query=comment.text_original,
                video_id=comment.video_id,
                trace_id=tid,
            )
            gw_response = self.gateway.process(request)
            if gw_response.is_blocked or not gw_response.final_reply:
                self.listener.mark_processed(comment.comment_id)
                return AgentTransactionResult(
                    trace_id=tid,
                    comment_id=comment.comment_id,
                    author_id=author_id,
                    input_text=comment.text_original,
                    sanitized_text=gw_response.sanitized_query,
                    final_reply=None,
                    is_blocked=gw_response.is_blocked,
                    dispatch_status=gw_response.audit_record.dispatch_status
                    if gw_response.audit_record
                    else DispatchStatus.BLOCKED,
                    audit_record=gw_response.audit_record,
                )

            dispatch_result = self.dispatcher.dispatch_reply(
                comment_id=comment.comment_id,
                reply_text=gw_response.final_reply,
                audit_record=gw_response.audit_record,
            )
            self.listener.mark_processed(comment.comment_id)
            return AgentTransactionResult(
                trace_id=tid,
                comment_id=comment.comment_id,
                author_id=author_id,
                input_text=comment.text_original,
                sanitized_text=gw_response.sanitized_query,
                final_reply=gw_response.final_reply,
                is_blocked=False,
                dispatch_status=dispatch_result.status,
                audit_record=gw_response.audit_record,
            )

        # Check rate limiter and circuit breaker
        if not self.gateway.rate_limiter.is_allowed(author_id):
            audit_record = AuditLogRecord.create(
                trace_id=tid,
                author_id=author_id,
                comment_id=comment.comment_id,
                sanitized_query=comment.text_original,
                raw_query_length=len(comment.text_original),
                security_verdict=SecurityVerdict.BLOCKED,
                dispatch_status=DispatchStatus.BLOCKED,
                error_message="Rate limit exceeded",
            )
            audit_logger.log_audit_record(audit_record)
            self.listener.mark_processed(comment.comment_id)
            return AgentTransactionResult(
                trace_id=tid,
                comment_id=comment.comment_id,
                author_id=author_id,
                input_text=comment.text_original,
                sanitized_text=comment.text_original,
                final_reply=None,
                is_blocked=True,
                dispatch_status=DispatchStatus.BLOCKED,
                audit_record=audit_record,
            )

        # Execute 3-Node Swarm Decision (Supervisor -> Perception -> Hive)
        swarm_decision = self.swarm.process_comment_through_swarm(
            comment_id=comment.comment_id,
            author_id=author_id,
            text=comment.text_original,
            video_id=comment.video_id,
            trace_id=tid,
            video_title=video_title,
            video_description=video_description,
            pinned_comment=pinned_comment,
        )

        audit_record = AuditLogRecord.create(
            trace_id=tid,
            author_id=author_id,
            comment_id=comment.comment_id,
            sanitized_query=swarm_decision.perception.raw_text,
            raw_query_length=len(comment.text_original),
            security_verdict=SecurityVerdict.ALLOWED if swarm_decision.dispatch_ready else SecurityVerdict.BLOCKED,
            dispatch_status=DispatchStatus.SKIPPED,
        )
        audit_record.room_temperature = swarm_decision.video_context.room_temperature.value
        audit_record.comment_category = swarm_decision.perception.category.value
        audit_record.semiotic_intent = swarm_decision.perception.semiotic_intent
        audit_record.energy_level = swarm_decision.perception.energy_level

        if not swarm_decision.dispatch_ready or not swarm_decision.final_output:
            self.listener.mark_processed(comment.comment_id)
            audit_record.dispatch_status = DispatchStatus.BLOCKED
            audit_logger.log_audit_record(audit_record)
            return AgentTransactionResult(
                trace_id=tid,
                comment_id=comment.comment_id,
                author_id=author_id,
                input_text=comment.text_original,
                sanitized_text=swarm_decision.perception.raw_text,
                final_reply=None,
                is_blocked=True,
                dispatch_status=DispatchStatus.BLOCKED,
                audit_record=audit_record,
                swarm_decision=swarm_decision,
            )

        # Dispatch verified reply to YouTube thread
        dispatch_result: DispatchResult = self.dispatcher.dispatch_reply(
            comment_id=comment.comment_id,
            reply_text=swarm_decision.final_output,
            audit_record=audit_record,
        )

        self.listener.mark_processed(comment.comment_id)

        return AgentTransactionResult(
            trace_id=tid,
            comment_id=comment.comment_id,
            author_id=author_id,
            input_text=comment.text_original,
            sanitized_text=swarm_decision.perception.raw_text,
            final_reply=swarm_decision.final_output,
            is_blocked=False,
            dispatch_status=dispatch_result.status,
            audit_record=audit_record,
            swarm_decision=swarm_decision,
        )

    def reset_state(self) -> None:
        """Reset internal swarm memory/state between iterations."""
        if self.swarm and hasattr(self.swarm, "reset_state"):
            self.swarm.reset_state()

    def run_polling_cycle(self, video_ids: Optional[List[str]] = None) -> List[AgentTransactionResult]:
        """Poll all target videos for new comments and execute the governed pipeline."""
        target_ids = video_ids or config.target_video_ids
        results: List[AgentTransactionResult] = []

        for vid in target_ids:
            comments = self.listener.poll_video_comments(vid)
            for comment in comments:
                # Ensure memory/state is cleanly reset before every loop iteration
                self.reset_state()
                res = self.process_single_comment(comment)
                results.append(res)
                # Reset state after processing
                self.reset_state()

        return results


# Global default agent instance
youtube_agent = GovernedYouTubeAgent()
