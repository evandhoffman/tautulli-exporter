"""Tautulli API client."""

import logging
from typing import Any

import httpx

from .config import Settings

logger = logging.getLogger(__name__)


class TautulliAPIError(Exception):
    """Exception raised for Tautulli API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class TautulliClient:
    """Async client for Tautulli API."""

    def __init__(self, settings: Settings):
        """Initialize the Tautulli client.

        Args:
            settings: Application settings containing URL and API key.
        """
        self.base_url = settings.tautulli_base_url
        self.api_key = settings.tautulli_api_key
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "TautulliClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the HTTP client, creating if necessary."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def _request(self, cmd: str, **params: Any) -> dict[str, Any]:
        """Make a request to the Tautulli API.

        Args:
            cmd: The API command to execute.
            **params: Additional parameters to pass to the API.

        Returns:
            The response data from the API.

        Raises:
            TautulliAPIError: If the API returns an error.
        """
        request_params = {
            "apikey": self.api_key,
            "cmd": cmd,
            **params,
        }

        try:
            response = await self.client.get(
                f"{self.base_url}/api/v2",
                params=request_params,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("response", {}).get("result") == "error":
                error_message = data.get("response", {}).get("message", "Unknown error")
                raise TautulliAPIError(f"API error: {error_message}")

            return data.get("response", {}).get("data", {})

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from Tautulli: {e.response.status_code}")
            raise TautulliAPIError(
                f"HTTP error: {e.response.status_code}",
                status_code=e.response.status_code,
            )
        except httpx.RequestError as e:
            logger.error(f"Request error to Tautulli: {e}")
            raise TautulliAPIError(f"Request error: {e}")

    # =========================================================================
    # Server/Status Methods
    # =========================================================================

    async def get_server_status(self) -> dict[str, Any]:
        """Check if Tautulli is connected to Plex.

        Returns:
            Dict containing 'connected' boolean.
        """
        return await self._request("server_status")

    async def get_server_info(self) -> dict[str, Any]:
        """Get Plex Media Server information.

        Returns:
            Dict containing PMS details (name, version, platform, etc.).
        """
        return await self._request("get_server_info")

    async def get_tautulli_info(self) -> dict[str, Any]:
        """Get Tautulli server information.

        Returns:
            Dict containing Tautulli version, platform, etc.
        """
        return await self._request("get_tautulli_info")

    async def status(self) -> dict[str, Any]:
        """Get Tautulli status.

        Returns:
            Dict containing result and message.
        """
        return await self._request("status")

    # =========================================================================
    # Activity Methods
    # =========================================================================

    async def get_activity(self) -> dict[str, Any]:
        """Get current streaming activity.

        Returns:
            Dict containing stream_count, bandwidth info, and sessions array.
        """
        return await self._request("get_activity")

    # =========================================================================
    # Library Methods
    # =========================================================================

    async def get_libraries(self) -> list[dict[str, Any]]:
        """Get list of all libraries.

        Returns:
            List of library dicts with section_id, name, type, counts.
        """
        return await self._request("get_libraries")

    async def get_library(self, section_id: str) -> dict[str, Any]:
        """Get details for a specific library.

        Args:
            section_id: The library section ID.

        Returns:
            Dict containing library details.
        """
        return await self._request("get_library", section_id=section_id)

    async def get_libraries_table(self) -> dict[str, Any]:
        """Get library statistics table.

        Returns:
            Dict containing library stats including plays and duration.
        """
        return await self._request("get_libraries_table")

    async def get_library_watch_time_stats(
        self, section_id: str, query_days: str = "1,7,30,0"
    ) -> list[dict[str, Any]]:
        """Get watch time statistics for a library.

        Args:
            section_id: The library section ID.
            query_days: Comma-separated days to query (0 = all time).

        Returns:
            List of stats dicts with query_days, total_plays, total_time.
        """
        return await self._request(
            "get_library_watch_time_stats",
            section_id=section_id,
            query_days=query_days,
        )

    # =========================================================================
    # User Methods
    # =========================================================================

    async def get_users(self) -> list[dict[str, Any]]:
        """Get list of all users.

        Returns:
            List of user dicts.
        """
        return await self._request("get_users")

    async def get_user(self, user_id: str) -> dict[str, Any]:
        """Get details for a specific user.

        Args:
            user_id: The Plex user ID.

        Returns:
            Dict containing user details.
        """
        return await self._request("get_user", user_id=user_id)

    async def get_users_table(self) -> dict[str, Any]:
        """Get users statistics table.

        Returns:
            Dict containing user stats including plays and duration.
        """
        return await self._request("get_users_table")

    async def get_user_watch_time_stats(
        self, user_id: str, query_days: str = "1,7,30,0"
    ) -> list[dict[str, Any]]:
        """Get watch time statistics for a user.

        Args:
            user_id: The Plex user ID.
            query_days: Comma-separated days to query (0 = all time).

        Returns:
            List of stats dicts with query_days, total_plays, total_time.
        """
        return await self._request(
            "get_user_watch_time_stats",
            user_id=user_id,
            query_days=query_days,
        )

    # =========================================================================
    # Stats Methods
    # =========================================================================

    async def get_home_stats(
        self,
        time_range: int = 30,
        stats_type: str = "plays",
        stats_count: int = 10,
    ) -> list[dict[str, Any]]:
        """Get homepage watch statistics.

        Args:
            time_range: Number of days to include.
            stats_type: Either 'plays' or 'duration'.
            stats_count: Number of items to return per stat.

        Returns:
            List of stat category dicts.
        """
        return await self._request(
            "get_home_stats",
            time_range=time_range,
            stats_type=stats_type,
            stats_count=stats_count,
        )

    async def get_history(
        self,
        length: int = 25,
        section_id: int | None = None,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """Get play history.

        Args:
            length: Number of history items to return.
            section_id: Optional library section filter.
            user_id: Optional user filter.

        Returns:
            Dict containing recordsTotal and data array.
        """
        params = {"length": length}
        if section_id:
            params["section_id"] = section_id
        if user_id:
            params["user_id"] = user_id
        return await self._request("get_history", **params)

    async def get_library_media_info(
        self,
        section_id: str | None = None,
        rating_key: str | None = None,
        section_type: str | None = None,
        order_column: str | None = None,
        order_dir: str | None = None,
        start: int | None = None,
        length: int | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        """Get the data on the Tautulli media info tables.

        This wraps the `get_library_media_info` API command and accepts
        common filtering parameters.
        """
        params: dict[str, Any] = {}
        if section_id is not None:
            params["section_id"] = section_id
        if rating_key is not None:
            params["rating_key"] = rating_key
        if section_type is not None:
            params["section_type"] = section_type
        if order_column is not None:
            params["order_column"] = order_column
        if order_dir is not None:
            params["order_dir"] = order_dir
        if start is not None:
            params["start"] = start
        if length is not None:
            params["length"] = length
        if search is not None:
            params["search"] = search

        return await self._request("get_library_media_info", **params)

    async def get_library_media_info_all(
        self,
        section_id: str | None = None,
        section_type: str | None = None,
        search: str | None = None,
        page_size: int = 500,
    ) -> list[dict[str, Any]]:
        """Fetch all media info rows for a library, following pagination.

        This helper will iterate over `start` offsets until no more rows are
        returned. It returns a flat list of media item dicts.
        """
        start = 0
        all_items: list[dict[str, Any]] = []

        while True:
            resp = await self.get_library_media_info(
                section_id=section_id,
                section_type=section_type,
                search=search,
                start=start,
                length=page_size,
            )

            # Response is expected to be a dict with 'data' list
            items = resp.get("data", []) if isinstance(resp, dict) else (resp or [])
            if not items:
                break

            all_items.extend(items)

            if len(items) < page_size:
                break

            start += page_size

        return all_items

    async def get_item_watch_time_stats(
        self, rating_key: str, media_type: str | None = None, query_days: str = "0"
    ) -> list[dict[str, Any]]:
        """Get watch time stats for a media item (episode/show).

        Args:
            rating_key: Rating key of the item.
            media_type: Optional media type for collection items.
            query_days: Comma-separated days to query (default "0" for all time).

        Returns:
            List of stats dicts with query_days, total_plays, total_time.
        """
        params: dict[str, Any] = {"rating_key": rating_key, "query_days": query_days}
        if media_type is not None:
            params["media_type"] = media_type
        return await self._request("get_item_watch_time_stats", **params)

    async def get_children_metadata(self, rating_key: str) -> list[dict[str, Any]]:
        """Get children metadata for a media item (e.g., seasons for a show, episodes for a season).

        Args:
            rating_key: Rating key of the parent item.

        Returns:
            List of child item dicts.
        """
        return await self._request("get_children_metadata", rating_key=rating_key)
