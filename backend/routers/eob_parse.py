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

from fastapi import APIRouter, HTTPException
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
    for page_b64 in req.pages:
        # Strip data URL prefix if present
        b64_data = page_b64
        media_type = "image/png"
        if page_b64.startswith("data:"):
            match = re.match(r"data:(image/\w+);base64,(.+)", page_b64, re.DOTALL)
            if match:
                media_type = match.group(1)
                b64_data = match.group(2)

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

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            temperature=0,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
        )
    except Exception as exc:
        print(f"EOB parsing API error: {exc}")
        raise HTTPException(
            status_code=502,
            detail="Could not read the EOB document. Please try again.",
        )

    # Extract text from response
    raw_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            raw_text += block.text

    # Parse JSON from response — handle potential markdown wrapping
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        print(f"EOB parsing returned invalid JSON: {raw_text[:500]}")
        raise HTTPException(
            status_code=502,
            detail="Could not read the EOB document. Please try again.",
        )

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
