"""Public shared report endpoint — no auth required.

GET /api/employer/shared-report/{share_token}
"""

from fastapi import APIRouter, HTTPException

from routers.employer_shared import _get_supabase
from utils.email import send_email

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
    is_first_view = not row.get("first_viewed_at")
    update_data = {"view_count": (row.get("view_count") or 0) + 1}
    if is_first_view:
        from datetime import datetime, timezone
        update_data["first_viewed_at"] = datetime.now(timezone.utc).isoformat()

    sb.table("broker_client_benchmarks").update(update_data).eq("id", row["id"]).execute()

    # Fetch broker info
    broker_email = row.get("broker_email", "")
    broker_name = ""
    firm_name = ""
    broker_logo_url = None
    if broker_email:
        broker = sb.table("broker_accounts").select("firm_name, contact_name, email, logo_url").eq("email", broker_email).execute()
        if broker.data:
            firm_name = broker.data[0].get("firm_name", "")
            broker_name = broker.data[0].get("contact_name", "")
            broker_logo_url = broker.data[0].get("logo_url")

    # Notify broker on first view
    if is_first_view and broker_email and broker_name:
        company = row.get("company_name", "A client")
        send_email(
            to=broker_email,
            subject=f"{company} just viewed their benchmark report",
            html=f"""
            <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 32px;">
                <h2 style="color: #1B3A5C; margin-bottom: 16px;">Report Viewed</h2>
                <p style="color: #475569; font-size: 15px; line-height: 1.8;">Hi {broker_name},</p>
                <p style="color: #475569; font-size: 15px; line-height: 1.8;">
                    <strong>{company}</strong> just viewed the benchmark report you shared with them.
                </p>
                <p style="color: #475569; font-size: 15px; line-height: 1.8;">
                    This is a good time to follow up &mdash; they're actively looking at their numbers.
                </p>
                <p style="color: #475569; font-size: 15px; line-height: 1.8;">
                    View their full profile: <a href="https://broker.civicscale.ai/dashboard" style="color: #0D7377;">broker.civicscale.ai/dashboard</a>
                </p>
                <p style="color: #475569; font-size: 15px; line-height: 1.8;">
                    &mdash; CivicScale
                </p>
            </div>
            """,
        )

    return {
        "company_name": row["company_name"],
        "industry": row.get("industry"),
        "state": row.get("state"),
        "carrier": row.get("carrier"),
        "employee_count": row.get("employee_count"),
        "estimated_pepm": row.get("estimated_pepm"),
        "benchmark_result": row.get("benchmark_result"),
        "broker_name": broker_name,
        "broker_firm": firm_name,
        "broker_email": broker_email,
        "broker_logo_url": broker_logo_url,
        "created_at": row.get("created_at"),
    }
