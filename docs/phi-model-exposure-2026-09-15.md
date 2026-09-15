# PHI reaching the model — a data-flow and compliance question, lifted out of the assertion policy

**Status: for the attorney, 2026-09-15. Not tiered, not gated. No code changed by this document.**
Companion to `parity_privacy_dataflow_investigation.docx` (2026-07-03), which established for
Parity Health what is transmitted versus kept local for each input type. This note extends the
same question across products to one specific hop: **what protected health information the
backend hands to the Anthropic API**, and where the products differ.

The shared assertion policy (`docs/shared-assertion-policy-phase-a-inventory.md`) found the
divergence while inventorying model surfaces and, per the operator's amendment, reports it here
rather than treating it as an assertion class. It is not one: it is about what goes *in*, not
what comes *out*.

## 1. The finding, product by product

| product | surface | what reaches the model | control in code |
|---|---|---|---|
| **Health** | patient appeal letter (`health_analyze._generate_appeal_result`) | patient name, member id, claim number and address are replaced by tokens (`__PATIENT_NAME__` …) before serialisation; real values restored by code after generation (`_deidentify_for_model`, PH-4a) | **yes** — and a runtime guard (`evidence_retrieval._assert_no_phi`) asserts no PHI field is on any outbound evidence query |
| Health | denial analysis (`analyze_denial`) | the **full denial letter text** the patient pasted or uploaded, which by construction contains name, member id, claim number, address, diagnosis | none — this is the extraction step; the model must read the document to extract from it |
| Health | bill / EOB / SBC extraction (`analyze_text`, `analyze_image`, `analyze_sbc`; `ai_parse`, `eob_parse`) | the full document (text or image), which is PHI; `eob_parse`'s prompt explicitly asks the model to return `patient_name` and `member_id` | none; documented in the 2026-07-03 investigation as PHI-in-transit, render-and-return |
| **Provider** | appeal letter (`provider_appeals._build_prompt_data`) | **`patient_name` is sent in clear**, with claim id, date of service, CPT, billed amount, payer | **none** — no tokenisation; the Health pattern exists and is not used here |
| Provider | denial intelligence, contract analysis, coding analysis | line-level claim data (CPT, amounts, adjustment codes, claim ids); 835 line items may carry patient identifiers depending on the parser's fields | none |
| Provider / Billing | fee-schedule extraction | payer contract PDFs — no PHI by nature | n/a |
| **Employer / Broker** | claims-file column mapping (`employer_claims.py:228`, `broker.py:2098`) | the column headers **plus five raw sample rows** of the employer's claims file. The prompt promises "member_id … (we will NOT store this)"; storing and transmitting are different things, and the five rows are transmitted | none — header-only mapping would withhold the rows entirely |
| Employer / Broker | claims narrative, benchmark, scorecard, trends | aggregates computed by code; SBC plan documents (no PHI) | n/a |
| Signal | Q&A, summaries, pipeline | no PHI (published evidence) | n/a |

## 2. Why this matters for the policy work, and why it is not part of it

The provider letter and the patient letter are built to the same shape and one of them
de-identifies while the other does not. That is the same mechanism — two same-named prompts
in two modules with no shared rule — that produced the citation divergence. The assertion
policy now has a discovering test that catches a *surface* without a tier; it does not, and
should not, decide what personal data a surface may transmit. That is a compliance
determination.

## 3. Questions for counsel

1. **Provider letter, `patient_name` in clear to the API.** Anthropic's API terms and the
   practice's BAA posture: is the current flow permissible for a covered entity's business
   associate, and if not, is the Health tokenisation pattern (identifier tokens in, real values
   substituted by code after) sufficient, given the model still receives CPT, date of service
   and payer? Note the `provider_appeals` record stores the letter with the real name.
2. **Extraction steps (Health denial / bill / EOB; Employer/Broker sample rows).** These
   cannot be tokenised before the model reads them — the model is the reader. What is the
   required disclosure, and does the Employer/Broker column-mapping call need the sample rows
   at all (the operator's engineering view: no — headers plus one synthetic row would do).
3. **Retention.** Confirm the zero-retention / no-training terms in force on the API account,
   since every table above is only as safe as that commitment.

## 4. A second item for counsel — AMA CPT descriptors in customer-facing letters

Until 2026-09-15 the provider appeal prompt instructed the model to write
`CPT Code: {code} — [full AMA CPT description of this code]` in the letter header, i.e. to
reproduce the AMA's copyrighted CPT long descriptor from memory in a document the practice
sends to a payer. The instruction was removed under the assertion policy because a descriptor
recited from memory is unverifiable (it is the fifth assertion class, "coded-vocabulary
descriptor"). The licensing question survives the removal:

- The repo holds CPT descriptors in `frontend/src/lib/cptLabel.js` (~70 codes, plain-English
  labels written in-house) and in CMS rate files (short descriptors). The policy's intended
  fix is to render descriptors **from a held table** rather than from the model.
- **Question:** is reproducing CPT descriptors — AMA long descriptors, CMS short descriptors,
  or in-house paraphrases — in a customer-facing letter, PDF report or UI a licensed use under
  the practice's or CivicScale's AMA CPT licence, and does the answer differ between the
  three sources? Until answered, the letters carry the code only.

## 5. What was deliberately not done

No product's data flow was changed by the assertion-policy work. The Provider letter still
sends `patient_name`; the Employer/Broker mapping still sends five rows. Changing either is a
one-afternoon change once counsel has said what the target state is; changing them before
that would be guessing at a compliance posture.
