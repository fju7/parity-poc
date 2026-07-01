# Baseline generated appeal — Signatera / Cigna (2026-07-01)

This is the appeal letter Parity Health generated on 2026-07-01, **before** SESSION PH-1,
reproduced as the baseline to beat. PII de-identified consistently with `denial_source.txt`
(Linda B. Ugast → Jane A. Doe; address → 123 Main St, Wesley Chapel, FL 33543;
member ID → MEMBER-TEST-001; claim → CLAIM-TEST-0340U; ordering physician → Dr. Sample Provider).

## Known defects in this baseline (targets for PH-1 and later phases)
- **Placeholder leakage:** `[Address]`, `[City, State, ZIP]`, `[Phone]`, `[Email]`,
  `[Cigna/EviCore Mailing Address]`, `[Signature]` left unfilled — several were available
  in the denial document (patient address; eviCore appeals address).
- **Invented date:** header shows `[Date: June 23, 2026]` (neither generation date nor a
  document date).
- **Phantom enclosures:** letter states "SUPPORTING DOCUMENTATION ENCLOSED … (7 items)"
  and "Enclosures: As listed above (7 items)" — nothing is actually attached (Phase 4).
- **Unsourced evidence:** "peer-reviewed literature supports…", "Medicare has begun
  covering 0340U", "NCCN/ASCO … where applicable" — zero verifiable citations (Phase 2).

## Strengths (must NOT regress)
- Correct claim reference (CLAIM-TEST-0340U), CPT (0340U), guideline (MOL.CU.117), payer.
- Accurate deadline analysis (30-day FL Adverse Determination panel vs. 365-day standard).
- Strong "weakness" argument (FDA Breakthrough Device; evolving coverage; blanket-vs-individualized).

---

## Letter body (verbatim, de-identified)

```
Jane A. Doe
[Address]
[City, State, ZIP]
[Phone]
[Email]

Cigna Health and Life Insurance Company
c/o EviCore Healthcare — Appeals Department
[Cigna/EviCore Mailing Address]

RE: FORMAL APPEAL OF CLAIM DENIAL
Patient Name: Jane A. Doe
Claim Number: CLAIM-TEST-0340U
Procedure Code: 0340U (Signatera MRD Plasma Test)
Ordering Provider: Dr. Sample Provider / Natera Inc.
Denial Reason Code: MOL.CU.117
Date of Denial: June 22, 2026

Dear Cigna Appeals Review Department and EviCore Healthcare Medical Director:

I am writing on behalf of Jane A. Doe to formally appeal the denial of coverage for
procedure code 0340U (Signatera Molecular Residual Disease [MRD] plasma test), issued
under claim number CLAIM-TEST-0340U and denial reason code MOL.CU.117. The claim was
denied on the basis that this test is classified as Experimental, Investigational, or
Unproven (EIU) under EviCore criteria. We respectfully but firmly disagree with this
determination and request a full reconsideration.

PRIMARY ARGUMENT: THE EIU CLASSIFICATION DOES NOT REFLECT THE CURRENT STATE OF THE EVIDENCE

- The U.S. Food and Drug Administration has granted Signatera Breakthrough Device
  Designation, reflecting the FDA's own assessment that the evidence base is meaningful
  and clinically significant — not experimental.
- Peer-reviewed clinical literature supports Signatera's utility for MRD monitoring across
  multiple cancer types; tumor-informed ctDNA results are clinically actionable.
- Medicare and several major commercial insurers have begun covering procedure code 0340U
  in specific clinical contexts.
- The denial does not appear to have considered the patient's individual clinical
  circumstances — cancer diagnosis, stage, and current treatment plan.

CLINICAL CONTEXT
Dr. Sample Provider, the treating oncologist, ordered the Signatera test as a medically
necessary component of the patient's cancer management. The result will directly inform
treatment decisions.

SUPPORTING DOCUMENTATION ENCLOSED
1. Letter of Medical Necessity from Dr. Sample Provider
2. Complete oncology treatment records
3. Peer-reviewed published studies (available through Natera Inc.)
4. FDA Breakthrough Device Designation documentation
5. Relevant NCCN and/or ASCO clinical guidelines
6. Comparative coverage policies from Medicare and other insurers
7. Supplemental statement from Dr. Sample Provider

REQUEST FOR RECONSIDERATION
We respectfully request a full, individualized review by a physician reviewer with oncology
expertise, and a written determination within 30 days of receipt of this letter.

Sincerely,

Jane A. Doe
[Signature]
[Address]
[City, State, ZIP]
[Phone]
[Email]

Enclosures: As listed above (7 items)
cc: Dr. Sample Provider; Natera Inc. Provider Relations
```
