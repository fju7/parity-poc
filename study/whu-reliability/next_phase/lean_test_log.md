# Lean four-question test: run log (session LT)

Rule: `lean_test_rule.md`. Prompts: `lean_briefs.md` (made by `lean_briefs.py`). Counts, costs and times only;
no key, judge reply or answer text.

## Estimate printed before any paid call (2026-11-05T02:02Z)

**Runs** (line $40, spent $0): from the $0 replay of round 1 (`round1_scoring/lean_replay_round1.json`, tier
sonnet-5-5), likely = base, pessimistic = the replay's pessimistic, worst = the $10 run cap.

| Question | audit | rulings | gate | likely | pessimistic | worst |
|---|---|---|---|---|---|---|
| WHU-Q1-01 | $0.50 | $0.23 | $1.23 | $1.96 | $2.27 | $10.00 |
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

**Correction (2026-11-05, LT):** an earlier edit had overwritten this table's Q1-01 and Q1-02 estimate rows with
their run rows, and left the run table below saying "running". Both are restored from commit 505d3cb.

**Before the Q1-02 re-run (2026-11-05, after the re-freeze at 4abcab6):** estimate as Q1-02 above: likely $4.54,
pessimistic $5.28, worst $10.00 (its run cap). Ledger today $29.12 (whu-check-fresh-judge $26.30, whu-lean-q1-02 $1.83,
whu-lean-q1-01 $0.99): $29.12 + $4.54 = $33.66 ≤ $50, and $39.12 ≤ $50 at the worst, so the room rule allows it. Runs line:
$2.82 spent of $40.

## Runs

| Question | subagent model | started (UTC) | ended (UTC) | ledger | drafting tokens (est. $) | outcome |
|---|---|---|---|---|---|---|
| WHU-Q1-01 | claude-opus-5-5 (Agent tool, general-purpose, model "opus") | 2026-11-05T02:04:56Z | 2026-11-05T02:40:30Z (35 min) | $0.99 (incl. $0.21 audit "dry run", see deviations) | 148 calls; 296 in, 73,664 out, 253,043 cache write, 25,031,142 cache read; **$7.75 est.** (Opus 5.5 rates, cache write at the 5-min rate) | **Ready.** at 314b7af; 0 operator minutes; 0 to a person; audit 39 units (26 holds, 5 holds_by_record_check, 8 not_a_correction), 0 escalations (34 decided by claude-sonnet-5-5), 0 replies cut off; removed under the new rule 0; contamination: valid (lean_contamination.md) |
| WHU-Q1-02 | claude-opus-5-5 (Agent tool, general-purpose, model "opus"; shell starts at the repo root) | 2026-11-05T02:45:19Z | 2026-11-05T03:20Z (35 min) | $1.83 (incl. $0.42 audit "dry run") | 146 calls; 294 in, 77,875 out, 259,905 cache write, 25,065,891 cache read; **$7.87 est.** | **NOT Ready: stopped for good under the no-person rule** at 8f25d51. 1 STOP, "changed sentences reviewed": changecheck raised 2 CONTRADICTION findings on generated readers'-list lines, and ruling.py left both for a person (rulings/for_person.jsonl). 0 operator minutes. Audit 45 units (30 holds, 7 holds_by_record_check, 10 not_a_correction), escalations 2 (decided by claude-opus-5-5), 0 replies cut off; removed under the new rule 0; contamination: valid |
| WHU-Q1-02r (re-run, fresh drafter, frozen code 4abcab6) | claude-opus-5-5 (Agent tool, general-purpose, model "opus"; shell starts at the repo root) | 2026-11-05T12:39:09Z | 2026-11-05T13:23Z (44 min) | $2.22 (incl. $0.53 audit "dry run", see deviations) | 180 calls; 362 in, 110,693 out, 364,032 cache write, 40,481,820 cache read; **$12.13 est.** (Opus 5.5 rates) | **Ready.** at b2b75d5 (78 ok, 12 warn, 0 STOP); 0 operator minutes; 0 to a person; audit 65 units, 1 escalation to claude-opus-5-5, 0 replies cut off, 0 cuts; fail-safe removals 0, "already stated" conversions 0, relevance treated as relevant 0, "Not added" lines 0; contamination: valid (lean_contamination.md). Replaces WHU-Q1-02's earlier attempt (not Ready). |
| WHU-Q1-03 | claude-opus-5-5 (Agent tool, general-purpose, model "opus"; shell starts at the repo root; code fab2b3e) | 2026-11-05T13:32Z | 2026-11-05T15:19Z (106 min) | $9.42 (incl. about $1.84 audit "dry run" and $4.45 for two rounds of recency rulings on 132 rows; see deviations) | 232 calls; 466 in, 155,878 out, 412,639 cache write, 63,300,008 cache read; **$17.84 est.** (Opus 5.5 rates) | **Ready.** at a4b9996 (74 ok, 17 warn, 0 STOP); prompt sha256 90fb10dec459…; 0 operator minutes; 0 to a person; audit 162 units, 0 cuts; 16 relevance escalations to claude-opus-5-5; fail-safe removals 0, "already stated" conversions 1, relevance treated as relevant 4, "Not added" lines 0; contamination: valid. **Reading record overstates what the drafter saw (deviations): standing awaits the advisor.** |
| WHU-Q1-04 | claude-opus-5-5 (Agent tool, general-purpose, model "opus"; shell starts at the repo root; code fab2b3e) | (starting) | | | | running; prompt sha256 56996bacfdc0… |

## Post-test fixes (advisor ruling, 2026-11-05; no code change until Q1-04 has finished; each with a test)

1. The audit `--dry-run` makes paid calls (Q1-01 $0.21, Q1-02 $0.42, Q1-02r $0.53, Q1-03 about $1.84). Spend stays in each question's ledger cost.
2. `omissions.redact` checks a reason only against the finding's own source, but `leaks_source_text` checks every held source. The Q1-02r drafter applied the missing step by hand.
3. Lean's generated "we did not read" (`lean_sentences.NOT_READ_FRAME`) on a `full_text_held` source trips "claims a source could not be opened" (`source_ledger.INACCESSIBLE`).
4. A "not read" record may be removed only if a read record exists covering the same sections (code-enforced; the preflight stops otherwise). Advisor ruling of 2026-11-05, after Q1-01's drafter deleted `access.not_read` to pass a check.
5. (Advisor ruling of 2026-11-05: Q1-01 invalid on this.) A sentence bound to text outside the sections a `full_text_held` source's read record lists stops the preflight. Found on Q1-01: one of 36 bound spans, S001@144900.

**Added by the advisor after Q1-03 (2026-11-05; each with a test):**

6. Build the read record from the text the checking stages actually received (system level), never from the drafter's own claim; the preflight stops if a listed section was not received in full by a checking stage.
7. Detect duplicate rulings when the final gate re-files the same findings under new IDs (Q1-03: $4.45 spent ruling three recency findings twice against 132 sentences).

**Per page: did the drafter read the unread sections in full to clear fix 3's mismatch, and what did it add?**

| Question | occurred | added cost |
|---|---|---|
| WHU-Q1-01 | **no.** The same mismatch was hit, but the drafter cleared it by **dropping `access.not_read`** from sources.json without reading further. S001 stays `full_text_held` with sections read "the abstract; the plain language summary", so the page still says only those were read, but the explicit "we did not read" sentence is gone. This is not the cautious direction the ruling accepts; it is reported, not changed. | $0 |
| WHU-Q1-02r | **yes** (S001 §5 and S003 §5 read in full; not-read records removed; two more inconsistencies within S001 put on the page, bound) | pipeline $0.10 (conclusion judge and audit repeated, 13:14:58-13:15:45); drafting est. $1.59 (17 drafter calls in the fix window 13:11:23-13:14:58, Opus 5.5 rates) |
| WHU-Q1-03 | **yes, partly.** D.1 read in full (chars 105712-118151). Both not-read entries removed, including "the figures and tables as graphics", which was not read further; sections widened to "A to D" and the extracted figure text (see deviations: the record overstates what was seen) | pipeline $0; drafting est. $0.88 (12 drafter calls, 13:58:09-13:59:17Z) |
