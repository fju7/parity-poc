"""Parity Signal — Live platform metrics endpoint.

Returns real counts from Supabase tables for the landing page.
Cached in-memory for 5 minutes to avoid excessive DB queries.
"""

import time
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/signal", tags=["signal"])

_sb = None


def _get_sb():
    global _sb
    if _sb is None:
        from supabase_client import supabase
        _sb = supabase
    return _sb


# Simple in-memory cache
_cache = {"data": None, "expires": 0}
CACHE_TTL = 300  # 5 minutes


@router.get("/metrics")
async def get_metrics():
    """Return live platform activity metrics."""
    now = time.time()

    if _cache["data"] and now < _cache["expires"]:
        return _cache["data"]

    sb = _get_sb()
    if not sb:
        return {"claims_scored": 0, "topics_tracked": 0, "sources_monitored": 0, "updates_this_month": 0}

    try:
        # Total scored claims (have a composite)
        claims_res = sb.table("signal_claim_composites").select("claim_id", count="exact").execute()
        claims_scored = claims_res.count or 0

        # Active topics (all issues with claims)
        issues_res = sb.table("signal_issues").select("id", count="exact").execute()
        topics_tracked = issues_res.count or 0

        # Total sources
        sources_res = sb.table("signal_sources").select("id", count="exact").execute()
        sources_monitored = sources_res.count or 0

        # Evidence updates this month
        from datetime import datetime, timezone
        month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        updates_res = (
            sb.table("signal_evidence_updates")
            .select("id", count="exact")
            .gte("detected_at", month_start)
            .execute()
        )
        updates_this_month = updates_res.count or 0

        result = {
            "claims_scored": claims_scored,
            "topics_tracked": topics_tracked,
            "sources_monitored": sources_monitored,
            "updates_this_month": updates_this_month,
        }

        _cache["data"] = result
        _cache["expires"] = now + CACHE_TTL

        return result

    except Exception:
        return {"claims_scored": 0, "topics_tracked": 0, "sources_monitored": 0, "updates_this_month": 0}
