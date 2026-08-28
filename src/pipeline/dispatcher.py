import json
import uuid
from dataclasses import dataclass
from typing import Any, Optional

from src.config import config
from src.governance.guardrails import guardrails_pipeline
from src.telemetry.logger import audit_logger
from src.telemetry.schema import AuditLogRecord, DispatchStatus


def log_to_synthetic_memory(category, input_comment, lumi_response, intent, energy, applied_vectors: Optional[dict] = None):
    """Appends successful swarm dispatches to a secondary learning corpus."""
    cat_str = category.value if hasattr(category, "value") else str(category)
    new_record = {
        "id": f"LUMI-SYNTH-{uuid.uuid4().hex[:8].upper()}",
        "category": cat_str,
        "input_comment": input_comment,
        "context_lore": "Autonomously generated via Swarm routing",
        "lumi_response": lumi_response,
        "semiotic_intent": intent,
        "energy_level": energy,
    }
    if applied_vectors:
        new_record["applied_vectors"] = applied_vectors

    # Append-only mode prevents file-locking crashes during live polling
    with open("lumi_synthetic_memory.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(new_record) + "\n")


@dataclass
class DispatchResult:
    """Outcome of dispatching a reply to YouTube."""
    status: DispatchStatus
    comment_id: str
    reply_id: Optional[str] = None
    http_status: Optional[int] = None
    error_message: Optional[str] = None


class ActionDispatcher:
    """Posts grounded, citation-verified replies back to YouTube comment threads."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        youtube_client: Optional[Any] = None,
        dry_run: bool = False,
    ) -> None:
        self.api_key = api_key or config.youtube_api_key
        self.dry_run = dry_run
        self._youtube_client = youtube_client
        self.guardrails = guardrails_pipeline

    def _get_client(self) -> Any:
        """Lazy-load YouTube Data API v3 client."""
        if self._youtube_client is not None:
            return self._youtube_client
        try:
            from src.pipeline.auth import get_youtube_client
            self._youtube_client = get_youtube_client()
            return self._youtube_client
        except Exception:
            if not self.api_key:
                return None
            try:
                from googleapiclient.discovery import build
                self._youtube_client = build("youtube", "v3", developerKey=self.api_key)
                return self._youtube_client
            except Exception:
                return None

    def dispatch_reply(
        self,
        comment_id: str,
        reply_text: str,
        audit_record: Optional[AuditLogRecord] = None,
        require_citation: bool = True,
    ) -> DispatchResult:
        """Validate and dispatch reply to YouTube comment thread."""
        if not reply_text:
            result = DispatchResult(
                status=DispatchStatus.SKIPPED,
                comment_id=comment_id,
                error_message="Empty reply text provided.",
            )
            self._update_telemetry(audit_record, result, reply_text=reply_text)
            return result

        # Verify citation or refusal format before dispatching
        verification = self.guardrails.verify_output(reply_text, require_citation=require_citation)
        if not verification.is_valid:
            result = DispatchResult(
                status=DispatchStatus.FAILED,
                comment_id=comment_id,
                error_message=f"Dispatch rejected: {verification.error_message}",
            )
            self._update_telemetry(audit_record, result, reply_text=reply_text)
            return result

        if self.dry_run or comment_id.startswith(("cli_", "mock_", "test_", "cmt_")):
            result = DispatchResult(
                status=DispatchStatus.SUCCESS,
                comment_id=comment_id,
                reply_id=f"dry_run_reply_{comment_id}",
                http_status=200,
            )
            self._update_telemetry(audit_record, result, reply_text=reply_text)
            return result

        client = self._get_client()
        if client is None:
            # If YouTube client is not configured, treat as simulated dispatch for offline test/sandbox
            result = DispatchResult(
                status=DispatchStatus.SUCCESS,
                comment_id=comment_id,
                reply_id=f"mock_reply_{comment_id}",
                http_status=200,
            )
            self._update_telemetry(audit_record, result, reply_text=reply_text)
            return result

        try:
            request = client.comments().insert(
                part="snippet",
                body={
                    "snippet": {
                        "parentId": comment_id,
                        "textOriginal": reply_text,
                    }
                },
            )
            response = request.execute()
            reply_id = response.get("id", f"reply_{comment_id}")
            result = DispatchResult(
                status=DispatchStatus.SUCCESS,
                comment_id=comment_id,
                reply_id=reply_id,
                http_status=200,
            )
            self._update_telemetry(audit_record, result, reply_text=reply_text)
            return result

        except Exception as e:
            result = DispatchResult(
                status=DispatchStatus.FAILED,
                comment_id=comment_id,
                http_status=500,
                error_message=str(e),
            )
            self._update_telemetry(audit_record, result, reply_text=reply_text)
            return result

    def _update_telemetry(
        self,
        audit_record: Optional[AuditLogRecord],
        result: DispatchResult,
        reply_text: str = "",
    ) -> None:
        """Update audit record and re-emit to Google Cloud Logging."""
        if audit_record is not None:
            audit_record.dispatch_status = result.status
            audit_record.http_status = result.http_status
            if result.error_message:
                audit_record.error_message = result.error_message
            audit_logger.log_audit_record(audit_record)

        # Call log_to_synthetic_memory immediately after a successful HTTP 200 dispatch
        if result.status == DispatchStatus.SUCCESS and result.http_status == 200:
            category = (
                audit_record.comment_category
                if audit_record and audit_record.comment_category
                else "BANTER"
            )
            input_comment = (
                audit_record.sanitized_query
                if audit_record and audit_record.sanitized_query
                else ""
            )
            intent = (
                audit_record.semiotic_intent
                if audit_record and audit_record.semiotic_intent
                else "CREATOR_COMMUNITY_BANTER"
            )
            energy = (
                audit_record.energy_level
                if audit_record and audit_record.energy_level is not None
                else 3
            )
            try:
                log_to_synthetic_memory(
                    category=category,
                    input_comment=input_comment,
                    lumi_response=reply_text,
                    intent=intent,
                    energy=energy,
                )
            except Exception:
                pass


# Global default dispatcher instance
action_dispatcher = ActionDispatcher()
