from __future__ import annotations

"""
/api/health/analyze-text and /api/health/analyze-image endpoints.

Uses Claude to extract structured bill data from pasted text or
uploaded images. Both endpoints return the same AIParseResponse shape
used by ai_parse.py so the frontend can converge all input paths
into a single pipeline.
"""

import base64
import csv
import io
import json
import os
import re
import time
import uuid

from datetime import datetime
from zoneinfo import ZoneInfo

from typing import Optional, List

from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from pydantic import BaseModel

from utils.evidence_retrieval import retrieve_evidence

router = APIRouter()

# Anthropic client — lazy-initialized (same pattern as ai_parse.py)
_anthropic_client = None


def _get_client():
    global _anthropic_client
    if _anthropic_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="AI parsing is not configured on this server.",
            )
        try:
            import anthropic
            _anthropic_client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="AI parsing dependencies are not installed.",
            )
    return _anthropic_client


def _get_supabase():
    """Lazy-initialize Supabase client."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        return None
    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AnalyzeTextRequest(BaseModel):
    text: str
    sbc_data: Optional[dict] = None


class AnalyzeImageRequest(BaseModel):
    pages: List[str]  # base64-encoded images
    sbc_data: Optional[dict] = None


class DenialAnalyzeRequest(BaseModel):
    text: str


class AppealGenerateRequest(BaseModel):
    denial_analysis: dict
    patient_name: Optional[str] = None
    provider_name: Optional[str] = None
    claim_number: Optional[str] = None
    patient_address: Optional[str] = None  # PHI — server-only, never sent to any external API


class AnalyzeLineItem(BaseModel):
    cpt_code: Optional[str] = None
    revenue_code: Optional[str] = None
    description: str = ""
    quantity: int = 1
    billed_amount: float = 0.0
    modifier: Optional[str] = None
    modifiers: List[str] = []
    place_of_service: Optional[str] = None
    date_of_service: Optional[str] = None


class AnalyzeResponse(BaseModel):
    provider_name: Optional[str] = None
    service_date: Optional[str] = None
    insurance_name: Optional[str] = None
    network_status: Optional[str] = None  # "in_network", "out_of_network", or null
    claim_number: Optional[str] = None
    adjudication_date: Optional[str] = None
    parser_version: int = 2
    line_items: List[AnalyzeLineItem] = []
    total_billed: Optional[float] = None
    parsing_confidence: str = "high"


# Shared extraction prompt — used by analyze-text and analyze-image
SYSTEM_PROMPT = """You are a medical bill and Explanation of Benefits (EOB) data extraction specialist. Consumers upload EOBs from many different insurance companies — formats, layouts, and terminology vary significantly.

IMPORTANT — read the ENTIRE document first before extracting any fields. Understand the document's structure, layout, and terminology as a whole before attempting extraction. Different insurance companies use different labels, layouts, and terminology for the same information. Infer field locations flexibly — never return null just because a label does not match an expected term. If the information is present anywhere in the document, find it.

Return ONLY valid JSON matching this exact structure, with no other text, markdown, or explanation:
{
  "provider_name": "string or null",
  "service_date": "YYYY-MM-DD or null",
  "insurance_name": "string or null",
  "network_status": "in_network or out_of_network or null",
  "claim_number": "string or null",
  "adjudication_date": "YYYY-MM-DD or null",
  "parser_version": 2,
  "line_items": [
    {
      "cpt_code": "5-character code or null",
      "revenue_code": "4-digit code or null",
      "description": "procedure description",
      "quantity": number,
      "billed_amount": number,
      "modifier": "first modifier code as string, or null if none",
      "modifiers": ["array of all modifier codes on this line, empty [] if none"],
      "place_of_service": "2-digit code or null",
      "date_of_service": "YYYY-MM-DD for this specific line, or null"
    }
  ],
  "total_billed": number or null
}

Rules:
- Extract every line item. Use null for any field genuinely absent. Do not include subtotal or total rows as line items.
- network_status: look for terms like "in-network", "out-of-network", "participating", "non-participating", "PPO", "HMO", "preferred", "non-preferred" to determine if the provider was in or out of network. Use null if not determinable.
- IMPORTANT for service_date: Extract the DATE OF SERVICE, not the patient's date of birth. The service date is when the medical service was performed — look for labels like "Date of Service", "Service Date", "DOS", "Dates of Service", "Date Treated", or dates near procedure descriptions. Patient DOB (date of birth, born, DOB) is NOT the service date. If multiple service dates exist, use the most recent one.
- modifier: the first modifier code as a single string (null if none). modifiers: an array of ALL modifier codes on that line (e.g. ["25", "59"]). If no modifiers, use null for modifier and [] for modifiers. Modifiers often appear next to CPT codes separated by dashes, commas, or in adjacent columns.
- claim_number: may appear as "Claim #", "Claim Number", "ICN", "DCN", "Reference Number", "Confirmation Number", "Control Number", or other insurer-specific labels. Return null only if genuinely absent from the document.
- adjudication_date: the date the claim was processed or paid — may appear as "Date Processed", "Adjudication Date", "Payment Date", "Paid Date", "Decision Date", "Statement Date", or similar. This is NOT the date of service. Return null only if genuinely absent.
- date_of_service per line: the date treatment was performed for this specific line. May appear as "Date of Service", "Service Date", "Date Treated", "DOS", or dates adjacent to procedure descriptions. Return null only if genuinely absent or if only a single service date exists (already captured in the top-level service_date field).
- parser_version must always be 2."""

# Extended prompt when SBC data is provided
SBC_CONTEXT_ADDENDUM = """

IMPORTANT: The patient has provided their Summary of Benefits and Coverage (SBC) plan details. After extracting the bill data, also include a "plan_responsibility" field in your JSON with this structure:
{
  "plan_responsibility": {
    "estimated_patient_responsibility": number,
    "explanation": "Brief explanation of how the patient's plan design affects what they owe",
    "deductible_applies": true/false,
    "copay_items": [{"description": "string", "copay_amount": number}],
    "coinsurance_items": [{"description": "string", "coinsurance_pct": number, "estimated_amount": number}]
  }
}

Use these plan details to estimate patient responsibility:
"""


# ---------------------------------------------------------------------------
# POST /api/health/analyze-text
# ---------------------------------------------------------------------------

@router.post("/api/health/analyze-text", response_model=AnalyzeResponse)
def analyze_text(req: AnalyzeTextRequest):
    if not req.text or len(req.text.strip()) < 20:
        raise HTTPException(status_code=400, detail="Insufficient text provided.")

    client = _get_client()

    print(f"[health/analyze-text] Parsing {len(req.text)} chars of text")

    system = SYSTEM_PROMPT
    if req.sbc_data:
        system += SBC_CONTEXT_ADDENDUM + json.dumps(req.sbc_data, indent=2)

    content = [
        {
            "type": "text",
            "text": (
                "Extract all procedure line items from this medical bill text. "
                "Return only the JSON structure specified in the system prompt.\n\n"
                f"---\n{req.text}\n---"
            ),
        }
    ]

    response = _call_claude(client, content, system_prompt=system)
    return _parse_response(response, sbc_data=req.sbc_data)


# ---------------------------------------------------------------------------
# POST /api/health/analyze-image
# ---------------------------------------------------------------------------

@router.post("/api/health/analyze-image", response_model=AnalyzeResponse)
def analyze_image(req: AnalyzeImageRequest):
    if not req.pages:
        raise HTTPException(status_code=400, detail="No images provided.")

    client = _get_client()

    system = SYSTEM_PROMPT
    if req.sbc_data:
        system += SBC_CONTEXT_ADDENDUM + json.dumps(req.sbc_data, indent=2)

    # Build content blocks: each page as a separate image
    content = []
    for idx, page_b64 in enumerate(req.pages):
        b64_data = page_b64.strip()
        media_type = "image/jpeg"

        # Strip data URL prefix if present
        if b64_data.startswith("data:"):
            match = re.match(r"data:(image/\w+);base64,(.+)", b64_data, re.DOTALL)
            if match:
                media_type = match.group(1)
                b64_data = match.group(2).strip()
            else:
                b64_data = b64_data.split(",", 1)[-1].strip()

        # Detect media type from base64 header bytes
        if b64_data.startswith("/9j/"):
            media_type = "image/jpeg"
        elif b64_data.startswith("iVBOR"):
            media_type = "image/png"

        print(f"[health/analyze-image] Page {idx+1}: {len(b64_data)} chars, media={media_type}")

        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": b64_data,
            },
        })

    content.append({
        "type": "text",
        "text": (
            "Extract all procedure line items from this medical bill. "
            "Return only the JSON structure specified in the system prompt."
        ),
    })

    response = _call_claude(client, content, system_prompt=system)
    return _parse_response(response, sbc_data=req.sbc_data)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _call_claude(client, content, system_prompt=None):
    """Call Claude with exponential backoff on 529 (overloaded)."""
    backoff_delays = [2, 5, 10]
    response = None
    sys = system_prompt or SYSTEM_PROMPT
    for attempt in range(len(backoff_delays) + 1):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                temperature=0,
                system=sys,
                messages=[{"role": "user", "content": content}],
            )
            break
        except Exception as exc:
            err_str = str(exc)
            if "529" in err_str and attempt < len(backoff_delays):
                delay = backoff_delays[attempt]
                print(f"[health/analyze] Claude overloaded (529), retry {attempt+1}/{len(backoff_delays)} in {delay}s...")
                time.sleep(delay)
                continue
            print(f"[health/analyze] API error: {exc}")
            if "529" in err_str:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=503,
                    content={"error": "overloaded", "message": "AI service is temporarily busy. Please try again in a moment."},
                )
            raise HTTPException(
                status_code=502,
                detail="AI reading encountered an error. Please try again.",
            )

    return response


def _parse_response(response, sbc_data=None):
    """Parse Claude's response into an AnalyzeResponse."""
    # Handle JSONResponse passthrough (overloaded case)
    from fastapi.responses import JSONResponse
    if isinstance(response, JSONResponse):
        return response

    raw_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            raw_text += block.text

    # Strip markdown code fences
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```\s*$", "", raw_text)
    raw_text = raw_text.strip()

    print(f"[health/analyze] Raw response: {raw_text[:200]}")

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        print(f"[health/analyze] Invalid JSON: {raw_text[:500]}")
        raise HTTPException(
            status_code=502,
            detail="AI reading encountered an error. Please try again.",
        )

    # Clean amount fields
    if parsed.get("total_billed") is not None and not isinstance(parsed["total_billed"], (int, float)):
        val = str(parsed["total_billed"]).replace("$", "").replace(",", "").strip()
        try:
            parsed["total_billed"] = float(val)
        except (ValueError, TypeError):
            parsed["total_billed"] = None

    for li in parsed.get("line_items", []):
        if li.get("billed_amount") is not None and not isinstance(li["billed_amount"], (int, float)):
            val = str(li["billed_amount"]).replace("$", "").replace(",", "").strip()
            try:
                li["billed_amount"] = float(val)
            except (ValueError, TypeError):
                li["billed_amount"] = 0

    items = parsed.get("line_items", [])
    confidence = "high" if len(items) >= 3 else "medium" if len(items) >= 1 else "low"

    # Normalize network_status
    raw_network = parsed.get("network_status")
    network_status = None
    if raw_network:
        ns_lower = str(raw_network).lower().replace("-", "_").replace(" ", "_")
        if "out" in ns_lower:
            network_status = "out_of_network"
        elif "in" in ns_lower or "participating" in ns_lower:
            network_status = "in_network"

    return AnalyzeResponse(
        provider_name=parsed.get("provider_name"),
        service_date=parsed.get("service_date"),
        insurance_name=parsed.get("insurance_name"),
        network_status=network_status,
        claim_number=parsed.get("claim_number"),
        adjudication_date=parsed.get("adjudication_date"),
        parser_version=parsed.get("parser_version", 2),
        line_items=[
            AnalyzeLineItem(
                cpt_code=li.get("cpt_code"),
                revenue_code=li.get("revenue_code"),
                description=li.get("description", ""),
                quantity=li.get("quantity", 1) or 1,
                billed_amount=li.get("billed_amount", 0) or 0,
                modifier=li.get("modifier"),
                modifiers=li.get("modifiers") or [],
                place_of_service=li.get("place_of_service"),
                date_of_service=li.get("date_of_service"),
            )
            for li in items
        ],
        total_billed=parsed.get("total_billed"),
        parsing_confidence=confidence,
    )


# ---------------------------------------------------------------------------
# POST /api/health/analyze-sbc
# ---------------------------------------------------------------------------

SBC_SYSTEM_PROMPT = """You are a health insurance plan document analyst. Extract the key plan design elements from this Summary of Benefits and Coverage (SBC) document. Return ONLY valid JSON matching this exact structure, with no other text, markdown, or explanation:
{
  "plan_name": "string or null",
  "plan_year": "string or null (e.g. '2024', '2024-2025')",
  "deductible_individual": number or null,
  "deductible_family": number or null,
  "oop_max_individual": number or null,
  "oop_max_family": number or null,
  "primary_care_copay": number or null,
  "specialist_copay": number or null,
  "emergency_room_copay": number or null,
  "urgent_care_copay": number or null,
  "generic_drug_copay": number or null,
  "brand_drug_copay": number or null,
  "coinsurance_in_network": number or null (as percentage, e.g. 20 for 20%),
  "out_of_network_deductible": number or null,
  "out_of_network_coinsurance": number or null (as percentage),
  "referral_required": true or false or null
}

Extract exact dollar amounts and percentages. Use null for any field not found in the document. For copays, extract the dollar amount the patient pays. For coinsurance, extract the percentage the patient pays (not the plan pays)."""


@router.post("/api/health/analyze-sbc")
async def analyze_sbc(
    file: UploadFile = File(...),
    x_health_session: Optional[str] = Header(None),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    client = _get_client()

    # Read the PDF and convert to base64 for Claude's vision
    pdf_bytes = await file.read()
    if len(pdf_bytes) > 20 * 1024 * 1024:  # 20MB limit
        raise HTTPException(status_code=400, detail="File too large. Maximum 20MB.")

    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")

    print(f"[health/analyze-sbc] Processing SBC PDF: {file.filename} ({len(pdf_bytes)} bytes)")

    content = [
        {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": pdf_b64,
            },
        },
        {
            "type": "text",
            "text": (
                "Extract the key plan design elements from this Summary of Benefits and Coverage document. "
                "Return only the JSON structure specified in the system prompt."
            ),
        },
    ]

    backoff_delays = [2, 5, 10]
    response = None
    for attempt in range(len(backoff_delays) + 1):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                temperature=0,
                system=SBC_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": content}],
            )
            break
        except Exception as exc:
            err_str = str(exc)
            if "529" in err_str and attempt < len(backoff_delays):
                delay = backoff_delays[attempt]
                print(f"[health/analyze-sbc] Claude overloaded (529), retry {attempt+1}/{len(backoff_delays)} in {delay}s...")
                time.sleep(delay)
                continue
            print(f"[health/analyze-sbc] API error: {exc}")
            raise HTTPException(
                status_code=502,
                detail="AI analysis encountered an error. Please try again.",
            )

    raw_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            raw_text += block.text

    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```\s*$", "", raw_text)
    raw_text = raw_text.strip()

    print(f"[health/analyze-sbc] Raw response: {raw_text[:300]}")

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        print(f"[health/analyze-sbc] Invalid JSON: {raw_text[:500]}")
        raise HTTPException(status_code=502, detail="AI analysis encountered an error. Please try again.")

    # Clean numeric fields — strip $ and , if Claude returns strings
    numeric_fields = [
        "deductible_individual", "deductible_family",
        "oop_max_individual", "oop_max_family",
        "primary_care_copay", "specialist_copay",
        "emergency_room_copay", "urgent_care_copay",
        "generic_drug_copay", "brand_drug_copay",
        "coinsurance_in_network", "out_of_network_deductible",
        "out_of_network_coinsurance",
    ]
    for field in numeric_fields:
        val = parsed.get(field)
        if val is not None and not isinstance(val, (int, float)):
            cleaned = str(val).replace("$", "").replace(",", "").replace("%", "").strip()
            try:
                parsed[field] = float(cleaned)
            except (ValueError, TypeError):
                parsed[field] = None

    # Save to Supabase if session provided
    session_id = x_health_session
    if session_id:
        sb = _get_supabase()
        if sb:
            try:
                sb.table("health_sbc_uploads").insert({
                    "id": str(uuid.uuid4()),
                    "session_id": session_id,
                    "plan_name": parsed.get("plan_name"),
                    "plan_year": parsed.get("plan_year"),
                    "sbc_data": parsed,
                }).execute()
                print(f"[health/analyze-sbc] Saved SBC data for session {session_id}")
            except Exception as e:
                print(f"[health/analyze-sbc] Failed to save SBC: {e}")

    return parsed


# ---------------------------------------------------------------------------
# POST /api/health/analyze-denial
# ---------------------------------------------------------------------------

DENIAL_SYSTEM_PROMPT = """You are a medical insurance denial analyst helping everyday patients understand why their claim was denied. Write all plain-language fields as if explaining to someone who has never dealt with insurance before — no jargon, no acronyms without explanation, short sentences. Analyze this insurance denial letter or Explanation of Benefits (EOB) and extract the following as JSON only, no other text:
{
  "denial_reason_code": "the specific reason code if present (e.g. CO-97, PR-96), or null",
  "denial_reason_plain": "plain English explanation of why the claim was denied",
  "denial_type": "clinical | administrative | coverage | other",
  "denial_category": "EIU | medical_necessity | bundling | coding_modifier | non_covered | authorization | administrative | other",
  "pre_service": "true if this is a prior-authorization / pre-service determination made BEFORE the service was rendered, false if it is a post-service claim denial",
  "specific_criterion": "the exact criterion, policy, or rule the carrier cited to deny",
  "weakness": "any apparent weakness in the denial reasoning, or null if denial appears straightforward",
  "carc_rarc_code": "the standardized CARC/RARC adjustment code (e.g. CO-97, PR-96) if present, or null",
  "payer_guideline_id": "the payer's internal medical-policy or guideline identifier (e.g. MOL.CU.117), distinct from a CARC/RARC code, or null",
  "cpt_codes": ["array of CPT/HCPCS procedure codes at issue, deduplicated (e.g. ['0340U']), or []"],
  "icd_codes": ["array of ICD-10 diagnosis codes if present, or []"],
  "procedure_terms": ["plain-language names of the procedure/test/service (e.g. ['Signatera','ctDNA MRD']), or []"],
  "billed_amount": "the dollar amount at issue as a number, or null (null for pre-service determinations with no billed amount)",
  "supporting_documentation": ["list of specific documents that would strengthen an appeal"],
  "appeal_deadline_hint": "any appeal deadline mentioned, in plain language, or null",
  "deadline_days_expedited": "number of days for an expedited or panel appeal if stated, or null",
  "deadline_days_standard": "number of days for a standard appeal if stated, or null",
  "appeal_submission": {
    "address": "the mailing address to send the appeal to, if stated, or null",
    "alt_address": "any alternate or secondary appeal address, or null",
    "fax": "appeal fax number if stated, or null",
    "phone": "appeal phone number if stated, or null"
  },
  "peer_to_peer_contact": "phone number for a provider peer-to-peer or physician-reviewer discussion if stated, or null",
  "appeal_rights": ["array of appeal rights or external-review options mentioned (e.g. ['ERISA §502(a)','ACA external review','Florida Dept. of Financial Services']), or []"],
  "reviewer_entity": "the entity that made or reviewed the decision (e.g. eviCore, the payer's medical director), or null",
  "confidence": "high | medium | low",
  "patient_name": "full patient name if found in the document, or null",
  "member_id": "the member, subscriber, or customer ID if found, or null",
  "patient_address": "the patient's mailing address if found in the document, or null",
  "state": "the patient's two-letter state if found or derivable from the address, or null",
  "provider_name": "ordering provider or physician name if found, or null",
  "facility_name": "facility or lab name if found (e.g. the testing lab), or null",
  "claim_number": "claim or reference number if found, or null",
  "date_of_service": "date of service if found (any format), or null",
  "payer_name": "insurance company name if found, or null"
}

Deduplicate cpt_codes. Distinguish payer_guideline_id (the payer's internal policy ID) from carc_rarc_code (a standardized adjustment code). Extract the appeal submission address, fax, phone, and deadlines directly from the denial document when they appear. Return null/[] for anything genuinely absent — never guess."""


@router.post("/api/health/analyze-denial")
def analyze_denial(req: DenialAnalyzeRequest):
    if not req.text or len(req.text.strip()) < 20:
        raise HTTPException(status_code=400, detail="Insufficient text provided.")

    client = _get_client()

    print(f"[health/analyze-denial] Parsing {len(req.text)} chars of denial text")

    content = [
        {
            "type": "text",
            "text": (
                "Analyze this insurance denial letter or EOB. "
                "Return only the JSON structure specified in the system prompt.\n\n"
                f"---\n{req.text}\n---"
            ),
        }
    ]

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        temperature=0,
        system=DENIAL_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )

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
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        print(f"[health/analyze-denial] Invalid JSON: {raw_text[:500]}")
        raise HTTPException(status_code=502, detail="AI analysis encountered an error. Please try again.")

    return parsed


# ---------------------------------------------------------------------------
# POST /api/health/generate-appeal
# ---------------------------------------------------------------------------

APPEAL_SYSTEM_PROMPT = """You are a medical billing advocate writing a formal insurance appeal letter on behalf of a patient. Using the denial analysis provided, write a professional, assertive appeal letter that:
- Opens with the specific claim/denial reference
- States clearly that the patient is appealing the denial
- Directly addresses the specific criterion the carrier cited
- If a weakness was identified in the denial reasoning, leads with that as the primary argument
- Lists the supporting documentation the patient will provide
- Closes with a clear request for reconsideration and a deadline expectation
- Uses professional but plain language, not legal jargon
- Is formatted as a real letter (date, addresses, subject line, body, closing)
- For the letterhead date, output the exact literal token __LETTER_DATE__ (our system substitutes the correct date). Use __LETTER_DATE__ exactly once, only as the letterhead date. Never write any other calendar date to mean "today"; dates that refer to the denial (e.g. the denial date) should be written normally.
- If clinical evidence from Parity Signal is provided, incorporate the key evidence points as specific citations supporting the appeal. This strengthens the letter with scientific backing.

Punctuation rule: Do not use em-dashes (—) or en-dashes (–) anywhere in the letter. Write in complete, direct sentences. Where you would use a dash, use a period, comma, colon, or parentheses as appropriate.

Writing style:
- Write the way an experienced human medical-billing advocate writes: direct, specific, and confident. Short-to-medium sentences. One idea per sentence.
- Do not open sentences with throat-clearing like "We respectfully request", "We draw the reviewer's attention to", or "It is important to note". State the point directly.
- Avoid summary constructions that cram three or more items into a single sentence set off by dashes or colons (for example, "Taken together, this body of evidence, A, B, C, and D, demonstrates..."). If you must summarize, use a short plain sentence.
- Prefer concrete statements over abstract ones. Instead of "does not reflect the current state of the evidence", say specifically what the evidence shows.
- Keep all clinical and regulatory terminology. The reader is a physician reviewer; precision is persuasive. Do not simplify medical or legal terms.
- Maintain a professional, respectful, firm tone. Confident, not aggressive. Never overstate what the evidence proves; stay within each item's stated indication.

Return only the letter text, no explanation or commentary."""


# Placeholder-label -> denial_analysis value resolver for _validate_letter.
def _resolve_placeholder(label: str, da: dict):
    """Return a substitution value for a bracketed placeholder label, or None if
    we have no known value for it. Case-insensitive on the label text."""
    key = label.strip().lower().rstrip(":").strip()
    sub = da.get("appeal_submission") or {}
    mapping = {
        "patient name": da.get("patient_name"),
        "patient": da.get("patient_name"),
        "name": da.get("patient_name"),
        "member id": da.get("member_id"),
        "member id #": da.get("member_id"),
        "member #": da.get("member_id"),
        "claim number": da.get("claim_number"),
        "claim #": da.get("claim_number"),
        "claim": da.get("claim_number"),
        "address": da.get("patient_address"),
        "patient address": da.get("patient_address"),
        "state": da.get("state"),
        "provider name": da.get("provider_name"),
        "ordering provider": da.get("provider_name"),
        "payer name": da.get("payer_name"),
        "date of service": da.get("date_of_service"),
        "denial reason code": da.get("denial_reason_code") or da.get("carc_rarc_code") or da.get("payer_guideline_id"),
        "reviewer": da.get("reviewer_entity"),
        "cigna/evicore mailing address": sub.get("address"),
        "payer address": sub.get("address"),
        "mailing address": sub.get("address"),
        "appeal address": sub.get("address"),
    }
    # Note: bare [Phone]/[Fax]/[Email] placeholders are patient-contact fields we do not
    # have — intentionally unmapped so their lines are removed rather than back-filled with
    # the payer's appeal phone/fax (which live in the "Where & How to Appeal" UI card).
    return mapping.get(key)


# Deterministic letterhead-date token the model is asked to emit; replaced in _validate_letter.
_LETTER_DATE_TOKEN = "__LETTER_DATE__"

# Bracket inner-text tokens that MUST be filled with a named signature (never line-removed).
_SIGNATURE_TOKENS = (
    "signature", "advocate", "provider name", "sender name",
    "your name", "name and title", "representative",
)

# Visible marker used when a must-have (signature) placeholder cannot be filled — surfaced
# in the letter instead of a silent removal or a mailable generic. No brackets, so it is not
# mistaken for an unresolved placeholder. (Supersedes the earlier "the member" fallback.)
_ACTION_REQUIRED_SIGNATURE = "ACTION REQUIRED — add the member's name and title before submitting"

# Placeholder keys whose substituted value is PHI — redacted from validation_log (CO-6).
_PHI_PLACEHOLDER_KEYS = {
    "patient name", "patient", "name",
    "member id", "member id #", "member #",
    "claim number", "claim #", "claim",
    "address", "patient address",
}

# A line that is *solely* a date: month-name form or MM/DD/YYYY, optional surrounding space.
_DATE_ONLY_RE = re.compile(
    r"^\s*(?:"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},?\s+\d{4}"
    r"|\d{1,2}/\d{1,2}/\d{4}"
    r")\s*$",
    re.IGNORECASE,
)


def _today_local() -> str:
    """Today's date in America/Chicago, formatted like 'July 1, 2026' (no leading zero)."""
    now = datetime.now(ZoneInfo("America/Chicago"))
    return f"{now.strftime('%B')} {now.day}, {now.year}"


def _is_signature_placeholder(key: str) -> bool:
    return any(tok in key for tok in _SIGNATURE_TOKENS)


def _validate_letter(letter_text: str, denial_analysis: dict) -> dict:
    """Deterministically clean a generated appeal letter. Pure string manipulation — no
    Claude call.

    - Letterhead date: replace the literal __LETTER_DATE__ token with today's LOCAL date
      (America/Chicago). If the model ignored the token, fall back to stamping a line that
      is *solely* a date within the first 8 non-empty lines (mid-sentence dates such as a
      denial-date reference are left untouched).
    - Named signature: any bracket matching signature/advocate/provider name/etc. is FILLED
      with "Submitted on behalf of {patient_name}" (or "the member" if unknown) — never
      removed or left blank.
    - Other [Placeholder]s: substitute a known value from denial_analysis, or drop the whole
      line so no empty bracket is emitted.
    - validation_log never contains the VALUE of a PHI field (patient_name, patient_address,
      member_id, claim_number); those are logged as "[REDACTED]".

    Returns {"letter_text": cleaned, "validation_log": [{field, action, value}]}.
    """
    today = _today_local()
    pn = denial_analysis.get("patient_name")
    # Named signature when we know the patient (value is PHI); otherwise a visible
    # ACTION-REQUIRED marker for this must-have field (never a silent removal).
    signature_value = f"Submitted on behalf of {pn}" if pn else _ACTION_REQUIRED_SIGNATURE
    signature_is_phi = bool(pn)
    placeholder_re = re.compile(r"\[([^\]]+)\]")
    log: List[dict] = []

    # -- CO-1: deterministic letterhead date via the __LETTER_DATE__ token --
    token_present = _LETTER_DATE_TOKEN in letter_text
    if token_present:
        letter_text = letter_text.replace(_LETTER_DATE_TOKEN, today)
        log.append({"field": "letter_date", "action": "stamped", "value": today})

    out_lines: List[str] = []
    for line in letter_text.split("\n"):
        labels = placeholder_re.findall(line)
        if not labels:
            out_lines.append(line)
            continue

        new_line = line
        drop_line = False
        for label in labels:
            token = "[" + label + "]"
            key = label.strip().lower()
            if re.fullmatch(r"E\d+", label.strip()):
                # Inline evidence citation ([E1], [E11], …) — a legitimate PH-4a
                # citation marker, NOT an unfilled placeholder. Leave it intact;
                # never substitute or drop the line for it.
                continue
            if key == "date" or key.startswith("date:"):
                # Letterhead date only ("[Date]" / "[Date: June 23, 2026]"). Deliberately does
                # NOT match "[Date of Service]" etc., which route to the resolver (real value
                # or line removal) — never overwritten with today.
                new_line = new_line.replace(token, today)
                log.append({"field": token, "action": "date_substituted", "value": today})
            elif _is_signature_placeholder(key):
                # Must-have signature — always filled, never removed. With a known patient the
                # value embeds patient_name (PHI) so it is redacted from the log (CO-6); without
                # one, it becomes a visible ACTION-REQUIRED marker (safe to log, not PHI).
                new_line = new_line.replace(token, signature_value)
                if signature_is_phi:
                    log.append({"field": token, "action": "signature_substituted", "value": "[REDACTED]"})
                else:
                    log.append({"field": token, "action": "action_required", "value": signature_value})
            else:
                val = _resolve_placeholder(label, denial_analysis)
                if val:
                    new_line = new_line.replace(token, str(val))
                    is_phi = key.rstrip(":").strip() in _PHI_PLACEHOLDER_KEYS
                    log.append({
                        "field": token,
                        "action": "substituted",
                        "value": "[REDACTED]" if is_phi else str(val),
                    })
                else:
                    drop_line = True
                    log.append({"field": token, "action": "line_removed", "value": None})

        if drop_line:
            continue  # unresolved placeholder -> remove the whole line (never emit empty brackets)
        out_lines.append(new_line)

    cleaned = "\n".join(out_lines)

    # -- CO-1 fallback: model ignored the token. Stamp a solely-date line within the first
    # 8 non-empty lines; never touch mid-sentence date references (e.g. the denial date). --
    if not token_present:
        result_lines = cleaned.split("\n")
        nonempty_seen = 0
        for i, line in enumerate(result_lines):
            if not line.strip():
                continue
            nonempty_seen += 1
            if nonempty_seen > 8:
                break
            if _DATE_ONLY_RE.match(line):
                result_lines[i] = today
                log.append({"field": "letter_date", "action": "stamped", "value": today})
                cleaned = "\n".join(result_lines)
                break

    return {"letter_text": cleaned, "validation_log": log}


def _apply_pregen_validators(da: dict, claim_number: Optional[str] = None) -> dict:
    """PH-1-B pre-generation data-integrity guards. Mutates and returns ``da``.

    Pure (no network / no model call) so it is unit-testable:
      (1) claim_number must exist and must not equal the denial or guideline code — else
          substitute "{member_id} / {YYYY-MM-DD}" and log a warning;
      (2) cpt_codes deduplicated;
      (3) state derived from patient_address when missing.
    """
    claim_number = claim_number or da.get("claim_number")
    denial_code = da.get("denial_reason_code") or da.get("carc_rarc_code")
    guideline_id = da.get("payer_guideline_id")
    if (not claim_number) or claim_number == denial_code or claim_number == guideline_id:
        member_id = da.get("member_id")
        fallback_ref = f"{member_id or 'UNKNOWN'} / {datetime.now(ZoneInfo('America/Chicago')).strftime('%Y-%m-%d')}"
        print(
            f"[health/generate-appeal] WARNING: claim_number missing or equals "
            f"denial/guideline code ({claim_number!r}); substituting reference {fallback_ref!r}"
        )
        claim_number = fallback_ref
    da["claim_number"] = claim_number

    cpt_codes = da.get("cpt_codes") or []
    if isinstance(cpt_codes, str):
        cpt_codes = [cpt_codes]
    da["cpt_codes"] = list(set(cpt_codes))

    if not da.get("state") and da.get("patient_address"):
        m = re.search(r"\b([A-Z]{2})\s+\d{5}(?:-\d{4})?\b", da["patient_address"])
        if m:
            da["state"] = m.group(1)

    return da


# ---------------------------------------------------------------------------
# PH-4a: evidence-into-letter integration
# ---------------------------------------------------------------------------

# Appended to APPEAL_SYSTEM_PROMPT only — augments PH-1 behavior, never replaces it.
APPEAL_EVIDENCE_INSTRUCTIONS = """

--- SUPPORTING EVIDENCE (verified) ---
You are given a list of verified evidence items, each with a key like [E1]. When you refer to supporting evidence, refer to it ONLY by its key in square brackets, e.g. [E2].
You MUST NOT write any of the following yourself: a PubMed ID, an FDA PMA number, a DOI, a journal name, an author name, a study title, a direct quotation, or any specific statistic/percentage/number-of-patients that is not already stated in the provided evidence summaries. If you want to cite support, use its [E#] key and let the reference list carry the details.
State each item's support only within its stated indication. Do NOT generalize an FDA approval or coverage policy beyond the specific indication given. Do not imply broader regulatory status than the evidence states.
For any item that is a clinical practice guideline, refer to its existence and general conclusion only; never reproduce or paraphrase its detailed recommendations.
Tone: confident but precise. Make the strongest case the evidence genuinely supports, but never overstate it. An unimpeachable letter beats an overreaching one.
If the evidence does not match the patient's specific diagnosis (e.g. no diagnosis code was provided), do NOT claim it does. Argue the general validity of the test, and do not fabricate a diagnosis-specific link.
A "References" section listing these items will be appended to your letter automatically — do NOT write your own References/Citations section or expand any [E#] into a full citation."""


def _format_reference(item: dict) -> str:
    """One-line reference for an evidence item, built ONLY from verified stored
    fields. This is the sole place bibliographic detail may originate, so it is
    trusted. Guideline items are rendered reference-only (no recommendation text,
    which is never stored anyway)."""
    def _clean(s):
        # Strip trailing periods/whitespace so joining with ". " never doubles them.
        return (str(s or "")).strip().rstrip(".").strip()

    item = item or {}
    source = item.get("source")
    uid = item.get("source_uid") or ""
    title = _clean(item.get("title"))
    url = (item.get("url") or "").strip()
    md = item.get("metadata") or {}

    if source == "pubmed":
        # Rebuild from stored fields (no messy stored citation): authors, title,
        # journal, year, PMID. No "PubMed" prefix (PMID already means PubMed ID)
        # and no study_type label — the "guideline" tag never leaks into the line.
        authors = [a for a in (md.get("authors") or []) if a]
        lead = (f"{authors[0]} et al" if len(authors) > 1 else (authors[0] if authors else ""))
        journal = _clean(md.get("journal"))
        year = item.get("pub_year")
        segments = [s for s in [lead, title, journal, (str(year) if year else "")] if s]
        body = ". ".join(segments)
        tail = f"PMID {uid}." if uid else ""
        return " ".join(p for p in [f"{body}." if body else "", tail, url] if p).strip()

    if source == "fda":
        indication = _clean(md.get("indication"))
        therapy = md.get("indication_therapy")
        if indication:
            s = f"FDA-approved companion diagnostic (PMA {uid}) for {indication}"
            if therapy:
                s += f" (use with {therapy})"
            return " ".join(p for p in [s + ".", url] if p).strip()
        # No specific indication stored: fall back to the stored summary (never a
        # bare "FDA-approved").
        return " ".join(p for p in [_clean(item.get("summary") or title) + ".", url] if p).strip()

    if source in ("cms_moldx", "cms_ncd_lcd"):
        dtype = md.get("document_type") or "coverage"
        return " ".join(p for p in [f"CMS {dtype} {uid}: {title}.", url] if p).strip()

    return " ".join(p for p in [title, url] if p).strip()


def _format_reference_plain(item: dict) -> str:
    """MODEL-FACING evidence line: plain-language description + source type +
    year + (for FDA/CMS) the specific stored indication/scope. Deliberately
    contains NO identifier the model could copy into the prose — no PMID, no FDA
    PMA number, no DOI, no URL, and no CMS document id. The full-identifier
    reference lives only in the code-built References section (_format_reference),
    appended AFTER generation. Removes the model's temptation to emit identifiers;
    the anti-fabrication guard still detects any that slip through."""
    item = item or {}
    source = item.get("source")
    title = (str(item.get("title") or "")).strip().rstrip(".").strip()
    year = item.get("pub_year")
    md = item.get("metadata") or {}
    ystr = f" ({year})" if year else ""

    if source == "pubmed":
        stype = "Professional guideline" if item.get("study_type") == "guideline" else "Peer-reviewed study"
        return f"{stype}: {title}{ystr}."

    if source == "fda":
        indication = (str(md.get("indication") or "")).strip().rstrip(".").strip()
        therapy = md.get("indication_therapy")
        if indication:
            desc = f"FDA-approved companion diagnostic for {indication}"
            if therapy:
                desc += f" (used with {therapy})"
        else:
            desc = "FDA-authorized companion diagnostic"   # identifier-free fallback
        return f"FDA approval: {desc}{ystr}."

    if source in ("cms_moldx", "cms_ncd_lcd"):
        return f"Medicare coverage policy: {title}{ystr}."

    return f"{title}{ystr}."


def _build_evidence_block(pack: dict) -> dict:
    """Deterministically assign stable keys E1..En (pubmed, then cms, then fda;
    pack order within each) and render two views:
      - references_block: full, identifier-bearing, appended to the letter (reader-facing);
      - model_block:      identifier-free, fed to the model to write from.

    Returns {"references_block", "model_block", "keys": {"E1": item, ...}, "gaps": [...]}.
    """
    pack = pack or {}
    keys: dict = {}
    ref_lines: List[str] = []
    model_lines: List[str] = []
    n = 0
    for channel in ("pubmed", "cms", "fda"):
        for item in (pack.get(channel) or []):
            n += 1
            k = f"E{n}"
            keys[k] = item
            ref_lines.append(f"[{k}] {_format_reference(item)}")
            model_lines.append(f"[{k}] {_format_reference_plain(item)}")
    return {
        "references_block": "\n".join(ref_lines),
        "model_block": "\n".join(model_lines),
        "keys": keys,
        "gaps": pack.get("gaps") or [],
    }


# Patterns that must never appear in the letter BODY (they belong only in the
# code-built References section). Presence in the prose implies the model
# fabricated a citation detail -> HARD FAIL.
_FAB_BARE_PMID_RE = re.compile(r"(?<!\d)\d{7,8}(?!\d)")
_FAB_PMA_RE = re.compile(r"\bP\d{6}\b")
_FAB_DOI_RE = re.compile(r"\b10\.\d{4,}/\S+")
_FAB_ETAL_RE = re.compile(r"\bet al\.", re.IGNORECASE)
_FAB_JOURNAL_CITE_RE = re.compile(r"\b\d{4};\s?\d+(?:\(\d+\))?:\s?\d+")  # e.g. 2023;41(4):678
# Soft-flag: a percentage or "N patients"-style statistic (hardest to auto-verify).
_STAT_RE = re.compile(r"\d+(?:\.\d+)?\s?%|\b\d+\s+patients\b", re.IGNORECASE)
_USED_KEY_RE = re.compile(r"\[(E\d+)\]")


def _validate_evidence_claims(letter_text: str, keys: dict) -> dict:
    """Deterministic anti-fabrication gate, run on the letter BODY (before the
    code-built References section is appended). No model call, no PHI logged.

    Returns {"citations_ok", "hard_failures", "review_flags", "used_keys"}.
    """
    keys = keys or {}
    used_keys = sorted(set(_USED_KEY_RE.findall(letter_text or "")), key=lambda k: int(k[1:]))
    hard: List[str] = []

    # 5.1 — every used key must exist.
    for k in used_keys:
        if k not in keys:
            hard.append(f"unknown evidence key {k} used in letter (only {sorted(keys)} exist)")

    # 5.2 — citation-detail patterns that should be impossible in the prose.
    if _FAB_BARE_PMID_RE.search(letter_text or ""):
        hard.append("possible fabricated PubMed ID (bare 7-8 digit number) in letter body")
    if _FAB_PMA_RE.search(letter_text or ""):
        hard.append("possible fabricated FDA PMA number (P######) in letter body")
    if _FAB_DOI_RE.search(letter_text or ""):
        hard.append("possible fabricated DOI in letter body")
    if _FAB_ETAL_RE.search(letter_text or ""):
        hard.append('"et al." citation-style text in letter body')
    if _FAB_JOURNAL_CITE_RE.search(letter_text or ""):
        hard.append("journal-style citation (year;vol:page) in letter body")

    # 5.3 — soft flags for reviewer (NOT failures): specific figures.
    review_flags: List[dict] = []
    for m in _STAT_RE.finditer(letter_text or ""):
        figure = m.group(0).strip()
        # Capture the surrounding sentence for the reviewer.
        start = (letter_text.rfind(".", 0, m.start()) + 1)
        end = letter_text.find(".", m.end())
        end = len(letter_text) if end == -1 else end + 1
        sentence = " ".join(letter_text[start:end].split())
        review_flags.append({"figure": figure, "sentence": sentence})

    return {
        "citations_ok": not hard,
        "hard_failures": hard,
        "review_flags": review_flags,
        "used_keys": used_keys,
    }


def _build_reviewer_checklist(evidence: dict, evidence_validation: dict,
                              extra_notes: Optional[List[str]] = None) -> dict:
    """Structured checklist the human must confirm before sending. Data only —
    the UI is PH-4b. Status is ALWAYS draft; a letter is never auto-send-ready."""
    keys = (evidence or {}).get("keys") or {}
    items: List[dict] = []

    # Cited items -> confirm-indication prompt.
    for k in (evidence_validation or {}).get("used_keys", []):
        it = keys.get(k)
        if not it:
            continue
        md = it.get("metadata") or {}
        items.append({
            "type": "confirm_indication",
            "key": k,
            "reference": _format_reference(it),
            "stated_indication": md.get("indication") or it.get("summary"),
            "prompt": "Confirm this evidence's stated indication matches the patient's diagnosis before relying on it.",
        })

    # Soft-flagged statistics -> verify prompt.
    for flag in (evidence_validation or {}).get("review_flags", []):
        items.append({
            "type": "verify_statistic",
            "figure": flag.get("figure"),
            "sentence": flag.get("sentence"),
            "prompt": "Verify this figure against the cited source before sending.",
        })

    # Gaps -> actions.
    for gap in (evidence or {}).get("gaps") or []:
        if "ICD" in gap:
            action = ("No diagnosis (ICD) code was provided — supply it and regenerate to "
                      "retrieve diagnosis-specific evidence and strengthen this appeal.")
        else:
            action = gap
        items.append({"type": "gap", "note": gap, "action": action})

    for note in (extra_notes or []):
        items.append({"type": "note", "note": note})

    return {
        "status": "draft — human review required before sending",
        "items": items,
    }


_ORDERED_ITEM_RE = re.compile(r"^(\s*)(\d+)\.(\s)")


def _renumber_ordered_lists(text: str) -> str:
    """Renumber every maximal contiguous run of ordered-list lines ('N. ...') to
    be sequential (1, 2, 3, …) with no gaps, preserving indentation and the text
    after the number. Mechanical only — the wording of each item is untouched.

    Gaps arise when earlier processing drops some list lines; this guarantees the
    surviving items are always numbered contiguously, regardless of which remain.
    """
    lines = (text or "").split("\n")
    out: List[str] = []
    counter = 0
    for line in lines:
        m = _ORDERED_ITEM_RE.match(line)
        if m:
            counter += 1
            rest = line[m.end():]
            out.append(f"{m.group(1)}{counter}.{m.group(3)}{rest}")
        else:
            counter = 0  # blank or non-list line ends the current run
            out.append(line)
    return "\n".join(out)


def _map_citation_numbers(text: str) -> str:
    """Presentation-only: map internal [E#] keys to reader-facing [#] numbers so
    the letter shows ordinary numbered citations. Runs AFTER the anti-fabrication
    guard (which validates the E-keys); E{i} -> {i}, so an inline [3] and its
    reference [3] always carry the same number."""
    return re.sub(r"\[E(\d+)\]", r"[\1]", text or "")


# Standalone em/en dashes only (surrounding spaces optional, but NOT newlines so
# line structure is preserved). Hyphen-minus (-) in "muscle-invasive" etc. is a
# different character and is never matched.
_DASH_RE = re.compile(r"[ \t]*[—–][ \t]*")
_URL_RE = re.compile(r"https?://\S+")


def _normalize_dashes(text: str) -> str:
    """Deterministically remove em-dashes (—) and en-dashes (–) from the letter
    BODY (run before the References section is appended, so reference URLs are
    never touched). Belt-and-suspenders on top of the prompt rule.

    Replacement: a standalone dash becomes ". " when it separates independent
    clauses (the next word is capitalized), else ", " (mid-sentence aside).
    Hyphens in hyphenated words are the hyphen-minus character and are left
    untouched; URLs are protected from any change.
    """
    if not text:
        return text
    # Protect URLs so no dash inside one is ever altered.
    urls: List[str] = []

    def _stash(m):
        urls.append(m.group(0))
        return f"\x00URL{len(urls) - 1}\x00"

    protected = _URL_RE.sub(_stash, text)

    def _repl(m):
        after = m.string[m.end():].lstrip()
        return ". " if after[:1].isupper() else ", "

    result = _DASH_RE.sub(_repl, protected)
    for i, u in enumerate(urls):
        result = result.replace(f"\x00URL{i}\x00", u)
    return result


@router.post("/api/health/generate-appeal")
def generate_appeal(req: AppealGenerateRequest):
    client = _get_client()

    # denial_analysis is mutated in place by the pre-generation validators below.
    da = req.denial_analysis or {}

    # Merge user-supplied (editable) fields into the analysis before validating.
    # PHI — server-only; these values are never sent to any external API.
    if req.patient_name:
        da["patient_name"] = req.patient_name
    if req.provider_name:
        da["provider_name"] = req.provider_name
    if req.patient_address:
        da["patient_address"] = req.patient_address

    # -- PH-1-B: pre-generation data-integrity validators (extracted for unit testing) --
    _apply_pregen_validators(da, req.claim_number)
    cpt_codes = da.get("cpt_codes") or []

    # -- PH-4a: retrieve verified external evidence. retrieve_evidence receives the
    # full da ONLY so its internal PHI guard can assert no PHI reaches any wire; it
    # builds queries strictly from procedure_terms/cpt_codes. Honest degradation:
    # any failure -> empty pack, letter generated without citations, never a crash. --
    try:
        pack = retrieve_evidence(da)
    except Exception as e:
        print(f"[health/generate-appeal] retrieve_evidence failed; proceeding without evidence: {e}")
        pack = {"pubmed": [], "cms": [], "fda": [], "gaps": []}
    evidence = _build_evidence_block(pack)

    context_parts = [f"Denial analysis:\n{json.dumps(da, indent=2)}"]

    # -- PH-1-D: Signal playbook enrichment (now reachable — cpt_codes is populated) --
    try:
        sb = _get_supabase()
        if sb:
            playbook_code = (
                da.get("carc_rarc_code")
                or da.get("denial_reason_code")
                or da.get("payer_guideline_id")
                or ""
            )
            if playbook_code and cpt_codes:
                playbook_res = (
                    sb.table("signal_denial_playbook")
                    .select("*")
                    .eq("denial_code", playbook_code)
                    .in_("cpt_code", cpt_codes)
                    .limit(3)
                    .execute()
                )
                if playbook_res.data:
                    pb = playbook_res.data[0]
                    signal_context = "\n\nClinical Evidence from Parity Signal:\n"
                    signal_context += f"Appeal strength: {pb['appeal_strength']}\n"
                    if pb.get("payer_analytical_path"):
                        signal_context += f"Payer reasoning: {pb['payer_analytical_path']}\n"
                    if pb.get("challenging_evidence_summary"):
                        signal_context += f"Challenging evidence: {pb['challenging_evidence_summary']}\n"
                    if pb.get("recommended_claims"):
                        claims = pb["recommended_claims"]
                        if isinstance(claims, str):
                            claims = json.loads(claims)
                        if claims:
                            signal_context += "Key evidence points:\n"
                            for claim in claims[:3]:
                                signal_context += f"- {claim.get('claim_text', '')}\n"
                    context_parts.append(signal_context)
                    print(
                        f"[health/generate-appeal] Signal playbook hit "
                        f"(denial_code={playbook_code}, cpt_codes={cpt_codes})"
                    )
                else:
                    print(
                        f"[health/generate-appeal] no playbook entry found "
                        f"(denial_code={playbook_code}, cpt_codes={cpt_codes})"
                    )
            else:
                print(
                    f"[health/generate-appeal] Signal playbook lookup skipped "
                    f"(denial_code={playbook_code!r}, cpt_codes={cpt_codes})"
                )
        else:
            print("[health/generate-appeal] Supabase unavailable; skipping Signal playbook lookup")
    except Exception as e:
        print(f"[warn] Health Signal playbook lookup failed: {e}")

    # -- PH-4a.3: feed the model the IDENTIFIER-FREE evidence view (no PMID/PMA/
    # DOI/URL to copy). Full identifiers live only in the code-built References
    # section appended after generation. Switch on the citation instructions only
    # when there is evidence to cite. --
    system_prompt = APPEAL_SYSTEM_PROMPT
    evidence_note = None
    if evidence["model_block"]:
        context_parts.append(
            "Verified evidence you may cite (refer to each ONLY by its [E#] key; "
            "do NOT write the bibliographic details yourself):\n"
            + evidence["model_block"]
        )
        system_prompt = APPEAL_SYSTEM_PROMPT + APPEAL_EVIDENCE_INSTRUCTIONS
    else:
        evidence_note = "No external evidence was retrieved; letter generated without citations."

    content = [{"type": "text", "text": "\n\n".join(context_parts)}]

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        temperature=0.3,
        system=system_prompt,
        messages=[{"role": "user", "content": content}],
    )

    raw_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            raw_text += block.text

    # -- PH-1-C: deterministic post-generation placeholder validation (unchanged) --
    validated = _validate_letter(raw_text.strip(), da)
    if validated["validation_log"]:
        print(f"[health/generate-appeal] validation_log: {json.dumps(validated['validation_log'])}")

    # -- PH-4a.1: mechanical cleanup. [E#] citations now survive _validate_letter;
    # renumber any ordered lists so surviving items are always sequential. --
    body = _renumber_ordered_lists(validated["letter_text"])

    # -- PH-4a.2: voice pass. Deterministically strip em/en dashes from the body
    # (runs before the References section is appended, so reference URLs are
    # untouched). Backstop to the prompt's no-dash rule. --
    body = _normalize_dashes(body)

    # -- PH-4a: anti-fabrication guard on the letter BODY (with [E#] keys intact,
    # before reader-facing numbering and before the References section). --
    evidence_validation = _validate_evidence_claims(body, evidence["keys"])
    if not evidence_validation["citations_ok"]:
        # Log the reason WITHOUT any PHI (hard_failures carry no PHI values).
        print(f"[health/generate-appeal] EVIDENCE GUARD hard failures: "
              f"{json.dumps(evidence_validation['hard_failures'])}")

    # -- PH-4a.1: presentation — map internal [E#] keys to reader-facing [#] in
    # BOTH the body and the References block (same number in each). Runs AFTER the
    # guard so the guard always validates the E-keys, never the display numbers. --
    body_render = _map_citation_numbers(body)
    final_letter = body_render
    if evidence["references_block"]:
        references_render = _map_citation_numbers(evidence["references_block"])
        final_letter = body_render.rstrip() + "\n\nReferences\n" + references_render

    reviewer_checklist = _build_reviewer_checklist(
        evidence, evidence_validation, [evidence_note] if evidence_note else []
    )
    needs_revision = not evidence_validation["citations_ok"]

    return {
        "letter_text": final_letter,
        "validation_log": validated["validation_log"],
        "evidence_validation": evidence_validation,
        "reviewer_checklist": reviewer_checklist,
        "needs_revision": needs_revision,
        "status": "needs_revision" if needs_revision else "draft — human review required before sending",
    }


# ---------------------------------------------------------------------------
# POST /api/health/classify-document
# ---------------------------------------------------------------------------

CLASSIFY_SYSTEM_PROMPT = """You are a medical document classifier. Examine the uploaded document and determine its type. Return ONLY valid JSON matching this exact structure, with no other text, markdown, or explanation:
{
  "document_type": "medical_bill | eob | denial_letter | sbc | unknown",
  "confidence": "high | medium | low",
  "reason": "brief explanation of why you classified it this way"
}

Classification rules:
- "medical_bill": An itemized bill from a healthcare provider showing procedures, CPT codes, billed amounts. Includes hospital bills, physician bills, lab bills, and facility bills.
- "eob": An Explanation of Benefits from an insurance company showing what was covered, patient responsibility, and plan payments. Often has columns like "Amount Billed", "Plan Paid", "You Owe".
- "denial_letter": A letter or notice from an insurance company denying a claim or prior authorization. Contains denial reason codes, appeal instructions, or language about coverage determination.
- "sbc": A Summary of Benefits and Coverage document describing a health insurance plan's deductibles, copays, coinsurance, and coverage details. Usually titled "Summary of Benefits and Coverage" or "SBC".
- "unknown": If the document does not match any of the above categories.

Both medical_bill and eob should route to the bill analysis pipeline. The distinction helps with user messaging but both are analyzed the same way."""


@router.post("/api/health/classify-document")
async def classify_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    fname = file.filename.lower()

    # Reject known non-PDF clinical data formats with a friendly message
    if fname.endswith((".txt", ".edi", ".837", ".835")):
        return {
            "document_type": "unsupported_format",
            "confidence": "high",
            "reason": f"File format ({fname.rsplit('.', 1)[-1].upper()}) is a clinical data format. Please upload a PDF of your bill, EOB, denial letter, or plan summary.",
        }

    if not fname.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    client = _get_client()

    pdf_bytes = await file.read()
    if len(pdf_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum 20MB.")

    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")

    print(f"[health/classify-document] Classifying: {file.filename} ({len(pdf_bytes)} bytes)")

    content = [
        {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": pdf_b64,
            },
        },
        {
            "type": "text",
            "text": "Classify this medical document. Return only the JSON structure specified in the system prompt.",
        },
    ]

    response = _call_claude(client, content, system_prompt=CLASSIFY_SYSTEM_PROMPT)

    # Handle overloaded passthrough
    from fastapi.responses import JSONResponse
    if isinstance(response, JSONResponse):
        return response

    raw_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            raw_text += block.text

    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```\s*$", "", raw_text)
    raw_text = raw_text.strip()

    print(f"[health/classify-document] Result: {raw_text[:200]}")

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        print(f"[health/classify-document] Invalid JSON: {raw_text[:500]}")
        return {
            "document_type": "unknown",
            "confidence": "low",
            "reason": "Could not determine document type.",
        }

    return parsed


# ---------------------------------------------------------------------------
# POST /api/health/extract-docx
# ---------------------------------------------------------------------------

@router.post("/api/health/extract-docx")
async def extract_docx(file: UploadFile = File(...)):
    """Extract text from a .docx file and return it for the text analysis pipeline."""
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Please upload a .docx file.")

    try:
        from docx import Document
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="DOCX parsing dependencies are not installed.",
        )

    file_bytes = await file.read()
    if len(file_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum 20MB.")

    print(f"[health/extract-docx] Processing: {file.filename} ({len(file_bytes)} bytes)")

    try:
        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n".join(paragraphs)
    except Exception as exc:
        print(f"[health/extract-docx] Parse error: {exc}")
        raise HTTPException(status_code=400, detail="Could not read the Word document. It may be corrupted.")

    if len(text.strip()) < 20:
        raise HTTPException(status_code=400, detail="The document doesn't contain enough text to analyze.")

    print(f"[health/extract-docx] Extracted {len(text)} chars from {len(paragraphs)} paragraphs")
    return {"text": text}


# ---------------------------------------------------------------------------
# POST /api/health/extract-table
# ---------------------------------------------------------------------------

@router.post("/api/health/extract-table")
async def extract_table(file: UploadFile = File(...)):
    """Extract text from .xlsx or .csv files and return a readable representation."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    fname = file.filename.lower()
    if not fname.endswith((".xlsx", ".csv")):
        raise HTTPException(status_code=400, detail="Please upload a .xlsx or .csv file.")

    file_bytes = await file.read()
    if len(file_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum 20MB.")

    print(f"[health/extract-table] Processing: {file.filename} ({len(file_bytes)} bytes)")

    try:
        import pandas as pd

        if fname.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
        else:
            content = file_bytes.decode("utf-8", errors="replace")
            df = pd.read_csv(io.StringIO(content))

        # Drop completely empty rows and columns
        df = df.dropna(how="all").dropna(axis=1, how="all")

        if df.empty:
            raise HTTPException(status_code=400, detail="The spreadsheet appears to be empty.")

        # Convert to readable text: column headers + rows
        lines = []
        cols = list(df.columns)
        lines.append("Columns: " + " | ".join(str(c) for c in cols))
        lines.append("")

        for idx, row in df.iterrows():
            row_parts = []
            for col in cols:
                val = row[col]
                if pd.notna(val):
                    row_parts.append(f"{col}: {val}")
            if row_parts:
                lines.append(", ".join(row_parts))

        text = "\n".join(lines)

    except HTTPException:
        raise
    except Exception as exc:
        print(f"[health/extract-table] Parse error: {exc}")
        raise HTTPException(status_code=400, detail="Could not read the spreadsheet. It may be corrupted or in an unsupported format.")

    if len(text.strip()) < 20:
        raise HTTPException(status_code=400, detail="The spreadsheet doesn't contain enough data to analyze.")

    print(f"[health/extract-table] Extracted {len(text)} chars, {len(df)} rows")
    return {"text": text}
