"""APPEALS-3 (Fred's ruling 2026-09-17): the gate does BOTH jobs on a letter to a payer.

  BLOCK the legal register -- regression corpus = the exact strings the APPEALS-1 audit
  quoted from the prompts, templates and UI. Every one must be refused.
  VERIFY evidence citations -- a real PMID/DOI whose record title matches the citation
  PASSES; a plausible-looking identifier that does not exist FAILS; a registry that does
  not answer leaves the citation UNVERIFIED (never a pass); the per-code clinical
  arguments carry no register and PASS.

The two strings the APPEALS-1 audit quoted that the same directive ALLOWS (naming the
Consolidated Appropriations Act as what a data request is made under, item 5) are asserted
to pass on the broker surface, and listed here so the exception is visible.

Run: venv/bin/python -m pytest backend/tests/verify/test_legal_register.py -q
The three verification tests need the network (Europe PMC / doi.org); without it they
assert UNVERIFIED, which is the documented behaviour, not a pass.
"""
import os, sys
import pytest
_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)
from verify.extract import AssertionClass as A, extract_legal_register  # noqa: E402
from verify.policy import Held, check  # noqa: E402

PROVIDER = "routers.provider_appeals::_gated_letter"
HEALTH = "routers.health_analyze::_generate_appeal_result"
BROKER = "routers.broker::generate_caa_letter"

# ---- the APPEALS-1 corpus: exact strings, with the audit's location ----------------
CORPUS = [
    # provider_appeals.py APPEAL_SYSTEM_PROMPT (pre-APPEALS-3)
    (":30", "You are a senior healthcare billing attorney and compliance officer with 20+ years of experience in payer appeals and reimbursement disputes. Generate a formal appeal letter that reads as if drafted by experienced legal counsel — precise, authoritative, and grounded in specific regulatory citations."),
    (":57", "This letter constitutes a formal first-level appeal of Aetna's denial of Claim C1 under denial code CO-16, issued on the remittance advice referenced above. The denial is without contractual or regulatory basis for the reasons set forth below."),
    (":59-66a", "under the applicable state prompt-pay requirements"),
    (":59-66b", "under the applicable external-review process"),
    (":79-80", "an administrative deficiency that has been cured is not grounds for denial."),
    (":88-89", "demand the specific written policy or criteria the denial relied on."),
    (":98", "Systematic underpayment below contracted rates constitutes a material breach of our provider participation agreement. We reserve the right to audit additional claims for similar variances and to pursue corrective action including interest on underpaid amounts as provided under our agreement."),
    (":101", "We demand reprocessing and payment of $120.00 within 30 calendar days, consistent with applicable state prompt pay statutes and the payment terms specified in our provider participation agreement."),
    (":102", "Failure to respond within this timeframe will necessitate escalation to the state Department of Insurance and/or initiation of the dispute resolution process outlined in our provider agreement."),
    (":106", "Write as experienced legal counsel — not adversarial, but leaving no doubt that the practice knows its rights and will pursue them."),
    (":122", "strength of legal/regulatory basis"),
    (":123", "external review, a complaint to the state insurance regulator, arbitration under the provider agreement, or the Medicare administrative appeal process"),
    # verify/allowlist.py prompt_block (removed)
    ("allowlist:78", "PERMITTED CITATIONS. You may cite ONLY the provisions below, by the exact citation string given, and only for what the excerpt supports. Any other statute, rule, CFR, manual or section number is forbidden"),
    # health_analyze.py APPEAL_SYSTEM_PROMPT (pre-APPEALS-3)
    (":697a", "The patient reserves all other appeal and external-review rights available under applicable federal and state law."),
    (":697b", "the patient is exercising their right to appeal this determination"),
    (":703", "Do not simplify medical or legal terms."),
    # broker.py (the two duty characterisations the directive removes)
    ("broker:2418", "the plan sponsor's right to its own plan's claims and cost data under the transparency provisions of the Consolidated Appropriations Act, 2021, and the plan fiduciaries' general duty to obtain the information needed to oversee the plan prudently."),
    ("broker:2454", "This letter constitutes a formal request for plan-level claims data and cost information under the transparency provisions of the Consolidated Appropriations Act, 2021, and in support of the plan fiduciaries' duty to obtain the information needed to oversee the plan prudently."),
    # ProviderApp.jsx UI copy (replaced)
    ("ui:1850", "This may violate state prompt-pay laws — consider filing a complaint with your state insurance commissioner."),
    ("ui:1851", "Monitor this trend and document patterns for potential prompt-pay complaints."),
    ("landing:337", "generates an attorney-grade appeal letter"),
]

# The audit quoted these two as well; the same directive (item 5) allows naming the Act as
# what a data request is made under. They must PASS on the broker surface.
ALLOWED_BY_RULING = [
    ("broker:2414", "drafting a claims-data request letter on behalf of a plan sponsor, made under the transparency provisions of the Consolidated Appropriations Act, 2021 (CAA)."),
    ("broker:2447", "RE: Request for Plan Claims Data and Cost Information under the Consolidated Appropriations Act, 2021"),
]

# The per-code arguments of the rewritten provider prompt, as a letter would state them.
CLINICAL_ARGUMENTS = [
    "The information the denial lists as missing -- the referring provider's NPI -- is on the attached corrected claim form, and the claim can be adjudicated with it.",
    "Our current executed provider agreement sets the rate for CPT 99214 at $142.00; the remittance shows $98.50 paid. The difference is $43.50 per line.",
    "The two services were performed at different anatomical sites in the same session, as the operative note of 2025-01-05 records; modifier 59 reports that circumstance.",
    "Modifier 22 reports the additional operative time documented in the procedure note: 190 minutes against the 95 minutes typical for this procedure.",
    "The clinical indicators recorded in the encounter note -- persistent symptoms after eight weeks of first-line therapy, and the imaging findings of 2025-01-02 -- are the basis for the service. Please send the written criteria applied in this denial and the specific criterion found unmet.",
    "The two claims are for different dates of service, 2025-01-05 and 2025-01-12, each with its own encounter note attached.",
    "The EOB shows the annual deductible was met on 2024-11-30; this claim's date of service is 2025-01-05 and the deductible was applied again.",
    "Please respond by 30 calendar days from the date of this letter. Please direct all correspondence regarding this appeal to Main Street Family Practice at 1 Main St, Columbus OH 43215.",
]


@pytest.mark.parametrize("loc,text", CORPUS, ids=[c[0] for c in CORPUS])
def test_every_audit_string_is_refused_as_legal_register(loc, text):
    hits = extract_legal_register(text)
    assert hits, f"{loc}: nothing in the register lexicon matched: {text!r}"
    v = check(PROVIDER, {"letter_text": text}, Held())
    assert not v.ok and any(f.cls is A.LEGAL_REGISTER for f in v.refusals), f"{loc}: gate passed {text!r}"


@pytest.mark.parametrize("loc,text", ALLOWED_BY_RULING, ids=[c[0] for c in ALLOWED_BY_RULING])
def test_naming_the_act_as_the_basis_of_a_data_request_passes_on_the_broker_surface(loc, text):
    v = check(BROKER, {"letter": text}, Held(named_ok={"caa"}))
    assert v.ok, v.note()


@pytest.mark.parametrize("text", CLINICAL_ARGUMENTS)
def test_per_code_clinical_arguments_carry_no_register(text):
    assert extract_legal_register(text) == []


def test_per_code_clinical_arguments_pass_the_provider_gate_when_their_figures_were_handed_over():
    letter = "\n".join(CLINICAL_ARGUMENTS)
    held = Held(inputs={"cpt_code": "99214", "contracted_rate": 142.00, "paid": 98.50, "variance": 43.50,
                        "modifier": ["59", "22"], "minutes": [190, 95], "weeks": 8,
                        "dates": ["2025-01-05", "2025-01-12", "2025-01-02", "2024-11-30"],
                        "response_days": 30, "practice_address": "1 Main St, Columbus OH 43215"})
    v = check(PROVIDER, {"letter_text": letter}, held)
    assert v.ok, v.note()


# ---- verification, not blocking ------------------------------------------------------
REAL = [
    ("PMID 31562796", "Hellmann MD et al. Nivolumab plus Ipilimumab in Advanced Non-Small-Cell Lung Cancer. N Engl J Med 2019. PMID 31562796."),
    ("DOI 10.1056/NEJMoa1903765", "Im SA et al. Overall Survival with Ribociclib plus Endocrine Therapy in Breast Cancer. N Engl J Med 2019. doi:10.1056/NEJMoa1903765"),
]
FAKE = [
    "Smith J et al. Circulating tumor DNA and recurrence in stage II colon cancer. J Clin Oncol 2023. PMID 99887766.",
    "Lee K et al. Molecular residual disease monitoring after resection. Lancet Oncol 2022. doi:10.1016/S1470-2045(22)99999-9",
]


@pytest.mark.parametrize("label,ref", REAL, ids=[r[0] for r in REAL])
def test_a_real_identifier_with_a_matching_title_passes(label, ref):
    v = check(PROVIDER, {"letter_text": "References\n" + ref}, Held())
    idf = [f for f in v.findings if f.cls is A.IDENTIFIER and f.kind in ("pmid", "doi")]
    assert idf, "no identifier finding"
    if idf[0].ok is None:
        pytest.skip(f"registry unreachable -> UNVERIFIED, not a pass: {idf[0].reason}")
    assert idf[0].ok is True and "title matches" in idf[0].reason, idf[0].reason
    assert v.ok


def test_a_real_identifier_attached_to_the_wrong_title_is_refused():
    ref = "Jones A et al. Circulating tumor DNA in stage III melanoma. Ann Oncol 2020. PMID 31562796."
    v = check(PROVIDER, {"letter_text": "References\n" + ref}, Held())
    idf = [f for f in v.findings if f.cls is A.IDENTIFIER and f.kind == "pmid"][0]
    if idf.ok is None:
        pytest.skip("registry unreachable -> UNVERIFIED")
    assert idf.ok is False and "does not match" in idf.reason, idf.reason


@pytest.mark.parametrize("ref", FAKE)
def test_a_plausible_but_nonexistent_identifier_is_refused(ref):
    v = check(PROVIDER, {"letter_text": "References\n" + ref}, Held())
    idf = [f for f in v.findings if f.cls is A.IDENTIFIER and f.kind in ("pmid", "doi")][0]
    if idf.ok is None:
        pytest.skip(f"registry unreachable -> UNVERIFIED: {idf.reason}")
    assert idf.ok is False and "does not exist" in idf.reason, idf.reason
    assert not v.ok


def test_registry_silence_is_unverified_not_pass(monkeypatch):
    import verify.evidence as ev
    from verify.types import Exists, Resolution
    monkeypatch.setattr(ev, "_resolve", lambda ident: Resolution(ident, Exists.UNCHECKED, extra={"registry_unavailable": {"europepmc": "HTTP 429 after 4 attempts"}}))
    v = check(PROVIDER, {"letter_text": "References\nHellmann MD et al. Nivolumab plus Ipilimumab in Advanced NSCLC. PMID 31562796."}, Held())
    assert v.ok and not v.verified
    assert v.unchecked and "could not be verified" in v.unchecked[0].reason
