# WHU-S01r (post-study re-run of WHU-S01) — study log

Post-study re-run under WHU fixes 1-3 (docs/whatholdsup-process.md §4.5; docs/whu-fix3-evidence-standard.md §3). Outside the study. Drafting agent: Claude Code.

| stage | start (UTC) | end (UTC) | metered spend | operator minutes | outcome |
|---|---|---|---|---|---|
| 0 read-in (CLAUDE.md, process §0-§5 + §4.5, fix 3 §3, issue.json) | 2026-10-27T23:5xZ (approx., before clock read) | 2026-10-28T00:00:09Z | $0.00 | 0 | done; clock read 2026-10-28T00:00:09Z, on or after the paid-stage floor |
| 1 premise (belief, kill condition, scope, evidence_standard) | 2026-10-28T00:00:09Z | 2026-10-28T00:02Z | $0.00 | 0 | premise.py status: scope declared ok; evidence standard declared ok; belief-held, sources-show, direction, coverage, kill-tested rows open until research |
| 2 sources (sources.json, acquire, store status, errata, sweep, canary) | 2026-10-28T00:02Z | 2026-10-28T00:09Z | $0.00 | 0 | 12 held by script (S001-S012; S012 = correction to S002 found by errata), 0 failed; errata ok; no registry record held, so sweep_registry not run; canary ok (S011 carries no decimal figures). S013 and S014 (XTEND, TB-NEAT) added 00:17Z as not_opened so the page's "did not read" sentence rests on the store |
| 3 draft and bind (scan, bind, check, status, lint, quotations) | 2026-10-28T00:09Z | 2026-10-28T00:21Z | $0.00 | 0 | 82 rows: 75 bound to spans, 3 judgements with premises, 1 on the store, 3 protected reading/scope sentences framed for a person; 0 STOP flags; lint 0 STOP (attributions recorded in attributions.json); 3 quotations, all verbatim |
| 3a source list (bibbind, sources_shown) | 2026-10-28T00:14Z | 2026-10-28T00:21Z | $0.00 | 0 | 12 listed documents = 12 bound documents; titles matched to held wording |
| 3c coverage | 2026-10-28T00:19Z | 2026-10-28T00:21Z | $0.00 | 0 | 27 units in 7 relied-on sources: 24 used, 1 out_of_scope, 2 not_material (3 declarations of budget 10); readers' list rendered onto the page; warn: no headline section found in S006, S008, S010, S011, S012 |
| 3d fix 3 judgements (ruling.py judgements --cap 50) | 2026-10-28T00:22:00Z | 2026-10-28T00:22:40Z | $0.105 | 0 | 12 held assessment judgements, 11 relevant, 11 stated; consistency re-run 2 of 3 usable pairs agree |
