"""Backfill billing_claim_lines from existing complete billing_835_jobs.

Run after migration 060 to populate claim lines from already-processed jobs.
Usage: python3 backend/scripts/backfill_claim_lines.py

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables.
"""

import os
import sys
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables")
    sys.exit(1)

sb = create_client(SUPABASE_URL, SUPABASE_KEY)


def derive_status(paid_amount, adjustments):
    """Derive line status from paid amount and adjustments."""
    co_codes = []
    for a in (adjustments or []):
        if isinstance(a, dict) and a.get("group_code") == "CO" and a.get("reason_code"):
            co_codes.append(f"{a['group_code']}-{a['reason_code']}")

    if paid_amount == 0 and co_codes:
        return "denied", co_codes
    elif paid_amount > 0 and not co_codes:
        return "paid", []
    else:
        return "partial", co_codes


def backfill():
    """Extract line items from complete jobs into billing_claim_lines."""
    # Get all complete jobs
    jobs = sb.table("billing_835_jobs").select(
        "id, billing_company_id, practice_id, result_json"
    ).eq("status", "complete").order("created_at").execute()

    if not jobs.data:
        print("No complete jobs found.")
        return

    total_lines = 0
    total_jobs = 0

    for job in jobs.data:
        rj = job.get("result_json") or {}
        line_items = rj.get("line_items") or []
        payer_name = rj.get("payer_name") or ""
        analysis_id = rj.get("analysis_id")

        if not line_items:
            print(f"  Job {job['id']}: no line items, skipping")
            continue

        # Check if already backfilled
        existing = sb.table("billing_claim_lines").select(
            "id", count="exact"
        ).eq("job_id", job["id"]).execute()

        if existing.count and existing.count > 0:
            print(f"  Job {job['id']}: already has {existing.count} lines, skipping")
            continue

        rows = []
        for li in line_items:
            paid = float(li.get("paid_amount") or 0)
            status, denial_codes = derive_status(paid, li.get("adjustments"))

            dos_raw = (li.get("date_of_service") or "")[:10] or None
            adj_raw = (li.get("adjudication_date") or "")[:10] or None

            rows.append({
                "billing_company_id": job["billing_company_id"],
                "practice_id": job["practice_id"],
                "job_id": job["id"],
                "analysis_id": analysis_id,
                "payer_name": payer_name,
                "claim_number": li.get("claim_number") or li.get("claim_id") or "",
                "cpt_code": li.get("cpt_code") or "",
                "date_of_service": dos_raw if dos_raw and len(dos_raw) >= 8 else None,
                "adjudication_date": adj_raw if adj_raw and len(adj_raw) >= 8 else None,
                "billed_amount": float(li.get("billed_amount") or 0),
                "paid_amount": paid,
                "status": status,
                "denial_codes": denial_codes if denial_codes else None,
            })

        if rows:
            sb.table("billing_claim_lines").insert(rows).execute()
            total_lines += len(rows)
            total_jobs += 1
            print(f"  Job {job['id']}: inserted {len(rows)} lines")

    print(f"\nDone. Backfilled {total_lines} lines from {total_jobs} jobs.")


if __name__ == "__main__":
    backfill()
