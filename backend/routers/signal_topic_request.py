"""Parity Signal — Topic Request endpoint (Premium only).

Allows premium users to request new topics for Parity Signal to cover.
"""

from typing import List, Optional

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

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
            detail="Topic requests are available to Premium subscribers only."
        )


class TopicRequestCreate(BaseModel):
    topic_name: str
    description: str
    reference_urls: Optional[List[str]] = []


@router.post("/topic-requests")
async def create_topic_request(body: TopicRequestCreate, request: Request):
    """Submit a new topic request (premium only)."""
    user = await _get_authenticated_user(request)
    _check_premium(str(user.id))

    topic_name = body.topic_name.strip()
    description = body.description.strip()

    if not topic_name:
        raise HTTPException(status_code=400, detail="Topic name is required")
    if len(topic_name) > 200:
        raise HTTPException(status_code=400, detail="Topic name too long (max 200 chars)")
    if not description:
        raise HTTPException(status_code=400, detail="Description is required")
    if len(description) > 2000:
        raise HTTPException(status_code=400, detail="Description too long (max 2000 chars)")

    # Clean up reference URLs — filter out empty strings
    reference_urls = [u.strip() for u in (body.reference_urls or []) if u.strip()]

    sb = _get_sb()
    try:
        result = sb.table("signal_topic_requests").insert({
            "user_id": str(user.id),
            "topic_name": topic_name,
            "description": description,
            "reference_urls": reference_urls,
            "status": "submitted",
        }).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database insert failed: {exc}")

    if not result.data:
        return {"id": None, "status": "submitted", "topic_name": topic_name}

    return result.data[0]


@router.get("/topic-requests")
async def list_topic_requests(request: Request):
    """List the authenticated user's own topic requests."""
    user = await _get_authenticated_user(request)

    sb = _get_sb()
    result = sb.table("signal_topic_requests").select("*").eq(
        "user_id", str(user.id)
    ).order("created_at", desc=True).execute()

    return {"requests": result.data or []}
