import pytest
from unittest.mock import AsyncMock

from tautulli_exporter.collectors.watch_time import WatchTimeCollector
from tautulli_exporter.metrics import EPISODE_WATCH_SECONDS

from tests.mock_tautulli_app import LIBRARY_MEDIA, SEASONS, EPISODES, WATCH_STATS


@pytest.mark.asyncio
async def test_episode_metric_labels_and_value(mock_client, sample_libraries_response):
    # Setup: Andor (rating_key=2973) already in test mock LIBRARY_MEDIA
    mock_client.get_libraries = AsyncMock(return_value=sample_libraries_response)

    # Return Andor show from library media info
    media_items = [
        m for m in LIBRARY_MEDIA.get("2", []) if m.get("rating_key") == "2973"
    ]
    mock_client.get_library_media_info = AsyncMock(
        return_value={"data": {"data": media_items}}
    )

    # children and stats provided by our mock app data
    async def fake_children(rk):
        if rk in SEASONS:
            return {"children_list": SEASONS[rk]}
        if rk in EPISODES:
            return {"children_list": EPISODES[rk]}
        return {"children_list": []}

    async def fake_stats(rating_key, media_type=None, query_days="0"):
        return WATCH_STATS.get(rating_key, [])

    mock_client.get_children_metadata = AsyncMock(side_effect=fake_children)
    mock_client.get_item_watch_time_stats = AsyncMock(side_effect=fake_stats)

    collector = WatchTimeCollector(mock_client, max_items=50)
    await collector.collect()

    # Find the episode metric for rating_key '2980'
    episode_samples = []
    for metric in EPISODE_WATCH_SECONDS.collect():
        for s in metric.samples:
            episode_samples.append((s.name, s.labels, s.value))

    # Find the sample that matches all expected labels for rating_key '2980'
    expected = {
        "library_name": "TV Shows",
        "rating_key": "2980",
        "title": "Kassa",
        "parent_title": "Season 1",
        "grandparent_title": "Andor",
        "media_index": "1",
        "section_id": "2",
    }

    found = None
    for _, labels, value in episode_samples:
        match = True
        for k, v in expected.items():
            if labels.get(k) != v:
                match = False
                break
        if match:
            found = (labels, value)
            break

    assert (
        found is not None
    ), f"Expected to find EPISODE_WATCH_SECONDS matching {expected}"

    labels, value = found
    assert int(value) == 2871
