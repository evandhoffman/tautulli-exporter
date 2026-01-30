import pytest
from unittest.mock import AsyncMock

from tautulli_exporter.collectors.watch_time import WatchTimeCollector
from tautulli_exporter.metrics import EPISODE_WATCH_SECONDS


@pytest.mark.asyncio
async def test_skip_unviewed_episodes(mock_client, sample_libraries_response):
    # Setup: a show with two episodes, one viewed and one not
    media_items = [
        {
            "rating_key": "S300",
            "title": "Skip Show",
            "media_type": "show",
            "last_played": "1700000000",
            "play_count": "1",
            "section_id": "2",
        }
    ]

    mock_client.get_libraries = AsyncMock(return_value=sample_libraries_response)
    mock_client.get_library_media_info = AsyncMock(return_value={"data": media_items})

    seasons_resp = {"children_list": [{"rating_key": "SE300", "title": "Season 1"}]}
    episodes_resp = {
        "children_list": [
            {
                "rating_key": "E300_1",
                "title": "Viewed Ep",
                "media_type": "episode",
                "media_index": "1",
                "last_viewed_at": "1700000000",
            },
            {
                "rating_key": "E300_2",
                "title": "Unviewed Ep",
                "media_type": "episode",
                "media_index": "2",
            },
        ]
    }

    mock_client.get_children_metadata = AsyncMock(
        side_effect=lambda rk: seasons_resp if rk == "S300" else episodes_resp
    )

    async def fake_stats(rating_key, media_type=None, query_days="0"):
        if rating_key == "E300_1":
            return [{"query_days": "0", "total_time": 1234}]
        if rating_key == "E300_2":
            return [{"query_days": "0", "total_time": 0}]
        return []

    mock_client.get_item_watch_time_stats = AsyncMock(side_effect=fake_stats)

    collector = WatchTimeCollector(mock_client, max_items=50)
    await collector.collect()

    episode_samples = []
    for metric in EPISODE_WATCH_SECONDS.collect():
        for s in metric.samples:
            episode_samples.append((s.name, s.labels, s.value))

    episode_keys = {labels.get("rating_key") for _, labels, _ in episode_samples}

    assert "E300_1" in episode_keys
    assert "E300_2" not in episode_keys
