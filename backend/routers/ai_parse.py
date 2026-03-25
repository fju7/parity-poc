from __future__ import annotations

"""
/api/parse-with-ai endpoint — Uses Claude to extract structured
bill data from PDF page images.

Privacy note: This is the ONLY endpoint that receives health data.
Standard parsing never sends document content to any server.
"""

import json
import os
import re
import time

from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# Anthropic client — lazy-initialized
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

class AIParseRequest(BaseModel):
    pages: List[str]  # base64-encoded page images


class AIParseLineItem(BaseModel):
    cpt_code: Optional[str] = None
    revenue_code: Optional[str] = None
    description: str = ""
    quantity: int = 1
    billed_amount: float = 0.0
    modifier: Optional[str] = None
    modifiers: List[str] = []
    place_of_service: Optional[str] = None
    date_of_service: Optional[str] = None


class AIParseResponse(BaseModel):
    provider_name: Optional[str] = None
    service_date: Optional[str] = None
    insurance_name: Optional[str] = None
    claim_number: Optional[str] = None
    adjudication_date: Optional[str] = None
    parser_version: int = 2
    line_items: List[AIParseLineItem] = []
    total_billed: Optional[float] = None
    parsing_confidence: str = "high"


SYSTEM_PROMPT = """You are a medical bill and Explanation of Benefits (EOB) data extraction specialist.

IMPORTANT — read the ENTIRE document first before extracting any fields. Understand the document's structure, layout, and terminology as a whole before attempting extraction. Different insurance companies use different labels, layouts, and terminology for the same information. Infer field locations flexibly — never return null just because a label does not match an expected term. If the information is present anywhere in the document, find it.

Return ONLY valid JSON matching this exact structure, with no other text, markdown, or explanation:
{
  "provider_name": "string or null",
  "service_date": "YYYY-MM-DD or null",
  "insurance_name": "string or null",
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
- modifier: the first modifier code as a single string (null if none). modifiers: an array of ALL modifier codes on that line (e.g. ["25", "59"]). If no modifiers, use null for modifier and [] for modifiers. Modifiers often appear next to CPT codes separated by dashes, commas, or in adjacent columns.
- claim_number: may appear as "Claim #", "Claim Number", "ICN", "DCN", "Reference Number", "Confirmation Number", "Control Number", or other insurer-specific labels. Return null only if genuinely absent from the document.
- adjudication_date: the date the claim was processed or paid — may appear as "Date Processed", "Adjudication Date", "Payment Date", "Paid Date", "Decision Date", "Statement Date", or similar. This is NOT the date of service. Return null only if genuinely absent.
- date_of_service per line: the date treatment was performed for this specific line. May appear as "Date of Service", "Service Date", "Date Treated", "DOS", or dates adjacent to procedure descriptions. Return null only if genuinely absent or if only a single service date exists (already captured in the top-level service_date field).
- parser_version must always be 2."""


@router.post("/api/parse-with-ai", response_model=AIParseResponse)
def parse_with_ai(req: AIParseRequest):
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
                b64_data = b64_data.split(",", 1)[-1].strip()

        # Detect media type from base64 header bytes
        if b64_data.startswith("/9j/"):
            media_type = "image/jpeg"
        elif b64_data.startswith("iVBOR"):
            media_type = "image/png"

        print(f"[AI Parse] Page {idx+1}: {len(b64_data)} chars, media={media_type}, starts={b64_data[:20]}")

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
        "text": "Extract all procedure line items from this medical bill. Return only the JSON structure specified in the system prompt.",
    })

    # Call Claude with exponential backoff retry on 529 (overloaded)
    backoff_delays = [2, 5, 10]
    response = None
    for attempt in range(len(backoff_delays) + 1):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                temperature=0,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": content}],
            )
            break
        except Exception as exc:
            err_str = str(exc)
            if "529" in err_str and attempt < len(backoff_delays):
                delay = backoff_delays[attempt]
                print(f"[AI Parse] Claude overloaded (529), retry {attempt+1}/{len(backoff_delays)} in {delay}s...")
                time.sleep(delay)
                continue
            print(f"AI parsing API error: {exc}")
            if "529" in err_str:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=503,
                    content={"error": "overloaded", "message": "AI service is temporarily busy. Please try again in a moment."},
                )
            raise HTTPException(
                status_code=502,
                detail="AI reading encountered an error. Please try a clearer image or enter manually.",
            )

    # Extract text from response
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

    print(f"AI parse raw response: {raw_text[:200]}")

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        print(f"AI parsing returned invalid JSON: {raw_text[:500]}")
        raise HTTPException(
            status_code=502,
            detail="AI reading encountered an error. Please try a clearer image or enter manually.",
        )

    # Clean amount fields — remove $ signs, commas, spaces before converting
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

    # Determine confidence based on number of line items extracted
    items = parsed.get("line_items", [])
    confidence = "high" if len(items) >= 3 else "medium" if len(items) >= 1 else "low"

    return AIParseResponse(
        provider_name=parsed.get("provider_name"),
        service_date=parsed.get("service_date"),
        insurance_name=parsed.get("insurance_name"),
        claim_number=parsed.get("claim_number"),
        adjudication_date=parsed.get("adjudication_date"),
        parser_version=parsed.get("parser_version", 2),
        line_items=[
            AIParseLineItem(
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
