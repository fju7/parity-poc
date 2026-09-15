"""Provider appeal endpoints — appeal letter generation, listing, status tracking."""

from __future__ import annotations

import base64
import io
import json
import re

from fastapi import APIRouter, HTTPException, Request

from utils.citation_gate import check_letter, violations_note
from verify.allowlist import build as build_allowlist, prompt_block
from routers.provider_shared import (
    _get_supabase, _get_authenticated_user, _verify_admin,
    _call_claude, ClaudeCallError,
    GenerateAppealRequest, GenerateAppealBatchRequest, UpdateAppealStatusRequest,
)

router = APIRouter(tags=["provider"])


# ---------------------------------------------------------------------------
# Appeal Letter Generation
# ---------------------------------------------------------------------------

# 2026-09-15: the header line no longer asks for "[full AMA CPT description of
# this code]". A descriptor recited from memory is a coded-vocabulary assertion
# nothing checks; descriptors come from tables the repo holds or are omitted.
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
   CPT Code: {cpt_code}
   Billed Amount: ${billed_amount}
   Payer Reference Number: {claim_id}

2. OPENING PARAGRAPH — state the claim precisely:
   "This letter constitutes a formal first-level appeal of {payer_name}'s denial of Claim {claim_id} under denial code {denial_code}, issued on the remittance advice referenced above. The denial is without contractual or regulatory basis for the reasons set forth below."

3. BASIS FOR THE APPEAL — argue from the denial code, the claim facts and the
   documentation. Describe the payer's obligations GENERICALLY. Examples of the
   register to use:
     "under the applicable state prompt-pay requirements"
     "under the plan's own medical-necessity standard and the clinical record"
     "under standard correct-coding conventions for separately identifiable services"
     "under the coding conventions for this modifier"
     "under the applicable external-review process"

   CITATION RULE — ABSOLUTE, with one exception. The letter must NOT cite any
   statute section, code section, CFR section, USC section, administrative-code
   rule, manual chapter or section number, or policy number — UNLESS the user
   message carries a "PERMITTED CITATIONS" block, in which case you may cite
   exactly those provisions, by the exact citation string given, for exactly
   what each excerpt supports, and nothing else. No federal regulation
   section, no state code section, no manual publication or chapter number, no
   coding-manual chapter, no dotted section number, no abbreviated code
   citation of any kind. Do not name a specific act, rule or manual by its
   formal title either. Every such reference the system has
   produced has been checked against the primary source and most were wrong; a
   wrong section number in a letter to a payer is worse than none. If you feel
   the need for a citation, write the obligation in plain words instead.

   Per denial code, the argument (no section numbers):
   CO-16 (missing information): the claim as submitted, with the attached
     documentation, contains the information needed to adjudicate it; an
     administrative deficiency that has been cured is not grounds for denial.
   CO-45 (charge exceeds fee schedule): the contracted rate from
     contracted_rate_info if provided; the variance between contracted and paid.
   CO-97 (already adjudicated / bundled): the services are clinically distinct
     and separately identifiable — different site, separate encounter, distinct
     medical necessity, or the modifier that reports it.
   CO-4 (modifier inconsistent with procedure): the modifier reports the actual
     procedural circumstance, supported by the operative documentation.
   CO-50 (non-covered / medical necessity): the clinical indicators in the record
     — diagnosis, symptoms, findings — that make the service necessary; demand the
     specific written policy or criteria the denial relied on.
   OA-18 (exact duplicate): the two claims are distinct — different date, modifier,
     anatomical site, or clinical circumstance — with documentation attached.
   PR-1 (deductible): appealable only if applied incorrectly; the EOB shows the
     deductible satisfied or misapplied.

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
  "cms_references": [],
  "appeal_strength": "high|medium|low",
  "appeal_strength_reason": "Assessment including: (1) strength of legal/regulatory basis, (2) estimated resolution timeline (30/60/90 days), (3) one sentence on key documentation the practice should attach",
  "escalation_path": "Specific next steps if this first-level appeal is denied — e.g., external review, a complaint to the state insurance regulator, arbitration under the provider agreement, or the Medicare administrative appeal process — described generically, with no section numbers",
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


# There is deliberately no Signal evidence in an appeal letter.
#
# Until 2026-09-14 the letter carried a section titled "Supporting Clinical
# Evidence from Signal Intelligence": the top-scored claims of whichever
# Signal topic signal_cpt_mappings tied to the first CPT code, introduced as
# "peer-reviewed evidence, independently scored and verified". Two things
# were wrong with that. verify_sources.py had established that the claims
# were extracted from model-written summaries, with 92 of 381 source
# identifiers resolving to nothing or to a different paper -- so "verified"
# was false. And the mapping put GLP-1 trial figures into every office-visit
# appeal (99213-99215 -> glp1-drugs), whatever the visit was for. A payer
# letter is the wrong place for either. The letter now rests on the claim
# facts, the denial reason and the regulatory citations, which is what the
# rest of the prompt has always been about.
#
# The eight letters generated before this change were the operator's own
# test accounts; none was sent.


_STATE = re.compile(r"\b([A-Z]{2})\s+\d{5}(?:-\d{4})?\b")


def _letter_context(denial: dict, ctx: dict) -> tuple[str | None, str]:
    """(state, payer_type) for the allow-list: the practice's state from its
    address; Medicare/Medicaid from the payer's name, commercial otherwise."""
    addr = denial.get("practice_address") or ctx.get("practice_address") or ""
    m = _STATE.search(addr)
    payer = (denial.get("payer_name") or "").lower()
    payer_type = "medicare" if "medicare" in payer else "medicaid" if "medicaid" in payer else "commercial"
    return (m.group(1) if m else None), payer_type


SURFACE = "routers.provider_appeals::_gated_letter"


def _gated_letter(prompt_data: str, allowed=None) -> dict | None:
    """Generate the letter and refuse it if it asserts what it may not.

    The prompt forbids section numbers unless an allow-list is handed to it;
    verify.policy.check is what makes either a control rather than a
    request. It runs over EVERY string field of the model's reply -- until
    2026-09-15 only letter_text and letter_html were checked, and
    escalation_path, appeal_strength_reason, cms_references and
    attach_documentation reached the caller unexamined. `allowed` comes from
    verify/allowlist.py -- the curated rows for this state, payer and denial
    code that a reviewer has signed and that resolved, fetched and bound just
    now. It is empty today. One regeneration is allowed, with the offending
    assertions named. If that draft still fails, no letter is returned: fail
    closed to no citation, never to an unverified one. On 2026-09-14, before
    the gate, 12 of 19 provisions cited across ten letters did not say what
    the letter claimed.

    Returns the result dict with a "verification" record (verify.policy
    Verdict.to_dict) attached, or None.
    """
    from verify.policy import check, held_for_prompt
    user = prompt_data + ("\n\n" + prompt_block(allowed) if allowed else "")
    held = held_for_prompt(APPEAL_SYSTEM_PROMPT, json.loads(prompt_data))
    held.allowed = list(allowed or [])
    result = _call_claude(system_prompt=APPEAL_SYSTEM_PROMPT, user_content=user, max_tokens=8192)
    if not result:
        return None
    verdict = check(SURFACE, result, held)
    if verdict.ok:
        result["verification"] = verdict.to_dict()
        return result
    print(f"[GenerateAppeal] draft refused ({len(verdict.refusals)}); regenerating once: " + verdict.note()[:400])
    legal = [c for c in check_letter(" ".join(t for _, t in _strings(result)), allowed)]
    note = violations_note(legal) if legal else (
        "The previous draft asserted the following, which is not permitted because it is not in the "
        "claim data you were given. Rewrite the letter without them:\n  - "
        + "\n  - ".join(sorted({f.text for f in verdict.refusals})[:12]))
    retry = _call_claude(system_prompt=APPEAL_SYSTEM_PROMPT, user_content=user + "\n\n" + note, max_tokens=8192)
    if not retry:
        return None
    verdict = check(SURFACE, retry, held)
    if not verdict.ok:
        print(f"[GenerateAppeal] REFUSED: second draft still fails: " + verdict.note()[:400])
        return None
    retry["verification"] = verdict.to_dict()
    return retry


def _attach_verification_column(record: dict, result: dict) -> None:
    """The verdict is stored beside the letter (provider_appeals.verification,
    migration 085, applied 2026-09-15). It is always written. Until 2026-09-15
    this function probed for the column and silently omitted the key when it
    was absent -- which is how a deploy that lands before its migration loses
    UNCHECKED's consumer with a single print. Now the insert carries the key
    and a missing column fails the insert, and _save_appeal_record makes that
    failure the caller's problem rather than a log line."""
    record["verification"] = result.get("verification")


class AppealRecordError(RuntimeError):
    """The letter was generated but its record -- and with it the verification
    verdict -- could not be stored. Raised, never printed-and-forgotten."""


def _save_appeal_record(sb, appeal_record: dict) -> str | None:
    try:
        ins = sb.table("provider_appeals").insert(appeal_record).execute()
    except Exception as exc:
        raise AppealRecordError(f"provider_appeals insert failed: {exc}") from exc
    if not ins.data:
        raise AppealRecordError("provider_appeals insert returned no row")
    return ins.data[0]["id"]


def _strings(obj):
    from verify.policy import walk_strings
    return walk_strings(obj)


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

    # The allow-list for this letter: reviewed candidate rows for the
    # practice's state, the payer type and the denial code, resolved and
    # bound now. Empty today; a state with no reviewed rows cites nothing.
    state, payer_type = _letter_context(denial_data, ctx)
    allowed, _rejected = build_allowlist(state, payer_type, req.denial_code or "")
    try:
        result = _gated_letter(prompt_data, allowed)
    except ClaudeCallError as exc:
        raise HTTPException(status_code=502, detail=f"The model call failed; no letter was generated. ({exc})")

    if not result:
        raise HTTPException(
            status_code=502,
            detail="Could not produce a letter that does not cite unverified law. "
                   "No letter was generated; please try again.",
        )

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
        "company_id": str(user.id),
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
    _attach_verification_column(appeal_record, result)

    # Fail closed: a letter whose record (and verdict) cannot be stored is not
    # returned as if it had been. Until 2026-09-15 this printed and carried on.
    try:
        appeal_id = _save_appeal_record(sb, appeal_record)
    except AppealRecordError as exc:
        print(f"[GenerateAppeal] REFUSED: {exc}")
        raise HTTPException(status_code=500, detail="The letter was generated but could not be recorded; it was not returned. " + str(exc)[:200])

    # Persist letter for reuse
    try:
        sb.table("provider_appeal_letters").insert({
            "user_id": str(user.id),
            "payer": req.payer_name or "",
            "denial_code": req.denial_code or "",
            "cpt_code": req.cpt_code or "",
            "letter_text": result.get("letter_text", ""),
            "signal_score": None,
        }).execute()
    except Exception as exc:
        print(f"[GenerateAppeal] Failed to persist letter: {exc}")

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
        "verification": result.get("verification"),
    }


@router.get("/saved-appeal-letter")
async def get_saved_appeal_letter(
    payer: str,
    denial_code: str,
    cpt_code: str = "",
    request: Request = None,
):
    """Look up a previously generated appeal letter by payer+denial_code+cpt_code."""
    user = _get_authenticated_user(request)
    sb = _get_supabase()
    try:
        q = (
            sb.table("provider_appeal_letters")
            .select("*")
            .eq("user_id", str(user.id))
            .eq("payer", payer)
            .eq("denial_code", denial_code)
            .eq("cpt_code", cpt_code)
            .order("generated_at", desc=True)
            .limit(1)
        )
        resp = q.execute()
        if resp.data and len(resp.data) > 0:
            row = resp.data[0]
            return {"found": True, "letter_text": row["letter_text"], "generated_at": row["generated_at"]}
        return {"found": False}
    except Exception:
        return {"found": False}


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

        state, payer_type = _letter_context(denial, ctx)
        allowed, _rejected = build_allowlist(state, payer_type, denial.get("denial_code") or "")
        try:
            result = _gated_letter(prompt_data, allowed)
        except ClaudeCallError as exc:
            results.append({"error": True, "claim_id": denial.get("claim_id", ""),
                            "detail": f"No letter: the model call failed ({exc})"})
            continue

        if not result:
            results.append({"error": True, "claim_id": denial.get("claim_id", ""),
                            "detail": "No letter: could not produce one that does not cite unverified law"})
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
            "company_id": str(user.id),
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
        _attach_verification_column(appeal_record, result)

        try:
            appeal_id = _save_appeal_record(sb, appeal_record)
        except AppealRecordError as exc:
            print(f"[GenerateAppealBatch] REFUSED {denial.get('claim_id', '')}: {exc}")
            results.append({"error": True, "claim_id": denial.get("claim_id", ""),
                            "detail": "Letter generated but could not be recorded; not returned. " + str(exc)[:200]})
            continue

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
            "verification": result.get("verification"),
        })

    return {"appeals": results, "count": len(results)}


@router.get("/appeals")
async def list_appeals(request: Request):
    """List all appeals for the authenticated user."""
    user = _get_authenticated_user(request)

    sb = _get_supabase()
    result = sb.table("provider_appeals") \
        .select("*") \
        .eq("company_id", str(user.id)) \
        .order("created_at", desc=True) \
        .execute()

    return {"appeals": result.data or []}


@router.post("/appeals/update-status")
async def update_appeal_status(req: UpdateAppealStatusRequest, request: Request):
    """Update the status of an appeal (drafted, sent, won, lost, pending)."""
    user = _get_authenticated_user(request)

    valid_statuses = {"drafted", "sent", "won", "lost", "pending", "partial"}
    if req.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {', '.join(valid_statuses)}")

    sb = _get_supabase()

    # Verify ownership
    row = sb.table("provider_appeals").select("company_id").eq("id", req.appeal_id).execute()
    if not row.data:
        raise HTTPException(status_code=404, detail="Appeal not found")
    if row.data[0].get("company_id") != str(user.id):
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

    # Record outcome in provider_appeal_outcomes for the data flywheel
    if req.status in ("won", "lost", "partial"):
        try:
            appeal_row = sb.table("provider_appeals").select(
                "claim_id, cpt_code, denial_code, payer_name, company_id, created_at"
            ).eq("id", req.appeal_id).execute()
            if appeal_row.data:
                a = appeal_row.data[0]
                # Look up Signal topic for this CPT
                signal_slug = None
                first_cpt = (a.get("cpt_code") or "").split(",")[0].strip()
                if first_cpt:
                    try:
                        # corpus read via service role: outcome analytics keep the
                        # topic tag whether or not the topic is published yet
                        m = sb.table("signal_cpt_mappings").select("topic_slug").eq(
                            "cpt_code", first_cpt
                        ).limit(1).execute()
                        if m.data:
                            signal_slug = m.data[0]["topic_slug"]
                    except Exception:
                        pass

                # Compute days to resolution
                days_to_resolution = None
                if req.resolution_date and a.get("created_at"):
                    try:
                        from datetime import datetime, date
                        created = datetime.fromisoformat(a["created_at"].replace("Z", "+00:00")).date()
                        resolved = date.fromisoformat(req.resolution_date)
                        days_to_resolution = (resolved - created).days
                    except Exception:
                        pass

                outcome_map = {"won": "paid", "partial": "partial", "lost": "denied"}
                outcome_row = {
                    "appeal_id": req.appeal_id,
                    "company_id": a.get("company_id"),
                    "claim_id": a.get("claim_id"),
                    "cpt_code": a.get("cpt_code"),
                    "denial_code": a.get("denial_code"),
                    "payer": a.get("payer_name"),
                    "signal_topic_slug": signal_slug,
                    "outcome": outcome_map.get(req.status, "pending"),
                    "outcome_recorded_at": "now()",
                    "notes": req.payer_response_notes or req.notes,
                    "recovered_amount": req.recovered_amount,
                    "resolution_date": req.resolution_date,
                    "days_to_resolution": days_to_resolution,
                }
                # Remove None values to avoid overwriting defaults
                outcome_row = {k: v for k, v in outcome_row.items() if v is not None}
                sb.table("provider_appeal_outcomes").insert(outcome_row).execute()
        except Exception as exc:
            print(f"[Appeal] Outcome tracking failed (non-fatal): {exc}")

    return {"status": "ok", "appeal_id": req.appeal_id, "new_status": req.status}
