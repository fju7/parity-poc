"""Provider appeal endpoints — appeal letter generation, listing, status tracking."""

from __future__ import annotations

import base64
import io
import json

from fastapi import APIRouter, HTTPException, Request

from routers.provider_shared import (
    _get_supabase, _get_authenticated_user, _verify_admin,
    _call_claude,
    GenerateAppealRequest, GenerateAppealBatchRequest, UpdateAppealStatusRequest,
)

router = APIRouter(tags=["provider"])


# ---------------------------------------------------------------------------
# Appeal Letter Generation
# ---------------------------------------------------------------------------

APPEAL_SYSTEM_PROMPT = """You are a senior healthcare billing attorney and compliance officer with 20+ years of experience in payer appeals and reimbursement disputes. Generate a formal appeal letter that reads as if drafted by experienced legal counsel — precise, authoritative, and grounded in specific regulatory citations.

CRITICAL INSTRUCTION: Use the following provider details to complete the letter — do not use placeholder brackets for any field that has been provided. Only use a placeholder if the value is genuinely unknown (i.e. the field is empty or null in the data below). Never output [INSERT ...], [CONTRACT EFFECTIVE DATE], [CONTRACT DATE], or similar bracket placeholders when the information exists in the provided data.

The user message contains a JSON object with these named variables:
- practice_name: The legal name of the provider practice (use as signing entity)
- billing_contact: The name of the billing contact person (use in signature block)
- npi: The practice NPI number
- practice_address: The practice mailing address for correspondence
- payer_name: The insurance payer being appealed to
- claim_id: The specific claim identifier
- denial_code: The CARC/RARC denial code (e.g. CO-45, CO-97)
- cpt_code: The CPT code(s) at issue
- billed_amount: The dollar amount originally billed
- date_of_service: The date the service was rendered
- patient_name: The patient name
- contracted_rate_info: Known contracted rates for the CPT codes (may be null)

LETTER STRUCTURE:

1. FORMAL HEADER BLOCK — open every letter with:
   RE: Formal Appeal of {denial_code} — Claim {claim_id}
   Patient: {patient_name}
   Date of Service: {date_of_service}
   CPT Code: {cpt_code} — [full AMA CPT description of this code]
   Billed Amount: ${billed_amount}
   Payer Reference Number: {claim_id}

2. OPENING PARAGRAPH — state the claim precisely:
   "This letter constitutes a formal first-level appeal of {payer_name}'s denial of Claim {claim_id} under denial code {denial_code}, issued on the remittance advice referenced above. The denial is without contractual or regulatory basis for the reasons set forth below."

3. REGULATORY AUTHORITY — cite specific regulatory support based on the denial code:

   CO-16 (missing information):
   - CMS Internet-Only Manual (IOM) Publication 100-04, Chapter 1, Section 80.3.2
   - 42 CFR § 424.5(a)(6) — required claim information
   - State: "Administrative deficiencies in claim submission do not constitute grounds for denial of a medically necessary, properly rendered service. The documentation accompanying this claim fully satisfies the requirements of 42 CFR § 424.5(a)(6)."

   CO-45 (charge exceeds fee schedule):
   - Reference the specific contracted rate from contracted_rate_info if provided
   - CMS Physician Fee Schedule (cite the specific PFS year and locality if Medicare)
   - State: "Pursuant to our current executed provider agreement, the contracted rate for CPT {cpt_code} is ${rate from contracted_rate_info}. Payment of ${paid} represents a variance of ${difference} from the contractually obligated amount."

   CO-97 (already adjudicated / bundled):
   - CMS National Correct Coding Initiative (NCCI) Policy Manual, Chapter 1, current edition
   - CMS Medically Unlikely Edits (MUE) tables
   - State: "The services rendered on {date_of_service} are clinically distinct and separately identifiable. NCCI bundling edits do not apply because [provide specific reason — different anatomical site, separate encounter, distinct medical necessity, or appropriate modifier usage]."

   CO-4 (modifier inconsistent with procedure code):
   - AMA CPT Assistant guidelines for the specific modifier used
   - CMS Claims Processing Manual, Chapter 12
   - State: "Modifier [XX] was applied in accordance with AMA CPT coding guidelines and CMS Claims Processing Manual Chapter 12. The operative documentation supports the distinct procedural circumstances that necessitate this modifier."

   CO-50 (non-covered service / medical necessity):
   - 42 CFR § 410.32(a) — medical necessity standard
   - Reference applicable Local Coverage Determination (LCD) or National Coverage Determination (NCD) if relevant to this CPT code
   - State: "The service meets the definition of medical necessity under 42 CFR § 410.32(a). The clinical record demonstrates [cite specific clinical indicators from the claim data — diagnosis, symptoms, or clinical findings that justify the service]."

   OA-18 (exact duplicate claim):
   - CMS Claims Processing Manual, Chapter 1, Section 80.3.1
   - State: "The claims identified as duplicates represent clinically distinct services as evidenced by [different date of service, different modifier, different anatomical site, or distinct clinical circumstance]. Documentation is attached to support the separate medical necessity of each service."

   PR-1 (deductible amount):
   - Only appealable if applied incorrectly
   - State: "Review of the patient's Explanation of Benefits indicates the deductible has been [satisfied as of date / incorrectly applied to this service]. The attached EOB documentation demonstrates the error in deductible calculation."

4. CONTRACTUAL OBLIGATIONS SECTION — include when contracted_rate_info is provided:
   - State the specific dollar variance between billed/contracted and paid amounts
   - Reference "our current executed provider agreement" as a binding contract (do NOT use a specific date or bracket placeholder for the contract date)
   - State: "Systematic underpayment below contracted rates constitutes a material breach of our provider participation agreement. We reserve the right to audit additional claims for similar variances and to pursue corrective action including interest on underpaid amounts as provided under our agreement."

5. PROFESSIONAL CLOSING — must include:
   - "We demand reprocessing and payment of ${billed_amount} within 30 calendar days, consistent with applicable state prompt pay statutes and the payment terms specified in our provider participation agreement."
   - "Failure to respond within this timeframe will necessitate escalation to the state Department of Insurance and/or initiation of the dispute resolution process outlined in our provider agreement."
   - "Please direct all correspondence regarding this appeal to {practice_name} at {practice_address}."
   - Sign with billing_contact name and practice_name.

6. TONE: Professional, firm, and authoritative throughout. Write as experienced legal counsel — not adversarial, but leaving no doubt that the practice knows its rights and will pursue them.

Return ONLY valid JSON:
{
  "letter_html": "<full HTML-formatted appeal letter with proper paragraphs, headings, and formatting>",
  "letter_text": "plain text version of the letter",
  "cms_references": ["list of every specific CMS/CFR/guideline reference cited in the letter"],
  "appeal_strength": "high|medium|low",
  "appeal_strength_reason": "Assessment including: (1) strength of legal/regulatory basis, (2) estimated resolution timeline (30/60/90 days), (3) one sentence on key documentation the practice should attach",
  "escalation_path": "Specific next steps if this first-level appeal is denied — e.g., external review, state DOI complaint, arbitration under provider agreement, or CMS administrative appeal for Medicare claims",
  "attach_documentation": "Specific list of documents the practice should attach — e.g., operative notes, signed orders, EOB showing deductible status, prior authorization approval, modifier documentation, fee schedule excerpt"
}"""


def _generate_appeal_pdf(letter_text: str, practice_name: str, payer_name: str, claim_id: str) -> bytes:
    """Generate a formatted PDF appeal letter using ReportLab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, HRFlowable
    from datetime import datetime

    TEAL = colors.HexColor("#0D9488")
    NAVY = colors.HexColor("#1E293B")

    styles = getSampleStyleSheet()
    s_header = ParagraphStyle("AppealHeader", parent=styles["Normal"], fontSize=10, textColor=TEAL, spaceAfter=2)
    s_body = ParagraphStyle("AppealBody", parent=styles["Normal"], fontSize=11, leading=16, textColor=NAVY)
    s_small = ParagraphStyle("AppealSmall", parent=styles["Normal"], fontSize=9, leading=12, textColor=colors.HexColor("#64748B"))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=1 * inch, rightMargin=1 * inch,
        topMargin=1 * inch, bottomMargin=1 * inch,
    )

    story = []

    # Letterhead
    story.append(Paragraph(practice_name, ParagraphStyle("PracticeName", parent=s_body, fontSize=14, textColor=NAVY, fontName="Helvetica-Bold")))
    story.append(Paragraph(f"Re: Appeal — Claim {claim_id}", s_header))
    story.append(Paragraph(f"Date: {datetime.now().strftime('%B %d, %Y')}", s_header))
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL, spaceAfter=16, spaceBefore=8))

    # Letter body
    for line in letter_text.split("\n"):
        if line.strip():
            story.append(Paragraph(line.strip(), s_body))
            story.append(Spacer(1, 6))
        else:
            story.append(Spacer(1, 12))

    # Footer
    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceAfter=8))
    story.append(Paragraph("Generated by Parity Health — CivicScale Benchmark Infrastructure", s_small))
    story.append(Paragraph("This letter template should be reviewed and customized before sending.", s_small))

    doc.build(story)
    return buf.getvalue()


def _fetch_provider_context(user_id: str) -> dict:
    """Fetch provider profile and all saved contract rates for appeal generation.

    Returns dict with practice_name, npi, practice_address, billing_contact,
    and a contracts dict keyed by payer_name.
    """
    ctx = {
        "practice_name": "",
        "npi": "",
        "practice_address": "",
        "billing_contact": "",
        "contracts": {},  # {payer_name: {cpt: rate_string, ...}}
    }
    try:
        sb = _get_supabase()
        profile = sb.table("provider_profiles").select("*").eq("company_id", user_id).execute()
        if profile.data:
            p = profile.data[0]
            ctx["practice_name"] = p.get("practice_name", "") or ""
            ctx["npi"] = p.get("npi", "") or ""
            ctx["practice_address"] = p.get("practice_address", "") or ""
            ctx["billing_contact"] = p.get("billing_contact", "") or p.get("practice_name", "") or ""
    except Exception as exc:
        print(f"[Appeal] Failed to fetch profile: {exc}")

    try:
        sb = _get_supabase()
        all_contracts = sb.table("provider_contracts").select("payer_name, rates").eq("company_id", user_id).order("created_at", desc=True).execute()
        for row in all_contracts.data or []:
            payer = row.get("payer_name", "")
            if payer and payer not in ctx["contracts"]:
                rate_map = {}
                for rate_item in row.get("rates") or []:
                    cpt = rate_item.get("cpt", "")
                    rate_vals = rate_item.get("rates", {})
                    if isinstance(rate_vals, dict) and cpt:
                        for v in rate_vals.values():
                            if v is not None:
                                rate_map[cpt] = f"${v:.2f}"
                                break
                if rate_map:
                    ctx["contracts"][payer] = rate_map
    except Exception as exc:
        print(f"[Appeal] Failed to fetch contracts: {exc}")

    return ctx


def _lookup_contracted_rates(ctx: dict, payer_name: str, cpt_codes: str) -> str:
    """Build contracted rate info string from provider context for given payer/CPTs."""
    if not payer_name or not cpt_codes:
        return ""
    payer_rates = ctx["contracts"].get(payer_name, {})
    if not payer_rates:
        return ""
    info_parts = []
    for cpt, rate in payer_rates.items():
        if cpt in cpt_codes:
            info_parts.append(f"Contracted rate for CPT {cpt}: {rate}")
    return ". ".join(info_parts) + "." if info_parts else ""


def _build_prompt_data(denial: dict, ctx: dict) -> str:
    """Build the JSON prompt data for Claude, merging denial data with provider context."""
    practice_name = denial.get("practice_name") or ctx["practice_name"]
    npi = denial.get("npi") or ctx["npi"]
    practice_address = denial.get("practice_address") or ctx["practice_address"]
    billing_contact = ctx["billing_contact"] or practice_name

    contracted_rate_info = _lookup_contracted_rates(
        ctx, denial.get("payer_name", ""), denial.get("cpt_code", "")
    )

    return json.dumps({
        "claim_id": denial.get("claim_id", ""),
        "denial_code": denial.get("denial_code", ""),
        "cpt_code": denial.get("cpt_code", ""),
        "billed_amount": denial.get("billed_amount", 0),
        "payer_name": denial.get("payer_name", ""),
        "date_of_service": denial.get("date_of_service", ""),
        "practice_name": practice_name,
        "practice_address": practice_address,
        "billing_contact": billing_contact,
        "npi": npi,
        "patient_name": denial.get("patient_name", ""),
        "contracted_rate_info": contracted_rate_info or None,
    })


@router.post("/generate-appeal")
async def generate_appeal(req: GenerateAppealRequest, request: Request):
    """Generate a formal appeal letter for a denied or underpaid claim."""
    user = _get_authenticated_user(request)

    # Fetch profile + all contracts once
    ctx = _fetch_provider_context(str(user.id))

    denial_data = {
        "claim_id": req.claim_id,
        "denial_code": req.denial_code,
        "cpt_code": req.cpt_code,
        "billed_amount": req.billed_amount,
        "payer_name": req.payer_name,
        "date_of_service": req.date_of_service,
        "practice_name": req.practice_name,
        "practice_address": req.practice_address,
        "npi": req.npi,
        "patient_name": req.patient_name,
    }
    prompt_data = _build_prompt_data(denial_data, ctx)

    practice_name = req.practice_name or ctx["practice_name"]

    result = _call_claude(
        system_prompt=APPEAL_SYSTEM_PROMPT,
        user_content=prompt_data,
        max_tokens=8192,
    )

    if not result:
        raise HTTPException(status_code=500, detail="Failed to generate appeal letter")

    # Generate PDF
    pdf_bytes = _generate_appeal_pdf(
        letter_text=result.get("letter_text", ""),
        practice_name=practice_name or "Practice",
        payer_name=req.payer_name or "Payer",
        claim_id=req.claim_id or "N/A",
    )
    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

    # Save appeal record
    sb = _get_supabase()
    appeal_record = {
        "user_id": str(user.id),
        "subscription_id": req.subscription_id,
        "audit_id": req.audit_id,
        "claim_id": req.claim_id,
        "payer_name": req.payer_name,
        "denial_code": req.denial_code,
        "cpt_code": req.cpt_code,
        "amount": req.billed_amount,
        "status": "drafted",
        "letter_text": result.get("letter_text", ""),
        "letter_html": result.get("letter_html", ""),
        "appeal_strength": result.get("appeal_strength", ""),
        "cms_references": result.get("cms_references", []),
    }

    appeal_id = None
    try:
        ins = sb.table("provider_appeals").insert(appeal_record).execute()
        if ins.data and len(ins.data) > 0:
            appeal_id = ins.data[0]["id"]
    except Exception as exc:
        print(f"[GenerateAppeal] Failed to save appeal record: {exc}")

    return {
        "appeal_id": appeal_id,
        "letter_html": result.get("letter_html", ""),
        "letter_text": result.get("letter_text", ""),
        "pdf_base64": pdf_base64,
        "cms_references": result.get("cms_references", []),
        "appeal_strength": result.get("appeal_strength", ""),
        "appeal_strength_reason": result.get("appeal_strength_reason", ""),
        "escalation_path": result.get("escalation_path", ""),
        "attach_documentation": result.get("attach_documentation", ""),
    }


@router.post("/generate-appeal-batch")
async def generate_appeal_batch(req: GenerateAppealBatchRequest, request: Request):
    """Generate appeal letters for multiple denials at once."""
    user = _get_authenticated_user(request)

    # Fetch profile + all contracts once for the entire batch
    ctx = _fetch_provider_context(str(user.id))
    practice_name = ctx["practice_name"]

    results = []
    for denial in req.denials:
        prompt_data = _build_prompt_data(denial, ctx)

        result = _call_claude(
            system_prompt=APPEAL_SYSTEM_PROMPT,
            user_content=prompt_data,
            max_tokens=8192,
        )

        if not result:
            results.append({"error": True, "claim_id": denial.get("claim_id", ""), "detail": "Generation failed"})
            continue

        # Generate PDF
        pdf_bytes = _generate_appeal_pdf(
            letter_text=result.get("letter_text", ""),
            practice_name=denial.get("practice_name") or practice_name or "Practice",
            payer_name=denial.get("payer_name", "Payer"),
            claim_id=denial.get("claim_id", "N/A"),
        )
        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

        # Save appeal record
        sb = _get_supabase()
        appeal_record = {
            "user_id": str(user.id),
            "subscription_id": req.subscription_id,
            "audit_id": req.audit_id,
            "claim_id": denial.get("claim_id", ""),
            "payer_name": denial.get("payer_name", ""),
            "denial_code": denial.get("denial_code", ""),
            "cpt_code": denial.get("cpt_code", ""),
            "amount": denial.get("billed_amount", 0),
            "status": "drafted",
            "letter_text": result.get("letter_text", ""),
            "letter_html": result.get("letter_html", ""),
            "appeal_strength": result.get("appeal_strength", ""),
            "cms_references": result.get("cms_references", []),
        }

        appeal_id = None
        try:
            ins = sb.table("provider_appeals").insert(appeal_record).execute()
            if ins.data and len(ins.data) > 0:
                appeal_id = ins.data[0]["id"]
        except Exception:
            pass

        results.append({
            "appeal_id": appeal_id,
            "claim_id": denial.get("claim_id", ""),
            "denial_code": denial.get("denial_code", ""),
            "cpt_code": denial.get("cpt_code", ""),
            "letter_html": result.get("letter_html", ""),
            "letter_text": result.get("letter_text", ""),
            "pdf_base64": pdf_base64,
            "appeal_strength": result.get("appeal_strength", ""),
            "escalation_path": result.get("escalation_path", ""),
            "attach_documentation": result.get("attach_documentation", ""),
        })

    return {"appeals": results, "count": len(results)}


@router.get("/appeals")
async def list_appeals(request: Request):
    """List all appeals for the authenticated user."""
    user = _get_authenticated_user(request)

    sb = _get_supabase()
    result = sb.table("provider_appeals") \
        .select("*") \
        .eq("user_id", str(user.id)) \
        .order("created_at", desc=True) \
        .execute()

    return {"appeals": result.data or []}


@router.post("/appeals/update-status")
async def update_appeal_status(req: UpdateAppealStatusRequest, request: Request):
    """Update the status of an appeal (drafted, sent, won, lost, pending)."""
    user = _get_authenticated_user(request)

    valid_statuses = {"drafted", "sent", "won", "lost", "pending"}
    if req.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {', '.join(valid_statuses)}")

    sb = _get_supabase()

    # Verify ownership
    row = sb.table("provider_appeals").select("user_id").eq("id", req.appeal_id).execute()
    if not row.data:
        raise HTTPException(status_code=404, detail="Appeal not found")
    if row.data[0].get("user_id") != str(user.id):
        # Also allow admin
        try:
            await _verify_admin(request)
        except Exception:
            raise HTTPException(status_code=403, detail="Not authorized")

    update_data = {"status": req.status}
    if req.outcome_amount is not None:
        update_data["outcome_amount"] = req.outcome_amount
    if req.notes is not None:
        update_data["notes"] = req.notes

    sb.table("provider_appeals").update(update_data).eq("id", req.appeal_id).execute()

    return {"status": "ok", "appeal_id": req.appeal_id, "new_status": req.status}
