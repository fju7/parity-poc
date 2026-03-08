"""Generate a sample 835 EDI file for Midwest Manufacturing Co (Dec 2024).

Produces Midwest_Manufacturing_Dec2024.835 with 970 claims totaling ~$623,000 paid.
"""

import os
import random

random.seed(42)

# Output path (same directory as this script)
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "Midwest_Manufacturing_Dec2024.835")

# Target totals
TARGET_CLAIMS = 970
TARGET_TOTAL_PAID = 623_000

# Flagged CPT codes: (cpt, count, avg_paid) — exact specs
FLAGGED = [
    ("27447", 8, 4200),
    ("29881", 12, 1950),
    ("73721", 14, 1840),
    ("27130", 5, 3800),
    ("93306", 18, 420),
    ("75571", 12, 310),
    ("22551", 4, 5100),
    ("93350", 8, 680),
    ("75574", 6, 2100),
    ("20610", 16, 280),
]

# Routine CPT codes: (cpt, base_count, avg_paid)
# Counts scaled proportionally to fill remaining slots; averages scaled to hit target total.
ROUTINE_BASE = [
    ("99213", 180, 105),
    ("99214", 120, 148),
    ("99395", 60, 210),
    ("99396", 50, 240),
    ("80053", 90, 45),
    ("85025", 90, 38),
    ("93000", 45, 85),
    ("36415", 80, 18),
    ("99283", 25, 380),
    ("99232", 30, 180),
]

BILLED_MULTIPLIER = 1.4


def _vary(amount: float) -> float:
    """Apply ±5% random variance."""
    return round(amount * random.uniform(0.95, 1.05), 2)


def _build_claims():
    """Build all claim records, hitting target claim count and total paid."""
    claims = []
    claim_num = 1

    # 1) Flagged claims at exact specs
    flagged_total = 0
    for cpt, count, avg_paid in FLAGGED:
        for _ in range(count):
            paid = _vary(avg_paid)
            flagged_total += paid
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

    flagged_count = sum(c for _, c, _ in FLAGGED)  # 103

    # 2) Routine claims — scale counts to fill remaining slots
    routine_slots = TARGET_CLAIMS - flagged_count  # 867
    base_total_count = sum(c for _, c, _ in ROUTINE_BASE)  # 770
    scale_factor = routine_slots / base_total_count

    # Scale counts proportionally, fix rounding to hit exactly routine_slots
    routine_counts = []
    for cpt, base_count, avg in ROUTINE_BASE:
        routine_counts.append((cpt, round(base_count * scale_factor), avg))

    # Adjust last entry to hit exact slot count
    current_sum = sum(c for _, c, _ in routine_counts)
    diff = routine_slots - current_sum
    last_cpt, last_count, last_avg = routine_counts[-1]
    routine_counts[-1] = (last_cpt, last_count + diff, last_avg)

    # 3) Scale routine averages to hit target total
    routine_paid_needed = TARGET_TOTAL_PAID - flagged_total
    routine_base_paid = sum(count * avg for _, count, avg in routine_counts)
    avg_scale = routine_paid_needed / routine_base_paid

    for cpt, count, base_avg in routine_counts:
        scaled_avg = base_avg * avg_scale
        for _ in range(count):
            paid = _vary(scaled_avg)
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


def main():
    claims = _build_claims()
    content = _build_835(claims)

    with open(OUTPUT_FILE, "w") as f:
        f.write(content)

    total_paid = sum(c["paid"] for c in claims)
    print(f"Generated {OUTPUT_FILE}")
    print(f"  Claims: {len(claims)}")
    print(f"  Total paid: ${total_paid:,.2f}")


if __name__ == "__main__":
    main()
