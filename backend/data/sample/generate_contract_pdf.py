"""Generate a realistic payer contract PDF for Sunrise Family Medicine.

Produces Sunrise_Family_Medicine_Aetna_Contract_2025.pdf — a multi-page
fee schedule with CPT codes, contracted rates, terms, and effective dates.
Designed to test the billing Contract Library upload and Claude vision extraction.

Usage: python3 backend/data/sample/generate_contract_pdf.py
"""

import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    HRFlowable,
)

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "Sunrise_Family_Medicine_Aetna_Contract_2025.pdf")

AETNA_PURPLE = colors.HexColor("#7B2D8E")
LIGHT_PURPLE = colors.HexColor("#F3E8F9")
NAVY = colors.HexColor("#1E293B")
LIGHT_GRAY = colors.HexColor("#F8FAFC")
DARK_GRAY = colors.HexColor("#333333")
MED_GRAY = colors.HexColor("#666666")


def _styles():
    ss = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("Title", parent=ss["Normal"],
            fontSize=22, leading=26, textColor=AETNA_PURPLE,
            fontName="Helvetica-Bold", spaceAfter=6),
        "subtitle": ParagraphStyle("Subtitle", parent=ss["Normal"],
            fontSize=14, leading=18, textColor=NAVY, spaceAfter=4),
        "heading": ParagraphStyle("Heading", parent=ss["Normal"],
            fontSize=12, leading=16, textColor=AETNA_PURPLE,
            fontName="Helvetica-Bold", spaceBefore=16, spaceAfter=8),
        "body": ParagraphStyle("Body", parent=ss["Normal"],
            fontSize=10, leading=14, textColor=DARK_GRAY),
        "small": ParagraphStyle("Small", parent=ss["Normal"],
            fontSize=8, leading=10, textColor=MED_GRAY),
        "footer": ParagraphStyle("Footer", parent=ss["Normal"],
            fontSize=7, leading=9, textColor=MED_GRAY, alignment=1),
    }


# Realistic fee schedule rates (based on typical Aetna PPO rates, ~115-125% of Medicare)
FEE_SCHEDULE = [
    # E/M Office Visits
    ("99202", "Office visit, new patient, level 2", 95.00),
    ("99203", "Office visit, new patient, level 3", 145.00),
    ("99204", "Office visit, new patient, level 4", 210.00),
    ("99205", "Office visit, new patient, level 5", 275.00),
    ("99211", "Office visit, est. patient, level 1", 35.00),
    ("99212", "Office visit, est. patient, level 2", 65.00),
    ("99213", "Office visit, est. patient, level 3", 98.00),
    ("99214", "Office visit, est. patient, level 4", 142.00),
    ("99215", "Office visit, est. patient, level 5", 195.00),
    # Preventive
    ("99381", "Preventive visit, new, infant", 165.00),
    ("99385", "Preventive visit, new, 18-39", 185.00),
    ("99386", "Preventive visit, new, 40-64", 205.00),
    ("99391", "Preventive visit, est., infant", 135.00),
    ("99395", "Preventive visit, est., 18-39", 155.00),
    ("99396", "Preventive visit, est., 40-64", 175.00),
    ("99397", "Preventive visit, est., 65+", 190.00),
    # Procedures
    ("36415", "Venipuncture", 8.50),
    ("36416", "Capillary blood draw", 6.00),
    ("10060", "I&D abscess, simple", 145.00),
    ("10061", "I&D abscess, complicated", 250.00),
    ("11102", "Tangential biopsy, single", 110.00),
    ("11104", "Punch biopsy, single", 95.00),
    ("17000", "Destruction, premalignant lesion, first", 65.00),
    ("17003", "Destruction, premalignant lesion, 2-14, each", 18.00),
    ("17110", "Destruction, warts, up to 14", 88.00),
    ("20610", "Aspiration/injection, major joint", 95.00),
    ("29125", "Short arm splint, static", 55.00),
    # Lab
    ("80053", "Comprehensive metabolic panel", 22.00),
    ("80061", "Lipid panel", 28.00),
    ("81001", "Urinalysis, automated with microscopy", 6.50),
    ("85025", "CBC with differential", 15.00),
    ("85610", "Prothrombin time", 8.50),
    ("87081", "Culture, screening", 12.00),
    ("87491", "Chlamydia, amplified probe", 42.00),
    # Immunizations
    ("90471", "Immunization admin, first", 25.00),
    ("90472", "Immunization admin, each additional", 15.00),
    ("90658", "Influenza vaccine, IIV3", 22.00),
    ("90707", "MMR vaccine", 72.00),
    ("90715", "Tdap vaccine", 48.00),
    # ECG / Diagnostics
    ("93000", "ECG, 12-lead, interpretation and report", 32.00),
    ("93005", "ECG tracing only", 18.00),
    ("94010", "Spirometry", 38.00),
    ("94060", "Bronchodilation response", 55.00),
    # Telehealth
    ("99441", "Telephone E/M, 5-10 min", 35.00),
    ("99442", "Telephone E/M, 11-20 min", 68.00),
    ("99443", "Telephone E/M, 21-30 min", 98.00),
]


def build_pdf():
    styles = _styles()
    doc = SimpleDocTemplate(OUTPUT_FILE, pagesize=letter,
                            leftMargin=0.75*inch, rightMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    story = []

    # --- Cover Page ---
    story.append(Spacer(1, 1.5*inch))
    story.append(Paragraph("Aetna Better Health", styles["title"]))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("Professional Services Agreement", styles["subtitle"]))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("Fee Schedule — Exhibit A", styles["subtitle"]))
    story.append(Spacer(1, 0.3*inch))
    story.append(HRFlowable(width="60%", thickness=2, color=AETNA_PURPLE, hAlign="CENTER"))
    story.append(Spacer(1, 0.4*inch))

    story.append(Paragraph("<b>Provider:</b> Sunrise Family Medicine", styles["body"]))
    story.append(Paragraph("<b>Tax ID:</b> 59-1234567", styles["body"]))
    story.append(Paragraph("<b>NPI:</b> 1234567890", styles["body"]))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph("<b>Payer:</b> Aetna Better Health of Florida", styles["body"]))
    story.append(Paragraph("<b>Plan Type:</b> PPO", styles["body"]))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph("<b>Effective Date:</b> January 1, 2025", styles["body"]))
    story.append(Paragraph("<b>Expiration Date:</b> December 31, 2025", styles["body"]))
    story.append(Paragraph("<b>Auto-Renewal:</b> Yes, 1-year terms unless 90-day written notice", styles["body"]))
    story.append(Spacer(1, 0.4*inch))

    story.append(Paragraph(
        "This Fee Schedule (Exhibit A) is incorporated by reference into the "
        "Professional Services Agreement between Aetna Better Health of Florida "
        "and Sunrise Family Medicine. All rates are per-unit, non-facility rates "
        "unless otherwise noted. Rates are effective for dates of service on or "
        "after the Effective Date listed above.",
        styles["body"]
    ))
    story.append(Spacer(1, 1.5*inch))
    story.append(Paragraph(
        "CONFIDENTIAL — This document contains proprietary rate information. "
        "Distribution outside the contracting parties is prohibited.",
        styles["small"]
    ))
    story.append(PageBreak())

    # --- Terms Page ---
    story.append(Paragraph("Key Contract Terms", styles["title"]))
    story.append(Spacer(1, 0.15*inch))

    terms = [
        ("Timely Filing", "Claims must be submitted within 180 days of the date of service. "
         "Claims submitted after 180 days are subject to denial under CARC code 29."),
        ("Clean Claim Payment", "Aetna will process clean claims within 30 calendar days of receipt. "
         "Interest accrues at 1% per month on claims not adjudicated within 45 days."),
        ("Prior Authorization", "Prior authorization required for: MRI/MRA, CT with contrast, "
         "surgical procedures over $500, DME over $200. Failure to obtain prior auth may result "
         "in denial under CARC code 197."),
        ("Coordination of Benefits", "Standard COB rules apply. Aetna is primary for members "
         "where Aetna is the subscriber's employer-sponsored plan."),
        ("Rate Escalator", "Rates will increase by CPI-Medical or 3%, whichever is less, "
         "on each anniversary date."),
        ("Dispute Resolution", "Rate disputes must be submitted in writing within 60 days "
         "of the Explanation of Payment. Disputes are resolved through binding arbitration."),
        ("Termination", "Either party may terminate with 90 days written notice. "
         "Provider must continue to treat members for 90 days post-termination."),
    ]

    for title, body in terms:
        story.append(Paragraph(f"<b>{title}</b>", styles["heading"]))
        story.append(Paragraph(body, styles["body"]))
        story.append(Spacer(1, 0.05*inch))

    story.append(PageBreak())

    # --- Fee Schedule Table ---
    story.append(Paragraph("Fee Schedule — Professional Services", styles["title"]))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(
        "All rates are per-unit, non-facility. Modifier adjustments: "
        "-26 (professional component) = 40% of listed rate. "
        "-TC (technical component) = 60% of listed rate. "
        "-50 (bilateral) = 150% of listed rate.",
        styles["small"]
    ))
    story.append(Spacer(1, 0.15*inch))

    # Build table
    header = [
        Paragraph("<b>CPT Code</b>", styles["small"]),
        Paragraph("<b>Description</b>", styles["small"]),
        Paragraph("<b>Rate (per unit)</b>", styles["small"]),
    ]

    data = [header]
    for cpt, desc, rate in FEE_SCHEDULE:
        data.append([
            Paragraph(cpt, styles["small"]),
            Paragraph(desc, styles["small"]),
            Paragraph(f"${rate:.2f}", styles["small"]),
        ])

    t = Table(data, colWidths=[1*inch, 4*inch, 1.2*inch])
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), AETNA_PURPLE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    for i in range(2, len(data), 2):
        style_cmds.append(("BACKGROUND", (0, i), (-1, i), LIGHT_GRAY))
    t.setStyle(TableStyle(style_cmds))
    story.append(t)

    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(
        f"Total CPT codes listed: {len(FEE_SCHEDULE)}",
        styles["small"]
    ))
    story.append(Spacer(1, 0.5*inch))

    # --- Signature Page ---
    story.append(PageBreak())
    story.append(Paragraph("Signatures", styles["title"]))
    story.append(Spacer(1, 0.5*inch))

    sig_data = [
        ["", ""],
        [Paragraph("<b>For Aetna Better Health of Florida:</b>", styles["body"]),
         Paragraph("<b>For Sunrise Family Medicine:</b>", styles["body"])],
        ["", ""],
        [Paragraph("_" * 40, styles["body"]), Paragraph("_" * 40, styles["body"])],
        [Paragraph("Name: Sarah Johnson", styles["small"]),
         Paragraph("Name: Dr. Maria Santos", styles["small"])],
        [Paragraph("Title: VP, Provider Relations", styles["small"]),
         Paragraph("Title: Practice Owner", styles["small"])],
        [Paragraph("Date: December 15, 2024", styles["small"]),
         Paragraph("Date: December 18, 2024", styles["small"])],
    ]

    sig_t = Table(sig_data, colWidths=[3.25*inch, 3.25*inch])
    sig_t.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(sig_t)

    story.append(Spacer(1, 1*inch))
    story.append(Paragraph(
        "Aetna Better Health of Florida &bull; 123 Healthcare Blvd, Suite 400, "
        "Tampa, FL 33602 &bull; (800) 555-0199",
        styles["footer"]
    ))

    doc.build(story)
    print(f"Generated: {OUTPUT_FILE}")
    print(f"  Pages: 4 (cover, terms, fee schedule, signatures)")
    print(f"  CPT codes: {len(FEE_SCHEDULE)}")


if __name__ == "__main__":
    build_pdf()
