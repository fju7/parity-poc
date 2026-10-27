# WHU reliability study: scorecard (draft, exploratory)

Reader-facing measures drawn from the finished study. Judged by AI models only; outside H1 and H2. Nothing here is published or deployed.

| File | What it is |
|---|---|
| `measures.py` → `measures.json` | Citation fidelity (supported / cited but not supported / uncited), overstatement, omission (Understates or Omits) and contradiction, per system, per question and in total; each judge and the two averaged; provenance in the file. Free. Before writing it checks that its failures and denominators reproduce `results/eight_ai_only.json` (and Perplexity's `results/perplexity/perplexity_ai_only.json`) in every view. |
| `takeaway_ext.py` | Spec (d)'s takeaway comparison on WHU-S05 to S08, through the spec (d) runner unchanged, on ledger issue `whu-scorecard-takeaway`. First stopped at its $12 cap (estimate $18.64 worst case); Fred raised the cap to $20 and it ran 2026-10-27: 80 calls, all parsed, $5.98. Its spend also counts toward the judging day cap and the $390 study total check. |
| `takeaway_counts.json` | Counts only from the takeaway comparison (S01-S04, and each S05-S08 question once its divergence summary is written; S06 so far): ratings per pair and judge, judge agreement, direct answers, quote check. The answer-derived text (bottom lines, differences, divergence summaries) and the builder are private: `~/Projects/whu-study-private/scorecard/`. |

ChatGPT performed no web search on WHU-S05 to S08 (deviations 2026-10-26), and its figures are labelled that way wherever they appear. Perplexity has WHU-S01 to S04 only.

The draft page mock-ups are private: `~/Projects/whu-study-private/scorecard/mockups/` (`scorecard.html`, `question-WHU-S02.html`, with an unchanged copy of `site/whatholdsup/style.css`).
