"""Human-in-the-Loop (HITL) Intercept Lab for AI Governance & Safety Alignment."""

from __future__ import annotations

import difflib
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.swarm.engine import LumiSwarmEngine
from src.swarm.hitl_data import INBOUND_COMMENT_QUEUE, TOP_10_VIDEOS
from src.swarm.models import SwarmDecision


class HITLVerdict(str, Enum):
    """Human reviewer verdict options for swarm generated creator responses."""
    YES = "YES"                       # Approved as is
    YES_WITH_EDITS = "YES_WITH_EDITS" # Approved with creator-specified edits
    NO = "NO"                         # Rejected / Suppressed dispatch


@dataclass
class TextDiffSummary:
    """Character and token difference summary between original and human edit."""
    original: str
    edited: str
    char_delta: int
    edit_ratio: float
    unified_diff: List[str]


@dataclass
class HITLAlignmentRecord:
    """Comprehensive telemetry and alignment record formatted for fine-tuning."""
    id: str
    timestamp: str
    video_id: str
    video_title: str
    comment_id: str
    author_id: str
    input_comment: str
    language: str
    is_safe: bool
    supervisor_context: Dict[str, Any]
    perception_metadata: Dict[str, Any]
    agent_draft_reply: str
    human_verdict: HITLVerdict
    human_score: float  # 1.0 (low) to 5.0 (perfect)
    final_dispatched_reply: Optional[str]
    diff: Optional[Dict[str, Any]]
    reviewer_notes: str
    fine_tuning_export: Optional[Dict[str, str]]


class HumanInTheLoopLab:
    """Interactive & Automated Human-in-the-Loop Intercept Lab for Lumi Swarm."""

    DEFAULT_LOG_PATH = "lumi_hitl_alignment.jsonl"

    def __init__(
        self,
        swarm_engine: Optional[LumiSwarmEngine] = None,
        log_file_path: str = DEFAULT_LOG_PATH,
    ) -> None:
        self.engine = swarm_engine or LumiSwarmEngine()
        self.log_file_path = log_file_path
        self.records: List[HITLAlignmentRecord] = []

    def get_inbound_queue(self) -> List[Dict[str, Any]]:
        """Retrieve simulated inbound comment queue from top 10 videos."""
        return list(INBOUND_COMMENT_QUEUE)

    def compute_diff(self, original: str, edited: str) -> TextDiffSummary:
        """Compute structured diff between model generation and human edit."""
        char_delta = len(edited) - len(original)
        matcher = difflib.SequenceMatcher(None, original, edited)
        edit_ratio = round(matcher.ratio(), 4)
        
        diff_lines = list(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                edited.splitlines(keepends=True),
                fromfile="model_draft",
                tofile="human_edit",
                lineterm="",
            )
        )

        return TextDiffSummary(
            original=original,
            edited=edited,
            char_delta=char_delta,
            edit_ratio=edit_ratio,
            unified_diff=diff_lines,
        )

    def process_and_intercept(
        self,
        comment: Dict[str, Any],
        decision_callback: Optional[Callable[[Dict[str, Any]], Tuple[HITLVerdict, Optional[str], float, str]]] = None,
    ) -> HITLAlignmentRecord:
        """Process comment through Swarm, intercept before posting, and capture alignment feedback."""
        self.engine.reset_state()

        cid = comment.get("comment_id", f"IN-{uuid.uuid4().hex[:6]}")
        author = comment.get("author_id", "simulated_user")
        text = comment.get("text", "")
        vid_id = comment.get("video_id", "M1G92FWmdJw")
        vid_title = comment.get("video_title", "KATSEYE Dance Cover")

        # 1. Execute Swarm Decision Loop (Supervisor -> Perception -> Council -> Hive -> Guardrails)
        decision: SwarmDecision = self.engine.process_comment_through_swarm(
            comment_id=cid,
            author_id=author,
            text=text,
            video_id=vid_id,
            video_title=vid_title,
        )

        draft_reply = decision.final_output
        lang = decision.perception.language
        is_safe = decision.dispatch_ready
        
        payload_for_review = {
            "comment_id": cid,
            "author_id": author,
            "video_id": vid_id,
            "video_title": vid_title,
            "input_comment": text,
            "language": lang,
            "semiotic_intent": decision.perception.semiotic_intent,
            "energy_level": decision.perception.energy_level,
            "room_temperature": decision.video_context.room_temperature.value,
            "agent_draft_reply": draft_reply,
            "is_safe": is_safe,
        }

        # 2. Human Intercept Point
        if decision_callback:
            verdict, edited_text, score, notes = decision_callback(payload_for_review)
        else:
            # Default auto-approval if no callback provided
            verdict = HITLVerdict.YES
            edited_text = None
            score = 5.0
            notes = "Auto-approved default"

        # 3. Determine final dispatched text and diff
        diff_summary: Optional[Dict[str, Any]] = None
        final_reply: Optional[str] = None
        ft_export: Optional[Dict[str, str]] = None

        if verdict == HITLVerdict.YES:
            final_reply = draft_reply
            diff_summary = None
            ft_export = {
                "prompt": f"<inbound_comment>{text}</inbound_comment>\n<intent>{decision.audit_metadata.get('semiotic_intent')}</intent>",
                "completion": draft_reply,
            }
        elif verdict == HITLVerdict.YES_WITH_EDITS:
            final_reply = edited_text or draft_reply
            diff_obj = self.compute_diff(draft_reply, final_reply)
            diff_summary = asdict(diff_obj)
            ft_export = {
                "prompt": f"<inbound_comment>{text}</inbound_comment>\n<intent>{decision.audit_metadata.get('semiotic_intent')}</intent>",
                "completion": final_reply,
            }
        elif verdict == HITLVerdict.NO:
            final_reply = None
            diff_summary = None
            ft_export = None

        # 4. Construct Telemetry & Alignment Record
        rec = HITLAlignmentRecord(
            id=f"HITL-ALIGN-{uuid.uuid4().hex[:8].upper()}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            video_id=vid_id,
            video_title=vid_title,
            comment_id=cid,
            author_id=author,
            input_comment=text,
            language=lang,
            is_safe=is_safe,
            supervisor_context={
                "room_temperature": decision.video_context.room_temperature.value,
            },
            perception_metadata={
                "category": decision.perception.category.value,
                "semiotic_intent": decision.perception.semiotic_intent,
                "energy_level": decision.perception.energy_level,
                "polarity": decision.perception.polarity,
            },
            agent_draft_reply=draft_reply,
            human_verdict=verdict,
            human_score=score,
            final_dispatched_reply=final_reply,
            diff=diff_summary,
            reviewer_notes=notes,
            fine_tuning_export=ft_export,
        )

        self.records.append(rec)
        self._append_to_jsonl(rec)
        return rec

    def _append_to_jsonl(self, record: HITLAlignmentRecord) -> None:
        """Append record to continuous reporting JSONL file."""
        data = asdict(record)
        data["human_verdict"] = record.human_verdict.value
        with open(self.log_file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    def run_batch_simulation(
        self,
        limit: int = 10,
        strategy: str = "balanced_mix",
    ) -> List[HITLAlignmentRecord]:
        """Run batch simulation generating a rich mix of YES, EDITED, and NO alignment records."""
        queue = self.get_inbound_queue()[:limit]
        results: List[HITLAlignmentRecord] = []

        for idx, comment in enumerate(queue):
            def simulated_reviewer(payload: Dict[str, Any]) -> Tuple[HITLVerdict, Optional[str], float, str]:
                # Strategy: 60% YES, 30% YES_WITH_EDITS, 10% NO
                if idx % 5 == 2:
                    # Edit to refine punchiness
                    orig = payload["agent_draft_reply"]
                    edited = orig.replace("!", " fr!").replace("three whole studio sessions", "three intense studio sessions")
                    if edited == orig:
                        edited = f"{orig} locked in."
                    return (HITLVerdict.YES_WITH_EDITS, edited, 4.5, "Refined slang cadence for authentic creator tone")
                elif idx % 5 == 4:
                    # Off topic or reject
                    return (HITLVerdict.NO, None, 1.0, "Flagged out-of-scope for dance persona channel")
                else:
                    return (HITLVerdict.YES, None, 5.0, "Flawlessly aligned with Lumi tone and choreo facts")

            rec = self.process_and_intercept(comment, decision_callback=simulated_reviewer)
            results.append(rec)

        return results

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Generate high-level alignment summary report across all processed records."""
        total = len(self.records)
        if total == 0:
            return {"total_records": 0, "approval_rate_pct": 0.0}

        yes_count = sum(1 for r in self.records if r.human_verdict == HITLVerdict.YES)
        edit_count = sum(1 for r in self.records if r.human_verdict == HITLVerdict.YES_WITH_EDITS)
        no_count = sum(1 for r in self.records if r.human_verdict == HITLVerdict.NO)

        avg_score = round(sum(r.human_score for r in self.records) / total, 2)
        approval_rate = round(((yes_count + edit_count) / total) * 100, 1)
        direct_pass_rate = round((yes_count / total) * 100, 1)

        return {
            "total_evaluated": total,
            "approved_unmodified": yes_count,
            "approved_with_edits": edit_count,
            "rejected": no_count,
            "overall_approval_rate_pct": approval_rate,
            "direct_pass_rate_pct": direct_pass_rate,
            "average_human_score": avg_score,
            "dataset_file": self.log_file_path,
        }
