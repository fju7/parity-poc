# Appeals workstream record — APPEALS-4 / APPEALS-5 (September 2026)

Companion to `appeal-strength-assessment-design.md` and `appeal-citation-candidates-review-2026-09.md`.
This file records findings whose evidence is code archaeology or a bounded window, so that a later
reader knows what was measured, what was inferred, and what cannot be recovered.

## Provider letter date — exposure window (APPEALS-5 ITEM 2)

`_generate_appeal_pdf` printed `Date: {datetime.now().strftime('%B %d, %Y')}` — the server clock, naive,
UTC on the host — so a provider letter generated at or after 19:00 America/Chicago carried the next day's
date in its PDF header (the letter body carried whatever date the model wrote, typically the date of
service; see e679913).

- Introduced: **`b646c55`, 2026-03-06T23:17:39Z** ("Add one-click appeal drafting from denial findings",
  in `backend/routers/provider.py`); carried unchanged into `backend/routers/provider_appeals.py` by the
  refactor `6ac90a2` (2026-03-07T13:30:52Z).
- Fixed: **`e679913`, 2026-09-19T19:50:01Z** (letter date stamped once from America/Chicago, the PDF prints
  that value).
- **Window: 2026-03-06T23:17Z → 2026-09-19T19:50Z, 196 days 20.5 h.**

**Count of letters generated in the window between 00:00Z and 05:00Z (19:00–00:00 Chicago in CDT).**
The instrument is `provider_appeals` — one row per returned provider letter, `appeal_generated_at` /
`created_at` (migration 018:17,20). The query is:

```sql
SELECT count(*) AS letters_after_1900_chicago
  FROM provider_appeals
 WHERE created_at >= '2026-03-06T23:17:39Z' AND created_at < '2026-09-19T19:50:01Z'
   AND (created_at AT TIME ZONE 'UTC')::time >= '00:00' AND (created_at AT TIME ZONE 'UTC')::time < '05:00';
```

**The count is NOT stated here: it was not run.** The session that wrote this record had no connection to
this project's database, and the count must come from that instrument and no other. Two limits of the
instrument itself, to be read with the figure when it is produced: (1) until 2026-09-15 (`_save_appeal_record`)
a failed insert was printed and the letter returned anyway, so rows can be missing for letters that were
generated; (2) `created_at` is the row's insert time, a few seconds after the PDF was built — the same
UTC date for the purpose of this window. **All users are test users: the figure is a record-integrity
figure (PDFs on file whose header date is one day later than the date they were produced), not payer
exposure.**

## The gunzip defect, characterised correctly (APPEALS-5 ITEM 3)

`backend/verify/http.py`'s `HTTPError` branch (introduced `e94ddb9`, 2026-09-14T20:08Z; fixed `911a0bb`,
2026-09-17T21:36Z) read `e.read()` without decompressing. Every registry adapter goes through the same
branch — `generic.resolve` (`verify/generic.py:72` → `http.get`), `literature.resolve`, `law`, `status`,
`search` — so the defect is correctly described as **"gzip-encoded error bodies were unreadable"**, not
"error bodies were unreadable": it bit hosts that gzip their 404s (the Handle API's `{"responseCode":100}`
for a nonexistent DOI came back UNCHECKED instead of NONEXISTENT) and left hosts that do not gzip error
bodies working. `literature.resolve`'s NCT path tests `st == 404` on the status alone and was never
affected.

**The zero-verifications finding rests on code archaeology — `evidence.py` and `policy.verify_citations`
did not exist in the window — not on reading verification rows.** The appeal-letter citation verifier
landed in `911a0bb`, the same commit as the fix, so no committed letter-verification path could have run
the defective branch. The Signal publish/re-check records in the window (16 publishes 2026-09-15/16) show
every DOI/PMID resolution as EXISTS; their UNCHECKED rows are generic URLs.

**Permanently unrecoverable:** whether any uncommitted development run between 2026-09-14 and 2026-09-17
verified a fabricated DOI. `VERIFY_CACHE_DIR` was unset, no request log exists, and uncommitted runs left
no record. The defect was found by the APPEALS-3 gate tests during development; that is the only
evidence such runs happened.

## Retired and renamed fields (APPEALS-4 / APPEALS-5)

- `provider_appeals.appeal_strength` (migration 018): the model-authored letter grade high|medium|low.
  **RETIRED** as of `e679913`; no writer, reader or renderer; rows are historical and must not be read;
  not dropped. `COMMENT ON COLUMN` in **`backend/migrations/094_…` — written, LEFT UNAPPLIED.**
- `signal_denial_playbook.appeal_strength` (migration 053): NOT the letter grade; a band of how many
  Signal claims map to the CPT's topic (≥3 / 1–2 / 0). **Renamed `signal_claim_count_band`** with values
  `3_plus_claims` / `1_2_claims` / `0_claims` — `backend/migrations/093_…` — written, LEFT UNAPPLIED;
  apply BEFORE deploying the code that reads the new name. The `/api/signal/denial-intelligence`
  response likewise now carries `challenging_claim_count` and `high_score_challenging_count` (the counts it
  computes) instead of a strong/moderate/weak grade; no caller of that endpoint exists in the repo, and no
  frontend reads `signal_evidence` from the audit response, so neither value reaches a rendered surface.

There is no document in this repo that tracks retired fields. Proposed home, not created here: a
`docs/schema-retired-fields.md` with one row per column (table, column, retired-at commit, why, migration
that comments it), maintained beside the migrations — or a section in `backend/migrations/README` if one
is started. Until then this file is the record.
