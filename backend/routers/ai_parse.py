"""
/api/parse-with-ai endpoint — Uses Claude to extract structured
bill data from PDF page images.

Privacy note: This is the ONLY endpoint that receives health data.
Standard parsing never sends document content to any server.
"""

import json
import os
import re

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
    pages: list[str]  # base64-encoded page images


class AIParseLineItem(BaseModel):
    cpt_code: str | None = None
    revenue_code: str | None = None
    description: str = ""
    quantity: int = 1
    billed_amount: float = 0.0
    modifier: str | None = None
    place_of_service: str | None = None


class AIParseResponse(BaseModel):
    provider_name: str | None = None
    service_date: str | None = None
    insurance_name: str | None = None
    line_items: list[AIParseLineItem] = []
    total_billed: float | None = None
    parsing_confidence: str = "high"


SYSTEM_PROMPT = """You are a medical bill data extraction specialist. Extract all procedure line items from this medical bill. Return ONLY valid JSON matching this exact structure, with no other text, markdown, or explanation:
{
  "provider_name": "string or null",
  "service_date": "YYYY-MM-DD or null",
  "insurance_name": "string or null",
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
Extract every line item. Use null for any field not visible. Do not include subtotal or total rows as line items."""


@router.post("/api/parse-with-ai", response_model=AIParseResponse)
def parse_with_ai(req: AIParseRequest):
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
        "text": "Extract all procedure line items from this medical bill. Return only the JSON structure specified in the system prompt.",
    })

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            temperature=0,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
        )
    except Exception as exc:
        print(f"AI parsing API error: {exc}")
        raise HTTPException(
            status_code=502,
            detail="AI reading encountered an error. Please try a clearer image or enter manually.",
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
        print(f"AI parsing returned invalid JSON: {raw_text[:500]}")
        raise HTTPException(
            status_code=502,
            detail="AI reading encountered an error. Please try a clearer image or enter manually.",
        )

    # Determine confidence based on number of line items extracted
    items = parsed.get("line_items", [])
    confidence = "high" if len(items) >= 3 else "medium" if len(items) >= 1 else "low"

    return AIParseResponse(
        provider_name=parsed.get("provider_name"),
        service_date=parsed.get("service_date"),
        insurance_name=parsed.get("insurance_name"),
        line_items=[
            AIParseLineItem(
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
