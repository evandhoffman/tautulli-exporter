"""Test configuration and fixtures."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from tautulli_exporter.config import Settings
from tautulli_exporter.tautulli_client import TautulliClient


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        tautulli_url="http://localhost:8181",
        tautulli_api_key="test-api-key",
        exporter_port=9487,
        log_level="DEBUG",
    )


@pytest.fixture
def mock_client(settings):
    """Create a mock Tautulli client."""
    client = TautulliClient(settings)
    client._client = AsyncMock()
    return client


@pytest.fixture
def sample_activity_response():
    """Sample get_activity API response."""
    return {
        "stream_count": "2",
        "stream_count_direct_play": 1,
        "stream_count_direct_stream": 0,
        "stream_count_transcode": 1,
        "total_bandwidth": 25000,
        "wan_bandwidth": 10000,
        "lan_bandwidth": 15000,
        "sessions": [
            {
                "session_key": "1",
                "user": "testuser",
                "friendly_name": "Test User",
                "username": "testuser",
                "media_type": "episode",
                "title": "Test Episode",
                "grandparent_title": "Test Show",
                "parent_media_index": "1",
                "media_index": "5",
                "full_title": "Test Show - Test Episode",
                "state": "playing",
                "transcode_decision": "direct play",
                "platform": "Chrome",
                "player": "Plex Web",
                "quality_profile": "Original",
                "library_name": "TV Shows",
                "location": "lan",
                "progress_percent": "45",
                "duration": "2700000",
            },
            {
                "session_key": "2",
                "user": "anotheruser",
                "friendly_name": "Another User",
                "username": "anotheruser",
                "media_type": "movie",
                "title": "Test Movie",
                "full_title": "Test Movie",
                "state": "paused",
                "transcode_decision": "transcode",
                "platform": "iOS",
                "player": "Plex for iOS",
                "quality_profile": "4 Mbps 720p",
                "library_name": "Movies",
                "location": "wan",
                "progress_percent": "72",
                "duration": "7200000",
            },
        ],
    }


@pytest.fixture
def sample_libraries_response():
    """Sample get_libraries API response."""
    return [
        {
            "section_id": "1",
            "section_name": "Movies",
            "section_type": "movie",
            "count": 500,
            "parent_count": None,
            "child_count": None,
            "is_active": 1,
        },
        {
            "section_id": "2",
            "section_name": "TV Shows",
            "section_type": "show",
            "count": 100,
            "parent_count": 500,
            "child_count": 5000,
            "is_active": 1,
        },
    ]


@pytest.fixture
def sample_users_response():
    """Sample get_users API response."""
    return [
        {
            "user_id": "1",
            "username": "admin",
            "friendly_name": "Admin User",
            "is_active": 1,
            "is_admin": 1,
        },
        {
            "user_id": "2",
            "username": "testuser",
            "friendly_name": "Test User",
            "is_active": 1,
            "is_admin": 0,
        },
        {
            "user_id": "3",
            "username": "inactive",
            "friendly_name": "Inactive User",
            "is_active": 0,
            "is_admin": 0,
        },
    ]


@pytest.fixture
def sample_server_status_response():
    """Sample server_status API response."""
    return {"connected": True}


@pytest.fixture
def sample_tautulli_info_response():
    """Sample get_tautulli_info API response."""
    return {
        "tautulli_version": "v2.13.0",
        "tautulli_branch": "master",
        "tautulli_platform": "Linux",
        "tautulli_python_version": "3.11.0",
    }


@pytest.fixture
def sample_server_info_response():
    """Sample get_server_info API response."""
    return {
        "pms_name": "Test Plex Server",
        "pms_version": "1.32.0.1234",
        "pms_platform": "Linux",
        "pms_ip": "192.168.1.100",
        "pms_port": 32400,
        "pms_ssl": 0,
    }
