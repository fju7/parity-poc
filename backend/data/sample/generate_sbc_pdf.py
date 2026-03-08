"""Generate a realistic SBC PDF for Midwest Manufacturing Co (2025).

Produces Midwest_Manufacturing_SBC_2025.pdf — a 2-page Summary of Benefits
and Coverage that matches the CMS standardized format. When parsed by the
employer scorecard, it should produce a C+ grade (~66/100).
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
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "Midwest_Manufacturing_SBC_2025.pdf")

CIGNA_BLUE = colors.HexColor("#006FA6")
LIGHT_BLUE = colors.HexColor("#E8F4FA")
LIGHT_GRAY = colors.HexColor("#F5F5F5")
DARK_GRAY = colors.HexColor("#333333")
MED_GRAY = colors.HexColor("#666666")


def _styles():
    """Build paragraph styles."""
    ss = getSampleStyleSheet()

    ss.add(ParagraphStyle(
        "SBCTitle", parent=ss["Heading1"],
        fontSize=14, textColor=CIGNA_BLUE, spaceAfter=4, leading=17,
    ))
    ss.add(ParagraphStyle(
        "SBCSubtitle", parent=ss["Normal"],
        fontSize=9, textColor=MED_GRAY, spaceAfter=2, leading=12,
    ))
    ss.add(ParagraphStyle(
        "SectionHead", parent=ss["Heading2"],
        fontSize=11, textColor=colors.white, spaceBefore=10, spaceAfter=4,
        leading=14, backColor=CIGNA_BLUE, borderPadding=(4, 6, 4, 6),
    ))
    ss.add(ParagraphStyle(
        "CellLeft", parent=ss["Normal"],
        fontSize=8.5, leading=11, textColor=DARK_GRAY,
    ))
    ss.add(ParagraphStyle(
        "CellBold", parent=ss["Normal"],
        fontSize=8.5, leading=11, textColor=DARK_GRAY,
    ))
    ss.add(ParagraphStyle(
        "SmallPrint", parent=ss["Normal"],
        fontSize=7, leading=9, textColor=MED_GRAY,
    ))
    ss.add(ParagraphStyle(
        "BodyText9", parent=ss["Normal"],
        fontSize=9, leading=12, textColor=DARK_GRAY,
    ))
    return ss


def _section_header(text, styles):
    """Blue banner section header."""
    return Table(
        [[Paragraph(f"<b>{text}</b>", styles["SectionHead"])]],
        colWidths=[7.2 * inch],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), CIGNA_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]),
    )


def _two_col_table(rows, col_widths=None, styles=None):
    """Create a two-column table with alternating row shading."""
    if col_widths is None:
        col_widths = [4.0 * inch, 3.2 * inch]

    s = styles or _styles()
    table_data = []
    for q, a in rows:
        table_data.append([
            Paragraph(q, s["CellLeft"]),
            Paragraph(f"<b>{a}</b>", s["CellLeft"]),
        ])

    ts = TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ])
    # Alternating shading
    for i in range(len(table_data)):
        if i % 2 == 0:
            ts.add("BACKGROUND", (0, i), (-1, i), LIGHT_GRAY)
        else:
            ts.add("BACKGROUND", (0, i), (-1, i), colors.white)

    return Table(table_data, colWidths=col_widths, style=ts)


def _three_col_table(rows, styles=None):
    """Create a three-column table (event, service, your cost) with shading."""
    s = styles or _styles()
    col_widths = [2.4 * inch, 2.4 * inch, 2.4 * inch]
    table_data = []
    for cells in rows:
        table_data.append([Paragraph(c, s["CellLeft"]) for c in cells])

    ts = TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), CIGNA_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ])
    for i in range(1, len(table_data)):
        if i % 2 == 1:
            ts.add("BACKGROUND", (0, i), (-1, i), LIGHT_BLUE)
        else:
            ts.add("BACKGROUND", (0, i), (-1, i), colors.white)

    return Table(table_data, colWidths=col_widths, style=ts)


def build_pdf():
    """Generate the SBC PDF."""
    doc = SimpleDocTemplate(
        OUTPUT_FILE,
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )

    s = _styles()
    story = []

    # ---- PAGE 1 ----

    # Title block
    story.append(Paragraph(
        "Summary of Benefits and Coverage: What this Plan Covers &amp; What You Pay For Covered Services",
        s["SBCTitle"],
    ))
    story.append(Paragraph(
        "<b>Coverage Period: 01/01/2025 – 12/31/2025</b>",
        s["SBCSubtitle"],
    ))
    story.append(Paragraph(
        "<b>Coverage for:</b> Individual + Family &nbsp;&nbsp;|&nbsp;&nbsp; <b>Plan Type:</b> PPO",
        s["SBCSubtitle"],
    ))
    story.append(Paragraph(
        "<b>Employer:</b> Midwest Manufacturing Co. &nbsp;&nbsp;|&nbsp;&nbsp; "
        "<b>Issuer:</b> Cigna Health and Life Insurance Company",
        s["SBCSubtitle"],
    ))
    story.append(Paragraph(
        "<b>Plan Name:</b> Cigna PPO Select — Midwest Manufacturing Group #MWM-2025",
        s["SBCSubtitle"],
    ))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1, color=CIGNA_BLUE))
    story.append(Spacer(1, 6))

    # Important Questions
    story.append(_section_header("Important Questions", s))
    story.append(Spacer(1, 2))
    story.append(_two_col_table([
        ("What is the overall deductible?",
         "$1,200 Individual / $2,400 Family"),
        ("Are there services covered before you meet your deductible?",
         "Yes. Preventive care, primary care and specialist copays, "
         "and prescription drug copays are covered before the deductible."),
        ("Are there other deductibles for specific services?",
         "No."),
        ("What is the out-of-pocket limit for this plan?",
         "$5,500 Individual / $11,000 Family"),
        ("What is not included in the out-of-pocket limit?",
         "Premiums, balance-billing charges, penalties for non-emergency "
         "use of the ER, and healthcare this plan doesn't cover."),
        ("Will you pay less if you use a network provider?",
         "Yes. See www.cigna.com for a list of in-network providers. "
         "Cigna Open Access Plus network. Using out-of-network providers "
         "will cost you more."),
        ("Do you need a referral to see a specialist?",
         "No. You can self-refer to any in-network specialist."),
    ], styles=s))

    story.append(Spacer(1, 8))

    # Common Medical Events table
    story.append(_section_header("Common Medical Events", s))
    story.append(Spacer(1, 2))

    med_rows = [
        ("<b>Common Medical Event</b>", "<b>Services You May Need</b>",
         "<b>What You Will Pay</b>"),
        ("If you visit a health care provider's office or clinic",
         "Primary care visit to treat an injury or illness",
         "<b>$30 copay</b> / visit"),
        ("",
         "Specialist visit",
         "<b>$50 copay</b> / visit"),
        ("",
         "Preventive care / screening / immunization",
         "<b>No charge.</b> Deductible does not apply."),
        ("If you have a test",
         "Diagnostic test (x-ray, blood work)",
         "<b>20% coinsurance</b> after deductible"),
        ("",
         "Imaging (CT/PET scans, MRIs)",
         "<b>20% coinsurance</b> after deductible"),
        ("If you need drugs to treat your illness or condition",
         "Generic drugs (Tier 1)",
         "<b>$10 copay</b> / prescription"),
        ("",
         "Preferred brand drugs (Tier 2)",
         "<b>$40 copay</b> / prescription"),
        ("",
         "Non-preferred brand drugs (Tier 3)",
         "<b>$80 copay</b> / prescription"),
        ("",
         "Specialty drugs (Tier 4)",
         "<b>20% coinsurance up to $250</b> / script"),
        ("If you have outpatient surgery",
         "Facility fee (e.g., ambulatory surgery center)",
         "<b>20% coinsurance</b> after deductible"),
        ("If you need immediate medical attention",
         "Emergency room care",
         "<b>$150 copay</b> + 20% coinsurance"),
        ("",
         "Urgent care",
         "<b>$75 copay</b> / visit"),
        ("",
         "Telehealth (MDLive)",
         "<b>$0 copay</b>"),
        ("If you have a hospital stay",
         "Hospital stay (facility fee, doctor, etc.)",
         "<b>20% coinsurance</b> after deductible"),
        ("If you need mental health, behavioral health, or substance abuse services",
         "Outpatient services — office visit",
         "<b>$30 copay</b> / visit (same as primary care)"),
        ("",
         "Inpatient services",
         "<b>20% coinsurance</b> after deductible"),
    ]
    story.append(_three_col_table(med_rows, styles=s))

    story.append(Spacer(1, 8))

    # Excluded services note
    story.append(Paragraph(
        "<b>Excluded Services &amp; Limitations (summary):</b> "
        "Cosmetic surgery, long-term custodial care, non-emergency care "
        "when traveling outside the U.S., routine dental and vision care "
        "(available under separate plans). Weight loss programs are not "
        "covered. Infertility treatment is not covered. "
        "This plan is <b>not HSA-eligible</b>; no HRA is included.",
        s["SmallPrint"],
    ))

    # ---- PAGE 2 ----
    story.append(PageBreak())

    # Header repeated
    story.append(Paragraph(
        "Cigna PPO Select — Midwest Manufacturing Group #MWM-2025",
        s["SBCTitle"],
    ))
    story.append(Paragraph(
        "Coverage Period: 01/01/2025 – 12/31/2025 &nbsp;&nbsp;|&nbsp;&nbsp; Page 2 of 2",
        s["SBCSubtitle"],
    ))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1, color=CIGNA_BLUE))
    story.append(Spacer(1, 8))

    # Excluded Services
    story.append(_section_header("Excluded Services & Other Covered Services", s))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "<b>Services Your Plan Generally Does NOT Cover</b> (check your policy "
        "or plan document for more information and a list of any other excluded services)",
        s["BodyText9"],
    ))
    story.append(Spacer(1, 4))

    excluded_items = [
        "Acupuncture",
        "Cosmetic surgery",
        "Dental care (Adult) — available under separate dental plan",
        "Infertility treatment",
        "Long-term care / custodial care",
        "Non-emergency care when traveling outside the U.S.",
        "Routine eye care (Adult) — available under separate vision plan",
        "Routine foot care",
        "Weight loss programs",
        "Private-duty nursing",
    ]
    for item in excluded_items:
        story.append(Paragraph(f"• {item}", s["CellLeft"]))
    story.append(Spacer(1, 4))

    story.append(Paragraph(
        "<b>Other Covered Services</b> (limitations may apply to these services; "
        "this isn't a complete list. Please see your plan document.)",
        s["BodyText9"],
    ))
    story.append(Spacer(1, 4))
    other_items = [
        "Bariatric surgery (prior authorization required)",
        "Chiropractic care (20 visits/year)",
        "Durable medical equipment (20% coinsurance after deductible)",
        "Hearing aids (one pair every 36 months, up to $2,500)",
        "Home health care (60 visits/year)",
        "Hospice services",
        "Rehabilitation services (60 visits/year combined PT/OT/ST)",
        "Skilled nursing care (60 days/year)",
    ]
    for item in other_items:
        story.append(Paragraph(f"• {item}", s["CellLeft"]))

    story.append(Spacer(1, 12))

    # Your Rights to Continue Coverage
    story.append(_section_header("Your Rights to Continue Coverage", s))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "There are agencies that can help if you want to continue your coverage "
        "after it ends. The contact information for those agencies is: U.S. "
        "Department of Labor's Employee Benefits Security Administration at "
        "1-866-444-3272 or www.dol.gov/ebsa, or the U.S. Department of Health "
        "and Human Services at 1-877-267-2323 x61565 or www.cciio.cms.gov. "
        "Other coverage options may be available to you through the Health "
        "Insurance Marketplace. Visit www.HealthCare.gov for more information.",
        s["BodyText9"],
    ))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "COBRA continuation coverage may be available if you lose group coverage. "
        "Contact your plan administrator for details.",
        s["BodyText9"],
    ))

    story.append(Spacer(1, 12))

    # Grievance and Appeals
    story.append(_section_header("Your Grievance and Appeals Rights", s))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "There are agencies that can help if you have a complaint against your "
        "plan for a denial of a claim. This complaint is called a grievance or "
        "appeal. For more information about your rights, this notice, or "
        "assistance, contact: Cigna Customer Service at <b>1-800-CIGNA24</b> "
        "(1-800-244-6224), 24 hours a day, 7 days a week. You may also contact "
        "the U.S. Department of Labor's Employee Benefits Security Administration "
        "at 1-866-444-3272 or www.dol.gov/ebsa.",
        s["BodyText9"],
    ))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Additionally, a consumer assistance program may help you file your "
        "appeal. Contact your state insurance department for more information.",
        s["BodyText9"],
    ))

    story.append(Spacer(1, 16))

    # Footer
    story.append(HRFlowable(width="100%", thickness=0.5, color=MED_GRAY))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Questions? Call <b>1-800-CIGNA24</b> (1-800-244-6224) or visit us at "
        "www.cigna.com. &nbsp;&nbsp;|&nbsp;&nbsp; "
        "If you aren't clear about any of the underlined terms used in this form, "
        "see the Glossary.",
        s["SmallPrint"],
    ))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "This document is only a summary. For a detailed description of coverage, "
        "consult the plan document or policy. This SBC was generated for "
        "demonstration purposes.",
        s["SmallPrint"],
    ))

    doc.build(story)
    file_size = os.path.getsize(OUTPUT_FILE)
    print(f"Generated {OUTPUT_FILE}")
    print(f"  Size: {file_size:,} bytes ({file_size / 1024:.1f} KB)")
    print(f"  Pages: 2")


if __name__ == "__main__":
    build_pdf()
