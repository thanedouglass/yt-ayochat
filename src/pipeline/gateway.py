"""Agent Gateway with Authentication, Quota Throttling, and Circuit Breaking."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from src.config import config
from src.governance.guardrails import (
    IngestionGovernanceResult,
    OutputVerificationResult,
    guardrails_pipeline,
)
from src.pipeline.rag_service import RAGInferenceResponse, RAGService, rag_service
from src.telemetry.logger import audit_logger
from src.telemetry.schema import (
    AuditLogRecord,
    DispatchStatus,
    GenerationMetrics,
    SecurityVerdict,
    VectorRetrievalMetrics,
)


class CircuitBreakerState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """Circuit Breaker to protect upstream Vertex AI & Chroma services from cascading failure."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_sec: float = 30.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: float = 0.0

    def can_execute(self) -> bool:
        """Check if request is allowed through circuit breaker."""
        now = time.time()
        if self.state == CircuitBreakerState.OPEN:
            if now - self.last_failure_time > self.recovery_timeout_sec:
                self.state = CircuitBreakerState.HALF_OPEN
                return True
            return False
        return True

    def record_success(self) -> None:
        """Record successful execution and reset breaker."""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED

    def record_failure(self) -> None:
        """Record upstream execution failure and trip breaker if threshold exceeded."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN


class SlidingWindowRateLimiter:
    """Sliding-window rate limiter per author and global traffic."""

    def __init__(self, max_requests_per_minute: int = 60) -> None:
        self.max_requests_per_minute = max_requests_per_minute
        self._user_timestamps: Dict[str, List[float]] = {}
        self._global_timestamps: List[float] = []

    def is_allowed(self, author_id: str) -> bool:
        """Check if an author request satisfies rate limits."""
        now = time.time()
        window_start = now - 60.0

        # Clean global timestamps
        self._global_timestamps = [t for t in self._global_timestamps if t > window_start]
        if len(self._global_timestamps) >= self.max_requests_per_minute:
            return False

        # Clean user timestamps
        user_ts = self._user_timestamps.get(author_id, [])
        user_ts = [t for t in user_ts if t > window_start]
        self._user_timestamps[author_id] = user_ts

        # Per user limit (max 10 requests / minute / author)
        if len(user_ts) >= 10:
            return False

        # Record new timestamp
        self._global_timestamps.append(now)
        self._user_timestamps[author_id].append(now)
        return True


@dataclass
class GatewayRequest:
    """Inbound request passed to the Agent Gateway."""
    comment_id: str
    author_id: str
    raw_query: str
    video_id: str
    trace_id: Optional[str] = None
    auth_token: Optional[str] = None


@dataclass
class GatewayResponse:
    """Result returned by the Agent Gateway."""
    trace_id: str
    comment_id: str
    author_id: str
    sanitized_query: str
    final_reply: Optional[str]
    security_verdict: SecurityVerdict
    is_blocked: bool
    is_rate_limited: bool = False
    is_circuit_broken: bool = False
    audit_record: Optional[AuditLogRecord] = None
    error_message: Optional[str] = None


class AgentGateway:
    """Enterprise Gateway mediating ingress, governance, RAG execution, and telemetry."""

    def __init__(
        self,
        rag_svc: Optional[RAGService] = None,
        rate_limiter: Optional[SlidingWindowRateLimiter] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        self.rag_svc = rag_svc or rag_service
        self.rate_limiter = rate_limiter or SlidingWindowRateLimiter(
            max_requests_per_minute=config.rate_limit_max_requests_per_minute
        )
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            failure_threshold=config.circuit_breaker_failure_threshold,
            recovery_timeout_sec=config.circuit_breaker_recovery_timeout_sec,
        )
        self.guardrails = guardrails_pipeline

    def process(self, request: GatewayRequest) -> GatewayResponse:
        """Process inbound comment through security screening, rate limits, and RAG."""
        trace_id = request.trace_id or uuid.uuid4().hex
        raw_len = len(request.raw_query)

        # 1. Rate Limiting Check
        if not self.rate_limiter.is_allowed(request.author_id):
            audit_rec = AuditLogRecord.create(
                trace_id=trace_id,
                author_id=request.author_id,
                comment_id=request.comment_id,
                sanitized_query=request.raw_query,
                raw_query_length=raw_len,
                security_verdict=SecurityVerdict.BLOCKED,
                security_details={"reason": "RATE_LIMIT_EXCEEDED"},
                dispatch_status=DispatchStatus.SKIPPED,
                error_message="Rate limit exceeded",
            )
            audit_logger.log_audit_record(audit_rec)
            return GatewayResponse(
                trace_id=trace_id,
                comment_id=request.comment_id,
                author_id=request.author_id,
                sanitized_query=request.raw_query,
                final_reply=None,
                security_verdict=SecurityVerdict.BLOCKED,
                is_blocked=True,
                is_rate_limited=True,
                audit_record=audit_rec,
                error_message="Rate limit exceeded",
            )

        # 2. Semantic Guardrails & Policy (SGP) Pre-Execution Screening
        gov_result: IngestionGovernanceResult = self.guardrails.govern_inbound_query(
            request.raw_query
        )

        if gov_result.is_blocked:
            audit_rec = AuditLogRecord.create(
                trace_id=trace_id,
                author_id=request.author_id,
                comment_id=request.comment_id,
                sanitized_query=gov_result.processed_text,
                raw_query_length=raw_len,
                security_verdict=SecurityVerdict.BLOCKED,
                security_details=gov_result.to_security_details(),
                dispatch_status=DispatchStatus.BLOCKED,
                error_message=gov_result.block_reason,
            )
            audit_logger.log_audit_record(audit_rec)
            return GatewayResponse(
                trace_id=trace_id,
                comment_id=request.comment_id,
                author_id=request.author_id,
                sanitized_query=gov_result.processed_text,
                final_reply=None,
                security_verdict=SecurityVerdict.BLOCKED,
                is_blocked=True,
                audit_record=audit_rec,
                error_message=gov_result.block_reason,
            )

        # 3. Circuit Breaker Check
        if not self.circuit_breaker.can_execute():
            audit_rec = AuditLogRecord.create(
                trace_id=trace_id,
                author_id=request.author_id,
                comment_id=request.comment_id,
                sanitized_query=gov_result.processed_text,
                raw_query_length=raw_len,
                security_verdict=gov_result.verdict,
                security_details=gov_result.to_security_details(),
                dispatch_status=DispatchStatus.FAILED,
                error_message="Circuit breaker is OPEN",
            )
            audit_logger.log_audit_record(audit_rec)
            return GatewayResponse(
                trace_id=trace_id,
                comment_id=request.comment_id,
                author_id=request.author_id,
                sanitized_query=gov_result.processed_text,
                final_reply=None,
                security_verdict=gov_result.verdict,
                is_blocked=False,
                is_circuit_broken=True,
                audit_record=audit_rec,
                error_message="Circuit breaker is OPEN",
            )

        # 4. RAG Retrieval & Generation Execution
        try:
            rag_response: RAGInferenceResponse = self.rag_svc.process_query(
                gov_result.processed_text, k=config.retrieval_k
            )
            self.circuit_breaker.record_success()

            # 5. Output Grounding & Refusal Verification
            verification: OutputVerificationResult = self.guardrails.verify_output(
                rag_response.response_text
            )

            # If response is neither refusal nor valid citation, default to refusal for safety
            final_reply = rag_response.response_text
            if not verification.is_valid:
                final_reply = config.refusal_message

            audit_rec = AuditLogRecord.create(
                trace_id=trace_id,
                author_id=request.author_id,
                comment_id=request.comment_id,
                sanitized_query=gov_result.processed_text,
                raw_query_length=raw_len,
                security_verdict=gov_result.verdict,
                security_details=gov_result.to_security_details(),
                vector_retrieval_metrics=rag_response.retrieval_metrics,
                generation_metrics=rag_response.generation_metrics,
                dispatch_status=DispatchStatus.SKIPPED,  # Pending dispatcher
            )
            audit_logger.log_audit_record(audit_rec)

            return GatewayResponse(
                trace_id=trace_id,
                comment_id=request.comment_id,
                author_id=request.author_id,
                sanitized_query=gov_result.processed_text,
                final_reply=final_reply,
                security_verdict=gov_result.verdict,
                is_blocked=False,
                audit_record=audit_rec,
            )

        except Exception as e:
            self.circuit_breaker.record_failure()
            audit_rec = AuditLogRecord.create(
                trace_id=trace_id,
                author_id=request.author_id,
                comment_id=request.comment_id,
                sanitized_query=gov_result.processed_text,
                raw_query_length=raw_len,
                security_verdict=gov_result.verdict,
                security_details=gov_result.to_security_details(),
                dispatch_status=DispatchStatus.FAILED,
                error_message=str(e),
            )
            audit_logger.log_audit_record(audit_rec)
            return GatewayResponse(
                trace_id=trace_id,
                comment_id=request.comment_id,
                author_id=request.author_id,
                sanitized_query=gov_result.processed_text,
                final_reply=None,
                security_verdict=gov_result.verdict,
                is_blocked=False,
                audit_record=audit_rec,
                error_message=str(e),
            )


# Global default gateway instance
agent_gateway = AgentGateway()
