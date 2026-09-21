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

## Retired and renamed fields

The register is **`docs/schema-retired-fields.md`** (one row per column: date, commit, why, whether the
data still exists, the migration that says so in the database). Both APPEALS-4/5 columns are its first
two rows.

## The rename reached no user (APPEALS-6 ITEM 3)

The `signal_denial_playbook.appeal_strength` ruling **rests on record integrity, not on user exposure.**
Established 2026-09-19 by reading every consumer: the column's only reader (`provider_audit.py`
~1552) copies it into the audit response's `denial_types[].signal_evidence`, and **no frontend file
reads `signal_evidence`**; the `/api/signal/denial-intelligence` endpoint that computed its own grade
has **no caller anywhere in the repo**. **No user was shown a misleading grade.** The field was misnamed
in the database and in two API payloads nobody rendered; that, and nothing more, is what was corrected.

## Three procedures, one vocabulary (APPEALS-6 ITEM 4)

This is a distinct finding from the one ruled on. "Appeal strength" as strong/moderate/weak (or
high/medium/low) was computed by **three unrelated procedures** in this codebase, none of which
examined appeal outcome:

1. the retired letter grade — the model's own high/medium/low for a provider letter (`provider_appeals`,
   migration 018; retired `e679913`);
2. the playbook column — a band of how many Signal claims map to the CPT's topic
   (`signal_intelligence.py populate_denial_playbook`, migration 053; renamed `032a629`);
3. the endpoint's rule — `signal_intelligence.py:349-356,367` in `/denial-intelligence`: "strong" if
   ≥3 challenging claims scored ≥4.0, "moderate" if ≥2 challenging, else "weak" — a third computation,
   under the same three words, that agreed with neither of the others (replaced by the two counts it
   actually computes, `032a629`).

**What made the recurrence likely:** the three were written months apart for three subsystems (letters,
the Signal playbook, the Signal API) by whoever was asked for "how strong is the appeal?"; the words
are the natural answer to that question, and nothing — no schema convention, no lint, no shared
definition — required the name to state the procedure. The same vocabulary already lives a fourth,
legitimate life as Signal's *consensus* categories (`signal_profiles.py:42-47`, strong/moderate/mixed/
weak about evidence consensus), which is not an appeal grade and is not touched — the hazard is the
**name** `appeal_strength`, not the adjectives.

**What now prevents a fourth:** `backend/tests/test_appeals5.py::test_no_code_file_uses_the_name_appeal_strength`
scans every non-comment line of backend and frontend code and fails on the name outside the migrations
and the retired-fields register. It prevents the *name* returning anywhere in code. It does not prevent
a new field named, say, `appeal_score` computed from something unrelated — that needs the discipline the
ruling states (name the procedure, not the conclusion) and review; no mechanical guard can check that a
name is honest.

## Provider letter date — the count stays UNESTABLISHED (APPEALS-6 ITEM 5)

The instrument is `provider_appeals.created_at` and the SQL is above. **No number exists yet;** the
window length (196 d 20.5 h) is not a count and must not be read as one. It stays unestablished until
Fred, or a session with a connection to this project's database, runs the query.

## Exposure of the unapplied-migration dependency (APPEALS-6 ITEM 1, measured 2026-09-19 ~23:05Z)

`032a629` is **live in production** — Render `parity-poc-api` (`srv-d6eh8c95pdvs73cuphug`, `autoDeploy: yes`,
branch `main`) deploy `dep-danh4najnfac738t7ra0`, status `live` since 2026-09-19T22:54:38Z — while
migration 093 is unapplied, so the served code reads `signal_claim_count_band` from a table whose column
is still `appeal_strength`. Measured exposure:

- **Writer:** `POST /api/signal/admin/populate-denial-playbook` (cron-secret admin auth). **No scheduled
  caller exists** — not in `backend/render.yaml` (one web service, one unrelated cron `parity-opps-clfs-loader`),
  not in any `.github/workflows/*.yml` (five workflows, none call it), not in any script. Only a manual
  admin call would hit it; it would fail on the INSERT (unknown column) and write nothing.
- **Reader:** `provider_audit.py` ~1530-1560 — the playbook enrichment runs inside `try: … except Exception
  as e: print("[warn] Signal playbook lookup failed …")`. The `select("*")` returns rows without the new
  key, `pb["signal_claim_count_band"]` raises `KeyError` while the dict literal is being built, before
  any `signal_evidence` is assigned; the exception is caught and printed. **The audit completes without
  `signal_evidence` (degrades; no 500, no partial state).** Nothing renders `signal_evidence`, so the
  degradation is invisible to users and visible only as a `[warn]` line in Render logs.
- **Observed:** Render request logs for `/api/provider/*` and `/api/signal/*` since the deploy: none; app
  logs matching the warning text: none. As of the measurement nothing had exercised either path.

Decision recorded 2026-09-19: **apply 093 promptly under Fred's review** rather than add a
both-names shim. A shim would re-admit the retired name to `provider_audit.py` (the guard test would need
an exemption for it), and shims that linger are a defect of their own; the exposure it would remove is a
logged degradation of an unrendered field. Until 093 is applied: the audit's Signal enrichment is
off (logged), and the admin populate endpoint must not be called.

## The enrichment had never run (APPEALS-7, 2026-09-21)

093 was applied 2026-09-21 (`20260921123941`) and verified from the database. Exercising the live
endpoint afterwards as the frontend calls it — `(CO-50, 90707)`, `adjustment_codes: "CO-50"` — returned
200 with **no `signal_evidence`**. Cause: `provider_audit.py` built its playbook filter with
`denial_codes.extend(line.adjustment_codes)` on a **string**, so PostgREST was asked for
`denial_code IN ('C','O','-','5','0')`. Nothing had matched since the lookup was wired in `f9dc071`
(2026-03-23). The KeyError that 093 closed was therefore never reachable through the endpoint either —
consistent with the 30-day logs, which hold no "playbook" line before or after the apply.

Format established before fixing (not guessed): `DenialLine.adjustment_codes: str`;
`ProviderApp.jsx:626` builds it as `(item.adjustments || []).map(a => a.code).join(", ")` over
`parse_835`'s `f"{group_code}-{reason_code}"`; `:665` and `:743` send it unchanged; the server-side
producer (`provider_audit.py:3119`) also joins with `", "`. Production `provider_analyses.result_json`
line_items: 59 of 224 carry two codes (`"CO-45, CO-97"`, `"CO-45, CO-50"`). `denial_totals`
(`provider_shared.py:469`) and `provider_trends.py:57` already parse the field with `split(",")` +
`strip()`. Fix: the same parse, one line. Test: `tests/test_appeals7_enrichment_reachable.py` goes
through `POST /api/provider/analyze-denials` with the frontend's payload and a fake reader that
honours `.in_()` values; it failed against the old code with the filter `['0','C','5','-','O']` and
passes after. The unit tests in `test_appeals5.py` had passed throughout because they hand
`_attach_signal_evidence` already-matched rows.

Output checked against its source: for `(CO-50, 90707)` all five `signal_evidence` fields are
byte-identical to playbook row `863388a3-bb30-40e8-9658-5c5c030a91df` read through the anon reader;
`payer_analytical_path` equals `DENIAL_PATH_MAP["CO-50"]`. Observed, not changed: the row is dated
2026-03-23 (pre-freeze); `challenging_evidence_summary` is four summaries joined with `", "` (reads
"…question., A 2015…"); `recommended_claims` is a JSON string, not a parsed list.

### Open items (recorded, not fixed)

- **OI-PARITY-1 — FIXED (APPEALS-8, 2026-09-21).** `signal_intelligence.py` `aggregate_denial_patterns`:
  the INSERT into `signal_topic_requests` omitted `topic_name` (`NOT NULL`, no default since migration
  005) → `23502` on every threshold-crossing pattern. Origin established from history, not inferred:
  `f03dc65` (2026-03-23) wrote `topic_name` + `description` and worked — that run flagged the two
  `provider_denial_patterns` rows that carry `topic_request_created = true` with no request behind them
  (their two request rows were later deleted; all 8 surviving requests have a `user_id`); `af25379`
  the next morning ("use correct column names") replaced those two columns with `parsed_*` and broke
  every insert since. Fix: `topic_name: parsed_title`, the human path's own convention
  (`signal_topic_request.py:286/304/324`); readers take `parsed_title` first and fall back to
  `topic_name`. Test `tests/test_appeals8_topic_request_insert.py` (fake client enforcing the NOT NULL,
  writes recorded in order) failed on the old code with the production error text and passes after;
  the exact payload was INSERTed into the live table inside a rolled-back transaction and accepted.
  The handler's "failed silently" wording stands as a misnomer (it is `logger.exception`, ERROR level).
  CONSEQUENCE ON DEPLOY: two BC BS of MD patterns (`0e14744f`, `aae38972`, count 5) are past threshold
  and unflagged; the first `analyze-denials` call after deploy creates two admin requests titled
  "Denial pattern: CO-45, CO-97 on CPT 99214" and "…CO-45, CO-4 on CPT 99213". No email is sent.
- **OI-PARITY-2** — no frontend reads `signal_evidence` (the only `grep` hit in `frontend/src` is a
  comment about `signal_evidence_updates`, a different table). The enrichment now populates the audit
  response and reaches no user. Wiring a consumer is a product decision; until it is made, the
  APPEALS-7 fix changes a response body and nothing on a page.
- **OI-PARITY-3** (found in APPEALS-8, not fixed) — `aggregate_denial_patterns` treats the comma-joined
  `adjustment_codes` string as ONE code (`if isinstance(adj_codes, str): adj_codes = [adj_codes]`,
  `signal_intelligence.py:551-553`), so `provider_denial_patterns.denial_code` holds `"CO-45, CO-97"`
  for two-code lines and the playbook coverage check (`.eq("denial_code", …)`) can never match them.
  Same family as APPEALS-7, a different site. Not changed here because splitting alters the aggregation
  key: the 32 existing pattern rows keyed on compound strings would not merge with rows keyed per code,
  and the two requests about to be auto-created carry compound titles. Decide the key first.
