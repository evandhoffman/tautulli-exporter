import pytest
from unittest.mock import AsyncMock

from tautulli_exporter.collectors.watch_time import WatchTimeCollector
from tautulli_exporter.metrics import EPISODE_WATCH_SECONDS


@pytest.mark.asyncio
async def test_skip_shows_without_last_played(mock_client, sample_libraries_response):
    # Show has no last_played, but its episodes have plays - they should be skipped
    media_items = [
        {
            "rating_key": "S4",
            "title": "Skip Show",
            "media_type": "show",
            "play_count": "0",
            "last_played": None,
        }
    ]

    mock_client.get_libraries = AsyncMock(return_value=sample_libraries_response)
    mock_client.get_library_media_info_all = AsyncMock(return_value=media_items)
    mock_client.get_library_media_info = AsyncMock(return_value={"data": media_items})

    # children return episodes
    mock_client.get_children_metadata = AsyncMock(
        side_effect=lambda rk: [
            {"rating_key": "E5", "title": "Ep5", "media_type": "episode"}
        ]
    )

    async def fake_stats(rating_key, media_type=None, query_days="0"):
        if rating_key == "E5":
            return [{"query_days": "0", "total_time": 500}]
        return []

    mock_client.get_item_watch_time_stats = AsyncMock(side_effect=fake_stats)

    collector = WatchTimeCollector(mock_client, max_items=50)

    await collector.collect()

    episode_samples = []
    for metric in EPISODE_WATCH_SECONDS.collect():
        for s in metric.samples:
            episode_samples.append((s.name, s.labels, s.value))

    keys = {labels.get("rating_key") for _, labels, _ in episode_samples}
    assert "E5" not in keys
