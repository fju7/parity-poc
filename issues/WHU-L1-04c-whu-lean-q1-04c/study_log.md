# WHU-L1-04c (lean test, "lean + machine scope notes") — study log

Question WHU-Q1-04, asked again of lean WHU. Drafting session: Claude Code (session WHU-L1-04c). Every command run with WHU_LEAN=1. Run cap $10; day cap $60 (stage start only if today + estimate <= $50).

| stage | start (UTC) | end (UTC) | metered spend | operator minutes | outcome |
|---|---|---|---|---|---|
| 1 premise (init, belief, kill condition, scope, evidence standard) | 2026-11-06T13:46:22Z | 2026-11-06T13:47:02Z | $0 | 0 | scope and evidence standard ok (written before any source opened); belief-held, coverage and kill-test rows filled after looking |
| 2 sources (sources.json; acquire_sources; S003 refused as "landing" by the article test, form declared "page" with reason, re-acquired; source_store status) | 2026-11-06T13:49:38Z | 2026-11-06T13:50:05Z | $0 | 0 | 4 held full text (S001 IPCC AR6 WGIII Ch12; S002, S003 State of CDR 3rd Ed Ch7, Ch8; S004 WGIII SPM added by code); no publisher-terms source; no operator step |
| 2b errata, sweep resolve (no registry record held) | 2026-11-06T13:50:05Z | 2026-11-06T13:50:25Z | $0 | 0 | errata ok (3 lookups warn: no correction record available); S003 DOI added from the report's own citation file; report's own errata PDF read and noted |
| 2c canary | 2026-11-06T13:50:10Z | 2026-11-06T13:50:12Z | $0 | 0 | 4 of 4 round-trip |
| 3 draft and bind (page; bindings scan/bind/check/status; lint_claims; quotations; generated sentences pasted from lean_sentences render) | 2026-11-06T13:51:00Z | 2026-11-06T14:28:03Z | $0 | 0 | 118 rows, 101 bound to spans, 1 judgement, 4 store; 0 span flags; lint ok; quotations ok; 21 generated sentences match |
| 3a source list (bibbind, sources_shown) | 2026-11-06T13:58:00Z | 2026-11-06T13:59:00Z | $0 | 0 | 8 author/title lines bound; all 4 sources shown and used |
| 3c coverage (coverage_check; declare; render) | 2026-11-06T14:01:00Z | 2026-11-06T14:28:03Z | $0 | 0 | 144 units: 139 used, 2 already stated, 3 declared not_material (figure text); readers' list rendered; S002/S003 no headline structure (warn) |
| 3d judgements (ruling.py judgements --cap 10) | 2026-11-06T14:05:33Z | 2026-11-06T14:14:37Z | $1.4520 | 0 | 115 candidates, 31 relevant (1 treated relevant by code, unverified); page extended: 25 stated with certainty terms, 6 declared not_material; row ok; declarations 9 of budget 10 |
| 3b commit first full draft | 2026-11-06T14:28:00Z | 2026-11-06T14:29:00Z | $0 | 0 | 2bd2b56, pushed 39ab18c..2bd2b56 |
| 4 gate (dry run, then run 1 of 3 with --report) | 2026-11-06T14:30:23Z | 2026-11-06T14:32:01Z | $0.66 | 0 | narrow: 0 undetermined claims; recency 4 assessed: S002 SUPERSEDED, S003 UNKNOWN (left to step 5 and rule 3b code) |
| 4b advocate (source_advocate run; ruling.py advocate) | 2026-11-06T14:32:24Z | 2026-11-06T14:38:01Z | $1.17 + $0.04 | 0 | 15 objections (2 MISSTATES, 13 LEAVES_OUT); S002-10 rejected, S004-14 amended |
| 4c apply amendment; step-3 checks; applied_check; --dangling | 2026-11-06T14:38:10Z | 2026-11-06T14:39:30Z | $0 | 0 | 1 applied as ruled, 0 mismatches, 0 dangling |
| 4d omissions (ruling.py omissions) | 2026-11-06T14:40:05Z | 2026-11-06T14:42:29Z | $0.31 | 0 | 5 ADD, 3 NOT_MATERIAL, 1 NOT_ADDED_BEYOND (code), 1 NOT_IN_SOURCE (code); none to a person |
| 4e insert ADDs (origin omission_add); applied_check; --dangling; three NOT_MATERIAL findings stated on the page so they convert to already stated (declarations 12 -> 9 of 10) | 2026-11-06T14:43:00Z | 2026-11-06T14:50:00Z | $0 | 0 | 5 inserted as ruled, 0 mismatches, 0 dangling; declarations ok |
| 5 findings --scan; ruling.py gate | 2026-11-06T14:47:23Z | 2026-11-06T14:47:31Z | $0 | 0 | 2 recency findings settled by code (rule 3b): S002 SUPERSEDED untied -> count line; S003 UNKNOWN -> "We could not establish whether ..." line; both pasted from lean_sentences render |
| 5a apply (regenerate lines); step-3 checks | 2026-11-06T14:48:00Z | 2026-11-06T14:50:00Z | $0 | 0 | FOUND: lint_claims row "unknowability claims searched the registries" STOPs on rule 3b's code-written UNKNOWN line (see note below) |
| 6 conclusion_judge; ruling.py conclusions | 2026-11-06T14:51:33Z | 2026-11-06T14:51:45Z | $0.004 | 0 | 1 judged, 0 flagged, 0 rulings |
| 7 audit (audit_stage run --cap 6.29); consistency audit | 2026-11-06T14:51:55Z | 2026-11-06T14:55:23Z | $0.85 | 0 | 143 units complete: 108 holds, 24 holds_by_record_check, 11 not_a_correction, 1 finding (on ADD u56, no ruling, no cut); 0 HUMAN_READ_REQUIRED; consistency: no rulings to re-run; "audit complete" ok |
| 7d final narrow gate (--changed-since, dry run then run 2 of 3); step 5 on its findings | 2026-11-06T14:57:33Z | 2026-11-06T14:58:30Z | $0 (recency carried) | 0 | same 2 recency findings, settled by code as before; page unchanged |
| 8 commit | 2026-11-06T14:59:00Z | 2026-11-06T15:00:00Z | $0 | 0 | 4762265, pushed 2bd2b56..4762265 |
| 9 changecheck --before 2bd2b56; ruling.py changecheck | 2026-11-06T15:01:30Z | 2026-11-06T15:01:55Z | $0.04 + $0.02 | 0 | 12 changed sentences, 1 CONTRADICTION (330 MtCO2 sentence), ruled reject (source states it verbatim); nothing to apply |
| 9a changecheck_coverage --first 2bd2b56 | 2026-11-06T15:02:00Z | 2026-11-06T15:02:05Z | $0 | 0 | every changed sentence read |
| 10 publish.py check | 2026-11-06T15:02:05Z | 2026-11-06T15:02:40Z | $0 | 0 | BLOCKED: one STOP only, "unknowability claims searched the registries" (lint_claims) on rule 3b's code-written line "We could not establish whether State of CDR 3rd Edition, Chapter 8 [3] has a newer edition." All post-study rows ok; "headline conclusions accounted for" and "page gate" warn |
| 11 private archive | 2026-11-06T15:04:02Z | 2026-11-06T15:04:30Z | $0 | 0 | 28 git-ignored files to ~/Projects/whu-study-private/WHU-L1-04c-whu-lean-q1-04c/20261106T150402Z/, verified; private_manifest.txt |

## Result: Not Ready, stopped for good (no drafting step can clear the last STOP)

The only STOP is a conflict between two pieces of code. Rule 3b (process doc §4.6.1, corrections after Q1-01b) settled the gate's UNKNOWN recency finding on S003 by writing the required protected line "We could not establish whether State of CDR 3rd Edition, Chapter 8 [3] has a newer edition." lint_claims.unknowability (run by publish.py check) flags any "we could not establish" sentence that names no registry or searched place, and it has no exemption for lean's generated lines (b13 and source_ledger have one; lint_claims does not). The drafting session may not edit a generated line (a hand-written protected sentence STOPs "generated sentences match the records"), may not switch editions (rule 3b), and may not change code. So the page cannot reach Ready. on this freeze. No person was needed at any step. Spend $4.60 of the $10 cap.
