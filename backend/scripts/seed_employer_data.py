"""
Seed script: generates 150 synthetic employer contributions for ACME-2847.

Usage:
    cd backend
    source venv/bin/activate
    python scripts/seed_employer_data.py
"""

import hashlib
import os
import random
from datetime import datetime, timedelta

from supabase import create_client

# ---------------------------------------------------------------------------
# Supabase connection
# ---------------------------------------------------------------------------

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://kfxxpscdwoemtzylhhhb.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

if not SUPABASE_SERVICE_KEY:
    raise RuntimeError(
        "Set SUPABASE_SERVICE_KEY env var before running.\n"
        "  export SUPABASE_SERVICE_KEY='your-service-role-key'"
    )

sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ---------------------------------------------------------------------------
# Look up ACME-2847 employer
# ---------------------------------------------------------------------------

emp = sb.table("employer_accounts").select("id").eq("employer_code", "ACME-2847").execute()
if not emp.data:
    raise RuntimeError("ACME-2847 not found in employer_accounts — run the SQL seed first")
EMPLOYER_ID = emp.data[0]["id"]

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROVIDERS = [
    # 2 outlier providers (will get high scores)
    "Clearwater Surgical Associates",
    "Bayshore Radiology Group",
    # 6 normal providers
    "Tampa General Hospital",
    "St. Petersburg Medical Center",
    "Suncoast Family Practice",
    "Gulf Coast Orthopedics",
    "Pinellas Urgent Care",
    "Bay Area Cardiology",
]

OUTLIER_PROVIDERS = {"Clearwater Surgical Associates", "Bayshore Radiology Group"}

CPT_CODES = [
    ("99213", "Office visit, established patient, level 3", 78.05),
    ("99214", "Office visit, established patient, level 4", 114.53),
    ("99215", "Office visit, established patient, level 5", 153.72),
    ("71046", "Chest X-ray, 2 views", 26.27),
    ("93000", "Electrocardiogram (ECG), 12-lead", 17.24),
    ("80053", "Comprehensive metabolic panel", 11.18),
    ("85025", "Complete blood count with differential", 7.77),
    ("36415", "Venipuncture for blood draw", 3.01),
    ("99203", "Office visit, new patient, level 3", 110.37),
    ("73721", "MRI lower extremity without contrast", 197.58),
    ("27447", "Total knee arthroplasty", 1180.97),
    ("29881", "Arthroscopy, knee, surgical", 468.15),
]

# 12 distinct fake user hashes
USER_IDS = [f"employee-{i:03d}@acme.example.com" for i in range(1, 13)]

CODING_FLAG_TYPES = [
    {"type": "ncci_bundle", "description": "Possible NCCI bundling issue"},
    {"type": "mue_exceeded", "description": "Units may exceed MUE limit"},
    {"type": "site_of_service", "description": "Site-of-service differential flag"},
    {"type": "em_level", "description": "E&M level may not match complexity"},
]

# Date range: Dec 2025 – Feb 2026
START_DATE = datetime(2025, 12, 1)
END_DATE = datetime(2026, 2, 28)
DATE_RANGE_DAYS = (END_DATE - START_DATE).days

# ---------------------------------------------------------------------------
# Generate rows
# ---------------------------------------------------------------------------

rows = []
for _ in range(150):
    provider = random.choice(PROVIDERS)
    is_outlier = provider in OUTLIER_PROVIDERS
    user_email = random.choice(USER_IDS)
    user_hash = hashlib.sha256(user_email.encode()).hexdigest()

    cpt_code, description, benchmark = random.choice(CPT_CODES)

    # Generate anomaly score
    if is_outlier:
        score = round(random.uniform(2.5, 12.0), 2)
    else:
        score = round(random.uniform(0.8, 2.8), 2)

    billed = round(benchmark * score, 2)
    flagged = score > 2.0

    # ~30% get coding flags
    coding_flags = []
    if random.random() < 0.30:
        coding_flags = [random.choice(CODING_FLAG_TYPES)]

    flag_reason = None
    if flagged:
        if score > 3.0:
            flag_reason = f"Billed at {score}x benchmark rate"
        else:
            flag_reason = "Above threshold"

    # Random date in range
    random_day = random.randint(0, DATE_RANGE_DAYS)
    contributed_at = (START_DATE + timedelta(days=random_day)).isoformat() + "Z"

    rows.append({
        "employer_id": EMPLOYER_ID,
        "source_user_hash": user_hash,
        "provider_name": provider,
        "cpt_code": cpt_code,
        "cpt_description": description,
        "billed_amount": billed,
        "benchmark_rate": benchmark,
        "anomaly_score": score,
        "flagged": flagged,
        "flag_reason": flag_reason,
        "coding_flags": coding_flags,
        "contributed_at": contributed_at,
    })

# ---------------------------------------------------------------------------
# Insert in batches
# ---------------------------------------------------------------------------

BATCH_SIZE = 50
for i in range(0, len(rows), BATCH_SIZE):
    batch = rows[i : i + BATCH_SIZE]
    sb.table("employer_contributions").insert(batch).execute()
    print(f"  Inserted {len(batch)} rows ({i + len(batch)}/{len(rows)})")

print(f"\nDone! Seeded {len(rows)} contributions for ACME-2847.")
print(f"  Providers: {len(PROVIDERS)} ({len(OUTLIER_PROVIDERS)} outliers)")
print(f"  Users: {len(USER_IDS)} distinct hashes")
print(f"  Date range: {START_DATE.strftime('%b %Y')} – {END_DATE.strftime('%b %Y')}")
