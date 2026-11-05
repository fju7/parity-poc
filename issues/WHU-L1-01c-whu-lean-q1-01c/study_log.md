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
