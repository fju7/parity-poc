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


# ---------------------------------------------------------------------------
# Counting helpers
#
# Never count by selecting rows and len()-ing them. PostgREST caps the rows it
# returns (Supabase default: 1000), so a plain .select().in_() silently returns
# a truncated page once the corpus is large enough. Every count below is either
# an exact HEAD count or comes from the signal_topic_counts view, both of which
# are computed in Postgres and cannot be truncated.
# ---------------------------------------------------------------------------


def _approved_issues(sb):
    """Issues that are visible on the public site.

    Falls back to all issues when quality_review_status is not yet in
    PostgREST's schema cache, matching the previous behaviour.
    """
    try:
        res = (
            sb.table("signal_issues")
            .select("*")
            .eq("quality_review_status", "approved")
            .execute()
        )
        return res.data or []
    except Exception:
        res = sb.table("signal_issues").select("*").execute()
        return res.data or []


def _exact_count(sb, table, column=None, value=None):
    """Exact row count, optionally filtered on one column.

    Uses count="exact" with head=True so PostgREST returns the total in the
    Content-Range header and no row payload at all.
    """
    try:
        # select("*") rather than a named column: head=True returns no rows, and
        # not every signal_ table has an "id" (signal_claim_composites is keyed
        # on claim_id).
        q = sb.table(table).select("*", count="exact", head=True)
        if column is not None:
            q = q.eq(column, value)
        res = q.execute()
        return res.count or 0
    except Exception:
        return 0


def _topic_counts(sb, issue_ids):
    """Return {issue_id: {claim_count, scored_count, source_count}}.

    Prefers the signal_topic_counts view (migration 070). If the view is not
    present yet, falls back to per-issue exact counts so the endpoint stays
    correct on a backend deployed ahead of the migration. scored_count is only
    available from the view — the fallback reports None for it.
    """
    if not issue_ids:
        return {}

    try:
        res = (
            sb.table("signal_topic_counts")
            .select("issue_id, claim_count, scored_count, source_count")
            .in_("issue_id", issue_ids)
            .execute()
        )
        rows = res.data or []
        if rows:
            return {
                row["issue_id"]: {
                    "claim_count": row.get("claim_count") or 0,
                    "scored_count": row.get("scored_count"),
                    "source_count": row.get("source_count") or 0,
                }
                for row in rows
            }
    except Exception:
        pass  # view not migrated yet — fall through

    return {
        iid: {
            "claim_count": _exact_count(sb, "signal_claims", "issue_id", iid),
            "scored_count": None,
            "source_count": _exact_count(sb, "signal_sources", "issue_id", iid),
        }
        for iid in issue_ids
    }


@router.get("/metrics")
async def get_metrics():
    """Return live platform activity metrics.

    Scoped to quality-approved topics so these numbers agree with the topic
    list rendered directly beneath them on the landing page.
    """
    now = time.time()

    if _cache["data"] and now < _cache["expires"]:
        return _cache["data"]

    empty = {
        "claims_scored": 0,
        "claims_total": 0,
        "topics_tracked": 0,
        "sources_monitored": 0,
        "updates_this_month": 0,
    }

    sb = _get_sb()
    if not sb:
        return empty

    try:
        issues = _approved_issues(sb)
        issue_ids = [i["id"] for i in issues]
        counts = _topic_counts(sb, issue_ids)

        claims_total = sum(c["claim_count"] for c in counts.values())
        sources_monitored = sum(c["source_count"] for c in counts.values())

        scored_values = [c["scored_count"] for c in counts.values()]
        if scored_values and all(v is not None for v in scored_values):
            claims_scored = sum(scored_values)
        else:
            # View unavailable — fall back to the global composite count. This
            # is an over-count if unapproved topics exist, but never truncated.
            claims_scored = _exact_count(sb, "signal_claim_composites")

        # Evidence updates this month
        from datetime import datetime, timezone
        month_start = datetime.now(timezone.utc).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        ).isoformat()
        try:
            updates_res = (
                sb.table("signal_evidence_updates")
                .select("id", count="exact", head=True)
                .gte("detected_at", month_start)
                .execute()
            )
            updates_this_month = updates_res.count or 0
        except Exception:
            updates_this_month = 0

        result = {
            "claims_scored": claims_scored,
            "claims_total": claims_total,
            "topics_tracked": len(issues),
            "sources_monitored": sources_monitored,
            "updates_this_month": updates_this_month,
        }

        _cache["data"] = result
        _cache["expires"] = now + CACHE_TTL

        return result

    except Exception as e:
        print(f"[Signal Metrics ERROR] {e}")
        return empty


@router.get("/stats")
async def get_stats():
    """Return total evidence claims and sources counts (public, no auth)."""
    sb = _get_sb()
    if not sb:
        return {"evidence_claims": 0, "evidence_sources": 0}

    return {
        "evidence_claims": _exact_count(sb, "signal_claims"),
        "evidence_sources": _exact_count(sb, "signal_sources"),
    }


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
        issues = _approved_issues(sb)

        if not issues:
            _topics_cache["data"] = []
            _topics_cache["expires"] = now + CACHE_TTL
            return JSONResponse(content=[])

        issue_ids = [i["id"] for i in issues]
        counts = _topic_counts(sb, issue_ids)

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

            c = counts.get(iid, {})
            result.append({
                "id": iid,
                "slug": issue.get("slug", ""),
                "title": issue.get("title", ""),
                "description": issue.get("description", ""),
                "claim_count": c.get("claim_count", 0),
                "scored_count": c.get("scored_count"),
                "source_count": c.get("source_count", 0),
                "categories": categories,
                "overall_summary": overall_summary,
            })

        _topics_cache["data"] = result
        _topics_cache["expires"] = now + CACHE_TTL

        return JSONResponse(content=result)

    except Exception as e:
        print(f"[Signal Topics ERROR] {e}")
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

        issue_ids = [i["id"] for i in issues]
        counts = _topic_counts(sb, issue_ids)

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
                "claim_count": counts.get(iid, {}).get("claim_count", 0),
                "scored_count": counts.get(iid, {}).get("scored_count"),
                "source_count": counts.get(iid, {}).get("source_count", 0),
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

Return a JSON object with exactly these four fields:

{
  "mechanism": "One paragraph. How does this work? Basic science or logic, no jargon, no scores. Why does this topic matter?",
  "evidence": "One to two paragraphs. What does the strongest evidence show? Include specific numbers where they matter. Surface what FAILED to find expected effects — do not bury disappointments. This builds credibility.",
  "limitations": "One paragraph. What are the important caveats, contested findings, access barriers, or unknowns? Be direct about what is genuinely unknown.",
  "watch": "One sentence only. What single question or research development would most change this picture?"
}

RULES:
- Return ONLY valid JSON. No markdown, no code fences, no explanation outside the JSON.
- Short sentences. Direct language.
- No hedging: do NOT use "it appears", "may suggest", "could potentially", "it is possible that". Say what the evidence shows. Say clearly when evidence is weak or contradictory.
- No scores, no dimension names, no methodology references.
- No bullet points — flowing paragraphs only within each field.
- The "mechanism" field should NOT start with "The evidence suggests" or similar. Start with the mechanism itself.
- Total across all fields: around 250-400 words."""


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
        raw_text = response.content[0].text.strip()

        # Parse JSON response — strip markdown code fences if present
        import json as _json
        clean = raw_text
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()

        try:
            plain_json = _json.loads(clean)
        except _json.JSONDecodeError:
            # Fallback: store as old-format text wrapper
            plain_json = {"text": raw_text}

        # Validate required fields
        if not all(k in plain_json for k in ("mechanism", "evidence", "limitations", "watch")):
            # Partial parse — wrap as text fallback
            if "mechanism" not in plain_json:
                plain_json = {"text": raw_text}

        # Store structured JSON in DB (column is JSONB)
        # NOTE: Existing approved summaries are in old {"text": "..."} format.
        # They need to be regenerated manually via the admin UI to get the
        # structured {mechanism, evidence, limitations, watch} format.
        sb.table("signal_issues").update({
            "plain_summary": plain_json,
            "plain_summary_status": "generated",
        }).eq("id", issue_id).execute()

        return JSONResponse(content={
            "ok": True,
            "issue_id": issue_id,
            "plain_summary": plain_json,
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
