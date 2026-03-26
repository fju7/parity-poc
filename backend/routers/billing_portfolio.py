"""Parity Billing — Portfolio analytics endpoints.

Aggregates provider_analyses data across all practices managed by a billing
company, using billing_company_id as the join key.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Header, HTTPException

from routers.auth import get_current_user
from routers.employer_shared import _get_supabase

router = APIRouter(prefix="/api/billing/portfolio", tags=["billing-portfolio"])


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

# Common CARC (Claim Adjustment Reason Code) descriptions
DENIAL_CODE_DESCRIPTIONS = {
    "1": "Deductible amount",
    "2": "Coinsurance amount",
    "3": "Co-payment amount",
    "4": "Procedure code inconsistent with modifier or not payable",
    "5": "Procedure code inconsistent with place of service",
    "16": "Claim/service lacks information needed for adjudication",
    "18": "Exact duplicate claim/service",
    "22": "Care may be covered by another payer",
    "23": "Payment adjusted — charges covered under capitation",
    "24": "Charges covered by savings plan",
    "27": "Expenses incurred after coverage terminated",
    "29": "Time limit for filing has expired",
    "31": "Patient cannot be identified as our insured",
    "35": "Lifetime benefit maximum reached",
    "45": "Charges exceed your contracted/legislated fee arrangement",
    "50": "Non-covered services (not deemed medically necessary)",
    "59": "Processed based on multiple/bilateral procedure rules",
    "96": "Non-covered charges",
    "97": "Payment adjusted — not paid separately",
    "109": "Claim/service not covered by this payer/contractor",
    "119": "Benefit maximum for this time period has been reached",
    "140": "Patient/insured health ID number and name do not match",
    "167": "Diagnosis not covered",
    "197": "Precertification/authorization/notification absent",
    "204": "Service/equipment/drug not covered by patient benefit plan",
    "226": "Information requested not furnished — resubmit",
    "242": "Services not provided by network/primary care providers",
    "A1": "Claim PPS Capital Day Outlier Amount",
    "A2": "Claim PPS Capital Cost Outlier Amount",
    "B1": "Non-covered visits",
    "B7": "Provider not certified for procedure",
}


def _require_billing_portfolio(authorization: str):
    """Authenticate and return (user, billing_company, sb)."""
    sb = _get_supabase()
    user = get_current_user(authorization, sb)

    if user["company"]["type"] != "billing":
        raise HTTPException(status_code=403, detail="Billing access only")

    # Look up billing company
    bc_user = sb.table("billing_company_users").select(
        "billing_company_id"
    ).eq("email", user["email"]).eq("status", "active").limit(1).execute()

    if not bc_user.data:
        raise HTTPException(status_code=404, detail="No billing company found.")

    bc_id = bc_user.data[0]["billing_company_id"]
    return user, bc_id, sb


def _date_cutoff(days: int) -> str:
    """Return ISO timestamp for N days ago."""
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


# ---------------------------------------------------------------------------
# GET /api/billing/portfolio/summary
# ---------------------------------------------------------------------------

@router.get("/summary")
async def portfolio_summary(days: int = 90, authorization: str = Header(None)):
    user, bc_id, sb = _require_billing_portfolio(authorization)
    cutoff = _date_cutoff(days)

    rows = sb.table("provider_analyses").select(
        "total_billed, total_paid, company_id, payer_name, result_json"
    ).eq("billing_company_id", bc_id).gte("created_at", cutoff).execute()

    if not rows.data:
        return {
            "total_billed": 0, "total_paid": 0, "total_lines": 0,
            "overall_denial_rate": 0, "practice_count": 0, "payer_count": 0,
            "analysis_count": 0,
        }

    total_billed = 0.0
    total_paid = 0.0
    total_lines = 0
    total_denied = 0
    practices = set()
    payers = set()

    for r in rows.data:
        total_billed += float(r.get("total_billed") or 0)
        total_paid += float(r.get("total_paid") or 0)
        practices.add(r.get("company_id"))
        payer = r.get("payer_name") or ""
        if payer:
            payers.add(payer)

        rj = r.get("result_json") or {}
        total_lines += int(rj.get("line_count") or 0)
        total_denied += int(rj.get("denied_lines") or 0)

    denial_rate = round((total_denied / total_lines * 100), 2) if total_lines > 0 else 0.0

    return {
        "total_billed": round(total_billed, 2),
        "total_paid": round(total_paid, 2),
        "total_lines": total_lines,
        "overall_denial_rate": denial_rate,
        "practice_count": len(practices),
        "payer_count": len(payers),
        "analysis_count": len(rows.data),
    }


# ---------------------------------------------------------------------------
# GET /api/billing/portfolio/practices
# ---------------------------------------------------------------------------

@router.get("/practices")
async def portfolio_practices(days: int = 90, authorization: str = Header(None)):
    user, bc_id, sb = _require_billing_portfolio(authorization)
    cutoff = _date_cutoff(days)

    rows = sb.table("provider_analyses").select(
        "company_id, total_billed, total_paid, result_json, created_at"
    ).eq("billing_company_id", bc_id).gte("created_at", cutoff).execute()

    # Group by practice (company_id)
    practice_map = {}  # company_id → {totals}
    for r in (rows.data or []):
        pid = r.get("company_id")
        if not pid:
            continue
        if pid not in practice_map:
            practice_map[pid] = {
                "practice_id": pid,
                "total_billed": 0, "total_paid": 0,
                "line_count": 0, "denied_lines": 0,
                "analysis_count": 0, "last_upload": None,
            }
        p = practice_map[pid]
        p["total_billed"] += float(r.get("total_billed") or 0)
        p["total_paid"] += float(r.get("total_paid") or 0)
        p["analysis_count"] += 1

        rj = r.get("result_json") or {}
        p["line_count"] += int(rj.get("line_count") or 0)
        p["denied_lines"] += int(rj.get("denied_lines") or 0)

        created = r.get("created_at")
        if created and (p["last_upload"] is None or created > p["last_upload"]):
            p["last_upload"] = created

    # Resolve practice names
    practice_ids = list(practice_map.keys())
    names = {}
    if practice_ids:
        name_rows = sb.table("companies").select("id, name").in_("id", practice_ids).execute()
        for nr in (name_rows.data or []):
            names[nr["id"]] = nr["name"]

    result = []
    for pid, p in practice_map.items():
        denial_rate = round((p["denied_lines"] / p["line_count"] * 100), 2) if p["line_count"] > 0 else 0.0
        result.append({
            "practice_id": pid,
            "practice_name": names.get(pid, "Unknown"),
            "total_billed": round(p["total_billed"], 2),
            "total_paid": round(p["total_paid"], 2),
            "denial_rate": denial_rate,
            "line_count": p["line_count"],
            "analysis_count": p["analysis_count"],
            "last_upload": p["last_upload"],
        })

    result.sort(key=lambda x: x["total_billed"], reverse=True)
    return {"practices": result}


# ---------------------------------------------------------------------------
# GET /api/billing/portfolio/payers
# ---------------------------------------------------------------------------

@router.get("/payers")
async def portfolio_payers(days: int = 90, authorization: str = Header(None)):
    user, bc_id, sb = _require_billing_portfolio(authorization)
    cutoff = _date_cutoff(days)

    rows = sb.table("provider_analyses").select(
        "payer_name, company_id, total_billed, total_paid, result_json"
    ).eq("billing_company_id", bc_id).gte("created_at", cutoff).execute()

    payer_map = {}  # payer_name → {totals}
    for r in (rows.data or []):
        payer = (r.get("payer_name") or "").strip()
        if not payer:
            continue
        if payer not in payer_map:
            payer_map[payer] = {
                "payer_name": payer,
                "total_billed": 0, "total_paid": 0,
                "line_count": 0, "denied_lines": 0,
                "practices": set(),
            }
        pm = payer_map[payer]
        pm["total_billed"] += float(r.get("total_billed") or 0)
        pm["total_paid"] += float(r.get("total_paid") or 0)
        pm["practices"].add(r.get("company_id"))

        rj = r.get("result_json") or {}
        pm["line_count"] += int(rj.get("line_count") or 0)
        pm["denied_lines"] += int(rj.get("denied_lines") or 0)

    result = []
    for payer, pm in payer_map.items():
        denial_rate = round((pm["denied_lines"] / pm["line_count"] * 100), 2) if pm["line_count"] > 0 else 0.0
        result.append({
            "payer_name": payer,
            "total_billed": round(pm["total_billed"], 2),
            "total_paid": round(pm["total_paid"], 2),
            "denial_rate": denial_rate,
            "line_count": pm["line_count"],
            "practice_count": len(pm["practices"]),
        })

    result.sort(key=lambda x: x["total_billed"], reverse=True)
    return {"payers": result}


# ---------------------------------------------------------------------------
# GET /api/billing/portfolio/denial-reasons
# ---------------------------------------------------------------------------

@router.get("/denial-reasons")
async def portfolio_denial_reasons(days: int = 90, authorization: str = Header(None)):
    user, bc_id, sb = _require_billing_portfolio(authorization)
    cutoff = _date_cutoff(days)

    rows = sb.table("provider_analyses").select(
        "result_json"
    ).eq("billing_company_id", bc_id).gte("created_at", cutoff).execute()

    code_map = {}  # code → {count, amount}
    for r in (rows.data or []):
        rj = r.get("result_json") or {}
        for li in (rj.get("line_items") or []):
            paid = float(li.get("paid_amount") or 0)
            if paid != 0:
                continue
            billed = float(li.get("billed_amount") or 0)
            for adj in (li.get("adjustments") or []):
                if not isinstance(adj, dict):
                    continue
                if adj.get("group_code") != "CO":
                    continue
                reason = adj.get("reason_code") or adj.get("code") or ""
                if not reason:
                    continue
                code = f"CO-{reason}" if not reason.startswith("CO-") else reason
                raw_reason = reason.replace("CO-", "")
                if code not in code_map:
                    code_map[code] = {
                        "denial_code": code,
                        "denial_description": DENIAL_CODE_DESCRIPTIONS.get(raw_reason, ""),
                        "count": 0,
                        "total_amount": 0,
                    }
                code_map[code]["count"] += 1
                code_map[code]["total_amount"] += billed

    result = sorted(code_map.values(), key=lambda x: x["count"], reverse=True)[:10]
    for r in result:
        r["total_amount"] = round(r["total_amount"], 2)

    return {"denial_reasons": result}
