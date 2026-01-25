"""Base collector class for Tautulli metrics."""

import logging
import time
from abc import ABC, abstractmethod

from ..metrics import SCRAPE_DURATION, SCRAPE_ERRORS
from ..tautulli_client import TautulliClient

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """Base class for metric collectors."""

    name: str = "base"

    def __init__(self, client: TautulliClient):
        """Initialize the collector.

        Args:
            client: Tautulli API client instance.
        """
        self.client = client

    @abstractmethod
    async def collect(self) -> None:
        """Collect and update metrics.

        This method should be implemented by subclasses to fetch data
        from Tautulli and update the relevant Prometheus metrics.
        """
        pass

    async def safe_collect(self) -> bool:
        """Safely collect metrics with error handling and timing.

        Returns:
            True if collection succeeded, False otherwise.
        """
        start_time = time.time()
        try:
            await self.collect()
            duration = time.time() - start_time
            SCRAPE_DURATION.labels(collector=self.name).set(duration)
            logger.debug(f"Collector {self.name} completed in {duration:.3f}s")
            return True
        except Exception as e:
            SCRAPE_ERRORS.labels(collector=self.name).inc()
            logger.error(f"Error in collector {self.name}: {e}")
            return False
