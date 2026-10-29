# WHU-Q1-02 (quarterly round 1) — study log

Drafting session: Claude Code. Runbook: docs/whatholdsup-process.md §4.5 + fix 3 (the frozen RUN.md does not govern this run).
Spend figures are from `spend_ledger.py --issue whu-quarterly-r1-02`. Round sum = r1-01..r1-04 + r1-judging.

| stage | start (UTC) | end (UTC) | metered spend | operator minutes | outcome |
|---|---|---|---|---|---|
| 1 premise (init, belief, kill condition, scope, evidence standard, status) | 2026-10-29T00:55:05Z | 2026-10-29T00:56:05Z | $0.00 | 0 | premise.json written before any source was opened; scope 5 out entries, evidence standard weighs measured+assessed (both rows ok). Source-dependent rows (outlets, what the sources show, direction, kill test) left for after research. |
| 2 sources (sources.json, acquire, store status, errata, sweep resolve, canary) | 2026-10-29T00:56:30Z | 2026-10-29T00:59:51Z | $0.00 | 0 | S001-S004 held (PMC CC BY copies for S001/S002; gov.uk PDF S003; White Rose repository S004). No registry record, so sweep_registry not run. errata: S002 AMENDED (corrigendum PMID 37133285, PMC8356339, DOI 10.1002/cl2.1104) — Europe PMC lists no CC licence, Crossref licence is Wiley terms: recorded as S005 NOT HELD, reason "publisher terms"; errata row "corrections not yet read" BLOCKED as a consequence (flagged for Fred). canary ok 4/4. |
| 3 draft and bind (page, scan, bind 57 rows, check, status, lint, quotations) + 3a (bibbind 8 lines, sources_shown) + 3c coverage | 2026-10-29T00:58:40Z | 2026-10-29T01:12:00Z | $0.00 | 0 | 50 bound to spans, 1 judgement, 6 on WHU records/store; check 0 flags; lint 0 STOP (attribution "Hunt" recorded); 3 quotations ok; sources_shown ok both ways; coverage: S001 19/19 used, S002 3 declared not_material (readers' list rendered, 3 of budget 10); S003/S004 no headline section found (warn). |
| 3d judgements (ruling.py judgements --cap 50) | 2026-10-29T01:12:33Z | 2026-10-29T01:13:09Z | $0.08 | 0 | 9 candidates (S001 6, S002 3); 5 relevant, 5 stated; "assessment judgements stated" ok. |
| 4 gate (factcheck_draft dry run, then run with --report; gate run 1 of 3) | 2026-10-29T01:15:38Z | 2026-10-29T01:16:32Z | $0.32 | 0 | dry run estimated 1 call x $0.75 (recency only); run: PASSED (narrow), nothing stale. |
| 4b source advocate + ruling.py advocate (MISSTATES) --cap 46.32 | 2026-10-29T01:16:45Z | 2026-10-29T01:23:35Z | $3.33 + $0.13 | 0 | 26 objections (S001 9, S002 6, S003 8, S004 3); 9 advocate quotations not in held text after re-ask. MISSTATES: 10 ruled, all reject; 2 on protected readers'-list sentences (S002-10 SERIOUS, S002-11 MINOR) left for a person. |
| 4c apply + checks | 2026-10-29T01:23:40Z | 2026-10-29T01:24:00Z | $0.00 | 0 | nothing to apply; applied_check 0 mismatches; --dangling 0. |
| 4d ruling.py omissions --cap 46.19 | 2026-10-29T01:24:18Z | 2026-10-29T01:25:48Z | $0.23 | 0 | 12 omission units: 4 NOT_IN_SOURCE (code), 7 ADD, 1 NOT_MATERIAL (S003 author list). |
| 4e apply ADDs + step-3 checks + applied_check + --dangling | 2026-10-29T01:26:00Z | 2026-10-29T01:36:00Z | $0.00 | 0 | 6 of 7 ADDs inserted word for word and bound origin omission_add (applied_check: 6 inserted as ruled). HELD for Fred: ADD S002@4924-5130 quotes "Over half ( n = 49) the impact evaluation come from upper‐middle income countries", which the map's own count (107 impact evaluations) contradicts and which the unheld corrigendum S005 likely corrects — 1 MISMATCH until a person rules. Readers' list now 4 declarations (budget 10). Binding check 0 flags; quotations 8 ok; --dangling 0. |
| 5 findings.py --scan + ruling.py gate --cap 45.90 | 2026-10-29T01:30:15Z | 2026-10-29T01:30:25Z | $0.00 | 0 | 0 gate findings; 0 rulings; 5a nothing to apply. |
| 6 conclusion_judge + ruling.py conclusions --cap 45.90 | 2026-10-29T01:30:31Z | 2026-10-29T01:30:45Z | $0.00 (est. $0.004) | 0 | 1 judged, 0 flagged; 0 rulings; 6a nothing to apply. |
| 7 audit — dry run (audit_stage.py run --dry-run --limit 100 --out <scratchpad>) | 2026-10-29T01:31:00Z | 2026-10-29T01:33:30Z | $2.21 | 0 | DRAFTER ERROR: run to get an estimate, but --dry-run is a real paid read of the first N units written outside the issue (docstring line 15). 71 units read, status complete, written to the session scratchpad only; it is not an audit of record and its verdicts are not used. Within caps; spend is real. |
| 7 audit (audit_stage.py run --cap 43.70) | 2026-10-29T01:34:32Z | 2026-10-29T01:34:32Z | $0.00 | 0 | NOT STARTED (day cap): estimated $2.90 (71 units x $0.0408); $2.59 left of the $25 day cap (all ledger lines, 2026-10-29). Resume after 2026-10-30T00:00Z with: py backend/scripts/whatholdsup/audit_stage.py run whu-quarterly-r1-02 --cap <min(50 - issue spend, 250 - round sum)>. |
| preflight fixes (sources.json also_called + used_for; first alias pinned to the readers'-list label so protected sentences stay word for word) + publish.py check | 2026-10-29T01:34:00Z | 2026-10-29T01:36:58Z | $0.00 | 0 | 'sources are identifiable' and 'every source is a source' now ok. Remaining STOPs: audit complete; changed sentences reviewed (both owned by steps 7-9, waiting on the day cap); advocate objections closed (S002-10, S002-11: protected, a person decides); corrections not yet read (S005, publisher terms); omission objections ruled (omissions.json reason for S003@143-358 quotes 'Kuper H, Saran A, White H', which code reads as S002 source text). |
| 11 private archive (end of day, stopped mid-run) | 2026-10-29T01:36:58Z | 2026-10-29T01:36:58Z | $0.00 | 0 | 19 git-ignored case files copied to ~/Projects/whu-study-private/WHU-Q1-02-whu-quarterly-r1-02/20261029T013646Z/; sha256 list in private_manifest.txt. STOPPED for the day: resume step 7 after 2026-10-30T00:00Z, and person items sent to Fred. |

## Reading record (Claude Code, 2026-10-29)

- Search: no systematic database search. Sources were found by web search on 29 October 2026 (WebSearch queries on the question's words; Europe PMC REST search for licences; Crossref for identifiers).
- S001 read: abstract, plain-language summary, discussion (6.1-6.5) and authors' conclusions (7, 7.1, 7.2).
- S003 read: executive summary and section 4.3.2 conclusions and recommendations.
- S004 read: abstract, opening of the discussion, conclusion.
- S002 read: abstract.
- Not read: the individual studies the reviews include.
- S005 (corrigendum to S002) not held: publisher terms.
