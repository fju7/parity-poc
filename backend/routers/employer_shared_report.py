"""Public shared report endpoint — no auth required.

GET /api/employer/shared-report/{share_token}
"""

from fastapi import APIRouter, HTTPException

from routers.employer_shared import _get_supabase

router = APIRouter(prefix="/api/employer", tags=["employer"])


@router.get("/shared-report/{share_token}")
async def get_shared_report(share_token: str):
    """Return benchmark result by share token. No auth required. Tracks views."""
    sb = _get_supabase()

    result = (
        sb.table("broker_client_benchmarks")
        .select("id, company_name, industry, state, carrier, employee_count, estimated_pepm, benchmark_result, broker_email, view_count, first_viewed_at, created_at")
        .eq("share_token", share_token)
        .limit(1)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Report not found or link has expired.")

    row = result.data[0]

    # Increment view count and set first_viewed_at
    update_data = {"view_count": (row.get("view_count") or 0) + 1}
    if not row.get("first_viewed_at"):
        from datetime import datetime, timezone
        update_data["first_viewed_at"] = datetime.now(timezone.utc).isoformat()

    sb.table("broker_client_benchmarks").update(update_data).eq("id", row["id"]).execute()

    # Fetch broker firm name
    broker_email = row.get("broker_email", "")
    firm_name = ""
    if broker_email:
        broker = sb.table("broker_accounts").select("firm_name, contact_name, email").eq("email", broker_email).execute()
        if broker.data:
            firm_name = broker.data[0].get("firm_name", "")

    return {
        "company_name": row["company_name"],
        "industry": row.get("industry"),
        "state": row.get("state"),
        "carrier": row.get("carrier"),
        "employee_count": row.get("employee_count"),
        "estimated_pepm": row.get("estimated_pepm"),
        "benchmark_result": row.get("benchmark_result"),
        "broker_firm": firm_name,
        "broker_email": broker_email,
        "created_at": row.get("created_at"),
    }
