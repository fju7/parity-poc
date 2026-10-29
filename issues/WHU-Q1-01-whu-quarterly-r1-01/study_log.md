# WHU-Q1-01 (quarterly round 1) — study log

Drafting session: Claude Code. Runbook: docs/whatholdsup-process.md §4.5 plus fix 3 (the frozen RUN.md does not govern this run).
Spend is from `backend/data/spend/ledger.jsonl` for ledger issue whu-quarterly-r1-01. Operator minutes are a person's time; none was needed unless stated.

| stage | start (UTC) | end (UTC) | metered spend | operator minutes | outcome |
|---|---|---|---|---|---|
| 1 premise (belief, kill condition, scope, evidence standard) | 2026-10-29T00:04:19Z | 2026-10-29T00:04:40Z | $0.00 | 0 | scope and evidence standard written before any source was opened; premise status: scope declared ok, evidence standard declared ok |
| 2 sources (Europe PMC search, sources.json, acquire, status) | 2026-10-29T00:04:40Z | 2026-10-29T00:06:30Z | $0.00 | 0 | S001 Cochrane review CD012925.pub2 held from Europe PMC (CC BY-NC; no Wiley copy fetched); S002 WHO 2019 guideline held from WHO IRIS. NCBI Bookshelf copy of S002 answered with a reCAPTCHA page and was not used |
| 2b errata, sweep resolve (no registry record held, so no registry sweep) | 2026-10-29T00:06:30Z | 2026-10-29T00:07:00Z | $0.00 | 0 | S001 clean; S002 n/a (guideline); 2 of 2 sweepable |
| 2c canary | 2026-10-29T00:07:00Z | 2026-10-29T00:07:10Z | $0.00 | 0 | 2 of 2 round-trip |
| 1 (cont.) premise filled after reading: what the sources show, direction narrows, kill condition tested | 2026-10-29T00:07:10Z | 2026-10-29T00:08:00Z | $0.00 | 0 | all premise rows ok |
| 3 draft, scan, bind, check, lint | 2026-10-29T00:08:00Z | 2026-10-29T00:13:30Z | $0.00 | 0 | 26 rows; 23 bound to spans, 2 on the store, 1 framing; one B21 warn (store cannot evaluate "we did not read the 18 included studies") |
| 3a source list, bibbind, sources_shown | 2026-10-29T00:12:00Z | 2026-10-29T00:13:00Z | $0.00 | 0 | 6 source-list rows bound; sources shown ok both ways |
| 3c coverage | 2026-10-29T00:13:00Z | 2026-10-29T00:13:50Z | $0.00 | 0 | 13 of 13 S001 units used after two sentences were added; warn: no headline section detected in S002; 0 declarations |
| 3d ruling.py judgements --cap 50 | 2026-10-29T00:14:06Z | 2026-10-29T00:14:17Z | $0.0197 | 0 | 2 candidates, 2 relevant, 2 stated (after splitting the conclusion binding into two spans) |
| 3 (fix) case .gitignore added: the root .gitignore's study block matches WHU-P*/WHU-S* only, so this case's bindings.json, rulings/, audit/ and gate reports were not ignored; a case-level .gitignore mirrors that block (root file unchanged) | 2026-10-29T00:17:23Z | 2026-10-29T00:17:40Z | $0.00 | 0 | bindings.json and rulings/ now ignored; nothing source-quoting committed |
| 3b commit first full draft | 2026-10-29T00:17:40Z | 2026-10-29T00:19:30Z | $0.00 | 0 | d5b3193, pushed 79fab0d..d5b3193 |
| 4 gate: dry run, then factcheck_draft.py --report (gate run 1 of 3) | 2026-10-29T00:19:58Z | 2026-10-29T00:20:52Z | $0.50 | 0 | PASSED (narrow); recency 2 assessed, 0 superseded |
| 4b source_advocate.py run | 2026-10-29T00:21:01Z | 2026-10-29T00:24:10Z | $1.80 | 0 | 11 objections (S001 7, S002 4); 5 quotations still not in the held text after one re-ask |
| 4b ruling.py advocate (MISSTATES) | 2026-10-29T00:24:16Z | 2026-10-29T00:24:39Z | $0.08 | 0 | 5 ruled, 5 rejected; nothing to apply |
| 4c applied_check, --dangling | 2026-10-29T00:24:45Z | 2026-10-29T00:24:55Z | $0.00 | 0 | 0 mismatches; 0 dangling |
| 4d ruling.py omissions (LEAVES_OUT) | 2026-10-29T00:25:01Z | 2026-10-29T00:26:04Z | $0.13 | 0 | 3 ADD, 1 NOT_MATERIAL, 2 NOT_IN_SOURCE (code) |
| 4e insert 3 ADDs word for word, bind origin omission_add; quotations; readers' list rendered; applied_check, --dangling | 2026-10-29T00:26:10Z | 2026-10-29T00:28:00Z | $0.00 | 0 | 3 inserted as ruled; quotations ok; 1 declaration shown to readers |
| 5 findings.py --scan, ruling.py gate | 2026-10-29T00:28:10Z | 2026-10-29T00:28:11Z | $0.00 | 0 | 0 findings |
| 6 conclusion_judge, ruling.py conclusions | 2026-10-29T00:28:16Z | 2026-10-29T00:28:21Z | $0.00 | 0 | 0 judged (no judgement-bucket rows) |
| 7 audit_stage.py run --cap 47.48; consistency.py audit 20261029T002827Z | 2026-10-29T00:28:27Z | 2026-10-29T00:30:00Z | $0.93 | 0 | 40 units: 26 holds, 9 headings, 2 findings (both accepted rewordings), 5 HUMAN_READ_REQUIRED (protected sentences) |
| 7b apply 2 audit rewordings word for word; rebind; step-3 checks; applied_check, --dangling | 2026-10-29T00:30:10Z | 2026-10-29T00:31:40Z | $0.00 | 0 | applied; applied_check reports 1 MISMATCH: ADD "The review notes that all of the studies…" sits after its anchor, but the anchor was reworded by the accepted audit ruling (Tanzania added) and applied_check does not follow an anchor through a later ruling. Not a preflight row; recorded as a tool limit |
| 7d final narrow gate --changed-since (dry run, then run; gate run 2 of 3) | 2026-10-29T00:31:49Z | 2026-10-29T00:31:58Z | $0.00 | 0 | PASSED (narrow); 0 findings; step 5 ruled 0; step 6 re-run 0 judged |
| 8 commit and push | 2026-10-29T00:32:20Z | 2026-10-29T00:34:30Z | $0.00 | 0 | cc8d81e, pushed d5b3193..cc8d81e |
| 9 changecheck.py --before d5b3193 | 2026-10-29T00:34:40Z | 2026-10-29T00:34:41Z | $0.04 | 0 | 7 changed sentences; nothing found (no ruling needed) |
| 9a changecheck_coverage.py --first d5b3193; canary before step 10 | 2026-10-29T00:34:45Z | 2026-10-29T00:34:50Z | $0.00 | 0 | every changed sentence was read; canary 2 of 2 |
| 10 publish.py check | 2026-10-29T00:35:00Z | 2026-10-29T00:35:20Z | $0.00 | 0 | BLOCKED on one row only: "audit complete" — 5 protected sentences (u2, u3, u31, u32, u33 of audit run 20261029T002827Z) need a person's recorded read in human_reads.jsonl. Sent to Fred; run paused |
| 11 private archive (mid-run stop) | 2026-10-29T00:35:29Z | 2026-10-29T00:35:45Z | $0.00 | 0 | 25 git-ignored files copied to ~/Projects/whu-study-private/WHU-Q1-01-whu-quarterly-r1-01/20261029T003529Z/; sha256 list in private_manifest.txt |

Spend on whu-quarterly-r1-01 at the pause: $3.47 of $50 (spend_ledger.py, 36 priced calls). Round-1 total across the five ledger issues: the same $3.47 (r1-02, r1-03, r1-04 and judging had nothing recorded).
