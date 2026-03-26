"""Parity Billing — white-label PDF branding utilities.

Provides branding context (logo, company name, header/footer text) and
ReportLab helper functions for generating branded billing reports.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    PageBreak, HRFlowable,
)


# ---------------------------------------------------------------------------
# Brand colors (matching Parity Provider palette)
# ---------------------------------------------------------------------------
TEAL = colors.HexColor("#0D9488")
NAVY = colors.HexColor("#1E293B")
SLATE = colors.HexColor("#64748B")
LIGHT_TEAL = colors.HexColor("#F0FDFA")
LIGHT_GRAY = colors.HexColor("#F8FAFC")
RED = colors.HexColor("#DC2626")
AMBER = colors.HexColor("#D97706")
WHITE = colors.white


# ---------------------------------------------------------------------------
# Shared styles
# ---------------------------------------------------------------------------
def _get_styles():
    """Return a dict of ParagraphStyles for billing reports."""
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "BillingTitle", parent=base["Normal"],
            fontSize=28, leading=34, textColor=TEAL, alignment=1,
            spaceAfter=6, fontName="Helvetica-Bold",
        ),
        "subtitle": ParagraphStyle(
            "BillingSubtitle", parent=base["Normal"],
            fontSize=14, leading=18, textColor=NAVY, alignment=1,
            spaceAfter=4,
        ),
        "header_text": ParagraphStyle(
            "BillingHeaderText", parent=base["Normal"],
            fontSize=11, leading=14, textColor=SLATE, alignment=1,
            spaceAfter=12,
        ),
        "heading2": ParagraphStyle(
            "BillingH2", parent=base["Normal"],
            fontSize=14, leading=18, textColor=NAVY,
            spaceBefore=16, spaceAfter=8, fontName="Helvetica-Bold",
        ),
        "body": ParagraphStyle(
            "BillingBody", parent=base["Normal"],
            fontSize=10, leading=14, textColor=NAVY,
        ),
        "small": ParagraphStyle(
            "BillingSmall", parent=base["Normal"],
            fontSize=8, leading=10, textColor=SLATE,
        ),
        "footer": ParagraphStyle(
            "BillingFooter", parent=base["Normal"],
            fontSize=8, leading=10, textColor=SLATE, alignment=1,
            fontName="Helvetica-Oblique",
        ),
        "kpi_value": ParagraphStyle(
            "KpiValue", parent=base["Normal"],
            fontSize=20, leading=24, textColor=TEAL, alignment=1,
            fontName="Helvetica-Bold",
        ),
        "kpi_label": ParagraphStyle(
            "KpiLabel", parent=base["Normal"],
            fontSize=8, leading=10, textColor=SLATE, alignment=1,
        ),
    }


def get_billing_branding(billing_company_id: str, sb) -> dict:
    """Fetch branding context from billing_companies."""
    row = sb.table("billing_companies").select(
        "company_name, logo_url, report_header_text, report_footer_text"
    ).eq("id", billing_company_id).limit(1).execute()

    if not row.data:
        return {"company_name": "", "logo_url": None,
                "header_text": None, "footer_text": None}

    bc = row.data[0]
    return {
        "company_name": bc.get("company_name") or "",
        "logo_url": bc.get("logo_url"),
        "header_text": bc.get("report_header_text"),
        "footer_text": bc.get("report_footer_text"),
    }


def fetch_logo_bytes(logo_url: str, sb) -> bytes | None:
    """Download logo image bytes from Supabase storage."""
    if not logo_url:
        return None
    try:
        # logo_url is like "billing-logos/{bc_id}/logo.png"
        # Extract bucket and path
        parts = logo_url.split("/", 1)
        if len(parts) != 2:
            return None
        bucket, path = parts
        data = sb.storage.from_(bucket).download(path)
        return data if data else None
    except Exception as e:
        print(f"[pdf_branding] Logo download failed: {e}")
        return None


def build_cover_page(branding: dict, practice_name: str, report_type: str,
                     date_range_label: str, logo_bytes: bytes = None) -> list:
    """Build a ReportLab story list for the branded cover page."""
    styles = _get_styles()
    story = []

    story.append(Spacer(1, 1.2 * inch))

    # Logo
    if logo_bytes:
        try:
            img = Image(io.BytesIO(logo_bytes))
            # Scale to max height 80px (about 1.1 inch), preserve aspect ratio
            max_h = 80
            ratio = img.imageWidth / img.imageHeight if img.imageHeight else 1
            img.drawHeight = max_h
            img.drawWidth = max_h * ratio
            img.hAlign = "CENTER"
            story.append(img)
            story.append(Spacer(1, 0.3 * inch))
        except Exception:
            pass  # Skip logo if image parsing fails

    # Company name
    story.append(Paragraph(branding["company_name"], styles["title"]))

    # Header text
    if branding.get("header_text"):
        story.append(Paragraph(branding["header_text"], styles["header_text"]))

    story.append(Spacer(1, 0.15 * inch))
    story.append(HRFlowable(width="60%", thickness=2, color=TEAL, hAlign="CENTER"))
    story.append(Spacer(1, 0.4 * inch))

    # Practice name
    story.append(Paragraph(f"Report for: <b>{practice_name}</b>", styles["subtitle"]))
    story.append(Spacer(1, 0.1 * inch))

    # Report type
    type_labels = {
        "denial_summary": "Denial Summary Report",
        "payer_performance": "Payer Performance Report",
        "appeal_roi": "Appeal & Recovery Report",
    }
    story.append(Paragraph(type_labels.get(report_type, report_type), styles["subtitle"]))
    story.append(Spacer(1, 0.15 * inch))

    # Date range
    story.append(Paragraph(f"Period: {date_range_label}", styles["body"]))
    story.append(Spacer(1, 0.05 * inch))

    # Generated date
    now = datetime.now(timezone.utc).strftime("%B %d, %Y")
    story.append(Paragraph(f"Generated: {now}", styles["body"]))

    # Footer text at bottom
    if branding.get("footer_text"):
        story.append(Spacer(1, 2 * inch))
        story.append(Paragraph(branding["footer_text"], styles["footer"]))

    story.append(PageBreak())
    return story


def build_header_footer_func(branding: dict):
    """Return a function for SimpleDocTemplate onLaterPages callback."""
    company_name = branding.get("company_name") or ""

    def _draw(canvas, doc):
        canvas.saveState()
        # Header: company name, top right
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(SLATE)
        canvas.drawRightString(
            doc.pagesize[0] - 0.75 * inch,
            doc.pagesize[1] - 0.5 * inch,
            company_name,
        )
        # Footer: page number, bottom center
        canvas.drawCentredString(
            doc.pagesize[0] / 2,
            0.5 * inch,
            f"Page {doc.page}",
        )
        canvas.restoreState()

    return _draw


def build_kpi_row(kpis: list) -> Table:
    """Build a row of KPI tiles as a ReportLab Table.

    kpis: list of {"label": str, "value": str}
    """
    styles = _get_styles()
    data = [[Paragraph(k["value"], styles["kpi_value"]) for k in kpis],
            [Paragraph(k["label"], styles["kpi_label"]) for k in kpis]]
    col_width = 6.5 * inch / len(kpis) if kpis else 1.5 * inch
    t = Table(data, colWidths=[col_width] * len(kpis))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_TEAL),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, 0), 12),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 0.5, TEAL),
        ("LINEBELOW", (0, 0), (-1, 0), 0, colors.white),
    ]))
    return t


def build_data_table(headers: list, rows: list, col_widths: list = None) -> Table:
    """Build a styled data table."""
    styles = _get_styles()
    header_paras = [Paragraph(f"<b>{h}</b>", styles["small"]) for h in headers]
    body_rows = []
    for row in rows:
        body_rows.append([Paragraph(str(cell), styles["small"]) for cell in row])
    data = [header_paras] + body_rows

    t = Table(data, colWidths=col_widths)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    # Alternating row colors
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), LIGHT_GRAY))
    t.setStyle(TableStyle(style_cmds))
    return t
