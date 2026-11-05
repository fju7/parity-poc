# WHU-L1-01 (lean test, "lean + machine scope notes") — study log

Question WHU-Q1-01 asked again of lean WHU. Ledger issue whu-lean-q1-01; run cap $10. Every command run with WHU_LEAN=1.
Drafting session: Claude Code (session WHU-L1-01). No person takes part.

| stage | start (UTC) | end (UTC) | metered spend | operator minutes | outcome |
|---|---|---|---|---|---|
| 1 premise (init, belief, kill condition, scope, evidence standard; before any source opened) | 2026-11-05T02:06:40Z | 2026-11-05T02:07:12Z | $0 | 0 | premise written; status: scope declared ok, evidence standard declared ok |
| 2 sources (Europe PMC search; sources.json; acquire_sources; source_store status) | 2026-11-05T02:07:54Z | 2026-11-05T02:08:53Z | $0 | 0 | S001 (Cochrane CD012925.pub2) held from the Europe PMC CC BY-NC copy (publisher-terms rule); WHO 2019 guideline considered, not added (iris.who.int answered the PDF URL with text/html; not worked around) |
| 2b errata, sweep_sources resolve --write (no registry record held: sweep_registry not run) | 2026-11-05T02:09Z | 2026-11-05T02:09Z | $0 | 0 | S001 clean; 1 of 1 sweepable |
| 2c canary | 2026-11-05T02:09Z | 2026-11-05T02:09Z | $0 | 0 | ok, 1 of 1 round-trips |
| 1 (cont.) premise fields filled after research (carrier, what the sources show, direction, kill condition tested) | 2026-11-05T02:10:19Z | 2026-11-05T02:10:19Z | $0 | 0 | all premise rows ok; kill condition: narrowed |
| 3 draft and bind (page; bindings scan/bind/check/status; lint_claims; quotations; generated sentences pasted from lean_sentences render) | 2026-11-05T02:12:55Z | 2026-11-05T02:22Z | $0 | 0 | 31 rows: 24 bound to S001 spans, 1 judgement, 5 on committed records, 1 on the store; check 0 flags; lint warns only (2 universal claims); the question quote declared the page's own voice; access.not_read dropped from sources.json after the preflight's "claims a source could not be opened" STOP (ledger full_text_held) |
| 3a source list (bibbind proposals bound; sources_shown) | 2026-11-05T02:16Z | 2026-11-05T02:17Z | $0 | 0 | author and title lines bound; sources_shown ok both rows |
| 3c coverage | 2026-11-05T02:18Z | 2026-11-05T02:18Z | $0 | 0 | 13 units, 13 used; 0 declarations (budget 7); readers' list empty, nothing to render |
| 3d judgements (ruling.py judgements --cap 10) | 2026-11-05T02:19:56Z | 2026-11-05T02:20:03Z | $0.0089 | 0 | 2 candidates (S001 abstract conclusions), 2 relevant, 2 stated |
| 3b commit first full draft | 2026-11-05T02:23Z | 2026-11-05T02:23Z | $0 | 0 | 812c50a (pushed 325b63c..812c50a) |
| 4 gate run 1 of 3 (dry run, then factcheck_draft --report) | 2026-11-05T02:24:18Z | 2026-11-05T02:24:50Z | $0.15 | 0 | narrow gate: recency only (1 call); PASSED (narrow) |
| 4b source advocate; ruling.py advocate | 2026-11-05T02:25:03Z | 2026-11-05T02:26:11Z | $0.32 | 0 | 2 objections (S001-01 MISSTATES, S001-02 LEAVES_OUT); S001-01 ruled amend |
| 4c apply advocate ruling word for word; step-3 checks; applied_check; --dangling | 2026-11-05T02:26:30Z | 2026-11-05T02:27Z | $0 | 0 | 1 applied as ruled; 0 dangling |
| 4d ruling.py omissions | 2026-11-05T02:27:08Z | 2026-11-05T02:27:38Z | $0.07 | 0 | S001-02 ruled ADD (stroke study: adherence, systolic BP, EQ-5D) |
| 4e insert ADD after eff96cf2, bound origin omission_add; applied_check; --dangling; ruling.py dangling; apply | 2026-11-05T02:28Z | 2026-11-05T02:29Z | $0.08 | 0 | ADD inserted as ruled; 3 dangling (EQ-5D, MD, RR) ruled: 1 amend (expand RR, MD), applied word for word; then 0 dangling, 0 mismatches |
| 5 findings --scan; ruling.py gate | 2026-11-05T02:29:39Z | 2026-11-05T02:29:45Z | $0 | 0 | 0 findings, 0 rulings |
| 6 conclusion_judge; ruling.py conclusions | 2026-11-05T02:29:52Z | 2026-11-05T02:30:05Z | $0.003 | 0 | 1 judged, 0 flagged; 0 rulings |
| 7 (deviation) audit_stage --dry-run --out <scratch> --limit 100, run to read the estimate | 2026-11-05T02:30:40Z | 2026-11-05T02:31:05Z | $0.205 | 0 | the "dry run" made the real model calls (metered on whu-lean-q1-01) and wrote its run outside the issue (session scratchpad); not used for anything; recorded here as spend |
| 7 audit_stage run --cap 9.14; consistency.py audit | 2026-11-05T02:31:17Z | 2026-11-05T02:32:04Z | $0.137 | 0 | run 20261105T023117Z complete: 39 units, 26 holds, 5 holds_by_record_check, 8 not_a_correction; 0 cuts, 0 rulings, 0 to a person; consistency: no rulings to re-run |
| 7d final narrow gate --changed-since (dry run, then run 2 of 3); step 5 on it | 2026-11-05T02:33:04Z | 2026-11-05T02:33:10Z | $0 | 0 | 2 changed sentences; recency carried (fresh); PASSED (narrow); 0 findings |
