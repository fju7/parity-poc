# STOP — do not publish. Remediation order.

Reviewer ruling, 8 September 2026, on CC's post-application report.
Page state 7e207eeeeaff81a8. Nothing to revert; nothing is committed.

---

## Why this stops

**The repo was never at 9 September.** `bindings.json` was clean at HEAD; the
revision existed only as loose files. Installing the page took unbound sentences
from 26 to 53. The packet the outside reviewer worked from claimed 42 inference
records; the repo can build 36.

That is not a bookkeeping gap. This publication's entire claim on a reader is
that every sentence is either bound to words in a document it holds or declared
a judgement and shown with its premises. A page with 53 unbound sentences does
not meet that description, and publishing it would make the page's own account
of itself false — which is a worse failure than any of the twenty-two findings
the review produced.

It also means the review was run against an artefact the repo could not
reproduce. The 42 records I verified in the bundle do not exist. Roughly 34
sentences of binding work was done in a working state that was never saved, and
the reviewer, the adjudication and the log entry all rest on it.

**Second blocker.** EORTC 18071 is cited three times on the page, including in
the reader-facing source list, and is not in the source store. The 8 September
entry as drafted says "The paper is now held and cited". That sentence would
publish a false claim about a document's status — the exact failure the
1 September correction was about, in the entry correcting it.

---

## My fourth error, and the pattern is now the finding

My verification addendum says "Sources entry carries DOI, PMID and PMCID." I
verified that against the rendered HTML. It is true of the page and false of the
store, and the store is what "held" means.

Four reviewer errors this round:

| # | What I did | What I concluded |
|---|---|---|
| RV-01 | read the `analyses` field | that a result was posted |
| RV-02 | took an interval from one hazard ratio | that it belonged to another |
| RV-03 | grepped 400 chars of a 1,013-char paragraph | that three sentences were absent | [figure corrected 2026-09-09; this originally read 2,116, which was never measured — see RV-08]
| RV-04 | checked the rendered HTML | that a document was in the source store |

All four are one error: **checking a partial or adjacent representation and
reporting a conclusion about the thing itself.** That is standing rule 2 —
an absence in our own view is not a fact about the world — committed four times
by the person who wrote it.

All four were caught by the implementation reading the base before acting
(standing rule 11), which is now four for four and is the strongest evidence in
this whole cycle that the rule earns its cost.

**Process doc amendment, to be made now, not later.** Add to §12 as failure 14:
*Verifying a rendering rather than the source of truth — the HTML rather than
the store, a field rather than the record, a truncation rather than the
paragraph.* Detection: name the artefact you actually read in the finding, so
the mismatch is visible before it is acted on. Add to the review prompt's
evidence discipline: **state which representation you checked.**

---

## CC's judgement call on 3a was right

Moving the page's own markup rather than the entry file's degraded copy — the
`data-whu="computed"` mark on the 3.35 arithmetic and the `<q>` tags on the
Merck quote — was correct and I did not anticipate it. Substituting the copy
would have turned a marked computation into unmarked prose demanding a source,
manufacturing a V3 failure out of a relocation. `furniture.py` passing at
2 computed / 5 restates / 1 scale confirms it.

---

## Remediation, in order

**1. Rebuild the bindings.** 53 unbound sentences down to zero, and the record
count back to at least the 42 the packet claimed. This is the bulk of the work
and everything else waits on it. Do not publish a partial pass: an issue that is
half-bound is harder to reason about than one that is unbound, because the
coverage statement in Appendix D becomes wrong rather than absent.

When it is done, rebuild the packet and record the new SHA. The bundle the
outside reviewer read is superseded and should be marked as such rather than
deleted.

**2. Put EORTC 18071 in the source store** with access state `full_text_held`
and the identifiers already on the page (DOI 10.1056/NEJMoa1611299, PMID
27717298, PMCID PMC5648545). Until it is there, the 8 September entry's "now
held and cited" clause must not publish. After it is there, the clause is true
and the 0.58 V3 failure clears.

**3. Re-key the 3.35 figure-exclusion** to the sentence the revision actually
left on the page. A stale exclusion is worse than none, because it reads as
coverage.

**4. Authorise the two extra log paragraphs.** My 4 September entry said four
misdated paragraphs; CC found six. My ruling on each:

- *"Statistical language"*, ending "corrected on 1 September; see the entry
  below" — **leave it.** A signposted forward reference to a later entry is not
  a misdated claim; it is a cross-reference, and the reader can follow it.
- *"What the evidence supports"*, narrating "On 3 September the rubric was
  published and the anchor turned out to read…" inline — **move it**, same
  treatment as the other three. It states a 3 September event under a 28 August
  heading with no signpost. Split it if only the tail is later-dated, exactly as
  3b splits "The third figure has not come back."

Update the 4 September entry's derivation note from "four paragraphs" to six,
and say that two were found by the implementation rather than the diff.

**5. The two blocked checks.**

- *negatives, on "narrowed only slightly"* — **take CC's alternative: drop
  "only".** "So the interval narrowed slightly" carries the same meaning and
  needs no disposition, no falsifier and no signature. Signing a quantifier
  disposition to preserve one word is the wrong trade.
- *sources_shown, 9 documents* — pre-existing, and it now matters more than it
  did. The Consensus sentence rests on the held sources agreeing; a reader who
  cannot see them cannot check it. **Fred's call**, but my recommendation is
  that it blocks: the page acquired a claim this round that depends on the list
  being visible.

**6. Fix `scan()`** — it conflates "not an empirical sentence" with "no longer
on the page", stamping live rows as departed. Not blocking, but it will corrupt
the binding work in item 1 if left, so fix it before item 1 rather than after.

**7. File hygiene.** Rename `2026-09-09-cc-directive-melanoma-REBASED.md` and
`2026-09-09-cc-directive-publish.md`. Delete the three `_1` download duplicates
— they carry the old date and the uncorrected text, and a duplicate of a
corrected document is a trap for whoever reads it next.

**8. Then the two things already scoped out:** the adjudication's second
signature, and filing the review, rebase note, addendum, adjudication and
process document into the issue directory. `publish.py` still reports that the
outside review has never been recorded, and that is true until item 8 is done.

---

## What does not change

Both scores stay 3.94 and 1.0. The six applied edits are correct and verified.
The twenty-two findings and their dispositions stand. Nothing in the substance
of the review is affected by any of this — what is affected is whether the
machinery can show its work, and right now it cannot.
