# Lean WHU four-question test: the rule (written before any paid call)

Session LT, 2026-11-05 UTC. Written and committed **before any paid call of the test** (advisor's rulings of
2026-11-05, `deviations.md`). It applies `validity_plan.md` §10 (frozen at `b4cf31a`), which stays **primary and
unchanged**; this file adds only what the rulings add. Nothing here changes a round-1 or study record.

## 1. What is tested

**"Lean + machine scope notes"**, not "lean as built": `WHU_LEAN=1` (`lean.STAGE_MODELS`: claude-sonnet-5-5 for the
audit's first read, the advocate and the relevance rulings, escalating to claude-opus-5-5; generated protected
sentences via `lean_sentences.py`; passage retrieval; prompt caching) **plus** the machine scope notes of
`docs/whatholdsup-process.md` §4.6.1, at commit `bf7bd4c`. The code is frozen at the commit that adds this file
for all four runs (a fix found during the test waits for its end).

Finding recorded first: **lean as built required person reads of 69 sentences across Q1-01..04 (65
scope/readers'-list plus 4 hand-written 'we did not search')** (`deviations.md` 2026-11-05; corrected by ruling 2,
2026-11-05, from 65, LT's preliminary count).

**Questions:** WHU-Q1-01..04, round 1's wording verbatim (each round-1 `issue.json` `question`). **Issues:**
`whu-lean-q1-01` .. `-04` (case folders `issues/WHU-L1-0n-whu-lean-q1-0n/`, `"study": true`, `"round": "lean"`).

**Drafting:** one fresh subagent per question (Claude Code Agent tool, model recorded; `lean_briefs.md`
holds each exact prompt), given only round 1's brief for that question (`quarterly/round1_briefs.md`) plus the
lean switch, with the substitutions `lean_briefs.md` lists. No person reads anything, no `person_decisions.md`, no
signed field names Fred, nothing is published. A step that needs a person stops the run. It is recorded where it
happened, and the session waits for a ruling. It is never worked around.

**In-sample.** Lean was replayed on these four questions (`lean_replay_round1.py`), the machine scope notes were
tested on their round-1 records, and the shared library still holds round 1's documents (plan §10's known leak).
Every result is labelled "in-sample; needs confirming on new questions".

## 2. Judging (as round 1's WHU answers were judged)

- Same code and rules as round 1 (`quarterly/prepare_round1.py` → `scripts/prepare_scoring.py`, `judge_m1.py`
  M1 v3, `judge_m2.py` M2 v2, `analyse_round1.py` rules), the same blinding (`blinding/blind.py`, phrase list and
  spelling map unchanged), **furniture left in as in round 1**.
- Judges: `claude-opus-5-5` and `gpt-6-astra`, both M1 and M2.
- **M1:** 20 claim-like sentences per answer (`identifiability.claim_like`), or all if fewer, drawn by
  `random.Random("%d/%s/WHU-lean/M1" % (R1SEED, q))` (plan §10; round 1's seed rule with system `WHU-lean`),
  R1SEED = `5f4a928b757d7f47c1ba8ed47600ced4a7a69f12` as an integer; uncited drawn sentences are UNCITED failures.
- **M2:** every conclusion of round 1's frozen keys (`keys_manifest_round1.txt`), for each lean answer.
- **Second reads:** a seeded 20% per judge, as round 1.
- Snapshots: one per distinct cited address, by round 1's routes. Route (d), in Fred's Chrome, is a human-adjacent
  step. If it is needed, the session stops for a ruling.
- Private run directory: `~/Projects/whu-study-private/scoring/lean/`. Committed outputs hold counts and hashes only.
  No key text goes to the advisor or into a committed file.

## 3. Pass rule: plan §10, primary, unchanged

All must hold:

1. **Cost:** median under $5 per answer and none over $10 (ledger; each run's `--cap` is $10, and a run that hits
   it fails this bar for that answer). Predicted to FAIL (replay median $5.86 likely); run anyway and reported as
   measured.
2. **Fred's time:** under 10 minutes per answer. Here the target is **zero**: any person step is recorded.
3. **M1 failure, two judges combined:** ≤ 15.0% as scored (round 1 WHU: 12.03%) **and** ≤ 6.0% excluding process
   and declaration sentences (round 1: 2.99%; the check-3c view, scope-note sentences excluded).
4. **M2:** Understates+Omits and Overstates+Contradicts no higher than round-1 WHU under either judge (round 1:
   Claude judge 0% and 0%; OpenAI judge 5.3% and 10.5%; 19 conclusions, so one failure under the Claude judge
   fails this bar).
5. **Seeded-defect bar (§9): deferred, not dropped.** The test has not run, so **the best possible verdict is
   "passes §10 pending the seeded-defect test"**.

A WHU run that cannot reach `Ready.` within its cap is a result: recorded, not scored, and it fails the bars it
cannot meet.

## 4. Secondary views (reported alongside; decide nothing)

- **(a) M1 within 10 points:** lean's two-judge combined M1 failure rate ≤ 22.0% (full WHU 12.0% + 10).
- **(b) Lead over each tool:** for Claude Research, ChatGPT deep research, Gemini Deep Research and Perplexity Deep
  Research, the difference (tool's M1 failure rate minus lean's, two-judge combined, round-1 tool answers and
  labels unchanged) keeps its sign (lean lower), with the 95% interval excluding zero. The bootstrap is
  `analyse_round1.py`'s: whole questions resampled, 10,000 resamples, seeded by R1SEED. Reported for all four
  questions **and** without WHU-Q1-02. Gemini has no WHU-Q1-04 answer, so its comparison has three questions.
- **(c) Cost and time:** median ledger cost per question ≤ $5, and zero human minutes.
- M2 (Overstates; Understates+Omits) against each tool and against full WHU, each judge alone and combined, as the
  weaker measure.

## 5. Reported

M1 and M2 tables (lean vs full WHU vs the four tools; each judge alone, combined, agreed only, cited only, uncited
share, reachability); the §10 bars and the secondary views; ledger cost and wall time per question; **drafting cost
(estimated)**, from each subagent's token usage where the harness reports it, priced at API rates, with "not
measured" per question where it does not; escalation counts (`decided_by`) per stage; every reply cut off at its
max-token limit (the audit's read limit is 12,000, `audit_stage.READ_MAX_OUT`; `ReplyCutOff` records) and what it cost; every step that needed a person.

## 6. Budget (plan §12, as ruled 2026-11-05)

- **Runs:** line $40 across `whu-lean-q1-01..04`, each run `--cap` ≤ $10 minus that issue's spend.
- **Judging:** line **$55** on `whu-reliability-judging-lean` ($45 + $10 from the reserve).
- Before any paid stage: print likely and worst (per stage and total). **STOP if likely exceeds the line's remaining
  balance** (gate on likely, as ruled 2026-11-01).
- **Room rule, each UTC day:** ledger total today + the stage's likely ≤ $50 ($60 day cap minus $10); otherwise wait
  for the next day and resume where it stopped. Never raise a cap, never `WHU_SPEND_OVERRIDE`, `--waive` or
  `--no-verify`.
