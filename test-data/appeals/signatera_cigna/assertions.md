# Signatera / Cigna — regression assertions

Machine-checkable rules for the Signatera prior-authorization denial fixture. Each rule
maps to a phase of the appeal enhancement. PH-1 rows are live now; later-phase rows are
recorded here as the target and are expected to fail until those phases land.

Inputs: `denial_source.txt` (Phase-1 input), `expected_extraction.json` (Phase-1 golden),
`baseline_appeal.md` (the letter to beat).

## PH-1 — extraction (analyze-denial → expected_extraction.json)
| # | Assertion |
|---|-----------|
| 1 | `cpt_codes == ["0340U"]` (deduplicated from the two identical denial rows) |
| 2 | `payer_guideline_id == "MOL.CU.117"` |
| 3 | `carc_rarc_code is None` (MOL.CU.117 is a payer policy ID, not a CARC/RARC) |
| 4 | `denial_category == "EIU"` |
| 5 | `pre_service is true` and `billed_amount is None` |
| 6 | `appeal_submission.fax == "866-889-8061"` |
| 7 | `appeal_submission.address` contains `"PO Box 5620"` and `"Hartford"` |
| 8 | `deadline_days_expedited == 30` and `deadline_days_standard == 365` |
| 9 | `peer_to_peer_contact == "800-792-8744"` |
| 10 | `state == "FL"` (derivable from patient_address if not stated) |
| 11 | `procedure_terms` includes `"Signatera"` |

## PH-1 — pre-generation validators (generate_appeal)
| # | Assertion |
|---|-----------|
| 12 | Final `claim_number` used in the letter `!= payer_guideline_id` (never "MOL.CU.117") |
| 13 | If `claim_number` is missing/equal-to-code, it is replaced by `"{member_id} / {YYYY-MM-DD}"` and a warning is logged |
| 14 | `cpt_codes` are deduplicated before use |

## PH-1 — post-generation validation (_validate_letter)
| # | Assertion |
|---|-----------|
| 15 | Cleaned letter contains **no** bracketed placeholder `\[[^\]]+\]` for a field we have a value for (patient_address, submission address) |
| 16 | No empty brackets remain; unresolved-placeholder lines are removed entirely |
| 17 | Any `[Date …]` placeholder is replaced with the generation date (today), not an invented date |
| 18 | `[Signature]` → `"Submitted on behalf of {patient_name}"` |
| 19 | `validation_log` is returned and lists each placeholder with an action of substituted / date_substituted / signature_substituted / line_removed |

## Phase 2 — evidence retrieval (FUTURE — expected to fail until Phase 2)
| # | Assertion |
|---|-----------|
| 20 | Evidence pack contains ≥1 PubMed citation, each verified to resolve (esearch→esummary round-trip) |
| 21 | CMS coverage lookup is attempted for `0340U` (≥0 rows; an empty result is recorded, not silently skipped) |
| 22 | `pack.gaps` records the missing ICD / cancer type |
| 23 | PHI leak test: no outbound retrieval URL contains any of `Doe`, `MEMBER-TEST-001`, `CLAIM-TEST-0340U`, `Main St` |

## Phase 3 / 4 — letter quality & package (FUTURE)
| # | Assertion |
|---|-----------|
| 24 | Every "evidence supports / Medicare covers / guidelines support" sentence carries a citation from the pack, or is replaced with an honest-absence statement |
| 25 | Enclosure reconciliation: no enclosure is listed unless it is actually attached or explicitly marked "you must obtain" |

## Baseline scorecard (what "better" must beat)
| Metric | baseline_appeal.md |
|--------|--------------------|
| Verified citations in letter | 0 |
| Leaked `[...]` placeholders | 6+ |
| Phantom enclosures | 7 |
| Submission address captured | No (was in the denial) |
| Deadline analysis correct | Yes (must not regress) |
