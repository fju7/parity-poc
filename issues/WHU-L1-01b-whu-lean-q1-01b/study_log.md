# WHU-L1-01b (whu-lean-q1-01b) study log

Lean four-question test, "lean + machine scope notes". Question WHU-Q1-01, asked again. Every command run with WHU_LEAN=1.
Drafting session: Claude Code (session WHU-L1-01b). Run cap $10; day cap rule: today's ledger total + stage estimate <= $50.

| stage | start (UTC) | end (UTC) | metered spend | operator minutes | outcome |
|---|---|---|---|---|---|
| 1 premise (init, belief, kill condition, scope, evidence_standard, status) | 2026-11-05T20:51:12Z | 2026-11-05T20:51:40Z | $0 | 0 | scope declared ok; evidence standard declared ok (written before any source opened). Belief/coverage/kill-tested rows open (filled after research). |
| 2 sources (sources.json, acquire_sources, status) | 2026-11-05T20:52Z | 2026-11-05T20:56Z | $0 | 0 | S001 Cochrane review CD012925.pub2 (2025), Europe PMC PMC11975193, CC BY-NC per Europe PMC; HELD full text (XML). No Elsevier/Wiley/SAGE/NCCN publisher copy fetched. |
| 2b errata, sweep_sources resolve --write (no registry record held) | 2026-11-05T20:57Z | 2026-11-05T20:57Z | $0 | 0 | S001 clean (PMCID matched); 1 of 1 sweepable. |
| 2c canary | 2026-11-05T20:57Z | 2026-11-05T20:57Z | $0 | 0 | ok: 1 of 1 held documents round-trip their figures. |
| 3 draft, bind (scan/check/status), lint_claims, quotations | 2026-11-05T20:58Z | 2026-11-05T21:00Z | $0 | 0 | 41 rows; 35 bound to spans, 1 judgement, 0 check flags; lint 2 warns (universal-claim scope; subhead count); 1 quotation (the question, rhetorical) ok. Generated sentences pasted from lean_sentences render; check ok (5). |
| 3a source list, bibbind, sources_shown | 2026-11-05T21:00Z | 2026-11-05T21:01Z | $0 | 0 | author and title lines bound; sources_shown ok both directions. |
| 3c coverage | 2026-11-05T21:01Z | 2026-11-05T21:01Z | $0 | 0 | 13 headline units, 13 used; 0 declarations; readers' list empty. |
| 3d ruling.py judgements --cap 10 | 2026-11-05T21:01:47Z | 2026-11-05T21:01:52Z | $0.0082 | 0 | 2 candidates (abstract conclusions), 2 relevant, 2 stated. Day total before: $44.26. |
