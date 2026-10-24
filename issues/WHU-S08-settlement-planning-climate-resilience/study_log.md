# WHU-S08 study log

Kept by the drafting session (RUN.md, ruling 4). Times are UTC, read from the clock. Metered spend is the ledger's figure for `settlement-planning-climate-resilience` after the stage minus before. Drafting is not metered.

| stage | start (UTC) | end (UTC) | metered spend | operator minutes | outcome |
|---|---|---|---|---|---|
| 1 premise | 2026-10-24T16:52:18Z | 2026-10-24T16:55:48Z | $0.00 | 0 | `premise.py init`; belief, reader and kill condition written at 16:52:41Z before any source was opened; filled after research; kill condition tested: narrowed; `premise.py status` all ok |
| 2 research and source store | 2026-10-24T16:52:41Z | 2026-10-24T16:56:30Z | $0.00 | 0 | four sources; `acquire_sources.py`: S001, S003, S004 held; S002 failed at the IOP URL (HTML, not the document) and was held from its PubMed Central copy; `source_store.py status` all ok |
| 2a operator fetches | — | — | $0.00 | 0 | not needed: every source was held by the scripts |
| 2b corrections check | 2026-10-24T16:56:35Z | 2026-10-24T16:56:50Z | $0.00 | 0 | `errata.py`: S001, S002 clean; S003 UNCHECKED (publisher deposits no updates); S004 UNCHECKABLE (working paper, no identifier). S004's journal version found by Crossref (doi 10.1093/aepp/ppz013), abstract identical, no update relation; recorded in sources.json. `sweep_sources.py resolve --write`: 3 of 4 sweepable. No registry source |
| 2c canary | 2026-10-24T16:57:01Z | 2026-10-24T16:57:03Z | $0.00 | 0 | 4 of 4 held documents round-trip their own figures |
| 3 draft and bind | 2026-10-24T16:57:10Z | 2026-10-24T17:04:00Z | $0.00 | 0 | page drafted; `bindings.py scan`, every row bound or declared (28 spans, 24 judgements with premises and steps, 7 resting on the store, 2 framing); `bindings.py check`: 0 STOP, 7 B19 warnings; `lint_claims.py`: 0 STOP (attributions recorded in attributions.json); no quoted passages, so no quotations.json. S005 (S004's journal version) registered not_opened |
| 3a visible source list | 2026-10-24T17:02:00Z | 2026-10-24T17:04:10Z | $0.00 | 0 | `<div class="sources">` written by hand; `bibbind.py` proposals applied (Siders' initials printed A.R., bound as a judgement); `sources_shown.py`: no used-but-unshown document |
