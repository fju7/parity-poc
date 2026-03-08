"""Generate a sample 835 EDI file for Midwest Manufacturing Co (Dec 2024).

Reads actual Medicare rates from the backend's CMS data files (pfs_rates.csv,
clfs_rates.csv, opps_rates.csv) to ensure the multiples shown in the claims
check UI match exactly what this generator intends.

Pricing strategy:
- Routine procedures at 1.2-1.6x Medicare (normal commercial rates)
- Flagged procedures at 2.0-6.5x Medicare (the problem claims)

Uses ZIP 60601 (Chicago, IL) → carrier 06102, locality 16.
"""

import csv
import os
import random
import sys

random.seed(42)

# Output path (same directory as this script)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "..")  # backend/
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "Midwest_Manufacturing_Dec2024.835")

# Locality for Midwest Manufacturing (Chicago, IL 60601)
CARRIER = "06102"
LOCALITY = "16"


def _load_backend_rates():
    """Load Medicare rates from the backend's actual CMS data files.

    Uses the same lookup logic as backend/routers/benchmark.py:
    1. PFS (Physician Fee Schedule) → max(facility, nonfacility)
    2. OPPS (Outpatient Prospective Payment System)
    3. CLFS (Clinical Laboratory Fee Schedule)
    """
    rates = {}

    # PFS rates
    pfs_path = os.path.join(DATA_DIR, "data", "pfs_rates.csv")
    with open(pfs_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["carrier"] == CARRIER and row["locality_code"] == LOCALITY:
                cpt = row["cpt_code"]
                fac = float(row["facility_amount"])
                nonfac = float(row["nonfacility_amount"])
                rates[cpt] = ("PFS", max(fac, nonfac))

    # CLFS rates (for codes not in PFS)
    clfs_path = os.path.join(DATA_DIR, "data", "clfs_rates.csv")
    with open(clfs_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row["hcpcs_code"]
            if code not in rates:
                rate = float(row["payment_rate"])
                if rate > 0:
                    rates[code] = ("CLFS", rate)

    # OPPS rates (for codes not in PFS or CLFS)
    opps_path = os.path.join(DATA_DIR, "data", "opps_rates.csv")
    with open(opps_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row["hcpcs_code"]
            if code not in rates:
                rate = float(row["payment_rate"])
                if rate > 0:
                    rates[code] = ("OPPS", rate)

    return rates


# Target multiples for each CPT code
# Flagged procedures — these are the problem claims the tool should identify
FLAGGED_SPECS = [
    # (cpt, count, target_multiple)
    ("27447", 8, 3.0),    # total knee replacement
    ("29881", 12, 3.5),   # knee arthroscopy
    ("73721", 14, 6.5),   # MRI knee ← KEY FINDING for demo video
    ("27130", 5, 2.8),    # total hip replacement
    ("93306", 18, 2.0),   # echocardiogram complete
    ("75571", 12, 2.9),   # cardiac CT calcium scoring
    ("22551", 4, 2.7),    # anterior cervical discectomy
    ("93350", 8, 2.5),    # stress echocardiogram
    ("75574", 6, 4.0),    # CTA coronary arteries
    ("20610", 16, 3.8),   # joint injection major
]

# Routine procedures — normal commercial rates, should NOT be flagged
ROUTINE_SPECS = [
    # (cpt, count, target_multiple)
    ("99213", 200, 1.4),  # office visit established level 3
    ("99214", 150, 1.4),  # office visit established level 4
    ("99204", 80, 1.3),   # new patient visit level 4 (replaces 99395 which isn't in CMS data)
    ("99205", 70, 1.3),   # new patient visit level 5 (replaces 99396 which isn't in CMS data)
    ("80053", 120, 1.5),  # comprehensive metabolic panel
    ("85025", 120, 1.5),  # CBC with differential
    ("93000", 60, 1.4),   # ECG complete
    ("36415", 100, 1.4),  # venipuncture
    ("99283", 35, 1.3),   # ED visit moderate
    ("99232", 45, 1.3),   # subsequent hospital care
]

BILLED_MULTIPLIER = 1.4  # billed = paid × 1.4 (standard commercial markup)


def _vary(amount: float, pct: float = 0.05) -> float:
    """Apply +/- pct random variance."""
    return round(amount * random.uniform(1 - pct, 1 + pct), 2)


def _build_claims(backend_rates):
    """Build all claim records using actual backend Medicare rates."""
    claims = []
    claim_num = 1
    missing = []

    all_specs = [(cpt, count, mult, "flagged") for cpt, count, mult in FLAGGED_SPECS]
    all_specs += [(cpt, count, mult, "routine") for cpt, count, mult in ROUTINE_SPECS]

    for cpt, count, target_mult, category in all_specs:
        if cpt not in backend_rates:
            missing.append(cpt)
            continue

        source, medicare_rate = backend_rates[cpt]
        avg_paid = medicare_rate * target_mult

        for _ in range(count):
            paid = _vary(avg_paid)
            billed = round(paid * BILLED_MULTIPLIER, 2)
            adjustment = round(billed - paid, 2)
            claim_id = f"MMC2024{claim_num:06d}"
            day = random.randint(1, 28)
            service_date = f"202412{day:02d}"
            claims.append({
                "claim_id": claim_id,
                "cpt": cpt,
                "billed": billed,
                "paid": paid,
                "adjustment": adjustment,
                "service_date": service_date,
                "medicare_rate": medicare_rate,
                "target_mult": target_mult,
                "category": category,
                "source": source,
            })
            claim_num += 1

    if missing:
        print(f"WARNING: CPT codes not found in backend data: {missing}")
        print("These codes will be skipped. Update the specs to use codes that exist.")

    # Shuffle so flagged claims aren't grouped together
    random.shuffle(claims)
    return claims


def _build_835(claims):
    """Build the 835 EDI content."""
    segments = []

    # ISA - Interchange Control Header
    segments.append(
        "ISA*00*          *00*          *ZZ*CIGNA          "
        "*ZZ*MIDWESTMFG     *250103*1200*^*00501*000000001*0*P*:"
    )

    # GS - Functional Group Header
    segments.append("GS*HP*CIGNA*MIDWESTMFG*20250103*1200*1*X*005010X221A1")

    # ST - Transaction Set Header
    segments.append("ST*835*0001")

    # BPR - Beginning of Payment
    total_paid = sum(c["paid"] for c in claims)
    segments.append(
        f"BPR*I*{total_paid:.2f}*C*ACH*CTX*01*011000015*DA*1234567890"
        f"*1512345678**01*011000015*DA*9876543210*20250103"
    )

    # TRN - Reassociation Trace
    segments.append("TRN*1*12345678901234*1512345678")

    # DTM - Production Date
    segments.append("DTM*405*20250103")

    # N1 - Payer
    segments.append("N1*PR*Cigna Health and Life Insurance Company")
    segments.append("N3*900 Cottage Grove Road")
    segments.append("N4*Bloomfield*CT*06002")

    # N1 - Payee
    segments.append("N1*PE*Midwest Manufacturing Co*FI*363456789")
    segments.append("N3*4500 Industrial Parkway")
    segments.append("N4*Columbus*OH*43228")

    # LX - Header Number
    segments.append("LX*1")

    # Claims
    for claim in claims:
        # CLP - Claim Level
        segments.append(
            f"CLP*{claim['claim_id']}*1*{claim['billed']:.2f}"
            f"*{claim['paid']:.2f}*0*12*CLAIMREF001*11"
        )

        # CAS - Contractual adjustment
        segments.append(f"CAS*CO*45*{claim['adjustment']:.2f}")

        # SVC - Service line
        segments.append(
            f"SVC*HC:{claim['cpt']}*{claim['billed']:.2f}"
            f"*{claim['paid']:.2f}**1"
        )

        # DTM - Service date
        segments.append(f"DTM*472*{claim['service_date']}")

    # SE - Transaction Set Trailer
    seg_count = len(segments) - 2 + 1  # exclude ISA/GS, include SE
    segments.append(f"SE*{seg_count}*0001")

    # GE - Functional Group Trailer
    segments.append("GE*1*1")

    # IEA - Interchange Control Trailer
    segments.append("IEA*1*000000001")

    return "~\n".join(segments) + "~\n"


def _verify(claims):
    """Print verification summary showing actual vs target multiples."""
    from collections import defaultdict

    by_cpt = defaultdict(list)
    for c in claims:
        by_cpt[c["cpt"]].append(c)

    total_paid = sum(c["paid"] for c in claims)
    print(f"\n{'=' * 78}")
    print("VERIFICATION SUMMARY")
    print(f"{'=' * 78}")
    print(f"Total claims: {len(claims)}")
    print(f"Total paid:   ${total_paid:,.2f}")

    flagged_cpts = {cpt for cpt, _, _ in FLAGGED_SPECS}
    routine_cpts = {cpt for cpt, _, _ in ROUTINE_SPECS}

    all_ok = True

    print(f"\n{'─' * 78}")
    print("FLAGGED PROCEDURES (target 2.0-6.5x Medicare)")
    print(f"{'─' * 78}")
    hdr = f"{'CPT':<8} {'Count':>6} {'Avg Paid':>10} {'Medicare':>10} {'Actual':>8} {'Target':>8} {'Source':>6}"
    print(hdr)
    for cpt in sorted(flagged_cpts):
        if cpt not in by_cpt:
            continue
        items = by_cpt[cpt]
        avg = sum(c["paid"] for c in items) / len(items)
        medicare = items[0]["medicare_rate"]
        actual = avg / medicare
        target = items[0]["target_mult"]
        src = items[0]["source"]
        print(f"{cpt:<8} {len(items):>6} {avg:>10.2f} {medicare:>10.2f} {actual:>7.1f}x {target:>7.1f}x {src:>6}")

    print(f"\n{'─' * 78}")
    print("ROUTINE PROCEDURES (must be under 2.0x Medicare)")
    print(f"{'─' * 78}")
    hdr = f"{'CPT':<8} {'Count':>6} {'Avg Paid':>10} {'Medicare':>10} {'Actual':>8} {'Target':>8} {'Source':>6} {'OK?':>5}"
    print(hdr)
    for cpt in sorted(routine_cpts):
        if cpt not in by_cpt:
            continue
        items = by_cpt[cpt]
        avg = sum(c["paid"] for c in items) / len(items)
        medicare = items[0]["medicare_rate"]
        actual = avg / medicare
        target = items[0]["target_mult"]
        src = items[0]["source"]
        ok = actual < 2.0
        if not ok:
            all_ok = False
        print(f"{cpt:<8} {len(items):>6} {avg:>10.2f} {medicare:>10.2f} {actual:>7.1f}x {target:>7.1f}x {src:>6} {'OK' if ok else 'FAIL':>5}")

    print(f"\n{'=' * 78}")
    if all_ok:
        print("ALL ROUTINE MULTIPLES UNDER 2.0x — PASS")
    else:
        print("SOME ROUTINE MULTIPLES ABOVE 2.0x — FAIL")
    print(f"{'=' * 78}\n")

    return all_ok


def main():
    print("Loading backend Medicare rates...")
    backend_rates = _load_backend_rates()

    # Verify all required codes exist
    all_cpts = [cpt for cpt, _, _ in FLAGGED_SPECS] + [cpt for cpt, _, _ in ROUTINE_SPECS]
    for cpt in all_cpts:
        if cpt not in backend_rates:
            print(f"ERROR: CPT {cpt} not found in backend CMS data files!")
            sys.exit(1)
        source, rate = backend_rates[cpt]
        print(f"  {cpt}: ${rate:.2f} ({source})")

    claims = _build_claims(backend_rates)
    content = _build_835(claims)

    with open(OUTPUT_FILE, "w") as f:
        f.write(content)

    total_paid = sum(c["paid"] for c in claims)
    print(f"\nGenerated {OUTPUT_FILE}")
    print(f"  Claims: {len(claims)}")
    print(f"  Total paid: ${total_paid:,.2f}")

    ok = _verify(claims)
    if not ok:
        print("ERROR: Routine multiples check failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
