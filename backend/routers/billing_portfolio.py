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

def _extract_line_stats(rows_data):
    """Extract line-level stats from provider_analyses result_json rows.

    Returns (lines, denied_lines, denied_amount, payer_map, denial_code_map, monthly_map).
    Each denied line: paid_amount == 0 and has a CO adjustment.
    Recovery proxy: total_paid represents payment realization.
    """
    payer_map = {}       # payer → {billed, paid, denied_amount, denied_count}
    denial_code_map = {} # code → {count, denied_amount, recovered_amount}
    monthly_map = {}     # YYYY-MM → {paid, denied_amount}
    total_billed = 0.0
    total_paid = 0.0
    total_denied_amount = 0.0
    total_lines = 0
    total_denied_lines = 0
    days_sum = 0
    days_count = 0

    for r in (rows_data or []):
        payer = (r.get("payer_name") or "").strip()
        rj = r.get("result_json") or {}
        created = r.get("created_at") or ""
        month = created[:7] if len(created) >= 7 else ""

        tb = float(r.get("total_billed") or 0)
        tp = float(r.get("total_paid") or 0)
        total_billed += tb
        total_paid += tp

        if payer and payer not in payer_map:
            payer_map[payer] = {"billed": 0, "paid": 0, "denied_amount": 0, "denied_count": 0}

        if month and month not in monthly_map:
            monthly_map[month] = {"paid": 0, "denied_amount": 0}

        for li in (rj.get("line_items") or []):
            total_lines += 1
            li_billed = float(li.get("billed_amount") or 0)
            li_paid = float(li.get("paid_amount") or 0)

            # Days to payment
            dos = li.get("date_of_service") or ""
            adj_date = li.get("adjudication_date") or ""
            if dos and adj_date and len(dos) >= 8 and len(adj_date) >= 8:
                try:
                    from datetime import date as dt_date
                    d1 = dt_date.fromisoformat(dos[:10])
                    d2 = dt_date.fromisoformat(adj_date[:10])
                    diff = (d2 - d1).days
                    if 0 <= diff <= 365:
                        days_sum += diff
                        days_count += 1
                except (ValueError, TypeError):
                    pass

            is_denied = (
                li_paid == 0
                and any(
                    isinstance(a, dict) and a.get("group_code") == "CO"
                    for a in (li.get("adjustments") or [])
                )
            )

            if payer:
                payer_map[payer]["billed"] += li_billed
                payer_map[payer]["paid"] += li_paid

            if is_denied:
                total_denied_lines += 1
                total_denied_amount += li_billed
                if payer:
                    payer_map[payer]["denied_amount"] += li_billed
                    payer_map[payer]["denied_count"] += 1
                if month:
                    monthly_map[month]["denied_amount"] += li_billed

                # Extract denial codes
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
                            "count": 0, "denied_amount": 0,
                        }
                    denial_code_map[code]["count"] += 1
                    denial_code_map[code]["denied_amount"] += li_billed
            else:
                if month:
                    monthly_map[month]["paid"] += li_paid

    avg_days = round(days_sum / days_count) if days_count > 0 else None

    return {
        "total_billed": total_billed,
        "total_paid": total_paid,
        "total_denied_amount": total_denied_amount,
        "total_lines": total_lines,
        "total_denied_lines": total_denied_lines,
        "avg_days_to_payment": avg_days,
        "payer_map": payer_map,
        "denial_code_map": denial_code_map,
        "monthly_map": monthly_map,
    }


# ---------------------------------------------------------------------------
# GET /api/billing/portfolio/appeal-roi
# ---------------------------------------------------------------------------

@router.get("/appeal-roi")
async def appeal_roi_summary(days: int = 180, authorization: str = Header(None)):
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_portfolio(authorization)
    cutoff = _date_cutoff(days)

    rows = _scoped_analyses_query(sb, bc_id, bc_role, bc_user_id, cutoff,
        "payer_name, total_billed, total_paid, result_json, created_at, company_id")

    stats = _extract_line_stats((rows.data if rows else None) or [])

    recovery_rate = round(
        (stats["total_paid"] / stats["total_billed"] * 100), 2
    ) if stats["total_billed"] > 0 else 0.0

    # Top payer by total paid
    top_payer = "—"
    if stats["payer_map"]:
        top_payer = max(stats["payer_map"], key=lambda k: stats["payer_map"][k]["paid"])

    return {
        "total_recovered": round(stats["total_paid"], 2),
        "total_denied": round(stats["total_denied_amount"], 2),
        "total_billed": round(stats["total_billed"], 2),
        "recovery_rate": recovery_rate,
        "avg_days_to_payment": stats["avg_days_to_payment"],
        "top_payer": top_payer,
        "total_lines": stats["total_lines"],
        "denied_lines": stats["total_denied_lines"],
    }


# ---------------------------------------------------------------------------
# GET /api/billing/portfolio/appeal-roi/by-payer
# ---------------------------------------------------------------------------

@router.get("/appeal-roi/by-payer")
async def appeal_roi_by_payer(days: int = 180, authorization: str = Header(None)):
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_portfolio(authorization)
    cutoff = _date_cutoff(days)

    rows = _scoped_analyses_query(sb, bc_id, bc_role, bc_user_id, cutoff,
        "payer_name, total_billed, total_paid, result_json, created_at, company_id")

    stats = _extract_line_stats((rows.data if rows else None) or [])

    result = []
    for payer, pm in stats["payer_map"].items():
        rr = round((pm["paid"] / pm["billed"] * 100), 2) if pm["billed"] > 0 else 0.0
        result.append({
            "payer_name": payer,
            "total_billed": round(pm["billed"], 2),
            "total_denied": round(pm["denied_amount"], 2),
            "total_recovered": round(pm["paid"], 2),
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

    rows = _scoped_analyses_query(sb, bc_id, bc_role, bc_user_id, cutoff,
        "payer_name, total_billed, total_paid, result_json, created_at, company_id")

    stats = _extract_line_stats((rows.data if rows else None) or [])

    result = []
    for code, dm in stats["denial_code_map"].items():
        result.append({
            "denial_code": dm["code"],
            "description": dm["description"],
            "total_denied": round(dm["denied_amount"], 2),
            "count": dm["count"],
        })

    result.sort(key=lambda x: x["count"], reverse=True)
    return {"denial_types": result[:15]}


# ---------------------------------------------------------------------------
# GET /api/billing/portfolio/appeal-roi/trend
# ---------------------------------------------------------------------------

@router.get("/appeal-roi/trend")
async def appeal_roi_trend(days: int = 180, authorization: str = Header(None)):
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_portfolio(authorization)
    cutoff = _date_cutoff(days)

    rows = _scoped_analyses_query(sb, bc_id, bc_role, bc_user_id, cutoff,
        "payer_name, total_billed, total_paid, result_json, created_at, company_id")

    stats = _extract_line_stats((rows.data if rows else None) or [])

    # Build at least 6 monthly buckets
    from datetime import date as dt_date
    now = datetime.now(timezone.utc)
    num_months = max(6, days // 30)
    buckets = []
    for i in range(num_months - 1, -1, -1):
        d = now - timedelta(days=i * 30)
        month_key = d.strftime("%Y-%m")
        if month_key not in [b["month"] for b in buckets]:
            buckets.append({"month": month_key, "total_recovered": 0, "total_denied": 0})

    # Fill with actual data
    for b in buckets:
        m = stats["monthly_map"].get(b["month"])
        if m:
            b["total_recovered"] = round(m["paid"], 2)
            b["total_denied"] = round(m["denied_amount"], 2)
        b["recovery_rate"] = round(
            (b["total_recovered"] / (b["total_recovered"] + b["total_denied"]) * 100), 2
        ) if (b["total_recovered"] + b["total_denied"]) > 0 else 0.0

    return {"trend": buckets}
