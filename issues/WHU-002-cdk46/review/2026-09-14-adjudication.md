# cdk46 — adjudication of the 34 unreconciled changes

Drafted 14 September 2026. For the operator to read and sign, or to send back.

Two sentences were struck and rewritten before signature. One understated a
defect in `changes.json` — it said two rows were duplicated where four are. The
other, in Ruling 2, asserted an identity between diff rows that the data does
not carry; Claude Code declined to file the version containing it, tested it as
written, and was right on both counts.

## ROUND-2026-09-14 — the 34 changes since the post-publication read of 29 August

**What this is about.** `publish.py check cdk46` reports one STOP and only one:

```
STOP  outside review   34 change(s) since the review of 3ca22e72 have no
                       decision behind them
```

`3ca22e72` is a content hash, not a commit: it is the sha256 of
`issues/WHU-002-cdk46/review/2026-08-29-post-publication-sent.html`, the bytes
the post-publication reader read on 29 August. The page now stands at
`fec7a9a2e0eebd41bebaa9b6eb98cede17b46c81b2fbe4cba3a1d1b7c551b105`, which is
what readers have been served since the production deployment of 13 September.

**How the 34 was partitioned.** `reconcile("cdk46")` finds 350 changes to the
prose since that read: 316 traced to a recorded decision, 34 not. The 34 were
then partitioned twice, independently — once by an assistant session running
the repository's own functions under the Linux bridge's system Python 3.10, and
once by Claude Code under `backend/venv/bin/python3` (3.14.3). Both partitions
agree: 28 of the 34 carry a recorded entry the reconciler could not match, and
6 carry no recorded entry at all. Neither partition rests on a hand extraction;
both call `reconcile`, `explain`, `recorded_changes` and `decision_labels` as
the repository defines them.

The two runs disagreed on one number and the disagreement is recorded here
rather than reconciled away: the assistant reported 170 unused recorded
entries, which is what `reconcile` returns; Claude Code found that by content
there are 168 distinct ones, because four rows of `changes.json` form two
duplicated pairs. The 168 figure is the true one. The duplication is a defect
in `changes.json` and is named below.

---

**Ruling 1 — the six sentences that have no recorded entry.**

Six changes have no entry in `changes.json` of any kind. All six are additions.
All six sit in the page's correction log, not in its evidence prose: each is a
sentence describing a correction that was already made and already decided.
They are, verbatim:

1. *Their paper contains nothing about the width of a confidence interval.*
2. *The published paper treats progression-free survival as primary for that
   particular data cut, and we collapsed the two — in the direction that made
   the survival signal easier to set aside.*
3. *Two other instances were corrected on 31 August; this one was missed
   because the wording differed.*
4. *Clinical benefit counts stable disease; response does not.*
5. *This page said the trial was powered on response rate, which is what the
   sample-size calculation says, and did not mention that the paper names a
   different endpoint as its objective.*
6. *Both now appear, because the source states both.*

The decision behind each was written on 1 September, in
`issues/WHU-002-cdk46/review/2026-09-01-adjudication.md`, under headings that
resolve in `decision_labels("cdk46")` today:

| sentence | label | heading |
|---|---|---|
| 1 | `CORR-14` | we put our own observation under someone else's name |
| 2 | `CORR-16` | an endpoint downgraded |
| 3 | `CORR-17` | the third time the same flattening |
| 4, 5, 6 | `CORR-19` | the trial names one primary endpoint and powers on another |

Each of the six is ruled a recorded change under the label above. They take
per-change entries in `changes.json`, not set-level attribution, because a
named decision exists for each and set-level attribution would understate what
is known about them.

**Ruling 2 — the twenty-eight the reconciler cannot match.**

Each of the remaining 28 carries a recorded entry in `changes.json` whose `now`
text is verbatim identical to the diff's `now` text, whose `because` resolves
in `decision_labels("cdk46")`, and which no other change has consumed. Between
them they cite thirteen labels: `AD-HOC` (×5), `LIC-Q-001` (×4), `PUB-04` (×4),
`PALM-FIG-001` (×3), `S007-WALL-001` (×3), `G1` (×2), `PREFLIGHT-01`, `G2`,
`PALM-END-001`, `CORR-17`, `OR-B`, `C95-001`, `PUB-03`. Every one resolves.

They fail for a mechanical reason. `explain()` (publish.py, ~2945–2961) matches
a diff row to a recorded entry on **both** sides, `was` and `now`. Of the 28,
13 carry a `was` that differs from the recorded entry's, and 15 differ in kind —
the diff calls it `changed` where the entry says `added` (5), or `added` where
the entry says `changed` (8) or `reworded` (2) — which leaves one side's `was`
empty and the other's populated, so neither of `explain()`'s two loops can fire.

The reason the shapes differ is upstream of anyone's record-keeping.
`changes_since()` diffs the page a sentence at a time with
`difflib.SequenceMatcher`, and inside a `replace` opcode it pairs the *k*-th old
sentence with the *k*-th new one positionally, whatever each one replaced. Rows
209 to 213 of the 350-row diff are one such opcode: three old sentences against
five new ones. What that pairing produces is visible at row 211, whose `now`
opens with the same 46 characters as row 210's `was` — *The paper prints 0.71;
the more precise 0.712* — and then departs from it, because the sentence was
reworded as it moved. Nothing in that block is byte-equal to anything else in
it, and an exact-match search across all 350 rows finds no case of one row's
`now` equalling the previous row's `was`. That is the mechanism rather than a
weakness in the account of it: a revised sentence has been set beside a
different old sentence than the one it revises, and no person ever recorded
that pairing, because that pairing never happened. A record that does not match
it is not a record with a gap in it.

These 28 are ruled decided, and covered at set level. Each is reported as
set-attributed and not as though a reason had been written for that particular
sentence, which is the truth of it: the reason was written for the change, and
the change is no longer addressable in the shape the reason was written in.

**Ruling 3 — what a signature on this document does not cover.**

This document does not re-adjudicate the substance of any of the 34 changes.
The evidence questions they turn on were settled in the adjudications the labels
above name, and this ruling does not reopen them. What is being decided here is
that the changes trace to decisions, and which ones.

---

**Three defects this exposed, which are obligations and not observations.**

*D1 — the reconciler cannot address a re-grouped sentence.* Where later editing
regroups sentences, a decided change becomes permanently unmatchable, and the
board reports it as a change with no decision behind it. That message is false
in those cases, and no amount of care in recording decisions prevents it.
Owner: Advisor Claude, to specify; Claude Code, to implement. Resolution path:
`explain()` gains a third pass that matches on `now` alone when the candidate
entry is unconsumed and its label resolves, and reports such a match under its
own name — never as a two-sided match. The counterfactual test that must
accompany it: a genuinely undecided change, whose `now` text appears in no
recorded entry, must still STOP, and the test must fail if the distinction is
deleted. Until that exists, every future round carries this same debt.

*D2 — four rows of `changes.json` form two duplicated pairs.* Indices 433 and
435, and indices 434 and 436: each pair shares `was`, `now` and `because`
(`INF8-001`), and each was written seconds apart on 13 September 2026. Nothing
is wrong on the page; the record says two things twice, and any count taken
from it is inflated by two — which is the whole of the 170-versus-168 gap
above. Owner: Claude Code, already reported; no action until the operator
rules, because a duplicated row is evidence of how the record was written and
deleting it silently destroys that evidence. The question the operator answers
is whether the writer that produced them can produce them again.

*D3 — `changes.json` and `changes_since()` use different vocabularies for
`kind`.* The record carries `reworded`; the differ emits only `changed`,
`added` and `removed`. Nothing reads `kind` today, so nothing is broken, and
that is exactly why it will still be true when something does read it. Owner:
Advisor Claude, to rule on which vocabulary is authoritative, before any check
consumes the field.

---

**What the operator is signing.**

Not a re-reading of 34 sentences. Specifically:

- That the six sentences quoted above are the page's own account of corrections
  made under CORR-14, CORR-16, CORR-17 and CORR-19, and that each describes the
  correction it belongs to accurately. This requires reading those six
  sentences, and nothing else on the page.
- That the 28 are changes already decided under the thirteen labels named, and
  that their failure to reconcile is the reconciler's pairing and not an absence
  of judgement.
- That D1, D2 and D3 are open, owned, and not resolved by this document.

Accepted by Fred Ugast, operator, 14 September 2026, stated in session. This
publication takes the operator's stated acceptance as his signature; no
manuscript signature is produced, and this line records the acceptance rather
than leaving a blank that could be read as its absence.
