from fastapi import FastAPI, Query
from typing import Any

app = FastAPI()

# Sample in-memory data
LIBRARIES = [
    {"section_id": 2, "section_name": "TV Shows", "section_type": "show"},
    {"section_id": 3, "section_name": "Movies", "section_type": "movie"},
]

# For simplicity, library media info keyed by section_id
LIBRARY_MEDIA = {
    "2": [
        {
            "rating_key": "S100",
            "media_type": "show",
            "title": "Mock Show",
            "last_played": "1700000000",
            "play_count": "2",
            "section_id": 2,
        }
    ],
    "3": [
        {
            "rating_key": "M100",
            "media_type": "movie",
            "title": "Mock Movie",
            "play_count": "1",
            "section_id": 3,
        }
    ],
}

# seasons keyed by show rating_key
SEASONS = {
    "S100": [
        {"rating_key": "SE100", "title": "Season 1"},
    ]
}

# episodes keyed by season rating_key
EPISODES = {
    "SE100": [
        {
            "rating_key": "E100",
            "title": "Pilot",
            "media_type": "episode",
            "media_index": "1",
        },
        {
            "rating_key": "E101",
            "title": "Second",
            "media_type": "episode",
            "media_index": "2",
        },
    ]
}

# watch time stats
WATCH_STATS = {
    "E100": [{"query_days": "0", "total_time": 1200}],
    "E101": [{"query_days": "0", "total_time": 600}],
    "M100": [{"query_days": "0", "total_time": 3600}],
}


@app.get("/api/v2")
async def api(cmd: str = Query(...), apikey: str = Query(None), **params: Any):
    # Minimal validation: accept any apikey
    if cmd == "get_libraries":
        return {"response": {"result": "success", "data": LIBRARIES}}

    if cmd == "get_library_media_info":
        section_id = str(params.get("section_id", ""))
        data = LIBRARY_MEDIA.get(section_id, [])
        return {"response": {"result": "success", "data": {"data": data}}}

    if cmd == "get_children_metadata":
        rating_key = str(params.get("rating_key", ""))
        # Return seasons or episodes
        if rating_key in SEASONS:
            return {"response": {"result": "success", "data": SEASONS[rating_key]}}
        if rating_key in EPISODES:
            return {"response": {"result": "success", "data": EPISODES[rating_key]}}
        # as fallback, return empty list
        return {"response": {"result": "success", "data": []}}

    if cmd == "get_item_watch_time_stats":
        rating_key = str(params.get("rating_key", ""))
        return {
            "response": {"result": "success", "data": WATCH_STATS.get(rating_key, [])}
        }

    # Default: unknown cmd
    return {"response": {"result": "error", "message": f"Unknown cmd {cmd}"}}
