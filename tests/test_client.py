"""Tests for the Tautulli API client."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from tautulli_exporter.tautulli_client import TautulliClient, TautulliAPIError


class TestTautulliClient:
    """Tests for TautulliClient."""

    @pytest.mark.asyncio
    async def test_get_activity_success(self, mock_client, sample_activity_response):
        """Test successful get_activity call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": {"result": "success", "data": sample_activity_response}
        }
        mock_response.raise_for_status = MagicMock()

        mock_client._client.get = AsyncMock(return_value=mock_response)

        result = await mock_client.get_activity()

        assert result["stream_count"] == "2"
        assert len(result["sessions"]) == 2

    @pytest.mark.asyncio
    async def test_get_libraries_success(self, mock_client, sample_libraries_response):
        """Test successful get_libraries call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": {"result": "success", "data": sample_libraries_response}
        }
        mock_response.raise_for_status = MagicMock()

        mock_client._client.get = AsyncMock(return_value=mock_response)

        result = await mock_client.get_libraries()

        assert len(result) == 2
        assert result[0]["section_name"] == "Movies"

    @pytest.mark.asyncio
    async def test_api_error_handling(self, mock_client):
        """Test API error response handling."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": {"result": "error", "message": "Invalid API key"}
        }
        mock_response.raise_for_status = MagicMock()

        mock_client._client.get = AsyncMock(return_value=mock_response)

        with pytest.raises(TautulliAPIError) as exc_info:
            await mock_client.get_activity()

        assert "Invalid API key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_http_error_handling(self, mock_client):
        """Test HTTP error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )

        mock_client._client.get = AsyncMock(return_value=mock_response)

        with pytest.raises(TautulliAPIError) as exc_info:
            await mock_client.get_activity()

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, mock_client):
        """Test connection error handling."""
        mock_client._client.get = AsyncMock(
            side_effect=httpx.RequestError("Connection failed", request=MagicMock())
        )

        with pytest.raises(TautulliAPIError) as exc_info:
            await mock_client.get_activity()

        assert "Request error" in str(exc_info.value)
