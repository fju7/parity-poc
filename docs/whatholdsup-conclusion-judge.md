# The conclusion judge

A publish stage for What Holds Up. A model reads each conclusion against the
passages the writer recorded for it. A person then records a decision on every
conclusion it flags. Publish preflight blocks until every flag has a current
decision.

Adopted 17 October 2026. Code: `backend/scripts/whatholdsup/conclusion_judge.py`.
Tests: `backend/tests/test_whatholdsup_conclusion_judge.py`. Validation results:
`backend/data/conclusion_judge_validation/` (round 1) and `…/round2/`.

## What it is for, and what it is not

B19 (hedge preserved) and B20 (confidence ceiling) are word-level. They catch a
dropped "may" and a "high" above a cited "moderate". They cannot see a
conclusion whose claim goes further than its premises in substance: T03 s56
says "the evidence says the calorie deficit, not the clock, does most of the
work", and no premise says anything about mechanism. The judge exists for that
class.

It is **not** a filter on B19 or B20, and a SUPPORTED verdict must never be used
to clear one:

- In round 1 the judge called SUPPORTED, four times out of four, every sentence
  whose dropped hedge B19 reports (T01 s1, T03 s1, T04 s1, T03 s56). It quoted
  the evidence with the hedge already removed ("moderately more effective" for
  "may be moderately more effective").
- In both rounds it passed T04 s60. That sentence says "high", and its premise,
  which the judge quoted, says "moderate certainty". B20 stops that sentence.

A flag is a question for a person. An unflagged conclusion is not thereby
verified.

## What the judge sees

For every on-page binding row whose bucket is `judgement`, **except holdings
sentences**:

- the sentence;
- about 400 characters of the page around it;
- each premise as (source id, access state, the recorded passage).

Holdings sentences are identified by `bindings.is_holdings`, the detector B21
uses to route them to the store. They are settled by the store, not by a reader
of passages. In round 2, 6 of the 38 flags were holdings sentences the judge
could not evaluate. In the four test issues, the exclusion leaves 65 of the 80
judgement sentences: T01 21, T02 18, T03 14, T04 12.

It does **not** see:

- the writer's stated reasoning (`step`; see the validation record);
- `check_flags`, gate findings, earlier verdicts or decisions.

A flag must be the judge's own reading of the evidence.

Model: `claude-sonnet-4-6`, one call per conclusion, temperature 0. That is
fixed in `factcheck_draft.call()`, so a second run adds little. Every call goes
through `factcheck_draft.call(search=False)` after `enter_issue()`, under the
issue's spend cap and the day cap, and is written to the spend ledger as role
`conclusion_judge/claude-sonnet-4-6`. Round 2 measured about $0.003 a call.

The prompt is the one validated in round 2, mode A. It is in the module as
`SYSTEM` and `USER_TEMPLATE`, and a test holds its shape.

## Running it

```
python3 backend/scripts/whatholdsup/conclusion_judge.py <slug>
```

This judges every new or changed conclusion and writes
`issues/<case>/conclusion-review.json`. Each judged sentence carries:
`sentence_sha`, `sentence`, `label`, `reason`, `model`, `run_on`, `flagged`
(label is not SUPPORTED, with an unparseable reply counted as flagged), and, if
flagged, an empty `decision` of `{decision, by, on, why}`.

Re-running:

- calls the model only for conclusions that are new or whose text changed;
- keeps the verdict and decision for every sentence whose text is unchanged;
- for a sentence whose text changed, keeps the old entry under `previous` with
  its decision marked `stale: true`, and leaves the new verdict undecided.

## Deciding

```
python3 backend/scripts/whatholdsup/conclusion_judge.py <slug> decide <sentence_sha> <accepted|rejected|judgement> --by "<name>" --why "<reason>"
```

- `accepted`: the judge is right and the sentence has been changed. Re-run the
  judge afterwards; the new text gets a new verdict.
- `rejected`: the judge is wrong. Say why, from the evidence.
- `judgement`: neither is a matter of fact (emphasis, framing). Say what the
  question is.

The date is written by the command. A unique prefix of at least 8 characters of
`sentence_sha` is enough. It refuses a decision on an unflagged sentence, with
no named person, or with no reason.

To see the preflight row without spending:

```
python3 backend/scripts/whatholdsup/conclusion_judge.py <slug> status
```

## Preflight

One row, `conclusion review settled`, added to `publish.preflight()` after B15's
`gate findings settled`:

| state | when |
|---|---|
| BLOCKED | no `conclusion-review.json` for an issue that requires one |
| BLOCKED | a current conclusion has no verdict on its current text (the draft changed since the run): re-run |
| BLOCKED | a flagged conclusion has no decision, or its decision is stale |
| ok | otherwise: "N conclusion(s) judged, F flagged, D decided" |
| ok, "SKIPPED — …" | the issue's first `publish` or `republish` row in `published.json` is before the adoption time (`ADOPTED`, 2026-10-17T16:00Z) |

Notes:

- **SKIPPED is shown as ok.** `publish.show()` turns any state other than
  ok / BLOCKED / warn into a STOP, so SKIPPED is an ok row whose detail starts
  with "SKIPPED" and gives the date.
- **Which issues are skipped.** Melanoma, cdk46 and deskilling are SKIPPED.
  Every issue first published after adoption needs the review.
- **A crash blocks.** If the check itself fails to run, the row is BLOCKED,
  not WARN.
- **Unwaivable on a send only.** The row is in `UNWAIVABLE_ON_SEND`, publish.py's
  only unwaivable list, which applies to the announce (email) path. On the page
  publish path no row is unwaivable, so `--waive` can still pass a page over
  this row, as it can any other.

## Validation record

All runs were on the four frozen test issues WHU-T01..T04, which have 80
judgement sentences between them. None of the issue files was edited.

**Known errors used to score it:**

- **Recorded:** T01 s85 (`issues/WHU-T01-ctp-exercise-depression/gate/PHASE_B.md`
  and `docs/whatholdsup-claim-bindings-spec.md` §4a); T03 s53 and T04 s60 (spec
  §4a).
- **Also tracked, from the calibration work:** T01 s1, T03 s1, T04 s1 and T03 s56.
  They are not in a repo record.

**Round 1** (17 October 2026). The prompt showed the writer's step. Two runs
each of `claude-sonnet-4-6` and `claude-opus-4-6`, so 320 calls, **$1.3730**.

- 24 of 80 flagged.
- T01 s85: Sonnet SUPPORTED on both runs; Opus OVERSTATES on both.
- T03 s56: SUPPORTED by both models on all runs (missed by both).
- T01 s1, T03 s1, T04 s1: SUPPORTED by all four. The dropped hedge was endorsed.
- T03 s53, T04 s60: SUPPORTED by all four.
- 2 of 160 model–sentence pairs gave different labels on their two runs.

**Round 2, mode A** (17 October 2026). The step was removed; nothing else in the
prompt changed. One run each of Sonnet and Opus, so 160 calls, **$0.6735**
(Sonnet $0.2460, Opus $0.4275).

- **38 of 80 flagged:** Sonnet flagged 35, Opus 15.
- **T01 s85:** OVERSTATES from both.
- **T03 s56:** Sonnet OVERSTATES ("the evidence only shows equivalence … not the
  underlying cause"); Opus SUPPORTED (missed).
- **T01 s1:** Sonnet OVERSTATES; Opus SUPPORTED.
- **T03 s1, T04 s1, T03 s53, T04 s60:** SUPPORTED by both.
- **Labels:** Sonnet 45 SUPPORTED, 15 OVERSTATES, 18 NOT_IN_EVIDENCE,
  2 CONTRADICTED. Opus 65 SUPPORTED, 2 OVERSTATES, 11 NOT_IN_EVIDENCE,
  1 CONTRADICTED, 1 UNDERSTATES.
- **Mode B was not run.** Mode B would have sent the full held text of each
  source instead of the recorded passage. Its estimate, about $14.22 (about
  $11.4 at round 2's measured characters per token), would have crossed that
  task's $6.00 limit. So T03 s53 has never been judged with the grade-bearing
  text in view.

**Why Sonnet only.** On the error class this stage exists for, Sonnet without
the step flagged both T01 s85 and T03 s56, and Opus missed T03 s56. Sonnet also
flags more in general (35 against 15). Many of its extra flags are
NOT_IN_EVIDENCE on points the passages simply do not cover, which is the cost of
the choice: more decisions for a person to record.

**Showing the writer's reasoning appeared to make the judge adopt it.** On
Sonnet, three of the known-error sentences went from SUPPORTED with the step to
OVERSTATES without it: T01 s85, T03 s56 and T01 s1. Treat this as a lead, not a
result:

- the sample is three sentences;
- round 2 also differs in run count (one run, not two);
- across all 80 sentences, 18 were newly flagged and 4 stopped being flagged
  between the rounds, so Sonnet became more sensitive generally, not only on
  these three.

The step is excluded on that lead.

**What it does not catch.** Neither round caught T03 s53 or T04 s60, the
confidence-ceiling errors B20 exists for. In round 1 it endorsed every hedge
that B19 reports dropped. **B19 warnings and B20 stops stand on their own; this
judge must not be used to filter, clear or rank them.**
