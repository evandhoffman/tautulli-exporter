"""Collector for per-item and per-show watch time metrics."""

import logging
from typing import Any

from ..metrics import (
    SHOW_WATCH_SECONDS,
    EPISODE_WATCH_SECONDS,
)
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

            # Fetch media info via paginated 'get_library_media_info' calls (start/length)
            items = []
            page_size = 500
            start = 0
            while True:
                try:
                    resp = await self.client.get_library_media_info(
                        section_id=section_id, start=start, length=page_size
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to fetch media info page starting at {start} for library {library_name}: {e}"
                    )
                    break

                # Normalize response to list of items
                page_items = []
                if isinstance(resp, dict):
                    data_field = resp.get("data")
                    if isinstance(data_field, list):
                        page_items = data_field
                    elif isinstance(data_field, dict):
                        page_items = data_field.get("data", [])
                elif isinstance(resp, list):
                    page_items = resp

                items.extend(page_items)

                try:
                    logger.debug(
                        "Library %s (id=%s) page start=%d returned %d items",
                        library_name,
                        section_id,
                        start,
                        len(page_items),
                    )
                except Exception:
                    pass

                if not page_items or len(page_items) < page_size:
                    break

                start += page_size

            try:
                logger.debug(
                    "Library %s (id=%s) total returned %d items",
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

                # Prepare common fields early
                rating_key = str(item.get("rating_key", ""))
                title = item.get("title") or item.get("full_title") or "unknown"
                media_type = item.get("media_type", "unknown")

                try:
                    play_count = int(item.get("play_count", 0) or 0)
                except Exception:
                    play_count = 0

                # For shows: follow the algorithm — only drill into shows where last_played is not null
                if media_type == "show":
                    last_played = item.get("last_played")
                    # Optionally allow drilling into all shows via config
                    from ..config import get_settings

                    drill_all = False
                    try:
                        drill_all = get_settings().watch_time_drill_all_shows
                    except Exception:
                        pass

                    if last_played in (None, "", 0, "0") and not drill_all:
                        try:
                            logger.debug(
                                "Skipping show with no last_played: rating_key=%s title=%s library=%s",
                                rating_key,
                                title,
                                library_name,
                            )
                        except Exception:
                            pass
                        # still process the top-level show item metrics, but don't drill
                        await self._process_item(
                            item,
                            rating_key,
                            title,
                            media_type,
                            library_name,
                            section_id,
                            show_totals,
                        )
                        processed += 1
                        continue
                    elif last_played in (None, "", 0, "0") and drill_all:
                        try:
                            logger.info(
                                "Drilling show %s (%s) despite missing last_played due to config",
                                title,
                                rating_key,
                            )
                        except Exception:
                            pass
                else:
                    # Non-show items: skip if no plays
                    if play_count <= 0:
                        try:
                            logger.debug(
                                "Skipping item with no plays: rating_key=%s title=%s library=%s",
                                rating_key,
                                title,
                                library_name,
                            )
                        except Exception:
                            pass
                        continue

                rating_key = str(item.get("rating_key", ""))
                title = item.get("title") or item.get("full_title") or "unknown"

                if media_type == "show":
                    # Drill down into show -> seasons -> episodes
                    await self._process_show(
                        rating_key, title, library_name, section_id, show_totals
                    )
                # Process the item itself (show, movie, episode)
                await self._process_item(
                    item,
                    rating_key,
                    title,
                    media_type,
                    library_name,
                    section_id,
                    show_totals,
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
                # Only set show-level watch seconds when > 0; otherwise remove any existing metric for the labelset
                try:
                    if seconds > 0:
                        SHOW_WATCH_SECONDS.labels(
                            show_rating_key=show_key or "",
                            show_title=show_title,
                            media_type=show_media_type,
                            library_name=lib_name,
                        ).set(seconds)
                        try:
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
                    else:
                        try:
                            SHOW_WATCH_SECONDS.remove(
                                show_key or "", show_title, show_media_type, lib_name
                            )
                        except Exception:
                            pass
                except Exception:
                    logger.debug("Failed to publish show-level watch time aggregates")
        except Exception:
            logger.debug("Failed to publish show-level watch time aggregates")

    async def _process_show(
        self,
        show_rating_key: str,
        show_title: str,
        library_name: str,
        section_id: str,
        show_totals: dict[tuple[str, str, str, str], int],
    ) -> None:
        """Drill down into a show to get episode watch times."""
        try:
            # Get seasons for the show. Some Tautulli versions return a list of dicts,
            # others may return a list of rating_key strings.
            seasons_resp = await self.client.get_children_metadata(show_rating_key)
        except Exception as e:
            logger.warning(
                f"Failed to get seasons for show {show_title} ({show_rating_key}): {e}"
            )
            return

        # Normalize seasons into an iterable of season dict-like objects or rating keys
        seasons = []
        if isinstance(seasons_resp, dict):
            # Some responses include nested 'data' -> 'children_list' or 'data' -> 'data'
            data_field = seasons_resp.get("data")
            if isinstance(data_field, dict) and "children_list" in data_field:
                seasons = data_field.get("children_list", [])
            elif isinstance(data_field, dict) and "data" in data_field:
                seasons = data_field.get("data", [])
            elif isinstance(data_field, list):
                seasons = data_field
            elif "children_list" in seasons_resp:
                seasons = seasons_resp.get("children_list", [])
        elif isinstance(seasons_resp, list):
            seasons = seasons_resp
        else:
            # Unexpected shape
            try:
                logger.debug(
                    "Unexpected seasons response type %s for show %s",
                    type(seasons_resp),
                    show_rating_key,
                )
            except Exception:
                pass
            return

        try:
            logger.debug(
                "Drilling show %s (%s): found %d seasons",
                show_title,
                show_rating_key,
                len(seasons),
            )
        except Exception:
            pass

        show_total_seconds = 0

        for season in seasons:
            # season may be a dict or a rating_key string
            if isinstance(season, dict):
                season_rating_key = str(
                    season.get("rating_key", "") or season.get("ratingKey", "")
                )
                season_title = season.get("title", "unknown")
            elif isinstance(season, (str, int)):
                season_rating_key = str(season)
                season_title = "unknown"
            else:
                logger.debug("Skipping unexpected season type: %s", type(season))
                continue

            if not season_rating_key:
                continue

            try:
                # Get episodes for the season
                episodes_resp = await self.client.get_children_metadata(
                    season_rating_key
                )
            except Exception as e:
                logger.warning(
                    f"Failed to get episodes for season {season_title} ({season_rating_key}): {e}"
                )
                continue

            # Normalize episodes response similarly: support 'data'->'children_list' and other shapes
            episodes = []
            if isinstance(episodes_resp, dict):
                data_field = episodes_resp.get("data")
                if isinstance(data_field, dict) and "children_list" in data_field:
                    episodes = data_field.get("children_list", [])
                elif isinstance(data_field, dict) and "data" in data_field:
                    episodes = data_field.get("data", [])
                elif isinstance(data_field, list):
                    episodes = data_field
                elif "children_list" in episodes_resp:
                    episodes = episodes_resp.get("children_list", [])
            elif isinstance(episodes_resp, list):
                episodes = episodes_resp
            else:
                logger.debug(
                    "Unexpected episodes response type %s for season %s",
                    type(episodes_resp),
                    season_rating_key,
                )
                episodes = []

            # Fallback: if no episodes found via children metadata, try library media info
            if not episodes:
                try:
                    fallback = await self.client.get_library_media_info(
                        section_id=section_id, rating_key=season_rating_key
                    )
                    if isinstance(fallback, dict) and "data" in fallback:
                        episodes = fallback.get("data", [])
                except Exception:
                    pass

            try:
                logger.debug(
                    "Season %s (%s): found %d episodes",
                    season_title,
                    season_rating_key,
                    len(episodes),
                )
            except Exception:
                pass

            try:
                logger.debug(
                    "Season %s (%s): found %d episodes",
                    season_title,
                    season_rating_key,
                    len(episodes),
                )
            except Exception:
                pass

            for episode in episodes:
                # episode may be a dict or a rating_key string
                episode_rating_key = None
                episode_title = "unknown"
                media_index = ""
                last_viewed = None

                if isinstance(episode, dict):
                    media_type_val = episode.get("media_type") or episode.get("type")
                    if media_type_val and str(media_type_val) != "episode":
                        continue

                    episode_rating_key = str(
                        episode.get("rating_key", "") or episode.get("ratingKey", "")
                    )
                    episode_title = episode.get("title", "unknown")
                    media_index = episode.get("media_index", "")
                    # Accept multiple possible last-viewed field names
                    last_viewed = (
                        episode.get("last_viewed_at")
                        or episode.get("last_viewed")
                        or episode.get("last_played")
                    )
                elif isinstance(episode, (str, int)):
                    episode_rating_key = str(episode)
                    episode_title = "unknown"
                    media_index = ""
                    # Try to fetch episode details to determine last_viewed
                    try:
                        ep_info = await self.client.get_library_media_info(
                            section_id=section_id, rating_key=episode_rating_key
                        )
                        if isinstance(ep_info, dict):
                            data = ep_info.get("data") or {}
                            # data may be a list or dict
                            if isinstance(data, list) and data:
                                ep = data[0]
                            elif isinstance(data, dict) and "data" in data:
                                ep_list = data.get("data", [])
                                ep = ep_list[0] if ep_list else None
                            else:
                                ep = None

                            if isinstance(ep, dict):
                                episode_title = ep.get("title", episode_title)
                                media_index = ep.get("media_index", media_index)
                                last_viewed = (
                                    ep.get("last_viewed_at")
                                    or ep.get("last_viewed")
                                    or ep.get("last_played")
                                )
                    except Exception:
                        # If we can't fetch details, continue and skip based on missing last_viewed
                        last_viewed = None
                else:
                    logger.debug("Skipping unexpected episode type: %s", type(episode))
                    continue

                if not episode_rating_key:
                    continue

                # Skip episodes without a last_viewed timestamp
                if last_viewed in (None, "", 0, "0"):
                    try:
                        logger.debug(
                            "Skipping episode with no last_viewed: %s (%s)",
                            episode_title,
                            episode_rating_key,
                        )
                    except Exception:
                        pass
                    continue

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

                try:
                    logger.debug(
                        "Got watch time stats for episode %s (%s): %s",
                        episode_title,
                        episode_rating_key,
                        stats,
                    )
                except Exception:
                    pass

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

                # Set per-episode metric (item-level)

                # Set explicit episode metric with richer labels (only if > 0)
                try:
                    if total_seconds > 0:
                        EPISODE_WATCH_SECONDS.labels(
                            library_name=library_name,
                            rating_key=episode_rating_key,
                            title=episode_title[:100],
                            parent_title=season_title[:100],
                            grandparent_title=show_title[:100],
                            media_index=str(media_index),
                            section_id=str(section_id),
                        ).set(total_seconds)
                    else:
                        # Remove any previous metric for this episode labelset
                        try:
                            EPISODE_WATCH_SECONDS.remove(
                                library_name,
                                episode_rating_key,
                                episode_title[:100],
                                season_title[:100],
                                show_title[:100],
                                str(media_index),
                                str(section_id),
                            )
                        except Exception:
                            pass
                    try:
                        logger.debug(
                            "Set/Removed EPISODE_WATCH_SECONDS: %s (%s) parent=%s grandparent=%s seconds=%d",
                            episode_title,
                            episode_rating_key,
                            season_title,
                            show_title,
                            total_seconds,
                        )
                    except Exception:
                        pass
                except Exception:
                    logger.debug("Failed to set/remove EPISODE_WATCH_SECONDS metric")

                # Log episode watch time
                try:
                    if total_seconds > 0:
                        logger.info(
                            "WatchTimeCollector: episode played - rating_key=%s title=%s parent_title=%s grandparent_title=%s media_index=%s library=%s seconds=%d",
                            episode_rating_key,
                            episode_title,
                            season_title,
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

        try:
            logger.debug(
                "Show %s (%s) total seconds from episodes: %d",
                show_title,
                show_rating_key,
                show_total_seconds,
            )
        except Exception:
            pass

    async def _process_item(
        self,
        item: dict[str, Any],
        rating_key: str,
        title: str,
        media_type: str,
        library_name: str,
        section_id: str,
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

        # If top-level item is an episode, also set the episode-specific metric
        if media_type == "episode":
            parent_title = (
                item.get("parent_title")
                or item.get("parent")
                or item.get("parent_full_title")
                or "unknown"
            )
            grandparent_title = (
                item.get("grandparent_title")
                or item.get("grandparent_full_title")
                or item.get("grandparent")
                or "unknown"
            )
            media_index = item.get("media_index", "")

            # Only export episode metric if last_viewed is present
            last_viewed = (
                item.get("last_viewed_at")
                or item.get("last_viewed")
                or item.get("last_played")
            )
            if last_viewed in (None, "", 0, "0"):
                try:
                    logger.debug(
                        "Skipping top-level episode with no last_viewed: %s (%s)",
                        title,
                        rating_key,
                    )
                except Exception:
                    pass
            else:
                try:
                    if total_seconds > 0:
                        EPISODE_WATCH_SECONDS.labels(
                            library_name=library_name,
                            rating_key=rating_key,
                            title=title[:100],
                            parent_title=parent_title[:100],
                            grandparent_title=grandparent_title[:100],
                            media_index=str(media_index),
                            section_id=str(section_id),
                        ).set(total_seconds)
                    else:
                        try:
                            EPISODE_WATCH_SECONDS.remove(
                                library_name,
                                rating_key,
                                title[:100],
                                parent_title[:100],
                                grandparent_title[:100],
                                str(media_index),
                                str(section_id),
                            )
                        except Exception:
                            pass
                except Exception:
                    logger.debug(
                        "Failed to set/remove EPISODE_WATCH_SECONDS for top-level episode"
                    )

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

        # Aggregate into show-level totals
        if media_type == "episode":
            show_key = str(
                item.get("grandparent_rating_key") or item.get("grandparent_key") or ""
            )
            show_title_agg = (
                item.get("grandparent_title")
                or item.get("grandparent_full_title")
                or item.get("grandparent")
                or "unknown"
            )
            show_media_type = "show"
        else:
            show_key = rating_key
            show_title_agg = title
            show_media_type = media_type

        show_id = (show_key, show_title_agg[:100], show_media_type, library_name)
        show_totals[show_id] = show_totals.get(show_id, 0) + total_seconds
