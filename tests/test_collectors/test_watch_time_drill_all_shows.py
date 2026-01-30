import pytest
from unittest.mock import AsyncMock

from tautulli_exporter.collectors.watch_time import WatchTimeCollector
from tautulli_exporter.metrics import EPISODE_WATCH_SECONDS


@pytest.mark.asyncio
async def test_drill_all_shows_enabled(
    mock_client, sample_libraries_response, monkeypatch
):
    # Show has no last_played but we enable drilling
    media_items = [
        {
            "rating_key": "S5",
            "title": "Drill Show",
            "media_type": "show",
            "play_count": "0",
            "last_played": None,
        }
    ]

    mock_client.get_libraries = AsyncMock(return_value=sample_libraries_response)
    mock_client.get_library_media_info_all = AsyncMock(return_value=media_items)
    mock_client.get_library_media_info = AsyncMock(return_value={"data": media_items})

    mock_client.get_children_metadata = AsyncMock(
        side_effect=lambda rk: (
            [{"rating_key": "SE5", "title": "Season 1"}]
            if rk == "S5"
            else [
                {
                    "rating_key": "E6",
                    "title": "Episode 6",
                    "media_type": "episode",
                    "last_viewed_at": "1700000000",
                }
            ]
        )
    )

    async def fake_stats(rating_key, media_type=None, query_days="0"):
        if rating_key == "E6":
            return [{"query_days": "0", "total_time": 700}]
        return []

    mock_client.get_item_watch_time_stats = AsyncMock(side_effect=fake_stats)

    # Monkeypatch get_settings to enable drill_all
    class DummySettings:
        watch_time_drill_all_shows = True

    # Patch the config provider used by the collector
    import tautulli_exporter.config as cfg

    monkeypatch.setattr(cfg, "get_settings", lambda: DummySettings())

    collector = WatchTimeCollector(mock_client, max_items=50)

    await collector.collect()

    episode_samples = []
    for metric in EPISODE_WATCH_SECONDS.collect():
        for s in metric.samples:
            episode_samples.append((s.name, s.labels, s.value))

    keys = {labels.get("rating_key") for _, labels, _ in episode_samples}
    assert "E6" in keys
