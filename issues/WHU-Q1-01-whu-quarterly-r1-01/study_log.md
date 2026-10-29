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
