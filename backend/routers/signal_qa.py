"""Parity Signal — Q&A endpoint (Premium only).

Accepts a user question about an issue, sends it to Claude with full
issue context (claims, scores, sources, consensus), returns the answer.
Stateless — no conversation history persistence.
"""

import os
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/signal", tags=["signal-qa"])

_sb = None


def _get_sb():
    global _sb
    if _sb is None:
        from supabase_client import supabase
        _sb = supabase
    return _sb


async def _get_authenticated_user(request: Request):
    """Extract Bearer token and validate via Supabase auth."""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = auth_header.split(" ", 1)[1]
    sb = _get_sb()
    if not sb:
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    try:
        user_response = sb.auth.get_user(token)
        user = user_response.user
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Auth failed: {exc}")


def _check_premium(user_id: str):
    """Verify user has premium tier. Raises 403 if not."""
    sb = _get_sb()
    result = sb.table("signal_subscriptions").select("tier").eq(
        "user_id", user_id
    ).execute()

    tier = result.data[0]["tier"] if result.data else "free"
    if tier != "premium":
        raise HTTPException(
            status_code=403,
            detail="Q&A is available to Premium subscribers only."
        )


QA_SYSTEM_PROMPT = """You are a medical evidence analyst for Parity Signal, an evidence intelligence platform. You answer questions about health topics based ONLY on the scored evidence data provided below.

## Rules
- Answer based on the scored evidence provided. Cite specific claims and their evidence scores when relevant.
- Be transparent about uncertainty. If the evidence is mixed or weak, say so clearly.
- DO NOT express personal opinions or make medical recommendations.
- DO NOT give medical advice. You are summarizing evidence, not prescribing.
- If a question is outside the scope of the provided evidence, say so.
- Keep answers concise (2-4 paragraphs max).
- Reference evidence strength categories: Strong (4.0+), Moderate (3.0-3.9), Mixed (2.0-2.9), Weak (<2.0).
- When claims conflict, present both sides and note which has stronger evidence support.

## Tone
Informative, neutral, transparent. Like a research librarian — helpful but never preachy."""


def _build_context(issue_id: str) -> str:
    """Build the evidence context string for Claude from DB data."""
    sb = _get_sb()

    # Get issue
    issue = sb.table("signal_issues").select("title, description").eq(
        "id", issue_id
    ).single().execute().data

    # Get claims with composites
    claims_res = sb.table("signal_claims").select(
        "id, claim_text, category, signal_claim_composites(composite_score, evidence_category)"
    ).eq("issue_id", issue_id).execute()
    claims = claims_res.data or []

    # Get consensus
    consensus_res = sb.table("signal_consensus").select(
        "category, consensus_status, summary_text, arguments_for, arguments_against"
    ).eq("issue_id", issue_id).execute()
    consensus = consensus_res.data or []

    # Get sources
    sources_res = sb.table("signal_sources").select(
        "title, source_type, publication_date"
    ).eq("issue_id", issue_id).execute()
    sources = sources_res.data or []

    # Build context
    parts = [
        f"# Topic: {issue['title']}",
        f"{issue.get('description', '')}",
        "",
        f"## Sources ({len(sources)} total)",
    ]
    for s in sources[:20]:  # Cap at 20 to manage token usage
        parts.append(f"- [{s['source_type']}] {s['title']} ({s.get('publication_date', 'n/d')})")

    parts.append("")
    parts.append(f"## Consensus by Category")
    for c in consensus:
        parts.append(f"### {c['category'].title()} — {c['consensus_status'].upper()}")
        parts.append(c.get("summary_text", ""))
        if c.get("arguments_for"):
            parts.append(f"  Supporting: {c['arguments_for']}")
        if c.get("arguments_against"):
            parts.append(f"  Opposing: {c['arguments_against']}")
        parts.append("")

    parts.append(f"## Scored Claims ({len(claims)} total)")
    # Group by category
    by_cat = {}
    for claim in claims:
        cat = claim.get("category", "other")
        by_cat.setdefault(cat, []).append(claim)

    for cat, cat_claims in by_cat.items():
        parts.append(f"\n### {cat.title()}")
        # Sort by score descending
        cat_claims.sort(
            key=lambda c: float((c.get("signal_claim_composites") or {}).get("composite_score", 0) or 0),
            reverse=True,
        )
        for claim in cat_claims:
            comp = claim.get("signal_claim_composites") or {}
            score = comp.get("composite_score", "n/a")
            cat_label = comp.get("evidence_category", "unscored")
            parts.append(f"- [{score} — {cat_label}] {claim['claim_text']}")

    return "\n".join(parts)


class QARequest(BaseModel):
    issue_id: str
    question: str


@router.post("/qa")
async def ask_question(body: QARequest, request: Request):
    """Answer a question about an issue using Claude + scored evidence context."""
    user = await _get_authenticated_user(request)
    _check_premium(str(user.id))

    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")
    if len(question) > 1000:
        raise HTTPException(status_code=400, detail="Question too long (max 1000 chars)")

    # Build evidence context
    try:
        context = _build_context(body.issue_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Issue not found")

    # Call Claude
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=503, detail="AI service not configured")

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            temperature=0.2,
            system=QA_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"{context}\n\n---\n\nUser question: {question}",
                }
            ],
        )

        answer = ""
        for block in response.content:
            if hasattr(block, "text"):
                answer += block.text

        return {"answer": answer.strip()}

    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI service error: {exc}")
