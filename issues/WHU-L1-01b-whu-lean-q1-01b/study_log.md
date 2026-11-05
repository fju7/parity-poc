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
| 3b commit, first full draft | 2026-11-05T21:02Z | 2026-11-05T21:03Z | $0 | 0 | e95882e (pushed b2f13ec..e95882e). |
| 4 gate, dry run | 2026-11-05T21:04Z | 2026-11-05T21:04Z | $0 | 0 | narrow: 0 undetermined claims; 1 call (recency), est. $0.75. Day total $44.27 + $0.75 <= $50. |
| 4 gate run 1 of 3 (--report draft/whu-lean-q1-01b.html.gate.json) | 2026-11-05T21:04:35Z | 2026-11-05T21:05:49Z | $0.54 | 0 | recency: 5 assessed; 1 SUPERSEDED (SINEMA trial; follow-ups 2024/2025), 3 UNKNOWN (studies the page does not name). |
| 4b source_advocate run; ruling.py advocate | 2026-11-05T21:06:23Z | 2026-11-05T21:08:17Z | advocate ~$0.58; ruling $0.0573 | 0 | 4 objections: 2 MISSTATES (S001-01 SERIOUS/NARROWS deaths CI; S001-02 MINOR nevirapine), 2 LEAVES_OUT (S001-03, S001-04). Both MISSTATES ruled amend. (ruling.py advocate run without --cap by oversight; issue and day caps applied.) |
| 4c apply amends word for word; step-3 checks; applied_check; --dangling | 2026-11-05T21:08Z | 2026-11-05T21:09Z | $0 | 0 | 2 applied as ruled, 0 mismatches; 0 dangling references. |
| 4d ruling.py omissions --cap 8.8 | 2026-11-05T21:09:33Z | 2026-11-05T21:10:26Z | $0.0859 | 0 | S001-03 NOT_ADDED_BEYOND (code, lean rule 3a: the ADD's span not in the finding); S001-04 NOT_MATERIAL. 0 ADDs. |
| 4e readers' list (coverage_check render) pasted; quotations recorded; rebind | 2026-11-05T21:10Z | 2026-11-05T21:11Z | $0 | 0 | 2 lines ("Not added" and "Judged not material"); 1 counted against the declarations budget of 10. Checks clean. |
| 5 findings.py --scan; ruling.py gate --cap 8.8 | 2026-11-05T21:11Z | 2026-11-05T21:12:15Z | $0 | 0 | 4 findings. SINEMA SUPERSEDED -> lean rule 3b "newer edition disclosed" (code). 3 UNKNOWN recency findings RECENCY_UNMATCHED: not ruled. |
| 5a paste code-written newer-edition line (lean_sentences render) | 2026-11-05T21:13Z | 2026-11-05T21:13Z | $0 | 0 | BLOCKED: the line rule 3b generates from the gate's "latest known" text contains full stops ("JAMA Netw Open. 2024", "at 5.5 years. (2)"), so the page splitter cuts it. "generated sentences match the records" (splits; stale frame) and "newer editions handled" (line not on page as one sentence) STOP; "figures in held documents" STOPs on 5.5 from the same line. Pasted verbatim; not editable by the drafter (generated, protected). |
| 10 publish.py check (diagnostic) | 2026-11-05T21:13Z | 2026-11-05T21:14Z | $0 | 0 | BLOCKED. See STOP. |
| STOP | 2026-11-05T21:14Z | | | | Stopped for good. (1) A PERSON IS NEEDED: preflight "recency findings attached" STOPs on 3 RECENCY_UNMATCHED findings (f34b5e413-rec-3, -rec-4, -rec-5); findings.py leaves them "for a person to attach", and no lean path rules them. (2) The rule 3b disclosure line cannot exist on the page as one sentence, so two lean rows STOP permanently. Neither can be cleared by the drafting session within the brief. Steps 6-9a (conclusion judge, audit, changecheck) not run: the page cannot reach Ready. Premise rows "belief shown to be held" and "carried in general coverage?" also still STOP (no coverage researched). Spend on whu-lean-q1-01b: $1.19. |
