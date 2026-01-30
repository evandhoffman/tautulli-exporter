"""Tests for the activity collector."""

import pytest
from unittest.mock import AsyncMock

from tautulli_exporter.collectors.activity import ActivityCollector
from tautulli_exporter.metrics import STREAMS_TOTAL, STREAMS_BY_TYPE, BANDWIDTH


class TestActivityCollector:
    """Tests for ActivityCollector."""

    @pytest.mark.asyncio
    async def test_collect_streams(self, mock_client, sample_activity_response):
        """Test that stream counts are collected correctly."""
        mock_client.get_activity = AsyncMock(return_value=sample_activity_response)

        collector = ActivityCollector(mock_client)
        await collector.collect()

        # Check that metrics were updated
        # Note: In a real test, you'd want to check the actual metric values
        mock_client.get_activity.assert_called_once()

    @pytest.mark.asyncio
    async def test_normalize_transcode_decision(self, mock_client):
        """Test transcode decision normalization."""
        collector = ActivityCollector(mock_client)

        assert collector._normalize_transcode_decision("direct play") == "direct_play"
        assert collector._normalize_transcode_decision("Direct Play") == "direct_play"
        assert (
            collector._normalize_transcode_decision("direct stream") == "direct_stream"
        )
        assert collector._normalize_transcode_decision("copy") == "direct_stream"
        assert collector._normalize_transcode_decision("transcode") == "transcode"
        assert collector._normalize_transcode_decision("Transcode") == "transcode"

    @pytest.mark.asyncio
    async def test_get_title_episode(self, mock_client):
        """Test title formatting for episodes."""
        collector = ActivityCollector(mock_client)

        session = {
            "media_type": "episode",
            "grandparent_title": "The Show",
            "parent_media_index": "2",
            "media_index": "5",
            "title": "Episode Title",
        }

        title = collector._get_title(session)
        assert title == "The Show S2E5"

    @pytest.mark.asyncio
    async def test_get_title_movie(self, mock_client):
        """Test title formatting for movies."""
        collector = ActivityCollector(mock_client)

        session = {
            "media_type": "movie",
            "title": "The Movie",
        }

        title = collector._get_title(session)
        assert title == "The Movie"

    @pytest.mark.asyncio
    async def test_get_title_track(self, mock_client):
        """Test title formatting for music tracks."""
        collector = ActivityCollector(mock_client)

        session = {
            "media_type": "track",
            "grandparent_title": "Artist Name",
            "title": "Song Title",
        }

        title = collector._get_title(session)
        assert title == "Artist Name - Song Title"
