from __future__ import annotations

"""
/api/health/analyze-text and /api/health/analyze-image endpoints.

Uses Claude to extract structured bill data from pasted text or
uploaded images. Both endpoints return the same AIParseResponse shape
used by ai_parse.py so the frontend can converge all input paths
into a single pipeline.
"""

import json
import os
import re
import time

from typing import Optional, List

from fastapi import APIRouter, HTTPException
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


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AnalyzeTextRequest(BaseModel):
    text: str


class AnalyzeImageRequest(BaseModel):
    pages: List[str]  # base64-encoded images


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
    line_items: List[AnalyzeLineItem] = []
    total_billed: Optional[float] = None
    parsing_confidence: str = "high"


# Shared extraction prompt — same as ai_parse.py SYSTEM_PROMPT
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


# ---------------------------------------------------------------------------
# POST /api/health/analyze-text
# ---------------------------------------------------------------------------

@router.post("/api/health/analyze-text", response_model=AnalyzeResponse)
def analyze_text(req: AnalyzeTextRequest):
    if not req.text or len(req.text.strip()) < 20:
        raise HTTPException(status_code=400, detail="Insufficient text provided.")

    client = _get_client()

    print(f"[health/analyze-text] Parsing {len(req.text)} chars of text")

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

    response = _call_claude(client, content)
    return _parse_response(response)


# ---------------------------------------------------------------------------
# POST /api/health/analyze-image
# ---------------------------------------------------------------------------

@router.post("/api/health/analyze-image", response_model=AnalyzeResponse)
def analyze_image(req: AnalyzeImageRequest):
    if not req.pages:
        raise HTTPException(status_code=400, detail="No images provided.")

    client = _get_client()

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

    response = _call_claude(client, content)
    return _parse_response(response)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _call_claude(client, content):
    """Call Claude with exponential backoff on 529 (overloaded)."""
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


def _parse_response(response):
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

    return AnalyzeResponse(
        provider_name=parsed.get("provider_name"),
        service_date=parsed.get("service_date"),
        insurance_name=parsed.get("insurance_name"),
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
