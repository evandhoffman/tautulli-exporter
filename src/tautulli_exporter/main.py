"""Main entry point for Tautulli Prometheus Exporter."""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .collectors import (
    ActivityCollector,
    LibraryCollector,
    ServerCollector,
    UserCollector,
    WatchTimeCollector,
)
from .config import Settings, get_settings
from .metrics import EXPORTER_UP
from .tautulli_client import TautulliClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class TautulliExporter:
    """Main exporter class that manages collectors and the API client."""

    def __init__(self, settings: Settings):
        """Initialize the exporter.

        Args:
            settings: Application settings.
        """
        self.settings = settings
        self.client = TautulliClient(settings)
        self._collectors = self._init_collectors()
        self._background_tasks: list[asyncio.Task] = []

    def _init_collectors(self) -> list:
        """Initialize all collectors.

        Returns:
            List of collector instances.
        """
        collectors = [
            ServerCollector(self.client),
            ActivityCollector(self.client),
        ]

        if self.settings.collect_library_stats:
            collectors.append(LibraryCollector(self.client))

        if self.settings.collect_user_stats:
            collectors.append(UserCollector(self.client))

        if self.settings.collect_watch_time_stats:
            collectors.append(
                WatchTimeCollector(
                    self.client, max_items=self.settings.watch_time_max_items
                )
            )

        return collectors

    async def collect_all(self) -> None:
        """Run all collectors."""
        for collector in self._collectors:
            await collector.safe_collect()

    async def start_background_collection(self) -> None:
        """Start background collection tasks."""
        # Activity collection (high frequency)
        activity_task = asyncio.create_task(
            self._collection_loop(
                [c for c in self._collectors if c.name == "activity"],
                self.settings.activity_collection_interval,
            )
        )
        self._background_tasks.append(activity_task)

        # Stats collection (lower frequency)
        stats_collectors = [
            c
            for c in self._collectors
            if c.name in ("server", "libraries", "users", "watch_time")
        ]
        if stats_collectors:
            stats_task = asyncio.create_task(
                self._collection_loop(
                    stats_collectors,
                    self.settings.stats_collection_interval,
                )
            )
            self._background_tasks.append(stats_task)

    async def _collection_loop(self, collectors: list, interval: int) -> None:
        """Run collection loop for a set of collectors.

        Args:
            collectors: List of collectors to run.
            interval: Collection interval in seconds.
        """
        while True:
            for collector in collectors:
                try:
                    await collector.safe_collect()
                except Exception as e:
                    logger.error(f"Collection error in {collector.name}: {e}")

            await asyncio.sleep(interval)

    async def stop(self) -> None:
        """Stop all background tasks."""
        for task in self._background_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


# Global exporter instance
exporter: TautulliExporter | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager."""
    global exporter

    settings = get_settings()

    # Configure logging level
    level = getattr(logging, settings.log_level, logging.INFO)
    logging.getLogger().setLevel(level)
    # Ensure existing handlers respect the configured level (uvicorn may reconfigure handlers)
    for h in logging.getLogger().handlers:
        try:
            h.setLevel(level)
        except Exception:
            pass
    logger.debug(f"Logging level set to {settings.log_level} ({level})")

    logger.info(f"Starting Tautulli Exporter v0.1.0")
    logger.info(f"Connecting to Tautulli at {settings.tautulli_base_url}")

    # Initialize exporter
    exporter = TautulliExporter(settings)

    # Enter async context for the client
    await exporter.client.__aenter__()

    # Initial collection
    try:
        await exporter.collect_all()
        logger.info("Initial metrics collection complete")
    except Exception as e:
        logger.error(f"Initial collection failed: {e}")
        EXPORTER_UP.set(0)

    # Start background collection
    await exporter.start_background_collection()

    yield

    # Cleanup
    logger.info("Shutting down Tautulli Exporter")
    if exporter:
        await exporter.stop()
        await exporter.client.__aexit__(None, None, None)


# Create FastAPI app
app = FastAPI(
    title="Tautulli Prometheus Exporter",
    description="Prometheus metrics exporter for Tautulli/Plex",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root() -> dict:
    """Root endpoint with basic info."""
    return {
        "name": "Tautulli Prometheus Exporter",
        "version": "0.1.0",
        "endpoints": {
            "metrics": "/metrics",
            "health": "/health",
        },
    }


def main() -> None:
    """Main entry point."""
    settings = get_settings()

    uvicorn.run(
        "tautulli_exporter.main:app",
        host=settings.exporter_host,
        port=settings.exporter_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
