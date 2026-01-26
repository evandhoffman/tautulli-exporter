# Tautulli Prometheus Exporter

A Prometheus exporter for [Tautulli](https://tautulli.com/) metrics, providing real-time monitoring of your Plex Media Server through Tautulli's API.

## Features

- 📊 Real-time streaming activity metrics
- 📚 Library statistics (item counts, play counts)
- 👥 User statistics (plays, watch time)
- 🖥️ Server health and connectivity status
- 🐳 Docker-ready with multi-stage builds
- ⚡ Async API client for optimal performance

## Quick Start

### Docker Compose (Recommended)

```yaml
services:
  tautulli-exporter:
    image: tautulli-exporter:latest
    build: .
    ports:
      - "9487:9487"
    environment:
      - TAUTULLI_URL=http://tautulli:8181
      - TAUTULLI_API_KEY=your-api-key-here
    restart: unless-stopped
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TAUTULLI_URL` | Yes | - | Tautulli base URL |
| `TAUTULLI_API_KEY` | Yes | - | Tautulli API key |
| `EXPORTER_PORT` | No | `9487` | Metrics endpoint port |
| `EXPORTER_HOST` | No | `0.0.0.0` | Host to bind |
| `LOG_LEVEL` | No | `INFO` | Log level |
| `COLLECT_USER_STATS` | No | `true` | Enable user metrics |
| `COLLECT_LIBRARY_STATS` | No | `true` | Enable library metrics |

### Getting Your Tautulli API Key

1. Open Tautulli web interface
2. Go to **Settings** → **Web Interface**
3. Find **API Key** section
4. Copy the API key

## Metrics

### Activity Metrics
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `tautulli_streams_count` | Gauge | - | Current active streams |
| `tautulli_streams_by_type` | Gauge | type | Streams by transcode decision |
| `tautulli_bandwidth_kbps` | Gauge | location | Bandwidth usage |

### Library Metrics
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `tautulli_library_items_count` | Gauge | name, type | Library item counts |
| `tautulli_library_plays_total` | Counter | name | Total library plays |

### User Metrics
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `tautulli_users_count` | Gauge | - | Total users |
| `tautulli_user_plays_total` | Counter | user | User play counts |

### Server Metrics
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `tautulli_up` | Gauge | - | Exporter health |
| `tautulli_server_connected` | Gauge | - | Plex connection status |
| `tautulli_info` | Info | version, platform | Tautulli version |

## Prometheus Configuration

```yaml
scrape_configs:
  - job_name: 'tautulli'
    static_configs:
      - targets: ['tautulli-exporter:9487']
    scrape_interval: 30s
```

## Development

### Prerequisites
- Python 3.11+
- Docker (optional)

### Local Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/tautulli-exporter.git
cd tautulli-exporter

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env
# Edit .env with your Tautulli settings

# Run the exporter
python -m tautulli_exporter.main
```

### Running Tests

```bash
pytest tests/ -v --cov=src/tautulli_exporter
```

## Grafana Dashboard

A sample Grafana dashboard is provided in `grafana/dashboard.json`.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
