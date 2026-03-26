"""Parity Billing — Portfolio analytics endpoints.

Aggregates provider_analyses data across all practices managed by a billing
company, using billing_company_id as the join key.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

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
    """Authenticate and return (user, bc_id, bc_role, bc_user_id, sb)."""
    sb = _get_supabase()
    user = get_current_user(authorization, sb)

    if user["company"]["type"] != "billing":
        raise HTTPException(status_code=403, detail="Billing access only")

    # Look up billing company
    bc_user = sb.table("billing_company_users").select(
        "id, billing_company_id, role"
    ).eq("email", user["email"]).eq("status", "active").limit(1).execute()

    if not bc_user.data:
        raise HTTPException(status_code=404, detail="No billing company found.")

    bc_id = bc_user.data[0]["billing_company_id"]
    bc_role = bc_user.data[0]["role"]
    bc_user_id = bc_user.data[0]["id"]
    return user, bc_id, bc_role, bc_user_id, sb


def _date_cutoff(days: int) -> str:
    """Return ISO timestamp for N days ago."""
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _get_scoped_practice_ids(bc_id: str, bc_user_id: str, bc_role: str, sb) -> list:
    """Return practice IDs visible to this user.

    Admin: all active practices for the billing company (returns None = no filter).
    Analyst/viewer: only assigned practices from analyst_practice_assignments.
    """
    if bc_role == "admin":
        return None  # No filter — admin sees everything

    assignments = sb.table("analyst_practice_assignments").select(
        "practice_id"
    ).eq("billing_company_id", bc_id).eq("analyst_user_id", bc_user_id).execute()

    return [a["practice_id"] for a in (assignments.data or [])]


def _scoped_analyses_query(sb, bc_id, bc_role, bc_user_id, cutoff, select_cols):
    """Build a provider_analyses query with analyst scoping applied."""
    scoped = _get_scoped_practice_ids(bc_id, bc_user_id, bc_role, sb)
    query = sb.table("provider_analyses").select(select_cols).eq(
        "billing_company_id", bc_id
    ).gte("created_at", cutoff)
    if scoped is not None:
        if not scoped:
            return None  # Analyst with no assignments — return empty
        query = query.in_("company_id", scoped)
    return query.execute()


# ---------------------------------------------------------------------------
# GET /api/billing/portfolio/summary
# ---------------------------------------------------------------------------

@router.get("/summary")
async def portfolio_summary(days: int = 90, authorization: str = Header(None)):
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_portfolio(authorization)
    cutoff = _date_cutoff(days)

    rows = _scoped_analyses_query(sb, bc_id, bc_role, bc_user_id, cutoff,
        "total_billed, total_paid, company_id, payer_name, result_json")

    if not rows or not rows.data:
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
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_portfolio(authorization)
    cutoff = _date_cutoff(days)

    rows = _scoped_analyses_query(sb, bc_id, bc_role, bc_user_id, cutoff,
        "company_id, total_billed, total_paid, result_json, created_at")

    # Group by practice (company_id)
    practice_map = {}  # company_id → {totals}
    for r in ((rows.data if rows else None) or []):
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
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_portfolio(authorization)
    cutoff = _date_cutoff(days)

    rows = _scoped_analyses_query(sb, bc_id, bc_role, bc_user_id, cutoff,
        "payer_name, company_id, total_billed, total_paid, result_json")

    payer_map = {}  # payer_name → {totals}
    for r in ((rows.data if rows else None) or []):
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
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_portfolio(authorization)
    cutoff = _date_cutoff(days)

    rows = _scoped_analyses_query(sb, bc_id, bc_role, bc_user_id, cutoff, "result_json, company_id")

    code_map = {}  # code → {count, amount}
    for r in ((rows.data if rows else None) or []):
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


# ---------------------------------------------------------------------------
# GET /api/billing/portfolio/specialties
# ---------------------------------------------------------------------------

@router.get("/specialties")
async def portfolio_specialties(authorization: str = Header(None)):
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_portfolio(authorization)

    # Get practice IDs — scoped by role
    scoped = _get_scoped_practice_ids(bc_id, bc_user_id, bc_role, sb)
    if scoped is not None:
        practice_ids = scoped
    else:
        links = sb.table("billing_company_practices").select(
            "practice_id"
        ).eq("billing_company_id", bc_id).eq("active", True).execute()
        practice_ids = [l["practice_id"] for l in (links.data or [])]

    if not practice_ids:
        return {"specialties": []}

    # Look up specialties from provider_profiles
    profiles = sb.table("provider_profiles").select(
        "specialty"
    ).in_("company_id", practice_ids).execute()

    specialties = sorted({
        p["specialty"] for p in (profiles.data or [])
        if p.get("specialty") and p["specialty"].strip()
    })

    return {"specialties": specialties}


# ---------------------------------------------------------------------------
# GET /api/billing/portfolio/payer-benchmark
# ---------------------------------------------------------------------------

@router.get("/payer-benchmark")
async def portfolio_payer_benchmark(
    days: int = 90,
    specialty: str = None,
    authorization: str = Header(None),
):
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_portfolio(authorization)
    cutoff = _date_cutoff(days)

    # If specialty filter, resolve matching practice IDs first
    filtered_practice_ids = None
    if specialty and specialty.strip():
        links = sb.table("billing_company_practices").select(
            "practice_id"
        ).eq("billing_company_id", bc_id).eq("active", True).execute()
        all_pids = [l["practice_id"] for l in (links.data or [])]

        if all_pids:
            profiles = sb.table("provider_profiles").select(
                "company_id"
            ).in_("company_id", all_pids).eq("specialty", specialty.strip()).execute()
            filtered_practice_ids = [p["company_id"] for p in (profiles.data or [])]

        if not filtered_practice_ids:
            return {"payers": [], "specialty_filter": specialty.strip()}

    # Apply role scoping
    scoped = _get_scoped_practice_ids(bc_id, bc_user_id, bc_role, sb)

    # Merge scoped + specialty filters
    final_filter = None
    if scoped is not None and filtered_practice_ids is not None:
        final_filter = list(set(scoped) & set(filtered_practice_ids))
    elif scoped is not None:
        final_filter = scoped
    elif filtered_practice_ids is not None:
        final_filter = filtered_practice_ids

    if final_filter is not None and not final_filter:
        return {"payers": [], "specialty_filter": (specialty.strip() if specialty else None)}

    # Query provider_analyses
    query = sb.table("provider_analyses").select(
        "payer_name, company_id, total_billed, total_paid, result_json"
    ).eq("billing_company_id", bc_id).gte("created_at", cutoff)

    if final_filter is not None:
        query = query.in_("company_id", final_filter)

    rows = query.execute()

    # Aggregate by payer
    payer_map = {}
    for r in (rows.data or []):
        payer = (r.get("payer_name") or "").strip()
        if not payer:
            continue
        if payer not in payer_map:
            payer_map[payer] = {
                "payer_name": payer,
                "total_billed": 0, "total_paid": 0,
                "line_count": 0, "paid_lines": 0,
                "practices": set(),
            }
        pm = payer_map[payer]
        pm["total_billed"] += float(r.get("total_billed") or 0)
        pm["total_paid"] += float(r.get("total_paid") or 0)
        pm["practices"].add(r.get("company_id"))

        rj = r.get("result_json") or {}
        lc = int(rj.get("line_count") or 0)
        denied = int(rj.get("denied_lines") or 0)
        pm["line_count"] += lc
        pm["paid_lines"] += (lc - denied)

    result = []
    for payer, pm in payer_map.items():
        adherence = round((pm["paid_lines"] / pm["line_count"] * 100), 2) if pm["line_count"] > 0 else 100.0
        result.append({
            "payer_name": payer,
            "adherence_rate": adherence,
            "practice_count": len(pm["practices"]),
            "claim_count": pm["line_count"],
            "total_billed": round(pm["total_billed"], 2),
            "total_paid": round(pm["total_paid"], 2),
        })

    # Default sort: ascending by adherence (worst first)
    result.sort(key=lambda x: x["adherence_rate"])
    return {
        "payers": result,
        "specialty_filter": (specialty.strip() if specialty else None),
    }


# ---------------------------------------------------------------------------
# GET /api/billing/portfolio/payer-anomalies
# ---------------------------------------------------------------------------

@router.get("/payer-anomalies")
async def portfolio_payer_anomalies(authorization: str = Header(None)):
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_portfolio(authorization)

    scoped = _get_scoped_practice_ids(bc_id, bc_user_id, bc_role, sb)
    now = datetime.now(timezone.utc)
    current_start = (now - timedelta(days=90)).isoformat()
    prior_start = (now - timedelta(days=180)).isoformat()

    # Current window: last 90 days
    cq = sb.table("provider_analyses").select(
        "payer_name, company_id, result_json"
    ).eq("billing_company_id", bc_id).gte("created_at", current_start)
    if scoped is not None:
        if not scoped:
            return {"anomalies": []}
        cq = cq.in_("company_id", scoped)
    current_rows = cq.execute()

    # Prior window: 90-180 days ago
    pq = sb.table("provider_analyses").select(
        "payer_name, company_id, result_json"
    ).eq("billing_company_id", bc_id).gte(
        "created_at", prior_start
    ).lt("created_at", current_start)
    if scoped is not None:
        pq = pq.in_("company_id", scoped)
    prior_rows = pq.execute()

    def _aggregate(rows_data):
        pmap = {}
        for r in (rows_data or []):
            payer = (r.get("payer_name") or "").strip()
            if not payer:
                continue
            if payer not in pmap:
                pmap[payer] = {"line_count": 0, "paid_lines": 0, "practices": set()}
            rj = r.get("result_json") or {}
            lc = int(rj.get("line_count") or 0)
            denied = int(rj.get("denied_lines") or 0)
            pmap[payer]["line_count"] += lc
            pmap[payer]["paid_lines"] += (lc - denied)
            pmap[payer]["practices"].add(r.get("company_id"))
        return pmap

    current_map = _aggregate(current_rows.data)
    prior_map = _aggregate(prior_rows.data)

    anomalies = []
    for payer, curr in current_map.items():
        prior = prior_map.get(payer)
        if not prior or prior["line_count"] == 0 or curr["line_count"] == 0:
            continue

        current_rate = round((curr["paid_lines"] / curr["line_count"] * 100), 2)
        prior_rate = round((prior["paid_lines"] / prior["line_count"] * 100), 2)
        delta = round(current_rate - prior_rate, 2)

        if delta < -10:  # adherence dropped more than 10 points
            anomalies.append({
                "payer_name": payer,
                "current_rate": current_rate,
                "prior_rate": prior_rate,
                "delta": delta,
                "practice_count": len(curr["practices"]),
            })

    anomalies.sort(key=lambda x: x["delta"])
    return {"anomalies": anomalies}


# ---------------------------------------------------------------------------
# GET /api/billing/portfolio/comparison
# ---------------------------------------------------------------------------

@router.get("/comparison")
async def portfolio_comparison(
    practice_a_id: str = None,
    practice_b_id: str = None,
    days: int = 90,
    authorization: str = Header(None),
):
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_portfolio(authorization)
    cutoff = _date_cutoff(days)

    if not practice_a_id or not practice_b_id:
        raise HTTPException(status_code=400, detail="Both practice_a_id and practice_b_id required.")

    # Validate both practices belong to this billing company
    for pid in [practice_a_id, practice_b_id]:
        link = sb.table("billing_company_practices").select("id").eq(
            "billing_company_id", bc_id
        ).eq("practice_id", pid).eq("active", True).limit(1).execute()
        if not link.data:
            raise HTTPException(status_code=404, detail=f"Practice {pid} not found in your company.")

    # Check analyst scoping
    scoped = _get_scoped_practice_ids(bc_id, bc_user_id, bc_role, sb)
    if scoped is not None:
        if practice_a_id not in scoped or practice_b_id not in scoped:
            raise HTTPException(status_code=403, detail="You do not have access to one or both practices.")

    # Get all analyses for portfolio average
    all_rows = _scoped_analyses_query(sb, bc_id, bc_role, bc_user_id, cutoff,
        "company_id, payer_name, total_billed, total_paid, result_json")

    def _compute_metrics(rows_data):
        total_billed = 0.0
        line_count = 0
        denied = 0
        payer_counts = {}
        denial_codes = {}

        for r in (rows_data or []):
            total_billed += float(r.get("total_billed") or 0)
            payer = (r.get("payer_name") or "").strip()
            if payer:
                payer_counts[payer] = payer_counts.get(payer, 0) + 1

            rj = r.get("result_json") or {}
            line_count += int(rj.get("line_count") or 0)
            denied += int(rj.get("denied_lines") or 0)

            for li in (rj.get("line_items") or []):
                if (li.get("paid_amount") or 0) != 0:
                    continue
                for adj in (li.get("adjustments") or []):
                    if not isinstance(adj, dict) or adj.get("group_code") != "CO":
                        continue
                    rc = adj.get("reason_code") or ""
                    if rc:
                        code = f"CO-{rc}"
                        denial_codes[code] = denial_codes.get(code, 0) + 1

        denial_rate = round((denied / line_count * 100), 2) if line_count > 0 else 0.0
        top_payer = max(payer_counts, key=payer_counts.get) if payer_counts else "—"
        top_denial = max(denial_codes, key=denial_codes.get) if denial_codes else "—"
        top_denial_desc = DENIAL_CODE_DESCRIPTIONS.get(top_denial.replace("CO-", ""), "") if top_denial != "—" else ""

        return {
            "denial_rate": denial_rate,
            "total_billed": round(total_billed, 2),
            "line_count": line_count,
            "top_payer": top_payer,
            "top_denial_reason": top_denial,
            "top_denial_description": top_denial_desc,
        }

    all_data = (all_rows.data if all_rows else []) or []
    practice_a_data = [r for r in all_data if r.get("company_id") == practice_a_id]
    practice_b_data = [r for r in all_data if r.get("company_id") == practice_b_id]

    # Resolve practice names
    names = {}
    for pid in [practice_a_id, practice_b_id]:
        nr = sb.table("companies").select("name").eq("id", pid).limit(1).execute()
        names[pid] = nr.data[0]["name"] if nr.data else "Unknown"

    metrics_a = _compute_metrics(practice_a_data)
    metrics_b = _compute_metrics(practice_b_data)
    metrics_avg = _compute_metrics(all_data)

    return {
        "practice_a": {"practice_id": practice_a_id, "practice_name": names[practice_a_id], **metrics_a},
        "practice_b": {"practice_id": practice_b_id, "practice_name": names[practice_b_id], **metrics_b},
        "portfolio_avg": metrics_avg,
    }


# ---------------------------------------------------------------------------
# GET /api/billing/portfolio/payer-detail
# ---------------------------------------------------------------------------

@router.get("/payer-detail")
async def portfolio_payer_detail(
    payer_name: str = None,
    days: int = 90,
    authorization: str = Header(None),
):
    """Detailed breakdown for a single payer across all practices."""
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_portfolio(authorization)

    if not payer_name or not payer_name.strip():
        raise HTTPException(status_code=400, detail="payer_name required.")

    payer_name = payer_name.strip()
    cutoff = _date_cutoff(days)

    rows = _scoped_analyses_query(sb, bc_id, bc_role, bc_user_id, cutoff,
        "company_id, payer_name, total_billed, total_paid, result_json, created_at")

    if not rows or not rows.data:
        return {"payer_name": payer_name, "practices": [], "denial_codes": [],
                "total_billed": 0, "total_paid": 0, "line_count": 0, "denied_lines": 0}

    # Filter to this payer
    payer_rows = [r for r in rows.data if (r.get("payer_name") or "").strip() == payer_name]

    if not payer_rows:
        return {"payer_name": payer_name, "practices": [], "denial_codes": [],
                "total_billed": 0, "total_paid": 0, "line_count": 0, "denied_lines": 0}

    # Per-practice breakdown
    practice_map = {}
    total_billed = 0.0
    total_paid = 0.0
    total_lines = 0
    total_denied = 0
    denial_code_map = {}

    for r in payer_rows:
        pid = r.get("company_id")
        tb = float(r.get("total_billed") or 0)
        tp = float(r.get("total_paid") or 0)
        rj = r.get("result_json") or {}
        lc = int(rj.get("line_count") or 0)
        den = int(rj.get("denied_lines") or 0)

        total_billed += tb
        total_paid += tp
        total_lines += lc
        total_denied += den

        if pid not in practice_map:
            practice_map[pid] = {
                "practice_id": pid, "total_billed": 0, "total_paid": 0,
                "line_count": 0, "denied_lines": 0, "analysis_count": 0,
            }
        pm = practice_map[pid]
        pm["total_billed"] += tb
        pm["total_paid"] += tp
        pm["line_count"] += lc
        pm["denied_lines"] += den
        pm["analysis_count"] += 1

        # Extract denial codes from line_items
        for li in (rj.get("line_items") or []):
            if (li.get("paid_amount") or 0) != 0:
                continue
            billed_amt = float(li.get("billed_amount") or 0)
            for adj in (li.get("adjustments") or []):
                if not isinstance(adj, dict) or adj.get("group_code") != "CO":
                    continue
                rc = adj.get("reason_code") or ""
                if not rc:
                    continue
                code = f"CO-{rc}"
                if code not in denial_code_map:
                    denial_code_map[code] = {
                        "code": code,
                        "description": DENIAL_CODE_DESCRIPTIONS.get(rc, ""),
                        "count": 0, "total_amount": 0,
                    }
                denial_code_map[code]["count"] += 1
                denial_code_map[code]["total_amount"] += billed_amt

    # Resolve practice names
    pids = list(practice_map.keys())
    names = {}
    if pids:
        nr = sb.table("companies").select("id, name").in_("id", pids).execute()
        for n in (nr.data or []):
            names[n["id"]] = n["name"]

    practices_result = []
    for pid, pm in practice_map.items():
        dr = round((pm["denied_lines"] / pm["line_count"] * 100), 2) if pm["line_count"] > 0 else 0.0
        practices_result.append({
            **pm,
            "practice_name": names.get(pid, "Unknown"),
            "denial_rate": dr,
            "total_billed": round(pm["total_billed"], 2),
            "total_paid": round(pm["total_paid"], 2),
        })
    practices_result.sort(key=lambda x: x["total_billed"], reverse=True)

    denial_codes = sorted(denial_code_map.values(), key=lambda x: x["count"], reverse=True)[:10]
    for dc in denial_codes:
        dc["total_amount"] = round(dc["total_amount"], 2)

    overall_denial_rate = round((total_denied / total_lines * 100), 2) if total_lines > 0 else 0.0

    return {
        "payer_name": payer_name,
        "total_billed": round(total_billed, 2),
        "total_paid": round(total_paid, 2),
        "line_count": total_lines,
        "denied_lines": total_denied,
        "denial_rate": overall_denial_rate,
        "practice_count": len(practices_result),
        "practices": practices_result,
        "denial_codes": denial_codes,
    }


# ===========================================================================
# Appeal ROI endpoints
# ===========================================================================

# ===========================================================================
# Appeal ROI — true cross-file recovery tracking via billing_claim_lines
# ===========================================================================


def _scoped_claim_lines_query(sb, bc_id, bc_role, bc_user_id, cutoff, select_cols):
    """Build a billing_claim_lines query with analyst scoping."""
    scoped = _get_scoped_practice_ids(bc_id, bc_user_id, bc_role, sb)
    query = sb.table("billing_claim_lines").select(select_cols).eq(
        "billing_company_id", bc_id
    ).gte("created_at", cutoff)
    if scoped is not None:
        if not scoped:
            return None
        query = query.in_("practice_id", scoped)
    return query.execute()


def _detect_recoveries(sb, bc_id, scoped_practice_ids=None):
    """Detect denied claims later paid across different 835 files.

    Matches by (practice_id, claim_number, cpt_code, date_of_service):
    - A denied line in an earlier job (by adjudication_date or created_at)
    - A paid line in a later job for the same claim

    Returns list of recovery dicts with recovered_amount.
    """
    # Get all denied lines
    dq = sb.table("billing_claim_lines").select(
        "id, practice_id, claim_number, cpt_code, date_of_service, "
        "billed_amount, payer_name, denial_codes, adjudication_date, created_at, job_id"
    ).eq("billing_company_id", bc_id).eq("status", "denied")
    if scoped_practice_ids is not None:
        if not scoped_practice_ids:
            return []
        dq = dq.in_("practice_id", scoped_practice_ids)
    denied_rows = dq.execute()

    if not denied_rows.data:
        return []

    # Get all paid lines
    pq = sb.table("billing_claim_lines").select(
        "id, practice_id, claim_number, cpt_code, date_of_service, "
        "paid_amount, payer_name, adjudication_date, created_at, job_id"
    ).eq("billing_company_id", bc_id).eq("status", "paid")
    if scoped_practice_ids is not None:
        pq = pq.in_("practice_id", scoped_practice_ids)
    paid_rows = pq.execute()

    if not paid_rows.data:
        return []

    # Build lookup of paid lines by match key
    paid_map = {}  # (practice_id, claim_number, cpt_code, dos) → [paid_lines]
    for p in paid_rows.data:
        key = (p["practice_id"], p.get("claim_number") or "", p.get("cpt_code") or "",
               str(p.get("date_of_service") or ""))
        if not key[1]:  # skip empty claim numbers
            continue
        paid_map.setdefault(key, []).append(p)

    recoveries = []
    matched_paid_ids = set()

    for d in denied_rows.data:
        key = (d["practice_id"], d.get("claim_number") or "", d.get("cpt_code") or "",
               str(d.get("date_of_service") or ""))
        if not key[1]:
            continue

        candidates = paid_map.get(key, [])
        for p in candidates:
            if p["id"] in matched_paid_ids:
                continue
            # Paid must be from a different (later) job
            if p["job_id"] == d["job_id"]:
                continue
            # Paid adjudication date should be after denied adjudication date
            d_adj = str(d.get("adjudication_date") or d.get("created_at") or "")
            p_adj = str(p.get("adjudication_date") or p.get("created_at") or "")
            if p_adj <= d_adj:
                continue

            matched_paid_ids.add(p["id"])
            recoveries.append({
                "denied_line_id": d["id"],
                "paid_line_id": p["id"],
                "practice_id": d["practice_id"],
                "payer_name": d.get("payer_name") or p.get("payer_name") or "",
                "claim_number": d.get("claim_number"),
                "cpt_code": d.get("cpt_code"),
                "date_of_service": str(d.get("date_of_service") or ""),
                "denied_amount": float(d.get("billed_amount") or 0),
                "recovered_amount": float(p.get("paid_amount") or 0),
                "denial_codes": d.get("denial_codes") or [],
                "recovery_adjudication_date": str(p.get("adjudication_date") or ""),
            })
            break  # One match per denied line

    return recoveries


# ---------------------------------------------------------------------------
# GET /api/billing/portfolio/appeal-roi
# ---------------------------------------------------------------------------

@router.get("/appeal-roi")
async def appeal_roi_summary(days: int = 180, authorization: str = Header(None)):
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_portfolio(authorization)
    cutoff = _date_cutoff(days)
    scoped = _get_scoped_practice_ids(bc_id, bc_user_id, bc_role, sb)

    # Query billing_claim_lines directly
    lines = _scoped_claim_lines_query(sb, bc_id, bc_role, bc_user_id, cutoff,
        "payer_name, billed_amount, paid_amount, status, date_of_service, adjudication_date")

    all_lines = (lines.data if lines else None) or []

    total_billed = sum(float(l.get("billed_amount") or 0) for l in all_lines)
    total_denied = sum(float(l.get("billed_amount") or 0) for l in all_lines if l.get("status") == "denied")
    total_lines = len(all_lines)
    denied_lines = sum(1 for l in all_lines if l.get("status") == "denied")

    # Avg days to payment
    days_vals = []
    for l in all_lines:
        dos = str(l.get("date_of_service") or "")[:10]
        adj = str(l.get("adjudication_date") or "")[:10]
        if dos and adj and len(dos) >= 8 and len(adj) >= 8:
            try:
                from datetime import date as dt_date
                d1 = dt_date.fromisoformat(dos)
                d2 = dt_date.fromisoformat(adj)
                diff = (d2 - d1).days
                if 0 <= diff <= 365:
                    days_vals.append(diff)
            except (ValueError, TypeError):
                pass
    avg_days = round(sum(days_vals) / len(days_vals)) if days_vals else None

    # True recovery detection
    recoveries = _detect_recoveries(sb, bc_id, scoped)
    total_recovered = sum(r["recovered_amount"] for r in recoveries)
    recovery_rate = round((total_recovered / total_denied * 100), 2) if total_denied > 0 else 0.0

    # Top payer by recovery
    payer_recovered = {}
    for r in recoveries:
        p = r.get("payer_name") or ""
        if p:
            payer_recovered[p] = payer_recovered.get(p, 0) + r["recovered_amount"]
    top_payer = max(payer_recovered, key=payer_recovered.get) if payer_recovered else "—"

    return {
        "total_recovered": round(total_recovered, 2),
        "total_denied": round(total_denied, 2),
        "total_billed": round(total_billed, 2),
        "recovery_rate": recovery_rate,
        "avg_days_to_payment": avg_days,
        "top_payer": top_payer,
        "total_lines": total_lines,
        "denied_lines": denied_lines,
        "recovery_count": len(recoveries),
    }


# ---------------------------------------------------------------------------
# GET /api/billing/portfolio/appeal-roi/by-payer
# ---------------------------------------------------------------------------

@router.get("/appeal-roi/by-payer")
async def appeal_roi_by_payer(days: int = 180, authorization: str = Header(None)):
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_portfolio(authorization)
    cutoff = _date_cutoff(days)
    scoped = _get_scoped_practice_ids(bc_id, bc_user_id, bc_role, sb)

    lines = _scoped_claim_lines_query(sb, bc_id, bc_role, bc_user_id, cutoff,
        "payer_name, billed_amount, paid_amount, status")
    all_lines = (lines.data if lines else None) or []

    # Aggregate by payer
    payer_map = {}
    for l in all_lines:
        payer = (l.get("payer_name") or "").strip()
        if not payer:
            continue
        if payer not in payer_map:
            payer_map[payer] = {"billed": 0, "denied": 0, "paid": 0}
        pm = payer_map[payer]
        pm["billed"] += float(l.get("billed_amount") or 0)
        if l.get("status") == "denied":
            pm["denied"] += float(l.get("billed_amount") or 0)
        pm["paid"] += float(l.get("paid_amount") or 0)

    # Get true recoveries by payer
    recoveries = _detect_recoveries(sb, bc_id, scoped)
    payer_recovered = {}
    for r in recoveries:
        p = r.get("payer_name") or ""
        if p:
            payer_recovered[p] = payer_recovered.get(p, 0) + r["recovered_amount"]

    result = []
    for payer, pm in payer_map.items():
        recovered = payer_recovered.get(payer, 0)
        rr = round((recovered / pm["denied"] * 100), 2) if pm["denied"] > 0 else 0.0
        result.append({
            "payer_name": payer,
            "total_billed": round(pm["billed"], 2),
            "total_denied": round(pm["denied"], 2),
            "total_recovered": round(recovered, 2),
            "recovery_rate": rr,
        })

    result.sort(key=lambda x: x["recovery_rate"])
    return {"payers": result}


# ---------------------------------------------------------------------------
# GET /api/billing/portfolio/appeal-roi/by-denial-type
# ---------------------------------------------------------------------------

@router.get("/appeal-roi/by-denial-type")
async def appeal_roi_by_denial_type(days: int = 180, authorization: str = Header(None)):
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_portfolio(authorization)
    cutoff = _date_cutoff(days)
    scoped = _get_scoped_practice_ids(bc_id, bc_user_id, bc_role, sb)

    # Get denied lines with their codes
    dq = sb.table("billing_claim_lines").select(
        "billed_amount, denial_codes, practice_id, claim_number, cpt_code, date_of_service"
    ).eq("billing_company_id", bc_id).eq("status", "denied").gte("created_at", cutoff)
    if scoped is not None:
        if not scoped:
            return {"denial_types": []}
        dq = dq.in_("practice_id", scoped)
    denied = dq.execute()

    # Get recoveries to map back to denial codes
    recoveries = _detect_recoveries(sb, bc_id, scoped)
    recovery_map = {}  # (practice_id, claim_number, cpt_code, dos) → recovered_amount
    for r in recoveries:
        key = (r["practice_id"], r["claim_number"], r["cpt_code"], r["date_of_service"])
        recovery_map[key] = r["recovered_amount"]

    code_map = {}
    for d in (denied.data or []):
        billed = float(d.get("billed_amount") or 0)
        codes = d.get("denial_codes") or []
        key = (d.get("practice_id"), d.get("claim_number") or "",
               d.get("cpt_code") or "", str(d.get("date_of_service") or ""))
        recovered = recovery_map.get(key, 0)

        for code in codes:
            raw = code.replace("CO-", "") if code.startswith("CO-") else code
            if code not in code_map:
                code_map[code] = {
                    "denial_code": code,
                    "description": DENIAL_CODE_DESCRIPTIONS.get(raw, ""),
                    "count": 0, "total_denied": 0, "total_recovered": 0,
                }
            code_map[code]["count"] += 1
            code_map[code]["total_denied"] += billed
            code_map[code]["total_recovered"] += recovered / max(len(codes), 1)

    result = sorted(code_map.values(), key=lambda x: x["count"], reverse=True)[:15]
    for r in result:
        r["total_denied"] = round(r["total_denied"], 2)
        r["total_recovered"] = round(r["total_recovered"], 2)
        r["recovery_rate"] = round(
            (r["total_recovered"] / r["total_denied"] * 100), 2
        ) if r["total_denied"] > 0 else 0.0

    return {"denial_types": result}


# ---------------------------------------------------------------------------
# GET /api/billing/portfolio/appeal-roi/trend
# ---------------------------------------------------------------------------

@router.get("/appeal-roi/trend")
async def appeal_roi_trend(days: int = 180, authorization: str = Header(None)):
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_portfolio(authorization)
    cutoff = _date_cutoff(days)
    scoped = _get_scoped_practice_ids(bc_id, bc_user_id, bc_role, sb)

    # Get denied lines with dates
    lines = _scoped_claim_lines_query(sb, bc_id, bc_role, bc_user_id, cutoff,
        "billed_amount, paid_amount, status, adjudication_date, created_at")
    all_lines = (lines.data if lines else None) or []

    # Get recoveries
    recoveries = _detect_recoveries(sb, bc_id, scoped)

    # Monthly buckets for denied amounts (by adjudication_date or created_at)
    denied_monthly = {}
    for l in all_lines:
        if l.get("status") != "denied":
            continue
        adj = str(l.get("adjudication_date") or l.get("created_at") or "")
        month = adj[:7] if len(adj) >= 7 else ""
        if month:
            denied_monthly[month] = denied_monthly.get(month, 0) + float(l.get("billed_amount") or 0)

    # Monthly buckets for recovered amounts (by recovery adjudication_date)
    recovered_monthly = {}
    for r in recoveries:
        adj = r.get("recovery_adjudication_date") or ""
        month = adj[:7] if len(adj) >= 7 else ""
        if month:
            recovered_monthly[month] = recovered_monthly.get(month, 0) + r["recovered_amount"]

    # Build at least 6 monthly buckets
    now = datetime.now(timezone.utc)
    num_months = max(6, days // 30)
    buckets = []
    seen = set()
    for i in range(num_months - 1, -1, -1):
        d = now - timedelta(days=i * 30)
        month_key = d.strftime("%Y-%m")
        if month_key not in seen:
            seen.add(month_key)
            buckets.append({
                "month": month_key,
                "total_recovered": round(recovered_monthly.get(month_key, 0), 2),
                "total_denied": round(denied_monthly.get(month_key, 0), 2),
            })

    for b in buckets:
        total = b["total_recovered"] + b["total_denied"]
        b["recovery_rate"] = round((b["total_recovered"] / total * 100), 2) if total > 0 else 0.0

    return {"trend": buckets}


# ===========================================================================
# PDF Report generation
# ===========================================================================

class GenerateReportRequest(BaseModel):
    practice_id: str
    report_type: str  # 'denial_summary' | 'payer_performance' | 'appeal_roi'
    date_range_days: int = 90


@router.post("/reports/generate")
async def generate_billing_report(req: GenerateReportRequest,
                                  authorization: str = Header(None)):
    from reportlab.platypus import SimpleDocTemplate, Spacer, PageBreak
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from utils.pdf_branding import (
        get_billing_branding, fetch_logo_bytes,
        build_cover_page, build_header_footer_func,
        build_kpi_row, build_data_table, _get_styles,
    )

    user, bc_id, bc_role, bc_user_id, sb = _require_billing_portfolio(authorization)
    cutoff = _date_cutoff(req.date_range_days)

    # Validate practice belongs to billing company
    link = sb.table("billing_company_practices").select("id").eq(
        "billing_company_id", bc_id
    ).eq("practice_id", req.practice_id).eq("active", True).limit(1).execute()
    if not link.data:
        raise HTTPException(status_code=404, detail="Practice not found.")

    # Check analyst scoping
    scoped = _get_scoped_practice_ids(bc_id, bc_user_id, bc_role, sb)
    if scoped is not None and req.practice_id not in scoped:
        raise HTTPException(status_code=403, detail="Access denied for this practice.")

    # Get practice name
    prac = sb.table("companies").select("name").eq("id", req.practice_id).limit(1).execute()
    practice_name = prac.data[0]["name"] if prac.data else "Unknown Practice"

    # Get branding
    branding = get_billing_branding(bc_id, sb)
    logo_bytes = fetch_logo_bytes(branding.get("logo_url"), sb)

    # Build date range label
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=req.date_range_days)
    date_label = f"Last {req.date_range_days} Days ({start.strftime('%b %d, %Y')} – {now.strftime('%b %d, %Y')})"

    # Get data for this practice
    lines = sb.table("billing_claim_lines").select(
        "payer_name, billed_amount, paid_amount, status, denial_codes, "
        "date_of_service, adjudication_date, cpt_code, claim_number"
    ).eq("billing_company_id", bc_id).eq(
        "practice_id", req.practice_id
    ).gte("created_at", cutoff).execute()

    all_lines = lines.data or []
    styles = _get_styles()

    # Build PDF
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                            topMargin=0.75 * inch, bottomMargin=0.75 * inch)

    story = build_cover_page(branding, practice_name, req.report_type,
                             date_label, logo_bytes)

    hf_func = build_header_footer_func(branding)

    if req.report_type == "denial_summary":
        story += _build_denial_summary_pages(all_lines, styles, practice_name)
    elif req.report_type == "payer_performance":
        story += _build_payer_performance_pages(all_lines, styles, practice_name)
    elif req.report_type == "appeal_roi":
        recoveries = _detect_recoveries(sb, bc_id, [req.practice_id])
        story += _build_appeal_roi_pages(all_lines, recoveries, styles, practice_name)
    else:
        raise HTTPException(status_code=400, detail="Invalid report_type.")

    doc.build(story, onLaterPages=hf_func)

    filename = f"{branding['company_name'].replace(' ', '_')}_{practice_name.replace(' ', '_')}_{req.report_type}_{now.strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        io.BytesIO(buf.getvalue()),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _build_denial_summary_pages(lines, styles, practice_name):
    """Build denial summary report pages."""
    from reportlab.lib.units import inch
    from utils.pdf_branding import build_kpi_row, build_data_table, Spacer, TEAL

    story = []
    story.append(Spacer(1, 0.2 * inch))

    total = len(lines)
    denied = [l for l in lines if l.get("status") == "denied"]
    denied_count = len(denied)
    denied_amount = sum(float(l.get("billed_amount") or 0) for l in denied)
    denial_rate = round((denied_count / total * 100), 2) if total > 0 else 0.0

    # KPIs
    story.append(build_kpi_row([
        {"label": "Total Lines", "value": f"{total:,}"},
        {"label": "Denied Lines", "value": f"{denied_count:,}"},
        {"label": "Denial Rate", "value": f"{denial_rate}%"},
        {"label": "Denied Amount", "value": f"${denied_amount:,.0f}"},
    ]))
    story.append(Spacer(1, 0.3 * inch))

    # Denial codes breakdown
    code_map = {}
    for l in denied:
        for code in (l.get("denial_codes") or []):
            raw = code.replace("CO-", "") if code.startswith("CO-") else code
            if code not in code_map:
                code_map[code] = {"count": 0, "amount": 0,
                                  "desc": DENIAL_CODE_DESCRIPTIONS.get(raw, "")}
            code_map[code]["count"] += 1
            code_map[code]["amount"] += float(l.get("billed_amount") or 0)

    if code_map:
        from reportlab.platypus import Paragraph
        story.append(Paragraph("<b>Denial Codes</b>", styles["heading2"]))
        sorted_codes = sorted(code_map.items(), key=lambda x: x[1]["count"], reverse=True)[:15]
        rows = []
        for code, data in sorted_codes:
            rows.append([code, data["desc"][:50], str(data["count"]), f"${data['amount']:,.0f}"])
        story.append(build_data_table(
            ["Code", "Description", "Count", "Amount"],
            rows, col_widths=[1 * inch, 3 * inch, 0.8 * inch, 1.2 * inch],
        ))

    # Payer breakdown
    payer_map = {}
    for l in denied:
        p = (l.get("payer_name") or "").strip()
        if p:
            payer_map[p] = payer_map.get(p, 0) + 1

    if payer_map:
        from reportlab.platypus import Paragraph
        story.append(Spacer(1, 0.3 * inch))
        story.append(Paragraph("<b>Denials by Payer</b>", styles["heading2"]))
        rows = [[p, str(c)] for p, c in sorted(payer_map.items(), key=lambda x: x[1], reverse=True)]
        story.append(build_data_table(
            ["Payer", "Denied Lines"], rows,
            col_widths=[4.5 * inch, 1.5 * inch],
        ))

    return story


def _build_payer_performance_pages(lines, styles, practice_name):
    """Build payer performance report pages."""
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph
    from utils.pdf_branding import build_kpi_row, build_data_table, Spacer

    story = []
    story.append(Spacer(1, 0.2 * inch))

    payer_map = {}
    for l in lines:
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

    total_billed = sum(pm["billed"] for pm in payer_map.values())
    total_paid = sum(pm["paid"] for pm in payer_map.values())
    payer_count = len(payer_map)

    story.append(build_kpi_row([
        {"label": "Total Billed", "value": f"${total_billed:,.0f}"},
        {"label": "Total Paid", "value": f"${total_paid:,.0f}"},
        {"label": "Payers", "value": str(payer_count)},
    ]))
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("<b>Payer Breakdown</b>", styles["heading2"]))
    rows = []
    for p, pm in sorted(payer_map.items(), key=lambda x: x[1]["billed"], reverse=True):
        dr = round((pm["denied"] / pm["lines"] * 100), 1) if pm["lines"] > 0 else 0
        rows.append([p, f"${pm['billed']:,.0f}", f"${pm['paid']:,.0f}",
                      str(pm["lines"]), f"{dr}%"])

    story.append(build_data_table(
        ["Payer", "Billed", "Paid", "Lines", "Denial %"],
        rows, col_widths=[2.2 * inch, 1.1 * inch, 1.1 * inch, 0.8 * inch, 0.8 * inch],
    ))

    return story


def _build_appeal_roi_pages(lines, recoveries, styles, practice_name):
    """Build appeal & recovery report pages."""
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph
    from utils.pdf_branding import build_kpi_row, build_data_table, Spacer

    story = []
    story.append(Spacer(1, 0.2 * inch))

    denied = [l for l in lines if l.get("status") == "denied"]
    total_denied = sum(float(l.get("billed_amount") or 0) for l in denied)
    total_recovered = sum(r["recovered_amount"] for r in recoveries)
    recovery_rate = round((total_recovered / total_denied * 100), 2) if total_denied > 0 else 0.0

    story.append(build_kpi_row([
        {"label": "Total Denied", "value": f"${total_denied:,.0f}"},
        {"label": "Total Recovered", "value": f"${total_recovered:,.0f}"},
        {"label": "Recovery Rate", "value": f"{recovery_rate}%"},
        {"label": "Recoveries", "value": str(len(recoveries))},
    ]))
    story.append(Spacer(1, 0.3 * inch))

    if recoveries:
        story.append(Paragraph("<b>Recovery Detail</b>", styles["heading2"]))
        rows = []
        for r in recoveries[:20]:
            rows.append([
                r.get("claim_number") or "—",
                r.get("cpt_code") or "—",
                r.get("payer_name") or "—",
                f"${r['denied_amount']:,.0f}",
                f"${r['recovered_amount']:,.0f}",
            ])
        story.append(build_data_table(
            ["Claim", "CPT", "Payer", "Denied", "Recovered"],
            rows, col_widths=[1.3 * inch, 0.8 * inch, 2 * inch, 1 * inch, 1 * inch],
        ))
    else:
        story.append(Paragraph(
            "No cross-file recoveries detected yet. Recoveries are identified when a "
            "denied claim in one remittance file appears as paid in a subsequent file.",
            styles["body"],
        ))

    return story
