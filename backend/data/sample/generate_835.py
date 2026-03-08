"""Generate a sample 835 EDI file for Midwest Manufacturing Co (Dec 2024).

Produces Midwest_Manufacturing_Dec2024.835 with realistic Medicare multiples:
- Routine procedures at 1.0-1.8x Medicare (normal commercial rates)
- Flagged procedures at 2.5-6.5x Medicare (the problem claims)
"""

import os
import random
import sys

random.seed(42)

# Output path (same directory as this script)
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "Midwest_Manufacturing_Dec2024.835")

# Medicare rates for reference
MEDICARE_RATES = {
    # Routine
    "99213": 99.63,
    "99214": 145.62,
    "99395": 198.00,
    "99396": 218.00,
    "80053": 11.00,
    "85025": 7.77,
    "93000": 16.22,
    "36415": 9.34,
    "99283": 78.55,
    "99232": 76.16,
    # Flagged
    "27447": 1543.00,
    "29881": 748.00,
    "73721": 283.00,
    "27130": 1489.00,
    "93306": 225.00,
    "75571": 107.00,
    "22551": 1876.00,
    "93350": 272.00,
    "75574": 534.00,
    "20610": 73.00,
}

# Flagged CPT codes: (cpt, count, avg_paid) — these are the problem claims (3-7x Medicare)
FLAGGED = [
    ("27447", 8, 4200),    # total knee — 2.7x Medicare
    ("29881", 12, 1950),   # knee arthroscopy — 2.6x Medicare
    ("73721", 14, 1840),   # MRI knee — 6.5x Medicare (key finding)
    ("27130", 5, 3800),    # total hip — 2.6x Medicare
    ("93306", 18, 420),    # echo complete — 1.9x Medicare
    ("75571", 12, 310),    # cardiac CT — 2.9x Medicare
    ("22551", 4, 5100),    # cervical disc — 2.7x Medicare
    ("93350", 8, 680),     # stress echo — 2.5x Medicare
    ("75574", 6, 2100),    # cardiac MRI — 3.9x Medicare
    ("20610", 16, 280),    # joint injection — 3.8x Medicare
]

# Routine CPT codes: (cpt, count, paid_low, paid_high) — realistic 1.0-1.8x Medicare
ROUTINE = [
    ("99213", 200, 130, 160),    # office visit — 1.3-1.6x
    ("99214", 150, 185, 220),    # office visit — 1.3-1.5x
    ("99395", 80, 220, 260),     # preventive 18-39 — 1.1-1.3x
    ("99396", 70, 240, 280),     # preventive 40-64 — 1.1-1.3x
    ("80053", 120, 14, 18),      # metabolic panel — 1.3-1.6x
    ("85025", 120, 10, 13),      # CBC — 1.3-1.7x
    ("93000", 60, 22, 30),       # ECG — 1.4-1.8x
    ("36415", 100, 12, 16),      # venipuncture — 1.3-1.7x
    ("99283", 35, 95, 130),      # ED moderate — 1.2-1.7x
    ("99232", 45, 95, 120),      # hospital f/u — 1.2-1.6x
]

BILLED_MULTIPLIER = 1.4  # billed amount is 1.4x paid (standard)


def _vary_range(low: float, high: float) -> float:
    """Pick a random value in the range [low, high]."""
    return round(random.uniform(low, high), 2)


def _vary(amount: float) -> float:
    """Apply +/-5% random variance."""
    return round(amount * random.uniform(0.95, 1.05), 2)


def _build_claims():
    """Build all claim records with realistic pricing."""
    claims = []
    claim_num = 1

    # 1) Flagged claims at spec averages with +/-5% variance
    for cpt, count, avg_paid in FLAGGED:
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
            })
            claim_num += 1

    # 2) Routine claims at realistic ranges (1.0-1.8x Medicare)
    for cpt, count, paid_low, paid_high in ROUTINE:
        for _ in range(count):
            paid = _vary_range(paid_low, paid_high)
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
            })
            claim_num += 1

    # Shuffle so flagged claims aren't all at the top
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
    """Print verification summary with Medicare multiples."""
    from collections import defaultdict

    by_cpt = defaultdict(list)
    for c in claims:
        by_cpt[c["cpt"]].append(c["paid"])

    total_paid = sum(c["paid"] for c in claims)
    print(f"\n{'='*70}")
    print(f"VERIFICATION SUMMARY")
    print(f"{'='*70}")
    print(f"Total claims: {len(claims)}")
    print(f"Total paid:   ${total_paid:,.2f}")

    flagged_cpts = {cpt for cpt, _, _ in FLAGGED}
    routine_cpts = {cpt for cpt, _, _, _ in ROUTINE}

    print(f"\n{'─'*70}")
    print(f"FLAGGED PROCEDURES (should be 2.5-7x Medicare)")
    print(f"{'─'*70}")
    print(f"{'CPT':<8} {'Count':>6} {'Avg Paid':>10} {'Medicare':>10} {'Multiple':>10}")
    for cpt in sorted(flagged_cpts):
        payments = by_cpt[cpt]
        avg = sum(payments) / len(payments)
        medicare = MEDICARE_RATES[cpt]
        mult = avg / medicare
        print(f"{cpt:<8} {len(payments):>6} {avg:>10.2f} {medicare:>10.2f} {mult:>10.1f}x")

    print(f"\n{'─'*70}")
    print(f"ROUTINE PROCEDURES (must be under 2.0x Medicare)")
    print(f"{'─'*70}")
    print(f"{'CPT':<8} {'Count':>6} {'Avg Paid':>10} {'Medicare':>10} {'Multiple':>10} {'Status':>8}")
    all_ok = True
    for cpt in sorted(routine_cpts):
        payments = by_cpt[cpt]
        avg = sum(payments) / len(payments)
        medicare = MEDICARE_RATES[cpt]
        mult = avg / medicare
        status = "OK" if mult < 2.0 else "FAIL"
        if mult >= 2.0:
            all_ok = False
        print(f"{cpt:<8} {len(payments):>6} {avg:>10.2f} {medicare:>10.2f} {mult:>10.1f}x {status:>8}")

    print(f"\n{'='*70}")
    if all_ok:
        print("ALL ROUTINE MULTIPLES UNDER 2.0x — PASS")
    else:
        print("SOME ROUTINE MULTIPLES ABOVE 2.0x — FAIL")
    print(f"{'='*70}\n")

    return all_ok


def main():
    claims = _build_claims()
    content = _build_835(claims)

    with open(OUTPUT_FILE, "w") as f:
        f.write(content)

    total_paid = sum(c["paid"] for c in claims)
    print(f"Generated {OUTPUT_FILE}")
    print(f"  Claims: {len(claims)}")
    print(f"  Total paid: ${total_paid:,.2f}")

    ok = _verify(claims)
    if not ok:
        print("ERROR: Routine multiples check failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
