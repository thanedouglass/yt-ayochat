"""The Supervisor Node (The Orchestrator) for The Lumi Architecture.

Analyzes incoming video data (PI Blurb, description, pinned comments) to establish the
holistic bird's-eye view, set the emotional room temperature, and delegate incoming
comment threads to the Perception & Autonomous Hive nodes.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from src.swarm.models import RoomTemperature, VideoContext


class SupervisorNode:
    """Central orchestrator establishing video room context and engagement directives."""

    def __init__(self, youtube_client: Optional[Any] = None) -> None:
        self._youtube_client = youtube_client
        self._cached_contexts: Dict[str, VideoContext] = {}

    def get_video_context(
        self,
        video_id: str,
        title_override: Optional[str] = None,
        description_override: Optional[str] = None,
        pinned_comment_override: Optional[str] = None,
    ) -> VideoContext:
        """Resolve and synthesize the holistic video context."""
        if video_id in self._cached_contexts and not any(
            [title_override, description_override, pinned_comment_override]
        ):
            return self._cached_contexts[video_id]

        title = title_override or ""
        description = description_override or ""
        pinned_comment = pinned_comment_override or ""

        # Fetch live video metadata if client is available and overrides missing
        if self._youtube_client is not None and not (title and description):
            try:
                request = self._youtube_client.videos().list(
                    part="snippet",
                    id=video_id,
                )
                response = request.execute()
                items = response.get("items", [])
                if items:
                    snippet = items[0].get("snippet", {})
                    title = title or snippet.get("title", "")
                    description = description or snippet.get("description", "")
            except Exception:
                pass

        # If still empty, supply default creator video context
        if not title:
            title = f"Dance Cover & Studio Vlog [{video_id}]"
        if not description:
            description = (
                "New dance cover choreography, street style fit check, and behind-the-scenes "
                "studio rehearsal vlog! Drop your counts & favorite moments below."
            )

        # Analyze room temperature from metadata
        room_temp = self._evaluate_room_temperature(title, description, pinned_comment)
        topic, goal = self._evaluate_topic_and_goal(title, description, room_temp)

        context = VideoContext(
            video_id=video_id,
            title=title,
            description=description,
            pinned_comment=pinned_comment,
            room_temperature=room_temp,
            primary_topic=topic,
            engagement_goal=goal,
        )

        self._cached_contexts[video_id] = context
        return context

    def _evaluate_room_temperature(
        self,
        title: str,
        description: str,
        pinned_comment: str,
    ) -> RoomTemperature:
        """Compute the emotional room temperature from video metadata."""
        text = f"{title} {description} {pinned_comment}".lower()

        if any(w in text for w in ["drama", "exposed", "apology", "addressing", "clearing the air"]):
            return RoomTemperature.CONTROVERSIAL_ALERT
        elif any(w in text for w in ["choreo", "dance cover", "rehearsal", "counts", "routine", "studio"]):
            return RoomTemperature.DANCE_STUDIO
        elif any(w in text for w in ["fit check", "grwm", "styling", "ootd", "thrift", "fashion", "aesthetic"]):
            return RoomTemperature.FASHION_AESTHETIC
        elif any(w in text for w in ["viral", "world tour", "huge announcement", "let's go", "insane"]):
            return RoomTemperature.HYPER_HYPE
        else:
            return RoomTemperature.CASUAL_CHILL

    def _evaluate_topic_and_goal(
        self,
        title: str,
        description: str,
        room_temp: RoomTemperature,
    ) -> tuple[str, str]:
        """Establish overarching topic and engagement goal."""
        if room_temp == RoomTemperature.DANCE_STUDIO:
            return (
                "Choreography, Dance Technique & Music",
                "Share counts, celebrate dancer rhythm, and answer technical routine questions",
            )
        elif room_temp == RoomTemperature.FASHION_AESTHETIC:
            return (
                "Fashion, Beauty & Visual Aesthetics",
                "Break down outfits, share styling tips, and validate community aesthetic",
            )
        elif room_temp == RoomTemperature.CONTROVERSIAL_ALERT:
            return (
                "Community Moderation & Clarification",
                "Maintain unbothered composure, defuse tension, and uplift real supporters",
            )
        elif room_temp == RoomTemperature.HYPER_HYPE:
            return (
                "High-Voltage Community Celebration",
                "Match the viewer hype at 100% voltage and turn energy into loyal community",
            )
        else:
            return (
                "Creator Lifestyle & Daily Vlogs",
                "Cultivate warm, witty, authentic creator-viewer connection in 1 punchy sentence",
            )


# Global supervisor instance
supervisor_node = SupervisorNode()
