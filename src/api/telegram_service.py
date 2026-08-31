"""Telegram Bot Service for Mobile Human-in-the-Loop (HITL) Alerting & Webhooks."""

from __future__ import annotations

import html
import logging
import re
from typing import Any, Dict, Optional, Tuple

import httpx

from src.api.models import HITLCommentRecord
from src.config import config

logger = logging.getLogger("yt_ayochat.telegram")


class TelegramService:
    """Asynchronous Telegram Bot client for mobile creator approvals and telemetry streaming."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        default_chat_id: Optional[str] = None,
    ) -> None:
        self.bot_token = bot_token or config.telegram_bot_token
        self.default_chat_id = default_chat_id or config.telegram_chat_id
        self._mock_counter = 1000

    @property
    def is_configured(self) -> bool:
        """Check if active Telegram bot credentials are provided."""
        return bool(self.bot_token and self.bot_token.strip() and self.bot_token != "mock_token")

    def _get_api_url(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self.bot_token}/{method}"

    async def send_message(
        self,
        text: str,
        chat_id: Optional[str] = None,
        reply_to_message_id: Optional[int] = None,
        parse_mode: str = "HTML",
    ) -> Optional[int]:
        """Send a formatted text message to Telegram, returning the sent message ID."""
        target_chat = chat_id or self.default_chat_id
        if not target_chat:
            target_chat = "sandbox_creator_chat"

        if not self.is_configured:
            self._mock_counter += 1
            logger.info(
                f"[TELEGRAM MOCK SEND] Chat: {target_chat} | MsgID: {self._mock_counter} | "
                f"ReplyTo: {reply_to_message_id} | Text: {text[:60]}..."
            )
            return self._mock_counter

        payload: Dict[str, Any] = {
            "chat_id": target_chat,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(self._get_api_url("sendMessage"), json=payload)
                data = res.json()
                if data.get("ok") and data.get("result"):
                    return int(data["result"]["message_id"])
                else:
                    logger.warning(f"Telegram API responded with error: {data}")
                    return None
        except Exception as e:
            logger.error(f"Failed to dispatch Telegram message: {e}")
            return None

    def format_hitl_notification_html(self, record: HITLCommentRecord) -> str:
        """Format an informative, high-contrast HTML notification for mobile Telegram clients."""
        v = record.applied_vectors or {}
        alpha = v.get("code_switch_alpha", 0.85)
        beta = v.get("sovereignty_beta", "ELEVATE")
        gamma = v.get("frequency_gamma", 3)
        tau = v.get("token_economy_tau", "Pass (1 Sentence)")

        safe_author = html.escape(record.author_name)
        safe_comment = html.escape(record.input_comment)
        safe_reply = html.escape(record.model_draft_reply)
        safe_title = html.escape(record.video_title)
        safe_category = html.escape(record.category)
        safe_intent = html.escape(record.semiotic_intent)

        msg = (
            f"⚡ <b>YT-AyoChat HITL Queue</b> · <code>{record.id[:8]}</code>\n"
            f"🎬 <b>Video:</b> {safe_title} (<code>{record.video_id}</code>)\n"
            f"👤 <b>Author:</b> {safe_author} (<code>{record.comment_id}</code>)\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📥 <b>Viewer:</b> \"<i>{safe_comment}</i>\"\n\n"
            f"🧭 <b>Perception:</b> <code>{safe_category}</code> | <code>{safe_intent}</code>\n"
            f"📊 <b>Vectors:</b> α={alpha} | β={beta} | γ={gamma}/5 | τ={tau}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 <b>Gemini 3.7 Flash Draft:</b>\n"
            f"💬 \"<b>{safe_reply}</b>\"\n\n"
            f"🎛️ <b>Reply to this message:</b>\n"
            f"• <code>a</code> ➔ <b>Approve & Dispatch</b>\n"
            f"• <code>s</code> ➔ <b>Skip Comment</b>\n"
            f"• <code>e: &lt;new text&gt;</code> ➔ <b>Edit & Calibrate</b>"
        )
        return msg

    async def send_hitl_notification(
        self,
        record: HITLCommentRecord,
        chat_id: Optional[str] = None,
    ) -> Optional[int]:
        """Format and dispatch a HITL comment draft notification to the creator's Telegram chat."""
        formatted_html = self.format_hitl_notification_html(record)
        return await self.send_message(text=formatted_html, chat_id=chat_id)

    def parse_telegram_user_input(self, text: str) -> Tuple[str, Optional[str]]:
        """Parse creator's mobile response into an actionable command and payload.
        
        Supported command syntax:
        - 'a', 'approve', '/approve', 'yes', 'y', 'ok' -> ('approve', None)
        - 's', 'skip', '/skip', 'no', 'n', 'pass' -> ('skip', None)
        - 'e: <text>', 'edit: <text>', 'e <text>', 'edit <text>', '/edit <text>' -> ('edit', '<text>')
        - 'status', '/status' -> ('status', None)
        - 'help', '/help', '?' -> ('help', None)
        """
        cleaned = text.strip()
        lower = cleaned.lower()

        # 1. Approval commands
        if lower in ("a", "approve", "/approve", "yes", "y", "ok", "lgtm", "send"):
            return ("approve", None)

        # 2. Skip commands
        if lower in ("s", "skip", "/skip", "no", "n", "pass", "drop"):
            return ("skip", None)

        # 3. Status queries
        if lower in ("status", "/status", "stats", "/stats"):
            return ("status", None)

        # 4. Help queries
        if lower in ("help", "/help", "?", "start", "/start"):
            return ("help", None)

        # 5. Edit commands
        edit_match = re.match(r"^(?:e:|edit:|/edit|e\s+|edit\s+)\s*(.+)$", cleaned, re.IGNORECASE | re.DOTALL)
        if edit_match:
            edited_body = edit_match.group(1).strip()
            return ("edit", edited_body)

        # 6. If creator types a long sentence directly in reply without prefix, treat as edit
        if len(cleaned.split()) >= 3 and not cleaned.startswith("/"):
            return ("edit", cleaned)

        return ("unknown", cleaned)


# Global default instance
telegram_service = TelegramService()
