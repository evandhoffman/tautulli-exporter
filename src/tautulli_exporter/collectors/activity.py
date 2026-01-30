"""Activity collector for real-time streaming metrics."""

import logging

from ..metrics import (
    BANDWIDTH,
    STREAM_DURATION,
    STREAM_INFO,
    STREAM_PROGRESS,
    STREAMS_BY_TYPE,
    STREAMS_TOTAL,
)
from ..tautulli_client import TautulliClient
from .base import BaseCollector

logger = logging.getLogger(__name__)


class ActivityCollector(BaseCollector):
    """Collector for real-time streaming activity metrics."""

    name = "activity"

    def __init__(self, client: TautulliClient):
        """Initialize the activity collector."""
        super().__init__(client)
        self._previous_sessions: set[str] = set()

    async def collect(self) -> None:
        """Collect streaming activity metrics."""
        data = await self.client.get_activity()

        # Update stream counts
        stream_count = int(data.get("stream_count", 0))
        STREAMS_TOTAL.set(stream_count)

        # Stream counts by type
        STREAMS_BY_TYPE.labels(type="direct_play").set(
            int(data.get("stream_count_direct_play", 0))
        )
        STREAMS_BY_TYPE.labels(type="direct_stream").set(
            int(data.get("stream_count_direct_stream", 0))
        )
        STREAMS_BY_TYPE.labels(type="transcode").set(
            int(data.get("stream_count_transcode", 0))
        )

        # Bandwidth metrics
        BANDWIDTH.labels(location="total").set(float(data.get("total_bandwidth", 0)))
        BANDWIDTH.labels(location="wan").set(float(data.get("wan_bandwidth", 0)))
        BANDWIDTH.labels(location="lan").set(float(data.get("lan_bandwidth", 0)))

        # Process individual sessions
        await self._process_sessions(data.get("sessions", []))

    async def _process_sessions(self, sessions: list[dict]) -> None:
        """Process individual streaming sessions.

        Args:
            sessions: List of session dictionaries from the API.
        """
        current_sessions: set[str] = set()

        # Clear previous stream info metrics
        # This is needed because sessions can end between scrapes
        STREAM_INFO.clear()
        STREAM_PROGRESS.clear()
        STREAM_DURATION.clear()

        for session in sessions:
            session_key = str(session.get("session_key", ""))
            current_sessions.add(session_key)

            # Extract session details
            user = session.get("friendly_name") or session.get("username", "unknown")
            media_type = session.get("media_type", "unknown")
            title = self._get_title(session)
            state = session.get("state", "unknown")
            transcode_decision = self._normalize_transcode_decision(
                session.get("transcode_decision", "unknown")
            )
            platform = session.get("platform", "unknown")
            player = session.get("player", "unknown")
            quality = session.get("quality_profile", "unknown")
            library = session.get("library_name", "unknown")
            location = session.get("location", "unknown")

            # Set stream info metric
            STREAM_INFO.labels(
                user=user,
                media_type=media_type,
                title=title[:50],  # Truncate long titles
                state=state,
                transcode_decision=transcode_decision,
                platform=platform,
                player=player,
                quality=quality,
                library=library,
                location=location,
            ).set(1)

            # Set progress metric
            progress = float(session.get("progress_percent", 0))
            STREAM_PROGRESS.labels(user=user, title=title[:50]).set(progress)

            # Set duration metric (convert from ms to seconds)
            duration_ms = int(session.get("duration", 0))
            STREAM_DURATION.labels(user=user, title=title[:50]).set(duration_ms / 1000)

        self._previous_sessions = current_sessions

    def _get_title(self, session: dict) -> str:
        """Get a human-readable title from a session.

        Args:
            session: Session dictionary.

        Returns:
            Formatted title string.
        """
        media_type = session.get("media_type", "")

        if media_type == "episode":
            show = session.get("grandparent_title", "")
            season = session.get("parent_media_index", "")
            episode = session.get("media_index", "")
            title = session.get("title", "")
            if show and season and episode:
                return f"{show} S{season}E{episode}"
            return session.get("full_title", title)

        elif media_type == "track":
            artist = session.get("grandparent_title", "")
            track = session.get("title", "")
            if artist and track:
                return f"{artist} - {track}"
            return session.get("full_title", track)

        return session.get("title", session.get("full_title", "Unknown"))

    def _normalize_transcode_decision(self, decision: str) -> str:
        """Normalize transcode decision to consistent values.

        Args:
            decision: Raw transcode decision string.

        Returns:
            Normalized decision: direct_play, direct_stream, or transcode.
        """
        decision_lower = decision.lower()
        if "direct play" in decision_lower:
            return "direct_play"
        elif "direct stream" in decision_lower or "copy" in decision_lower:
            return "direct_stream"
        elif "transcode" in decision_lower:
            return "transcode"
        return decision_lower.replace(" ", "_")
