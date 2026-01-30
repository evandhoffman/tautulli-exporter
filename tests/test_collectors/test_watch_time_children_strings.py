import pytest
from unittest.mock import AsyncMock

from tautulli_exporter.collectors.watch_time import WatchTimeCollector
from tautulli_exporter.metrics import SHOW_WATCH_SECONDS


@pytest.mark.asyncio
async def test_children_metadata_returns_strings(
    mock_client, sample_libraries_response
):
    # Setup libraries
    mock_client.get_libraries = AsyncMock(return_value=sample_libraries_response)

    # Media items: a show at top-level
    media_items = [
        {
            "rating_key": "S2",
            "title": "String Show",
            "media_type": "show",
            "play_count": "1",
            "last_played": "1700000000",
        }
    ]

    mock_client.get_library_media_info_all = AsyncMock(return_value=media_items)
    mock_client.get_library_media_info = AsyncMock(return_value={"data": media_items})

    # get_children_metadata returns lists of strings for seasons and episodes
    mock_client.get_children_metadata = AsyncMock(
        side_effect=lambda rk: ["SE2"] if rk == "S2" else ["E3"]
    )

    # When episodes are returned as strings, the collector will call
    # get_library_media_info to fetch episode details (including last_viewed_at)
    # get_library_media_info should return library list when called for the library,
    # and episode details when called with rating_key='E3'. Use side_effect to handle both.
    def lib_media_side_effect(section_id=None, rating_key=None, **kwargs):
        if rating_key == "E3":
            return {
                "data": [
                    {
                        "rating_key": "E3",
                        "media_type": "episode",
                        "title": "E3",
                        "media_index": "1",
                        "last_viewed_at": "1700000000",
                        "section_id": "2",
                        "parent_title": "Season 1",
                        "grandparent_title": "String Show",
                    }
                ]
            }
        return {"data": media_items}

    mock_client.get_library_media_info = AsyncMock(side_effect=lib_media_side_effect)

    async def fake_stats(rating_key, media_type=None, query_days="0"):
        if rating_key in ("E3",):
            return [{"query_days": "0", "total_time": 900}]
        return []

    mock_client.get_item_watch_time_stats = AsyncMock(side_effect=fake_stats)

    collector = WatchTimeCollector(mock_client, max_items=50)

    await collector.collect()

    # Verify episode-specific metric exists for E3
    episode_samples = []
    from tautulli_exporter.metrics import EPISODE_WATCH_SECONDS

    for metric in EPISODE_WATCH_SECONDS.collect():
        for s in metric.samples:
            episode_samples.append((s.name, s.labels, s.value))

    episode_keys = {labels.get("rating_key") for _, labels, _ in episode_samples}
    assert "E3" in episode_keys

    show_samples = []
    for metric in SHOW_WATCH_SECONDS.collect():
        for s in metric.samples:
            show_samples.append((s.name, s.labels, s.value))

    show_keys = {labels.get("show_rating_key") for _, labels, _ in show_samples}
    assert "S2" in show_keys
