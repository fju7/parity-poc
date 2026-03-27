"""Parity Signal — Live platform metrics endpoint.

Returns real counts from Supabase tables for the landing page.
Cached in-memory for 5 minutes to avoid excessive DB queries.
"""

import os
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
        # Fetch approved issues only (quality review gate)
        # Try filtering by quality_review_status; fall back to all if column not yet visible
        try:
            issues_res = (
                sb.table("signal_issues")
                .select("*")
                .eq("quality_review_status", "approved")
                .execute()
            )
            issues = issues_res.data or []
        except Exception:
            # Column not in PostgREST cache yet — return all issues as fallback
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


@router.get("/admin/review-topics")
async def get_review_topics():
    """Return all topics with quality_review_status for admin review."""
    sb = _get_sb()
    if not sb:
        return JSONResponse(content=[])

    try:
        issues_res = sb.table("signal_issues").select("*").execute()
        issues = issues_res.data or []

        # Get claim counts
        issue_ids = [i["id"] for i in issues]
        claims_res = sb.table("signal_claims").select("id, issue_id").in_("issue_id", issue_ids).execute()
        claim_counts = {}
        for row in claims_res.data or []:
            claim_counts[row["issue_id"]] = claim_counts.get(row["issue_id"], 0) + 1

        # Get source counts
        sources_res = sb.table("signal_sources").select("id, issue_id").in_("issue_id", issue_ids).execute()
        source_counts = {}
        for row in sources_res.data or []:
            source_counts[row["issue_id"]] = source_counts.get(row["issue_id"], 0) + 1

        result = []
        for issue in issues:
            iid = issue["id"]
            result.append({
                "id": iid,
                "slug": issue.get("slug", ""),
                "title": issue.get("title", ""),
                "description": issue.get("description", ""),
                "status": issue.get("status", "draft"),
                "quality_review_status": issue.get("quality_review_status", "pending"),
                "plain_summary": issue.get("plain_summary"),
                "plain_summary_status": issue.get("plain_summary_status", "pending"),
                "claim_count": claim_counts.get(iid, 0),
                "source_count": source_counts.get(iid, 0),
                "created_at": issue.get("created_at", ""),
            })

        return JSONResponse(content=result)
    except Exception as e:
        print(f"[Admin Review] Error: {e}")
        return JSONResponse(content=[])


@router.post("/admin/review-topic")
async def review_topic(body: dict):
    """Update quality_review_status for a topic. Body: {issue_id, status}"""
    sb = _get_sb()
    if not sb:
        return JSONResponse(content={"error": "DB not available"}, status_code=500)

    issue_id = body.get("issue_id")
    new_status = body.get("status")

    if not issue_id or new_status not in ("pending", "approved", "rejected"):
        return JSONResponse(
            content={"error": "Required: issue_id and status (pending|approved|rejected)"},
            status_code=400,
        )

    try:
        sb.table("signal_issues").update(
            {"quality_review_status": new_status}
        ).eq("id", issue_id).execute()

        # Invalidate topics cache so change is visible immediately
        _topics_cache["data"] = None
        _topics_cache["expires"] = 0

        return JSONResponse(content={"ok": True, "issue_id": issue_id, "status": new_status})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# Plain Summary — generate and approve
# ---------------------------------------------------------------------------

PLAIN_SUMMARY_PROMPT = """You are writing a plain-language summary of a complex evidence topic for a general audience. Your reader is intelligent but not a specialist. Think: a knowledgeable friend explaining what they read, not a scientist writing an abstract.

Structure your summary as follows:

PARAGRAPH 1 — THE MECHANISM: Why does this topic matter? What is the basic science or logic behind it? No scores, no jargon. One paragraph.

PARAGRAPHS 2-3 — THE EVIDENCE: What the strongest evidence shows. Where evidence is mixed or inconsistent. Importantly, where studies have FAILED to find expected effects — surface the disappointments, don't bury them. This builds credibility. Two to three paragraphs.

FINAL SENTENCE — WHAT TO WATCH: What research is underway or what question would most change the current picture if answered? One sentence.

RULES:
- Short sentences. Direct language.
- No hedging: do NOT use "it appears", "may suggest", "could potentially", "it is possible that". Say what the evidence shows. Say clearly when evidence is weak or contradictory.
- No scores, no dimension names, no methodology references.
- No bullet points or headers — flowing paragraphs only.
- Do not start with "The evidence suggests" or similar. Start with the mechanism.
- 3-5 paragraphs total. Around 250-400 words."""


@router.post("/admin/generate-plain-summary")
async def generate_plain_summary(body: dict):
    """Generate a plain-language summary for a Signal topic using Claude."""
    sb = _get_sb()
    if not sb:
        return JSONResponse(content={"error": "DB not available"}, status_code=500)

    issue_id = body.get("issue_id")
    if not issue_id:
        return JSONResponse(content={"error": "issue_id required"}, status_code=400)

    try:
        # Fetch the issue
        issue = sb.table("signal_issues").select("id, title, description").eq("id", issue_id).single().execute()
        if not issue.data:
            return JSONResponse(content={"error": "Issue not found"}, status_code=404)

        topic = issue.data

        # Fetch the latest summary
        summary_res = sb.table("signal_summaries").select("summary_json").eq(
            "issue_id", issue_id
        ).order("version", desc=True).limit(1).execute()
        overall_summary = ""
        if summary_res.data and summary_res.data[0].get("summary_json"):
            overall_summary = summary_res.data[0]["summary_json"].get("overall_summary", "")

        # Fetch consensus entries
        consensus_res = sb.table("signal_consensus").select(
            "category, consensus_status, summary_text, arguments_for, arguments_against"
        ).eq("issue_id", issue_id).execute()
        consensus_text = ""
        for c in (consensus_res.data or []):
            consensus_text += f"\n\nCategory: {c['category']} — Status: {c['consensus_status']}\n"
            if c.get("summary_text"):
                consensus_text += f"Summary: {c['summary_text']}\n"
            if c.get("arguments_for"):
                consensus_text += f"Arguments for: {c['arguments_for']}\n"
            if c.get("arguments_against"):
                consensus_text += f"Arguments against: {c['arguments_against']}\n"

        # Fetch top 10 claims by composite score
        claims_res = sb.table("signal_claims").select(
            "claim_text, category, signal_claim_composites(composite_score, evidence_category)"
        ).eq("issue_id", issue_id).execute()
        scored_claims = []
        for cl in (claims_res.data or []):
            comp = cl.get("signal_claim_composites")
            if comp and comp.get("composite_score"):
                scored_claims.append({
                    "text": cl["claim_text"],
                    "category": cl["category"],
                    "score": comp["composite_score"],
                    "strength": comp.get("evidence_category", ""),
                })
        scored_claims.sort(key=lambda x: x["score"], reverse=True)
        top_claims = scored_claims[:10]

        # Build context for Claude
        claims_block = "\n".join(
            f"- [{c['strength'].upper()}] ({c['category']}) {c['text']}"
            for c in top_claims
        )

        user_content = f"""Topic: {topic['title']}
Description: {topic.get('description', '')}

Technical Summary:
{overall_summary}

Consensus by Category:
{consensus_text}

Top 10 Evidence Claims (strongest first):
{claims_block}

Write the plain-language summary now."""

        # Call Claude
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            temperature=0.3,
            system=PLAIN_SUMMARY_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        plain_text = response.content[0].text.strip()

        # Store in DB
        sb.table("signal_issues").update({
            "plain_summary": plain_text,
            "plain_summary_status": "generated",
        }).eq("id", issue_id).execute()

        return JSONResponse(content={
            "ok": True,
            "issue_id": issue_id,
            "plain_summary": plain_text,
            "status": "generated",
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(content={"error": str(e)}, status_code=500)


@router.post("/admin/approve-plain-summary")
async def approve_plain_summary(body: dict):
    """Approve a generated plain summary for public display."""
    sb = _get_sb()
    if not sb:
        return JSONResponse(content={"error": "DB not available"}, status_code=500)

    issue_id = body.get("issue_id")
    if not issue_id:
        return JSONResponse(content={"error": "issue_id required"}, status_code=400)

    try:
        sb.table("signal_issues").update({
            "plain_summary_status": "approved",
        }).eq("id", issue_id).execute()

        return JSONResponse(content={"ok": True, "issue_id": issue_id, "status": "approved"})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
