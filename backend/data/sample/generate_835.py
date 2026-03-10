"""Generate a sample 835 EDI file for Midwest Manufacturing Co (Dec 2024).

Reads actual Medicare rates from the backend's CMS data files (pfs_rates.csv,
clfs_rates.csv, opps_rates.csv) to ensure the multiples shown in the claims
check UI match exactly what this generator intends.

Pricing strategy:
- Routine procedures at 1.2-1.6x Medicare (normal commercial rates)
- Flagged procedures at 2.0-6.5x Medicare (the problem claims)

Includes NM1 provider segments and CLM place-of-service data for Level 2
analytics testing (provider variation, site of care, carrier rates, network).

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

# Rendering providers (pool of 8)
PROVIDERS = [
    {"last": "MARTINEZ", "first": "CARLOS", "npi": "1234567890"},
    {"last": "JOHNSON", "first": "SARAH", "npi": "2345678901"},
    {"last": "PATEL", "first": "RAJ", "npi": "3456789012"},
    {"last": "WILLIAMS", "first": "JAMES", "npi": "4567890123"},
    {"last": "CHEN", "first": "LISA", "npi": "5678901234"},
    {"last": "THOMPSON", "first": "MICHAEL", "npi": "6789012345"},
    {"last": "GARCIA", "first": "MARIA", "npi": "7890123456"},
    {"last": "ANDERSON", "first": "DAVID", "npi": "8901234567"},
]

# Service facilities — weighted mix for site-of-care analysis
FACILITIES = [
    {"name": "MIDWEST GENERAL HOSPITAL", "npi": "1111111111", "pos": "22"},   # hospital outpatient
    {"name": "MIDWEST GENERAL HOSPITAL", "npi": "1111111111", "pos": "22"},   # hospital outpatient (weighted)
    {"name": "ADVANCED IMAGING CENTER", "npi": "2222222222", "pos": "11"},    # office
    {"name": "ORTHO SURGICAL CENTER", "npi": "3333333333", "pos": "24"},      # ASC
    {"name": "REGIONAL MEDICAL CENTER", "npi": "4444444444", "pos": "22"},    # hospital outpatient
    {"name": "COMMUNITY IMAGING LLC", "npi": "5555555555", "pos": "11"},      # office
    {"name": "NORTHWEST SURGICAL ASC", "npi": "6666666666", "pos": "24"},     # ASC
    {"name": "ST LUKE OUTPATIENT", "npi": "7777777777", "pos": "19"},         # off-campus outpatient
]

# Facility subsets by category
HOSPITAL_FACILITIES = [f for f in FACILITIES if f["pos"] in ("22", "19")]
OFFICE_FACILITIES = [f for f in FACILITIES if f["pos"] == "11"]
ASC_FACILITIES = [f for f in FACILITIES if f["pos"] == "24"]
NON_HOSPITAL_FACILITIES = OFFICE_FACILITIES + ASC_FACILITIES

# CPT category sets for facility assignment
IMAGING_CPTS = {"73721", "75574", "70553", "75571"}
SURGICAL_CPTS = {"29881", "27447", "22551", "27130"}
LAB_CPTS = {"80053", "85025", "36415"}
# High-volume CPTs that need both hospital and non-hospital claims for variation testing
VARIATION_CPTS = {"73721", "75574", "20610", "29881", "27447"}


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


def _assign_facility(cpt, claim_index):
    """Assign a facility based on CPT category with realistic distribution."""
    if cpt in IMAGING_CPTS:
        # 60% hospital outpatient, 40% imaging center
        if random.random() < 0.6:
            return random.choice(HOSPITAL_FACILITIES)
        else:
            return random.choice(OFFICE_FACILITIES)
    elif cpt in SURGICAL_CPTS:
        # 70% ASC or hospital, 30% office
        if random.random() < 0.4:
            return random.choice(HOSPITAL_FACILITIES)
        elif random.random() < 0.6:
            return random.choice(ASC_FACILITIES)
        else:
            return random.choice(OFFICE_FACILITIES)
    elif cpt in LAB_CPTS:
        # 80% office, 20% hospital outpatient
        if random.random() < 0.8:
            return random.choice(OFFICE_FACILITIES)
        else:
            return random.choice(HOSPITAL_FACILITIES)
    else:
        # Random from full pool
        return random.choice(FACILITIES)


def _adjust_paid_for_facility(paid, cpt, facility):
    """Adjust paid amount based on facility type to create realistic variation.

    Hospital outpatient claims should be 2-3x higher than office/ASC for
    imaging and surgical procedures — this is realistic and triggers variation detection.
    """
    pos = facility["pos"]

    if cpt in VARIATION_CPTS:
        if pos in ("22", "19"):
            # Hospital outpatient: inflate paid by 1.8-2.5x
            return round(paid * random.uniform(1.8, 2.5), 2)
        elif pos == "11":
            # Office: reduce paid by 0.35-0.50x (imaging centers are cheaper)
            return round(paid * random.uniform(0.35, 0.50), 2)
        elif pos == "24":
            # ASC: slightly below base
            return round(paid * random.uniform(0.55, 0.75), 2)

    return paid


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

        for i in range(count):
            paid = _vary(avg_paid)
            facility = _assign_facility(cpt, claim_num)
            provider = PROVIDERS[claim_num % len(PROVIDERS)]

            # Adjust paid amount based on facility for variation CPTs
            paid = _adjust_paid_for_facility(paid, cpt, facility)

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
                "provider": provider,
                "facility": facility,
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
        provider = claim["provider"]
        facility = claim["facility"]
        pos = facility["pos"]

        # CLP - Claim Level
        segments.append(
            f"CLP*{claim['claim_id']}*1*{claim['billed']:.2f}"
            f"*{claim['paid']:.2f}*0*12*CLAIMREF001*11"
        )

        # CLM - Claim with place of service
        segments.append(
            f"CLM*{claim['claim_id']}*{claim['billed']:.2f}***{pos}:B:1*Y*A*Y*I"
        )

        # NM1*82 - Rendering Provider
        segments.append(
            f"NM1*82*1*{provider['last']}*{provider['first']}***XX*{provider['npi']}"
        )

        # NM1*77 - Service Facility
        segments.append(
            f"NM1*77*2*{facility['name']}****XX*{facility['npi']}"
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

    # Provider & facility summary
    print(f"\n{'─' * 78}")
    print("PROVIDER / FACILITY SUMMARY")
    print(f"{'─' * 78}")
    provider_names = set()
    facility_names = set()
    pos_counts = defaultdict(int)
    for c in claims:
        provider_names.add(f"{c['provider']['last']}, {c['provider']['first']}")
        facility_names.add(c['facility']['name'])
        pos_counts[c['facility']['pos']] += 1
    print(f"Unique providers: {len(provider_names)}")
    print(f"Unique facilities: {len(facility_names)}")
    for pos, cnt in sorted(pos_counts.items()):
        pos_labels = {"11": "Office", "19": "Off-Campus Outpatient", "22": "Hospital Outpatient", "24": "ASC"}
        print(f"  POS {pos} ({pos_labels.get(pos, 'Other')}): {cnt} claims")

    # Variation CPT summary
    print(f"\n{'─' * 78}")
    print("VARIATION CPT PRICE RANGES (for Level 2 testing)")
    print(f"{'─' * 78}")
    for cpt in sorted(VARIATION_CPTS):
        if cpt not in by_cpt:
            continue
        items = by_cpt[cpt]
        by_facility = defaultdict(list)
        for c in items:
            by_facility[c['facility']['name']].append(c['paid'])
        print(f"CPT {cpt}:")
        for fname, paids in sorted(by_facility.items()):
            avg_p = sum(paids) / len(paids)
            print(f"  {fname}: {len(paids)} claims, avg ${avg_p:,.2f} (range ${min(paids):,.2f}-${max(paids):,.2f})")

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
