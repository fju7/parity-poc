# WHU reliability study: scorecard (draft, exploratory)

Reader-facing measures drawn from the finished study. Judged by AI models only; outside H1 and H2. Nothing here is published or deployed.

| File | What it is |
|---|---|
| `measures.py` → `measures.json` | Citation fidelity (supported / cited but not supported / uncited), overstatement, omission (Understates or Omits) and contradiction, per system, per question and in total; each judge and the two averaged; provenance in the file. Free. Before writing it checks that its failures and denominators reproduce `results/eight_ai_only.json` (and Perplexity's `results/perplexity/perplexity_ai_only.json`) in every view. |
| `takeaway_ext.py` | Spec (d)'s takeaway comparison on WHU-S05 to S08, through the spec (d) runner unchanged, on ledger issue `whu-scorecard-takeaway` with a $12 cap. **Not run:** the estimate (worst case $18.64) is over the cap, so it stopped before any call. For comparison, S01-S04's estimate was $19.24 and its actual spend $6.83. |
| `takeaway_counts.json` | Counts only from the S01-S04 takeaway comparison: ratings per pair and judge, judge agreement, direct answers, quote check. The answer-derived text (bottom lines, differences, divergence summaries) and the builder are private: `~/Projects/whu-study-private/scorecard/`. |

ChatGPT performed no web search on WHU-S05 to S08 (deviations 2026-10-26), and its figures are labelled that way wherever they appear. Perplexity has WHU-S01 to S04 only.

The draft page mock-ups are private: `~/Projects/whu-study-private/scorecard/mockups/` (`scorecard.html`, `question-WHU-S02.html`, with an unchanged copy of `site/whatholdsup/style.css`).
