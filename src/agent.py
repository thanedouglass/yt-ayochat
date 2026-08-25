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
from src.telemetry.logger import audit_logger
from src.telemetry.schema import AuditLogRecord, DispatchStatus


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


class GovernedYouTubeAgent:
    """Full-lifecycle Governed RAG Agent for YouTube Comments."""

    def __init__(
        self,
        gateway: Optional[AgentGateway] = None,
        dispatcher: Optional[ActionDispatcher] = None,
        listener: Optional[YouTubeCommentListener] = None,
    ) -> None:
        self.gateway = gateway or agent_gateway
        self.dispatcher = dispatcher or action_dispatcher
        self.listener = listener or YouTubeCommentListener()

    def process_single_comment(
        self,
        comment: InboundComment,
        trace_id: Optional[str] = None,
    ) -> AgentTransactionResult:
        """Process an inbound comment through gateway, RAG inference, and dispatcher."""
        tid = trace_id or uuid.uuid4().hex

        request = GatewayRequest(
            comment_id=comment.comment_id,
            author_id=comment.author_channel_id or comment.author_name,
            raw_query=comment.text_original,
            video_id=comment.video_id,
            trace_id=tid,
        )

        gw_response: GatewayResponse = self.gateway.process(request)

        # If blocked or rate-limited, no reply is generated or dispatched
        if gw_response.is_blocked or not gw_response.final_reply:
            self.listener.mark_processed(comment.comment_id)
            return AgentTransactionResult(
                trace_id=tid,
                comment_id=comment.comment_id,
                author_id=comment.author_channel_id,
                input_text=comment.text_original,
                sanitized_text=gw_response.sanitized_query,
                final_reply=None,
                is_blocked=gw_response.is_blocked,
                dispatch_status=gw_response.audit_record.dispatch_status
                if gw_response.audit_record
                else DispatchStatus.BLOCKED,
                audit_record=gw_response.audit_record,
            )

        # Dispatch verified reply to YouTube thread
        dispatch_result: DispatchResult = self.dispatcher.dispatch_reply(
            comment_id=comment.comment_id,
            reply_text=gw_response.final_reply,
            audit_record=gw_response.audit_record,
        )

        self.listener.mark_processed(comment.comment_id)

        return AgentTransactionResult(
            trace_id=tid,
            comment_id=comment.comment_id,
            author_id=comment.author_channel_id,
            input_text=comment.text_original,
            sanitized_text=gw_response.sanitized_query,
            final_reply=gw_response.final_reply,
            is_blocked=False,
            dispatch_status=dispatch_result.status,
            audit_record=gw_response.audit_record,
        )

    def run_polling_cycle(self, video_ids: Optional[List[str]] = None) -> List[AgentTransactionResult]:
        """Poll all target videos for new comments and execute the governed pipeline."""
        target_ids = video_ids or config.target_video_ids
        results: List[AgentTransactionResult] = []

        for vid in target_ids:
            comments = self.listener.poll_video_comments(vid)
            for comment in comments:
                res = self.process_single_comment(comment)
                results.append(res)

        return results


# Global default agent instance
youtube_agent = GovernedYouTubeAgent()
