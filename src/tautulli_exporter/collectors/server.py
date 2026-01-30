"""Server status and info collector."""

import logging

from ..metrics import EXPORTER_UP, PMS_INFO, SERVER_CONNECTED, TAUTULLI_INFO
from ..tautulli_client import TautulliClient
from .base import BaseCollector

logger = logging.getLogger(__name__)


class ServerCollector(BaseCollector):
    """Collector for server status and info metrics."""

    name = "server"

    def __init__(self, client: TautulliClient):
        """Initialize the server collector."""
        super().__init__(client)
        self._tautulli_info_set = False
        self._pms_info_set = False

    async def collect(self) -> None:
        """Collect server status and info metrics."""
        # Check server connection status
        try:
            status = await self.client.get_server_status()
            connected = status.get("connected", False)
            SERVER_CONNECTED.set(1 if connected else 0)
            EXPORTER_UP.set(1)
        except Exception as e:
            logger.error(f"Failed to get server status: {e}")
            SERVER_CONNECTED.set(0)
            EXPORTER_UP.set(0)
            raise

        # Collect Tautulli info (only once, it's static)
        if not self._tautulli_info_set:
            await self._collect_tautulli_info()

        # Collect PMS info (only once, it's static)
        if not self._pms_info_set:
            await self._collect_pms_info()

    async def _collect_tautulli_info(self) -> None:
        """Collect Tautulli server information."""
        try:
            info = await self.client.get_tautulli_info()
            TAUTULLI_INFO.info(
                {
                    "version": info.get("tautulli_version", "unknown"),
                    "branch": info.get("tautulli_branch", "unknown"),
                    "platform": info.get("tautulli_platform", "unknown"),
                    "python_version": info.get("tautulli_python_version", "unknown"),
                }
            )
            self._tautulli_info_set = True
            logger.info(f"Tautulli version: {info.get('tautulli_version', 'unknown')}")
        except Exception as e:
            logger.warning(f"Failed to get Tautulli info: {e}")

    async def _collect_pms_info(self) -> None:
        """Collect Plex Media Server information."""
        try:
            info = await self.client.get_server_info()
            PMS_INFO.info(
                {
                    "name": info.get("pms_name", "unknown"),
                    "version": info.get("pms_version", "unknown"),
                    "platform": info.get("pms_platform", "unknown"),
                    "ip": info.get("pms_ip", "unknown"),
                }
            )
            self._pms_info_set = True
            logger.info(f"Plex server: {info.get('pms_name', 'unknown')}")
        except Exception as e:
            logger.warning(f"Failed to get PMS info: {e}")
