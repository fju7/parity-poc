# WHU-L1-01c (lean test, "lean + machine scope notes") — study log

Run cap $10 (issue.json run_cap_usd). Day cap rule: today's ledger total + a stage's estimate <= $50 before any paid stage.
Every command run with WHU_LEAN=1. Drafting session: Claude Code (session whu-lean-q1-01c).

| stage | start (UTC) | end (UTC) | metered spend | operator minutes | outcome |
|---|---|---|---|---|---|
| 1 premise (init, belief, kill condition, scope, evidence standard, status) | 2026-11-05T22:14:27Z | 2026-11-05T22:16Z | $0 | 0 | premise.json written before any source opened; scope (5 out entries) and evidence_standard (measured + assessed) ok at 22:15:01Z; belief-coverage rows filled after research |
| 2 sources (sources.json, acquire, store status) | 2026-11-05T22:16Z | 2026-11-05T22:18Z | $0 | 0 | S001 Cochrane CD012925.pub2 via Europe PMC (CC BY-NC listed by Europe PMC; Wiley not fetched); S002 WHO 2019 guideline via WHO IRIS API (CC BY-NC-SA 3.0 IGO); both full_text_held |
| 2b errata / sweep resolve | 2026-11-05T22:18Z | 2026-11-05T22:19Z | $0 | 0 | S001 clean; S002 n/a (guideline); no trial registry record held, sweep_registry not run |
| 2c canary | 2026-11-05T22:19Z | 2026-11-05T22:19Z | $0 | 0 | ok, 2 of 2 round-trip |
| 3 draft and bind (page, bindings scan/check/status, lint_claims, quotations, generated sentences pasted from lean_sentences render) | 2026-11-05T22:20Z | 2026-11-05T22:29Z | $0 | 0 | 44 rows bound or declared; bindings check 0 flags, 0 STOP; lint 0 STOP (attribution recorded in attributions.json); 1 quotation (the question, rhetorical); lean_sentences check ok (7 generated) |
| 3a source list (bibbind, sources_shown) | 2026-11-05T22:25Z | 2026-11-05T22:27Z | $0 | 0 | 4 bibliographic lines bound from bibbind proposals, 2 citation lines bound by hand; sources_shown ok both ways |
| 3c coverage (coverage_check, render) | 2026-11-05T22:27Z | 2026-11-05T22:29Z | $0 | 0 | S001 13 headline units, 13 used (3 added to the page as bound sentences); S002 no headline section (warn); 0 declarations, readers' list empty |
| 3d judgements (ruling.py judgements --cap 10) | 2026-11-05T22:30:15Z | 2026-11-05T22:30:20Z | $0.0083 | 0 | 2 candidates (S001 abstract conclusions), 2 relevant, 2 stated on the page; row ok |
| 4 gate (dry run, then run 1 of 3 with --report) | 2026-11-05T22:33:02Z | 2026-11-05T22:33:41Z | $0.196 | 0 | narrow gate: 1 call (recency), 0 external claims, 2 recency assessed, 0 superseded or unknown; PASSED (narrow) |
| 4b advocate run + ruling.py advocate | 2026-11-05T22:33:59Z | 2026-11-05T22:36:13Z | advocate ~$0.66 (see ledger) + rulings $0.054 | 0 | 5 items (S001: 2 MISSTATES, 2 LEAVES_OUT; S002: 1 LEAVES_OUT); S001-01 no merit; S001-02 merit yes, verdict sentence replaced word for word |
| 4c apply + step-3 checks, applied_check, --dangling | 2026-11-05T22:36Z | 2026-11-05T22:37Z | $0 | 0 | 1 applied as ruled, 0 mismatches, 0 dangling |
| 4d ruling.py omissions | 2026-11-05T22:37:18Z | 2026-11-05T22:38:20Z | $0.104 | 0 | S001-04 NOT_MATERIAL (readers' list); S001-03 NOT_ADDED_BEYOND by code (readers' list, "Not added" line); S002-05 ADD |
| 4e insert ADD, readers' list rendered and pasted, applied_check, --dangling | 2026-11-05T22:38Z | 2026-11-05T22:41Z | $0 | 0 | 1 ADD inserted after the named sentence, bound origin omission_add; 1 inserted as ruled, 0 mismatches, 0 dangling; budgets: ADDs 1, declarations 1 of 10 |
| 5 findings --scan + ruling.py gate | 2026-11-05T22:39:46Z | 2026-11-05T22:39:52Z | $0 | 0 | 0 gate findings; 0 rulings |
| 6 conclusion_judge + ruling.py conclusions | 2026-11-05T22:39:59Z | 2026-11-05T22:40:11Z | ~$0.008 | 0 | 2 judged, 0 flagged; 0 rulings |
| 7 audit (audit_stage run --cap 8.96; dry run est $1.90) | 2026-11-05T22:40:22Z | 2026-11-05T22:41:24Z | $0.291 | 0 | complete: 61 units, 39 holds, 10 holds_by_record_check, 12 not_a_correction (headings); 0 cuts, 0 rulings, 0 HUMAN_READ_REQUIRED; second read 5, 0 findings |
| 7 consistency.py audit 20261105T224022Z | 2026-11-05T22:41:40Z | 2026-11-05T22:41:40Z | $0 | 0 | "no rulings" in the run (exit 1): nothing to re-check |
| 7a-7c person reads / apply / re-audit | — | — | $0 | 0 | none needed: no sentence for a person, nothing to apply |
| 7d final narrow gate (dry run, then run 2 of 3, --changed-since gate_1) | 2026-11-05T22:42:42Z | 2026-11-05T22:42:58Z | $0 (recency carried, 0d old) | 0 | 5 changed sentences, 3 new quotations; PASSED (narrow); findings 0; ruling.py gate 0 |
| 8 commit (bcf19f3) | 2026-11-05T22:44Z | 2026-11-05T22:44Z | $0 | 0 | pushed 619bf7b..bcf19f3 |
| 9 changecheck --before 619bf7b + ruling.py changecheck | 2026-11-05T22:45:23Z | 2026-11-05T22:46:20Z | changecheck ~$0.04 + rulings $0.070 | 0 | 5 changed sentences read; 2 findings (CONTRADICTION, OURS) on the verdict sentence; ruled "amend"; applied word for word; applied_check 0 mismatches, 0 dangling |
| 5-7d repeated after the 9 amendment | 2026-11-05T22:47:21Z | 2026-11-05T22:48:17Z | audit $0.060; gate $0 (recency carried) | 0 | 0 gate findings; conclusion judge 1 judged, 0 flagged; re-audit complete (42 carried, 8 holds, 10 record check, 1 heading), 0 cuts, 0 rulings; final narrow gate run 3 of 3 PASSED |
| 9 changecheck --before 619bf7b (after the amendment) + ruling.py changecheck | 2026-11-05T22:50:32Z | 2026-11-05T22:51:02Z | changecheck ~$0.04 + rulings $0.042 | 0 | 1 finding (CONTRADICTION) on the amended verdict sentence; ruled "reject" (consistency re-run agrees); page unchanged |
| 9a changecheck_coverage --first 619bf7b | 2026-11-05T22:51:10Z | 2026-11-05T22:51:10Z | $0 | 0 | 5 changed body sentences, every one read |
| 10 publish.py check (canary re-run first) | 2026-11-05T22:51Z | 2026-11-05T22:53:05Z | $0 | 0 | Ready. (0 STOP; warns only); issue spend $1.53 of $10 |
| 11 private archive | 2026-11-05T22:53:30Z | 2026-11-05T22:54Z | $0 | 0 | 36 uncommitted files (34 git-ignored + 2 untracked gate-report copies gate_1/gate_2) copied to ~/Projects/whu-study-private/WHU-L1-01c-whu-lean-q1-01c/20261105T225330Z/; sha256 list in private_manifest.txt, verified 36/36 |

Result: FINISHED, publish.py check printed `Ready.` No person was needed at any step. Gate runs 3 of 3 (runs 2 and 3 carried recency, 0 d old).
