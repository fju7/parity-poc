from __future__ import annotations

"""
/api/health/analyze-text and /api/health/analyze-image endpoints.

Uses Claude to extract structured bill data from pasted text or
uploaded images. Both endpoints return the same AIParseResponse shape
used by ai_parse.py so the frontend can converge all input paths
into a single pipeline.
"""

import base64
import copy
import csv
import html
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
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from utils.evidence_retrieval import retrieve_evidence
from routers.health_auth import get_health_user

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
    patient_diagnosis: Optional[str] = None  # plain-language condition/diagnosis (any condition)
    patient_icd_code: Optional[str] = None   # optional ICD-10 code


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
  "appeal_deadline_hint": "the denial's appeal deadline in its OWN literal words and units, verbatim. If the denial says '72 hours', store '72 hours' (NEVER convert to days); if it says '180 days', store '180 days'. Plain language, or null",
  "deadline_days_expedited": "number of DAYS for an expedited or panel appeal, ONLY when the denial expresses it in days. If the denial gives this timeframe in hours or any non-day unit, leave this null and capture the literal phrase in appeal_deadline_hint instead (do NOT convert). Or null",
  "deadline_days_standard": "number of DAYS for a standard appeal, ONLY when the denial expresses it in days. If the denial gives this timeframe in hours or any non-day unit, leave this null and capture the literal phrase in appeal_deadline_hint instead (do NOT convert). Or null",
  "appeal_submission": {
    "address": "the mailing address to send the appeal to, if stated, or null",
    "alt_address": "any alternate or secondary appeal address, or null",
    "fax": "appeal fax number if stated, or null",
    "phone": "appeal phone number if stated, or null"
  },
  "peer_to_peer_contact": "phone number for a provider peer-to-peer or physician-reviewer discussion if stated, or null",
  "appeal_rights": ["appeal rights and external-review options ONLY as the denial LITERALLY states them, in the denial's own words. Do NOT add statute names (e.g. ERISA), program names (e.g. ACA), or agency characterizations the denial did not use. Example of the rule: if the denial says 'Independent external reviews', store 'Independent external reviews' exactly; do NOT relabel it 'ACA independent external review' or add 'ACA'. Include a right ONLY if the denial states it. Return [] if the denial states no appeal rights"],
  "reviewer_entity": "the entity that made or reviewed the decision (e.g. eviCore, the payer's medical director), or null",
  "confidence": "high | medium | low",
  "patient_name": "full patient name if found in the document, or null",
  "member_id": "the member, subscriber, or customer ID if found, or null",
  "patient_address": "the patient's mailing address if found in the document, or null",
  "state": "the patient's two-letter state if found or derivable from the address, or null",
  "provider_name": "ordering provider's name if found, NAME ONLY without any title/credential prefix (the title goes in provider_title), or null",
  "provider_title": "the ordering provider's stated credential/title EXACTLY as written in the denial (e.g. 'Dr.', 'MD', 'NP', 'FNP', 'PA', 'RN', 'APRN'), or null if the denial does not state one. Do NOT guess, assume, or default to 'Dr.'",
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

# LEGAL REVIEW PENDING -- reservation-of-rights clause: the appeal-rights bullet below
# instructs the letter to add ONE general reservation sentence. Interim default wording:
#   "The patient reserves all other appeal and external-review rights available under
#    applicable federal and state law."
# This exact wording is a placeholder pending attorney review. When finalized, update it
# both here and in the appeal-rights bullet inside APPEAL_SYSTEM_PROMPT below.
APPEAL_SYSTEM_PROMPT = """You are a medical billing advocate writing a formal insurance appeal letter on behalf of a patient. Using the denial analysis provided, write a professional, assertive appeal letter that:
- Opens with the specific claim/denial reference
- States clearly that the patient is appealing the denial
- Directly addresses the specific criterion the carrier cited
- If a weakness was identified in the denial reasoning, leads with that as the primary argument
- Include a focused argument on clinical management impact. Many denials, especially those citing "experimental, investigational, or unproven" (EIU) grounds, turn on whether the test result will change or inform the patient's clinical management. Make this argument directly: explain what role this category of test plays in clinical decision-making (for example, how results of this type of test can guide treatment decisions such as continuing, changing, escalating, de-escalating, or monitoring therapy). If the denial analysis includes the patient's diagnosis or condition, frame this argument in the context of that condition. Argue at the level of what this class of test does and the diagnosis you were actually given.
- CRITICAL: do NOT fabricate this patient's specific clinical facts. You do NOT know this patient's specific treatment history, prior therapies, test results, or the exact management decision at stake unless the denial analysis explicitly provides them. Do NOT invent them. Do NOT state as fact any specific prior treatment, response, staging detail, or management decision that is not given in the denial analysis. Argue what this type of test does in general and for the provided diagnosis, and explicitly note that the ordering provider's separately submitted letter of medical necessity will document the specific clinical rationale and the precise management decision for this patient. This keeps the letter forceful and honest: it makes the medical-necessity argument at the level you can support, and defers patient-specific specifics to the provider.
- Handle supporting documentation HONESTLY. Never claim to enclose, attach, or submit-herewith a document that does not genuinely accompany this letter. Distinguish these categories:
  - The ONLY items that accompany this letter are this appeal letter itself and the list of published evidence citations/references appended automatically below. Cite that evidence by reference (its bracketed [number] key); do NOT claim to physically enclose journal articles or PDFs.
  - Documents already in the insurer's possession (the claim, the billing and diagnosis codes (CPT/ICD), the denial letter itself, and the payer's own medical policy) must be REFERENCED as already on file with the insurer, NOT listed as enclosures the patient is attaching.
  - The letter of medical necessity from the ordering provider and the patient's relevant medical records will be submitted SEPARATELY by the ordering provider, referencing this claim number (__CLAIM_NUMBER__). State this as a separate submission by the provider; do NOT claim these are enclosed with the patient's letter.
  - When in doubt, describe a document as "to be provided" or "being submitted separately," never as already enclosed or attached.
- Closes with a clear request for reconsideration. When stating any appeal deadline, use the denial's LITERAL timeframe wording exactly as given (e.g. "within 72 hours", drawn from appeal_deadline_hint / the deadline fields). Do NOT convert units (never turn "72 hours" into "3 days") and do NOT invent a timeframe the denial did not state
- Uses professional but plain language, not legal jargon
- Is formatted as a real letter (date, addresses, subject line, body, closing)
- Direct this appeal to the appeal submission address the denial provided (appeal_submission.address, and appeal_submission.alt_address if the denial provided a second one), stating each as the destination to which this appeal is submitted. Include the appeal fax and phone (appeal_submission.fax, appeal_submission.phone) if provided. State these purely as factual routing information for the insurer. This is a letter TO THE INSURER, not to the patient: do NOT address the patient or give the patient instructions about the addresses. In particular, do NOT say "which applies to you", do NOT tell the patient to call the member services number on their insurance card, and do NOT tell the patient to send the appeal to both addresses.
- For the letterhead date, output the exact literal token __LETTER_DATE__ (our system substitutes the correct date). Use __LETTER_DATE__ exactly once, only as the letterhead date. Never write any other calendar date to mean "today"; dates that refer to the denial (e.g. the denial date) should be written normally.
- Refer to the ordering provider using ONLY the title/credential stated in the denial analysis (the provider_title field), if any. If a title is provided, use it (for example "Dr. Smith", "Smith, NP", or "Smith, PA" as appropriate to the credential). If NO title is provided (provider_title is null or absent), refer to the provider neutrally as "the ordering provider, <Name>" and do NOT use "Dr." or any other credential you were not given. Never assume the provider is a physician.
- The denial analysis uses placeholder tokens for the patient's identifying details: __PATIENT_NAME__ for the patient's name, __MEMBER_ID__ for the member ID, __CLAIM_NUMBER__ for the claim number, and __PATIENT_ADDRESS__ for the patient's address. Write these tokens verbatim wherever that information belongs in the letter (letterhead, the RE/subject block, the signature). Do NOT invent or guess a real name, ID, claim number, or address. Our system substitutes the real values after the letter is written.
- If clinical evidence from Parity Signal is provided, incorporate the key evidence points as specific citations supporting the appeal. This strengthens the letter with scientific backing.
- Do NOT assert any external regulatory status, approval, clearance, designation (including Breakthrough Device designation, Priority Review, or any similar program), endorsement, coverage determination, or clinical guideline position from any agency or body (for example the FDA, CMS, NCCN, ASCO, ESMO, or NICE) unless that specific fact is supported by a provided bracketed [number] citation, and then only as far as that cited item's stated indication supports. Do NOT characterize what such a status, designation, or program means or implies, and do NOT claim that any body has endorsed, incorporated, approved, cleared, or recommended the service, unless a provided [number] citation states it. Do NOT state or imply that the ordering provider will supply, identify, or submit guideline or regulatory references; the ordering provider decides independently what to submit, and the letter must not assume it.
- State the patient's appeal rights using ONLY the rights and external-review options named in the denial analysis (the appeal_rights field), in the denial's own words, adding nothing. Do NOT add appeal rights, statutes, programs, or agencies that are not listed there, and do NOT assert that a particular right applies unless the denial stated it. Do not characterize which rights apply based on the patient's plan type. Then include exactly ONE general reservation sentence, to preserve the patient's remaining rights WITHOUT listing them: "The patient reserves all other appeal and external-review rights available under applicable federal and state law." If appeal_rights is empty, do not invent rights (no specific statutes, programs, or agencies); simply state that the patient is exercising their right to appeal this determination, followed by that same single general reservation sentence.

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
        # Alternate/secondary appeal address (never selected over the primary; both
        # are shown, each labeled — see the appeal prompt's address instruction).
        "alternate appeal address": sub.get("alt_address"),
        "secondary appeal address": sub.get("alt_address"),
        "alternate mailing address": sub.get("alt_address"),
    }
    # Note: bare [Phone]/[Fax]/[Email] placeholders are patient-contact fields we do not
    # have — intentionally unmapped so their lines are removed rather than back-filled with
    # the payer's appeal phone/fax (which live in the "Where & How to Appeal" UI card).
    return mapping.get(key)


# Deterministic letterhead-date token the model is asked to emit; replaced in _validate_letter.
_LETTER_DATE_TOKEN = "__LETTER_DATE__"

# The four direct patient identifiers, each mapped to a placeholder token. The
# denial analysis is de-identified (real value -> token) BEFORE it is sent to the
# model, and re-identified (token -> real value) server-side after the letter is
# generated — the same round-trip pattern used for __LETTER_DATE__. This dict is
# the SINGLE place identifiers are defined, so more can be added later trivially.
IDENTIFIER_TOKENS = {
    "patient_name":    "__PATIENT_NAME__",
    "member_id":       "__MEMBER_ID__",
    "claim_number":    "__CLAIM_NUMBER__",
    "patient_address": "__PATIENT_ADDRESS__",
}

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

# A well-formed evidence citation bracket: a single key or a comma-separated group,
# e.g. [E6], [E6, E7], [E1, E2, E4, E5]. These are citations, never placeholders.
_CITATION_BRACKET_RE = re.compile(r"\[E\d+(?:\s*,\s*E\d+)*\]")
# Anything citation-SHAPED ("[E" + digit), including malformed forms the well-formed
# pattern won't match. Used only by the never-silently-delete safeguard.
_CITATION_SHAPED_RE = re.compile(r"^E\d")


def _today_local() -> str:
    """Today's date in America/Chicago, formatted like 'July 1, 2026' (no leading zero)."""
    now = datetime.now(ZoneInfo("America/Chicago"))
    return f"{now.strftime('%B')} {now.day}, {now.year}"


def _is_signature_placeholder(key: str) -> bool:
    return any(tok in key for tok in _SIGNATURE_TOKENS)


def _deidentify_for_model(da: dict):
    """Return (da_model, token_map): a DEEP-COPIED, de-identified copy of the denial
    analysis that is safe to send to the model, plus a token -> real-value map.

    Each of the four direct identifiers (IDENTIFIER_TOKENS) that is present and
    non-empty is replaced with its placeholder token — both as its own field AND
    anywhere its real value appears inside any other string value (side-door scrub,
    so a name/id/address embedded in a free-text field is removed too). The real
    ``da`` is NEVER mutated; its real values are kept for re-identification after
    the letter is generated. Non-identifier fields (patient_diagnosis, icd_codes,
    state, payer_name, provider_name, facility_name, dates, CPT codes, etc.) are
    left intact and still go to the model.
    """
    da_model = copy.deepcopy(da or {})
    token_map = {}

    # 1) Replace the identifier FIELDS with their tokens; record the real values.
    for field, token in IDENTIFIER_TOKENS.items():
        val = da_model.get(field)
        if isinstance(val, str) and val.strip():
            token_map[token] = val
            da_model[field] = token

    # 2) Side-door scrub: replace any occurrence of a real identifier value inside
    #    every string in the copy. Only scrub values >= 4 chars (avoid pathological
    #    over-replacement); replace LONGER values before shorter ones so a shorter
    #    value that is a substring of a longer one cannot corrupt the replacement.
    replacements = sorted(
        ((token_map[t], t) for t in token_map if len(token_map[t]) >= 4),
        key=lambda pair: len(pair[0]),
        reverse=True,
    )

    def _scrub(obj):
        if isinstance(obj, str):
            for real, token in replacements:
                if real in obj:
                    obj = obj.replace(real, token)
            return obj
        if isinstance(obj, list):
            return [_scrub(x) for x in obj]
        if isinstance(obj, dict):
            return {k: _scrub(v) for k, v in obj.items()}
        return obj

    da_model = _scrub(da_model)
    return da_model, token_map


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

    # -- Re-identify: restore each patient-identifier token with its real value from
    #    the (real) denial_analysis — the source of truth, NOT the model output. PHI
    #    values are redacted from the log. An absent/empty value replaces the token
    #    with "" so no literal __TOKEN__ is ever left visible in the final letter. --
    for _field, _itoken in IDENTIFIER_TOKENS.items():
        if _itoken in letter_text:
            _real = denial_analysis.get(_field)
            letter_text = letter_text.replace(_itoken, str(_real) if _real else "")
            log.append({"field": _itoken, "action": "identifier_substituted",
                        "value": "[REDACTED]" if _real else None})

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
            if _CITATION_BRACKET_RE.fullmatch(token):
                # Inline evidence citation — single ([E1], [E11]) OR grouped
                # ([E6, E7], [E1, E2, E4, E5]). A legitimate PH-4a citation marker,
                # NEVER an unfilled placeholder. Preserve it. Grouped brackets are
                # EXPANDED into adjacent single brackets ([E6, E7] -> [E6][E7]) so
                # the downstream single-key anti-fabrication guard validates every
                # key and the renderer maps each. Single brackets are unchanged.
                if "," in label:
                    expanded = "".join(f"[{part.strip()}]" for part in label.split(","))
                    new_line = new_line.replace(token, expanded)
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
                elif _CITATION_SHAPED_RE.match(label.strip()):
                    # SAFEGUARD (Task 3): the token is citation-shaped ("[E<digit>…")
                    # but not a form we could cleanly preserve/expand above. NEVER
                    # silently delete a citation. Leave it in place and flag it for
                    # human review rather than emptying the sentence.
                    log.append({
                        "field": token,
                        "action": "citation_preserved_for_review",
                        "value": "a citation could not be automatically resolved and was left in place for human review",
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
When referring to an FDA approval, clearance, designation, or a coverage policy, always state its specific approved indication or scope exactly as given in the evidence description (for example, "approved as a companion diagnostic in muscle-invasive bladder cancer", or "covered for [the specific indication stated]"). Do NOT describe it vaguely (for example, "a specific indication") and do NOT imply the approval or policy applies to the patient's condition unless the evidence description says so.
For any item that is a clinical practice guideline, refer to its existence and general conclusion only; never reproduce or paraphrase its detailed recommendations.
Tone: confident but precise. Make the strongest case the evidence genuinely supports, but never overstate it. An unimpeachable letter beats an overreaching one.
If the evidence does not match the patient's specific diagnosis (e.g. no diagnosis code was provided), do NOT claim it does. Argue the general validity of the test, and do not fabricate a diagnosis-specific link.
When a patient's condition or diagnosis is provided, you may state that the cited evidence supports the denied service for that specific condition ONLY IF the provided evidence descriptions are actually about that condition. If the provided evidence covers different or multiple conditions, describe it accurately (for example, as supporting the service across the relevant clinical contexts) and do NOT claim the studies are specific to the patient's condition. Never assert that enclosed literature concerns the patient's specific condition unless the evidence descriptions provided actually say so.
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
    reference [3] always carry the same number.

    Handles both single ([E6] -> [6]) and grouped ([E6, E7] -> [6][7]) brackets;
    grouped brackets render as adjacent bracketed numbers. (In the live pipeline
    _validate_letter already expands groups to single brackets before the guard,
    so grouped input rarely reaches here, but this stays robust either way.)"""
    def _render(m):
        nums = re.findall(r"E(\d+)", m.group(0))
        return "".join(f"[{n}]" for n in nums)
    return _CITATION_BRACKET_RE.sub(_render, text or "")


def _render_cited_references(body: str, evidence: dict, used_keys) -> tuple:
    """Keep ONLY the evidence items the letter body actually cites, renumber the
    survivors sequentially, and remap BOTH the body's inline [E#] markers and the
    References list to the new [n] so inline numbers and the list stay in sync.

    used_keys are the E-keys the anti-fabrication guard found in the body, already in
    ascending E-number order (== pack/assignment order); that order becomes the new
    1..k numbering (earliest E-number -> [1]). Uncited (often off-condition) items are
    dropped. Returns (body_render, references_render); references_render is "" when
    nothing valid is cited, so the caller appends NO References section.

    Handles grouped brackets ([E6, E7]) and adjacent singles ([E6][E7]) via the same
    _CITATION_BRACKET_RE the renderer uses. This filters WHICH items appear and their
    NUMBERS only; the per-item reference text (_format_reference) is unchanged.
    """
    keys = (evidence or {}).get("keys") or {}
    valid_used = [ek for ek in (used_keys or []) if ek in keys]     # cited AND known
    remap = {ek: str(i) for i, ek in enumerate(valid_used, start=1)}  # e.g. 'E5' -> '3'

    def _render(m):
        out = ""
        for ej in re.findall(r"E(\d+)", m.group(0)):    # each E-number in this bracket
            ek = f"E{ej}"
            out += f"[{remap[ek]}]" if ek in remap else f"[{ek}]"   # unknown/uncited: leave as-is
        return out

    body_render = _CITATION_BRACKET_RE.sub(_render, body or "")
    ref_lines = [f"[{remap[ek]}] {_format_reference(keys[ek])}" for ek in valid_used]
    return body_render, "\n".join(ref_lines)


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


def _build_da_from_request(req: AppealGenerateRequest) -> dict:
    """Merge the request's editable fields into the denial_analysis and run the
    pre-generation data-integrity validators (claim_number, cpt dedup, state). Returns
    the merged, validated `da`.

    Pure data assembly — NO model call, NO evidence retrieval — so it is shared by BOTH
    the appeal-letter path (_generate_appeal_result) and the data-only patient-
    instruction-sheet path. Behaviour is identical to the inline block it replaced."""
    # denial_analysis is mutated in place by the pre-generation validators below.
    da = req.denial_analysis or {}

    # Merge user-supplied (editable) fields into the analysis before validating.
    # These identifiers are de-identified (replaced with placeholder tokens) before
    # the denial analysis is sent to the model, and restored server-side after
    # generation (see _deidentify_for_model + the token substitution in _validate_letter).
    if req.patient_name:
        da["patient_name"] = req.patient_name
    if req.provider_name:
        da["provider_name"] = req.provider_name
    if req.patient_address:
        da["patient_address"] = req.patient_address

    # Condition-neutral diagnosis: plain-language condition + optional ICD-10 code.
    if req.patient_diagnosis and req.patient_diagnosis.strip():
        da["patient_diagnosis"] = req.patient_diagnosis.strip()
    if req.patient_icd_code and req.patient_icd_code.strip():
        code = req.patient_icd_code.strip()
        icd = da.get("icd_codes")
        if not isinstance(icd, list):
            icd = []
        if code not in icd:
            icd.append(code)
        da["icd_codes"] = icd

    # -- PH-1-B: pre-generation data-integrity validators (extracted for unit testing) --
    _apply_pregen_validators(da, req.claim_number)
    return da


def _generate_appeal_result(req: AppealGenerateRequest) -> dict:
    """Shared appeal-generation path used by BOTH the JSON endpoint (generate_appeal)
    and the PDF endpoint (generate_appeal_pdf). Returns the exact dict the JSON
    endpoint responds with (letter_text + validation/checklist metadata), so the two
    endpoints always produce the identical letter. Callers MUST perform auth
    (get_health_user) BEFORE invoking this. Stores nothing; logs no PHI values."""
    client = _get_client()

    # denial_analysis merged with the request's editable fields and validated. Shared
    # verbatim with the data-only patient-sheet path via _build_da_from_request.
    da = _build_da_from_request(req)
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

    # De-identify the four direct identifiers BEFORE serializing for the model.
    # The real `da` is left unchanged and is still used by the post-processing
    # (_validate_letter) to restore the real values into the final letter.
    da_model, token_map = _deidentify_for_model(da)
    context_parts = [f"Denial analysis:\n{json.dumps(da_model, indent=2)}"]

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

    # -- PH: presentation — keep ONLY the references the body actually cites, renumber
    # them sequentially, and remap BOTH the body and the References list to the new [n]
    # so inline numbers and the list stay perfectly in sync. Reuses the guard's
    # already-computed used_keys. Uncited (often off-condition) references are dropped;
    # if the body cites nothing, NO References section is appended. Runs AFTER the guard
    # so the guard always validates the E-keys, never the display numbers. --
    body_render, references_render = _render_cited_references(
        body, evidence, evidence_validation["used_keys"])
    final_letter = body_render
    if references_render:
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


@router.post("/api/health/generate-appeal")
def generate_appeal(req: AppealGenerateRequest, authorization: str = Header(None)):
    # Require a logged-in Health user. Same pattern as the other authenticated
    # Health endpoints (e.g. GET /api/health/auth/me): validate the Bearer token
    # BEFORE any letter work or PHI handling. Raises 401 if missing/invalid/expired.
    get_health_user(authorization, _get_supabase())
    return _generate_appeal_result(req)


def _render_appeal_letter_pdf(letter_text: str) -> bytes:
    """Render an already-generated Health appeal letter (plain text that ALREADY
    contains its own letterhead date, inside address, and RE: block) to a clean,
    professional PDF using ReportLab, and return the bytes.

    Deliberately does NOT add any letterhead / Re: / Date line of its own — unlike the
    Provider builder — because the letter_text is self-contained and a second header
    would duplicate the letter's existing one. The letter's structure is interpreted
    for readability: ALL-CAPS (or **bold**) lines become bold headings, lines starting
    with "- " become bullets, and the trailing "References" block is set apart with
    smaller numbered entries; blank lines become paragraph spacing. Every line is
    HTML-escaped before it reaches ReportLab Paragraph (which parses a markup subset),
    so characters like "&", "<", ">" render literally. Stores nothing."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter as _letter_size
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, HRFlowable

    # Parity palette (matches the house PDF tooling in utils/pdf_branding.py).
    NAVY = colors.HexColor("#1E293B")
    TEAL = colors.HexColor("#0D9488")
    SLATE = colors.HexColor("#64748B")

    base = getSampleStyleSheet()
    s_body = ParagraphStyle("HealthAppealBody", parent=base["Normal"],
                            fontSize=10.5, leading=15, textColor=NAVY, spaceAfter=2)
    s_heading = ParagraphStyle("HealthAppealHeading", parent=s_body,
                               fontName="Helvetica-Bold", fontSize=11,
                               spaceBefore=10, spaceAfter=4)
    s_bullet = ParagraphStyle("HealthAppealBullet", parent=s_body,
                              leftIndent=16, spaceAfter=2)
    s_ref_heading = ParagraphStyle("HealthAppealRefHeading", parent=s_heading, textColor=TEAL)
    s_ref = ParagraphStyle("HealthAppealRef", parent=base["Normal"],
                           fontSize=8.5, leading=11, textColor=SLATE,
                           leftIndent=14, firstLineIndent=-14, spaceAfter=2)

    def _esc(s: str) -> str:
        # Escape only &, <, > (quote=False) so ReportLab Paragraph markup can't break.
        return html.escape(s, quote=False)

    story = []
    in_references = False
    for raw in (letter_text or "").split("\n"):
        stripped = raw.strip()
        if not stripped:
            story.append(Spacer(1, 6))
            continue

        # References section: the literal "References" line, then "[n] ..." entries.
        if stripped == "References" and not in_references:
            in_references = True
            story.append(Spacer(1, 8))
            story.append(HRFlowable(width="100%", thickness=0.5, color=SLATE, spaceAfter=6))
            story.append(Paragraph("References", s_ref_heading))
            continue
        if in_references:
            story.append(Paragraph(_esc(stripped), s_ref))
            continue

        # Bulleted item.
        if stripped.startswith("- "):
            story.append(Paragraph(_esc(stripped[2:].strip()), s_bullet, bulletText="•"))
            continue

        # Heading: a **bold-marked** line, or an ALL-CAPS (short) line.
        is_bold_marked = stripped.startswith("**") and stripped.endswith("**") and len(stripped) > 4
        alpha = [c for c in stripped if c.isalpha()]
        is_caps_heading = bool(alpha) and all(c.isupper() for c in alpha) and len(stripped) <= 120
        if is_bold_marked:
            story.append(Paragraph("<b>" + _esc(stripped.strip("*").strip()) + "</b>", s_heading))
            continue
        if is_caps_heading:
            story.append(Paragraph("<b>" + _esc(stripped) + "</b>", s_heading))
            continue

        story.append(Paragraph(_esc(stripped), s_body))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=_letter_size,
                            leftMargin=0.85 * inch, rightMargin=0.85 * inch,
                            topMargin=0.85 * inch, bottomMargin=0.85 * inch)
    doc.build(story)
    return buf.getvalue()


@router.post("/api/health/generate-appeal-pdf")
def generate_appeal_pdf(req: AppealGenerateRequest, authorization: str = Header(None)):
    """PH-4b-1: render the SAME appeal letter as generate-appeal to a clean PDF and
    stream it back. Render-and-return ONLY — STORES NOTHING (no DB insert/upsert, no
    storage upload of letter_text or the PDF) and logs no PHI, because the letter
    carries the patient's real identifiers. Same auth + same request model as
    generate-appeal; the letter is produced by the shared _generate_appeal_result."""
    get_health_user(authorization, _get_supabase())
    result = _generate_appeal_result(req)
    pdf_bytes = _render_appeal_letter_pdf(result["letter_text"])
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="appeal-letter.pdf"'},
    )


# ---------------------------------------------------------------------------
# PH-4b-2 — Patient instruction sheet (DATA-ONLY; no model, no evidence search).
# Holds the patient-facing content that was removed from the insurer letter:
# where/how to send the appeal, deadlines as plain advice, what to gather, and a
# copy-paste provider email. Assembled purely from the request data; stores nothing.
# ---------------------------------------------------------------------------

def _service_description(da: dict) -> str:
    """Plain-language description of the service at issue, from procedure_terms
    (preferred) and/or cpt_codes. Returns "" if neither is present."""
    terms = [str(t).strip() for t in (da.get("procedure_terms") or []) if str(t).strip()]
    codes = [str(c).strip() for c in (da.get("cpt_codes") or []) if str(c).strip()]
    if terms and codes:
        return f"{', '.join(terms)} (CPT {', '.join(codes)})"
    if terms:
        return ", ".join(terms)
    if codes:
        return f"CPT {', '.join(codes)}"
    return ""


def _build_provider_email(da: dict) -> str:
    """Compose a copy-paste email the PATIENT sends to their PROVIDER's office asking
    them to submit a letter of medical necessity and relevant records DIRECTLY to the
    insurer, referencing the claim number. Data-only (NO model call). Every value is
    filled from `da`; missing values are phrased gracefully, never left as blank
    tokens."""
    provider_name = (da.get("provider_name") or "").strip()
    claim_number = (da.get("claim_number") or "").strip()
    payer_name = (da.get("payer_name") or "").strip()
    service = _service_description(da)
    patient_name = (da.get("patient_name") or "").strip()

    greeting = f"Dear {provider_name}," if provider_name else "Dear ordering provider's office,"

    # Build the body in plain sentences, omitting clauses whose data is absent.
    service_clause = f" for {service}" if service else ""
    payer_clause = f" to {payer_name}" if payer_name else " to my insurer"
    claim_clause = f", referencing claim number {claim_number}" if claim_number else ""

    lines = [
        greeting,
        "",
        (f"My insurance claim{service_clause} was denied and I am filing an appeal. "
         "To support the appeal, I am asking your office to submit a letter of medical "
         f"necessity and my relevant medical records directly{payer_clause}{claim_clause}."),
        "",
        ("The letter of medical necessity should explain why this service was ordered "
         "and why it is medically necessary for my care. Please send it, along with any "
         "supporting records (office notes, test results, and prior treatment history), "
         "as soon as possible so it arrives within the appeal deadline."),
        "",
        "Please let me know if you need anything from me to complete this request.",
        "",
        "Thank you,",
        (patient_name or "[Your name]"),
    ]
    return "\n".join(lines)


def _build_patient_sheet_content(da: dict) -> dict:
    """Assemble the patient instruction sheet sections from `da` (real field names).
    Data-only: no model, no evidence. Omits any line whose source field is absent;
    never emits a literal null. Returns a structured dict the renderer consumes."""
    sub = da.get("appeal_submission") or {}
    patient_name = (da.get("patient_name") or "").strip()
    claim_number = (da.get("claim_number") or "").strip()

    # -- WHERE TO SEND: addresses + the patient-directed guidance removed from the letter --
    address = (sub.get("address") or "").strip()
    alt_address = (sub.get("alt_address") or "").strip()
    fax = (sub.get("fax") or "").strip()
    phone = (sub.get("phone") or "").strip()
    where = {
        "address": address or None,
        "alt_address": alt_address or None,
        "fax": fax or None,
        "phone": phone or None,
        # Only meaningful when a second address exists and we cannot tell which is the
        # patient's plan — the correct home for the "which applies to you" guidance.
        "guidance": (
            "If you are unsure which applies to you, you may send your appeal to both "
            "addresses, or call the member services number on your insurance card to confirm."
            if alt_address else None
        ),
    }

    # -- DEADLINES as plain advice. Literal wording verbatim; day integers in plain language. --
    deadlines = []
    hint = (da.get("appeal_deadline_hint") or "").strip()
    if hint:
        deadlines.append(f"Your denial states the appeal deadline as: {hint}. Do not miss it.")
    std = da.get("deadline_days_standard")
    if isinstance(std, int) and std > 0:
        deadlines.append(f"You have up to {std} days to file a standard appeal.")
    exp = da.get("deadline_days_expedited")
    if isinstance(exp, int) and exp > 0:
        deadlines.append(f"For an expedited (urgent) appeal, you have up to {exp} days.")
    p2p = (da.get("peer_to_peer_contact") or "").strip()
    if p2p:
        deadlines.append(f"Your provider can call {p2p} to request a peer-to-peer review with the insurer's reviewer.")

    # -- WHAT YOU NEED TO DO: the appeal letter already contains the argument and the
    # supporting medical evidence, so the patient does not gather documents themselves.
    # The one thing to secure is a letter of medical necessity + records from the
    # provider. Worded to stay true whether or not the letter has a citations list.
    # Folds in the old gather_note substance (provider sends to insurer, claim ref). --
    provider_name = (da.get("provider_name") or "").strip()
    provider_clause = f" ({provider_name})" if provider_name else ""
    claim_ref = f", referencing claim number {claim_number}" if claim_number else ""
    what_you_need_to_do = (
        "Your appeal letter already lays out the argument and the medical evidence "
        "supporting your case, so you do not need to gather studies or documents yourself. "
        "The most important thing you can do is ask your provider" + provider_clause
        + " for a letter of medical necessity, along with your relevant medical records "
        "(such as diagnosis, stage, and treatment history). Your provider sends these "
        "directly to the insurer" + claim_ref + ". Use the email in the \"Email Your "
        "Provider\" section below to request them."
    )

    return {
        "title": "What To Do Next With Your Appeal",
        "personalized_for": patient_name or None,
        "intro": (
            "This sheet explains what to do with the appeal letter we prepared for you. "
            "It is for YOU. Do not send this instruction sheet to your insurance company; "
            "send the appeal letter itself (and keep this sheet for your own reference)."
        ),
        "where": where,
        "deadlines": deadlines,
        "what_you_need_to_do": what_you_need_to_do,
        "provider_email": _build_provider_email(da),
        "provider_email_intro": "Copy the text below into an email to your provider's office:",
        "next_steps": [
            "Review and sign the appeal letter.",
            "Send the appeal letter to the address above before the deadline.",
            "Email your provider (using the text above) to submit the medical-necessity letter and records.",
            "Keep copies of everything you send.",
        ],
    }


def _render_patient_sheet_pdf(content: dict) -> bytes:
    """Render the patient instruction sheet (structured sections) to a clean PDF using
    ReportLab, following the SAME palette/style conventions as _render_appeal_letter_pdf
    (NAVY/TEAL/SLATE, Helvetica, letter size, 0.85in margins). Composes flowables per
    section (no text parsing). Every dynamic string is HTML-escaped before Paragraph.
    NO Provider letterhead. Stores nothing; returns bytes."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter as _letter_size
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, HRFlowable, Table, TableStyle,
    )

    NAVY = colors.HexColor("#1E293B")
    TEAL = colors.HexColor("#0D9488")
    SLATE = colors.HexColor("#64748B")
    LIGHT = colors.HexColor("#F0FDFA")

    base = getSampleStyleSheet()
    s_title = ParagraphStyle("PSTitle", parent=base["Normal"], fontName="Helvetica-Bold",
                             fontSize=18, leading=22, textColor=NAVY, spaceAfter=4)
    s_sub = ParagraphStyle("PSSub", parent=base["Normal"], fontSize=11, leading=15,
                           textColor=SLATE, spaceAfter=6)
    s_section = ParagraphStyle("PSSection", parent=base["Normal"], fontName="Helvetica-Bold",
                               fontSize=12, leading=16, textColor=TEAL, spaceBefore=12, spaceAfter=4)
    s_body = ParagraphStyle("PSBody", parent=base["Normal"], fontSize=10.5, leading=15,
                            textColor=NAVY, spaceAfter=3)
    s_bullet = ParagraphStyle("PSBullet", parent=s_body, leftIndent=16, spaceAfter=2)
    s_email = ParagraphStyle("PSEmail", parent=base["Normal"], fontName="Courier",
                             fontSize=9.5, leading=13, textColor=NAVY)

    def _esc(s):
        return html.escape(str(s or ""), quote=False)

    story = []

    # Header.
    story.append(Paragraph(_esc(content.get("title") or "What To Do Next"), s_title))
    if content.get("personalized_for"):
        story.append(Paragraph("Instructions for " + _esc(content["personalized_for"]), s_sub))
    story.append(HRFlowable(width="100%", thickness=1.5, color=TEAL, spaceAfter=8))
    if content.get("intro"):
        story.append(Paragraph(_esc(content["intro"]), s_body))

    # Where to send.
    where = content.get("where") or {}
    if where.get("address") or where.get("fax") or where.get("phone"):
        story.append(Paragraph("Where To Send Your Appeal", s_section))
        if where.get("address"):
            story.append(Paragraph("Send your appeal to:", s_body))
            for ln in str(where["address"]).split("\n"):
                if ln.strip():
                    story.append(Paragraph(_esc(ln.strip()), s_bullet))
        if where.get("alt_address"):
            story.append(Paragraph("Or, alternatively:", s_body))
            for ln in str(where["alt_address"]).split("\n"):
                if ln.strip():
                    story.append(Paragraph(_esc(ln.strip()), s_bullet))
        if where.get("fax"):
            story.append(Paragraph("Fax: " + _esc(where["fax"]), s_body))
        if where.get("phone"):
            story.append(Paragraph("Phone: " + _esc(where["phone"]), s_body))
        if where.get("guidance"):
            story.append(Paragraph(_esc(where["guidance"]), s_body))

    # Deadlines.
    if content.get("deadlines"):
        story.append(Paragraph("Deadlines", s_section))
        for d in content["deadlines"]:
            story.append(Paragraph(_esc(d), s_bullet, bulletText="•"))

    # What you need to do (renders in the same position the old "What To Gather" did,
    # i.e. above "Email Your Provider", so the paragraph's "section below" is correct).
    if content.get("what_you_need_to_do"):
        story.append(Paragraph("What You Need to Do", s_section))
        story.append(Paragraph(_esc(content["what_you_need_to_do"]), s_body))

    # Email your provider (visually set off in a bordered/shaded block).
    if content.get("provider_email"):
        story.append(Paragraph("Email Your Provider", s_section))
        if content.get("provider_email_intro"):
            story.append(Paragraph(_esc(content["provider_email_intro"]), s_body))
        email_flow = [Paragraph(_esc(ln) if ln.strip() else "&nbsp;", s_email)
                      for ln in str(content["provider_email"]).split("\n")]
        box = Table([[email_flow]], colWidths=[6.4 * inch])
        box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.75, TEAL),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(box)

    # Next steps recap.
    if content.get("next_steps"):
        story.append(Paragraph("Next Steps", s_section))
        for i, step in enumerate(content["next_steps"], start=1):
            story.append(Paragraph(f"{i}. " + _esc(step), s_bullet))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=_letter_size,
                            leftMargin=0.85 * inch, rightMargin=0.85 * inch,
                            topMargin=0.85 * inch, bottomMargin=0.85 * inch)
    doc.build(story)
    return buf.getvalue()


@router.post("/api/health/generate-patient-sheet-pdf")
def generate_patient_sheet_pdf(req: AppealGenerateRequest, authorization: str = Header(None)):
    """PH-4b-2: render the PATIENT instruction sheet (data-only) to a clean PDF and
    stream it back. Does NOT call the model or evidence retrieval — assembled purely
    from the request via _build_da_from_request. Render-and-return ONLY: STORES NOTHING
    (no DB insert/upsert, no storage upload) and logs no PHI. Same auth + same request
    model as generate-appeal."""
    get_health_user(authorization, _get_supabase())
    da = _build_da_from_request(req)
    content = _build_patient_sheet_content(da)
    pdf_bytes = _render_patient_sheet_pdf(content)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="patient-instructions.pdf"'},
    )


@router.post("/api/health/provider-email")
def provider_email(req: AppealGenerateRequest, authorization: str = Header(None)):
    """PH-4b-2: return the copy-paste provider email TEXT (same text the patient sheet
    PDF shows) for the on-screen 'Copy provider email' button. Data-only (no model);
    STORES NOTHING and logs no PHI. Same auth + request model."""
    get_health_user(authorization, _get_supabase())
    da = _build_da_from_request(req)
    return {"email": _build_provider_email(da)}


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
