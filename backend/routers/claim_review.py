"""Claim review endpoints — 837P parsing and pre-submission risk scoring."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from routers.auth import get_current_user
from utils.parse_837 import parse_837
from utils.risk_scorer import score_claims

router = APIRouter(prefix="/api/claim-review", tags=["claim-review"])


def _get_supabase():
    import os
    from supabase import create_client
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )


@router.post("/analyze-837")
async def analyze_837(request: Request, file: UploadFile = File(...)):
    """Parse an 837P file and score claims for pre-submission risk.

    Accepts multipart file upload (field: file).
    Returns parsed claims, risk flags, and summary.
    Does NOT persist to Supabase — stateless analysis.
    """
    # Auth check
    auth_header = request.headers.get("authorization", "")
    sb = _get_supabase()
    get_current_user(auth_header, sb)

    # Read file content
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except Exception:
            raise HTTPException(status_code=400, detail="Unable to decode file — expected UTF-8 or Latin-1 text.")

    if not text.strip():
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Verify it looks like an 837
    if "ISA" not in text[:500]:
        raise HTTPException(status_code=400, detail="File does not appear to be a valid 837 EDI file — missing ISA segment.")

    # Parse and score
    parsed = parse_837(text)

    if not parsed.get("claims"):
        raise HTTPException(status_code=400, detail="No claims found in the uploaded 837 file.")

    scored = score_claims(parsed)

    return {
        "claims": parsed["claims"],
        "risk_flags": scored["risk_flags"],
        "summary": scored["summary"],
        "parser_version": parsed["parser_version"],
        "billing_provider_name": parsed.get("billing_provider_name", ""),
        "billing_provider_npi": parsed.get("billing_provider_npi", ""),
    }
