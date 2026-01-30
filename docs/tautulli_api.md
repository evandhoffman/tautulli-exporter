# Tautulli API Reference for Prometheus Exporter

This document contains the relevant Tautulli API endpoints for building a Prometheus metrics exporter.

## API Overview

### Base URL Structure
```
http://IP_ADDRESS:PORT/api/v2?apikey=$apikey&cmd=$command
```

### Authentication
- All requests require an `apikey` parameter
- API key can be obtained via `get_apikey` endpoint (requires username/password if auth is enabled)

### Response Format
```json
{
    "response": {
        "data": {...},
        "message": null,
        "result": "success"
    }
}
```

### Optional Parameters
- `out_type`: "json" or "xml" (default: json)
- `callback`: For JSONP responses
- `debug`: 1 to enable debug output

---

## Key Endpoints for Metrics Collection

### 1. Server Status & Info

#### `server_status`
Check Tautulli's connection to Plex server.
```
Required: None
Returns: {"connected": true/false}
```
**Metrics**: Server connectivity (gauge: 0/1)

#### `get_server_info`
Get PMS server information.
```
Required: None
Returns:
  - pms_identifier
  - pms_ip
  - pms_is_remote (0/1)
  - pms_name
  - pms_platform
  - pms_plexpass (0/1)
  - pms_port
  - pms_ssl (0/1)
  - pms_version
```
**Metrics**: Server info labels, PlexPass status

#### `get_tautulli_info`
Get Tautulli server info.
```
Required: None
Returns:
  - tautulli_version
  - tautulli_branch
  - tautulli_platform
  - tautulli_python_version
```
**Metrics**: Tautulli version info

---

### 2. Current Activity (Real-time Metrics)

#### `get_activity`
Get current streaming activity on PMS. **PRIMARY ENDPOINT FOR REAL-TIME METRICS**
```
Required: None
Optional:
  - session_key (int): Filter to specific session
  - session_id (str): Filter to specific session
Returns:
  - stream_count: Total active streams
  - stream_count_direct_play: Direct play count
  - stream_count_direct_stream: Direct stream count
  - stream_count_transcode: Transcode count
  - total_bandwidth: Total bandwidth (Kbps)
  - wan_bandwidth: WAN bandwidth (Kbps)
  - lan_bandwidth: LAN bandwidth (Kbps)
  - sessions[]: Array of session details including:
    - user, user_id, friendly_name
    - media_type (movie, episode, track, live)
    - title, full_title, grandparent_title
    - state (playing, paused, buffering)
    - transcode_decision (direct play, copy, transcode)
    - video_decision, audio_decision
    - quality_profile
    - bandwidth
    - progress_percent
    - duration, view_offset
    - player, platform, product
    - ip_address, location (lan/wan)
    - library_name, section_id
    - transcode_hw_decoding, transcode_hw_encoding
    - stream_video_resolution, stream_audio_channels
```
**Metrics**:
- `tautulli_streams_total` (gauge)
- `tautulli_streams_direct_play` (gauge)
- `tautulli_streams_direct_stream` (gauge)
- `tautulli_streams_transcode` (gauge)
- `tautulli_bandwidth_total_kbps` (gauge)
- `tautulli_bandwidth_wan_kbps` (gauge)
- `tautulli_bandwidth_lan_kbps` (gauge)
- `tautulli_stream_info` (gauge with labels: user, media_type, state, platform, quality, transcode_decision, library)

---

### 3. Library Statistics

#### `get_libraries`
Get list of all libraries.
```
Required: None
Returns: Array with:
  - section_id
  - section_name
  - section_type (movie, show, artist, photo)
  - count: Number of items
  - parent_count: Number of parent items (e.g., seasons for shows)
  - child_count: Number of child items (e.g., episodes)
  - is_active (0/1)
```
**Metrics**:
- `tautulli_library_total_items` (gauge, labels: library_name, library_type)
- `tautulli_library_parent_items` (gauge)
- `tautulli_library_child_items` (gauge)

#### `get_library`
Get details for a specific library.
```
Required: section_id (str)
Optional: include_last_accessed (bool)
Returns:
  - section_id, section_name, section_type
  - count, parent_count, child_count
  - is_active, do_notify, keep_history
  - last_accessed (timestamp)
```

#### `get_libraries_table`
Get detailed library statistics.
```
Required: None
Returns: Array with:
  - plays: Total play count
  - duration: Total watch duration (seconds)
  - last_accessed: Timestamp
  - last_played: Title of last played item
```
**Metrics**:
- `tautulli_library_plays_total` (counter, labels: library_name)
- `tautulli_library_duration_seconds_total` (counter)
- `tautulli_library_last_accessed_timestamp` (gauge)

#### `get_library_watch_time_stats`
Get watch time statistics for a library.
```
Required: section_id (str)
Optional:
  - grouping (int): 0 or 1
  - query_days (str): Comma separated, e.g., "1,7,30,0" (0 = all time)
Returns: Array with:
  - query_days
  - total_plays
  - total_time (seconds)
```
**Metrics**:
- `tautulli_library_watch_time_seconds` (gauge, labels: library_name, period)
- `tautulli_library_plays` (gauge, labels: library_name, period)

### Per-item and Per-show Watch Time

The exporter can collect detailed watch-time metrics per media item (episodes/movies) and aggregated per-show totals. These are implemented by querying media info for libraries and then requesting per-item watch-time stats. Be aware this can be API-heavy on large libraries; control via configuration (`COLLECT_WATCH_TIME_STATS`, `WATCH_TIME_MAX_ITEMS`).

**Metrics**:

- `tautulli_show_watch_seconds{show_rating_key,show_title,media_type,library_name}`: Aggregated total seconds watched per show (episodes summed) or per-movie.

### Episode Drilldown Algorithm

To obtain watched time for each episode of a show (TV series), the exporter should drill down the library metadata using the following approach:

1. Start from the show's `rating_key` (the show-level rating key returned by `get_library_media_info` or other endpoints).
2. For any item returned by `get_library_media_info` where `last_played` > 0 and the item indicates a show (e.g. `media_type == "show"` or `section_type == "show"`), recursively drill down.
3. Call `get_children_metadata` with the show's `rating_key` to retrieve its child items (usually seasons). From each season entry capture the season's `rating_key` and any season metadata such as `parent_title`/`title`.
4. For each season, call `get_children_metadata` again using the season's `rating_key` to retrieve episode-level items. Some libraries may have an extra nesting level—keep drilling until you reach items where `media_type` == `episode`.
4. Once you have an item whose `media_type` is `episode`, take that episode's `rating_key` and call `get_item_watch_time_stats` with `query_days=0` to fetch all-time watch stats for that episode. The response looks like:

```
{
  "response": {
    "result": "success",
    "message": null,
    "data": [
      {
        "query_days": 0,
        "total_time": 2533,
        "total_plays": 1
      }
    ]
  }
}
```

5. Export the returned `total_time` as a per-episode metric.

Metric to export:

- `tautulli_episode_watch_seconds`: Gauge containing watched seconds per episode with these labels (populate from the `get_children_metadata` responses and the episode item):
  - `library_name`
  - `rating_key` (episode rating key)
  - `title` (episode title)
  - `parent_title` (season title or parent container)
  - `grandparent_title` (series/show title)
  - `media_index` (episode index/media_index)
  - `section_id` (library section id)

Notes:
- The drilldown uses `get_children_metadata` repeatedly until items with `media_type == "episode"` are found.
- Use `query_days=0` for `get_item_watch_time_stats` to get all-time totals.
- This process can be API-heavy on large libraries; respect configuration limits such as `WATCH_TIME_MAX_ITEMS` and consider caching results.

---

### 4. User Statistics

#### `get_users`
Get list of all users with server access.
```
Required: None
Returns: Array with:
  - user_id
  - username
  - friendly_name
  - email
  - is_active (0/1)
  - is_admin (0/1)
  - is_home_user (0/1)
  - is_allow_sync (0/1)
  - shared_libraries[]
```
**Metrics**:
- `tautulli_users_total` (gauge)
- `tautulli_users_active` (gauge)

#### `get_user`
Get specific user details.
```
Required: user_id (str)
Optional: include_last_seen (bool)
Returns:
  - user_id, username, friendly_name
  - email
  - is_active, is_admin, is_home_user
  - last_seen (timestamp)
  - keep_history, do_notify
```

#### `get_users_table`
Get users with play statistics.
```
Required: None
Returns: Array with:
  - user_id, username, friendly_name
  - plays: Total play count
  - duration: Total watch duration
  - last_seen: Timestamp
  - last_played: Title
  - ip_address
  - platform, player
```
**Metrics**:
- `tautulli_user_plays_total` (counter, labels: user)
- `tautulli_user_duration_seconds_total` (counter, labels: user)
- `tautulli_user_last_seen_timestamp` (gauge, labels: user)

#### `get_user_watch_time_stats`
Get watch time stats for a specific user.
```
Required: user_id (str)
Optional:
  - grouping (int): 0 or 1
  - query_days (str): "1,7,30,0"
Returns: Array with:
  - query_days
  - total_plays
  - total_time (seconds)
```
**Metrics**:
- `tautulli_user_watch_time_seconds` (gauge, labels: user, period)
- `tautulli_user_plays` (gauge, labels: user, period)

#### `get_user_player_stats`
Get player/platform stats for a user.
```
Required: user_id (str)
Returns: Array with:
  - platform
  - player_name
  - total_plays
  - total_time
```

---

### 5. Historical/Aggregate Statistics

#### `get_home_stats`
Get homepage watch statistics. **COMPREHENSIVE STATS ENDPOINT**
```
Required: None
Optional:
  - grouping (int): 0 or 1
  - time_range (int): Days, default 30
  - stats_type (str): 'plays' or 'duration'
  - stats_count (int): Number of items, default 5
  - stat_id (str): Filter to specific stat type
  - section_id (int): Filter by library
  - user_id (int): Filter by user
  - before/after (str): "YYYY-MM-DD"
Available stat_id values:
  - top_movies, popular_movies
  - top_tv, popular_tv
  - top_music, popular_music
  - top_libraries
  - top_users
  - top_platforms
  - last_watched
  - most_concurrent
Returns: Array of stat objects with rows containing:
  - rating_key, title
  - total_plays, total_duration
  - users_watched
  - last_play timestamp
```
**Metrics**:
- `tautulli_top_media_plays` (gauge, labels: title, media_type, rank)
- `tautulli_most_concurrent_streams` (gauge)

#### `get_history`
Get play history.
```
Required: None
Optional:
  - grouping (int): 0 or 1
  - user_id (int)
  - section_id (int)
  - media_type (str): movie, episode, track, live
  - start_date, before, after (str): "YYYY-MM-DD"
  - transcode_decision (str): direct play, copy, transcode
  - length (int): Number of items, default 25
Returns:
  - recordsTotal: Total history count
  - total_duration: Human readable
  - data[]: Array of history items
```
**Metrics**:
- `tautulli_history_total` (counter)

---

### 6. Graph/Trend Data

#### `get_plays_by_date`
Daily play counts.
```
Required: None
Optional:
  - time_range (str): Days
  - y_axis (str): "plays" or "duration"
  - user_id (str): Comma separated
  - grouping (int): 0 or 1
Returns:
  - categories[]: Date strings "YYYY-MM-DD"
  - series[]: {name: "Movies/TV/Music/Live TV", data: [...]}
```

#### `get_plays_by_stream_type`
Stream type (direct play/stream/transcode) by date.
```
Returns:
  - categories[]: Date strings
  - series[]: {name: "Direct Play/Direct Stream/Transcode", data: [...]}
```

#### `get_plays_per_month`
Monthly play counts.
```
Optional: time_range (str): Months
Returns:
  - categories[]: "Jan 2016", "Feb 2016", ...
  - series[]: {name: "Movies/TV/Music/Live TV", data: [...]}
```

#### `get_concurrent_streams_by_stream_type`
Concurrent stream data by date.
```
Returns:
  - categories[]: Date strings
  - series[]: Includes "Max. Concurrent Streams" data
```
**Metrics**:
- `tautulli_concurrent_streams_max` (gauge, labels: date)

---

### 7. Recently Added

#### `get_recently_added`
Get recently added items.
```
Required: count (str)
Optional:
  - start (str)
  - media_type (str): movie, show, artist
  - section_id (str)
Returns:
  - recently_added[]: Array of media items with metadata
```
**Metrics**:
- `tautulli_recently_added_total` (gauge, labels: media_type, library)

---

### 8. System/Health

#### `status`
Get Tautulli status.
```
Required: None
Optional: check (str): "database"
Returns: {"result": "success", "message": "Ok"}
```
**Metrics**:
- `tautulli_up` (gauge: 0/1)
- `tautulli_database_ok` (gauge: 0/1)

#### `get_pms_update`
Check for Plex Media Server updates.
```
Returns:
  - update_available (bool)
  - version
  - release_date
```
**Metrics**:
- `tautulli_pms_update_available` (gauge: 0/1)

---

## Recommended Metrics Summary

### Gauges (Current State)
| Metric Name | Labels | Description |
|-------------|--------|-------------|
| `tautulli_up` | | Exporter health |
| `tautulli_server_connected` | | Plex server connection status |
| `tautulli_streams_total` | | Current active streams |
| `tautulli_streams_by_type` | type={direct_play,direct_stream,transcode} | Streams by transcode decision |
| `tautulli_bandwidth_kbps` | location={total,wan,lan} | Current bandwidth usage |
| `tautulli_stream_info` | user, media_type, state, platform, library, quality | Per-stream details |
| `tautulli_users_total` | | Total users |
| `tautulli_users_active` | | Active users |
| `tautulli_library_items` | library, type, level={total,parent,child} | Library item counts |
| `tautulli_pms_update_available` | | PMS update available |

### Counters (Cumulative)
| Metric Name | Labels | Description |
|-------------|--------|-------------|
| `tautulli_plays_total` | library, media_type | Total plays |
| `tautulli_watch_time_seconds_total` | library, media_type | Total watch time |
| `tautulli_user_plays_total` | user | Plays per user |
| `tautulli_user_watch_time_seconds_total` | user | Watch time per user |

### Info Metrics
| Metric Name | Labels | Description |
|-------------|--------|-------------|
| `tautulli_info` | version, branch, platform | Tautulli version info |
| `tautulli_pms_info` | name, version, platform, ip | Plex server info |

---

## API Call Strategy

### High Frequency (Every Scrape - 15s-60s)
1. `get_activity` - Real-time streaming data

### Medium Frequency (Every 5 Minutes)
1. `server_status` - Connection health
2. `status` - Tautulli health

### Low Frequency (Every 15-30 Minutes)
1. `get_libraries` - Library counts
2. `get_libraries_table` - Library play stats
3. `get_users` - User list
4. `get_users_table` - User play stats
5. `get_home_stats` - Top content/users

### Very Low Frequency (Every Hour+)
1. `get_server_info` - Server metadata
2. `get_tautulli_info` - Tautulli metadata
3. `get_pms_update` - Update status

---

## Error Handling

### Response Codes
- `result: "success"` - Request successful
- `result: "error"` - Request failed, check `message` field

### Common Errors
- Invalid API key
- Server not connected
- Rate limiting (implement backoff)

### Best Practices
- Cache static info (server_info, tautulli_info)
- Handle connection timeouts gracefully
- Implement exponential backoff on failures
- Use async requests where possible
