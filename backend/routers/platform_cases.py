"""Platform Cases — unified case tracking for Provider appeals and Health disputes.

Endpoints:
  POST /api/platform/cases          — Create a new case
  GET  /api/platform/cases          — List cases (filtered by product, status)
  POST /api/platform/cases/resolve  — Record outcome
  POST /api/platform/send-case-reminders — Send reminders for stale cases
"""

import os
from datetime import datetime, timezone

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/platform", tags=["platform"])

_sb = None


def _get_sb():
    global _sb
    if _sb is None:
        from supabase_client import supabase
        _sb = supabase
    return _sb


@router.post("/cases")
async def create_case(body: dict):
    """Create a new platform case."""
    sb = _get_sb()
    if not sb:
        return JSONResponse(content={"error": "DB not available"}, status_code=500)

    required = ["product"]
    for field in required:
        if not body.get(field):
            return JSONResponse(content={"error": f"Missing required field: {field}"}, status_code=400)

    row = {
        "product": body["product"],
        "user_id": body.get("user_id"),
        "case_type": body.get("case_type"),
        "cpt_code": body.get("cpt_code"),
        "denial_code": body.get("denial_code"),
        "payer": body.get("payer"),
        "signal_topic_slug": body.get("signal_topic_slug"),
        "signal_score": body.get("signal_score"),
        "description": body.get("description"),
        "status": "open",
    }

    try:
        resp = sb.table("platform_cases").insert(row).execute()
        case_id = resp.data[0]["id"] if resp.data else None
        return JSONResponse(content={"ok": True, "case_id": case_id})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@router.get("/cases")
async def list_cases(
    product: str = Query(...),
    status: str = Query("open"),
    user_id: str = Query(None),
):
    """List cases filtered by product and status."""
    sb = _get_sb()
    if not sb:
        return JSONResponse(content={"error": "DB not available"}, status_code=500)

    try:
        q = sb.table("platform_cases").select("*").eq("product", product).eq("status", status)
        if user_id:
            q = q.eq("user_id", user_id)
        q = q.order("opened_at", desc=False)
        resp = q.execute()
        return JSONResponse(content={"cases": resp.data or []})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@router.post("/cases/resolve")
async def resolve_case(body: dict):
    """Record outcome for a case."""
    sb = _get_sb()
    if not sb:
        return JSONResponse(content={"error": "DB not available"}, status_code=500)

    case_id = body.get("case_id")
    outcome = body.get("outcome")

    valid_outcomes = {"won", "lost", "partial", "withdrawn"}
    if not case_id or outcome not in valid_outcomes:
        return JSONResponse(
            content={"error": f"Required: case_id and outcome ({', '.join(valid_outcomes)})"},
            status_code=400,
        )

    try:
        sb.table("platform_cases").update({
            "status": outcome,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "notes": body.get("notes"),
        }).eq("id", case_id).execute()
        return JSONResponse(content={"ok": True, "case_id": case_id, "status": outcome})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@router.post("/send-case-reminders")
async def send_case_reminders():
    """Send reminders for stale open cases.

    Provider: 30 days, Health: 14 days.
    Updates reminder_sent_at after sending.
    Returns count of reminders sent per product.
    """
    sb = _get_sb()
    if not sb:
        return JSONResponse(content={"error": "DB not available"}, status_code=500)

    provider_sent = 0
    health_sent = 0

    try:
        # Fetch all open cases without reminders
        resp = (
            sb.table("platform_cases")
            .select("*")
            .eq("status", "open")
            .is_("reminder_sent_at", "null")
            .execute()
        )
        cases = resp.data or []
        now = datetime.now(timezone.utc)

        for case in cases:
            opened = datetime.fromisoformat(case["opened_at"].replace("Z", "+00:00"))
            days_open = (now - opened).days
            product = case.get("product")
            email = None

            # Check threshold
            if product == "provider" and days_open < 30:
                continue
            elif product == "health" and days_open < 14:
                continue
            elif product not in ("provider", "health"):
                continue

            # Try to get user email
            user_id = case.get("user_id")
            if user_id:
                try:
                    user_resp = sb.auth.admin.get_user_by_id(user_id)
                    user = getattr(user_resp, "user", None)
                    if user:
                        email = getattr(user, "email", None)
                except Exception:
                    pass

            if email:
                # Send email via Resend
                try:
                    import resend
                    resend_key = os.environ.get("RESEND_API_KEY")
                    if resend_key:
                        resend.api_key = resend_key
                        cpt = case.get("cpt_code", "")
                        payer = case.get("payer", "")
                        desc = case.get("description", "")

                        if product == "provider":
                            subject = f"Follow up on your appeal — CPT {cpt}"
                            html = (
                                f"<p>You tracked an appeal {days_open} days ago for "
                                f"CPT {cpt} denied by {payer}.</p>"
                                f"<p>Please record the outcome — your data helps improve "
                                f"Signal's evidence recommendations.</p>"
                                f"<p><a href='https://provider.civicscale.ai'>Open Appeals →</a></p>"
                            )
                        else:
                            subject = "Follow up on your billing issue"
                            html = (
                                f"<p>You flagged a billing issue {days_open} days ago: {desc}</p>"
                                f"<p>Did you follow up? Mark it resolved or let us know if you need help.</p>"
                                f"<p><a href='https://health.civicscale.ai'>Open Issues →</a></p>"
                            )

                        resend.Emails.send({
                            "from": f"Parity {'Provider' if product == 'provider' else 'Health'} <notifications@civicscale.ai>",
                            "to": [email],
                            "subject": subject,
                            "html": html,
                        })
                except Exception as exc:
                    print(f"[Reminders] Email failed for case {case['id']}: {exc}")

            # Mark reminder sent regardless
            sb.table("platform_cases").update({
                "reminder_sent_at": now.isoformat(),
            }).eq("id", case["id"]).execute()

            if product == "provider":
                provider_sent += 1
            else:
                health_sent += 1

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

    return JSONResponse(content={
        "provider_reminders_sent": provider_sent,
        "health_reminders_sent": health_sent,
    })
