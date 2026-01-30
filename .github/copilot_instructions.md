# Tautulli Prometheus Exporter - Copilot Instructions

## Project Overview
This is a **containerized Python application** that exports Plex/Tautulli metrics to Prometheus.

### Technology Stack
- **Language**: Python 3.11+
- **Web Framework**: Flask or FastAPI (for `/metrics` endpoint)
- **Prometheus Client**: `prometheus_client` library
- **HTTP Client**: `requests` or `httpx` (async)
- **Containerization**: Docker with multi-stage builds
- **Configuration**: Environment variables

---

## Project Structure

```
tautulli-exporter/
├── .github/
│   └── copilot_instructions.md
├── docs/
│   └── tautulli_api.md
├── src/
│   └── tautulli_exporter/
│       ├── __init__.py
│       ├── main.py              # Entry point, web server
│       ├── config.py            # Configuration management
│       ├── tautulli_client.py   # Tautulli API client
│       ├── collectors/
│       │   ├── __init__.py
│       │   ├── base.py          # Base collector class
│       │   ├── activity.py      # Real-time activity metrics
│       │   ├── libraries.py     # Library statistics
│       │   ├── users.py         # User statistics
│       │   └── server.py        # Server/system metrics
│       └── metrics.py           # Prometheus metric definitions
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_client.py
│   ├── test_collectors/
│   │   └── ...
│   └── fixtures/
│       └── *.json               # Sample API responses
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
├── README.md
└── .env.example
```

---

## Configuration (Environment Variables)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TAUTULLI_URL` | Yes | - | Tautulli base URL (e.g., `http://tautulli:8181`) |
| `TAUTULLI_API_KEY` | Yes | - | Tautulli API key |
| `EXPORTER_PORT` | No | `9487` | Port for metrics endpoint |
| `EXPORTER_HOST` | No | `0.0.0.0` | Host to bind to |
| `SCRAPE_INTERVAL` | No | `30` | Seconds between metric collection |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARN, ERROR) |
| `COLLECT_USER_STATS` | No | `true` | Enable per-user metrics |
| `COLLECT_LIBRARY_STATS` | No | `true` | Enable per-library metrics |
| `COLLECT_WATCH_TIME_STATS` | No | `true` | Enable per-item watch-time metrics (may be API-heavy) |
| `WATCH_TIME_MAX_ITEMS` | No | `500` | Maximum items to query when collecting watch-time stats |

---

## Metrics Implementation

### Metric Naming Convention
Follow Prometheus naming conventions:
- Prefix: `tautulli_`
- Use snake_case
- Include unit in name (e.g., `_seconds`, `_bytes`, `_total`)
- Counters end with `_total`

### Core Metrics to Implement

```python
# Gauge metrics (current state)
tautulli_up                           # Exporter health (1=up, 0=down)
tautulli_server_connected             # Plex connection status
tautulli_streams_count                # Current active streams
tautulli_streams_by_type{type}        # Streams by transcode decision
tautulli_bandwidth_kbps{location}     # Bandwidth by location
tautulli_library_items_count{name,type}  # Library item counts
tautulli_users_count                  # Total user count

# Info metrics (metadata as labels)
tautulli_info{version,platform}       # Tautulli version
tautulli_pms_info{name,version}       # Plex server info

# Counter metrics (cumulative)
tautulli_plays_total{library,type}    # Total plays
tautulli_watch_seconds_total{library} # Total watch time

```

### Stream Detail Metrics (per-session labels)
```python
tautulli_stream_info{
    user,
    media_type,      # movie, episode, track
    state,           # playing, paused, buffering
    transcode,       # direct_play, direct_stream, transcode
    platform,
    player,
    quality,
    library,
    location         # lan, wan
}
```

---

## Code Style & Patterns

### Async Preferred
Use `httpx` with async for better performance:
```python
import httpx

class TautulliClient:
    async def get_activity(self) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v2",
                params={"apikey": self.api_key, "cmd": "get_activity"}
            )
            return response.json()["response"]["data"]
```

### Collector Pattern
```python
from prometheus_client import Gauge

class ActivityCollector:
    def __init__(self, client: TautulliClient):
        self.client = client
        self.streams_gauge = Gauge(
            'tautulli_streams_count',
            'Current active streams'
        )
    
    async def collect(self):
        data = await self.client.get_activity()
        self.streams_gauge.set(data.get('stream_count', 0))
```

### Error Handling
- Always catch API errors gracefully
- Set `tautulli_up` to 0 on failure
- Log errors but don't crash the exporter
- Implement exponential backoff for retries

### Caching Strategy
```python
from functools import lru_cache
from time import time

class CachedCollector:
    def __init__(self, ttl_seconds: int = 300):
        self._cache = {}
        self._ttl = ttl_seconds
    
    async def get_cached(self, key: str, fetch_func):
        now = time()
        if key in self._cache:
            value, timestamp = self._cache[key]
            if now - timestamp < self._ttl:
                return value
        
        value = await fetch_func()
        self._cache[key] = (value, now)
        return value
```

---

## Docker Configuration

### Dockerfile Pattern
```dockerfile
# Build stage
FROM python:3.11-slim as builder
WORKDIR /app
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY src/ ./src/
EXPOSE 9487
CMD ["python", "-m", "tautulli_exporter.main"]
```

### Docker Compose Example
```yaml
services:
  tautulli-exporter:
    build: .
    ports:
      - "9487:9487"
    environment:
      - TAUTULLI_URL=http://tautulli:8181
      - TAUTULLI_API_KEY=${TAUTULLI_API_KEY}
    restart: unless-stopped
```

---

## Testing Requirements

### Test Coverage Goals
- Unit tests for all collectors
- Integration tests with mocked API responses
- Use pytest with pytest-asyncio for async tests

### Test Fixtures
Store sample API responses in `tests/fixtures/`:
- `get_activity.json`
- `get_libraries.json`
- `get_users.json`
- etc.

---

## API Reference
See [docs/tautulli_api.md](../docs/tautulli_api.md) for complete API documentation.

### Key Endpoints
| Endpoint | Priority | Collection Frequency |
|----------|----------|---------------------|
| `get_activity` | HIGH | Every scrape (15-60s) |
| `server_status` | HIGH | Every 5 minutes |
| `get_libraries` | MEDIUM | Every 15 minutes |
| `get_users_table` | MEDIUM | Every 15 minutes |
| `get_home_stats` | LOW | Every 30 minutes |
| `get_server_info` | LOW | Every hour |

---

## Implementation Checklist

### Phase 1: Core Infrastructure
- [ ] Project setup with pyproject.toml
- [ ] Configuration management (pydantic-settings)
- [ ] Tautulli API client with error handling
- [ ] Basic web server with /metrics endpoint
- [ ] Dockerfile and docker-compose.yml

### Phase 2: Core Metrics
- [ ] Activity collector (streams, bandwidth)
- [ ] Server status collector
- [ ] Library collector
- [ ] User collector

### Phase 3: Polish
- [ ] Health check endpoint (/health)
- [ ] Graceful shutdown
- [ ] Comprehensive logging
- [ ] Unit tests
- [ ] Documentation

### Phase 4: Advanced
- [ ] Per-stream detail metrics
- [ ] Historical stats (optional)
- [ ] Grafana dashboard JSON
- [ ] Helm chart (optional)

**Dashboard Sync:** When adding, renaming, or removing exporter metrics, update `tautulli-dashboard.json` to reflect the new metric names and label usage. Keep dashboard queries and panel IDs consistent with metric names; include a quick example of new queries in the PR description so reviewers can verify visualizations.

---

## Dependencies

### Required
```
prometheus_client>=0.19.0
httpx>=0.26.0
pydantic>=2.0
pydantic-settings>=2.0
uvicorn>=0.25.0
fastapi>=0.109.0
```

### Development
```
pytest>=7.4.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0
black>=24.0.0
ruff>=0.1.0
mypy>=1.8.0
```
