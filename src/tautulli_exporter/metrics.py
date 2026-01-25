"""Prometheus metric definitions for Tautulli Exporter."""

from prometheus_client import Counter, Gauge, Info

# =============================================================================
# Info Metrics
# =============================================================================

TAUTULLI_INFO = Info(
    "tautulli",
    "Tautulli server information",
)

PMS_INFO = Info(
    "tautulli_pms",
    "Plex Media Server information",
)

# =============================================================================
# Server Status Metrics
# =============================================================================

EXPORTER_UP = Gauge(
    "tautulli_up",
    "Whether the Tautulli exporter is up and able to connect to Tautulli",
)

SERVER_CONNECTED = Gauge(
    "tautulli_server_connected",
    "Whether Tautulli is connected to the Plex Media Server",
)

# =============================================================================
# Activity Metrics (Real-time)
# =============================================================================

STREAMS_TOTAL = Gauge(
    "tautulli_streams_count",
    "Current number of active streams",
)

STREAMS_BY_TYPE = Gauge(
    "tautulli_streams_by_type",
    "Current number of streams by transcode decision",
    ["type"],  # direct_play, direct_stream, transcode
)

BANDWIDTH = Gauge(
    "tautulli_bandwidth_kbps",
    "Current bandwidth usage in Kbps",
    ["location"],  # total, wan, lan
)

# Per-stream info metric (using gauge with labels)
STREAM_INFO = Gauge(
    "tautulli_stream_info",
    "Information about active streams (value is always 1)",
    [
        "user",
        "media_type",
        "title",
        "state",
        "transcode_decision",
        "platform",
        "player",
        "quality",
        "library",
        "location",
    ],
)

STREAM_PROGRESS = Gauge(
    "tautulli_stream_progress_percent",
    "Progress of active streams as percentage",
    ["user", "title"],
)

STREAM_DURATION = Gauge(
    "tautulli_stream_duration_seconds",
    "Duration of the media being streamed",
    ["user", "title"],
)

# =============================================================================
# Library Metrics
# =============================================================================

LIBRARY_ITEMS = Gauge(
    "tautulli_library_items_count",
    "Number of items in library",
    ["library_name", "library_type", "level"],  # level: total, parent, child
)

LIBRARY_SIZE_BYTES = Gauge(
    "tautulli_library_size_bytes",
    "Total size of library in bytes",
    ["library_name", "library_type"],
)

LIBRARY_PLAYS = Gauge(
    "tautulli_library_plays_total",
    "Total plays for library",
    ["library_name"],
)

LIBRARY_DURATION = Gauge(
    "tautulli_library_watch_duration_seconds",
    "Total watch duration for library",
    ["library_name"],
)

# =============================================================================
# User Metrics
# =============================================================================

USERS_TOTAL = Gauge(
    "tautulli_users_count",
    "Total number of users",
)

USERS_ACTIVE = Gauge(
    "tautulli_users_active_count",
    "Number of active users",
)

USER_PLAYS = Gauge(
    "tautulli_user_plays_total",
    "Total plays for user",
    ["user"],
)

USER_DURATION = Gauge(
    "tautulli_user_watch_duration_seconds",
    "Total watch duration for user",
    ["user"],
)

USER_LAST_SEEN = Gauge(
    "tautulli_user_last_seen_timestamp",
    "Timestamp of user's last activity",
    ["user"],
)

# =============================================================================
# Item / Show watch time
# =============================================================================

ITEM_WATCH_SECONDS = Gauge(
    "tautulli_item_watch_seconds",
    "Total seconds watched for a media item (episodes/shows)",
    ["rating_key", "title", "media_type", "library_name"],
)

SHOW_WATCH_SECONDS = Gauge(
    "tautulli_show_watch_seconds",
    "Total seconds watched aggregated per show or movie",
    ["show_rating_key", "show_title", "media_type", "library_name"],
)

# =============================================================================
# Scrape Metrics
# =============================================================================

SCRAPE_DURATION = Gauge(
    "tautulli_scrape_duration_seconds",
    "Duration of the last scrape",
    ["collector"],
)

SCRAPE_ERRORS = Counter(
    "tautulli_scrape_errors_total",
    "Total number of scrape errors",
    ["collector"],
)
