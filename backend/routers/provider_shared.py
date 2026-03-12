"""Shared helpers, constants, and Pydantic models for provider sub-routers."""

from __future__ import annotations

import io
import json
import os
import re
import time
from collections import Counter
from pathlib import Path
from typing import List, Optional

from fastapi import HTTPException, Request
from pydantic import BaseModel

from supabase import create_client

from routers.benchmark import resolve_locality, lookup_rate, get_all_pfs_rates_for_locality
from utils.parse_835 import parse_835

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# ---------------------------------------------------------------------------
# Supabase client (lazy singleton)
# ---------------------------------------------------------------------------

_supabase = None


def _get_supabase():
    global _supabase
    if _supabase is None:
        url = os.environ.get("SUPABASE_URL", "https://kfxxpscdwoemtzylhhhb.supabase.co")
        key = os.environ.get("SUPABASE_SERVICE_KEY", "")
        if not key:
            raise RuntimeError("SUPABASE_SERVICE_KEY not set")
        _supabase = create_client(url, key)
    return _supabase


STRIPE_PRICE_PROVIDER_MONTHLY = os.environ.get("STRIPE_PRICE_PROVIDER_MONTHLY", "")


class _AuthUser:
    """Thin wrapper so legacy code can do user.id and user.email."""
    def __init__(self, data: dict):
        self._data = data
        self.id = data["company_id"]
        self.email = data.get("email", "")
        self.role = data.get("role", "member")
        self.company = data.get("company")
        self.full_name = data.get("full_name")


def _get_authenticated_user(request: Request):
    """Validate Bearer token via unified auth. Returns _AuthUser with .id, .email compat."""
    from routers.auth import get_current_user
    auth_header = request.headers.get("authorization", "")
    sb = _get_supabase()
    user_data = get_current_user(auth_header, sb)
    return _AuthUser(user_data)


async def _verify_admin(request: Request):
    """Verify request comes from admin (CRON_SECRET header or unified auth admin role)."""
    # Option 1: CRON_SECRET header (for server-to-server / cron jobs)
    cron_secret = os.environ.get("CRON_SECRET")
    if cron_secret and request.headers.get("X-Cron-Secret") == cron_secret:
        return

    # Option 2: Bearer token with admin role via unified auth
    try:
        user = _get_authenticated_user(request)
        if user.role == "admin":
            return
    except Exception:
        pass

    raise HTTPException(status_code=401, detail="Unauthorized")


# ---------------------------------------------------------------------------
# Anthropic Claude client (lazy singleton)
# ---------------------------------------------------------------------------

_anthropic_client = None


def _get_claude():
    global _anthropic_client
    if _anthropic_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="AI analysis is not configured on this server.",
            )
        try:
            import anthropic
            _anthropic_client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="AI dependencies are not installed.",
            )
    return _anthropic_client


def _call_claude(system_prompt: str, user_content, max_tokens: int = 4096) -> dict:
    """Call Claude API with retry on 529, return parsed JSON.

    user_content can be a string or a list of content blocks (for multimodal).
    """
    client = _get_claude()
    backoff_delays = [2, 5, 10]
    response = None

    for attempt in range(len(backoff_delays) + 1):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
                temperature=0,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            break
        except Exception as exc:
            err_str = str(exc)
            if "529" in err_str and attempt < len(backoff_delays):
                delay = backoff_delays[attempt]
                print(f"[Provider AI] Claude overloaded (529), retry {attempt + 1}/{len(backoff_delays)} in {delay}s...")
                time.sleep(delay)
                continue
            print(f"[Provider AI] API error: {exc}")
            if "529" in err_str:
                return None  # Non-fatal — caller handles gracefully
            return None

    if response is None:
        return None

    raw_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            raw_text += block.text

    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```\s*$", "", raw_text)
    raw_text = raw_text.strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        print(f"[Provider AI] Invalid JSON: {raw_text[:500]}")
        return None


def _call_claude_text(system_prompt: str, user_content, max_tokens: int = 4096) -> Optional[str]:
    """Call Claude API and return raw text (not JSON). Used for narrative sections."""
    client = _get_claude()
    backoff_delays = [2, 5, 10]
    response = None

    for attempt in range(len(backoff_delays) + 1):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            break
        except Exception as exc:
            err_str = str(exc)
            if "529" in err_str and attempt < len(backoff_delays):
                delay = backoff_delays[attempt]
                print(f"[Provider AI] Claude overloaded (529), retry {attempt + 1}/{len(backoff_delays)} in {delay}s...")
                time.sleep(delay)
                continue
            print(f"[Provider AI] API error: {exc}")
            return None

    if response is None:
        return None

    raw_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            raw_text += block.text

    return raw_text.strip()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class PayerRate(BaseModel):
    payer_name: str
    rate: float


class ContractRateItem(BaseModel):
    cpt: str
    description: Optional[str] = ""
    rates: dict  # {payer_name: rate}


class SaveRatesRequest(BaseModel):
    user_id: str
    payer_name: str
    rates: List[ContractRateItem]


class RemittanceLine(BaseModel):
    cpt_code: str
    code_type: str = "CPT"
    billed_amount: float
    paid_amount: float
    units: int = 1
    adjustments: Optional[str] = ""
    claim_id: Optional[str] = ""


class AnalyzeRequest(BaseModel):
    user_id: str
    payer_name: str
    zip_code: Optional[str] = ""
    contract_rates: dict  # {cpt_code: rate}
    remittance_lines: List[RemittanceLine]


class CodingLine(BaseModel):
    cpt_code: str
    units: int = 1
    billed_amount: float = 0.0


class CodingAnalyzeRequest(BaseModel):
    user_id: str
    specialty: str = ""
    date_range: Optional[str] = ""
    lines: List[CodingLine]


class DenialLine(BaseModel):
    cpt_code: str
    billed_amount: float = 0.0
    adjustment_codes: str = ""
    claim_id: str = ""


class AnalyzeDenialsRequest(BaseModel):
    payer_name: str
    denied_lines: List[DenialLine]


class ExtractFeeScheduleTextRequest(BaseModel):
    text: str


class CalculateMedicarePercentageRequest(BaseModel):
    payer_name: str
    percentage: float  # e.g., 115 for 115%
    zip_code: str
    effective_date: str = ""


class AuditReportRequest(BaseModel):
    audit_id: Optional[str] = None
    analysis_data: Optional[dict] = None  # inline data for immediate report
    trend_data: Optional[dict] = None  # optional trend data for month 2+ reports


class GenerateAppealRequest(BaseModel):
    claim_id: str = ""
    denial_code: str = ""
    cpt_code: str = ""
    billed_amount: float = 0.0
    payer_name: str = ""
    date_of_service: str = ""
    practice_name: str = ""
    practice_address: str = ""
    provider_name: str = ""
    npi: str = ""
    patient_name: str = ""
    # Optional context
    subscription_id: Optional[str] = None
    audit_id: Optional[str] = None


class GenerateAppealBatchRequest(BaseModel):
    denials: List[dict] = []  # list of denial dicts matching GenerateAppealRequest fields
    subscription_id: Optional[str] = None
    audit_id: Optional[str] = None


class UpdateAppealStatusRequest(BaseModel):
    appeal_id: str
    status: str  # drafted, sent, won, lost, pending
    outcome_amount: Optional[float] = None
    notes: Optional[str] = None


class SubmitAuditRequest(BaseModel):
    practice_name: str
    specialty: str = ""
    num_providers: int = 1
    billing_company: str = ""
    contact_email: str
    contact_phone: str = ""
    payer_list: list = []  # [{payer_name, fee_schedule_method, code_count, fee_schedule_data}]
    remittance_data: list = []  # [{filename, payer_name, claims: [{claim_id, lines: [...]}]}]
    consent: bool = False
    user_id: Optional[str] = None


# Admin-specific models
class AdminArchiveBody(BaseModel):
    audit_id: str
    archived: bool = True


class AdminDeleteBody(BaseModel):
    audit_id: str


class AdminRunAnalysisBody(BaseModel):
    audit_id: str
    zip_code: str = ""       # optional override for Medicare locality
    percentage: float = 0    # optional override for medicare-pct method


class AdminNotesBody(BaseModel):
    audit_id: str
    notes: str


class AdminDeliverBody(BaseModel):
    audit_id: str


class AdminFollowUpBody(BaseModel):
    audit_id: str


class AdminStatusBody(BaseModel):
    audit_id: str
    status: str


class AdminConvertBody(BaseModel):
    audit_id: str


class AdminAddMonthBody(BaseModel):
    subscription_id: str


class SubscriptionCheckoutBody(BaseModel):
    audit_id: str


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

FEE_SCHEDULE_EXTRACTION_PROMPT = """You are a medical billing data extraction specialist. You will receive a document containing a payer fee schedule or contract rate table. Extract all CPT/HCPCS codes and their corresponding contracted reimbursement rates.

Return ONLY valid JSON matching this exact structure:
{
  "payer_name": "extracted payer name or empty string if not found",
  "effective_date": "YYYY-MM-DD or empty string if not found",
  "rates": [
    {"cpt": "99213", "rate": 95.50, "description": "Office visit, est. patient, level 3"}
  ]
}

Rules:
- Extract every CPT/HCPCS code visible in the document
- Rate should be the dollar amount per unit
- If multiple rates exist per code (e.g., facility/non-facility), use the non-facility rate
- If a code has no rate (N/A, blank, $0), skip it
- Description can be brief or empty string if not available
- Do not invent or estimate rates — only extract what is explicitly shown
- If no CPT codes or rates are found, return an empty rates array"""


DENIAL_SYSTEM_PROMPT = """You are a medical billing expert. You will receive a list of denied claims from an 835 remittance file. For each denial reason code present, explain the reason in plain language, assess whether an appeal is likely to succeed, estimate the value of attempting an appeal, and if appealable, draft a brief appeal letter template. Also identify patterns across the full denial set.

Return ONLY valid JSON matching this exact structure, with no other text:
{
  "denial_types": [
    {
      "adjustment_code": "CO-16",
      "plain_language": "explanation of what this code means",
      "is_actionable": true,
      "appeal_worthiness": "high",
      "recommended_action": "specific action to take",
      "appeal_letter_template": "Dear [Payer Name],\\n\\nWe are writing to appeal...",
      "count": 3,
      "total_value": 450.00
    }
  ],
  "pattern_summary": "summary of patterns across all denials",
  "total_recoverable_value": 1240.00,
  "preventable_denial_rate": 0.67
}

appeal_worthiness must be one of: "high", "medium", "low".
Group denials by adjustment code. Include count and total_value per group."""


# E&M code families for distribution analysis
EM_CODES = {
    "New Patient": ["99201", "99202", "99203", "99204", "99205"],
    "Established Patient": ["99211", "99212", "99213", "99214", "99215"],
}

# CMS benchmark E&M distributions by specialty (approximate national averages)
EM_BENCHMARKS = {
    "Internal Medicine": {
        "99211": 3, "99212": 8, "99213": 40, "99214": 38, "99215": 11,
    },
    "Family Medicine": {
        "99211": 4, "99212": 10, "99213": 42, "99214": 35, "99215": 9,
    },
    "Cardiology": {
        "99211": 2, "99212": 5, "99213": 25, "99214": 45, "99215": 23,
    },
    "Orthopedics": {
        "99211": 3, "99212": 7, "99213": 30, "99214": 42, "99215": 18,
    },
    "Dermatology": {
        "99211": 5, "99212": 12, "99213": 45, "99214": 30, "99215": 8,
    },
    "Radiology": {
        "99211": 2, "99212": 6, "99213": 35, "99214": 40, "99215": 17,
    },
    "Pathology/Lab": {
        "99211": 3, "99212": 8, "99213": 38, "99214": 38, "99215": 13,
    },
    "Other": {
        "99211": 3, "99212": 8, "99213": 38, "99214": 38, "99215": 13,
    },
}

SUBSCRIPTION_STATUS_COLORS = {
    "active": "green",
    "canceled": "gray",
    "past_due": "red",
}


# ---------------------------------------------------------------------------
# Email template helpers
# ---------------------------------------------------------------------------

def _email_wrapper(inner_html: str) -> str:
    """Wrap email body in consistent branded template."""
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #1E293B;">
        <div style="background: #0D9488; padding: 24px; text-align: center;">
            <h1 style="color: #fff; margin: 0; font-size: 24px;">Parity Audit</h1>
            <p style="color: #CCFBF1; margin: 4px 0 0; font-size: 14px;">by CivicScale</p>
        </div>
        <div style="padding: 32px 24px;">
            {inner_html}
        </div>
        <div style="background: #F8FAFC; padding: 16px 24px; text-align: center; border-top: 1px solid #E2E8F0;">
            <p style="color: #94A3B8; font-size: 12px; margin: 0;">
                Parity Audit by CivicScale &middot; Benchmark comparisons use publicly available CMS Medicare data.
                Not legal or financial advice. &middot; civicscale.ai
            </p>
        </div>
    </div>
    """


def _send_submission_confirmation(audit: dict):
    """Email 1: Submission confirmation — sent immediately when audit is submitted."""
    try:
        import resend
        resend_key = os.environ.get("RESEND_API_KEY")
        if not resend_key:
            print("[AuditEmail] RESEND_API_KEY not configured, skipping")
            return
        resend.api_key = resend_key

        practice_name = audit.get("practice_name", "Practice")
        contact_email = audit.get("contact_email", "")
        audit_id = audit.get("id", "")
        payer_list = audit.get("payer_list", [])
        payer_names = ", ".join(p.get("payer_name", "Unknown") for p in payer_list) or "Not specified"
        frontend_url = os.environ.get("FRONTEND_URL", "https://civicscale.ai")

        inner = f"""
        <h2 style="color: #1E293B; margin-top: 0;">Your Parity Audit has been submitted</h2>
        <p>Thank you for submitting your billing data for analysis. Your Parity Audit Report will be
        delivered to this email address within <strong>5-7 business days</strong>.</p>

        <div style="background: #F0FDFA; border: 1px solid #99F6E4; border-radius: 8px; padding: 16px; margin: 20px 0;">
            <p style="margin: 0 0 8px; font-weight: 600;">Audit Details:</p>
            <p style="margin: 4px 0; font-size: 14px; color: #475569;">Audit ID: <code>{audit_id}</code></p>
            <p style="margin: 4px 0; font-size: 14px; color: #475569;">Practice: {practice_name}</p>
            <p style="margin: 4px 0; font-size: 14px; color: #475569;">Payers analyzed: {payer_names}</p>
        </div>

        <p style="text-align: center; margin: 20px 0 0; font-size: 14px;">
            <a href="{frontend_url}/audit/account" style="color: #0D9488; font-weight: 600;">View your audit status &rarr;</a>
        </p>

        <p>If you have questions, reply to this email or contact
        <a href="mailto:fred@civicscale.ai" style="color: #0D9488;">fred@civicscale.ai</a>.</p>
        """

        resend.Emails.send({
            "from": "Parity Provider <notifications@civicscale.ai>",
            "to": [contact_email],
            "subject": f"Your Parity Audit has been submitted — {practice_name}",
            "html": _email_wrapper(inner),
        })
        print(f"[AuditEmail] Submission confirmation sent to {contact_email}")

    except Exception as exc:
        print(f"[AuditEmail] Submission confirmation failed: {exc}")


def _send_delivery_email(audit: dict, admin_notes: str = "", report_token: str = ""):
    """Email 2: Report delivery — sent when admin clicks 'Deliver Report'."""
    try:
        import resend
        resend_key = os.environ.get("RESEND_API_KEY")
        if not resend_key:
            print("[AuditEmail] RESEND_API_KEY not configured, skipping")
            return
        resend.api_key = resend_key

        practice_name = audit.get("practice_name", "Practice")
        contact_email = audit.get("contact_email", "")
        audit_id = audit.get("id", "")
        payer_list = audit.get("payer_list", [])
        payer_count = len(payer_list)
        frontend_url = os.environ.get("FRONTEND_URL", "https://civicscale.ai")

        # Try to get summary stats from analysis
        analysis_ids = audit.get("analysis_ids", [])
        total_underpayment = 0
        total_lines = 0

        if analysis_ids:
            try:
                sb = _get_supabase()
                for aid in analysis_ids[:10]:
                    row = sb.table("provider_analyses").select("result_json").eq("id", aid).execute()
                    if row.data:
                        rj = row.data[0].get("result_json", {})
                        s = rj.get("summary", {})
                        total_underpayment += s.get("total_underpayment", 0)
                        total_lines += s.get("line_count", 0)
            except Exception as exc:
                print(f"[AuditEmail] Failed to fetch analysis stats: {exc}")

        underpayment_str = f"${total_underpayment:,.2f}" if total_underpayment > 0 else "findings detailed in the report"

        notes_section = ""
        if admin_notes:
            notes_section = f"""
            <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px; padding: 16px; margin: 20px 0;">
                <p style="margin: 0 0 8px; font-weight: 600; color: #1E40AF;">Notes from our review:</p>
                <p style="margin: 0; font-size: 14px; color: #1E40AF;">{admin_notes}</p>
            </div>
            """

        inner = f"""
        <h2 style="color: #1E293B; margin-top: 0;">Your Parity Audit Report is ready</h2>
        <p>We analyzed <strong>{total_lines}</strong> transactions across <strong>{payer_count}</strong>
        payer{"s" if payer_count != 1 else ""} and identified <strong>{underpayment_str}</strong>
        in potential recoverable revenue.</p>

        <div style="text-align: center; margin: 28px 0;">
            <a href="{frontend_url}/report/{report_token}" style="
                display: inline-block; padding: 14px 32px; border-radius: 8px;
                background: #0D9488; color: #fff; font-weight: 600; font-size: 15px;
                text-decoration: none;
            ">View Report Online &rarr;</a>
        </div>
        <p style="text-align: center; margin: 8px 0 0; font-size: 13px;">
            <a href="{frontend_url}/audit/account" style="color: #0D9488;">View your account &rarr;</a>
        </p>

        {notes_section}

        <p>Want to discuss the findings? Reply to this email or contact
        <a href="mailto:fred@civicscale.ai" style="color: #0D9488;">fred@civicscale.ai</a>.</p>
        """

        resend.Emails.send({
            "from": "Parity Provider <notifications@civicscale.ai>",
            "to": [contact_email],
            "subject": f"Your Parity Audit Report is ready — {practice_name}",
            "html": _email_wrapper(inner),
        })
        print(f"[AuditEmail] Delivery email sent to {contact_email}")

        # Admin notification
        resend.Emails.send({
            "from": "Parity Provider <notifications@civicscale.ai>",
            "to": ["fred@civicscale.ai"],
            "subject": f"Audit Delivered: {practice_name}",
            "html": f"<p>Audit report delivered to {contact_email} for {practice_name}.</p>"
                     f"<p>Audit ID: {audit_id}</p>"
                     f"<p>Total underpayment: {underpayment_str}</p>",
        })

    except Exception as exc:
        print(f"[AuditEmail] Delivery email failed: {exc}")


def _send_followup_email(audit: dict):
    """Email 3: Follow-up — sent 3 days after delivery (manual or cron)."""
    try:
        import resend
        resend_key = os.environ.get("RESEND_API_KEY")
        if not resend_key:
            print("[AuditEmail] RESEND_API_KEY not configured, skipping")
            return
        resend.api_key = resend_key

        practice_name = audit.get("practice_name", "Practice")
        contact_email = audit.get("contact_email", "")
        payer_list = audit.get("payer_list", [])
        payer_count = len(payer_list)
        report_token = audit.get("report_token", "")
        frontend_url = os.environ.get("FRONTEND_URL", "https://civicscale.ai")

        # Get total underpayment for messaging
        total_underpayment = 0
        analysis_ids = audit.get("analysis_ids", [])
        if analysis_ids:
            try:
                sb = _get_supabase()
                for aid in analysis_ids[:10]:
                    row = sb.table("provider_analyses").select("result_json").eq("id", aid).execute()
                    if row.data:
                        rj = row.data[0].get("result_json", {})
                        total_underpayment += rj.get("summary", {}).get("total_underpayment", 0)
            except Exception:
                pass

        annualized = total_underpayment * 12
        underpayment_str = f"${annualized:,.2f}" if annualized > 0 else "significant potential"

        report_link_section = ""
        if report_token:
            report_link_section = f"""
            <div style="text-align: center; margin: 24px 0;">
                <a href="{frontend_url}/report/{report_token}" style="
                    display: inline-block; padding: 14px 32px; border-radius: 8px;
                    background: #0D9488; color: #fff; font-weight: 600; font-size: 15px;
                    text-decoration: none;
                ">View Your Report &rarr;</a>
            </div>
            """

        inner = f"""
        <h2 style="color: #1E293B; margin-top: 0;">Following up on your Parity Audit</h2>
        <p>We delivered your Parity Audit Report a few days ago. We identified
        <strong>{underpayment_str}</strong> in potential annual recoverable revenue across
        <strong>{payer_count}</strong> payer{"s" if payer_count != 1 else ""}.</p>

        {report_link_section}
        <p style="text-align: center; margin: 8px 0 0; font-size: 13px;">
            <a href="{frontend_url}/audit/account" style="color: #0D9488;">View your account &rarr;</a>
        </p>

        <p>Have you had a chance to review the findings? If you would like to discuss:</p>
        <ul style="color: #475569; font-size: 14px; line-height: 1.8;">
            <li>Which underpayments to appeal first</li>
            <li>How to address the denial patterns we identified</li>
            <li>What ongoing monitoring would look like for your practice</li>
        </ul>

        <p>Reply to this email or contact
        <a href="mailto:fred@civicscale.ai" style="color: #0D9488;">fred@civicscale.ai</a>.</p>

        <div style="background: #F0FDFA; border: 1px solid #99F6E4; border-radius: 8px; padding: 16px; margin: 20px 0;">
            <p style="margin: 0 0 8px; font-weight: 600; color: #0D9488;">Ongoing Monitoring</p>
            <p style="margin: 0; font-size: 14px; color: #475569;">
                Ongoing monitoring scans every remittance automatically and alerts you when new underpayments
                or denial patterns emerge. It costs <strong>$300/month</strong> and typically pays for itself
                within the first month.
            </p>
        </div>
        """

        resend.Emails.send({
            "from": "Parity Provider <notifications@civicscale.ai>",
            "to": [contact_email],
            "subject": f"Following up on your Parity Audit — {practice_name}",
            "html": _email_wrapper(inner),
        })
        print(f"[AuditEmail] Follow-up sent to {contact_email}")

        # Admin tracking
        resend.Emails.send({
            "from": "Parity Provider <notifications@civicscale.ai>",
            "to": ["fred@civicscale.ai"],
            "subject": f"Follow-up sent: {practice_name}",
            "html": f"<p>Follow-up email sent to {contact_email} for {practice_name}.</p>",
        })

    except Exception as exc:
        print(f"[AuditEmail] Follow-up email failed: {exc}")


# ---------------------------------------------------------------------------
# Shared analysis helpers
# ---------------------------------------------------------------------------

def _aggregate_underpayments(enriched_lines: list) -> dict:
    """Aggregate underpayment amounts by CPT code."""
    result = {}
    for line in enriched_lines:
        if line.get("flag") == "UNDERPAID" and line.get("variance") is not None:
            cpt = line["cpt_code"]
            result[cpt] = result.get(cpt, 0) + abs(line["variance"])
    return result


def _run_analysis_for_payer(
    payer_name: str,
    rates: dict,
    lines: list,
    user_id: str,
    carrier: str = None,
    locality: str = None,
    sb=None,
) -> dict:
    """Run contract integrity + denial intelligence analysis for a single payer.

    Returns dict with keys: analysis_id, summary, scorecard, line_items, denial_intel, top_underpaid.
    """
    if sb is None:
        sb = _get_supabase()

    enriched_lines = []
    total_contracted = 0.0
    total_paid = 0.0
    total_underpayment = 0.0
    correct_count = 0
    underpaid_count = 0
    denied_count = 0
    overpaid_count = 0
    no_contract_count = 0
    billed_below_count = 0
    total_chargemaster_gap = 0.0
    denial_adj_codes = []

    for line in lines:
        contracted_rate = rates.get(line["cpt_code"])
        expected_payment = None
        variance = None
        flag = "NO_CONTRACT"
        chargemaster_gap = None

        if contracted_rate is not None:
            contracted_rate = float(contracted_rate)
            expected_payment = round(contracted_rate * line["units"], 2)
            variance = round(line["paid_amount"] - expected_payment, 2)

            if line["billed_amount"] < contracted_rate:
                chargemaster_gap = round((contracted_rate - line["billed_amount"]) * line["units"], 2)
                billed_below_count += 1
                total_chargemaster_gap += chargemaster_gap
                flag = "BILLED_BELOW"
            elif line["paid_amount"] == 0 and expected_payment > 0:
                flag = "DENIED"
                denied_count += 1
                denial_adj_codes.append(line.get("adjustments", ""))
            elif variance < -0.50:
                flag = "UNDERPAID"
                underpaid_count += 1
                total_underpayment += abs(variance)
            elif variance > 0.50:
                flag = "OVERPAID"
                overpaid_count += 1
            else:
                flag = "CORRECT"
                correct_count += 1

            total_contracted += expected_payment
        else:
            no_contract_count += 1

        total_paid += line["paid_amount"]

        # Medicare benchmark
        medicare_rate = None
        medicare_source = None
        if carrier and locality:
            rate_val, source, _, _ = lookup_rate(line["cpt_code"], "CPT", carrier, locality)
            if rate_val is not None:
                medicare_rate = rate_val
                medicare_source = source

        enriched_lines.append({
            "cpt_code": line["cpt_code"],
            "billed_amount": line["billed_amount"],
            "paid_amount": line["paid_amount"],
            "units": line["units"],
            "contracted_rate": contracted_rate,
            "expected_payment": expected_payment,
            "variance": variance,
            "flag": flag,
            "chargemaster_gap": chargemaster_gap,
            "adjustments": line.get("adjustments", ""),
            "claim_id": line.get("claim_id", ""),
            "medicare_rate": medicare_rate,
            "medicare_source": medicare_source,
        })

    lines_with_contract = correct_count + underpaid_count + denied_count + overpaid_count + billed_below_count
    adherent_count = correct_count + overpaid_count
    adherence_rate = round((adherent_count / lines_with_contract) * 100, 1) if lines_with_contract > 0 else 100.0

    clean_claim_rate = round(((correct_count + overpaid_count) / lines_with_contract) * 100, 1) if lines_with_contract > 0 else 100.0
    denial_rate = round((denied_count / lines_with_contract) * 100, 1) if lines_with_contract > 0 else 0.0
    preventable_codes = {"CO-16", "CO-97", "16", "97"}
    preventable_denial_count = 0
    for adj_str in denial_adj_codes:
        codes = [c.strip() for c in adj_str.split(",")]
        if any(c in preventable_codes for c in codes):
            preventable_denial_count += 1
    preventable_denial_rate = round((preventable_denial_count / denied_count) * 100, 1) if denied_count > 0 else 0.0

    summary = {
        "total_contracted": round(total_contracted, 2),
        "total_paid": round(total_paid, 2),
        "total_underpayment": round(total_underpayment, 2),
        "adherence_rate": adherence_rate,
        "line_count": len(enriched_lines),
        "correct_count": correct_count,
        "underpaid_count": underpaid_count,
        "denied_count": denied_count,
        "overpaid_count": overpaid_count,
        "no_contract_count": no_contract_count,
        "billed_below_count": billed_below_count,
        "total_chargemaster_gap": round(total_chargemaster_gap, 2),
    }

    scorecard = {
        "clean_claim_rate": clean_claim_rate,
        "denial_rate": denial_rate,
        "payer_adherence_rate": adherence_rate,
        "preventable_denial_rate": preventable_denial_rate,
        "narrative": None,
    }

    # Run denial intelligence for denied lines
    denial_intel = None
    denied_lines_data = [
        {"cpt_code": l["cpt_code"], "billed_amount": l["billed_amount"],
         "adjustment_codes": l["adjustments"], "claim_id": l.get("claim_id", "")}
        for l in enriched_lines if l["flag"] == "DENIED"
    ]
    if denied_lines_data:
        denial_input = json.dumps({
            "payer_name": payer_name,
            "denied_lines": denied_lines_data,
            "total_denied_count": len(denied_lines_data),
        })
        denial_intel = _call_claude(
            system_prompt=DENIAL_SYSTEM_PROMPT,
            user_content=denial_input,
            max_tokens=4096,
        )

    top_underpaid = sorted(
        [
            {"cpt_code": cpt, "total_underpayment": round(amt, 2)}
            for cpt, amt in _aggregate_underpayments(enriched_lines).items()
        ],
        key=lambda x: x["total_underpayment"],
        reverse=True,
    )[:10]

    # Save analysis to provider_analyses
    analysis_record = {
        "company_id": user_id,
        "payer_name": payer_name,
        "production_date": "",
        "total_billed": summary["total_contracted"],
        "total_paid": summary["total_paid"],
        "underpayment": summary["total_underpayment"],
        "adherence_rate": summary["adherence_rate"],
        "result_json": {
            "summary": summary,
            "scorecard": scorecard,
            "line_items": enriched_lines,
            "top_underpaid": top_underpaid,
            "denial_intel": denial_intel,
        },
    }

    analysis_id = None
    try:
        ins = sb.table("provider_analyses").insert(analysis_record).execute()
        if ins.data and len(ins.data) > 0:
            analysis_id = ins.data[0]["id"]
    except Exception as exc:
        print(f"[RunAnalysis] Failed to save analysis for {payer_name}: {exc}")

    return {
        "analysis_id": analysis_id,
        "summary": summary,
        "scorecard": scorecard,
        "line_items": enriched_lines,
        "denial_intel": denial_intel,
        "top_underpaid": top_underpaid,
    }
