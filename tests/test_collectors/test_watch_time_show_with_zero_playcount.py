import pytest
from unittest.mock import AsyncMock

from tautulli_exporter.collectors.watch_time import WatchTimeCollector
from tautulli_exporter.metrics import EPISODE_WATCH_SECONDS


@pytest.mark.asyncio
async def test_show_with_zero_playcount_but_episodes_played(
    mock_client, sample_libraries_response
):
    # Top-level show has play_count 0
    media_items = [
        {
            "rating_key": "S3",
            "title": "Zero Show",
            "media_type": "show",
            "play_count": "0",
            "last_played": "1600000000",
        }
    ]

    mock_client.get_libraries = AsyncMock(return_value=sample_libraries_response)
    mock_client.get_library_media_info_all = AsyncMock(return_value=media_items)
    mock_client.get_library_media_info = AsyncMock(return_value={"data": media_items})

    # Children metadata returns a season with one episode
    mock_client.get_children_metadata = AsyncMock(
        side_effect=lambda rk: (
            [{"rating_key": "SE3", "title": "Season 1"}]
            if rk == "S3"
            else [{"rating_key": "E4", "title": "Episode 4", "media_type": "episode"}]
        )
    )

    async def fake_stats(rating_key, media_type=None, query_days="0"):
        if rating_key == "E4":
            return [{"query_days": "0", "total_time": 600}]
        return []

    mock_client.get_item_watch_time_stats = AsyncMock(side_effect=fake_stats)

    collector = WatchTimeCollector(mock_client, max_items=50)

    await collector.collect()

    # Check EPISODE metric for E4
    episode_samples = []
    for metric in EPISODE_WATCH_SECONDS.collect():
        for s in metric.samples:
            episode_samples.append((s.name, s.labels, s.value))

    keys = {labels.get("rating_key") for _, labels, _ in episode_samples}
    assert "E4" in keys
