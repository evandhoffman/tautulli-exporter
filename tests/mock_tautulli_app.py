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
        },
        {
            "rating_key": "2973",
            "media_type": "show",
            "title": "Andor",
            "last_played": "1769740410",
            "play_count": "1",
            "section_id": 2,
        },
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
    ],
    "2973": [
        {"rating_key": "2974", "title": "Season 1"},
        {"rating_key": "8779", "title": "Season 2"},
    ],
}

# episodes keyed by season rating_key
EPISODES = {
    "SE100": [
        {
            "rating_key": "E100",
            "title": "Pilot",
            "media_type": "episode",
            "media_index": "1",
            "last_viewed_at": 1700000000,
        },
        {
            "rating_key": "E101",
            "title": "Second",
            "media_type": "episode",
            "media_index": "2",
            "last_viewed_at": 1700000001,
        },
    ],
    "2974": [
        {
            "rating_key": "2980",
            "title": "Kassa",
            "media_type": "episode",
            "media_index": "1",
            "last_viewed_at": 1769740410,
        },
        {
            "rating_key": "2984",
            "title": "That Would Be Me",
            "media_type": "episode",
            "media_index": "2",
            # intentionally no last_viewed_at to simulate un-viewed episode
        },
    ],
}

# watch time stats
WATCH_STATS = {
    "E100": [{"query_days": "0", "total_time": 1200}],
    "E101": [{"query_days": "0", "total_time": 600}],
    "M100": [{"query_days": "0", "total_time": 3600}],
    "2980": [{"query_days": 0, "total_time": 2871, "total_plays": 1}],
    "2984": [{"query_days": "0", "total_time": 2138}],
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
        # Return seasons or episodes using the `data.children_list` shape (as in your samples)
        if rating_key in SEASONS:
            return {
                "response": {
                    "result": "success",
                    "data": {"children_list": SEASONS[rating_key]},
                }
            }
        if rating_key in EPISODES:
            return {
                "response": {
                    "result": "success",
                    "data": {"children_list": EPISODES[rating_key]},
                }
            }
        # as fallback, return empty list
        return {"response": {"result": "success", "data": {"children_list": []}}}

    if cmd == "get_item_watch_time_stats":
        rating_key = str(params.get("rating_key", ""))
        return {
            "response": {"result": "success", "data": WATCH_STATS.get(rating_key, [])}
        }

    # Default: unknown cmd
    return {"response": {"result": "error", "message": f"Unknown cmd {cmd}"}}
