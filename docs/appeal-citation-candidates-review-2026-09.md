# Appeal-letter citation candidates — review packet, September 2026

> **CLOSED 2026-09-17 — not sent, review withdrawn.** Fred's ruling, 2026-09-17: appeal letters
> rest on evidence and argument only — no legal language, no statutory or regulatory citation,
> no assertion about what a law requires. The twelve rows below will not be cited by the
> product, so no attorney signature is sought. Kept as a historical record; see
> `docs/legal-review/README.md`. Escalation to an attorney is the user's judgment; the product
> may surface the facts that bear on it, never the judgment itself.

**For:** the reviewing attorney. **From:** Parity (Fred Ugast). **Why you are
reading this:** the provider appeal letter cites no law today, by design.
Before it may cite a single provision, a person qualified to judge it must
sign the row. This packet is the twelve rows drafted on 2026-09-14. Nothing
on it takes effect until `reviewed_by` and `reviewed_on` are filled in on
`backend/data/verify/candidates.json`.

## What the system already checks, and what it cannot

For every row, the software verifies — deterministically, with no model —
that the cited provision **exists** at the primary source, that its
**heading** agrees with the characterisation, that every **number** in what
the letter may assert is in the provision's text, and that it **applies** to
the payer type and state. All twelve rows pass those checks today.

What no software checks, and what your signature attests: that this is the
**right provision to cite for that denial code** — apposite, the one counsel
would reach for, not merely a true one. That judgement is the `rationale`
column below. If you disagree with a rationale, say so in the margin; the
row is withdrawn, not argued.

Context for all rows: a provider practice in **Ohio**; the letter is a
first-level appeal to the payer; `payer_type` says whether the payer is a
commercial insurer or Medicare. "May assert" is the most the letter will be
allowed to say the provision requires; the letter will be refused if it
cites the provision for anything the excerpt does not support.

## The rows

| # | denial | payer | cite | characterisation | may assert | rationale (drafted) | reviewer |
|---|---|---|---|---|---|---|---|
| 1 | CO-16 missing information | commercial | ORC § 3901.381 | third-party payers processing claims for payment | deficiency notice within 15 days of receipt; pay or deny a clean claim within 30 days (45 when documentation is needed) | 3901.381 sets both clocks a CO-16 letter needs. | ☐ |
| 2 | CO-45 exceeds fee schedule | commercial | ORC § 3901.381 | (as 1) | pay or deny within 30 days | The reprocessing clock once the fee-schedule dispute is resolved; the rate itself is contractual. | ☐ |
| 3 | CO-45 | commercial | ORC § 3901.389 | computation of interest on late claim payments | interest at 18% per annum, paid directly to the provider | Underpayment left unpaid past the 3901.381 deadline carries statutory interest. | ☐ |
| 4 | CO-97 bundled | commercial | ORC § 3901.381 | (as 1) | pay or deny within 30 days | Ohio statute says nothing about bundling; only the clock is statable. Coding argument stays generic (CPT). | ☐ |
| 5 | CO-4 modifier | commercial | ORC § 3901.381 | (as 1) | pay or deny within 30 days | As row 4. | ☐ |
| 6 | CO-50 medical necessity | commercial | ORC § 3922.01 | external review of adverse benefit determinations | a medical-necessity denial is subject to external review under Chapter 3922 | 3922.01 is the definitions section of the external-review chapter. **Question for you:** should the operative request section be cited instead, and which? | ☐ |
| 7 | CO-50 | commercial | ORC § 3901.20 | prohibition against unfair or deceptive acts in insurance | no person shall engage in an unfair or deceptive act or practice in the business of insurance | The prohibition a Department of Insurance complaint rests on. **Question:** does a bare CO-50 without disclosed criteria plausibly reach it, or is this over-reach in a first-level appeal? | ☐ |
| 8 | OA-18 duplicate | commercial | ORC § 3901.381 | (as 1) | pay or deny within 30 days | A duplicate denial of a distinct service is a denial of a clean claim. Ohio does not define "duplicate". | ☐ |
| 9 | PR-1 deductible | commercial | ORC § 3901.381 | (as 1) | pay or deny within 30 days | Only appealable if misapplied; the clock is the only statutory hook. Deductible rules are plan-document territory. | ☐ |
| 10 | CO-16 | **Medicare** | IOM 100-04 ch.1 § 80.3.2 | handling of incomplete or invalid claims | an incomplete or invalid claim is returned as unprocessable rather than denied | The MAC instruction for a claim missing information. | ☐ |
| 11 | CO-97 | **Medicare** | NCCI Policy Manual ch.I § D | evaluation and management services with a procedure | a significant and separately identifiable E&M service unrelated to the decision for a minor procedure is separately reportable with modifier 25 | The policy CO-97 edits implement; the exception is stated there verbatim. | ☐ |
| 12 | CO-4 | **Medicare** | IOM 100-04 ch.12 § 30.6.6 | E/M services during the global surgical period, modifier 25 | a significant, separately identifiable E/M service on the day of a procedure is reported with modifier 25 | The MAC instruction on modifiers 24, 25, 57. | ☐ |

## What was wrong before, so you know what this replaces

Ten letters generated on 2026-09-14 cited nineteen provisions; twelve did
not say what the letter claimed — Ohio Administrative Code 3901-1-54 cited
as the health-claims settlement rule (it is the property-and-casualty
rule), ORC 3902.11 cited as requiring disclosure of clinical criteria (it
is the coordination-of-benefits definitions), 42 CFR 410.32(a) cited as the
federal medical-necessity standard (it governs who orders diagnostic tests,
and only for Medicare). None of those can return: the software refuses any
citation not on a signed row.

## How to sign

Reply with the row numbers you approve, any you withdraw, and answers to the
two questions in rows 6 and 7. Fred fills `reviewed_by` / `reviewed_on` on
the file; the next deploy makes those rows citable and nothing else.
