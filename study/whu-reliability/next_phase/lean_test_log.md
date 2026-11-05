# Lean four-question test: run log (session LT)

Rule: `lean_test_rule.md`. Prompts: `lean_briefs.md` (made by `lean_briefs.py`). Counts, costs and times only;
no key, judge reply or answer text.

## Estimate printed before any paid call (2026-11-05T02:02Z)

**Runs** (line $40, spent $0): from the $0 replay of round 1 (`round1_scoring/lean_replay_round1.json`, tier
sonnet-5-5), likely = base, pessimistic = the replay's pessimistic, worst = the $10 run cap.

| Question | audit | rulings | gate | likely | pessimistic | worst |
|---|---|---|---|---|---|---|
| WHU-Q1-01 | claude-opus-5-5 (Agent tool, general-purpose, model "opus") | 2026-11-05T02:04:56Z | 2026-11-05T02:40:30Z (35 min) | $0.99 (incl. $0.21 audit "dry run", see deviations) | 148 calls; 296 in, 73,664 out, 253,043 cache write, 25,031,142 cache read; **$7.75 est.** (Opus 5.5 rates, cache write at the 5-min rate) | **Ready.** at 314b7af; 0 operator minutes; 0 to a person; audit 39 units (26 holds, 5 holds_by_record_check, 8 not_a_correction), 0 escalations (34 decided by claude-sonnet-5-5), 0 replies cut off; removed under the new rule 0; contamination: valid (lean_contamination.md) |
| WHU-Q1-02 | $0.61 | $2.65 | $1.28 | $4.54 | $5.28 | $10.00 |
| WHU-Q1-03 | $3.39 | $1.69 | $2.19 | $7.27 | $8.78 | $10.00 |
| WHU-Q1-04 | $1.38 | $3.43 | $2.37 | $7.18 | $8.44 | $10.00 |
| **Total** | | | | **$20.95** | **$24.77** | **$40.00** |

Likely median $5.86, so the cost bar is predicted to fail. Likely $20.95 ≤ the line's $40 remaining, so the runs may start.
Q1-02's figure includes the $2.21 drafter dry run that round 1 recorded.

**Judging** (line $55, spent $0), from round 1's measured mean cost per call on `whu-quarterly-r1-judging`:
M1 Claude $0.193 and OpenAI $0.310; M2 Claude $0.029 and OpenAI $0.070. With about 75 cited items plus 20% repeats,
that is about 90 M1 calls per judge (~$45.3), and 19 conclusions plus 20% repeats is about 23 M2 calls per judge
(~$2.3). **Likely ~$47.6** ≤ $55. Worst: the runners' own figure, printed by their free estimate once the answers
exist, before any judging call.

**Drafting cost (estimated, not on the ledger):** the subagents' own tokens; measured per question after the run.

**Room today (2026-11-05 UTC):** ledger $26.30, so $23.70 is left under the $50 room rule. The runs go one at a time,
in question order. Each stage's own day-cap check and the brief's room rule decide whether it starts today.

## Runs

| Question | subagent model | started (UTC) | ended (UTC) | ledger | drafting tokens (est. $) | outcome |
|---|---|---|---|---|---|---|
| WHU-Q1-01 | claude-opus-5-5 (Agent tool, general-purpose, model "opus") | 2026-11-05T02:04:56Z | | | | running; prompt sha256 e416e0d8fc4c… |
