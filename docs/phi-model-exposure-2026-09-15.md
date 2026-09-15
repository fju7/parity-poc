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

## 5. A second fact for the same pass: the letters were readable and writable with the public key

Found 2026-09-15 by the grant check the migration policy requires after every
migration (run on `provider_appeals` after migration 085), and closed the same day
by migration 086 — the operator reviewed the SQL before it was applied.

**What was exposed.** Fourteen tables carried a row-level-security policy named
"Service role full access" that was written `FOR ALL USING (true) WITH CHECK (true)`
with no `TO` clause — so it applied to every role — while the `anon` and
`authenticated` roles held the full INSERT / SELECT / UPDATE / DELETE grants
PostgreSQL gives them at table creation. The `anon` key is embedded in the
frontend bundle and is therefore in every visitor's browser. Probed with it before
the fix: `GET /rest/v1/provider_appeals` → HTTP 206, `content-range: 0-0/6` — all six
provider appeal letters, each with the patient's name in `letter_text`, readable;
and by the same policy insertable, updatable and deletable. The tables:

| table | personal data in it | rows on 2026-09-15 |
|---|---|---|
| `provider_appeals` | patient name inside `letter_text`; claim id; payer | 6 |
| `provider_analyses`, `provider_audits`, `provider_contracts` | practice-level claim and contract data | 58 / 10 / 11 |
| `provider_profiles`, `provider_subscriptions` | NPI, practice address, Stripe customer id | 4 / 5 |
| `health_users`, `health_subscriptions` | consumer email, full name, Stripe customer id | 3 / 2 |
| `employer_accounts`, `employer_users`, `employer_contributions` | employer user emails, contribution data | 1 / 4 / 150 |
| `mue_limits`, `ncci_edits`, `pharmacy_asp` | none (CMS reference data — writable by anyone was the defect) | 15,098 / 2,210,396 / 531 |

**The window.** For the provider tables the policy text was introduced by
migration 032 (`provider_tables_company_id`, committed 2026-03-12), which dropped
the correct `USING (auth.role() = 'service_role')` policy that migration 018 had
written six days earlier and recreated it as `USING (true)`; `provider_profiles`
got the same text from migration 031 the same day; `pharmacy_asp` from 039
(2026-03-14). For `health_*`, `employer_*`, `mue_limits` and `ncci_edits` no
migration file in the repository creates the table or the policy, and Supabase's
own migration history begins at 069 — so their policy's creation date is not
recoverable; the earliest row in `employer_accounts` is 2026-02-25 and in
`health_users` 2026-03-12. **Window: 2026-03-12 (provider, health), possibly as
early as 2026-02-25 (employer), until 2026-09-15 ~14:53 UTC.**

**What the logs show.** Supabase edge logs retain 90 days (earliest entry
2026-06-17 15:44 UTC). Every day from then to 2026-09-15 was queried for any
request to any of the fourteen tables whose JWT role was not `service_role`.
There is exactly one: the operator's own anon-key probe on `provider_appeals` at
2026-09-15 14:14:47 UTC. Every other request in the window came from the backend
with the service key. **Before 2026-06-17 the logs do not exist, so whether the
public key was used against these tables between 2026-03-12 and 2026-06-17 is
unknowable.** Table statistics offer weak corroboration only: `provider_appeals`
shows 7 inserts and 1 delete since the counters last reset, which is exactly the
six real letters plus the operator's 2026-09-15 probe.

**Who the affected people are.** Enumerated on 2026-09-15 (the counts are small
enough), and NOT all the operator's own: the six appeal letters and the four
provider profiles are the operator's test practices (`provider_appeals.company_id`
is the operator's provider company); but `health_users` holds **one email address
that is not the operator's** (of three), and `employer_users` holds **two that are
not the operator's** (of four; the fourth is an `example.com` placeholder). Those
three people's email addresses (and, for the health user, full name and
subscription status) were readable and writable with the public key for the
window above. The operator holds the list; it is deliberately not reproduced
here.

**Reconciling "eight letters".** The plan of record's "eight letters generated
before this change" is the count of `provider_appeal_letters` (8 rows,
2026-03-19 → 03-25, the reuse cache written on every generation); the six is
`provider_appeals` (created by migration 018 on 2026-03-06 but first written
2026-03-23, so the three 2026-03-19 letters predate it). 8 − 6 = the three
earliest letters, which exist only in the cache table. No row is missing.

**Closed by.** Migration 086: the eleven account/PHI tables are now
service-role-only (policy `TO service_role`; every privilege revoked from
`PUBLIC`, `anon`, `authenticated`); the three reference tables are read-only to
the public key. Probed after: anon GET / INSERT / DELETE on `provider_appeals` all
return HTTP 401 `permission denied`; a letter generated through the backend with
the service key still stores, with its verification record.

**Question for counsel.** Given (a) three real people's account records (email;
one full name; subscription status — no clinical data) were exposed alongside the
operator's own test data, (b) no non-service access is recorded in the retained
logs, and (c) the first three months of the window have no logs at all, does
anything in the operator's HIPAA / state-law posture require a notification to
those three people, or a record beyond this document?

## 6. What was deliberately not done

No product's data flow was changed by the assertion-policy work. The Provider letter still
sends `patient_name`; the Employer/Broker mapping still sends five rows. Changing either is a
one-afternoon change once counsel has said what the target state is; changing them before
that would be guessing at a compliance posture.
