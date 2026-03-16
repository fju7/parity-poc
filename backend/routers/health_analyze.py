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

from typing import Optional, List

from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from pydantic import BaseModel

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


class AnalyzeLineItem(BaseModel):
    cpt_code: Optional[str] = None
    revenue_code: Optional[str] = None
    description: str = ""
    quantity: int = 1
    billed_amount: float = 0.0
    modifier: Optional[str] = None
    place_of_service: Optional[str] = None


class AnalyzeResponse(BaseModel):
    provider_name: Optional[str] = None
    service_date: Optional[str] = None
    insurance_name: Optional[str] = None
    network_status: Optional[str] = None  # "in_network", "out_of_network", or null
    line_items: List[AnalyzeLineItem] = []
    total_billed: Optional[float] = None
    parsing_confidence: str = "high"


# Shared extraction prompt — same as ai_parse.py SYSTEM_PROMPT
SYSTEM_PROMPT = """You are a medical bill data extraction specialist. Extract all procedure line items from this medical bill. Return ONLY valid JSON matching this exact structure, with no other text, markdown, or explanation:
{
  "provider_name": "string or null",
  "service_date": "YYYY-MM-DD or null",
  "insurance_name": "string or null",
  "network_status": "in_network or out_of_network or null",
  "line_items": [
    {
      "cpt_code": "5-character code or null",
      "revenue_code": "4-digit code or null",
      "description": "procedure description",
      "quantity": number,
      "billed_amount": number,
      "modifier": "2-character code or null",
      "place_of_service": "2-digit code or null"
    }
  ],
  "total_billed": number or null
}
Extract every line item. Use null for any field not visible. Do not include subtotal or total rows as line items. For network_status, look for terms like "in-network", "out-of-network", "participating", "non-participating", "PPO", "HMO" to determine if the provider was in or out of network. Use null if not determinable.

IMPORTANT for service_date: Extract the DATE OF SERVICE, not the patient's date of birth. The service date is when the medical service was performed — look for labels like "Date of Service", "Service Date", "DOS", "Dates of Service", or dates near procedure descriptions. Patient DOB (date of birth, born, DOB) is NOT the service date. If multiple service dates exist, use the most recent one."""

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
        line_items=[
            AnalyzeLineItem(
                cpt_code=li.get("cpt_code"),
                revenue_code=li.get("revenue_code"),
                description=li.get("description", ""),
                quantity=li.get("quantity", 1) or 1,
                billed_amount=li.get("billed_amount", 0) or 0,
                modifier=li.get("modifier"),
                place_of_service=li.get("place_of_service"),
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
  "denial_reason_code": "the specific reason code if present (e.g. CO-97, PR-96)",
  "denial_reason_plain": "plain English explanation of why the claim was denied",
  "denial_type": "clinical | administrative | coverage | other",
  "specific_criterion": "the exact criterion, policy, or rule the carrier cited to deny",
  "weakness": "any apparent weakness in the denial reasoning, or null if denial appears straightforward",
  "supporting_documentation": ["list of specific documents that would strengthen an appeal"],
  "appeal_deadline_hint": "any appeal deadline mentioned, or null",
  "confidence": "high | medium | low",
  "patient_name": "full patient name if found in the document, or null",
  "provider_name": "provider or facility name if found, or null",
  "claim_number": "claim or reference number if found, or null",
  "date_of_service": "date of service if found (any format), or null",
  "payer_name": "insurance company name if found, or null"
}"""


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
- Uses professional but plain language — not legal jargon
- Is formatted as a real letter (date, addresses, subject line, body, closing)

Return only the letter text, no explanation or commentary."""


@router.post("/api/health/generate-appeal")
def generate_appeal(req: AppealGenerateRequest):
    client = _get_client()

    context_parts = [f"Denial analysis:\n{json.dumps(req.denial_analysis, indent=2)}"]
    if req.patient_name:
        context_parts.append(f"Patient name: {req.patient_name}")
    if req.provider_name:
        context_parts.append(f"Provider name: {req.provider_name}")
    if req.claim_number:
        context_parts.append(f"Claim number: {req.claim_number}")

    content = [{"type": "text", "text": "\n\n".join(context_parts)}]

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        temperature=0.3,
        system=APPEAL_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )

    raw_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            raw_text += block.text

    return {"letter_text": raw_text.strip()}


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
