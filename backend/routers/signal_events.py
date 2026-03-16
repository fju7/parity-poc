"""Signal analytics event capture endpoint.

Privacy-first: accepts session_id (random UUID per page load), never user_id.
Accepts lightweight event payloads and writes to signal_events table.
Uses text/plain content type to support navigator.sendBeacon without CORS preflight.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import json
import uuid

router = APIRouter(prefix="/api/signal", tags=["signal"])

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
    "claims_expanded",
    "section_expand",
    "nav_click",
    "ask_submitted",
    "chip_click",
    "session_depth",
    "analytical_paths_opened",
    "weights_adjusted",
    "weights_reset",
}

MAX_EVENT_DATA_SIZE = 8192


@router.post("/events")
async def capture_event(request: Request):
    """Accept an analytics event. Returns 200 always — never fail the UI."""
    try:
        body = await request.body()
        if len(body) > MAX_EVENT_DATA_SIZE:
            return JSONResponse({"status": "accepted"}, status_code=200)

        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return JSONResponse({"status": "accepted"}, status_code=200)

    event_type = payload.get("event_type")
    if not event_type or event_type not in ALLOWED_EVENT_TYPES:
        return JSONResponse({"status": "accepted"}, status_code=200)

    session_id = payload.get("session_id", "")
    if session_id:
        try:
            uuid.UUID(session_id)
        except ValueError:
            session_id = ""

    sb = _get_sb()
    if not sb:
        return JSONResponse({"status": "accepted"}, status_code=200)

    try:
        sb.table("signal_events").insert({
            "session_id": session_id or str(uuid.uuid4()),
            "topic_slug": payload.get("topic_slug", ""),
            "event_type": event_type,
            "element_id": payload.get("element_id", ""),
            "event_data": payload.get("event_data", {}),
        }).execute()
    except Exception as e:
        print(f"[Signal Events] Write failed (non-fatal): {e}")

    return JSONResponse({"status": "ok"}, status_code=200)
