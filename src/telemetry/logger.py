"""Structured audit logging sink with Google Cloud Logging compatibility."""

from __future__ import annotations

import json
import logging
import sys
from typing import Any, List, Optional
from pydantic import BaseModel

from src.config import config
from src.telemetry.schema import AuditLogRecord, SecurityVerdict, DispatchStatus


class GoogleCloudJsonFormatter(logging.Formatter):
    """Custom formatter producing JSON compatible with Google Cloud Logging."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "message": record.getMessage(),
            "severity": record.levelname,
            "logger": record.name,
            "timestamp": getattr(record, "timestamp", None),
        }

        # Attach Cloud Trace ID if available
        trace_id = getattr(record, "trace_id", None)
        if trace_id:
            project = getattr(record, "gcp_project", config.google_cloud_project)
            payload["logging.googleapis.com/trace"] = f"projects/{project}/traces/{trace_id}"
            payload["trace_id"] = trace_id

        # Attach structured audit payload if provided
        audit_data = getattr(record, "audit_data", None)
        if audit_data:
            if isinstance(audit_data, BaseModel):
                payload["jsonPayload"] = audit_data.model_dump()
            elif isinstance(audit_data, dict):
                payload["jsonPayload"] = audit_data

        return json.dumps(payload, default=str)


class AuditLogger:
    """Enterprise Audit & Telemetry sink for the governed RAG pipeline."""

    def __init__(
        self,
        name: str = "yt_ayochat.audit",
        use_cloud_logging: bool = False,
    ) -> None:
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()

        # Console JSON Stream Handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(GoogleCloudJsonFormatter())
        self.logger.addHandler(handler)

        # In-memory sinks for testing and evaluation runners
        self._in_memory_records: List[AuditLogRecord] = []
        self._use_cloud_logging = use_cloud_logging

        if use_cloud_logging:
            try:
                from google.cloud import logging as gcp_logging
                client = gcp_logging.Client(project=config.google_cloud_project)
                cloud_handler = client.get_default_handler()
                self.logger.addHandler(cloud_handler)
            except Exception as e:
                self.logger.warning(
                    f"Google Cloud Logging client initialization failed: {e}. Falling back to JSON stdout."
                )

    def log_audit_record(self, record: AuditLogRecord) -> None:
        """Emit a structured audit log event."""
        self._in_memory_records.append(record)

        extra = {
            "trace_id": record.trace_id,
            "gcp_project": config.google_cloud_project,
            "audit_data": record,
        }

        level = logging.INFO
        if record.security_verdict == SecurityVerdict.BLOCKED:
            level = logging.WARNING
        elif record.dispatch_status == DispatchStatus.FAILED:
            level = logging.ERROR

        self.logger.log(
            level,
            f"Audit event: trace_id={record.trace_id} verdict={record.security_verdict.value} dispatch={record.dispatch_status.value}",
            extra=extra,
        )

    def get_records(self) -> List[AuditLogRecord]:
        """Return in-memory audit records (useful for test assertions)."""
        return list(self._in_memory_records)

    def clear_records(self) -> None:
        """Clear in-memory audit records."""
        self._in_memory_records.clear()


# Global audit logger instance
audit_logger = AuditLogger()
