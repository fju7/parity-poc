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
_topics_cache = {"data": None, "expires": 0}
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


@router.get("/stats")
async def get_stats():
    """Return total evidence claims and sources counts (public, no auth)."""
    result = {"evidence_claims": 0, "evidence_sources": 0}

    sb = _get_sb()
    if not sb:
        return result

    try:
        claims_res = sb.table("signal_claims").select("id", count="exact").execute()
        result["evidence_claims"] = claims_res.count or 0
    except Exception as e:
        print(f"[Signal Stats ERROR] claims query failed: {e}")

    try:
        sources_res = sb.table("signal_sources").select("id", count="exact").execute()
        result["evidence_sources"] = sources_res.count or 0
    except Exception as e:
        print(f"[Signal Stats ERROR] sources query failed: {e}")


    return result


@router.get("/topics")
async def get_topics():
    """Return all topics with claim counts, source counts, categories, and summary."""
    now = time.time()

    if _topics_cache["data"] and now < _topics_cache["expires"]:
        return JSONResponse(content=_topics_cache["data"])

    sb = _get_sb()
    if not sb:
        return JSONResponse(content=[])

    try:
        # Fetch all issues
        issues_res = sb.table("signal_issues").select("*").execute()
        issues = issues_res.data or []

        if not issues:
            _topics_cache["data"] = []
            _topics_cache["expires"] = now + CACHE_TTL
            return JSONResponse(content=[])

        issue_ids = [i["id"] for i in issues]

        # Count claims per issue
        claims_res = sb.table("signal_claims").select("id, issue_id").in_("issue_id", issue_ids).execute()
        claim_counts = {}
        for row in claims_res.data or []:
            claim_counts[row["issue_id"]] = claim_counts.get(row["issue_id"], 0) + 1

        # Count sources per issue
        sources_res = sb.table("signal_sources").select("id, issue_id").in_("issue_id", issue_ids).execute()
        source_counts = {}
        for row in sources_res.data or []:
            source_counts[row["issue_id"]] = source_counts.get(row["issue_id"], 0) + 1

        # Fetch latest summary per issue (order by version desc)
        summaries_res = (
            sb.table("signal_summaries")
            .select("issue_id, summary_json, version")
            .in_("issue_id", issue_ids)
            .order("version", desc=True)
            .execute()
        )
        # Keep only the latest summary per issue
        summary_map = {}
        for row in summaries_res.data or []:
            iid = row["issue_id"]
            if iid not in summary_map:
                summary_map[iid] = row.get("summary_json")

        # Build response
        result = []
        for issue in issues:
            iid = issue["id"]
            summary_json = summary_map.get(iid) or {}
            raw_cats = summary_json.get("categories", []) if isinstance(summary_json, dict) else []
            if isinstance(raw_cats, list):
                categories = [c["name"] for c in raw_cats if isinstance(c, dict) and "name" in c]
            elif isinstance(raw_cats, dict):
                categories = list(raw_cats.keys())
            else:
                categories = []
            overall_summary = summary_json.get("overall_summary", "") if isinstance(summary_json, dict) else ""

            result.append({
                "id": iid,
                "slug": issue.get("slug", ""),
                "title": issue.get("title", ""),
                "description": issue.get("description", ""),
                "claim_count": claim_counts.get(iid, 0),
                "source_count": source_counts.get(iid, 0),
                "categories": categories,
                "overall_summary": overall_summary,
            })

        _topics_cache["data"] = result
        _topics_cache["expires"] = now + CACHE_TTL

        return JSONResponse(content=result)

    except Exception:
        return JSONResponse(content=[])
