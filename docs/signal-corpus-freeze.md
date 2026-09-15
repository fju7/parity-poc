# The Signal corpus freeze

**Frozen 2026-09-14.** The `signal_*` tables in the Parity Supabase project
(`kfxxpscdwoemtzylhhhb`) are evidence for the ai-research-reliability work and
are not modified or rebuilt. This note is the register of every change dated
after the freeze that touched them, so that the dependency closure can show
what altered access and what altered content.

## What the freeze holds

`scripts/signal/verify_sources.py`, full run 2026-09-14
(snapshot: `backend/scripts/signal/output/verify_sources_2026-09-14.json`):

| verdict | sources |
|---|---|
| NEVER_FETCHED — `content_text` is a model summary, never the document | 288 |
| FABRICATED_IDENTIFIER — DOI/NCT/PMID resolves to nothing | 59 |
| WRONG_DOCUMENT — identifier resolves to a paper sharing no distinctive title word with ours | 33 |
| NO_CONTENT | 1 |
| **total** | **381** |

Every one of the 11 `signal_issues` rows has `status = 'draft'`.

## Post-freeze changes, in order

| date | change | rows | columns | access | where |
|---|---|---|---|---|---|
| 2026-09-14 (applied ~20:50 UTC by the operator in the Parity SQL editor; confirmed by `pg_policies` and by anon reading 0 rows from every corpus table while the service role reads all) | Migration 078: SELECT policies on `signal_issues`, `signal_sources`, `signal_claims`, `signal_claim_sources`, `signal_claim_scores`, `signal_claim_composites`, `signal_consensus`, `signal_summaries`, `signal_evidence_updates`, `signal_denial_playbook` replaced with `status = 'published'` gates; RLS enabled on `signal_cpt_mappings` with the same gate; `signal_topic_counts` view set `security_invoker`; a COMMENT on `signal_issues.status`. Ruled not a breach by the operator: catalog metadata only. | 0 | 0 | **yes** — anon/authenticated see nothing until a topic is published | `backend/migrations/078_signal_published_gate.sql` |
| 2026-09-14 | Migration 079: three rows deleted from `signal_cpt_mappings` (0537T, 0538T, 81479 → crispr-gene-therapy). Product configuration seeded by migration 046, not evidence. Operator-directed. | **3 deleted** | 0 | no | `backend/migrations/079_cpt_mappings_misapplied.sql` |

| 2026-09-14 | Migration 081: two identifiers in `signal_sources` corrected on four rows, fixing forward — Jain 2015 `10.1001/jama.2015.1534` (nonexistent) → `10.1001/jama.2015.3077`; Honda 2005 `10.1111/j.1469-8749.2005.tb01095.x` and `…tb01215.x` (a gastrostomy paper and a botulinum paper) → `10.1111/j.1469-7610.2005.01425.x`. Found by exact-title lookup, read back. Curator: Claude Opus 5 on the operator's direction. The snapshot and the mmr record at gate 2b84a4a keep the wrong values. | **4 updated** (url column) | 0 | no | `backend/migrations/081_signal_sources_two_identifiers.sql` |

| 2026-09-14 | Migration 082: seven `signal_claims.claim_text` values corrected, fixing forward — "650,000" → "657,461" (Hviid) ×4, "530,000" → "537,303" (Madsen) ×2, "1.2 million" → "1,256,407" (Taylor 2014). Truncations of the source's figure; FIGURE was not loosened. Old text preserved in `082_signal_claims_seven_truncations.json`. Curator: Claude Opus 5 on the operator's direction. | **7 updated** (claim_text) | 0 | no | `backend/migrations/082_signal_claims_seven_truncations.sql` |
| 2026-09-15 | Migration 083: the two Cochrane rows in `signal_sources` re-cited from `CD004407.pub4` (2020, superseded) to `CD004407.pub5` (22 Nov 2021, the current version), the DOI taken from Crossref's update-to on the source itself. Nine claims re-bind against pub5. Curator: Claude Opus 5 on the operator's direction. | **2 updated** (url) | 0 | no | `backend/migrations/083_signal_sources_cochrane_pub5.sql` |
| 2026-09-15 | Migration 088: five `signal_claims.plain_summary` values set to NULL on mmr-vaccine-autism (8b84dcfd, 6bbf8769, 43dc8f6d, 58b05989, 77ad8922) — the model-written summaries that the prose gate (`scripts/signal/prose_gate.py`, wired 2026-09-15) refuses because they add a figure the claim and its sources do not carry ("before 37 weeks", "over half a million US dollars", "1.0 would mean identical risk", …). Two of the five rendered; three sat on withheld claims. Refusal path, no rewrite: the claim renders without a summary. Rendered page probed headlessly after: both claims present, old summaries absent, a kept summary (Jain, "nearly 96,000") still renders. Curator: Claude Opus 5 on the operator's direction. | **5 updated** (plain_summary → NULL) | 0 | no | `backend/migrations/088_mmr_plain_summaries_refused.sql` |
| 2026-09-15 | Migration 089: one more `plain_summary` set to NULL (5b3bff25) — "six years before" was a model-computed interval (2010 − 2004); the 2010 is in the claim's own model-written source text and in Crossref's event data for the retraction, neither of which the summariser was handed. The gate had exempted it as a counting word; `verify/policy.py` now refuses a word-form figure followed by a unit (`_has_unit`). 112 of 128 mmr claims keep a summary. Curator: Claude Opus 5 on the operator's direction. | **1 updated** (plain_summary → NULL) | 0 | no | `backend/migrations/089_mmr_plain_summary_six_years.sql` |
| 2026-09-15 | Re-run of the frozen mmr record through the current binder, into scratch (not the corpus): FIGURE_BOUND 56 / IDENTITY_ONLY 40 / UNSUPPORTED 32, 0 verdict changes, 0 per-source level changes, 0 bound → unbound. The operator read stands unchanged. | 0 | 0 | no | scratch only |
| *pending* | **Human read of mmr-vaccine-autism** (design §6a) against `docs/mmr-vaccine-autism-operator-read-2026-09-14.md`. Reader: ________ · Date: ________ · Ruling: ________ | — | — | — | the flip, if any, is recorded on the row below this one |

## Operator-supplied documents (Provenance.OPERATOR_SUPPLIED) — one row each

A document a person fetched by hand enters the corpus only through
`scripts/supply_document.py` (`backend/verify/supplied.py`): the registry must
name the identifier, the file must carry the registry's title (HEADING,
mandatory, never abstains), and every other binding runs unchanged. The
operator supplies the document, never the conclusion. Each admission is a
post-freeze change and gets a row here before the topic is re-frozen. The
publication record marks the source `provenance: OPERATOR_SUPPLIED` with the
hash and the supplier, so a reader can tell which sources a human went and
got. None yet (2026-09-15).

| date | identifier | sha256 of the bytes | fetched from | supplied by | admitted / refused (HEADING evidence) | claims moved (id: old → new) |
|---|---|---|---|---|---|---|
| 2026-09-15 | `doi:10.1016/S0140-6736(10)60175-4` — Retraction—Ileal-lymphoid-nodular hyperplasia…, The Lancet 375(9713):445, Comment, 6 Feb 2010, The Editors of The Lancet | `b70a220048dc7ce64cb24fc78cf354cbf0670a2f9630dfeb0c23e5fa446c642f` | thelancet.com fulltext page (browser print, 6 pp; Elsevier serves the machine a shell) | Fred Ugast | **admitted** — registry title matches the wrapped title line, ratio 1.00 (first attempt refused at 0.75: page chrome above the title; title candidates widened to wrapped non-sentence lines). Status at freeze: `retraction_notice` for 10.1016/s0140-6736(97)11096-0. Says "incorrect" / "proven to be false" (consecutive referral, ethics approval); does not say fraud. Cites the GMC panel judgment of 28 Jan 2010 — recorded in events.json as two-source agreement with the GMC document. | 19214753 UNSUPPORTED → FIGURE_BOUND (paid by lawyers, 1998); 77c65493 → FIGURE_BOUND ("February 2010", month precision; 05143523 "May 2010" stays withheld on CHRONOLOGY); 721f53f7 → IDENTITY_ONLY; 129d0533 → IDENTITY_ONLY |
| 2026-09-15 | `doi:10.1136/bmj.c5347` — Deer B. How the case against the MMR vaccine was fixed. BMJ 2011;342:c5347, 6 Jan 2011 | `79373a9f7f1f81ae5bd6dc8a5d5663990f542a4ceb25e9b40c2ea9431444fb55` | bmj.com/content/342/bmj.c5347 (browser print, 17 pp; the machine gets 403) | Fred Ugast | **admitted** — title line ratio 1.00; status `unchanged` | 9b7a3312 → FIGURE_BOUND (12 children); 58b05989 → FIGURE_BOUND (£435,643); 1f6b6c20 → FIGURE_BOUND (12); 0eda21d2 stays withheld — SPAN: 'an elaborate fraud' is not in Deer's feature (it is Godlee's editorial; migration 090, pending review) |
| 2026-09-15 | `doi:10.1136/bmj.c7452` — Godlee F, Smith J, Marcovitch H. Wakefield's article linking MMR vaccine and autism was fraudulent. BMJ 2011;342:c7452, 6 Jan 2011 | `f58bdbdd4b9b0cbd4e38976fbd9ee813a96b19bcd92e251fcd3c91371afb6084` | bmj.com/content/342/bmj.c7452 (browser print, 5 pp) | Fred Ugast | **admitted** — title line ratio 1.00; "an elaborate fraud" appears once, character for character. Not yet a corpus source: migration 090 adds it and re-cites 0eda21d2 to it (Tier-1 review pending) | none until 090 |
| 2026-09-15 | *(no registry identifier)* — Omnibus Autism Proceeding, Autism General Order #1, 22 Nov 2002 (`omnibus_autism_20021122_0.pdf`, 27 pp, CCITT bitonal) | `f799e4edf40dd2b0f088b0cd03bea6ea718079e2492a630c6e1a6919c2e97c38` | uscfc.uscourts.gov | Fred Ugast | **UNCHECKED — no text layer** (27 extractable characters), and refused at the door: no registry answers for it. It is the 2002 order establishing the proceeding, not the 2009 Cedillo decision; would not recover those claims even OCR'd. Not OCR'd. | none |
| 2026-09-15 | *(negative control)* Warner v HHS, No. 20-225V, Special Master Horner, decision on attorneys' fees, filed 23 Jan 2024 | `33d2d0e64b45c928…` | govinfo (USCOURTS-cofc-1_20-vv-00225-1) | Fred Ugast | **refused** — a DTaP / hepatitis A fees decision, unrelated to the Omnibus proceeding and Cedillo; kept as the permanent OPERATOR_SUPPLIED negative control (`tests/verify/fixtures/supplied/`): REFUSED_HEADING under any DOI, REFUSED_REGISTRY as itself | none |
| 2026-09-15 | *(negative control)* `doi:10.1136/bmj.d1678` — BMJ correction to c7452 (competing interests), 15 Mar 2011 | `953b3c5010ca76c5…` | bmj.com/content/342/bmj.d1678 | Fred Ugast | **refused** when offered as c7452 — same title as the editorial; its own head names bmj.d1678 first (the own-DOI check exists because of this file). Supports nothing; second permanent negative control | none |
| 2026-09-15 | *(not admitted, identity confirmed)* Walker-Smith v GMC [2012] EWHC 503 (Admin), CO/7039/2010, Mitting J, 7 Mar 2012, 76 pp | `072ea8a12594eeb9…` | Fred's copy; machine-fetchable at caselaw.nationalarchives.gov.uk/ewhc/admin/2012/503 (HTTP 200) | Fred Ugast | no registry identifier, so not supplied; added as a URL source by migration 090 (pending review), linked to no claim | none until Fred decides the wording |
| 2026-09-15 | *(not admitted, identity confirmed)* GMC Fitness to Practise Panel hearing, 28 Jan 2010 (`gmc-charge-sheet.pdf` — despite the filename, the 143-page determination: Wakefield, Walker-Smith, Murch) | `3a5d06c85e1542b4…` | no URL on file | Fred Ugast | no registry answers for it; used only as the second source on the 2010-01-28 date in events.json | none |

Re-frozen after the admissions: record `20260915T190740+0000-0e25a32` — **31 of 35 sources, FIGURE_BOUND 63 / IDENTITY_ONLY 43 / UNSUPPORTED 22** (from 29 / 58 / 41 / 29); seven claims moved, none bound → unbound.

## The named-events table (CHRONOLOGY) — every row, so a wrong date is traceable

`backend/data/verify/events.json`, load-bearing on whether a claim publishes since 2026-09-14. Dates a registry can answer are not here (the Lancet 2010 retraction and the 2004 partial retraction of Wakefield 1998 resolve from Crossref/Europe PMC on the source itself).

| label | date | primary URL | reviewed_by |
|---|---|---|---|
| GMC fitness-to-practise determination (findings of fact) | 2010-01-28 | *not verified* — reviewer to supply | null |
| Wakefield erased from the UK medical register (GMC sanction) | 2010-05-24 | *not verified* — reviewer to supply | null |
| Brian Deer's BMJ series | 2011-01-05 | https://doi.org/10.1136/bmj.c5347 (resolves at Crossref; page 403s) | null |
| Omnibus Autism Proceeding test-case decisions | 2009-02-12 | *not verified* — corpus URL and two court paths 404 | null |

Not on this register because they touch no `signal_*` table: the noindex of
signal.civicscale.ai (`d75c178`), the removal of the appeal letter's Signal
section (`13ca102`), and the backend's move to an anon-key reader
(`backend/signal_reader.py`).

## How to check the freeze held

Row and column counts of every `signal_*` table, compared with the day of the
freeze, should differ only by the three rows in 079. Policies will differ (078).
Six `plain_summary` values are NULL that were not (088, 089); no other column of
`signal_claims` changed after 082.
