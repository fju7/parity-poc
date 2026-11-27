# Assembling the page from records: cost assessment (advisor's ruling 1 on P169, 2026-11-27)

This is an assessment only. Nothing has been built. The decision is the advisor's.

## The proposal

Today every step edits `draft/page.json` in place: `orch/page.Page` replace, delete, insert_after and set_html. Under
the proposal, each step would record its intended edits instead: insert, replace or remove, each anchored to a body
sentence id or a record id. Code would then assemble the page from the draft and those records, with the
code-written blocks placed last.

## What the last three stops share, and what they don't

| Run | Stop | Caused by editing in place? |
|---|---|---|
| 01b | An ADD was left after a sentence a later ruling removed. Fixed by P153, the anchor cascade. | **Yes.** A later edit broke an earlier one. |
| 01d | An ADD was anchored to the code-written fail-safe sentence. Fixed by P171. | **Partly.** The anchor came from the model, and nothing restricted anchors to body sentences. Assembly with body-sentence ids would have ruled it out by construction. So would P171's check at ruling time. |
| 01c | S005's title ends with a full stop, so its readers'-list line split into two sentences. Fixed by P163, safe_label. | **No.** The defect is in how one line is built, and assembling from records builds the line the same way. |

The redesign would remove two of the three causes by construction. It does nothing for the third, which is text
assembly within a single line.

## Records already in place

Most of the proposal exists already. Every edit is already a record: rulings.jsonl (accept/amend), audit cuts,
omissions.json ADDs, lean_removed.jsonl, the anchor cascade, and orchestrator/applied.jsonl. `orch/apply.py`
already replays them onto the page in time order. What is missing:

1. **Stable ids.** Anchors are sentence fingerprints, which change when a sentence is rewritten. The proposal needs
   an id per body sentence, fixed at the draft.
2. **A pure assembly.** Today the page is mutated and saved by each step. Under the proposal it would be computed:
   draft + all records → page.
3. **One placement rule for code-written blocks,** applied at assembly rather than written by each step.

**The page cannot be assembled only once, at the end.** The gate, advocate, audit, overstatement and changecheck
steps each read the page as it stands when they run. So the page would have to be re-assembled after every step,
as a deterministic function of draft + records, and not kept as a mutable file.

## Modules that change, and size

| Module | Change | Estimate |
|---|---|---|
| `orch/page.py` (208 lines) | Sentence ids at the draft. A new `assemble(draft, records)`. Edits become record constructors. | +150, −60 |
| `orch/apply.py` (208) | Becomes the assembler's record reader. `_cascade`, `_removed_earlier` and `already_removed` become one resolution rule: an insert whose anchor id is removed is not placed and is listed for readers. | rewrite, ~200 |
| `orchestrator.py` (2154) | 5 `page.save(ctx.page_json)` sites and the `_rerender` / `set_html` calls (draft; coverage and judgements statements at the end of findings; the apply step; corrections; belief). Each writes a record and calls assemble. | ~250 changed |
| `ruling.py` | `_placement` / `placement.py` return a body-sentence id rather than a fingerprint. omissions.json `after` becomes an id. | ~60 |
| `applied_check.py` (439), `bindings.py` | Insertions are checked by id. Bindings stay keyed by fingerprint, with an id↔fingerprint map from the assembly. | ~100 |
| `orch/replay.py`, `orch/replay_gate.py` | Replay the assembly, not the in-place log. | ~80 |
| Tests | About 10 test files touch page.json or insert_after (anchor cascade, fix-2 applied / omissions / ruling, the lean fail-safe). They need rewriting, plus new assembly tests. | ~400 |

**Total:** about 1,200 lines across 8 modules and about 10 test files. `orch/page.py`, `orch/apply.py` and
`orchestrator.py` are harness files, so every step's code hash moves. No run checkpointed before the change can
resume, which is already true after any WHU change.

## Checks it makes redundant

- **P153, the anchor cascade.** It becomes the assembler's resolution rule rather than a separate pass.
- **P100's already_removed bookkeeping.** A record removing a removed id is a no-op by construction.
- **P171's code-written-anchor rule at ruling time.** It becomes structural, since anchors can only be body ids. It
  should still stay, as the place where the fallback (the last body sentence bound to the source) is decided.
- **NotPlaced for a code-written line** in `Page.replace` / `insert_after`. That error can no longer arise.
- **Part of "bindings and page disagree"** (P104) and "records match the orchestrator's chain". The page becomes a
  function of the records, so the two can disagree only if the assembler is wrong. Both checks should stay, as the
  assembler's own test.

## Checks it does not make redundant

- safe_label / text_sweep (P163): the 01c class.
- Every check of what a sentence says: rule 1, quotations, coverage, overstatement, belief claims.
- The E2 rule (bind only sentences an applied record produced).

## Cost of replaying every recorded run through it

- **Model spend: $0.** Replays use recorded replies (reply_store; ~/Projects/whu-study-private/replies/ holds
  01, 01b, 01c, 01d and 04). The replay gate's 4 runs (02z–02zd) replay from raw > parsed > synthetic replies.
- **Compute:** about the pre-run check's 7–11 minutes per batch. About 30 minutes covers the gate's 4 runs plus the
  5 with stored replies.
- **The real cost is coverage, not money.** Once an assembled page differs from the recorded page at any sentence
  (ordering of tiled ADDs, a cascade resolved differently), every later recorded model call sees a different input.
  The replay then reports "unreplayable: new input" from that step on. Those replays would have to be read and
  re-baselined by a person, run by run. Until that is done, the replay gate covers less than it does today.

## Risks

1. **Precedence becomes explicit.** Two records on the same sentence (a ruling's replace and an audit cut, or two
   ADDs at one anchor) are resolved today by time order, implicitly. The assembler needs a written precedence rule.
   Writing it is a ruling on what the page says: category (a).
2. **Ids against fingerprints.** Bindings, verdicts, coverage units, protected-sentence comparisons and the
   first-draft check all key on fingerprints. A mapping layer is a new place for disagreement.
3. **Replay divergence,** as above. The replay gate loses coverage until the recorded runs are re-baselined.
4. **No paid run to validate it.** The trial line has $6.78, and the next run needs about $7. A change this size
   would first meet live model output after the trial, with only replays and rehearsals behind it.
5. **What it does not fix.** It addresses where edits go, not what an edit says. Of the three stops, one (01c) is
   untouched, and 01d's is already handled by P171.

## Recommendation (for the advisor's decision)

Not now. P153 and P171 close the two placement classes the redesign would close by construction. The sweeps show
no other recorded anchor outside the body (1 of 105). The redesign's main cost is losing replay coverage until a
person re-baselines the recorded runs, at the point where there is no money to validate live.

If it is wanted later, the cheaper first step is ids without a rewrite. Give each body sentence an id at the draft
and have omissions.json `after` name the id. This keeps the in-place editor and removes the fingerprint-drift risk.
It is about 150 lines in page.py, apply.py and ruling.py, and recorded runs replay unchanged, because fingerprints
remain the key wherever no id is recorded.
