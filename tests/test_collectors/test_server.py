"""Tests for the server collector."""

import pytest
from unittest.mock import AsyncMock

from tautulli_exporter.collectors.server import ServerCollector


class TestServerCollector:
    """Tests for ServerCollector."""

    @pytest.mark.asyncio
    async def test_collect_server_status(
        self,
        mock_client,
        sample_server_status_response,
        sample_tautulli_info_response,
        sample_server_info_response,
    ):
        """Test that server status is collected correctly."""
        mock_client.get_server_status = AsyncMock(
            return_value=sample_server_status_response
        )
        mock_client.get_tautulli_info = AsyncMock(
            return_value=sample_tautulli_info_response
        )
        mock_client.get_server_info = AsyncMock(
            return_value=sample_server_info_response
        )

        collector = ServerCollector(mock_client)
        await collector.collect()

        mock_client.get_server_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_info_collected_once(
        self,
        mock_client,
        sample_server_status_response,
        sample_tautulli_info_response,
        sample_server_info_response,
    ):
        """Test that info metrics are only collected once."""
        mock_client.get_server_status = AsyncMock(
            return_value=sample_server_status_response
        )
        mock_client.get_tautulli_info = AsyncMock(
            return_value=sample_tautulli_info_response
        )
        mock_client.get_server_info = AsyncMock(
            return_value=sample_server_info_response
        )

        collector = ServerCollector(mock_client)

        # First collection
        await collector.collect()
        assert mock_client.get_tautulli_info.call_count == 1
        assert mock_client.get_server_info.call_count == 1

        # Second collection - info should not be fetched again
        await collector.collect()
        assert mock_client.get_tautulli_info.call_count == 1
        assert mock_client.get_server_info.call_count == 1
