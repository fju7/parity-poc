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
