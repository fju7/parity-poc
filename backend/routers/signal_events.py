"""Signal analytics event capture endpoint.

Accepts lightweight event payloads from the frontend and writes them
to the signal_events table. Uses text/plain content type to support
navigator.sendBeacon without CORS preflight.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import json
import uuid

router = APIRouter(prefix="/api/signal", tags=["signal"])

# Lazy Supabase client — only needed on first request
_sb = None


def _get_sb():
    global _sb
    if _sb is None:
        from supabase_client import supabase
        _sb = supabase
    return _sb


ALLOWED_EVENT_TYPES = {
    "issue_viewed",
    "category_selected",
    "claim_expanded",
    "score_rationale_viewed",
    "source_clicked",
    "summary_scroll_depth",
    "summary_theme_expanded",
}

MAX_EVENT_DATA_SIZE = 4096  # bytes


@router.post("/events")
async def capture_event(request: Request):
    """Accept an analytics event.

    Accepts both application/json and text/plain (for sendBeacon
    compatibility without CORS preflight).
    """
    try:
        body = await request.body()
        if len(body) > MAX_EVENT_DATA_SIZE:
            return JSONResponse({"error": "payload too large"}, status_code=413)

        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return JSONResponse({"error": "invalid json"}, status_code=400)

    event_type = payload.get("event_type")
    if not event_type or event_type not in ALLOWED_EVENT_TYPES:
        return JSONResponse({"error": "invalid event_type"}, status_code=400)

    # Validate anonymous_id is a UUID (no PII)
    anonymous_id = payload.get("anonymous_id")
    if anonymous_id:
        try:
            uuid.UUID(anonymous_id)
        except ValueError:
            anonymous_id = None

    event_data = payload.get("event_data", {})
    if not isinstance(event_data, dict):
        event_data = {}

    device_type = payload.get("device_type", "unknown")
    if device_type not in ("mobile", "tablet", "desktop", "unknown"):
        device_type = "unknown"

    sb = _get_sb()
    if not sb:
        # No Supabase service key — silently accept (dev mode)
        return JSONResponse({"status": "accepted"}, status_code=202)

    sb.table("signal_events").insert({
        "user_id": anonymous_id,
        "event_type": event_type,
        "event_data": event_data,
        "device_type": device_type,
    }).execute()

    return JSONResponse({"status": "ok"}, status_code=201)
