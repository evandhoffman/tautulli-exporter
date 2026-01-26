"""Library statistics collector."""

import logging

from ..metrics import LIBRARY_DURATION, LIBRARY_ITEMS, LIBRARY_PLAYS
from ..tautulli_client import TautulliClient
from .base import BaseCollector

logger = logging.getLogger(__name__)


class LibraryCollector(BaseCollector):
    """Collector for library statistics."""

    name = "libraries"

    def __init__(self, client: TautulliClient):
        """Initialize the library collector."""
        super().__init__(client)

    async def collect(self) -> None:
        """Collect library metrics."""
        # Get basic library info
        libraries = await self.client.get_libraries()

        for library in libraries:
            section_id = str(library.get("section_id", ""))
            name = library.get("section_name", "unknown")
            lib_type = library.get("section_type", "unknown")

            # Item counts
            count = int(library.get("count", 0))
            parent_count = int(library.get("parent_count", 0) or 0)
            child_count = int(library.get("child_count", 0) or 0)

            LIBRARY_ITEMS.labels(
                library_name=name,
                library_type=lib_type,
                level="total",
            ).set(count)

            if parent_count:
                LIBRARY_ITEMS.labels(
                    library_name=name,
                    library_type=lib_type,
                    level="parent",
                ).set(parent_count)

            if child_count:
                LIBRARY_ITEMS.labels(
                    library_name=name,
                    library_type=lib_type,
                    level="child",
                ).set(child_count)

        # Get library play statistics
        await self._collect_library_stats()

    async def _collect_library_stats(self) -> None:
        """Collect library play statistics from the libraries table."""
        try:
            data = await self.client.get_libraries_table()
            libraries = data.get("data", [])

            for library in libraries:
                name = library.get("section_name", "unknown")

                # Play count
                plays = int(library.get("plays", 0))
                LIBRARY_PLAYS.labels(library_name=name).set(plays)

                # Duration (in seconds)
                duration = int(library.get("duration", 0))
                LIBRARY_DURATION.labels(library_name=name).set(duration)

        except Exception as e:
            logger.warning(f"Failed to collect library stats: {e}")
