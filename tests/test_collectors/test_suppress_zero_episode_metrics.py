import pytest
from unittest.mock import AsyncMock

from tautulli_exporter.collectors.watch_time import WatchTimeCollector
from tautulli_exporter.metrics import EPISODE_WATCH_SECONDS


@pytest.mark.asyncio
async def test_zero_episode_not_exported(mock_client, sample_libraries_response):
    # Show with one viewed episode but zero watch time
    media_items = [
        {
            "rating_key": "S10",
            "title": "Zero Ep Show",
            "media_type": "show",
            "last_played": "1700000000",
            "play_count": "1",
            "section_id": "2",
        }
    ]

    mock_client.get_libraries = AsyncMock(return_value=sample_libraries_response)
    mock_client.get_library_media_info = AsyncMock(return_value={"data": media_items})

    seasons_resp = {"children_list": [{"rating_key": "SE10", "title": "Season 1"}]}
    episodes_resp = {
        "children_list": [
            {
                "rating_key": "E10_1",
                "title": "Viewed Ep",
                "media_type": "episode",
                "media_index": "1",
                "last_viewed_at": "1700000000",
            }
        ]
    }

    mock_client.get_children_metadata = AsyncMock(
        side_effect=lambda rk: seasons_resp if rk == "S10" else episodes_resp
    )

    async def fake_stats(rating_key, media_type=None, query_days="0"):
        return [{"query_days": "0", "total_time": 0}]

    mock_client.get_item_watch_time_stats = AsyncMock(side_effect=fake_stats)

    collector = WatchTimeCollector(mock_client, max_items=50)
    await collector.collect()

    episode_keys = {
        labels.get("rating_key")
        for _, labels, _ in EPISODE_WATCH_SECONDS.collect()[0].samples
    }
    assert "E10_1" not in episode_keys


@pytest.mark.asyncio
async def test_remove_existing_episode_metric_when_zero(
    mock_client, sample_libraries_response
):
    # Pre-seed an episode metric (match the collector's grandparent title)
    EPISODE_WATCH_SECONDS.labels(
        library_name="TV Shows",
        rating_key="E11",
        title="Old Ep",
        parent_title="Season 1",
        grandparent_title="Now Zero Show",
        media_index="1",
        section_id="2",
    ).set(200)

    media_items = [
        {
            "rating_key": "S11",
            "title": "Now Zero Show",
            "media_type": "show",
            "last_played": "1700000000",
            "play_count": "1",
            "section_id": "2",
        }
    ]

    mock_client.get_libraries = AsyncMock(return_value=sample_libraries_response)
    mock_client.get_library_media_info = AsyncMock(return_value={"data": media_items})

    seasons_resp = {"children_list": [{"rating_key": "SE11", "title": "Season 1"}]}
    episodes_resp = {
        "children_list": [
            {
                "rating_key": "E11",
                "title": "Old Ep",
                "media_type": "episode",
                "media_index": "1",
                "last_viewed_at": "1700000000",
            }
        ]
    }

    mock_client.get_children_metadata = AsyncMock(
        side_effect=lambda rk: seasons_resp if rk == "S11" else episodes_resp
    )

    async def fake_stats(rating_key, media_type=None, query_days="0"):
        return [{"query_days": "0", "total_time": 0}]

    mock_client.get_item_watch_time_stats = AsyncMock(side_effect=fake_stats)

    collector = WatchTimeCollector(mock_client, max_items=50)
    await collector.collect()

    episode_samples = []
    for metric in EPISODE_WATCH_SECONDS.collect():
        for s in metric.samples:
            episode_samples.append((s.name, s.labels, s.value))
    episode_keys = {labels.get("rating_key") for _, labels, _ in episode_samples}
    assert "E11" not in episode_keys
