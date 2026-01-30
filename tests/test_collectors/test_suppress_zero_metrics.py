import pytest
from unittest.mock import AsyncMock

from tautulli_exporter.collectors.watch_time import WatchTimeCollector
from tautulli_exporter.metrics import ITEM_WATCH_SECONDS, SHOW_WATCH_SECONDS


@pytest.mark.asyncio
async def test_zero_item_and_show_not_exported(mock_client, sample_libraries_response):
    # Setup: a movie and a show where watch stats are zero
    media_items = [
        {
            "rating_key": "M0",
            "title": "Zero Movie",
            "media_type": "movie",
            "play_count": "1",
        },
        {
            "rating_key": "S0",
            "title": "Zero Show",
            "media_type": "show",
            "play_count": "1",
            "last_played": "1700000000",
            "section_id": "2",
        },
    ]

    mock_client.get_libraries = AsyncMock(return_value=sample_libraries_response)
    mock_client.get_library_media_info = AsyncMock(return_value={"data": media_items})

    # Show children include a season with one episode that has zero time
    mock_client.get_children_metadata = AsyncMock(
        side_effect=lambda rk: (
            [{"rating_key": "SE0", "title": "Season 1"}]
            if rk == "S0"
            else [
                {
                    "rating_key": "E0",
                    "title": "Episode 0",
                    "media_type": "episode",
                    "media_index": "1",
                    "last_viewed_at": "1700000000",
                }
            ]
        )
    )

    async def fake_stats(rating_key, media_type=None, query_days="0"):
        # All stats return zero
        return [{"query_days": "0", "total_time": 0}]

    mock_client.get_item_watch_time_stats = AsyncMock(side_effect=fake_stats)

    # Ensure no lingering metrics
    try:
        ITEM_WATCH_SECONDS.remove("M0", "Zero Movie", "movie", "Movies")
    except Exception:
        pass
    try:
        SHOW_WATCH_SECONDS.remove("S0", "Zero Show", "show", "TV Shows")
    except Exception:
        pass

    collector = WatchTimeCollector(mock_client, max_items=50)
    await collector.collect()

    # Collect metrics
    item_keys = {
        labels.get("rating_key")
        for _, labels, _ in ITEM_WATCH_SECONDS.collect()[0].samples
    }
    show_keys = {
        labels.get("show_rating_key")
        for _, labels, _ in SHOW_WATCH_SECONDS.collect()[0].samples
    }

    assert "M0" not in item_keys
    assert "S0" not in show_keys


@pytest.mark.asyncio
async def test_remove_existing_item_metric_when_zero(
    mock_client, sample_libraries_response
):
    # Start by setting a metric value manually
    ITEM_WATCH_SECONDS.labels(
        rating_key="M1", title="Now 100", media_type="movie", library_name="Movies"
    ).set(100)

    # Now collector returns zero for M1
    media_items = [
        {
            "rating_key": "M1",
            "title": "Now 100",
            "media_type": "movie",
            "play_count": "1",
        }
    ]
    mock_client.get_libraries = AsyncMock(return_value=sample_libraries_response)
    mock_client.get_library_media_info = AsyncMock(return_value={"data": media_items})

    async def fake_stats(rating_key, media_type=None, query_days="0"):
        return [{"query_days": "0", "total_time": 0}]

    mock_client.get_item_watch_time_stats = AsyncMock(side_effect=fake_stats)

    collector = WatchTimeCollector(mock_client, max_items=50)
    await collector.collect()

    keys = {
        labels.get("rating_key")
        for _, labels, _ in ITEM_WATCH_SECONDS.collect()[0].samples
    }
    assert "M1" not in keys
