# D1 — specification: the `now`-only pass in `explain()`/`reconcile()`

Drafted 14 September 2026 by Advisor Claude; condition (d) amended 15 September
on Claude Code's reconnaissance. For the operator to accept or send
back. Nothing here has been implemented. Written against `publish.py` as it
stands at `59d0033`; CC verifies every line number and field name before
writing code, and reports any that have moved.

---

## 1. The defect, stated so it can be tested

`reconcile()` calls `explain()` once per diff row. `explain()` matches a diff
row to a recorded change entry on **both** sides — `was` and `now` — either
exactly or by containment. `changes_since()` produces those rows by diffing the
page a sentence at a time with `difflib.SequenceMatcher` and, inside a
`replace` opcode, pairing the *k*-th old sentence with the *k*-th new one
positionally, whatever each one replaced.

So when later editing regroups sentences — inserts one into a paragraph,
splits one in two, merges two into one — the differ emits pairs no person ever
made. A recorded entry that names the real change cannot match a pairing that
never happened. The board then reports the change as having **no decision
behind it**, and that report is false.

Measured on cdk46 on 14 September, at review sha `3ca22e72…` against page sha
`fec7a9a2…`: 350 changes, 34 reported as undecided. Of those 34, **28** had a
recorded entry whose `now` was byte-identical to the diff's `now`, which no
other row had consumed, citing a label that already resolved. Six were genuinely
unrecorded. The 28 were bookkeeping the apparatus generated for itself.

The cost of leaving it: every future round pays it again, and the only available
remedy is a change set — which attributes at round level work that was in fact
decided sentence by sentence, understating what is known.

## 2. The rule

> A change is explained when a person wrote down that **this sentence** went in,
> and named a reason that resolves. What the sentence displaced is bookkeeping
> about the diff, not about the decision.

That is what rule 14 has always asked. The two-sided match is a *proxy* for it —
a good one, because a matching `was` confirms the pairing is the one the writer
had in mind. The `now`-only match is the same test with the proxy removed, and
it must be reported as such and never as a two-sided match.

**What the proxy was also silently buying, and must be bought back.** A
mispaired `changed` row can conceal a deletion: in a `replace` opcode with more
old sentences than new, an old sentence that vanished entirely can be consumed
into a pairing rather than surfacing as its own `removed` row. Under the two-sided rule that row goes to `bad` ONLY when no change set
covers the span; with a set, phase 3 swallowed it. That is a correction to
this specification, found on 15 September when the pass first ran: a change
set was attesting "these changes were decided" and, silently, "and nothing
vanished unrecorded" — a second claim nobody asked it to make and nobody
checked. A naive `now`-only pass would rescue such a row and the deletion
would never be examined. So the pass carries an explicit condition (2d below)
that keeps it blocking, and phase 2 runs before phase 3 so that a set cannot
absorb it.

A row qualifies for `now`-only attribution when **all** of:

- **(a) Non-empty `now`.** A `removed` row has no `now`. Matching on an empty
  string would match the first recorded entry with an empty `now` and rescue
  every deletion on the page. Deletions are never rescued by this pass.
- **(b) Exactly one unconsumed candidate.** Among recorded entries not already
  consumed by a two-sided match, exactly one has `flatten(entry["now"]) ==
  flatten(row.now)`. Zero is no evidence. Two or more means the record cannot
  say which decision this sentence came from, and guessing is worse than
  blocking — `changes.json` is known to contain duplicate rows (D2), so this
  case is live, not hypothetical.
- **(c) The candidate's `because` resolves** in `decision_labels(slug)`. Same
  requirement a two-sided match carries. A candidate whose label does not
  resolve is not a candidate; the row stays blocking and the report names the
  unresolved label rather than saying nothing was found.
- **(d) The row's `was` is accounted for.** If `row.was` is non-empty, its
  flattened text must satisfy at least one of: it still appears in the flattened
  current page (the sentence moved rather than died); or it is the `flatten`ed
  `was` of some recorded entry (someone wrote down what happened to it). If
  neither holds, the sentence vanished with nothing recording it, and the row
  **stays blocking** regardless of how good the `now` match is.

  *Amended 15 September, on CC's finding.* This condition was drafted with a
  third limb — "or it appears in the issue's deletions record" — on the
  assumption that `deletions.json` carries deleted sentence text. It does not:
  it is the B14 **figure**-deletion record, whose rows are bare numbers with a
  reason. The limb is therefore dropped, and the drafter's worry that dropping
  it weakens the guard was backwards. (d) is a disjunction, so removing a limb
  makes FEWER rows qualify: it fails closed, and its only cost is a false block,
  never a false pass. Measured on the cdk46 round that motivated this: of the 28
  rows, ten are additions with no `was`, seventeen satisfy the second limb, one
  satisfies the first. The dropped limb would never have been consulted.

  A figure-based substitute — "the `was` contains a figure recorded as deleted"
  — is **rejected**: it would pass a row because it mentions a number that was
  removed somewhere, which is containment standing in for identity, and would
  turn a fail-closed guard into one that fails open on arithmetic coincidence.

  Extending `deletions.json` to record sentence text is **deferred, not
  rejected**. Nothing demonstrates the need. If a round ever produces a row
  whose displaced sentence was genuinely deleted and recorded, it will be
  falsely blocked, visibly, and a person will look at it — which is the system
  asking for the limb rather than us predicting it.

## 3. The algorithm

`explain()` is stateless and cannot know what other rows have consumed.
Condition (b) is load-bearing and needs that knowledge. So the pass does **not**
go inside `explain()`. `reconcile()` becomes explicitly phased, and each phase
completes before the next begins.

```
PHASE 1 — two-sided, unchanged.
  For each diff row: r = explain(kind, was, now, recorded).
  If r and r.because does not resolve  -> hold as UNRESOLVED(r)
  If r                                 -> ok, mark r consumed
  else                                 -> hold as UNMATCHED

PHASE 2 — now-only, new. Runs over the UNMATCHED rows only, after
  phase 1 has finished consuming, so that a row which can match
  two-sided always gets its entry ahead of a row that can only
  match on one side.
  For each UNMATCHED row:
     if conditions (a)(b)(c)(d) hold  -> ok, marked now_only, mark consumed
     elif a sole now-candidate exists but (c) fails
                                      -> bad, reported as UNRESOLVED LABEL
     elif a sole now-candidate exists but (d) fails
                                      -> bad, reported as UNACCOUNTED DELETION
     else                             -> remains UNMATCHED

PHASE 3 — set-level, unchanged, over what is still UNMATCHED.

PHASE 4 — whatever remains, plus every UNRESOLVED, is bad.
```

Phase 2 **must** precede phase 3. A change with its own recorded decision is
reported as having one; folding it into a round-level set would understate the
record, which is the objection `recorded_change_sets()` already states about
itself.

`explain()` itself is not modified. Its docstring gains one line saying that the
two-sided match is a proxy and where the third pass lives.

## 4. What the board must say

`outside_review()` currently builds one sentence counting per-change and
set-level attributions. It gains a third counter, and a `now`-only attribution
is **never** described as "traced to a per-change decision". Shape:

```
N change(s) since, A traced to a per-change decision, B to a recorded decision
matched on the new text alone (the diff paired them against a different old
sentence), and C to a recorded change set (<labels>)
```

The parenthetical matters: a reader of the board should be able to tell, without
opening the code, that B is a weaker link than A and why. And the existing
`cites` list should be built from the labels actually cited, not from every `ok`
row — today it sweeps in all 350, which will be misread as the change set's
`decided_by`.

## 5. The tests

In `backend/tests/`, alongside `test_reconciliation.py`. Each names the exact
weakening it exists to catch. Fixtures are frozen files, not the live repo —
a test that reads `site/whatholdsup/cdk46.html` rots the moment the page moves.

**T1 — the rescue works.** A diff row whose `was` is mispaired and whose `now`
equals a recorded entry's `now`, label resolving, `was` still present elsewhere
on the page. Assert: in `ok`, `now_only` true, `bad` empty.

**T2 — equality, not containment.** *Catches: someone "relaxes" (b) to the
containment test phase 1 already uses.* Fixture: recorded entry `now` = "The
paper prints 0.71; the more precise 0.712 is the Cox hazard ratio in the
registry posting." Undecided new sentence = "The paper prints 0.71." — a strict
prefix of it, and nobody's recorded decision. Assert: **still bad**. Under
containment it would be rescued and this test goes red.

**T3 — uniqueness.** *Catches: someone drops (b) and takes `candidates[0]`.*
Two unconsumed recorded entries share a `now` and carry **different**
`because` labels. A row matches that `now`. Assert: **bad**, and the report says
the record cannot say which decision it came from. Taking the first entry passes
the row and this test goes red.

**T4 — the label check survives.** *Catches: someone drops (c) on the grounds
that a `now` match is evidence enough.* Sole candidate, `because` not in
`decision_labels`. Assert: **bad**, reported as an unresolved label — not as
"no decision behind it", which would be a different and false statement.

**T5 — deletions are never rescued.** *Catches: someone drops (a).* A `removed`
row, `now` empty, and at least one recorded entry with an empty `now`. Assert:
**bad**. Without (a) every deletion on the page silently passes.

**T6 — a hidden deletion still blocks.** *Catches: someone drops (d) as
over-engineering.* A row whose `now` matches a recorded entry cleanly, but whose
`was` sentence appears nowhere in the current page, in no recorded entry's `was`,
and in no deletions record. Assert: **bad**, reported as an unaccounted
deletion. This is the test that keeps the pass honest: it is the case where the
old rule was right for a reason the new rule would otherwise lose.

**T7 — phase ordering.** *Catches: someone interleaves the passes for speed.*
Construct row A (earlier in the diff) whose only route to entry E is `now`-only,
and row B (later) which matches E two-sided. Assert: B gets E as a two-sided
match; A does not get E. Interleaving lets A consume E first and this goes red.

**T8 — the board's wording.** *Catches: someone merges the counters.* Assert
that the OK string reports the `now`-only count separately and does not include
those changes in the "traced to a per-change decision" figure.

**T9 — the replayed round.** A frozen copy of cdk46's review snapshot, page and
`changes.json` **as they stood before the 14 September change set was written**.
Assert: 350 total, 322 two-sided, 28 `now`-only, **0 bad**, and no change set
consulted. This is the proof the pass does the job it was built for, on the data
that motivated it, without the set that was needed to work around its absence.

**T10 — the counterfactual proper.** Same frozen fixture as T9, with one
additional genuinely undecided sentence inserted — new text appearing in no
recorded entry at all. Assert: exactly **1 bad**, naming that sentence, and the
other 350 unaffected. Measured on 15 September: T10 goes red under (b) relaxed to containment, and
stays GREEN under deletion of (a), (b)'s uniqueness, (c) and (d) entire —
because none of those bites on cdk46's data. The unit tests carry those four.
This corrects the drafter's claim that T10 must go red under any weakening in
T2–T6; it was asserted without being run.

## 6. What this deliberately does not do

- **It does not repair history.** No recorded entry is rewritten, no `by` field
  is filled in, no duplicate is merged. D2's four rows stay as they are until
  the operator rules.
- **It does not touch phase 1's containment loop.** That loop can return an
  entry already returned for an earlier row, because `explain()` cannot see
  consumption — a latent weakness of the same family, and a separate decision
  with its own risk. It is recorded here as **D1b** and left open, owned by
  Advisor Claude to rule on, rather than fixed in passing.
- **It does not change `explain()`'s second caller** (publish.py:1193, the
  "correction recorded" row), which will keep matching two-sided and will keep
  reporting the same false negatives this pass exists to remove. That asymmetry
  is recorded as **D1c**, open and owned. It is named in `explain()`'s docstring
  so that the next reader finds it rather than discovering it; it is not fixed
  here because that call site's consumption semantics have not been established,
  and a pass that cannot see consumption cannot carry condition (b).
- **It does change `review_diff_text()`.** That function prints `ok` rows
  without distinguishing set-level attribution, so it would print a `now`-only
  match as though it were a two-sided one. Leaving it would mean the board tells
  the truth about the strength of a link while the narrative a person actually
  reads does not. Both say the same thing or neither does.
- **It does not make the gate deterministic**, change any spend path, or alter
  what `check` blocks on beyond the row this is about.
- **It does not lower the bar.** Every rescued row still requires a person to
  have written down that this sentence went in, and a label that resolves to a
  document on disk. What it removes is a requirement that the differ have
  guessed the same pairing that person had in mind.

## 7. Residual, stated rather than left to be discovered

A `now`-only match cannot distinguish a sentence that was **added** for the
recorded reason from one that was **moved** and had its recorded reason attach
at the old position. Both are decided changes citing a document a person can
open, so the rule's own test is satisfied either way, and condition (d) covers
the case where something died in the move. But the board's wording should not
imply more precision than that, which is why §4 says "matched on the new text
alone" rather than anything stronger.

---

Accepted by Fred Ugast, operator, 15 September 2026, stated in session. Condition
(d) was sent back on 15 September and amended before acceptance; §2 records that.
This publication takes the operator's stated acceptance as his signature — no
manuscript signature is produced, and this line records the acceptance rather
than leaving a blank that could be read as its absence.
