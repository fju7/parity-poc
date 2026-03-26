"""Backfill Stripe customers for existing billing companies.

Creates Stripe customers for billing companies missing stripe_customer_id.
Also updates subscription tier from 'trial' to 'free'.

Usage:
    STRIPE_SECRET_KEY=sk_test_... SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \
    python3 backend/scripts/backfill_billing_stripe_customers.py
"""

import os
import sys

stripe_key = os.environ.get("STRIPE_SECRET_KEY")
sb_url = os.environ.get("SUPABASE_URL")
sb_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not stripe_key or not sb_url or not sb_key:
    print("ERROR: Set STRIPE_SECRET_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY")
    sys.exit(1)

import stripe
stripe.api_key = stripe_key

from supabase import create_client
sb = create_client(sb_url, sb_key)


def main():
    # Get all billing companies without stripe_customer_id
    companies = sb.table("billing_companies").select("id, company_name, contact_email, stripe_customer_id").execute()

    created = 0
    skipped = 0

    for bc in (companies.data or []):
        if bc.get("stripe_customer_id"):
            print(f"  {bc['company_name']}: already has customer {bc['stripe_customer_id']}")
            skipped += 1
            continue

        try:
            customer = stripe.Customer.create(
                email=bc["contact_email"],
                name=bc["company_name"],
                metadata={"billing_company_id": str(bc["id"])},
            )
            sb.table("billing_companies").update({
                "stripe_customer_id": customer.id,
            }).eq("id", bc["id"]).execute()
            print(f"  {bc['company_name']}: created customer {customer.id}")
            created += 1
        except Exception as exc:
            print(f"  {bc['company_name']}: FAILED — {exc}")

    # Update trial → free for all existing subscriptions
    subs = sb.table("billing_company_subscriptions").select("id, tier").eq("tier", "trial").execute()
    updated = 0
    for s in (subs.data or []):
        sb.table("billing_company_subscriptions").update({
            "tier": "free",
            "practice_count_limit": 1,
        }).eq("id", s["id"]).execute()
        updated += 1

    print(f"\nDone. Customers: {created} created, {skipped} skipped. Subscriptions: {updated} updated trial→free.")


if __name__ == "__main__":
    main()
