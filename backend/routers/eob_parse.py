"""
/api/parse-eob endpoint — Uses Claude to extract structured
data from Explanation of Benefits (EOB) document images.

EOBs do not contain procedure-level health data (no CPT codes,
no diagnoses), so this extraction is lower sensitivity than
bill parsing.
"""

import json
import os
import re
import time
import urllib.request
import urllib.parse

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()

# Reuse the same lazy Anthropic client pattern as ai_parse.py
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


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class EOBParseRequest(BaseModel):
    pages: list[str]  # base64-encoded page images


class EOBParseTextRequest(BaseModel):
    text: str  # raw PDF text


class EOBParseResponse(BaseModel):
    insurance_company: str | None = None
    patient_name: str | None = None
    provider_name: str | None = None
    service_date: str | None = None
    claim_number: str | None = None
    member_id: str | None = None
    group_number: str | None = None
    amount_billed: float | None = None
    plan_paid: float | None = None
    patient_responsibility: float | None = None
    cost_reduction: float | None = None
    provider_address: str | None = None
    account_name: str | None = None


# ---------------------------------------------------------------------------
# NPPES proxy — CMS NPPES API does not support CORS, so we proxy it
# ---------------------------------------------------------------------------

NPPES_BASE = "https://npiregistry.cms.hhs.gov/api/"


@router.get("/api/nppes-lookup")
def nppes_lookup(
    name: str = Query(..., min_length=2),
    enumeration_type: str = Query("NPI-2"),
    limit: int = Query(5, ge=1, le=10),
):
    params = urllib.parse.urlencode({
        "version": "2.1",
        "enumeration_type": enumeration_type,
        "organization_name": name,
        "limit": str(limit),
    })
    url = f"{NPPES_BASE}?{params}"
    print(f"[NPPES proxy] Fetching: {url}")

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        print(f"[NPPES proxy] Error: {exc}")
        raise HTTPException(status_code=502, detail="NPPES lookup failed.")

    return data


SYSTEM_PROMPT = """You are an insurance document data extraction specialist. Extract key information from this Explanation of Benefits (EOB) document. Return ONLY valid JSON with no other text:
{
  "insurance_company": "name of the insurance company (e.g. Cigna, Aetna, UnitedHealthcare)",
  "patient_name": "full name of the patient/subscriber",
  "provider_name": "name of the healthcare provider or facility that rendered services",
  "service_date": "date of service in YYYY-MM-DD format or null",
  "claim_number": "the claim number or ID",
  "member_id": "the member or subscriber ID number",
  "group_number": "the group number if present",
  "amount_billed": "total amount billed as a number",
  "plan_paid": "amount the insurance plan paid as a number",
  "patient_responsibility": "amount the patient owes as a number",
  "cost_reduction": "discount or cost reduction amount as a number or null",
  "provider_address": "provider mailing address if shown on the EOB or null",
  "account_name": "employer or account name if shown or null"
}
Extract exactly what is shown. Use null for any field not present. For amounts, return numbers only (no $ signs or commas). If multiple claims appear, extract data for the primary or largest claim."""


@router.post("/api/parse-eob", response_model=EOBParseResponse)
def parse_eob(req: EOBParseRequest):
    if not req.pages:
        raise HTTPException(status_code=400, detail="No pages provided.")

    client = _get_client()

    # Build content blocks: each page as a separate image
    content = []
    for idx, page_b64 in enumerate(req.pages):
        # Strip data URL prefix if present
        b64_data = page_b64.strip()
        media_type = "image/jpeg"  # Default to JPEG (frontend sends JPEG)
        if b64_data.startswith("data:"):
            match = re.match(r"data:(image/\w+);base64,(.+)", b64_data, re.DOTALL)
            if match:
                media_type = match.group(1)
                b64_data = match.group(2).strip()
            else:
                # Fallback: strip everything up to and including the first comma
                b64_data = b64_data.split(",", 1)[-1].strip()

        # Detect media type from base64 header bytes
        if b64_data.startswith("/9j/"):
            media_type = "image/jpeg"
        elif b64_data.startswith("iVBOR"):
            media_type = "image/png"

        print(f"[EOB] Page {idx+1}: {len(b64_data)} chars, media={media_type}, starts={b64_data[:20]}")

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
        "text": "Extract the key information from this Explanation of Benefits document. Return only the JSON structure specified in the system prompt.",
    })

    # Call Claude with exponential backoff retry on 529 (overloaded)
    backoff_delays = [2, 5, 10]
    response = None
    for attempt in range(len(backoff_delays) + 1):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                temperature=0,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": content}],
            )
            break
        except Exception as exc:
            err_str = str(exc)
            if "529" in err_str and attempt < len(backoff_delays):
                delay = backoff_delays[attempt]
                print(f"[EOB] Claude overloaded (529), retry {attempt+1}/{len(backoff_delays)} in {delay}s...")
                time.sleep(delay)
                continue
            print(f"EOB parsing API error: {exc}")
            if "529" in err_str:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=503,
                    content={"error": "overloaded", "message": "AI service is temporarily busy. Please try again in a moment."},
                )
            raise HTTPException(
                status_code=502,
                detail="Could not read the EOB document. Please try again.",
            )

    return _parse_claude_response(response)


# ---------------------------------------------------------------------------
# Text-based EOB parsing (much cheaper/faster than image-based)
# ---------------------------------------------------------------------------

@router.post("/api/parse-eob-text", response_model=EOBParseResponse)
def parse_eob_text(req: EOBParseTextRequest):
    if not req.text or len(req.text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Insufficient text provided.")

    client = _get_client()

    print(f"[EOB-text] Parsing {len(req.text)} chars of text")

    content = [
        {
            "type": "text",
            "text": f"Extract the key information from this Explanation of Benefits document text. Return only the JSON structure specified in the system prompt.\n\n---\n{req.text}\n---",
        }
    ]

    # Call Claude with exponential backoff retry on 529 (overloaded)
    backoff_delays = [2, 5, 10]
    response = None
    for attempt in range(len(backoff_delays) + 1):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                temperature=0,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": content}],
            )
            break
        except Exception as exc:
            err_str = str(exc)
            if "529" in err_str and attempt < len(backoff_delays):
                delay = backoff_delays[attempt]
                print(f"[EOB-text] Claude overloaded (529), retry {attempt+1}/{len(backoff_delays)} in {delay}s...")
                time.sleep(delay)
                continue
            print(f"EOB text parsing API error: {exc}")
            if "529" in err_str:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=503,
                    content={"error": "overloaded", "message": "AI service is temporarily busy. Please try again in a moment."},
                )
            raise HTTPException(
                status_code=502,
                detail="Could not read the EOB document. Please try again.",
            )

    return _parse_claude_response(response)


# ---------------------------------------------------------------------------
# Shared response parsing
# ---------------------------------------------------------------------------

def _parse_claude_response(response):
    """Parse Claude's response into an EOBParseResponse."""
    raw_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            raw_text += block.text

    # Strip markdown code fences before parsing JSON
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```\s*$", "", raw_text)
    raw_text = raw_text.strip()

    print(f"EOB parse raw response: {raw_text[:200]}")

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        print(f"EOB parsing returned invalid JSON: {raw_text[:500]}")
        raise HTTPException(
            status_code=502,
            detail="Could not read the EOB document. Please try again.",
        )

    # Clean amount fields — remove $ signs, commas, spaces before converting
    for field in ["amount_billed", "plan_paid", "patient_responsibility", "cost_reduction"]:
        val = parsed.get(field)
        if val is not None and not isinstance(val, (int, float)):
            val = str(val).replace("$", "").replace(",", "").strip()
            try:
                parsed[field] = float(val)
            except (ValueError, TypeError):
                parsed[field] = None

    return EOBParseResponse(
        insurance_company=parsed.get("insurance_company"),
        patient_name=parsed.get("patient_name"),
        provider_name=parsed.get("provider_name"),
        service_date=parsed.get("service_date"),
        claim_number=parsed.get("claim_number"),
        member_id=parsed.get("member_id"),
        group_number=parsed.get("group_number"),
        amount_billed=parsed.get("amount_billed"),
        plan_paid=parsed.get("plan_paid"),
        patient_responsibility=parsed.get("patient_responsibility"),
        cost_reduction=parsed.get("cost_reduction"),
        provider_address=parsed.get("provider_address"),
        account_name=parsed.get("account_name"),
    )
