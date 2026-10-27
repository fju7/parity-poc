# WHU-S05 study log (undernutrition-tb-risk)

Kept by the drafting session (Claude Code), per study/whu-reliability/RUN.md ruling 4. Times from `date -u`; metered spend from `spend_ledger.py --issue undernutrition-tb-risk`.

| stage | start (UTC) | end (UTC) | metered spend | operator minutes | outcome |
|---|---|---|---|---|---|
| 1 premise (belief, kill condition before any source opened) | 2026-10-27T00:34:34Z | 2026-10-27T00:35:08Z | $0.00 | 0 | premise.json written; coverage (carried_by) added at 00:39Z after search; kill condition to be tested after reading |
| 2 research and source store | 2026-10-27T00:35:08Z | 2026-10-27T00:37:21Z | $0.00 | 0 | 5 sources; S001-S003 held by acquire_sources.py (PMC); S004 (Lancet RATIONS) HTTP 403 / landing page; S005 (its erratum) not identifiable; find_access: no free route (Unpaywall is_oa false) |
| 2b corrections check | 2026-10-27T00:37:21Z | 2026-10-27T00:38:10Z | $0.00 | 0 | errata.py: S001-S003 clean; S004 AMENDED (erratum PMID 39067903, added as S005), BLOCKED until S005 is held and read; sweep_sources resolve --write: 4 of 4 sweepable; no registry source, so no sweep_registry |
| 2c canary | 2026-10-27T00:38:18Z | 2026-10-27T00:38:18Z | $0.00 | 0 | 3 of 3 held documents round-trip their own figures; to run again when S004/S005 are added |
| 2a operator fetch (S004, S005) | 2026-10-27T00:39Z (clock reading taken when the request was logged; its seconds were lost when this row was rewritten) | 2026-10-27T01:15:19Z | $0.00 | 5 | Fred downloaded both to ~/Downloads (hashes d81d5e06… and 1b2ff6fb… checked); added by Claude Code with source_store.py add: S004 'Lancet article page saved as PDF from the browser, by Fred Ugast' (browser save of the article page, not the typeset PDF), held as full_text; S005 'Lancet PDF page, by Fred Ugast', refused on identity (no DOI/PMID in the page), read by Claude Code (the notice says the appendix was corrected as of July 25, 2024) and added with --force |
| 2b corrections check (rerun) | 2026-10-27T01:15:19Z | 2026-10-27T01:15:28Z | $0.00 | 0 | errata.py: all 5 checked, correction S005 held and read; sweep_sources resolve: 5 of 5 sweepable |
| 2c canary (rerun) | 2026-10-27T01:15:28Z | 2026-10-27T01:15:28Z | $0.00 | 0 | 5 of 5 held documents round-trip their own figures |
| 1 kill condition tested | 2026-10-27T01:15:30Z | 2026-10-27T01:23:51Z | $0.00 | 0 | narrowed: holds for adults (S001, S003, S004); not established for children (S001, S002); direction changed from confirms to narrows after reading |
| 3 draft and bind (B1-B24) | 2026-10-27T01:18:21Z | 2026-10-27T01:23:00Z | $0.00 | 0 | page drafted; 43 of 43 rows bound (7 proposed by autobind, rest by Claude Code), check: no span flags, 1 B19 info (disposed); lint_claims: 1 warn (23 vs 22 studies, two analyses, stated on the page); no quotations on the page, so no quotations.json |
| 3a visible source list | 2026-10-27T01:22:00Z | 2026-10-27T01:23:00Z | $0.00 | 0 | 5 entries; bibbind proposals for titles and authors confirmed; journal/year lines bound by hand; sources_shown: none used-but-unshown, none shown-but-unused |
