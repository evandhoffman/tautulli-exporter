import pytest
import httpx
from fastapi import FastAPI
from tautulli_exporter.tautulli_client import TautulliClient
from tautulli_exporter.collectors.watch_time import WatchTimeCollector
from tautulli_exporter.metrics import EPISODE_WATCH_SECONDS

from tests.mock_tautulli_app import (
    app as mock_app,
    LIBRARIES,
    LIBRARY_MEDIA,
    SEASONS,
    EPISODES,
    WATCH_STATS,
)


@pytest.mark.asyncio
async def test_watch_time_integration_with_mock_app(monkeypatch):
    # Create a TautulliClient and use httpx AsyncClient bound to the ASGI app
    from tautulli_exporter.config import Settings

    settings = Settings(
        tautulli_url="http://testserver",
        tautulli_api_key="test-api-key",
        exporter_port=9487,
        log_level="DEBUG",
    )

    client = TautulliClient(settings)

    # Use an AsyncClient that routes to the FastAPI app in process
    # Use httpx MockTransport to stub requests for the collector
    from httpx import MockTransport, Response

    def handler(request: httpx.Request) -> Response:
        q = request.url.params
        cmd = q.get("cmd")
        if cmd == "get_libraries":
            return Response(
                200, json={"response": {"result": "success", "data": LIBRARIES}}
            )
        if cmd == "get_library_media_info":
            section_id = q.get("section_id")
            data = LIBRARY_MEDIA.get(str(section_id), [])
            return Response(
                200, json={"response": {"result": "success", "data": {"data": data}}}
            )
        if cmd == "get_children_metadata":
            rating_key = q.get("rating_key")
            if rating_key in SEASONS:
                return Response(
                    200,
                    json={
                        "response": {"result": "success", "data": SEASONS[rating_key]}
                    },
                )
            if rating_key in EPISODES:
                return Response(
                    200,
                    json={
                        "response": {"result": "success", "data": EPISODES[rating_key]}
                    },
                )
            return Response(200, json={"response": {"result": "success", "data": []}})
        if cmd == "get_item_watch_time_stats":
            rating_key = q.get("rating_key")
            return Response(
                200,
                json={
                    "response": {
                        "result": "success",
                        "data": WATCH_STATS.get(rating_key, []),
                    }
                },
            )
        return Response(
            400, json={"response": {"result": "error", "message": "Unknown cmd"}}
        )

    transport = MockTransport(handler)
    asgi_client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    client._client = asgi_client

    collector = WatchTimeCollector(client, max_items=100)

    # Run collection
    await collector.collect()

    # Assert episode metrics exist for E100 and E101
    episode_samples = []
    for metric in EPISODE_WATCH_SECONDS.collect():
        for s in metric.samples:
            episode_samples.append((s.name, s.labels, s.value))

    keys = {labels.get("rating_key") for _, labels, _ in episode_samples}
    assert "E100" in keys
    assert "E101" in keys

    # Also verify show-level aggregates were set
    found_show = any(
        s.labels.get("show_rating_key") == "S100"
        for metric in EPISODE_WATCH_SECONDS.collect()
        for s in metric.samples
    )
    assert not found_show  # EPISODE metrics should have episode labels, not show labels

    # Cleanup
    await asgi_client.aclose()
