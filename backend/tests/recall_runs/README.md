# Recall runs

One JSON per run of `backend/scripts/signal/factcheck_recall.py`, kept because a
measurement you cannot compare against an earlier one is not a measurement.

## 2026-08-28 — before/after four new error classes

The first paired run. Same fixture, same code; the only difference is the recall
brief, which gained `SOURCE_FAULTED_ON_OUR_OWN_DEFINITION`,
`SOURCE_PRECISION_IMPORTED_UNCHECKED`, `RECALL_BRIEF_OVERFIRED_A_NEW_CLASS` and
`BRIEF_COLUMN_LOST_IN_DRAFTING` (the last of these is `kind: process` and is not
fed to any role).

|                | before | after |
|----------------|--------|-------|
| found          | 11     | 12    |
| missed         | 4      | 3     |
| mislabelled    | 0      | 3     |
| blind classes  | 3      | 3     |

**Do not read that table as a result.** Eight of the fifteen seeded errors
changed verdict between the two runs, including three that merely swapped
between FOUND and FOUND BY ANOTHER ROLE, and `OVERSTATED`, which went from found
to missed although it is present in both briefs and nothing about it changed.
The gate is a sampler; this is what its variance looks like.

The one difference with a mechanism behind it:
`SOURCE_FAULTED_ON_OUR_OWN_DEFINITION` was a blind spot in the before run — the
class did not exist yet — and was found in the after run. That is directional
evidence, at n = 1, in the expected direction.

Recorded as `RECALL_MEASUREMENT_UNDERPOWERED` in
`../fixtures/factcheck_known_errors.json`, with the standing rule that any claim
about a change to the prompts or the brief needs at least three runs per arm and
is a claim about rates, not rows.

Neither run recorded what it cost, because the script did not write usage into
its report. It does now.
