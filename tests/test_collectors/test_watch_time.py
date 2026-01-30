import pytest
from unittest.mock import AsyncMock

from tautulli_exporter.collectors.watch_time import WatchTimeCollector
from tautulli_exporter.metrics import (
    ITEM_WATCH_SECONDS,
    SHOW_WATCH_SECONDS,
    EPISODE_WATCH_SECONDS,
)


@pytest.mark.asyncio
async def test_collect_drilldown_and_item_processing(
    mock_client, sample_libraries_response
):
    # Setup libraries
    mock_client.get_libraries = AsyncMock(return_value=sample_libraries_response)

    # Prepare media info items: one show, one movie, one episode
    media_items = [
        {
            "rating_key": "S1",
            "title": "Test Show",
            "media_type": "show",
            "play_count": "2",
            "last_played": "1610000000",
        },
        {
            "rating_key": "M1",
            "title": "Test Movie",
            "media_type": "movie",
            "play_count": "1",
        },
        {
            "rating_key": "E1",
            "title": "Pilot",
            "media_type": "episode",
            "play_count": "1",
            "grandparent_rating_key": "S1",
            "grandparent_title": "Test Show",
            "last_viewed_at": "1610000001",
        },
    ]

    mock_client.get_library_media_info_all = AsyncMock(return_value=media_items)
    # Some code paths call get_library_media_info (paged or single response)
    mock_client.get_library_media_info = AsyncMock(return_value={"data": media_items})

    # child metadata: seasons for S1 and episodes for season SE1
    mock_client.get_children_metadata = AsyncMock(
        side_effect=lambda rk: (
            [{"rating_key": "SE1", "title": "Season 1"}]
            if rk == "S1"
            else [
                {
                    "rating_key": "E2",
                    "title": "Episode 2",
                    "media_type": "episode",
                    "media_index": "2",
                    "last_viewed_at": "1610000002",
                }
            ]
        )
    )

    # watch time stats returns 1200 seconds for episodes and 3600 for movies
    async def fake_stats(rating_key, media_type=None, query_days="0"):
        if rating_key in ("E1", "E2"):
            return [{"query_days": "0", "total_time": 1200}]
        if rating_key == "M1":
            return [{"query_days": "0", "total_time": 3600}]
        return []

    mock_client.get_item_watch_time_stats = AsyncMock(side_effect=fake_stats)

    collector = WatchTimeCollector(mock_client, max_items=50)

    # Run collection
    await collector.collect()

    # Verify client calls
    mock_client.get_library_media_info.assert_called()
    mock_client.get_children_metadata.assert_called()
    mock_client.get_item_watch_time_stats.assert_called()

    # Verify ITEM metrics: expect at least entries for M1 and possibly E1
    item_samples = []
    for metric in ITEM_WATCH_SECONDS.collect():
        for s in metric.samples:
            item_samples.append((s.name, s.labels, s.value))

    keys = {labels.get("rating_key") for _, labels, _ in item_samples}
    assert "M1" in keys

    # Verify EPISODE metric has entries for episodes collected (E1 and E2)
    episode_samples = []
    for metric in EPISODE_WATCH_SECONDS.collect():
        for s in metric.samples:
            episode_samples.append((s.name, s.labels, s.value))

    episode_keys = {labels.get("rating_key") for _, labels, _ in episode_samples}
    assert "E1" in episode_keys or "E2" in episode_keys

    # Verify show aggregate metric exists for the show
    show_samples = []
    for metric in SHOW_WATCH_SECONDS.collect():
        for s in metric.samples:
            show_samples.append((s.name, s.labels, s.value))

    show_keys = {labels.get("show_rating_key") for _, labels, _ in show_samples}
    assert "S1" in show_keys
