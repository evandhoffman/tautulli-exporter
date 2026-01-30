import pytest
from unittest.mock import AsyncMock

from tautulli_exporter.collectors.watch_time import WatchTimeCollector
from tautulli_exporter.metrics import SHOW_WATCH_SECONDS


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
        SHOW_WATCH_SECONDS.remove("S0", "Zero Show", "show", "TV Shows")
    except Exception:
        pass

    collector = WatchTimeCollector(mock_client, max_items=50)
    await collector.collect()

    # Collect metrics
    show_keys = {
        labels.get("show_rating_key")
        for _, labels, _ in SHOW_WATCH_SECONDS.collect()[0].samples
    }

    assert "S0" not in show_keys
