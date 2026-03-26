"""Parity Billing — Team management and analyst assignment endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from routers.auth import get_current_user
from routers.employer_shared import _get_supabase

router = APIRouter(prefix="/api/billing/team", tags=["billing-team"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_billing_team(authorization: str):
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
# Pydantic models
# ---------------------------------------------------------------------------

class AssignmentRequest(BaseModel):
    analyst_user_id: str
    practice_ids: List[str]


# ---------------------------------------------------------------------------
# GET /api/billing/team/analysts — list all users with assignments
# ---------------------------------------------------------------------------

@router.get("/analysts")
async def list_analysts(authorization: str = Header(None)):
    user, bc_id, bc_role, _, sb = _require_billing_team(authorization)

    # Get all billing_company_users
    users = sb.table("billing_company_users").select(
        "id, email, full_name, role, status, created_at"
    ).eq("billing_company_id", bc_id).order("created_at").execute()

    # Get all assignments for this billing company
    assignments = sb.table("analyst_practice_assignments").select(
        "analyst_user_id, practice_id, companies(id, name)"
    ).eq("billing_company_id", bc_id).execute()

    # Build assignment map: user_id → [{practice_id, practice_name}]
    assign_map = {}
    for a in (assignments.data or []):
        uid = a["analyst_user_id"]
        practice = a.get("companies") or {}
        if uid not in assign_map:
            assign_map[uid] = []
        assign_map[uid].append({
            "practice_id": a["practice_id"],
            "practice_name": practice.get("name", "Unknown"),
        })

    result = []
    for u in (users.data or []):
        result.append({
            "user_id": u["id"],
            "email": u["email"],
            "full_name": u.get("full_name"),
            "role": u["role"],
            "status": u["status"],
            "assigned_practices": assign_map.get(u["id"], []),
        })

    return {"analysts": result}


# ---------------------------------------------------------------------------
# POST /api/billing/team/assignments — replace assignments for an analyst
# ---------------------------------------------------------------------------

@router.post("/assignments")
async def update_assignments(req: AssignmentRequest, authorization: str = Header(None)):
    user, bc_id, bc_role, _, sb = _require_billing_team(authorization)

    if bc_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    analyst_id = req.analyst_user_id.strip()
    practice_ids = [p.strip() for p in req.practice_ids if p.strip()]

    # Verify analyst belongs to this billing company
    analyst = sb.table("billing_company_users").select("id, role").eq(
        "id", analyst_id
    ).eq("billing_company_id", bc_id).limit(1).execute()

    if not analyst.data:
        raise HTTPException(status_code=404, detail="Analyst not found in your company.")

    # Verify all practice_ids belong to this billing company
    if practice_ids:
        links = sb.table("billing_company_practices").select("practice_id").eq(
            "billing_company_id", bc_id
        ).eq("active", True).execute()
        valid_ids = {l["practice_id"] for l in (links.data or [])}
        for pid in practice_ids:
            if pid not in valid_ids:
                raise HTTPException(status_code=400, detail=f"Practice {pid} is not linked to your company.")

    # Delete existing assignments for this analyst
    sb.table("analyst_practice_assignments").delete().eq(
        "analyst_user_id", analyst_id
    ).eq("billing_company_id", bc_id).execute()

    # Insert new assignments
    for pid in practice_ids:
        sb.table("analyst_practice_assignments").insert({
            "billing_company_id": bc_id,
            "analyst_user_id": analyst_id,
            "practice_id": pid,
            "assigned_by_email": user["email"],
        }).execute()

    return {"updated": True, "analyst_user_id": analyst_id, "practice_count": len(practice_ids)}
