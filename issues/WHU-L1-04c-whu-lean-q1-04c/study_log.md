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
