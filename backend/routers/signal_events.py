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


ADMIN_USER_ID = "4c62234e-86cc-4b8d-a782-c54fe1d11eb0"


@router.get("/admin/analytics")
async def admin_analytics(request: Request):
    """Return aggregated analytics data. Admin-only."""
    # Auth check
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    token = auth_header.split(" ", 1)[1]
    sb = _get_sb()
    if not sb:
        return JSONResponse({"error": "no db"}, status_code=500)

    try:
        user = sb.auth.get_user(token)
        if user.user.id != ADMIN_USER_ID:
            return JSONResponse({"error": "forbidden"}, status_code=403)
    except Exception:
        return JSONResponse({"error": "invalid token"}, status_code=401)

    try:
        # Total events
        total_res = sb.table("signal_events").select("id", count="exact").execute()
        total_events = total_res.count or 0

        # Unique sessions
        all_events = sb.table("signal_events").select("session_id, topic_slug, event_type, element_id").execute()
        rows = all_events.data or []
        unique_sessions = len({r.get("session_id") for r in rows if r.get("session_id")})

        # Questions count
        question_count = sum(1 for r in rows if r.get("event_type") == "ask_submitted")

        # Per-topic breakdown
        topic_map = {}
        for r in rows:
            slug = r.get("topic_slug") or "unknown"
            if slug not in topic_map:
                topic_map[slug] = {"event_count": 0, "sections": {}, "question_count": 0}
            topic_map[slug]["event_count"] += 1
            if r.get("event_type") in ("section_expand", "summary_theme_expanded"):
                eid = r.get("element_id") or "unknown"
                topic_map[slug]["sections"][eid] = topic_map[slug]["sections"].get(eid, 0) + 1
            if r.get("event_type") == "ask_submitted":
                topic_map[slug]["question_count"] += 1

        topics = []
        for slug, info in sorted(topic_map.items(), key=lambda x: -x[1]["event_count"]):
            top_sections = sorted(info["sections"].items(), key=lambda x: -x[1])[:3]
            topics.append({
                "topic_slug": slug,
                "event_count": info["event_count"],
                "top_sections": [s[0] for s in top_sections],
                "question_count": info["question_count"],
            })

        # Event type distribution
        type_counts = {}
        for r in rows:
            et = r.get("event_type", "unknown")
            type_counts[et] = type_counts.get(et, 0) + 1
        event_types = [{"event_type": k, "count": v} for k, v in sorted(type_counts.items(), key=lambda x: -x[1])]

        return {
            "total_events": total_events,
            "unique_sessions": unique_sessions,
            "question_count": question_count,
            "topics": topics,
            "event_types": event_types,
        }
    except Exception as e:
        print(f"[Signal Admin Analytics] Error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
