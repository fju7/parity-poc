"""Parity Billing — Contract Library management endpoints."""

from __future__ import annotations

import base64
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel

from routers.auth import get_current_user
from routers.employer_shared import _get_supabase
from routers.billing_portfolio import _get_scoped_practice_ids

router = APIRouter(prefix="/api/billing/contracts", tags=["billing-contracts"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_billing_contracts(authorization: str):
    """Authenticate and return (user, bc_id, bc_role, bc_user_id, sb)."""
    sb = _get_supabase()
    user = get_current_user(authorization, sb)

    if user["company"]["type"] != "billing":
        raise HTTPException(status_code=403, detail="Billing access only")

    bc_user = sb.table("billing_company_users").select(
        "id, billing_company_id, role"
    ).eq("email", user["email"]).eq("status", "active").limit(1).execute()

    if not bc_user.data:
        raise HTTPException(status_code=404, detail="No billing company found.")

    return (
        user,
        bc_user.data[0]["billing_company_id"],
        bc_user.data[0]["role"],
        bc_user.data[0]["id"],
        sb,
    )


# ---------------------------------------------------------------------------
# POST /api/billing/contracts/upload
# ---------------------------------------------------------------------------

@router.post("/upload")
async def upload_contract(
    practice_id: str = Form(...),
    payer_name: str = Form(...),
    effective_date: Optional[str] = Form(None),
    expiry_date: Optional[str] = Form(None),
    file: UploadFile = File(...),
    authorization: str = Header(None),
):
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_contracts(authorization)

    # Validate practice
    link = sb.table("billing_company_practices").select("id").eq(
        "billing_company_id", bc_id
    ).eq("practice_id", practice_id).eq("active", True).limit(1).execute()
    if not link.data:
        raise HTTPException(status_code=404, detail="Practice not found.")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File must be under 10MB.")

    fname = file.filename or "contract.pdf"

    payer = payer_name.strip()
    if not payer:
        raise HTTPException(status_code=400, detail="Payer name required.")

    # Version logic: find current version for same practice + payer
    existing = sb.table("billing_contracts").select("id, version").eq(
        "billing_company_id", bc_id
    ).eq("practice_id", practice_id).eq("payer_name", payer).eq(
        "is_current", True
    ).limit(1).execute()

    new_version = 1
    if existing.data:
        old = existing.data[0]
        new_version = (old.get("version") or 1) + 1
        # Mark old as not current
        sb.table("billing_contracts").update({
            "is_current": False,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", old["id"]).execute()

    # Parse dates
    eff_date = effective_date if effective_date and len(effective_date) >= 8 else None
    exp_date = expiry_date if expiry_date and len(expiry_date) >= 8 else None

    # Insert metadata row first (to get the UUID)
    row = sb.table("billing_contracts").insert({
        "billing_company_id": bc_id,
        "practice_id": practice_id,
        "payer_name": payer,
        "effective_date": eff_date,
        "expiry_date": exp_date,
        "version": new_version,
        "is_current": True,
        "filename": fname,
        "file_size": len(content),
        "uploaded_by_email": user["email"],
    }).execute()

    contract_id = row.data[0]["id"]

    # Upload PDF to Supabase Storage
    storage_path = f"{bc_id}/{contract_id}.pdf"
    try:
        sb.storage.from_("billing-contracts").upload(
            path=storage_path,
            file=content,
            file_options={"content-type": "application/pdf"},
        )
        sb.table("billing_contracts").update({
            "storage_path": storage_path,
        }).eq("id", contract_id).execute()
    except Exception as exc:
        print(f"WARNING: Storage upload failed for contract {contract_id}: {exc}")
        # Fallback: store as base64 in column so the contract isn't lost
        file_b64 = base64.b64encode(content).decode("ascii")
        sb.table("billing_contracts").update({
            "file_content": file_b64,
        }).eq("id", contract_id).execute()

    return {
        "created": True,
        "contract_id": contract_id,
        "version": new_version,
        "payer_name": payer,
    }


# ---------------------------------------------------------------------------
# GET /api/billing/contracts — list current contracts
# ---------------------------------------------------------------------------

@router.get("/")
async def list_contracts(practice_id: str = None, authorization: str = Header(None)):
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_contracts(authorization)
    scoped = _get_scoped_practice_ids(bc_id, bc_user_id, bc_role, sb)

    query = sb.table("billing_contracts").select(
        "id, practice_id, payer_name, effective_date, expiry_date, version, "
        "is_current, filename, file_size, analyzed_at, uploaded_by_email, created_at, "
        "companies(name)"
    ).eq("billing_company_id", bc_id).eq("is_current", True).order("created_at", desc=True)

    if practice_id:
        query = query.eq("practice_id", practice_id)
    if scoped is not None:
        if not scoped:
            return {"contracts": []}
        query = query.in_("practice_id", scoped)

    rows = query.execute()

    result = []
    now = datetime.now(timezone.utc).date()
    for r in (rows.data or []):
        practice = r.pop("companies", None) or {}
        exp = r.get("expiry_date")
        if exp:
            try:
                from datetime import date as dt_date
                exp_d = dt_date.fromisoformat(str(exp)[:10])
                days_to_expiry = (exp_d - now).days
                if days_to_expiry < 0:
                    status = "expired"
                elif days_to_expiry <= 90:
                    status = "expiring_soon"
                else:
                    status = "active"
            except (ValueError, TypeError):
                status = "active"
        else:
            status = "active"

        result.append({
            **r,
            "practice_name": practice.get("name", "Unknown"),
            "status": status,
        })

    return {"contracts": result}


# ---------------------------------------------------------------------------
# GET /api/billing/contracts/{contract_id}/history
# ---------------------------------------------------------------------------

@router.get("/{contract_id}/history")
async def contract_history(contract_id: str, authorization: str = Header(None)):
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_contracts(authorization)

    # Get the contract to find practice_id + payer_name
    contract = sb.table("billing_contracts").select(
        "practice_id, payer_name"
    ).eq("id", contract_id).eq("billing_company_id", bc_id).limit(1).execute()

    if not contract.data:
        raise HTTPException(status_code=404, detail="Contract not found.")

    c = contract.data[0]

    # Get all versions
    versions = sb.table("billing_contracts").select(
        "id, version, is_current, filename, file_size, analyzed_at, "
        "uploaded_by_email, created_at, effective_date, expiry_date"
    ).eq("billing_company_id", bc_id).eq(
        "practice_id", c["practice_id"]
    ).eq("payer_name", c["payer_name"]).order("version", desc=True).execute()

    return {"versions": versions.data or []}


# ---------------------------------------------------------------------------
# DELETE /api/billing/contracts/{contract_id}
# ---------------------------------------------------------------------------

@router.delete("/{contract_id}")
async def delete_contract(contract_id: str, authorization: str = Header(None)):
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_contracts(authorization)

    if bc_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    contract = sb.table("billing_contracts").select(
        "id, practice_id, payer_name, version, is_current"
    ).eq("id", contract_id).eq("billing_company_id", bc_id).limit(1).execute()

    if not contract.data:
        raise HTTPException(status_code=404, detail="Contract not found.")

    c = contract.data[0]

    # Soft-delete: mark as not current (preserves history).
    # TODO: When implementing permanent purge, also delete the file from
    # Supabase Storage via sb.storage.from_("billing-contracts").remove([c["storage_path"]])
    # if the contract has a storage_path set.
    sb.table("billing_contracts").update({
        "is_current": False,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", contract_id).execute()

    # If this was current, promote prior version
    if c["is_current"]:
        prior = sb.table("billing_contracts").select("id").eq(
            "billing_company_id", bc_id
        ).eq("practice_id", c["practice_id"]).eq(
            "payer_name", c["payer_name"]
        ).eq("is_current", False).neq("id", contract_id).order(
            "version", desc=True
        ).limit(1).execute()

        if prior.data:
            sb.table("billing_contracts").update({
                "is_current": True,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", prior.data[0]["id"]).execute()

    return {"deleted": True}


# ---------------------------------------------------------------------------
# POST /api/billing/contracts/{contract_id}/analyze
# ---------------------------------------------------------------------------

@router.post("/{contract_id}/analyze")
async def analyze_contract(contract_id: str, authorization: str = Header(None)):
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_contracts(authorization)

    contract = sb.table("billing_contracts").select(
        "id, billing_company_id, practice_id, payer_name, effective_date, "
        "expiry_date, storage_path, file_content"
    ).eq(
        "id", contract_id
    ).eq("billing_company_id", bc_id).limit(1).execute()

    if not contract.data:
        raise HTTPException(status_code=404, detail="Contract not found.")

    c = contract.data[0]

    # Load PDF: prefer Storage, fall back to legacy file_content column
    file_b64 = None
    if c.get("storage_path"):
        try:
            pdf_bytes = sb.storage.from_("billing-contracts").download(c["storage_path"])
            file_b64 = base64.b64encode(pdf_bytes).decode("ascii")
        except Exception as exc:
            print(f"WARNING: Storage download failed for {c['storage_path']}: {exc}")

    if not file_b64:
        file_b64 = c.get("file_content")

    if not file_b64:
        raise HTTPException(status_code=400, detail="No file content stored for this contract.")

    # Use Claude vision to extract rates from the contract PDF
    from routers.provider_shared import _call_claude, FEE_SCHEDULE_EXTRACTION_PROMPT

    try:
        result = _call_claude(
            file_b64,
            "application/pdf",
            FEE_SCHEDULE_EXTRACTION_PROMPT,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}")

    # Enrich with contract metadata
    analysis = {
        "extraction": result,
        "payer_name": c["payer_name"],
        "effective_date": str(c.get("effective_date") or ""),
        "expiry_date": str(c.get("expiry_date") or ""),
        "rates_extracted": len(result.get("rates", [])) if isinstance(result, dict) else 0,
    }

    # Store result
    now = datetime.now(timezone.utc).isoformat()
    sb.table("billing_contracts").update({
        "analysis_result": analysis,
        "analyzed_at": now,
        "updated_at": now,
    }).eq("id", contract_id).execute()

    return {"analyzed": True, "contract_id": contract_id, "analysis": analysis}


# ---------------------------------------------------------------------------
# POST /api/billing/contracts/analyze-all
# ---------------------------------------------------------------------------

@router.post("/analyze-all")
async def analyze_all_contracts(authorization: str = Header(None)):
    user, bc_id, bc_role, bc_user_id, sb = _require_billing_contracts(authorization)

    if bc_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    # Get all current contracts not analyzed in last 30 days
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    contracts = sb.table("billing_contracts").select(
        "id, analyzed_at, storage_path, file_content"
    ).eq("billing_company_id", bc_id).eq("is_current", True).execute()

    from routers.provider_shared import _call_claude, FEE_SCHEDULE_EXTRACTION_PROMPT

    analyzed = 0
    skipped = 0
    errors = []

    for c in (contracts.data or []):
        # Skip if recently analyzed
        if c.get("analyzed_at") and c["analyzed_at"] > cutoff:
            skipped += 1
            continue

        # Load PDF: prefer Storage, fall back to legacy file_content column
        file_b64 = None
        if c.get("storage_path"):
            try:
                pdf_bytes = sb.storage.from_("billing-contracts").download(c["storage_path"])
                file_b64 = base64.b64encode(pdf_bytes).decode("ascii")
            except Exception as exc:
                print(f"WARNING: Storage download failed for {c['storage_path']}: {exc}")

        if not file_b64:
            file_b64 = c.get("file_content")

        if not file_b64:
            skipped += 1
            continue

        try:
            result = _call_claude(
                file_b64,
                "application/pdf",
                FEE_SCHEDULE_EXTRACTION_PROMPT,
            )

            analysis = {
                "extraction": result,
                "rates_extracted": len(result.get("rates", [])) if isinstance(result, dict) else 0,
            }

            now = datetime.now(timezone.utc).isoformat()
            sb.table("billing_contracts").update({
                "analysis_result": analysis,
                "analyzed_at": now,
                "updated_at": now,
            }).eq("id", c["id"]).execute()
            analyzed += 1
        except Exception as exc:
            errors.append({"contract_id": c["id"], "error": str(exc)[:200]})

    return {"analyzed": analyzed, "skipped": skipped, "errors": errors}
