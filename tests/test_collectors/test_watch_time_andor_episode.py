import pytest
from unittest.mock import AsyncMock

from tautulli_exporter.collectors.watch_time import WatchTimeCollector
from tautulli_exporter.metrics import EPISODE_WATCH_SECONDS

from tests.mock_tautulli_app import LIBRARY_MEDIA


@pytest.mark.asyncio
async def test_andor_episode_watch_time(mock_client, sample_libraries_response):
    # Setup: Andor (rating_key=2973) already in test mock LIBRARY_MEDIA
    mock_client.get_libraries = AsyncMock(return_value=sample_libraries_response)

    # Return Andor show from library media info
    media_items = [
        m for m in LIBRARY_MEDIA.get("2", []) if m.get("rating_key") == "2973"
    ]
    mock_client.get_library_media_info_all = AsyncMock(return_value=media_items)
    mock_client.get_library_media_info = AsyncMock(
        return_value={"data": {"data": media_items}}
    )

    # children and stats are handled by tests.mock_tautulli_app data via previous tests
    async def fake_children(rk):
        # Return the inner data shape that TautulliClient._request would return
        from tests.mock_tautulli_app import SEASONS, EPISODES

        if rk in SEASONS:
            return {"children_list": SEASONS[rk]}
        if rk in EPISODES:
            return {"children_list": EPISODES[rk]}
        return []

    async def fake_stats(rating_key, media_type=None, query_days="0"):
        from tests.mock_tautulli_app import WATCH_STATS

        return WATCH_STATS.get(rating_key, [])

    mock_client.get_children_metadata = AsyncMock(side_effect=fake_children)
    # Instead of mocking get_children_metadata intricately again, let the real mock app be validated via earlier integration test

    mock_client.get_item_watch_time_stats = AsyncMock(side_effect=fake_stats)

    collector = WatchTimeCollector(mock_client, max_items=50)

    await collector.collect()

    # Find EPISODE_WATCH_SECONDS for rating_key '2980'
    episode_samples = []
    for metric in EPISODE_WATCH_SECONDS.collect():
        for s in metric.samples:
            episode_samples.append((s.name, s.labels, s.value))

    keys = {labels.get("rating_key"): value for _, labels, value in episode_samples}
    assert "2980" in keys
    assert int(keys["2980"]) == 2871
