"""Collector for per-item and per-show watch time metrics."""

import logging
from typing import Any

from ..metrics import ITEM_WATCH_SECONDS, SHOW_WATCH_SECONDS
from ..tautulli_client import TautulliClient
from .base import BaseCollector

logger = logging.getLogger(__name__)


class WatchTimeCollector(BaseCollector):
    """Collects seconds watched per episode and per show.

    Strategy:
    - For each library, fetch media info entries via `get_library_media_info`.
    - For shows with play_count > 0, drill down using get_children_metadata:
      - Get seasons from show
      - Get episodes from each season
      - For each episode, call get_item_watch_time_stats with query_days=0
    - For movies and other items, call get_item_watch_time_stats directly
    - Aggregate episode watch times into show totals

    Note: This may be expensive on large libraries; config can disable it.
    """

    name = "watch_time"

    def __init__(self, client: TautulliClient, max_items: int = 500):
        super().__init__(client)
        self.max_items = max_items
        try:
            logger.info(
                "WatchTimeCollector initialized: max_items=%d, client=%s",
                self.max_items,
                getattr(client, "base_url", repr(client)),
            )
        except Exception:
            logger.debug("WatchTimeCollector initialization log failed")

    async def collect(self) -> None:
        # Get libraries
        libs = await self.client.get_libraries()

        processed = 0
        # aggregate per-show totals: key -> seconds
        show_totals: dict[tuple[str, str, str, str], int] = {}
        for lib in libs:
            section_id = str(lib.get("section_id", ""))
            library_name = lib.get("section_name", "unknown")

            try:
                media_table = await self.client.get_library_media_info(
                    section_id=section_id
                )
            except Exception as e:
                logger.warning(
                    f"Failed to fetch media info for library {library_name}: {e}"
                )
                continue

            items = media_table.get("data", []) if isinstance(media_table, dict) else []

            for item in items:
                if processed >= self.max_items:
                    """Collector for per-item and per-show watch time metrics."""

                    import logging
                    from typing import Any

                    from ..metrics import ITEM_WATCH_SECONDS, SHOW_WATCH_SECONDS
                    from ..tautulli_client import TautulliClient
                    from .base import BaseCollector

                    logger = logging.getLogger(__name__)

                    class WatchTimeCollector(BaseCollector):
                        """Collects seconds watched per episode and per show.

                        Strategy:
                        - For each library, fetch media info entries via `get_library_media_info`.
                        - Filter items with `play_count > 0` to avoid unplayed items.
                        - For each qualifying item (episode or show), call
                          `get_item_watch_time_stats` with `query_days=0` (all time) and set metric.

                        Note: This may be expensive on large libraries; config can disable it.
                        """

                        name = "watch_time"

                        def __init__(
                            self, client: TautulliClient, max_items: int = 500
                        ):
                            super().__init__(client)
                            self.max_items = max_items
                            try:
                                logger.info(
                                    "WatchTimeCollector initialized: max_items=%d, client=%s",
                                    self.max_items,
                                    getattr(client, "base_url", repr(client)),
                                )
                            except Exception:
                                logger.debug(
                                    "WatchTimeCollector initialization log failed"
                                )

                        async def collect(self) -> None:
                            # Get libraries
                            libs = await self.client.get_libraries()

                            processed = 0
                            # aggregate per-show totals: key -> seconds
                            show_totals: dict[tuple[str, str, str, str], int] = {}

                            try:
                                logger.debug(
                                    "WatchTimeCollector starting collect: max_items=%d libraries=%d",
                                    self.max_items,
                                    len(libs),
                                )
                            except Exception:
                                pass

                            for lib in libs:
                                section_id = str(lib.get("section_id", ""))
                                library_name = lib.get("section_name", "unknown")

                                try:
                                    items = (
                                        await self.client.get_library_media_info_all(
                                            section_id=section_id
                                        )
                                    )
                                except Exception as e:
                                    logger.warning(
                                        f"Failed to fetch media info for library {library_name}: {e}"
                                    )
                                    continue
                                try:
                                    logger.debug(
                                        "Library %s (id=%s) returned %d items (paged)",
                                        library_name,
                                        section_id,
                                        len(items),
                                    )
                                except Exception:
                                    pass

                                for item in items:
                                    if processed >= self.max_items:
                                        logger.info(
                                            "WatchTimeCollector reached max_items cap: processed=%d max_items=%d (stopping, library=%s)",
                                            processed,
                                            self.max_items,
                                            library_name,
                                        )
                                        return

                                    try:
                                        play_count = int(item.get("play_count", 0) or 0)
                                    except Exception:
                                        play_count = 0

                                    if play_count <= 0:
                                        try:
                                            logger.debug(
                                                "Skipping item with no plays: rating_key=%s title=%s library=%s",
                                                item.get("rating_key"),
                                                item.get("title")
                                                or item.get("full_title"),
                                                library_name,
                                            )
                                        except Exception:
                                            pass
                                        continue

                                    rating_key = str(item.get("rating_key", ""))
                                    title = (
                                        item.get("title")
                                        or item.get("full_title")
                                        or "unknown"
                                    )
                                    media_type = item.get("media_type", "unknown")

                if media_type == "show":
                    # Drill down into show -> seasons -> episodes
                    await self._process_show(
                        rating_key, title, library_name, show_totals
                    )
                else:
                    # For movies and other media types, get watch time directly
                    await self._process_item(
                        rating_key, title, media_type, library_name, show_totals
                    )

                processed += 1

        # Publish aggregated show-level totals
        try:
            for (
                show_key,
                show_title,
                show_media_type,
                lib_name,
            ), seconds in show_totals.items():
                SHOW_WATCH_SECONDS.labels(
                    show_rating_key=show_key or "",
                    show_title=show_title,
                    media_type=show_media_type,
                    library_name=lib_name,
                ).set(seconds)
                # Log aggregated show totals when there is watched time
                try:
                    if seconds > 0:
                        logger.info(
                            "WatchTimeCollector: show aggregate - show_rating_key=%s show_title=%s media_type=%s library=%s seconds=%d",
                            show_key,
                            show_title,
                            show_media_type,
                            lib_name,
                            seconds,
                        )
                except Exception:
                    logger.debug("Failed to log show aggregate info")
        except Exception:
            logger.debug("Failed to publish show-level watch time aggregates")

    async def _process_show(
        self,
        show_rating_key: str,
        show_title: str,
        library_name: str,
        show_totals: dict[tuple[str, str, str, str], int],
    ) -> None:
        """Drill down into a show to get episode watch times."""
        try:
            # Get seasons for the show
            seasons = await self.client.get_children_metadata(show_rating_key)
        except Exception as e:
            logger.warning(
                f"Failed to get seasons for show {show_title} ({show_rating_key}): {e}"
            )
            return

        show_total_seconds = 0

        for season in seasons:
            season_rating_key = str(season.get("rating_key", ""))
            if not season_rating_key:
                continue

            try:
                # Get episodes for the season
                episodes = await self.client.get_children_metadata(season_rating_key)
            except Exception as e:
                logger.warning(
                    f"Failed to get episodes for season {season.get('title', 'unknown')} ({season_rating_key}): {e}"
                )
                continue

            for episode in episodes:
                if episode.get("media_type") != "episode":
                    continue

                episode_rating_key = str(episode.get("rating_key", ""))
                episode_title = episode.get("title", "unknown")
                media_index = episode.get("media_index", "")

                # Get watch time stats for the episode
                try:
                    stats = await self.client.get_item_watch_time_stats(
                        rating_key=episode_rating_key,
                        media_type="episode",
                        query_days="0",
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to get watch time for episode {episode_title} ({episode_rating_key}): {e}"
                    )
                    continue

                # Extract total_seconds
                total_seconds = 0
                if isinstance(stats, list) and stats:
                    match = None
                    for s in stats:
                        if str(s.get("query_days", "")) == "0":
                            match = s
                            break
                    if match is None:
                        match = stats[-1]
                    try:
                        total_seconds = int(match.get("total_time", 0) or 0)
                    except Exception:
                        total_seconds = 0

                # Set per-episode metric
                ITEM_WATCH_SECONDS.labels(
                    rating_key=episode_rating_key,
                    title=episode_title[:100],
                    media_type="episode",
                    library_name=library_name,
                ).set(total_seconds)

                # Log episode watch time
                try:
                    if total_seconds > 0:
                        logger.info(
                            "WatchTimeCollector: episode played - rating_key=%s title=%s parent_title=%s grandparent_title=%s media_index=%s library=%s seconds=%d",
                            episode_rating_key,
                            episode_title,
                            season.get("title", "unknown"),
                            show_title,
                            media_index,
                            library_name,
                            total_seconds,
                        )
                except Exception:
                    logger.debug("Failed to log episode watch info")

                show_total_seconds += total_seconds

        # Update show totals
        show_id = (show_rating_key, show_title[:100], "show", library_name)
        show_totals[show_id] = show_totals.get(show_id, 0) + show_total_seconds

    async def _process_item(
        self,
        rating_key: str,
        title: str,
        media_type: str,
        library_name: str,
        show_totals: dict[tuple[str, str, str, str], int],
    ) -> None:
        """Process a non-show item (movie, etc.) for watch time."""
        # Fetch watch time stats (all time)
        try:
            stats = await self.client.get_item_watch_time_stats(
                rating_key=rating_key,
                media_type=media_type,
                query_days="0",
            )
        except Exception as e:
            logger.warning(
                f"Failed to get watch time for item {title} ({rating_key}): {e}"
            )
            return

        # stats is a list of dicts. Find entry with query_days == 0 or pick last
        total_seconds = 0
        if isinstance(stats, list) and stats:
            match = None
            for s in stats:
                # some responses include 'query_days' as int or str
                if str(s.get("query_days", "")) == "0":
                    match = s
                    break
            if match is None:
                match = stats[-1]
            try:
                total_seconds = int(match.get("total_time", 0) or 0)
            except Exception:
                total_seconds = 0

        ITEM_WATCH_SECONDS.labels(
            rating_key=rating_key,
            title=title[:100],
            media_type=media_type,
            library_name=library_name,
        ).set(total_seconds)

        # Log each played item with >0 seconds
        try:
            if total_seconds > 0:
                logger.info(
                    "WatchTimeCollector: item played - rating_key=%s title=%s media_type=%s library=%s seconds=%d",
                    rating_key,
                    title,
                    media_type,
                    library_name,
                    total_seconds,
                )
        except Exception:
            # Ensure logging errors don't interrupt collection
            logger.debug("Failed to log item watch info")

        # For non-episodes, aggregate into show-level totals (though for movies, show_key = rating_key)
        show_key = rating_key
        show_title_agg = title
        show_media_type = media_type

        show_id = (show_key, show_title_agg[:100], show_media_type, library_name)
        show_totals[show_id] = show_totals.get(show_id, 0) + total_seconds
