"""User statistics collector."""

import logging

from ..metrics import (
    USER_DURATION,
    USER_LAST_SEEN,
    USER_PLAYS,
    USERS_ACTIVE,
    USERS_TOTAL,
)
from ..tautulli_client import TautulliClient
from .base import BaseCollector

logger = logging.getLogger(__name__)


class UserCollector(BaseCollector):
    """Collector for user statistics."""

    name = "users"

    def __init__(self, client: TautulliClient):
        """Initialize the user collector."""
        super().__init__(client)

    async def collect(self) -> None:
        """Collect user metrics."""
        # Get basic user list
        users = await self.client.get_users()

        total_users = len(users)
        active_users = sum(1 for u in users if u.get("is_active", 0) == 1)

        USERS_TOTAL.set(total_users)
        USERS_ACTIVE.set(active_users)

        # Get detailed user statistics
        await self._collect_user_stats()

    async def _collect_user_stats(self) -> None:
        """Collect detailed user statistics from users table."""
        try:
            data = await self.client.get_users_table()
            users = data.get("data", [])

            for user in users:
                name = user.get("friendly_name") or user.get("username", "unknown")

                # Skip if no valid name
                if not name or name == "unknown":
                    continue

                # Play count
                plays = int(user.get("plays", 0))
                USER_PLAYS.labels(user=name).set(plays)

                # Duration (in seconds)
                duration = int(user.get("duration", 0))
                USER_DURATION.labels(user=name).set(duration)

                # Last seen timestamp
                last_seen = user.get("last_seen")
                if last_seen:
                    USER_LAST_SEEN.labels(user=name).set(int(last_seen))

        except Exception as e:
            logger.warning(f"Failed to collect user stats: {e}")
