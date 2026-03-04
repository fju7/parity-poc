"""Parity Signal — Topic Request endpoints.

Allows users to request new topics (with tier-based limits), uses Claude
to parse/validate requests, and provides admin approval workflow.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

BACKEND_ROOT = Path(__file__).resolve().parent.parent

router = APIRouter(prefix="/api/signal", tags=["signal-topic-requests"])

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


ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID", "")


async def _verify_admin(request: Request):
    """Verify request comes from admin (CRON_SECRET header or admin Bearer token)."""
    # Option 1: CRON_SECRET header (for server-to-server / cron jobs)
    cron_secret = os.environ.get("CRON_SECRET")
    if cron_secret and request.headers.get("X-Cron-Secret") == cron_secret:
        return

    # Option 2: Bearer token from ADMIN_USER_ID (for frontend admin dashboard)
    if ADMIN_USER_ID:
        try:
            user = await _get_authenticated_user(request)
            if str(user.id) == ADMIN_USER_ID:
                return
        except Exception:
            pass

    raise HTTPException(status_code=401, detail="Unauthorized")


def _get_user_tier_and_usage(user_id: str) -> dict:
    """Fetch tier and topic request usage for a user."""
    from routers.signal_stripe import TIER_LIMITS, _maybe_reset_counters

    sb = _get_sb()
    result = sb.table("signal_subscriptions").select(
        "tier, topic_requests_used, topic_requests_reset_at"
    ).eq("user_id", user_id).execute()

    if not result.data:
        return {"tier": "free", "topic_requests_used": 0, "limit": 0}

    row = result.data[0]
    _maybe_reset_counters(sb, user_id, row)
    tier = row.get("tier", "free")
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])

    return {
        "tier": tier,
        "topic_requests_used": row.get("topic_requests_used", 0),
        "limit": limits["topic_requests_per_month"],
    }


def _increment_topic_request_counter(user_id: str):
    """Increment the topic request counter for this user."""
    sb = _get_sb()
    result = sb.table("signal_subscriptions").select(
        "topic_requests_used"
    ).eq("user_id", user_id).execute()

    current = 0
    if result.data:
        current = result.data[0].get("topic_requests_used", 0)

    sb.table("signal_subscriptions").update(
        {"topic_requests_used": current + 1}
    ).eq("user_id", user_id).execute()


TOPIC_PARSE_SYSTEM_PROMPT = """You are a topic analyst for Parity Signal, a medical evidence intelligence platform. Users submit requests for new topics they want researched.

Your job:
1. Determine if the request is a well-formed topic that can be evaluated with evidence scoring
2. Determine if it's healthcare-related (current scope)
3. Parse it into a structured format
4. If unclear, suggest improved framing

Return JSON:
{
  "is_valid": true/false,
  "needs_clarification": true/false,
  "parsed_title": "Clean, concise topic title",
  "parsed_description": "1-2 sentence description of what will be researched",
  "parsed_slug": "lowercase-kebab-case-slug",
  "suggestion": "If needs_clarification or not valid, explain why and suggest improvement",
  "rejection_reason": "If clearly out of scope, explain why"
}

Rules:
- Healthcare, medical, pharmaceutical, mental health, and public health topics are in scope
- Policy topics with health implications are in scope
- Pure financial, political, or entertainment topics are out of scope
- Topics should be specific enough to score with evidence (not "tell me about healthcare")
- Suggest narrowing broad topics to scorable claims"""


def _parse_topic_request(request_text: str) -> dict:
    """Use Claude to parse and validate a topic request."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {"is_valid": True, "needs_clarification": False,
                "parsed_title": request_text[:100], "parsed_description": request_text,
                "parsed_slug": request_text[:50].lower().replace(" ", "-"),
                "suggestion": None, "rejection_reason": None}

    import anthropic
    import json
    import re

    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            temperature=0,
            system=TOPIC_PARSE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Topic request: {request_text}"}],
        )

        raw = ""
        for block in response.content:
            if hasattr(block, "text"):
                raw += block.text

        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```\s*$", "", raw)

        return json.loads(raw.strip())

    except Exception as exc:
        print(f"[TopicRequest] Claude parsing failed: {exc}")
        return {"is_valid": True, "needs_clarification": False,
                "parsed_title": request_text[:100], "parsed_description": request_text,
                "parsed_slug": request_text[:50].lower().replace(" ", "-"),
                "suggestion": None, "rejection_reason": None}


def _send_admin_email(request_data: dict, user_tier: str):
    """Send notification email to admin about a new topic request."""
    try:
        import resend
        resend_key = os.environ.get("RESEND_API_KEY")
        if not resend_key:
            print("[TopicRequest] RESEND_API_KEY not configured, skipping admin email")
            return
        resend.api_key = resend_key

        frontend_url = os.environ.get("FRONTEND_URL", "https://civicscale.ai")
        title = request_data.get("parsed_title", "Untitled")
        req_id = request_data.get("id", "unknown")

        html = f"""
        <h2>New Topic Request: {title}</h2>
        <p><strong>Requester tier:</strong> {user_tier.title()}</p>
        <p><strong>Original request:</strong> {request_data.get('raw_request', 'N/A')}</p>
        <p><strong>Parsed title:</strong> {request_data.get('parsed_title', 'N/A')}</p>
        <p><strong>Parsed description:</strong> {request_data.get('parsed_description', 'N/A')}</p>
        <p><strong>Suggested slug:</strong> {request_data.get('parsed_slug', 'N/A')}</p>
        <hr>
        <p><a href="{frontend_url}/signal/admin/requests">View All Requests</a></p>
        <p style="color:#666;font-size:12px;">Parity Signal by CivicScale</p>
        """

        resend.Emails.send({
            "from": "Parity Signal <notifications@civicscale.ai>",
            "to": ["fred@civicscale.ai"],
            "subject": f"New Topic Request: {title}",
            "html": html,
        })
        print(f"[TopicRequest] Admin email sent for request {req_id}")

    except Exception as exc:
        print(f"[TopicRequest] Failed to send admin email: {exc}")


def _notify_requester(user_id: str, title: str, body: str, deep_link: str = ""):
    """Create an in-app notification and queue email for the requester."""
    sb = _get_sb()
    try:
        sb.table("signal_notifications").insert({
            "user_id": user_id,
            "title": title,
            "body": body,
            "deep_link": deep_link,
            "delivery_method": "email",
        }).execute()
    except Exception as exc:
        print(f"[TopicRequest] Failed to create notification: {exc}")


# ---------------------------------------------------------------------------
# User-facing endpoints
# ---------------------------------------------------------------------------

class TopicRequestBody(BaseModel):
    request_text: str


@router.post("/topic-request")
async def request_topic(body: TopicRequestBody, request: Request):
    """Submit a new topic request with Claude parsing/validation."""
    user = await _get_authenticated_user(request)
    user_id = str(user.id)

    request_text = body.request_text.strip()
    if not request_text:
        raise HTTPException(status_code=400, detail="Request text is required")
    if len(request_text) > 2000:
        raise HTTPException(status_code=400, detail="Request text too long (max 2000 chars)")

    # Check tier limits
    usage = _get_user_tier_and_usage(user_id)
    if usage["limit"] == 0:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "topic_request_not_available",
                "message": "Topic requests are not available on the Free plan. Upgrade to Standard or above.",
                "upgrade_to": "standard",
            },
        )

    if usage["topic_requests_used"] >= usage["limit"]:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "topic_request_limit_reached",
                "limit": usage["limit"],
                "used": usage["topic_requests_used"],
                "tier": usage["tier"],
            },
        )

    # Parse with Claude
    parsed = _parse_topic_request(request_text)

    sb = _get_sb()

    if parsed.get("rejection_reason") and not parsed.get("is_valid"):
        # Out of scope — save and return rejection
        row = sb.table("signal_topic_requests").insert({
            "user_id": user_id,
            "topic_name": parsed.get("parsed_title", request_text[:100]),
            "raw_request": request_text,
            "parsed_title": parsed.get("parsed_title"),
            "parsed_description": parsed.get("parsed_description"),
            "parsed_slug": parsed.get("parsed_slug"),
            "status": "rejected",
            "rejection_reason": parsed.get("rejection_reason"),
        }).execute()

        return {
            "status": "rejected",
            "reason": parsed["rejection_reason"],
        }

    if parsed.get("needs_clarification"):
        # Save with clarification_needed status
        result = sb.table("signal_topic_requests").insert({
            "user_id": user_id,
            "topic_name": parsed.get("parsed_title", request_text[:100]),
            "raw_request": request_text,
            "parsed_title": parsed.get("parsed_title"),
            "parsed_description": parsed.get("parsed_description"),
            "parsed_slug": parsed.get("parsed_slug"),
            "status": "clarification_needed",
            "clarification_message": parsed.get("suggestion"),
        }).execute()

        return {
            "status": "clarification_needed",
            "request_id": result.data[0]["id"] if result.data else None,
            "suggestion": parsed["suggestion"],
            "parsed_title": parsed.get("parsed_title"),
            "original": request_text,
        }

    # Valid — save as approved
    result = sb.table("signal_topic_requests").insert({
        "user_id": user_id,
        "topic_name": parsed.get("parsed_title", request_text[:100]),
        "raw_request": request_text,
        "parsed_title": parsed.get("parsed_title"),
        "parsed_description": parsed.get("parsed_description"),
        "parsed_slug": parsed.get("parsed_slug"),
        "status": "approved",
    }).execute()

    # Increment counter
    _increment_topic_request_counter(user_id)

    # Notify admin
    req_data = result.data[0] if result.data else {"raw_request": request_text, **parsed}
    _send_admin_email(req_data, usage["tier"])

    return {
        "status": "approved",
        "title": parsed.get("parsed_title"),
        "message": "Your topic has been queued for research. We'll notify you when it's ready.",
    }


class ConfirmRequestBody(BaseModel):
    request_id: str
    confirmed_title: Optional[str] = None
    confirmed_description: Optional[str] = None


@router.post("/topic-request/confirm")
async def confirm_topic_request(body: ConfirmRequestBody, request: Request):
    """Confirm a topic request after clarification."""
    user = await _get_authenticated_user(request)
    user_id = str(user.id)

    sb = _get_sb()
    result = sb.table("signal_topic_requests").select("*").eq(
        "id", body.request_id
    ).eq("user_id", user_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Request not found")

    req = result.data[0]
    if req["status"] != "clarification_needed":
        raise HTTPException(status_code=400, detail="Request is not awaiting confirmation")

    # Check limits again
    usage = _get_user_tier_and_usage(user_id)
    if usage["topic_requests_used"] >= usage["limit"]:
        raise HTTPException(status_code=403, detail="Topic request limit reached")

    # Update request
    update_data = {"status": "approved"}
    if body.confirmed_title:
        update_data["parsed_title"] = body.confirmed_title
    if body.confirmed_description:
        update_data["parsed_description"] = body.confirmed_description

    sb.table("signal_topic_requests").update(update_data).eq("id", body.request_id).execute()

    _increment_topic_request_counter(user_id)

    # Notify admin
    req.update(update_data)
    _send_admin_email(req, usage["tier"])

    return {
        "status": "approved",
        "title": update_data.get("parsed_title", req.get("parsed_title")),
        "message": "Your topic has been queued for research. We'll notify you when it's ready.",
    }


@router.get("/topic-requests")
async def list_topic_requests(request: Request):
    """List the authenticated user's own topic requests."""
    user = await _get_authenticated_user(request)

    sb = _get_sb()
    result = sb.table("signal_topic_requests").select("*").eq(
        "user_id", str(user.id)
    ).order("submitted_at", desc=True).execute()

    return {"requests": result.data or []}


class PurchaseTopicRequestBody(BaseModel):
    return_path: str = "/signal"


@router.post("/topic-request/purchase")
async def purchase_topic_request(body: PurchaseTopicRequestBody, request: Request):
    """Create a Stripe Checkout session for a one-time additional topic request."""
    user = await _get_authenticated_user(request)
    user_id = str(user.id)

    from routers.signal_stripe import TOPIC_REQUEST_PRICE_IDS, _get_or_create_stripe_customer

    usage = _get_user_tier_and_usage(user_id)
    tier = usage["tier"]

    price_id = TOPIC_REQUEST_PRICE_IDS.get(tier, "")
    if not price_id:
        raise HTTPException(status_code=400, detail="No topic request price configured for this tier")

    import stripe
    customer_id = _get_or_create_stripe_customer(user)
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="payment",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{frontend_url}{body.return_path}?topic_purchase=1",
        cancel_url=f"{frontend_url}{body.return_path}",
        metadata={"supabase_user_id": user_id, "type": "topic_request"},
    )

    return {"checkout_url": session.url}


# ---------------------------------------------------------------------------
# Admin endpoints (secured with CRON_SECRET)
# ---------------------------------------------------------------------------

@router.get("/admin/topic-requests")
async def admin_list_requests(request: Request, status: Optional[str] = None):
    """List all topic requests (admin only)."""
    await _verify_admin(request)

    sb = _get_sb()
    query = sb.table("signal_topic_requests").select("*").order("submitted_at", desc=True)
    if status:
        query = query.eq("status", status)

    result = query.execute()
    return {"requests": result.data or []}


class AdminApproveBody(BaseModel):
    request_id: str


async def _run_topic_pipeline(request_id: str, slug: str, title: str, description: str, requester_id: str):
    """Launch the full topic pipeline as an async subprocess."""
    proc = await asyncio.create_subprocess_exec(
        sys.executable, str(BACKEND_ROOT / "scripts" / "signal" / "run_full_topic.py"),
        "--slug", slug,
        "--title", title,
        "--description", description,
        "--request-id", request_id,
        "--requester-id", requester_id,
        cwd=str(BACKEND_ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        print(f"[Pipeline] FAILED for {slug}: {stderr.decode()[-500:]}")
    else:
        print(f"[Pipeline] Completed for {slug}")


@router.post("/admin/topic-requests/approve")
async def admin_approve(body: AdminApproveBody, request: Request):
    """Approve a topic request, notify the requester, and launch the pipeline."""
    await _verify_admin(request)

    sb = _get_sb()
    result = sb.table("signal_topic_requests").select("*").eq(
        "id", body.request_id
    ).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Request not found")

    req = result.data[0]
    sb.table("signal_topic_requests").update(
        {"status": "processing"}
    ).eq("id", body.request_id).execute()

    _notify_requester(
        req["user_id"],
        f"Topic Approved: {req.get('parsed_title', 'Your topic')}",
        f"Your topic '{req.get('parsed_title', 'Your topic')}' has been approved and research is underway. We'll notify you when it's ready.",
        "/signal",
    )

    # Launch the full pipeline as a background task
    slug = req.get("parsed_slug", "")
    title = req.get("parsed_title", "")
    description = req.get("parsed_description", "")
    requester_id = req.get("user_id", "")

    if slug and title:
        asyncio.create_task(
            _run_topic_pipeline(body.request_id, slug, title, description, requester_id)
        )
        print(f"[Pipeline] Background task launched for {slug}")
    else:
        print(f"[Pipeline] Skipped: missing slug or title for request {body.request_id}")

    return {"status": "processing", "message": "Pipeline started"}


class AdminRejectBody(BaseModel):
    request_id: str
    reason: str


@router.post("/admin/topic-requests/reject")
async def admin_reject(body: AdminRejectBody, request: Request):
    """Reject a topic request and notify the requester."""
    await _verify_admin(request)

    sb = _get_sb()
    result = sb.table("signal_topic_requests").select("*").eq(
        "id", body.request_id
    ).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Request not found")

    req = result.data[0]
    sb.table("signal_topic_requests").update({
        "status": "rejected",
        "rejection_reason": body.reason,
    }).eq("id", body.request_id).execute()

    _notify_requester(
        req["user_id"],
        f"Topic Request Update: {req.get('parsed_title', 'Your topic')}",
        f"We're unable to research '{req.get('parsed_title', 'Your topic')}' at this time. {body.reason}",
        "/signal",
    )

    return {"status": "rejected"}


class AdminClarifyBody(BaseModel):
    request_id: str
    message: str


@router.post("/admin/topic-requests/clarify")
async def admin_clarify(body: AdminClarifyBody, request: Request):
    """Request clarification from the user and notify them."""
    await _verify_admin(request)

    sb = _get_sb()
    result = sb.table("signal_topic_requests").select("*").eq(
        "id", body.request_id
    ).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Request not found")

    req = result.data[0]
    sb.table("signal_topic_requests").update({
        "status": "clarification_needed",
        "clarification_message": body.message,
    }).eq("id", body.request_id).execute()

    _notify_requester(
        req["user_id"],
        f"Topic Request: Clarification Needed",
        f"We'd like to refine your topic request for '{req.get('parsed_title', 'Your topic')}'. {body.message}",
        "/signal",
    )

    return {"status": "clarification_needed"}


class AdminCompleteBody(BaseModel):
    request_id: str
    issue_id: str


@router.post("/admin/topic-requests/complete")
async def admin_complete(body: AdminCompleteBody, request: Request):
    """Mark a request as completed, link to issue, notify and auto-subscribe."""
    await _verify_admin(request)

    sb = _get_sb()
    result = sb.table("signal_topic_requests").select("*").eq(
        "id", body.request_id
    ).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Request not found")

    req = result.data[0]

    # Get the issue slug for the deep link
    issue_res = sb.table("signal_issues").select("slug").eq("id", body.issue_id).execute()
    issue_slug = issue_res.data[0]["slug"] if issue_res.data else ""

    # Update request
    sb.table("signal_topic_requests").update({
        "status": "completed",
        "issue_id": body.issue_id,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", body.request_id).execute()

    # Auto-subscribe the requester to the new topic
    try:
        sb.table("signal_topic_subscriptions").upsert({
            "user_id": req["user_id"],
            "issue_id": body.issue_id,
        }, on_conflict="user_id,issue_id").execute()
    except Exception as exc:
        print(f"[TopicRequest] Auto-subscribe failed: {exc}")

    _notify_requester(
        req["user_id"],
        f"Topic Ready: {req.get('parsed_title', 'Your topic')}",
        f"Your requested topic '{req.get('parsed_title', 'Your topic')}' is ready! View the full evidence dashboard now.",
        f"/signal/{issue_slug}" if issue_slug else "/signal",
    )

    return {"status": "completed", "issue_slug": issue_slug}
