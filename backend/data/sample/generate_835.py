#!/usr/bin/env python3
"""Generate a sample 835 EDI file for the Midwest Manufacturing demo."""

import random
import sys

random.seed(42)  # Reproducible output

PAYER = "CIGNA HEALTH AND LIFE INSURANCE COMPANY"
PAYEE = "MIDWEST MANUFACTURING CO"
PAYER_ID = "62308"
PAYEE_ID = "MW-MFG-500"

# Segment and element delimiters
SEG = "~"
EL = "*"

# Flagged procedures from the demo
FLAGGED = [
    ("27447", 8, 4200, 5880),    # Total knee arthroplasty
    ("29881", 12, 1950, 2730),   # Knee arthroscopy w/ meniscectomy
    ("73721", 14, 1840, 2576),   # MRI knee without contrast
    ("27130", 5, 3800, 5320),    # Total hip arthroplasty
    ("93306", 18, 420, 588),     # Echocardiogram complete
    ("75571", 12, 310, 434),     # Cardiac CT calcium scoring
    ("22551", 4, 5100, 7140),    # Anterior cervical discectomy
    ("93350", 8, 680, 952),      # Stress echocardiogram
    ("75574", 6, 2100, 2940),    # Cardiac MRI
    ("20610", 16, 280, 392),     # Joint injection major joint
]

# Routine procedures to fill ~750 claims totaling ~$467,040
ROUTINE = [
    ("99214", 120, 148, 207),    # Office visit moderate
    ("99213", 100, 105, 147),    # Office visit low
    ("99215", 45, 195, 273),     # Office visit high
    ("99395", 42, 210, 294),     # Preventive 18-39
    ("99396", 38, 240, 336),     # Preventive 40-64
    ("93000", 45, 85, 119),      # ECG 12-lead
    ("70553", 15, 1800, 2520),   # MRI brain
    ("72148", 18, 1650, 2310),   # MRI lumbar spine
    ("74177", 22, 950, 1330),    # CT abdomen/pelvis
    ("71046", 30, 180, 252),     # Chest X-ray
    ("96413", 12, 890, 1246),    # Chemo IV infusion
    ("96365", 18, 420, 588),     # IV infusion therapeutic
    ("J1745", 8, 4200, 5880),    # Infliximab injection
    ("99285", 8, 1850, 2590),    # ED visit high
    ("99284", 12, 980, 1372),    # ED visit high urgency
    ("99283", 8, 580, 812),      # ED visit moderate
    ("80053", 45, 48, 67),       # Comprehensive metabolic panel
    ("85025", 55, 28, 39),       # CBC with differential
    ("81001", 20, 18, 25),       # Urinalysis
    ("90834", 50, 125, 175),     # Psychotherapy 45 min
    ("90837", 25, 165, 231),     # Psychotherapy 60 min
    # Additional common procedures to reach $623K total
    ("99232", 35, 1250, 1750),   # Subsequent hospital care
    ("99223", 12, 2800, 3920),   # Initial hospital care, high
    ("99291", 8, 3200, 4480),    # Critical care, first 30-74 min
    ("43239", 10, 2400, 3360),   # Upper GI endoscopy w/ biopsy
    ("45380", 15, 1800, 2520),   # Colonoscopy w/ biopsy
    ("11042", 10, 450, 630),     # Debridement, subcutaneous tissue
    ("64483", 10, 1200, 1680),   # Epidural injection, lumbar
    ("99243", 14, 280, 392),     # Office consultation
    ("58661", 5, 3400, 4760),    # Laparoscopy, surgical
    ("47562", 8, 2800, 3920),    # Laparoscopic cholecystectomy
    ("27446", 4, 3600, 5040),    # Knee arthroplasty revision
]

def vary(base, pct=0.15):
    """Add random variance to a value."""
    return round(base * (1 + random.uniform(-pct, pct)), 2)

def random_date():
    """Random date in December 2024."""
    day = random.randint(1, 31)
    if day > 31:
        day = 31
    return f"2024120{day:01d}" if day < 10 else f"202412{day:02d}"

def build_claims():
    """Build all claim records."""
    claims = []
    claim_num = 1000

    # Flagged procedures
    for cpt, count, paid_avg, billed_avg in FLAGGED:
        for _ in range(count):
            claim_num += 1
            paid = vary(paid_avg, 0.08)
            billed = vary(billed_avg, 0.08)
            adj = round(billed - paid, 2)
            claims.append({
                "claim_id": f"CLM{claim_num:06d}",
                "cpt": cpt,
                "billed": billed,
                "paid": paid,
                "adj": adj,
                "date": random_date(),
            })

    # Routine procedures
    for cpt, count, paid_avg, billed_avg in ROUTINE:
        for _ in range(count):
            claim_num += 1
            paid = vary(paid_avg, 0.10)
            billed = vary(billed_avg, 0.10)
            adj = round(billed - paid, 2)
            claims.append({
                "claim_id": f"CLM{claim_num:06d}",
                "cpt": cpt,
                "billed": billed,
                "paid": paid,
                "adj": adj,
                "date": random_date(),
            })

    return claims

def generate_835():
    """Generate the full 835 EDI content."""
    claims = build_claims()
    total_paid = sum(c["paid"] for c in claims)
    total_billed = sum(c["billed"] for c in claims)
    seg_count = 0
    segments = []

    def add(s):
        nonlocal seg_count
        segments.append(s)
        seg_count += 1

    # ISA - Interchange Control Header (exactly 106 chars before delimiter)
    add(f"ISA{EL}00{EL}          {EL}00{EL}          {EL}ZZ{EL}{PAYER_ID:<15}{EL}ZZ{EL}{PAYEE_ID:<15}{EL}250115{EL}1200{EL}^{EL}00501{EL}000000001{EL}0{EL}P{EL}:")

    # GS - Functional Group Header
    add(f"GS{EL}HP{EL}{PAYER_ID}{EL}{PAYEE_ID}{EL}20250115{EL}1200{EL}1{EL}X{EL}005010X221A1")

    # ST - Transaction Set Header
    add(f"ST{EL}835{EL}0001{EL}005010X221A1")

    # BPR - Financial Information
    add(f"BPR{EL}I{EL}{total_paid:.2f}{EL}C{EL}ACH{EL}CCP{EL}01{EL}021000021{EL}DA{EL}123456789{EL}1512345678{EL}01{EL}031000024{EL}DA{EL}987654321{EL}20250115")

    # TRN - Reassociation Trace
    add(f"TRN{EL}1{EL}TRACE20250115001{EL}1512345678")

    # DTM - Production Date
    add(f"DTM{EL}405{EL}20250115")

    # N1 - Payer Identification
    add(f"N1{EL}PR{EL}{PAYER}{EL}XV{EL}{PAYER_ID}")

    # N1 - Payee Identification
    add(f"N1{EL}PE{EL}{PAYEE}{EL}FI{EL}36-1234567")

    # Claims
    for c in claims:
        patient_resp = round(vary(25, 0.5), 2)

        # CLP - Claim Level
        add(f"CLP{EL}{c['claim_id']}{EL}1{EL}{c['billed']:.2f}{EL}{c['paid']:.2f}{EL}{patient_resp:.2f}{EL}12{EL}CIGNA{c['claim_id'][-6:]}")

        # CAS - Claim-level adjustment (contractual obligation CO-45)
        add(f"CAS{EL}CO{EL}45{EL}{c['adj']:.2f}{EL}1")

        # SVC - Service Line
        add(f"SVC{EL}HC:{c['cpt']}{EL}{c['billed']:.2f}{EL}{c['paid']:.2f}{EL}{EL}{EL}{EL}1")

        # DTM - Service Date
        add(f"DTM{EL}472{EL}{c['date']}")

        # CAS - Line-level adjustment
        add(f"CAS{EL}CO{EL}45{EL}{c['adj']:.2f}{EL}1")

    # SE - Transaction Set Trailer
    add(f"SE{EL}{seg_count + 1}{EL}0001")

    # GE - Functional Group Trailer
    add(f"GE{EL}1{EL}1")

    # IEA - Interchange Control Trailer
    add(f"IEA{EL}1{EL}000000001")

    return SEG.join(segments) + SEG

if __name__ == "__main__":
    content = generate_835()
    outpath = "data/sample/Midwest_Manufacturing_Dec2024.835"
    with open(outpath, "w") as f:
        f.write(content)

    # Quick stats
    claims = build_claims()
    total_paid = sum(c["paid"] for c in claims)
    print(f"Generated {len(claims)} claims, total paid: ${total_paid:,.2f}")
    print(f"Written to {outpath}")
