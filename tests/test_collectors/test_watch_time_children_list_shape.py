import pytest
from unittest.mock import AsyncMock

from tautulli_exporter.collectors.watch_time import WatchTimeCollector
from tautulli_exporter.metrics import EPISODE_WATCH_SECONDS


@pytest.mark.asyncio
async def test_children_list_shape_is_handled(mock_client, sample_libraries_response):
    # Show response uses data.children_list structure
    media_items = [
        {
            "rating_key": "2973",
            "title": "Andor",
            "media_type": "show",
            "last_played": "1769740410",
            "play_count": "1",
            "section_id": "2",
        }
    ]

    mock_client.get_libraries = AsyncMock(return_value=sample_libraries_response)
    mock_client.get_library_media_info_all = AsyncMock(return_value=media_items)
    mock_client.get_library_media_info = AsyncMock(return_value={"data": media_items})

    # get_children_metadata for show returns a dict with data.children_list (as in sample)
    seasons_resp = {
        "data": {
            "children_list": [
                {
                    "media_type": "season",
                    "section_id": "2",
                    "rating_key": "2974",
                    "title": "Season 1",
                }
            ]
        }
    }

    # episodes returned for season uses children_list
    episodes_resp = {
        "data": {
            "children_list": [
                {
                    "media_type": "episode",
                    "rating_key": "E2974_1",
                    "title": "Episode 1",
                    "media_index": "1",
                    "last_viewed_at": "1700000000",
                },
                {
                    "media_type": "episode",
                    "rating_key": "E2974_2",
                    "title": "Episode 2",
                    "media_index": "2",
                    "last_viewed_at": "1700000001",
                },
            ]
        }
    }

    mock_client.get_children_metadata = AsyncMock(
        side_effect=lambda rk: seasons_resp if rk == "2973" else episodes_resp
    )

    async def fake_stats(rating_key, media_type=None, query_days="0"):
        if rating_key in ("E2974_1", "E2974_2"):
            return [{"query_days": "0", "total_time": 900}]
        return []

    mock_client.get_item_watch_time_stats = AsyncMock(side_effect=fake_stats)

    collector = WatchTimeCollector(mock_client, max_items=50)

    await collector.collect()

    episode_samples = []
    for metric in EPISODE_WATCH_SECONDS.collect():
        for s in metric.samples:
            episode_samples.append((s.name, s.labels, s.value))

    keys = {labels.get("rating_key") for _, labels, _ in episode_samples}
    assert "E2974_1" in keys
    assert "E2974_2" in keys
