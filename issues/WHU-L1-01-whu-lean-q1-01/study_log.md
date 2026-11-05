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
