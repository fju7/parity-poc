# deskilling — adjudication of the outside review, 2026-08-30

Reviewed content: `2026-08-30-sent.html`, sha256 `3900205df166c3ba`

The review itself is in `2026-08-30-review.md` and is never edited after the fact,
including by us. This file sits beside it and is where our decisions go.

This file was written after the fact, on the evening of 2026-08-30. `send-for-review`
was never run for this issue — the reviewer was sent the page by hand — so nothing
created the snapshot or this template at the time. The snapshot was reconstructed from
commit `b589b6a`, and its hash matches the one written at the top of the review. That
gap is itself the finding: the review that stopped this issue publishing a false claim
existed for a day without being recorded anywhere the board could see.

Sections OR-nnn are the reviewer's findings. Sections POST-nnn are the changes made
after the review, each pointing at the file where its full reasoning lives, so that
`review-changes` resolves rather than treating a day of adjudicated work as unexplained.

---

## OR-001

**Finding**

> "So the honest position on a null result is that we do not have one."

BREACH — Question 3. Also a factual error as written. Pedersen et al., *Endoscopy*,
published online 3 June 2026, exposed endoscopists to CADe, removed it, and found no
deskilling. "The page can explain why it does not settle the matter, but it cannot
publish the statement that no null result exists."

**Disposition** — ACCEPT

**Reason**

Correct, and the most consequential thing anyone has said about this page. The study
had been in print for nearly three months when the piece was drafted. Two fact-check
runs passed over it. We had recorded the search as outstanding and wrote the sentence
anyway, which is the failure — not the missing paper, but publishing a universal
negative with the search still open.

**Change**

The sentence is gone. In its place the page carries the Pedersen trial in full, read
at source in the publisher's PDF: thirteen endoscopists, 5,013 colonoscopies, three
phases, the per-group figures with their intervals, the authors' own conclusion
verbatim, and — the best thing in either paper — the authors' own reconciliation with
the Polish study, which identifies a design difference we had not seen. The page also
now says plainly that it did not find this study and that a reviewer did. The later
statement about every measurement being three months or less was rewritten with it.

**Sources considered** — S043 (read in full), S021

---

## OR-002

**Finding**

> "We therefore do not know what it corrects or whether it touches any figure on this page."

BREACH — factual/support error. The Lancet correction is accessible and states what
was corrected.

**Disposition** — ACCEPT

**Reason**

Correct. Leaving a correction described as unread creates uncertainty the available
source resolves. An unread source is not a source that agrees with us, and it is not a
source that disagrees either — it is a thing to go and open.

**Change**

The correction was obtained and read. The page now says what it corrects: a covariate,
indication for colonoscopy, mistakenly omitted from the multivariable analysis in
supplementary table 6; two variables changed; the journal says interpretation is
unaffected. The page adds that one of the two affected findings is the exposure
variable itself in the adjusted model, and that the unadjusted headline figures it uses
are not the ones the correction touches. The request asking readers to obtain it is
gone, replaced by a record of the seven routes tried before it was read.

**Sources considered** — S021 and its correction notice

---

## POST-01 — the unsourced laboratory reconciliation, removed

A reconciliation of the two cytology laboratory counts (three of 48 accredited
laboratories closing before the 2019-20 consolidation) was put on the page from a
fact-check note without anyone opening NHS Digital. It read as our own reading of a
source we had never seen. Removed the same day; the page now says the two counts
differ and that we cannot say why, and cites the College's figures because those are
the ones we read.

Full reasoning: `../draft/2026-08-30-gate-adjudication.md`.

---

## POST-02 — findings from the gate, cycle 2

Every change in this class traces to a finding in a fact-check run and a written
decision in `backend/tests/fixtures/draft_decisions.json`. The adjudications are in
`../draft/2026-08-30-gate-adjudication.md`, which records what was verified at source
and what was rejected and why.

The substantive ones:

- **Fortune.** The page said nothing false had been printed. Fortune's article says the
  endoscopists went from 28.4% "with the technology" to 22.4% "after they no longer had
  access to the AI tools" — the exact design error this page is about. The paragraph now
  prints Fortune's sentence, the correction, and the fact that we had it wrong first.
- **Kosmyna 55/54.** The page carried the Comment's objection alone; the paper answers
  it, in a sentence the Comment does not address. Both are now on the page.
- **The Heudel abstract's second design error** — "reverted to non-AI procedures after
  repeated AI use" implies withdrawal, and there was none — added beside the first.
- **The Heudel citation** corrected from volume 11(C) to volume 12, with the proof-vs-
  registered-record discrepancy disclosed, and the title-vs-methods disagreement
  ("scoping review" against "a narrative review") noted.
- **"Nine months"** was nine months and twenty days. Both occurrences corrected.
- **The Weinberg and Bretthauer editorial**, found through a fact-check run, added as
  prior art with the disclosure that we found it after writing the section it qualifies.
- **The Levartovsky letter stays unread and unprinted.** A finding claimed its abstract
  was public and quoted it; Europe PMC carries no abstract, PubMed shows none, and the
  quoted phrase returns nothing on the open web. The paragraph was tightened, not
  reversed.

---

## POST-03 — findings from the counterexample hunt

Full reasoning: `../counterexample/2026-08-30-adjudication.md`, sections CE-01 to CE-09.

- **CE-02.** Professor Osmani named the volume rise at the Science Media Centre on the
  day of publication, and our sentence three paragraphs later read as though nobody had.
  Rewritten: the rise travelled, the reason for it did not.
- **CE-03.** "It carries caveats of its own... but none of this study's" dropped the
  noun, and a careful reader took it as "none of this study's findings". The noun is now
  on the page.

---

## POST-04 — source notes rewritten as documents were read at source

Provenance changes, not claim changes: entries in the source list rewritten when a
document moved from abstract to full text, from preprint to published form, or from
somebody else's summary to our own reading. Each is recorded in `../sources.json` under
that source's `access` block with what was read, by whom, on what date, and what was
not read. Includes the Rosbach preprint updated to its MELBA-published form, the Shaw
and Nave confidence sentence, the Weidlich audit read in the author's own copy, and the
Budzyń entry updated when the Warwick open-access manuscript was opened.
