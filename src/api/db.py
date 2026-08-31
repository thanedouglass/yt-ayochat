"""Lightweight SQLite Database Layer for HITL State Management."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.api.models import HITLCommentRecord, HITLStatsResponse, HITLStatus, HITLVerdict
from src.config import config


class HITLDatabase:
    """Thread-safe SQLite database manager for asynchronous HITL state tracking."""

    def __init__(self, db_path: Optional[Path | str] = None) -> None:
        self.db_path = Path(db_path or config.hitl_db_path)
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create and configure a connection with WAL mode and JSON serialization."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def init_db(self) -> None:
        """Initialize database schema if not already present."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS hitl_comments (
                    id TEXT PRIMARY KEY,
                    comment_id TEXT NOT NULL,
                    video_id TEXT NOT NULL,
                    video_title TEXT NOT NULL,
                    author_name TEXT NOT NULL,
                    input_comment TEXT NOT NULL,
                    language TEXT NOT NULL DEFAULT 'en',
                    category TEXT NOT NULL,
                    semiotic_intent TEXT NOT NULL,
                    energy_level INTEGER NOT NULL DEFAULT 3,
                    polarity REAL NOT NULL DEFAULT 0.0,
                    model_draft_reply TEXT NOT NULL,
                    applied_vectors TEXT NOT NULL DEFAULT '{}',
                    cultural_alignment_flag INTEGER NOT NULL DEFAULT 1,
                    rationale TEXT,
                    status TEXT NOT NULL DEFAULT 'PENDING_APPROVAL',
                    telegram_message_id INTEGER,
                    human_verdict TEXT,
                    human_score REAL,
                    final_dispatched_reply TEXT,
                    diff_json TEXT,
                    alignment_delta REAL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_hitl_status ON hitl_comments (status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_hitl_video_id ON hitl_comments (video_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_hitl_telegram_msg ON hitl_comments (telegram_message_id);")
            conn.commit()

    def _row_to_record(self, row: sqlite3.Row) -> HITLCommentRecord:
        """Convert a SQLite Row into a strongly-typed HITLCommentRecord."""
        d = dict(row)
        applied_vectors = json.loads(d["applied_vectors"]) if d.get("applied_vectors") else {}
        diff_json = json.loads(d["diff_json"]) if d.get("diff_json") else None

        return HITLCommentRecord(
            id=d["id"],
            comment_id=d["comment_id"],
            video_id=d["video_id"],
            video_title=d["video_title"],
            author_name=d["author_name"],
            input_comment=d["input_comment"],
            language=d["language"],
            category=d["category"],
            semiotic_intent=d["semiotic_intent"],
            energy_level=int(d["energy_level"]),
            polarity=float(d["polarity"]),
            model_draft_reply=d["model_draft_reply"],
            applied_vectors=applied_vectors,
            cultural_alignment_flag=bool(d["cultural_alignment_flag"]),
            rationale=d["rationale"],
            status=HITLStatus(d["status"]),
            telegram_message_id=d["telegram_message_id"],
            human_verdict=HITLVerdict(d["human_verdict"]) if d.get("human_verdict") else None,
            human_score=float(d["human_score"]) if d.get("human_score") is not None else None,
            final_dispatched_reply=d["final_dispatched_reply"],
            diff_json=diff_json,
            alignment_delta=float(d["alignment_delta"]) if d.get("alignment_delta") is not None else None,
            created_at=d["created_at"],
            updated_at=d["updated_at"],
        )

    def insert_hitl_comment(self, record: HITLCommentRecord) -> HITLCommentRecord:
        """Insert or replace a comment record into the database."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO hitl_comments (
                    id, comment_id, video_id, video_title, author_name, input_comment,
                    language, category, semiotic_intent, energy_level, polarity,
                    model_draft_reply, applied_vectors, cultural_alignment_flag, rationale,
                    status, telegram_message_id, human_verdict, human_score,
                    final_dispatched_reply, diff_json, alignment_delta, created_at, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?
                );
                """,
                (
                    record.id,
                    record.comment_id,
                    record.video_id,
                    record.video_title,
                    record.author_name,
                    record.input_comment,
                    record.language,
                    record.category,
                    record.semiotic_intent,
                    record.energy_level,
                    record.polarity,
                    record.model_draft_reply,
                    json.dumps(record.applied_vectors),
                    1 if record.cultural_alignment_flag else 0,
                    record.rationale,
                    record.status.value,
                    record.telegram_message_id,
                    record.human_verdict.value if record.human_verdict else None,
                    record.human_score,
                    record.final_dispatched_reply,
                    json.dumps(record.diff_json) if record.diff_json else None,
                    record.alignment_delta,
                    record.created_at or now,
                    record.updated_at or now,
                ),
            )
            conn.commit()
        return record

    def get_hitl_comment(self, record_id: str) -> Optional[HITLCommentRecord]:
        """Fetch a record by primary key."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM hitl_comments WHERE id = ?", (record_id,)).fetchone()
            if row:
                return self._row_to_record(row)
        return None

    def get_comment_by_comment_id(self, comment_id: str) -> Optional[HITLCommentRecord]:
        """Fetch a record by YouTube comment ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM hitl_comments WHERE comment_id = ? ORDER BY created_at DESC LIMIT 1",
                (comment_id,),
            ).fetchone()
            if row:
                return self._row_to_record(row)
        return None

    def get_latest_pending_comment(self, video_id: Optional[str] = None) -> Optional[HITLCommentRecord]:
        """Retrieve the oldest pending comment (FIFO queue for creator review)."""
        with self._get_connection() as conn:
            if video_id:
                row = conn.execute(
                    "SELECT * FROM hitl_comments WHERE status = 'PENDING_APPROVAL' AND video_id = ? ORDER BY created_at ASC LIMIT 1",
                    (video_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM hitl_comments WHERE status = 'PENDING_APPROVAL' ORDER BY created_at ASC LIMIT 1"
                ).fetchone()
            if row:
                return self._row_to_record(row)
        return None

    def get_comment_by_telegram_message_id(self, message_id: int) -> Optional[HITLCommentRecord]:
        """Look up record correlated with a specific Telegram notification message ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM hitl_comments WHERE telegram_message_id = ? LIMIT 1",
                (message_id,),
            ).fetchone()
            if row:
                return self._row_to_record(row)
        return None

    def update_telegram_message_id(self, record_id: str, message_id: int) -> bool:
        """Associate a Telegram message ID with a record."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cur = conn.execute(
                "UPDATE hitl_comments SET telegram_message_id = ?, updated_at = ? WHERE id = ?",
                (message_id, now, record_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def update_hitl_comment_decision(
        self,
        record_id: str,
        status: HITLStatus,
        human_verdict: HITLVerdict,
        final_reply: Optional[str] = None,
        diff_json: Optional[Dict[str, Any]] = None,
        alignment_delta: Optional[float] = None,
        human_score: Optional[float] = 5.0,
    ) -> Optional[HITLCommentRecord]:
        """Update review verdict, edit diffs, alignment deltas, and state."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE hitl_comments SET
                    status = ?,
                    human_verdict = ?,
                    final_dispatched_reply = ?,
                    diff_json = ?,
                    alignment_delta = ?,
                    human_score = ?,
                    updated_at = ?
                WHERE id = ?;
                """,
                (
                    status.value,
                    human_verdict.value,
                    final_reply,
                    json.dumps(diff_json) if diff_json else None,
                    alignment_delta,
                    human_score,
                    now,
                    record_id,
                ),
            )
            conn.commit()
        return self.get_hitl_comment(record_id)

    def list_hitl_comments(
        self,
        status: Optional[str] = None,
        video_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[HITLCommentRecord]:
        """List records with optional status or video filters."""
        query = "SELECT * FROM hitl_comments"
        params: List[Any] = []
        clauses = []

        if status:
            clauses.append("status = ?")
            params.append(status.upper())
        if video_id:
            clauses.append("video_id = ?")
            params.append(video_id)

        if clauses:
            query += " WHERE " + " AND ".join(clauses)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
            return [self._row_to_record(r) for r in rows]

    def get_hitl_stats(self) -> HITLStatsResponse:
        """Aggregate summary counts across the state machine."""
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM hitl_comments").fetchone()[0]
            pending = conn.execute("SELECT COUNT(*) FROM hitl_comments WHERE status = 'PENDING_APPROVAL'").fetchone()[0]
            approved = conn.execute("SELECT COUNT(*) FROM hitl_comments WHERE status = 'APPROVED'").fetchone()[0]
            edited = conn.execute("SELECT COUNT(*) FROM hitl_comments WHERE status = 'EDITED'").fetchone()[0]
            skipped = conn.execute("SELECT COUNT(*) FROM hitl_comments WHERE status = 'SKIPPED'").fetchone()[0]
            dispatched = conn.execute("SELECT COUNT(*) FROM hitl_comments WHERE status = 'DISPATCHED'").fetchone()[0]

            return HITLStatsResponse(
                total_records=total,
                pending_approval=pending,
                approved=approved,
                edited=edited,
                skipped=skipped,
                dispatched=dispatched,
            )

    def clear_all_records(self) -> None:
        """Wipe database table (used in test isolation)."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM hitl_comments;")
            conn.commit()


# Global default database instance
db = HITLDatabase()
