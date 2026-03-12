"""
Seed script for Parity Provider demo data.

Inserts demo practice profile and 3 historical contract integrity analyses
into Supabase so the Dashboard home screen has data to show.

USAGE:
  1. Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables
  2. Run: python scripts/seed_provider_demo.py
  3. Or: just read the output SQL and run it in Supabase SQL Editor

The script targets a specific demo user_id. Update DEMO_USER_ID below
to match the authenticated user you want to seed data for.
"""

import json
import os
import sys

# ---------------------------------------------------------------------------
# Configuration — update these before running
# ---------------------------------------------------------------------------

DEMO_USER_ID = "REPLACE_WITH_YOUR_USER_ID"  # from supabase auth.users

DEMO_PRACTICE = {
    "company_id": DEMO_USER_ID,
    "practice_name": "Sunshine Internal Medicine",
    "specialty": "Internal Medicine",
    "npi": "1234567890",
    "zip_code": "33701",
}

# 3 months of contract integrity analyses: Nov 2025, Dec 2025, Jan 2026
DEMO_ANALYSES = [
    {
        "company_id": DEMO_USER_ID,
        "payer_name": "UnitedHealthcare",
        "production_date": "2025-11-15",
        "total_billed": 8420.00,
        "total_paid": 7135.50,
        "underpayment": 1284.50,
        "adherence_rate": 82.5,
        "result_json": {
            "summary": {
                "total_contracted": 8420.00,
                "total_paid": 7135.50,
                "total_underpayment": 1284.50,
                "adherence_rate": 82.5,
                "line_count": 40,
                "correct_count": 33,
                "underpaid_count": 5,
                "denied_count": 2,
                "overpaid_count": 0,
                "no_contract_count": 0,
            },
            "top_underpaid": [
                {"cpt_code": "99214", "total_underpayment": 487.20},
                {"cpt_code": "93000", "total_underpayment": 312.00},
                {"cpt_code": "99215", "total_underpayment": 285.30},
                {"cpt_code": "85025", "total_underpayment": 200.00},
            ],
            "line_count": 40,
        },
    },
    {
        "company_id": DEMO_USER_ID,
        "payer_name": "UnitedHealthcare",
        "production_date": "2025-12-15",
        "total_billed": 9150.00,
        "total_paid": 8022.75,
        "underpayment": 1127.25,
        "adherence_rate": 85.7,
        "result_json": {
            "summary": {
                "total_contracted": 9150.00,
                "total_paid": 8022.75,
                "total_underpayment": 1127.25,
                "adherence_rate": 85.7,
                "line_count": 42,
                "correct_count": 36,
                "underpaid_count": 4,
                "denied_count": 2,
                "overpaid_count": 0,
                "no_contract_count": 0,
                "billed_below_count": 0,
                "total_chargemaster_gap": 0,
            },
            "top_underpaid": [
                {"cpt_code": "99214", "total_underpayment": 405.60},
                {"cpt_code": "93000", "total_underpayment": 356.00},
                {"cpt_code": "36415", "total_underpayment": 185.65},
                {"cpt_code": "85025", "total_underpayment": 180.00},
            ],
            "scorecard": {
                "clean_claim_rate": 85.7,
                "denial_rate": 4.8,
                "payer_adherence_rate": 85.7,
                "preventable_denial_rate": 50.0,
                "narrative": "Your clean claim rate of 85.7% is below the industry benchmark of 95%, primarily driven by underpayment on E&M codes 99214 and 93000. Your denial rate of 4.8% is within acceptable range, but half of denials are preventable (CO-16 missing information). Focus on ensuring complete documentation at time of submission.",
            },
            "denial_intelligence": {
                "denial_types": [
                    {
                        "adjustment_code": "CO-16",
                        "plain_language": "Claim lacks information needed for adjudication — typically missing modifier, authorization, or supporting documentation.",
                        "is_actionable": True,
                        "appeal_worthiness": "high",
                        "recommended_action": "Resubmit with complete documentation. Attach operative notes or medical necessity letter.",
                        "count": 1,
                        "total_value": 175.00,
                    },
                    {
                        "adjustment_code": "CO-45",
                        "plain_language": "Charges exceed the fee schedule or maximum allowable amount per the payer contract.",
                        "is_actionable": False,
                        "appeal_worthiness": "low",
                        "recommended_action": "Review contract terms. This is typically a contractual write-off, not appealable.",
                        "count": 1,
                        "total_value": 35.00,
                    },
                ],
                "pattern_summary": "Two denials in December: one preventable (CO-16, missing info) worth $175 and one contractual adjustment (CO-45) worth $35. The CO-16 denial is likely recoverable with resubmission.",
                "total_recoverable_value": 175.00,
            },
            "line_count": 42,
        },
    },
    {
        "company_id": DEMO_USER_ID,
        "payer_name": "UnitedHealthcare",
        "production_date": "2026-01-15",
        "total_billed": 7890.00,
        "total_paid": 6803.22,
        "underpayment": 1086.78,
        "adherence_rate": 87.1,
        "result_json": {
            "summary": {
                "total_contracted": 7890.00,
                "total_paid": 6803.22,
                "total_underpayment": 1086.78,
                "adherence_rate": 87.1,
                "line_count": 38,
                "correct_count": 33,
                "underpaid_count": 3,
                "denied_count": 2,
                "overpaid_count": 0,
                "no_contract_count": 0,
            },
            "top_underpaid": [
                {"cpt_code": "99215", "total_underpayment": 428.40},
                {"cpt_code": "93000", "total_underpayment": 378.38},
                {"cpt_code": "99214", "total_underpayment": 280.00},
            ],
            "line_count": 38,
        },
    },
]

# Contract rates that match the test template
DEMO_CONTRACT = {
    "user_id": DEMO_USER_ID,
    "payer_name": "UnitedHealthcare",
    "rates": [
        {"cpt": "99213", "description": "Office visit, established, level 3", "rates": {"UnitedHealthcare": 95.00}},
        {"cpt": "99214", "description": "Office visit, established, level 4", "rates": {"UnitedHealthcare": 135.00}},
        {"cpt": "99215", "description": "Office visit, established, level 5", "rates": {"UnitedHealthcare": 175.00}},
        {"cpt": "93000", "description": "Electrocardiogram (ECG/EKG), 12-lead", "rates": {"UnitedHealthcare": 35.00}},
        {"cpt": "36415", "description": "Venipuncture (blood draw)", "rates": {"UnitedHealthcare": 12.00}},
        {"cpt": "85025", "description": "Complete blood count (CBC) with differential", "rates": {"UnitedHealthcare": 15.00}},
    ],
}


def generate_sql():
    """Generate SQL statements for manual execution in Supabase SQL Editor."""

    lines = []
    lines.append("-- Parity Provider Demo Seed Data")
    lines.append(f"-- Target user_id: {DEMO_USER_ID}")
    lines.append("-- Run this in Supabase SQL Editor after replacing DEMO_USER_ID")
    lines.append("")

    # Provider profile
    p = DEMO_PRACTICE
    lines.append("-- 1. Provider profile")
    lines.append(f"INSERT INTO provider_profiles (company_id, practice_name, specialty, npi, zip_code)")
    lines.append(f"VALUES ('{p['user_id']}', '{p['practice_name']}', '{p['specialty']}', '{p['npi']}', '{p['zip_code']}')")
    lines.append(f"ON CONFLICT (company_id) DO UPDATE SET practice_name = EXCLUDED.practice_name;")
    lines.append("")

    # Contract rates
    c = DEMO_CONTRACT
    rates_json = json.dumps(c["rates"]).replace("'", "''")
    lines.append("-- 2. Contract rates")
    lines.append(f"DELETE FROM provider_contracts WHERE company_id = '{c['company_id']}' AND payer_name = '{c['payer_name']}';")
    lines.append(f"INSERT INTO provider_contracts (company_id, payer_name, rates)")
    lines.append(f"VALUES ('{c['company_id']}', '{c['payer_name']}', '{rates_json}'::jsonb);")
    lines.append("")

    # Analyses
    lines.append("-- 3. Historical analyses")
    for i, a in enumerate(DEMO_ANALYSES):
        result_json = json.dumps(a["result_json"]).replace("'", "''")
        lines.append(f"INSERT INTO provider_analyses (company_id, payer_name, production_date, total_billed, total_paid, underpayment, adherence_rate, result_json)")
        lines.append(f"VALUES ('{a['company_id']}', '{a['payer_name']}', '{a['production_date']}', {a['total_billed']}, {a['total_paid']}, {a['underpayment']}, {a['adherence_rate']}, '{result_json}'::jsonb);")
        lines.append("")

    return "\n".join(lines)


def seed_via_api():
    """Seed data via Supabase Python client."""
    url = os.environ.get("SUPABASE_URL", "https://kfxxpscdwoemtzylhhhb.supabase.co")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not key:
        print("ERROR: SUPABASE_SERVICE_KEY not set. Cannot seed via API.")
        print("Set the env var or use the SQL output below.\n")
        return False

    try:
        from supabase import create_client
        sb = create_client(url, key)

        # Upsert profile
        sb.table("provider_profiles").upsert(DEMO_PRACTICE, on_conflict="company_id").execute()
        print("  Inserted provider profile")

        # Upsert contract
        sb.table("provider_contracts").delete().eq("company_id", DEMO_USER_ID).eq("payer_name", DEMO_CONTRACT["payer_name"]).execute()
        sb.table("provider_contracts").insert(DEMO_CONTRACT).execute()
        print("  Inserted contract rates")

        # Insert analyses
        for a in DEMO_ANALYSES:
            sb.table("provider_analyses").insert(a).execute()
        print(f"  Inserted {len(DEMO_ANALYSES)} analyses")

        return True
    except Exception as exc:
        print(f"  API seed failed: {exc}")
        return False


if __name__ == "__main__":
    if DEMO_USER_ID == "REPLACE_WITH_YOUR_USER_ID":
        print("=" * 60)
        print("DEMO SEED SCRIPT — Parity Provider")
        print("=" * 60)
        print()
        print("Before running, update DEMO_USER_ID in this script")
        print("with your actual Supabase auth user ID.")
        print()
        print("To find your user_id:")
        print("  1. Log in to Parity Provider")
        print("  2. Open browser console")
        print("  3. Run: (await supabase.auth.getSession()).data.session.user.id")
        print()
        print("Then either:")
        print("  a) Set SUPABASE_SERVICE_KEY env var and re-run this script")
        print("  b) Copy the SQL below and run in Supabase SQL Editor")
        print()
        print("-" * 60)
        print("SQL OUTPUT (replace REPLACE_WITH_YOUR_USER_ID first):")
        print("-" * 60)
        print()
        print(generate_sql())
        sys.exit(0)

    print("Seeding Parity Provider demo data...")
    print(f"  User ID: {DEMO_USER_ID}")
    print()

    success = seed_via_api()
    if not success:
        print("Falling back to SQL output:\n")
        print(generate_sql())
    else:
        print("\nDemo data seeded successfully!")
