# WHU-Q1-02 (quarterly round 1) — study log

Drafting session: Claude Code. Runbook: docs/whatholdsup-process.md §4.5 + fix 3 (the frozen RUN.md does not govern this run).
Spend figures are from `spend_ledger.py --issue whu-quarterly-r1-02`. Round sum = r1-01..r1-04 + r1-judging.

| stage | start (UTC) | end (UTC) | metered spend | operator minutes | outcome |
|---|---|---|---|---|---|
| 1 premise (init, belief, kill condition, scope, evidence standard, status) | 2026-10-29T00:55:05Z | 2026-10-29T00:56:05Z | $0.00 | 0 | premise.json written before any source was opened; scope 5 out entries, evidence standard weighs measured+assessed (both rows ok). Source-dependent rows (outlets, what the sources show, direction, kill test) left for after research. |
| 2 sources (sources.json, acquire, store status, errata, sweep resolve, canary) | 2026-10-29T00:56:30Z | 2026-10-29T00:59:51Z | $0.00 | 0 | S001-S004 held (PMC CC BY copies for S001/S002; gov.uk PDF S003; White Rose repository S004). No registry record, so sweep_registry not run. errata: S002 AMENDED (corrigendum PMID 37133285, PMC8356339, DOI 10.1002/cl2.1104) — Europe PMC lists no CC licence, Crossref licence is Wiley terms: recorded as S005 NOT HELD, reason "publisher terms"; errata row "corrections not yet read" BLOCKED as a consequence (flagged for Fred). canary ok 4/4. |
| 3 draft and bind (page, scan, bind 57 rows, check, status, lint, quotations) + 3a (bibbind 8 lines, sources_shown) + 3c coverage | 2026-10-29T00:58:40Z | 2026-10-29T01:12:00Z | $0.00 | 0 | 50 bound to spans, 1 judgement, 6 on WHU records/store; check 0 flags; lint 0 STOP (attribution "Hunt" recorded); 3 quotations ok; sources_shown ok both ways; coverage: S001 19/19 used, S002 3 declared not_material (readers' list rendered, 3 of budget 10); S003/S004 no headline section found (warn). |
| 3d judgements (ruling.py judgements --cap 50) | 2026-10-29T01:12:33Z | 2026-10-29T01:13:09Z | $0.08 | 0 | 9 candidates (S001 6, S002 3); 5 relevant, 5 stated; "assessment judgements stated" ok. |

## Reading record (Claude Code, 2026-10-29)

- Search: no systematic database search. Sources were found by web search on 29 October 2026 (WebSearch queries on the question's words; Europe PMC REST search for licences; Crossref for identifiers).
- S001 read: abstract, plain-language summary, discussion (6.1-6.5) and authors' conclusions (7, 7.1, 7.2).
- S003 read: executive summary and section 4.3.2 conclusions and recommendations.
- S004 read: abstract, opening of the discussion, conclusion.
- S002 read: abstract.
- Not read: the individual studies the reviews include.
- S005 (corrigendum to S002) not held: publisher terms.
