"""Parity Billing — Practice Client Portal endpoints.

Read-only portal for practices to view their billing data with the billing
company's branding. Uses product='billing_portal' session tokens.
"""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from routers.auth import _generate_otp, _send_otp_email, OTP_EXPIRY_MINUTES, SESSION_EXPIRY_DAYS
from routers.employer_shared import _get_supabase
from routers.billing_portfolio import DENIAL_CODE_DESCRIPTIONS, _detect_recoveries

router = APIRouter(prefix="/api/billing/portal", tags=["billing-portal"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class PortalSendOtpRequest(BaseModel):
    email: str
    practice_id: str

class PortalVerifyOtpRequest(BaseModel):
    email: str
    code: str
    practice_id: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_portal_session(authorization: str, sb=None):
    """Validate portal session token. Returns (email, practice_id, bc_id, settings)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization header")

    token = authorization.split(" ", 1)[1].strip()
    if not sb:
        sb = _get_supabase()

    now = datetime.now(timezone.utc).isoformat()
    session = sb.table("sessions").select("*").eq("id", token).eq(
        "product", "billing_portal"
    ).gt("expires_at", now).execute()

    if not session.data:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")

    s = session.data[0]
    practice_id = s.get("company_id")  # For portal sessions, company_id = practice_id
    email = s.get("email")

    # Refresh last_active_at
    sb.table("sessions").update({"last_active_at": now}).eq("id", token).execute()

    # Look up portal settings to get billing_company_id
    ps = sb.table("practice_portal_settings").select("*").eq(
        "practice_id", practice_id
    ).eq("portal_enabled", True).limit(1).execute()

    if not ps.data:
        raise HTTPException(status_code=403, detail="Portal access not enabled for this practice.")

    settings = ps.data[0]
    return email, practice_id, settings["billing_company_id"], settings, sb


# ---------------------------------------------------------------------------
# POST /api/billing/portal/send-otp
# ---------------------------------------------------------------------------

@router.post("/send-otp")
async def portal_send_otp(req: PortalSendOtpRequest):
    sb = _get_supabase()
    email = req.email.strip().lower()
    practice_id = req.practice_id.strip()

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email required")

    # Validate portal is enabled and email matches
    ps = sb.table("practice_portal_settings").select(
        "portal_contact_email, portal_enabled"
    ).eq("practice_id", practice_id).limit(1).execute()

    if not ps.data:
        raise HTTPException(status_code=403, detail="No portal configured for this practice.")

    row = ps.data[0]
    if not row.get("portal_enabled"):
        raise HTTPException(status_code=403, detail="Portal is not enabled for this practice.")

    portal_email = (row.get("portal_contact_email") or "").strip().lower()
    if portal_email and portal_email != email:
        raise HTTPException(status_code=403, detail="Email does not match the portal contact for this practice.")

    code = _generate_otp()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat()

    sb.table("otp_codes").delete().eq("email", email).eq("product", "billing_portal").execute()
    sb.table("otp_codes").insert({
        "email": email,
        "code": code,
        "expires_at": expires_at,
        "product": "billing_portal",
    }).execute()

    _send_otp_email(email, code, "billing")
    return {"sent": True, "email": email}


# ---------------------------------------------------------------------------
# POST /api/billing/portal/verify-otp
# ---------------------------------------------------------------------------

@router.post("/verify-otp")
async def portal_verify_otp(req: PortalVerifyOtpRequest, request: Request):
    sb = _get_supabase()
    email = req.email.strip().lower()
    practice_id = req.practice_id.strip()
    now = datetime.now(timezone.utc)

    otp = sb.table("otp_codes").select("*").eq("email", email).eq(
        "code", req.code.strip()
    ).eq("product", "billing_portal").gt("expires_at", now.isoformat()).execute()

    if not otp.data:
        raise HTTPException(status_code=400, detail="Invalid or expired code.")

    sb.table("otp_codes").delete().eq("email", email).eq("product", "billing_portal").execute()

    # Verify portal settings
    ps = sb.table("practice_portal_settings").select("*").eq(
        "practice_id", practice_id
    ).eq("portal_enabled", True).limit(1).execute()

    if not ps.data:
        raise HTTPException(status_code=403, detail="Portal not enabled for this practice.")

    settings = ps.data[0]
    bc_id = settings["billing_company_id"]

    # Get billing company name for branding
    bc = sb.table("billing_companies").select("company_name").eq("id", bc_id).limit(1).execute()
    bc_name = bc.data[0]["company_name"] if bc.data else ""

    # Get practice name
    prac = sb.table("companies").select("name").eq("id", practice_id).limit(1).execute()
    practice_name = prac.data[0]["name"] if prac.data else ""

    # Create portal session — product='billing_portal', company_id=practice_id
    session_id = str(uuid.uuid4())
    expires_at = (now + timedelta(days=SESSION_EXPIRY_DAYS)).isoformat()

    sb.table("sessions").insert({
        "id": session_id,
        "email": email,
        "company_id": practice_id,
        "product": "billing_portal",
        "expires_at": expires_at,
        "last_active_at": now.isoformat(),
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent", "")[:255],
    }).execute()

    return {
        "verified": True,
        "token": session_id,
        "email": email,
        "practice_id": practice_id,
        "practice_name": practice_name,
        "billing_company_name": bc_name,
        "portal_settings": {
            "show_denial_summary": settings.get("show_denial_summary", False),
            "show_payer_performance": settings.get("show_payer_performance", False),
            "show_appeal_roi": settings.get("show_appeal_roi", False),
            "show_generate_report": settings.get("show_generate_report", False),
        },
    }


# ---------------------------------------------------------------------------
# GET /api/billing/portal/me
# ---------------------------------------------------------------------------

@router.get("/me")
async def portal_me(authorization: str = Header(None)):
    email, practice_id, bc_id, settings, sb = _require_portal_session(authorization)

    prac = sb.table("companies").select("name").eq("id", practice_id).limit(1).execute()
    practice_name = prac.data[0]["name"] if prac.data else ""

    bc = sb.table("billing_companies").select("company_name, logo_url").eq("id", bc_id).limit(1).execute()
    bc_data = bc.data[0] if bc.data else {}

    return {
        "email": email,
        "practice_id": practice_id,
        "practice_name": practice_name,
        "billing_company_id": bc_id,
        "billing_company_name": bc_data.get("company_name", ""),
        "logo_url": bc_data.get("logo_url"),
        "portal_settings": {
            "show_denial_summary": settings.get("show_denial_summary", False),
            "show_payer_performance": settings.get("show_payer_performance", False),
            "show_appeal_roi": settings.get("show_appeal_roi", False),
            "show_generate_report": settings.get("show_generate_report", False),
        },
    }


# ---------------------------------------------------------------------------
# GET /api/billing/portal/denial-summary
# ---------------------------------------------------------------------------

@router.get("/denial-summary")
async def portal_denial_summary(days: int = 90, authorization: str = Header(None)):
    email, practice_id, bc_id, settings, sb = _require_portal_session(authorization)

    if not settings.get("show_denial_summary"):
        raise HTTPException(status_code=403, detail="Section not enabled.")

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    lines = sb.table("billing_claim_lines").select(
        "billed_amount, paid_amount, status, denial_codes, payer_name"
    ).eq("billing_company_id", bc_id).eq("practice_id", practice_id).gte("created_at", cutoff).execute()

    all_lines = lines.data or []
    total = len(all_lines)
    denied = [l for l in all_lines if l.get("status") == "denied"]
    denied_count = len(denied)
    denied_amount = sum(float(l.get("billed_amount") or 0) for l in denied)
    denial_rate = round((denied_count / total * 100), 2) if total > 0 else 0.0

    # Denial codes
    code_map = {}
    for l in denied:
        for code in (l.get("denial_codes") or []):
            raw = code.replace("CO-", "") if code.startswith("CO-") else code
            if code not in code_map:
                code_map[code] = {"code": code, "description": DENIAL_CODE_DESCRIPTIONS.get(raw, ""),
                                  "count": 0, "amount": 0}
            code_map[code]["count"] += 1
            code_map[code]["amount"] += float(l.get("billed_amount") or 0)

    codes = sorted(code_map.values(), key=lambda x: x["count"], reverse=True)[:10]
    for c in codes:
        c["amount"] = round(c["amount"], 2)

    # Payer breakdown
    payer_map = {}
    for l in denied:
        p = (l.get("payer_name") or "").strip()
        if p:
            payer_map[p] = payer_map.get(p, 0) + 1

    payers = [{"payer_name": p, "denied_count": c} for p, c in
              sorted(payer_map.items(), key=lambda x: x[1], reverse=True)]

    return {
        "total_lines": total, "denied_count": denied_count,
        "denied_amount": round(denied_amount, 2), "denial_rate": denial_rate,
        "denial_codes": codes, "payer_breakdown": payers,
    }


# ---------------------------------------------------------------------------
# GET /api/billing/portal/payer-performance
# ---------------------------------------------------------------------------

@router.get("/payer-performance")
async def portal_payer_performance(days: int = 90, authorization: str = Header(None)):
    email, practice_id, bc_id, settings, sb = _require_portal_session(authorization)

    if not settings.get("show_payer_performance"):
        raise HTTPException(status_code=403, detail="Section not enabled.")

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    lines = sb.table("billing_claim_lines").select(
        "payer_name, billed_amount, paid_amount, status"
    ).eq("billing_company_id", bc_id).eq("practice_id", practice_id).gte("created_at", cutoff).execute()

    payer_map = {}
    for l in (lines.data or []):
        p = (l.get("payer_name") or "").strip()
        if not p:
            continue
        if p not in payer_map:
            payer_map[p] = {"billed": 0, "paid": 0, "lines": 0, "denied": 0}
        pm = payer_map[p]
        pm["billed"] += float(l.get("billed_amount") or 0)
        pm["paid"] += float(l.get("paid_amount") or 0)
        pm["lines"] += 1
        if l.get("status") == "denied":
            pm["denied"] += 1

    result = []
    for p, pm in payer_map.items():
        dr = round((pm["denied"] / pm["lines"] * 100), 2) if pm["lines"] > 0 else 0.0
        result.append({
            "payer_name": p,
            "total_billed": round(pm["billed"], 2),
            "total_paid": round(pm["paid"], 2),
            "line_count": pm["lines"],
            "denial_rate": dr,
        })

    result.sort(key=lambda x: x["total_billed"], reverse=True)
    return {"payers": result}


# ---------------------------------------------------------------------------
# GET /api/billing/portal/appeal-roi
# ---------------------------------------------------------------------------

@router.get("/appeal-roi")
async def portal_appeal_roi(days: int = 180, authorization: str = Header(None)):
    email, practice_id, bc_id, settings, sb = _require_portal_session(authorization)

    if not settings.get("show_appeal_roi"):
        raise HTTPException(status_code=403, detail="Section not enabled.")

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    lines = sb.table("billing_claim_lines").select(
        "billed_amount, paid_amount, status"
    ).eq("billing_company_id", bc_id).eq("practice_id", practice_id).gte("created_at", cutoff).execute()

    all_lines = lines.data or []
    total_denied = sum(float(l.get("billed_amount") or 0) for l in all_lines if l.get("status") == "denied")

    recoveries = _detect_recoveries(sb, bc_id, [practice_id])
    total_recovered = sum(r["recovered_amount"] for r in recoveries)
    recovery_rate = round((total_recovered / total_denied * 100), 2) if total_denied > 0 else 0.0

    return {
        "total_denied": round(total_denied, 2),
        "total_recovered": round(total_recovered, 2),
        "recovery_rate": recovery_rate,
        "recovery_count": len(recoveries),
    }


# ---------------------------------------------------------------------------
# POST /api/billing/portal/generate-report
# ---------------------------------------------------------------------------

@router.post("/generate-report")
async def portal_generate_report(authorization: str = Header(None)):
    from reportlab.platypus import SimpleDocTemplate
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from utils.pdf_branding import (
        get_billing_branding, fetch_logo_bytes,
        build_cover_page, build_header_footer_func,
    )
    # Import report builders from billing_portfolio
    from routers.billing_portfolio import (
        _build_denial_summary_pages, _build_payer_performance_pages,
        _build_appeal_roi_pages, _detect_recoveries, _get_styles,
    )

    email, practice_id, bc_id, settings, sb = _require_portal_session(authorization)

    if not settings.get("show_generate_report"):
        raise HTTPException(status_code=403, detail="Report generation not enabled.")

    branding = get_billing_branding(bc_id, sb)
    logo_bytes = fetch_logo_bytes(branding.get("logo_url"), sb)

    prac = sb.table("companies").select("name").eq("id", practice_id).limit(1).execute()
    practice_name = prac.data[0]["name"] if prac.data else "Practice"

    now = datetime.now(timezone.utc)
    date_label = f"Last 90 Days ({(now - timedelta(days=90)).strftime('%b %d, %Y')} – {now.strftime('%b %d, %Y')})"

    cutoff = (now - timedelta(days=90)).isoformat()
    lines = sb.table("billing_claim_lines").select(
        "payer_name, billed_amount, paid_amount, status, denial_codes, "
        "date_of_service, adjudication_date, cpt_code, claim_number"
    ).eq("billing_company_id", bc_id).eq("practice_id", practice_id).gte("created_at", cutoff).execute()

    all_lines = lines.data or []
    styles = _get_styles()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                            topMargin=0.75 * inch, bottomMargin=0.75 * inch)

    story = build_cover_page(branding, practice_name, "denial_summary", date_label, logo_bytes)

    # Include all enabled sections
    if settings.get("show_denial_summary"):
        story += _build_denial_summary_pages(all_lines, styles, practice_name)
    if settings.get("show_payer_performance"):
        from reportlab.platypus import PageBreak
        story.append(PageBreak())
        story += _build_payer_performance_pages(all_lines, styles, practice_name)
    if settings.get("show_appeal_roi"):
        from reportlab.platypus import PageBreak
        story.append(PageBreak())
        recoveries = _detect_recoveries(sb, bc_id, [practice_id])
        story += _build_appeal_roi_pages(all_lines, recoveries, styles, practice_name)

    hf = build_header_footer_func(branding)
    doc.build(story, onLaterPages=hf)

    filename = f"{practice_name.replace(' ', '_')}_Report_{now.strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        io.BytesIO(buf.getvalue()),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
