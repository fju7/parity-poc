"""Parity Billing — Cross-practice escalation tracking endpoints."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from routers.auth import get_current_user
from routers.employer_shared import _get_supabase
from routers.billing_portfolio import (
    DENIAL_CODE_DESCRIPTIONS, _get_scoped_practice_ids,
)

router = APIRouter(prefix="/api/billing/escalations", tags=["billing-escalations"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_billing_escalations(authorization: str):
    """Authenticate and return (user, bc_id, bc_role, bc_user_id, sb)."""
    sb = _get_supabase()
    user = get_current_user(authorization, sb)

    if user["company"]["type"] != "billing":
        raise HTTPException(status_code=403, detail="Billing access only")

    bc_user = sb.table("billing_company_users").select(
        "id, billing_company_id, role"
    ).eq("email", user["email"]).eq("status", "active").limit(1).execute()

    if not bc_user.data:
        raise HTTPException(status_code=404, detail="No billing company found.")

    return (
        user,
        bc_user.data[0]["billing_company_id"],
        bc_user.data[0]["role"],
        bc_user.data[0]["id"],
        sb,
    )


# ---------------------------------------------------------------------------
# GET /api/billing/escalations/detect-patterns
# ---------------------------------------------------------------------------

@router.get("/detect-patterns")
async def detect_patterns(days: int = 180, authorization: str = Header(None)):
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_escalations(authorization)
    scoped = _get_scoped_practice_ids(bc_id, bc_user_id, bc_role, sb)

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # Fetch all denied lines
    query = sb.table("billing_claim_lines").select(
        "practice_id, payer_name, denial_codes, billed_amount, claim_number, "
        "adjudication_date"
    ).eq("billing_company_id", bc_id).eq("status", "denied").gte("created_at", cutoff)

    if scoped is not None:
        if not scoped:
            return {"patterns": []}
        query = query.in_("practice_id", scoped)

    rows = query.execute()

    if not rows.data:
        return {"patterns": []}

    # Unnest denial_codes in Python and group by (payer_name, denial_code)
    # pattern_key → {practices: {pid → {amount, claims, dates}}}
    pattern_map = {}

    for r in rows.data:
        payer = (r.get("payer_name") or "").strip()
        codes = r.get("denial_codes") or []
        pid = r.get("practice_id")
        billed = float(r.get("billed_amount") or 0)
        claim = r.get("claim_number") or ""
        adj_date = str(r.get("adjudication_date") or "")

        if not payer or not pid:
            continue

        for code in codes:
            key = (payer, code)
            if key not in pattern_map:
                pattern_map[key] = {
                    "payer_name": payer,
                    "denial_code": code,
                    "practices": {},
                    "min_date": adj_date or "",
                    "max_date": adj_date or "",
                }
            pm = pattern_map[key]

            if pid not in pm["practices"]:
                pm["practices"][pid] = {"amount": 0, "count": 0, "claims": []}
            pp = pm["practices"][pid]
            pp["amount"] += billed
            pp["count"] += 1
            if claim and len(pp["claims"]) < 5:
                pp["claims"].append(claim)

            if adj_date:
                if not pm["min_date"] or adj_date < pm["min_date"]:
                    pm["min_date"] = adj_date
                if not pm["max_date"] or adj_date > pm["max_date"]:
                    pm["max_date"] = adj_date

    # Filter to patterns affecting 2+ practices
    multi_practice = [
        pm for pm in pattern_map.values()
        if len(pm["practices"]) >= 2
    ]

    # Resolve practice names
    all_pids = set()
    for pm in multi_practice:
        all_pids.update(pm["practices"].keys())
    names = {}
    if all_pids:
        nr = sb.table("companies").select("id, name").in_("id", list(all_pids)).execute()
        for n in (nr.data or []):
            names[n["id"]] = n["name"]

    result = []
    for pm in multi_practice:
        raw_code = pm["denial_code"].replace("CO-", "") if pm["denial_code"].startswith("CO-") else pm["denial_code"]
        total_denied = sum(pp["amount"] for pp in pm["practices"].values())
        total_claims = sum(pp["count"] for pp in pm["practices"].values())
        practice_names = [names.get(pid, "Unknown") for pid in pm["practices"]]

        result.append({
            "payer_name": pm["payer_name"],
            "denial_code": pm["denial_code"],
            "denial_description": DENIAL_CODE_DESCRIPTIONS.get(raw_code, ""),
            "practice_count": len(pm["practices"]),
            "practice_names": practice_names,
            "total_denied_amount": round(total_denied, 2),
            "claim_count": total_claims,
            "date_range": f"{pm['min_date'][:10] if pm['min_date'] else ''} to {pm['max_date'][:10] if pm['max_date'] else ''}",
        })

    result.sort(key=lambda x: x["total_denied_amount"], reverse=True)
    return {"patterns": result}


# ---------------------------------------------------------------------------
# POST /api/billing/escalations — create escalation from pattern
# ---------------------------------------------------------------------------

class CreateEscalationRequest(BaseModel):
    payer_name: str
    denial_code: str
    denial_description: Optional[str] = None
    days: int = 180

@router.post("/")
async def create_escalation(req: CreateEscalationRequest, authorization: str = Header(None)):
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_escalations(authorization)

    if bc_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    payer = req.payer_name.strip()
    code = req.denial_code.strip()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=req.days)).isoformat()

    # Re-query billing_claim_lines for this specific pattern
    rows = sb.table("billing_claim_lines").select(
        "practice_id, billed_amount, claim_number, adjudication_date"
    ).eq("billing_company_id", bc_id).eq("status", "denied").eq(
        "payer_name", payer
    ).gte("created_at", cutoff).execute()

    # Filter to lines that have this denial code in their array
    matched = []
    for r in (rows.data or []):
        # Supabase returns denial_codes as a list
        line_codes = r.get("denial_codes") if hasattr(r, 'get') else []
        # But since we queried without the array filter, we need to check manually
        # Actually denial_codes isn't in the select — let me re-query with it
    # Re-query with denial_codes
    rows = sb.table("billing_claim_lines").select(
        "practice_id, billed_amount, claim_number, adjudication_date, denial_codes"
    ).eq("billing_company_id", bc_id).eq("status", "denied").eq(
        "payer_name", payer
    ).gte("created_at", cutoff).execute()

    practice_data = {}  # pid → {amount, count, claims, dates}
    for r in (rows.data or []):
        codes = r.get("denial_codes") or []
        if code not in codes:
            continue
        pid = r.get("practice_id")
        if not pid:
            continue
        if pid not in practice_data:
            practice_data[pid] = {"amount": 0, "count": 0, "claims": [], "min_date": "", "max_date": ""}
        pd = practice_data[pid]
        pd["amount"] += float(r.get("billed_amount") or 0)
        pd["count"] += 1
        claim = r.get("claim_number") or ""
        if claim and len(pd["claims"]) < 3:
            pd["claims"].append(claim)
        adj = str(r.get("adjudication_date") or "")
        if adj:
            if not pd["min_date"] or adj < pd["min_date"]:
                pd["min_date"] = adj
            if not pd["max_date"] or adj > pd["max_date"]:
                pd["max_date"] = adj

    if len(practice_data) < 2:
        raise HTTPException(status_code=400, detail="Pattern must affect 2+ practices.")

    # Resolve practice names
    pids = list(practice_data.keys())
    names = {}
    if pids:
        nr = sb.table("companies").select("id, name").in_("id", pids).execute()
        for n in (nr.data or []):
            names[n["id"]] = n["name"]

    total_denied = sum(pd["amount"] for pd in practice_data.values())
    total_claims = sum(pd["count"] for pd in practice_data.values())

    # Build global date range
    all_min = min((pd["min_date"] for pd in practice_data.values() if pd["min_date"]), default="")
    all_max = max((pd["max_date"] for pd in practice_data.values() if pd["max_date"]), default="")

    # Build evidence summary
    evidence = {
        "total_denied_amount": round(total_denied, 2),
        "claim_count": total_claims,
        "practice_count": len(practice_data),
        "date_range": f"{all_min[:10] if all_min else ''} to {all_max[:10] if all_max else ''}",
        "practices": [
            {
                "practice_id": pid,
                "practice_name": names.get(pid, "Unknown"),
                "denied_amount": round(pd["amount"], 2),
                "claim_count": pd["count"],
                "sample_claim_numbers": pd["claims"],
            }
            for pid, pd in practice_data.items()
        ],
    }

    raw_code = code.replace("CO-", "") if code.startswith("CO-") else code
    desc = req.denial_description or DENIAL_CODE_DESCRIPTIONS.get(raw_code, "")

    # Insert escalation
    esc = sb.table("billing_escalations").insert({
        "billing_company_id": bc_id,
        "payer_name": payer,
        "denial_code": code,
        "denial_description": desc,
        "status": "open",
        "affected_practice_count": len(practice_data),
        "total_denied_amount": round(total_denied, 2),
        "evidence_summary": evidence,
        "created_by_email": user["email"],
    }).execute()

    esc_id = esc.data[0]["id"]

    # Insert practice rows
    for pid, pd in practice_data.items():
        sb.table("billing_escalation_practices").insert({
            "escalation_id": esc_id,
            "practice_id": pid,
            "denied_amount": round(pd["amount"], 2),
            "claim_count": pd["count"],
            "sample_claim_numbers": pd["claims"] if pd["claims"] else None,
        }).execute()

    return {
        "created": True,
        "escalation_id": esc_id,
        "payer_name": payer,
        "denial_code": code,
        "affected_practices": len(practice_data),
        "total_denied_amount": round(total_denied, 2),
    }


# ---------------------------------------------------------------------------
# GET /api/billing/escalations — list escalations
# ---------------------------------------------------------------------------

@router.get("/")
async def list_escalations(status: str = None, authorization: str = Header(None)):
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_escalations(authorization)
    scoped = _get_scoped_practice_ids(bc_id, bc_user_id, bc_role, sb)

    query = sb.table("billing_escalations").select("*").eq(
        "billing_company_id", bc_id
    ).order("created_at", desc=True)

    if status:
        query = query.eq("status", status)

    rows = query.execute()

    # If analyst, filter to escalations involving their practices
    if scoped is not None:
        scoped_set = set(scoped)
        filtered = []
        for esc in (rows.data or []):
            ep = sb.table("billing_escalation_practices").select(
                "practice_id"
            ).eq("escalation_id", esc["id"]).execute()
            esc_pids = {p["practice_id"] for p in (ep.data or [])}
            if esc_pids & scoped_set:
                filtered.append(esc)
        return {"escalations": filtered}

    return {"escalations": rows.data or []}


# ---------------------------------------------------------------------------
# GET /api/billing/escalations/{escalation_id} — full detail
# ---------------------------------------------------------------------------

@router.get("/{escalation_id}")
async def get_escalation(escalation_id: str, authorization: str = Header(None)):
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_escalations(authorization)

    esc = sb.table("billing_escalations").select("*").eq(
        "id", escalation_id
    ).eq("billing_company_id", bc_id).limit(1).execute()

    if not esc.data:
        raise HTTPException(status_code=404, detail="Escalation not found.")

    # Get practices
    practices = sb.table("billing_escalation_practices").select(
        "*, companies(name)"
    ).eq("escalation_id", escalation_id).execute()

    practice_list = []
    for p in (practices.data or []):
        company = p.pop("companies", None) or {}
        practice_list.append({
            **p,
            "practice_name": company.get("name", "Unknown"),
        })

    result = esc.data[0]
    result["practices"] = practice_list
    return result


# ---------------------------------------------------------------------------
# PATCH /api/billing/escalations/{escalation_id}/status
# ---------------------------------------------------------------------------

class UpdateStatusRequest(BaseModel):
    status: str
    resolution_notes: Optional[str] = None
    recovered_amount: Optional[float] = None

@router.patch("/{escalation_id}/status")
async def update_escalation_status(escalation_id: str, req: UpdateStatusRequest,
                                    authorization: str = Header(None)):
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_escalations(authorization)

    if bc_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    valid_statuses = {"open", "in_progress", "resolved", "closed"}
    if req.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Use: {', '.join(valid_statuses)}")

    esc = sb.table("billing_escalations").select("status").eq(
        "id", escalation_id
    ).eq("billing_company_id", bc_id).limit(1).execute()

    if not esc.data:
        raise HTTPException(status_code=404, detail="Escalation not found.")

    # Validate transitions
    current = esc.data[0]["status"]
    valid_transitions = {
        "open": {"in_progress", "closed"},
        "in_progress": {"resolved", "closed"},
        "resolved": {"closed"},
        "closed": set(),
    }

    if req.status not in valid_transitions.get(current, set()):
        raise HTTPException(status_code=400,
            detail=f"Cannot transition from '{current}' to '{req.status}'.")

    updates = {
        "status": req.status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    if req.resolution_notes:
        updates["resolution_notes"] = req.resolution_notes.strip()

    if req.status == "resolved" and req.recovered_amount is not None:
        updates["recovered_amount"] = round(req.recovered_amount, 2)

    sb.table("billing_escalations").update(updates).eq("id", escalation_id).execute()

    return {"updated": True, "status": req.status}


# ---------------------------------------------------------------------------
# GET /api/billing/escalations/{escalation_id}/export — PDF evidence package
# ---------------------------------------------------------------------------

@router.get("/{escalation_id}/export")
async def export_escalation(escalation_id: str, authorization: str = Header(None)):
    import io
    from reportlab.platypus import SimpleDocTemplate, Spacer, PageBreak, Paragraph
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from utils.pdf_branding import (
        get_billing_branding, fetch_logo_bytes,
        build_cover_page, build_header_footer_func,
        build_kpi_row, build_data_table, _get_styles,
        TEAL, NAVY, SLATE,
    )

    user, bc_id, bc_role, bc_user_id, sb = _require_billing_escalations(authorization)

    # Analyst scoping check
    scoped = _get_scoped_practice_ids(bc_id, bc_user_id, bc_role, sb)

    esc = sb.table("billing_escalations").select("*").eq(
        "id", escalation_id
    ).eq("billing_company_id", bc_id).limit(1).execute()

    if not esc.data:
        raise HTTPException(status_code=404, detail="Escalation not found.")

    e = esc.data[0]

    # Analyst can only export if escalation involves their practices
    if scoped is not None:
        ep = sb.table("billing_escalation_practices").select("practice_id").eq(
            "escalation_id", escalation_id
        ).execute()
        esc_pids = {p["practice_id"] for p in (ep.data or [])}
        if not (esc_pids & set(scoped)):
            raise HTTPException(status_code=403, detail="Access denied.")

    # Get practices with names
    practices = sb.table("billing_escalation_practices").select(
        "*, companies(name)"
    ).eq("escalation_id", escalation_id).execute()

    practice_list = []
    for p in (practices.data or []):
        company = p.pop("companies", None) or {}
        practice_list.append({**p, "practice_name": company.get("name", "Unknown")})

    # Branding
    branding = get_billing_branding(bc_id, sb)
    logo_bytes = fetch_logo_bytes(branding.get("logo_url"), sb)
    styles = _get_styles()

    evidence = e.get("evidence_summary") or {}
    payer = e.get("payer_name") or ""
    code = e.get("denial_code") or ""
    desc = e.get("denial_description") or ""
    status = e.get("status") or "open"
    total_denied = float(e.get("total_denied_amount") or 0)
    date_range = evidence.get("date_range") or ""
    claim_count = evidence.get("claim_count") or 0
    practice_count = e.get("affected_practice_count") or len(practice_list)

    now_str = datetime.now(timezone.utc).strftime("%B %d, %Y")

    # Build PDF
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                            topMargin=0.75 * inch, bottomMargin=0.75 * inch)

    story = []

    # --- Page 1: Cover ---
    story.append(Spacer(1, 1.2 * inch))

    if logo_bytes:
        try:
            from reportlab.platypus import Image
            img = Image(io.BytesIO(logo_bytes))
            max_h = 80
            ratio = img.imageWidth / img.imageHeight if img.imageHeight else 1
            img.drawHeight = max_h
            img.drawWidth = max_h * ratio
            img.hAlign = "CENTER"
            story.append(img)
            story.append(Spacer(1, 0.3 * inch))
        except Exception:
            pass

    story.append(Paragraph(branding["company_name"], styles["title"]))
    if branding.get("header_text"):
        story.append(Paragraph(branding["header_text"], styles["header_text"]))

    story.append(Spacer(1, 0.15 * inch))
    from reportlab.platypus import HRFlowable
    story.append(HRFlowable(width="60%", thickness=2, color=TEAL, hAlign="CENTER"))
    story.append(Spacer(1, 0.4 * inch))

    story.append(Paragraph("Escalation Evidence Package", styles["subtitle"]))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(f"<b>Payer:</b> {payer}", styles["body"]))
    story.append(Paragraph(f"<b>Denial Code:</b> {code} — {desc}", styles["body"]))
    story.append(Paragraph(f"<b>Status:</b> {status.replace('_', ' ').title()}", styles["body"]))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(f"Generated: {now_str}", styles["body"]))

    if branding.get("footer_text"):
        story.append(Spacer(1, 1.5 * inch))
        story.append(Paragraph(branding["footer_text"], styles["footer"]))

    story.append(PageBreak())

    # --- Page 2: Executive Summary ---
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("<b>Executive Summary</b>", styles["heading2"]))
    story.append(Spacer(1, 0.1 * inch))

    story.append(build_kpi_row([
        {"label": "Total Denied", "value": f"${total_denied:,.0f}"},
        {"label": "Affected Practices", "value": str(practice_count)},
        {"label": "Affected Claims", "value": str(claim_count)},
        {"label": "Date Range", "value": date_range or "—"},
    ]))
    story.append(Spacer(1, 0.3 * inch))

    # Narrative
    narrative = (
        f"{payer} has systematically denied claims with code {code}"
        f" ({desc})" if desc else f"{payer} has systematically denied claims with code {code}"
    )
    narrative += (
        f" across {practice_count} practice{'s' if practice_count != 1 else ''}"
        f" managed by {branding['company_name']},"
        f" totaling ${total_denied:,.2f} in denied claims"
    )
    if date_range:
        narrative += f" between {date_range}"
    narrative += (
        ". This pattern suggests a systematic payer-side policy"
        " rather than individual coding errors."
    )
    story.append(Paragraph(narrative, styles["body"]))
    story.append(Spacer(1, 0.2 * inch))

    # Recovery summary (if resolved)
    if status == "resolved":
        recovered = float(e.get("recovered_amount") or 0)
        recovery_rate = round((recovered / total_denied * 100), 2) if total_denied > 0 else 0.0
        resolution_notes = e.get("resolution_notes") or ""

        story.append(Paragraph("<b>Recovery Summary</b>", styles["heading2"]))
        story.append(build_kpi_row([
            {"label": "Recovered Amount", "value": f"${recovered:,.0f}"},
            {"label": "Recovery Rate", "value": f"{recovery_rate}%"},
        ]))
        if resolution_notes:
            story.append(Spacer(1, 0.1 * inch))
            story.append(Paragraph(f"<b>Resolution Notes:</b> {resolution_notes}", styles["body"]))
        story.append(Spacer(1, 0.2 * inch))

    story.append(PageBreak())

    # --- Page 3: Affected Practices ---
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("<b>Affected Practices</b>", styles["heading2"]))

    prac_rows = []
    for p in practice_list:
        samples = (p.get("sample_claim_numbers") or [])[:3]
        prac_rows.append([
            p["practice_name"],
            f"${float(p.get('denied_amount') or 0):,.0f}",
            str(p.get("claim_count") or 0),
            ", ".join(samples) if samples else "—",
        ])
    # Subtotal
    prac_rows.append([
        "TOTAL",
        f"${total_denied:,.0f}",
        str(claim_count),
        "",
    ])

    story.append(build_data_table(
        ["Practice Name", "Denied Amount", "Claims", "Sample Claim Numbers"],
        prac_rows,
        col_widths=[2.2 * inch, 1.1 * inch, 0.8 * inch, 2.2 * inch],
    ))

    # --- Page 4: All sample claims ---
    all_claims = []
    for p in practice_list:
        for cn in (p.get("sample_claim_numbers") or []):
            all_claims.append((p["practice_name"], cn))

    if all_claims:
        story.append(Spacer(1, 0.3 * inch))
        story.append(Paragraph("<b>Claim Detail</b>", styles["heading2"]))
        claim_rows = [[pn, cn] for pn, cn in all_claims]
        story.append(build_data_table(
            ["Practice", "Claim Number"],
            claim_rows,
            col_widths=[3 * inch, 3 * inch],
        ))

    hf = build_header_footer_func(branding)
    doc.build(story, onLaterPages=hf)

    safe_payer = payer.replace(" ", "_")[:30]
    safe_code = code.replace("-", "")
    filename = f"Escalation_{safe_payer}_{safe_code}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"

    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        io.BytesIO(buf.getvalue()),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
