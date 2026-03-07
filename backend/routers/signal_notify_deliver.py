"""Parity Signal — Email Notification Delivery endpoint.

Sweeps undelivered email notifications from signal_notifications,
sends them via Resend, and stamps delivered_at. Intended to be called
by a cron job or manually.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(
    prefix="/api/signal/notifications",
    tags=["signal-notifications"],
)

_sb = None


def _get_sb():
    global _sb
    if _sb is None:
        from supabase_client import supabase
        _sb = supabase
    return _sb


def _verify_cron_secret(request: Request):
    """Check X-Cron-Secret header against CRON_SECRET env var."""
    expected = os.environ.get("CRON_SECRET")
    if not expected:
        raise HTTPException(status_code=503, detail="CRON_SECRET not configured")
    provided = request.headers.get("X-Cron-Secret", "")
    if provided != expected:
        raise HTTPException(status_code=401, detail="Invalid cron secret")


@router.get("/deliver")
async def deliver_email_notifications(request: Request):
    """Send all pending email notifications via Resend.

    Auth: X-Cron-Secret header must match CRON_SECRET env var.

    1. Query signal_notifications where delivered_at IS NULL and delivery_method = 'email'
    2. Batch-fetch user emails from Supabase Auth
    3. Send each via Resend
    4. Stamp delivered_at on success
    """
    _verify_cron_secret(request)

    sb = _get_sb()
    if not sb:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    # 1. Fetch undelivered email notifications
    resp = (
        sb.table("signal_notifications")
        .select("id, user_id, title, body, deep_link")
        .is_("delivered_at", "null")
        .eq("delivery_method", "email")
        .execute()
    )
    pending = resp.data or []

    if not pending:
        return {"delivered": 0, "failed": 0, "skipped_no_email": 0}

    # 2. Collect unique user_ids and fetch emails
    unique_user_ids = list({row["user_id"] for row in pending})
    user_emails: Dict[str, str] = {}

    for uid in unique_user_ids:
        try:
            user_resp = sb.auth.admin.get_user_by_id(uid)
            email = getattr(user_resp, "user", None)
            if email:
                email = getattr(email, "email", None)
            if email:
                user_emails[uid] = email
        except Exception as exc:
            print(f"[deliver] Failed to fetch email for user {uid[:8]}...: {exc}")

    # 3. Send emails via Resend
    import resend

    resend_key = os.environ.get("RESEND_API_KEY")
    if not resend_key:
        raise HTTPException(status_code=503, detail="RESEND_API_KEY not configured")
    resend.api_key = resend_key

    frontend_url = os.environ.get("FRONTEND_URL", "https://civicscale.ai")
    delivered = 0
    failed = 0
    skipped_no_email = 0

    for notif in pending:
        uid = notif["user_id"]
        email = user_emails.get(uid)

        if not email:
            skipped_no_email += 1
            continue

        deep_link = notif.get("deep_link") or ""
        full_link = f"{frontend_url}{deep_link}" if deep_link else frontend_url

        html_body = (
            f"<h2>{notif['title']}</h2>"
            f"<p>{notif['body']}</p>"
            f'<p><a href="{full_link}">View in Parity Signal</a></p>'
            f"<hr>"
            f"<p style=\"color:#666;font-size:12px;\">"
            f"Parity Signal by CivicScale &mdash; "
            f"Evidence-based intelligence for healthcare decisions.</p>"
        )

        try:
            resend.Emails.send({
                "from": "Parity Signal <notifications@civicscale.ai>",
                "to": [email],
                "subject": notif["title"],
                "html": html_body,
            })

            # Stamp delivered_at
            sb.table("signal_notifications").update({
                "delivered_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", notif["id"]).execute()

            delivered += 1
        except Exception as exc:
            print(f"[deliver] Failed to send to {email}: {exc}")
            failed += 1

    return {
        "delivered": delivered,
        "failed": failed,
        "skipped_no_email": skipped_no_email,
    }
