# What Holds Up — how an issue gets made

**The Issue Process, version 1.0. Adopted 2026-09-09.**

Scope: everything from choosing a subject to publishing a correction. This is
the production process. It does not restate the editorial standards — the four
questions and the eleven rules live in `whatholdsup-outside-review-prompt.md`
and are binding on every stage below, not only on the review.

Relationship to other documents:

| document | governs | status |
|---|---|---|
| `whatholdsup-outside-review-prompt.md` | the four questions, the eleven rules, what counts as a finding, evidence discipline | current, referenced here, not duplicated |
| Standard version 1.1 | the four questions and the eleven rules | **reconciled 2026-09-09 — it is not a separate document.** See §1.5 |
| `docs/whatholdsup-open-gaps.md` | known blind spots in the machinery | current |
| `backend/scripts/whatholdsup/review_packet.py` | builds the outside-review packet | current |
| this document | the pipeline, the standing rules, the failure catalogue | new |

Every rule below carries the incident that produced it. That is deliberate. A
rule whose cost you cannot see is a rule people stop following, and every
standing rule in this document was bought with a specific error in a specific
issue.

---

## 0. The one-paragraph version

An issue is a claim about somebody else's evidence. Because that is what it is,
the only thing that makes it publishable is that every sentence in it is either
bound to words in a document we have opened, or declared a judgement and shown
with its premises. The machinery checks the first kind. Only a reader checks the
second kind. So the process is: acquire documents and open them, write sentences
and bind them, let the machine check what it can, then hand a reader everything
they need to argue with us — including a list of what we could not read and a
list of the sentences that assert nothing exists. Then decide, in writing, what
to do about what they found. Then publish the decision alongside the piece.

---

## 1. The stages

| # | Stage | Output | Gate to the next stage |
|---|---|---|---|
| 1 | Selection | subject, and the strongest version of the claim | can we state the claim as its proponents would? |
| 2 | Research | source store populated, access state per document | is every document we intend to cite **opened**? |
| 3 | Drafting and binding | draft page, every sentence bound or declared | does `spancheck` pass on every bound span? |
| 4 | Machine gate | `<page>.gate.json`, gate adjudication | ≤ 2 runs used; every finding adjudicated in writing |
| 5 | Internal pre-review | `YYYY-MM-DD-internal-pre-review.md` + `-actions.md` | actions taken or recorded as declined |
| 6 | Outside review | `YYYY-MM-DD-review.md`, saved verbatim | reviewer had the current build |
| 7 | Adjudication | `YYYY-MM-DD-adjudication.md` | every finding has a disposition and a reason |
| 8 | Publication | page + dated correction-log entry | log entry describes this round, dated today |
| 9 | Revision | back to stage 3, with rebase discipline | new SHA recorded; reviewers told which build |

Stages 4 through 8 repeat. Nothing skips stage 7.

---

## 1.5 Standard v1.1, reconciled

**There is no separate Standard document.** Standard v1.1 is the four questions
plus the eleven rules, and `whatholdsup-outside-review-prompt.md` carries them
verbatim. Checked 2026-09-09 against every citation of the standard in the cdk46
files:

| citation | says | prompt text | verdict |
|---|---|---|---|
| review, OR-001/002 | "Question 2 (what evidence actually supports it)" | Question 2, *What evidence actually supports it?* | exact |
| review, OR-003 | "Rule 7's concern with preserving the actual inferential framework" | Rule 7, *State the inferential framework before quoting a p-value* | same rule, paraphrased, correctly applied to a significance boundary |
| pre-review, OR-001 | "Rule 11 (a claim that a third party missed something must survive…)" | Rule 11, *…must survive somebody having said it* | exact |
| pre-review actions | "the record of having got it wrong belongs on the page under rule 10" | Rule 10, *Publish the correction history* | exact |

No drift. Nothing to reconcile in the sense of a conflict.

**Why the two sets do not collide.** The eleven rules are editorial — they
govern what the prose may claim. The twenty-one standing rules below are
procedural — they govern how the work is done. They are orthogonal, and that is
the whole relationship. Three connections should still be made explicit, because
a reader of one document should not have to derive them:

1. **Standing rules 15–18 are the operational content of Rule 10.** "Publish the
   correction history" is the obligation; dating each round, never retro-editing
   an entry, keeping the header and the log in agreement, and holding a
   correction notice to the standard of the piece are how it is discharged. They
   are not new rules and should not be argued with separately.
2. **Rule 8 is why the scorecard is two numbers.** "Distinguish confidence in
   direction from confidence in magnitude. These are separate questions and one
   verdict cannot express both." The 3 September split was compliance with an
   existing rule, not a new idea, and OR-006 and OR-018 of the melanoma
   adjudication are both downstream of it.
3. **Rule 5 governs the blinding caveat.** "Do not import a design criticism
   across designs — and the converse: saying blinding 'does not eliminate' a
   problem without saying what it does address overstates it." The functional-
   unblinding paragraph added at OR-015 is the exact case Rule 5 is about. As
   written it complies: it states what the double-blind design does address
   before adding what reactogenicity may leave open. **It sits close enough to
   the line that any future edit to it must be checked against Rule 5**, and the
   adjudication entry should name the rule.

**One forward gap.** The eleven rules are oncology-specific — hazard ratios,
composite endpoints, adjuvant designs, p-value framing. That is right for issues
one to three. The first issue that is not about a clinical trial will need either
a generalised rule set or a domain annex, and discovering that mid-issue is the
expensive way to find out. Raise it before the subject is chosen, not after.

---

## 2. Selection

Choose a claim, not a topic. "The melanoma result" is a topic; "intismeran plus
pembrolizumab improves recurrence-free survival in resected stage IIB–IV
melanoma" is a claim, and it is the thing the rubric scores.

Before research starts, write the claim in the form its own proponents would
endorse. This is question 1 of the standard and it is easiest to get right
before you have read the criticism. A piece that starts from the weakest version
of a claim never recovers, because every later stage checks it against evidence
rather than against fairness.

---

## 3. Research and the source store

Every document gets an id (`S001`…) and an **access state**:

| state | means |
|---|---|
| `full_text_held` | we have opened and read the whole document |
| `abstract_held` | we have the abstract only |
| `blocked` | we tried and could not get it |
| `not_opened` | we have it and have not read it |

**These states are load-bearing and they are published.** Appendix B of the
review packet prints them, and the rows we could not read in full are flagged to
the reviewer as the most valuable thing on the list.

**Standing rule 1 — no claim about a document we have not opened.** Not in the
page, not in a gate output, not in an adjudication.
*Origin:* the costliest error in cdk46 was a claim that a network meta-analysis
used stale MONARCH 3 data. It was generated by the gate's recency role and
repeated across three runs. No further runs could have caught it, because the
document was never opened.

**Standing rule 2 — an absence in our library is never a fact about the world.**
Every sentence scoped to what we hold must say so, in the sentence, in words a
reader can check against Appendix B.
*Origin:* on 1 September three figures were removed from the melanoma page as
appearing in no document we held. Two were real and were sitting in a document
we had acquired and never opened. On 3 September the page's own gate produced a
third document we had said stayed out "until somebody produces it".
*Corollary, added 2026-09-09:* a registry record that has not been updated since
before the event you are citing it about is a stale file, not a live absence.
Check `lastUpdatePostDate` before treating a registry silence as evidence, and
publish that date beside the claim.

**Standing rule 3 — `not_opened` is a debt, and the review packet collects it.**
Anything still `not_opened` or `blocked` at review time is flagged to the
reviewer with a request to reach it.
*Origin:* Spruance et al. sat `not_opened` in the melanoma manifest through four
rounds. It contains the proportional-hazards caveat the piece's central
explainer needed and a patient-level gloss the piece had told readers did not
exist.

---

## 4. Drafting and binding

Since 2 September, every sentence in an issue is either:

- **bound** — tied to a span in a document we hold, verifiable byte-for-byte by
  `spancheck.b2_present(span, issue, source_id)`; or
- **declared a judgement** — bucket `judgement`, carrying its premises (each a
  `source_id` + `span`) and the step taken from those words to the claim.

Judgements become Appendix A of the review packet. Bound figures become the
thing the machine can check.

**Standing rule 4 — the binding coverage rule is wider than "inference".**
Anything that is not a direct restatement of a span needs a record. That
includes: a claim about what a document says (as opposed to a quote from it), a
description of how two figures relate, and a comparison between two numbers.
*Origin:* three of the six factual errors found in the 9 September melanoma
review were in sentences with no record among the 37 — a claim about what a
registry said, a description of which way two interval bounds moved, and a
contrast between two adverse-event figures. All three are inference-shaped. None
was recorded. That is not a coincidence; it is where the errors live.

**Standing rule 5 — a structural change sweeps its dependants.** When a score,
a section or a definition changes, grep for every sentence that describes it.
*Origin:* the melanoma scorecard was split into two scores on 3 September. The
sentence predicting how the score would move survived the split by six days,
describing a single composite that no longer existed.

---

## 5. The machine gate

The gate reads the page in roles — fact-check, source advocate, counterexample
hunt, recency — and emits `<page>.gate.json`: claims marked VERIFIED /
NOT_FOUND / WRONG_VALUE, plus objections and inferences.

**Standing rule 6 — `RUNS_PER_CYCLE = 2`. Two runs before review, one after.**
*Origin:* the cap exists because gate runs are not free ($10.89, 27 API calls
and 134 web searches for one run of one issue) and because they have diminishing
returns against a fixed weakness: each role reads the page alone, none audits
another's output, and none holds two distant paragraphs together. Fourteen gate
runs on the cdk46 assessment found none of the three findings the outside review
found.

**Standing rule 7 — every gate run is adjudicated in one pass, and every edit
made at once.** That is what the cap is for.

**Standing rule 8 — report what a check tests, never what it appears to
guarantee.** If prose describes a check, the prose must be narrower than the
check, not wider.
*Origin:* twice. On 1 September a check reporting "this figure is in nothing we
hold" — which says in its own output that a miss is not a falsehood — was
written up as the figures having "come from no document" and one existing
"nowhere". The 2 September entry named this the failure worth keeping in view.
On 4 September the Sources block claimed every number traced to a primary
document "and none to a news report — a check that runs before this page can
publish refuses it otherwise". The check tests span presence, figure provenance
against held documents, and source representation. It has no opinion on what
counts as news. The failure recurred within a week of being named.

**What the gate cannot do, and what to stop expecting of it.** It cannot check a
step from facts to a conclusion. It cannot find a counterexample to a universal
negative. It cannot hold two passages several thousand words apart in mind at
once. It cannot notice what a piece left out. Those four are the outside
reviewer's job and the reason the review step exists.

---

## 5.5 Passage reading

**Added 10 September 2026. It sits after binding and before verification.**

Nine stages, and every one of them operated on a sentence, a figure, a span or a
document. **Nothing ever looked at a paragraph whole and asked whether it held
together.** That is why a passage could say *"we have now read it"* and, four
sentences later, that we could not know what it touched *"because that requires
reading it"*, with every gate green.

This is a **reading, not a detector**, which is why it exists from today without
being built or validated. Four questions, per passage:

1. **Do any two sentences here contradict each other?**
2. **Does any sentence assert a state — what we hold, have read, can reach, have
   checked — that another sentence or the store contradicts?**
3. **Could a careful reader leave this passage believing something false that no
   sentence in it states?**
4. **Is a reader asked to hold anything in suspension longer than the passage
   supports?**
5. **Do the words introducing each quotation assert a history the record
   holds?** A quotation is checked against its source; the words introducing it
   are checked against the record. "The page now says", "it later said", "this
   was added" assert a history. A label that implies a change the record does
   not hold is an error even when every quoted character is exact.

   *Added 11 September 2026 as a fifth question rather than a clause of Q2,
   because Q2 as run tests the quotation and stops: the instance below survived
   a full run of Q2 with every quoted character verified. A separate question
   is asked separately. The instance: the correction notice for issue two
   introduced an exact quotation of the page's sourcing sentence with "The page
   now says" — a sentence that had named comparative studies in every published
   version, and whose wording was tightened on 30 August without changing that.
   The label implied the page had once carried the email's error. Q2 passed it
   because the quotation was exact; the advisor caught it on the label.*

Run it **twice**: at passage scope, then at whole-page scope including the
appendices and the change log. The same four questions have different answers at
different distances, and an impression can be created by the arrangement of
passages that no single passage creates.

**Question 3 is the one nothing else asks, and it is the whole of what "fair"
adds to "accurate".** A page can be true sentence by sentence and leave a false
impression, and every sentence-scoped check in this apparatus will pass it. That
gap is the exact thing this publication exists to point at in other people's
work, and it has been unguarded in its own since issue one.

**Question 4 is the KOL Pulse question**, written so it can be answered rather
than argued about.

### What the acceptance stage is for, shown once

On 10 September 2026 the session preparing an acceptance block added, unprompted, a note
above the signature: **the verification record was performed against sha
`7ae5304c…`, and the page has moved twice since — yesterday's publication and
today's correction — so that record does not cover the current bytes;
`confirm-review` is what carries it forward.**

Nobody asked for it. It is not a check's output and no rule required it. It is
what a stage staffed by a reader produces and a stage staffed by a checklist does
not: **noticing that a document's stated basis had quietly stopped matching the
thing it was about to be used for.**

Recorded as the worked example of why this stage is a reading rather than a
detector. The four questions below are what to ask; this is what asking them
looks like when the answer is something nobody thought to ask about.

### The email can never be fully derived, and the boundary is stated

**10 September 2026.** A correction email has three parts. Two are derivable from the
record — *what changed* and *why, including how we found it*. The third —
**what you should now believe that differs from what you believed before** — is
a claim about a reader's mind. **No record contains it.**

So the email is **part derived, part written, and the boundary is explicit rather
than hidden.** That matters because a hidden boundary is how a hand-written
sentence acquires a derived sentence's authority: a reader of a mostly-generated
document assumes all of it was generated.

> **REQUIRED: part 3 goes through this stage's four questions before any send.**

Hand-written prose about our own error, under time pressure, by the party that
made it, is the exact class this stage exists for — and it is the one part of
that email nothing else touches. Its first run, on 10 September 2026, changed a sentence:
*"What their paper does establish is stronger for the piece"* told a reader how
to feel about our own correction, inside the correction, in the flattering
direction. It now states what the paper establishes and says whether that helps
or hurts is the reader's to judge.

### Its worklist comes from the epistemic check

`epistemic.py` does not adjudicate; **it triages.** Every sentence it reports as
**NOT EVALUATED** — subject not resolvable, or source unclassified — is a
sentence making a claim about what we hold or have read that no machine could
check. **That list is this stage's worklist**, and it is the join between the
mechanical third of the coherence problem and the two thirds that are a reading.

The machine narrows the field; the reader decides. On 10 September 2026 the field is 89
sentences across three issues, of which 88 are unevaluable — which is a large
worklist and an honest one.

### Who performs it

**Every passage-level and whole-level catch in this cycle came from the
operator.** *"Is my signature window dressing."* *"The homepage says 28 August."*
*"We can't paper over this."* None of those is a sentence-level finding and none
of them could have been. The stage has been staffed by one person who was not
named in this document as performing it, and naming it does two things: it stops
the work being invisible, and it makes clear what kind of work it is.

Machine readers may **assist** at this stage. Their agreement is weak evidence
here — the shared-blind-spot limit at §14 applies, and three of them misread one
box between them.

---

## 6. Internal pre-review

One reader inside the process, before the packet goes out. Output is a review
file and an actions file. Its value is that it costs nothing to run and it
catches the class of error the gate structurally cannot — the cdk46 internal
pre-review found the same failure the outside review later found in a different
sentence.

---

## 7. The outside review

Governed by `whatholdsup-outside-review-prompt.md`. Read it; do not summarise it
from memory. The essentials that belong in *this* document because they are
process rather than instruction:

**What the reviewer gets:** the current page, plus Appendix A (every inference
with its premises and its step), Appendix B (what we hold and what we could not
read), Appendix C (the universal negatives, listed), Appendix D (where our own
machinery has not looked).

**What the reviewer does not get:** our gate report and our adjudication record.
A reader shown our findings anchors on them. The cost is that they may raise
things we have settled; that cost is paid in adjudication, and independence is
the whole asset.

**Standing rule 9 — the reviewer must be given the current build, and must
verify it themselves.** The packet header states the page's SHA and build date.
The reviewer's first action is to check for a newer `for-reviewer` build in the
output directory, not to trust the attachment.
*Origin:* twice. The 28 August reviewer read `bd101cd121688ead` while 208 prose
changes went in behind them. The 8 September reviewer was handed the 3 September
packet when the 4 September build was live, and four of twenty-two findings were
already fixed before the review began. The bundle warns about this in its own
header and it happened anyway.

**Standing rule 10 — the review is saved verbatim and never edited after the
fact, including by us.** Corrections, rebases and reviewer errors go in
*separate* dated files beside it.

---

## 8. Adjudication

**This is the step that makes the rest of it real.** A review with no
adjudication is a document nobody has to answer.

File: `YYYY-MM-DD-adjudication.md`, beside the review. Header carries the
reviewed content's filename and SHA, and the standard version.

Per finding: **Finding** (the quote plus the breach), **Disposition**
(ACCEPT / REJECT / PARTIAL / NOT ACTED ON), **Reason**, **Change** (the actual
new text), **Sources considered**.

Then: **Outstanding after this adjudication** — carried items, new items, and
anything deliberately not done, "recorded here so that its absence is a decision
rather than an oversight". Then **What this review demonstrated** — what the
machinery missed and why, which is how the process learns.

**Standing rule 11 — every source the reviewer cites is opened and read here
before any change is made.** This is standing rule 1 applied to review findings,
and it is the rule that most earns its keep: it has twice caught a reviewer
error before it reached the page.
*Origin:* the 9 September melanoma reviewer confirmed a claim by reading one
registry field and not the field that decides it, and separately proposed
attaching an 80% confidence interval to the wrong hazard ratio. Both would have
put errors on the page. Both were caught by opening the documents.

**Standing rule 12 — reviewer errors are adjudicated and recorded, as RV-nn.** A
log that only ever reports the reviewer catching us describes something that did
not happen.

**Standing rule 13 — the adjudication is verified by someone who did not write
it, and accepted by someone answerable for it.** Two acts, and they may be two
different kinds of reader.

*Verification* requires independence from authorship, not humanness. A session
that never wrote the entries, reading them against the page and the artifacts,
supplies it. Verification confirms four things: every ACCEPT actually landed on
the page; each disposition matches what was decided rather than what reads well
afterwards; nothing was quietly dropped; and the RV entries are honest. Read the
RV entries hardest — they are where a reviewer assessed their own errors, and a
reviewer writing up their own mistakes will describe them as narrower than they
were. An RV entry that reads tidier than what happened is itself a finding, and
worth more than the entry it corrects. The verification is recorded as it is
performed: for each entry, the disposition checked, the artifact opened to check
it, and the verdict. A verification that records only its conclusion is an
assertion of the same kind as the ones it is checking, and the acceptance
signature would then attest to something unaudited.

*Acceptance* is the operator's, and it is not a second verification. It attests
that the verification was done by someone who did not author the work, and that
its result is accepted. Signing without that having happened records that two
readers looked when one did, which is the same class of untruth as a log
paragraph dated before the event it describes.

A verifier does not edit what they are verifying. A discrepancy is reported and
returned; the correction is a separate act by a separate hand, and is itself
subject to verification.

The author of the adjudication may supply neither act.

*Origin:* the 9 September melanoma adjudication was drafted by its own reviewer,
who then made six errors in the same cycle and wrote the six entries assessing
them. The first version of this rule asked for a second human editor this
operation does not have, and an unmeetable rule is waived rather than followed —
so it was rewritten into the two acts it was reaching for. The prohibition on
self-adjudication is unchanged and is now stated where it belongs, at the end.

**Standing rule 14 — every change to the page reconciles to a written
decision.** `publish.reconcile(issue)` reports the ratio. A change with no
decision is not a small bookkeeping matter; it is a change nobody can explain
later.
*Origin:* 175 of 208 melanoma prose changes between 28 August and 4 September
reconcile to no written decision. The adjudication practice began with issue two
on 29 August; issue one was already published and in revision and was never
brought under it. Those justifications cannot be recovered.
**And they will not be reconstructed.** Rationale written after the fact reads as
more confident than the decision it replaces, because it is written knowing the
change survived. Where the record is empty, the log says the record is empty.

---

## 9. Publication and the correction log

**Standing rule 15 — every round gets its own dated entry, on the day it
happened.** The entry describes what changed in *that* round.

**Standing rule 16 — entries are never retro-edited to absorb later events.** A
superseded entry is kept and marked superseded; new facts go in a new dated
entry that quotes the old one.
*Origin:* on the melanoma page, three paragraphs describing 3 September events
were filed under "Updated 28 August 2026", and a fourth was edited in place
inside the 2 September entry so that it read "On 3 September our own page gate
produced it". The log asserted we knew things on dates before we knew them. This
is the same failure as an undated change, pointed the other way, and it happened
inside an entry whose own text says superseded entries are kept rather than
deleted.

**Standing rule 17 — the header date and the log agree.** If the header says the
page was updated on a date, the log explains that date.
*Origin:* the melanoma header claimed "Updated 4 September 2026" for five days
with no 4 September entry in the log.

**Standing rule 18 — a correction notice is held to the standard of the piece.**
Do not accuse yourself of more than you did, and do not describe a check as
having said more than it said.
*Origin:* "Accusing ourselves of inventing figures we had not invented is a
worse failure than the missing intervals."

---

## 10. Revision rounds

**Standing rule 19 — the page's SHA is the version.** Record it in the packet
header, in the adjudication header, and in any directive sent to an
implementer.

**Standing rule 20 — a directive that does not match its base is stopped, not
partially applied.** The implementer's instruction is: if any required edit span
does not match, stop and report which one.
*Origin:* the 8 September melanoma directive was written against a superseded
packet. Applied mechanically it would have reverted a correct paragraph to an
earlier wrong one. It was caught because the implementer stopped at the first
mismatch instead of adapting around it.

**Standing rule 22 — search nearest first.** Before asserting that a document
cannot be reached, query every identifier the record already holds. A negative
about the outside world is not established until the inside of our own store has
been exhausted.
*Origin:* on 2026-09-09 four searches of the outside world — Europe PMC full
text, the journal's own listing, the open web, and every file in the operator's
Downloads folder — were run and declared exhaustive on S028, while the DOI and
PMID sitting in that source's own record went unqueried. Both resolved
immediately, and Crossref returned the publisher's deposited reference list
carrying the exact citation the claim turned on. The instruction issued on the
strength of that "exhaustive" search would have written a false statement into
`sources.json` and `corrections.md`. RV-09.

**Standing rule 21 — when a rebase is needed, rebase the directive, do not
adapt the edits.** Then say in writing which items are withdrawn, which survive,
and which were wrong.

---

## 11. The standing rules, collected

1. No claim about a document we have not opened.
2. An absence in our library is never a fact about the world.
3. `not_opened` is a debt; the packet collects it.
4. Binding coverage is wider than "inference".
5. A structural change sweeps its dependants.
6. Two gate runs before review, one after.
7. One adjudication pass per gate run; all edits at once.
8. Report what a check tests, never what it appears to guarantee.
9. The reviewer gets the current build and verifies it themselves.
10. The review is saved verbatim, never edited after the fact.
11. Every source a reviewer cites is opened before any change is made.
12. Reviewer errors are adjudicated and recorded.
13. The adjudication is verified by a non-author and accepted by the operator;
    the author of the adjudication supplies neither.
14. Every change reconciles to a written decision; empty records stay empty.
15. Every round gets its own dated log entry. *(Rule 10)*
16. Log entries are never retro-edited to absorb later events. *(Rule 10)*
17. The header date and the log agree. *(Rule 10)*
18. A correction notice is held to the standard of the piece. *(Rule 10)*
19. The SHA is the version.
20. A directive that does not match its base is stopped, not partly applied.
21. Rebase the directive, not the edits.
22. Search nearest first: query the identifiers we already hold before
    asserting a document cannot be reached.
23. A rehearsal exercises the shipping path. It does not resemble it.
24. Repairing a guard is maintenance; changing one to get past it is not.
    The test is whether the edit is worth making when nothing is blocked.
25. A finding about a document is checked against the document. A checker's
    inability to reach a source is a fact about the checker.
26. Provenance is recorded when a figure is taken, never reconstructed by
    searching for it afterwards.
27. Decompose before deferring, and price the parts, not the whole.
28. Record a defect and proceed only where proceeding does not run through it.
29. Write the new artefact before removing the old, and never through a pipe.
30. Never cache an empty result, and never trust one.
31. A notice derived from a verified record may contain exactly three kinds of
    sentence: (i) quotation of what we published or sent, (ii) restatement of
    what the record says was changed and why, and (iii) what follows for a
    reader from (i) and (ii) together. It may not introduce a fact, figure,
    quotation or argument that appears in neither the record nor the document
    being corrected. Anything worth asserting that fails this test belongs in
    an issue, under the issue's apparatus, before it belongs in a notice.

    *Reason, 11 September 2026: this rule was first written in a form that
    would have deleted the "what you should now believe" section, which is the
    purpose of a correction notice. A rule that forbids assertion must still
    permit entailment.*

    Clarifications, 11 September 2026:
    (a) "The record" means the issue's record files — corrections.md,
        changes.json, attributions.json, reviews.json and their kin — not
        corrections.md alone.
    (b) A notice may state what a technical term means where the correction
        cannot be understood without it, provided the statement is general —
        true of any data, not a claim about these data — and provided the
        meaning is not itself the thing being corrected.
    (c) A notice may state what a corrected page now says, where the statement
        has been checked against the published bytes.
    (d) A notice may state facts about this publication's own operation — why
        a notice is late, what was built — provided each such sentence has
        something in the repository behind it. Sentences of this kind are
        checked against the record like any other; the first two ever written
        were wrong.

    *Reason for the amendment: the rule was written from a single example and
    met the whole document only at classification.*

32. A quotation ends where the source ends, or the truncation is marked. A
    quotation is never closed with punctuation the source does not have.
    Truncation that removes a qualifier is a misquotation even when every
    quoted word is correct — and a truncation that makes us look worse is not
    made safe by being against ourselves.

---

## 11.5 The remedy list

**A catalogue with only failures in it teaches what to fear and not what to do.**
This is the other list. It is short on purpose: one remedy has done nearly all
the work.

### Derive at the point of use, rather than transcribe

**A value that is read from its source each time it is needed cannot drift from
it.** A value copied into a second place can, will, and will do so silently —
which is what every entry in the catalogue below has in common.

Five applications as of 10 September 2026, all of them replacing something a person had
written down:

| what | derived from | what it replaced |
|---|---|---|
| `EDITORIAL_TZ` and the index dates | `published.json`, converted at display time | dates typed into the homepage once and never read again |
| `record_begins()` | the earliest `at` in the record | the assumption that the record reaches back to the page |
| `jsonio.write()` | the file's own existing indentation | remembering which file uses `indent=1` and which uses `2` |
| `open_list.py` | the checks' own outputs | an acceptance list assembled from memory |
| a figure exclusion's `in_sentence` | `corrections_check.sentences()` | prose retyped by hand, which failed on one space |

**The last one is the smallest and the most instructive.** A declaration written
by hand against prose that a machine normalises is a hand-maintained
representation of a machine-derived one — and it failed within the hour, on a
space before a full stop, in the one file whose purpose is to hold a person's
signature.

**The test of whether a remedy is this one:** could the two copies ever disagree,
and would anything notice? If yes to the first and no to the second, derive it.

---

### A rehearsal exercises the shipping path, rather than resembling it

*Established 10 September 2026, building the correction sender.*

The first version of the sender rehearsed through `send_test_email.py` and was
refused. The two senders guard unsubscribe in opposite directions, and
`send_broadcast.py` says so itself:

> "the guards below are the inverse of the ones in send_test_email.py. There, the
> check is that an unsubscribe is present in every part. Here, the check is that
> the RESEND MERGE TAG is present in the HTML."

A broadcast is expanded by Resend at send time, so only Resend can fill the
per-recipient link and the HTML must carry `{{{RESEND_UNSUBSCRIBE_URL}}}` unfilled.
A test email names one recipient, so it signs the URL itself and an unfilled merge
tag is an unusable unsubscribe. One body cannot satisfy both.

**The available workaround was to render two variants, and it is the trap.** The
general form is worth stating at full weight, because the reasoning that makes it
attractive is always the same and always sounds like diligence:

> **A rehearsal that differs from the shipping path differs precisely where it can
> least afford to.** The thing a rehearsal cannot share is the environment-specific
> element — the credential, the recipient list, the merge tag the platform fills in
> — and that is exactly the element that breaks in production, because it is the
> only part that was never exercised. Rendering two unsubscribe variants would have
> put the difference in the single element most likely to be wrong, and then
> reported the rehearsal as evidence about the other one.

So the rehearsal is a **broadcast to a segment containing only test addresses**:
the same API call, the same body, the same merge tag, the same code path, and a
different list. The list is the only thing a rehearsal is permitted to vary,
because the list is the only thing a rehearsal is *for*.

**This is failure 15's shape in a new place.** A green result is only as
informative as the scope of the run that produced it, and a rehearsal of
different bytes reports on bytes nobody is going to send.

---

## 11.6 The publish sequence, and why its order is not a matter of care

**Required order, established 10 September 2026:**

```
publish.py dateline <slug>      # FIRST — it changes the page bytes
record / re-pin the change set   # pins from_sha and to_sha
publish.py confirm-review <slug> # binds to the current bytes
changecheck.py <slug> --before <last published rev>
publish.py publish <slug> --yes  # with any waive, named
```

**The reason is not tidiness, and ordering discipline does not solve it.**

The masthead dateline is derived from `editorial_today()`. **It changes by
itself.** Any publish sequence that crosses midnight in New York invalidates its
own `confirm-review` and un-pins its own change set — **regardless of whether
anyone got the order wrong.** On 10 September 2026 that happened across two days, because
the acceptance was prepared on one and signed on the next. It will happen to
somebody working late on a single evening, and they will have done nothing wrong.

> **A time-derived field inside a sha-pinned workflow is unstable by
> construction.** Ordering discipline narrows the window; it cannot close it.

**The durable fix is that `publish` should set the dateline atomically as part of
publishing**, rather than as a separate earlier step whose result something else
has to be pinned against. Not built 10 September 2026 — recorded so that the next person
who hits this reads a known property rather than diagnoses it again.

**And the change set is state, not a record.** Re-pinning `to_sha` after the
dateline moved is required, not retro-editing: §13's distinction settles it — a
dated finding must not be retro-edited, a live status list must be kept current,
and a change set is the second kind. The previous value is kept in `to_sha_was`
rather than overwritten silently. **The operator's signature is unaffected**: it
cites the verification record and the sha that record was performed against,
neither of which moves, so **no fresh signature is required and none should be
requested.**

---

## 12. The failure catalogue

The ways this publication has actually been wrong, and what catches each.

*No count appears in this sentence. It said "fourteen" while the table below held twenty — a hand-maintained tally in prose, drifting beside the list it describes, which is RV-10's exact failure sitting inside the failure catalogue. The list is the count.*

| # | Failure | Caught by |
|---|---|---|
| 1 | Treating an absence in our library as a fact about the world | rule 2; reviewer |
| 2 | Prose overstating what a check provides | rule 8; reviewer |
| 3 | Two correctly sourced figures placed in a contrast neither can bear | reviewer; rule 4 record |
| 4 | A sentence with no binding record carrying a factual claim | rule 4 |
| 5 | A change with no written decision | rule 14; `reconcile()` |
| 6 | Log entries retro-edited or misdated | rules 15–17 |
| 7 | Reviewing a stale base | rules 9, 19, 20 |
| 8 | A dependant sentence not swept after a structural change | rule 5 |
| 9 | The gate generating a false claim and repeating it across runs | rules 1, 6 |
| 10 | Two distant passages never held together | outside reviewer only |
| 11 | A scoped claim padding its denominator with a case that cannot answer | outside reviewer; Appendix C |
| 12 | A printed composite not matching its own working | publish check |
| 13 | Reviewer error — reading one field, not the deciding one | rule 11 |
| 14 | Verifying a rendering rather than the source of truth — the HTML rather than the store, a field rather than the record, a truncation rather than the paragraph | rule 11; name the artefact you read |
| 15 | A check that examines part of what its name describes, and reports the unexamined part as passing | scope stated in the check's own docstring |
| 16 | A protective construct whose triggering condition was never tested — a guard that catches nothing, a stop wired to a probe that cannot fire, a test containing `or True` | the construct must be made to fire once |
| 17 | A check whose condition is sound and whose message names a cause that is not the cause | read the message as if you did not already know the answer |
| 18 | A defect deferred whole, on an estimate of cost made by the person who benefits from the estimate being high | decompose it, then defer the parts that survive |
| 19 | A test set drawn from known incidents, mistaken for a test of the problem | run the new check against the whole corpus before wiring it anywhere |
| 20 | A datum edited to make a check pass — reasoning from the symptom, in the data layer | ask what the datum IS, never what value would silence the check |
| 21 | A normalisation step that destroys the very difference the comparison exists to find | compare the raw objects once before normalising |
| 22 | A rehearsal that resembles the shipping path instead of exercising it | the rehearsal runs the shipping code, on the shipping body, differing only in the list |
| 23 | Concluding a working guard is broken, from a run performed under the wrong interpreter | run the guard the way the guard runs itself |
| 24 | Reading a checker's confidence as its accuracy, when the two run opposite | the hedges are the signal; a categorical finding about an unreachable source is a lead |
| 25 | Sourcing a figure by finding it somewhere, when the same figure appears in two documents for different reasons | provenance is recorded, never inferred from a match |
| 26 | Recording a defect, then routing the next action through the thing recorded | "record it and proceed" requires that proceeding not depend on it |
| 27 | Destroying the evidence for the thing you are about to diagnose | write the new artefact before removing the old; a pipe is a deletion too |
| 28 | A fix scoped to the cases it was written for, meeting the first case it did not anticipate | fix the resolution rule, never the case list |
| 29 | Caching a negative result, which makes the failure permanent | a cache of "nothing" is not a cache of a value |
| 30 | Paying to confirm a result already derivable from what is on disk | failure 18 applied to spending: decompose what the spend buys |
| 31 | Improving a correction indefinitely, while the cost of delay falls on someone else | at the last change the bar becomes "is this false", not "could this be better" |
| 32 | Trusting a downgrade-only control for its direction, when the direction only guards against false blocks | measure what each downgrade rests on; a pointer to the wrong document is a false reassurance, not a weak finding |
| 33 | An urgency argument from an unverified number, used to argue for less verification | the number that sets the bar is measured before the bar is set; "who bears the cost" is a count, not a premise |
| 34 | A self-description in a correction notice, wrong in the flattering direction ("corrected the same day" — the record says 31 August, 1 September, 9 September) | every sentence about our own operation is classified against the record before it goes out; it was caught only that way |

### 12s. A downgrade-only control is safe against false blocks, and against nothing else

*11 September 2026, step 48. The reachability matcher, on the day it was built and
endorsed.*

The argument for a crude figure-matcher was its direction: it can only mark a
finding LEAD, never VERIFIED, so a coincidental match costs at most a finding a
human still reads. Written into the module's docstring, endorsed in review, and
true — for one of the two ways a control can be wrong.

> A control that can only weaken a finding cannot produce a **false block**. It
> can still produce a **false reassurance**: "we hold the settling bytes, here is
> the sentence" — said of bytes we do not hold, about a sentence that is about
> something else. The direction bounds the first error and says nothing about
> the second. Once the control downgrades on coincidences, the direction it can
> move protects nothing, and whatever safety it had was coming from it being
> right, not from which way it could be wrong.

Measured: of sixteen leads on run 3, two rest only on `34.9` — a token in six
documents that the matcher, stopping at the first in sort order, resolved to a
PALOMA paper when the melanoma paper eight entries later held the settling
sentence. A third rests on `0.051`, in two documents, both coincidences, for a
figure no held document contains — and that one is the graver kind: not a right
conclusion through a wrong pointer but a **wrong conclusion**, "we hold this"
said of a figure `bindings.json` had recorded as not held since 1 September. The
labeller never read the ledger built to answer its question. Filed separately
in open-gaps under "Lead 10".

The general form: **asymmetry arguments name the error they bound and are
silent about the other one.** When a control's safety is argued from its
direction, ask what the direction does not bound, and measure that.

---

### 12p. A cache of a negative result is a different object from a cache of a positive one

*11 September 2026, in `reachability.py`, on the day it was written.*

`held_text()` cached its extraction so 65 documents would not be re-read every
run. Its first call arrived with a slug that indexed nothing, extracted nothing,
and **wrote `{}` to the cache**. Every later call read the `{}` back and reported
"no held sources" without touching the library again. The bug that would have
been visible on run two was made invisible by the optimisation.

> **Caching a value says "this is what it is". Caching an empty says "there is
> nothing", and that is a claim about the world made from one failed attempt.**
> A cache of a negative result converts a transient failure into a permanent
> one, and removes the evidence that it was ever transient.

Never write an empty, and never trust one. This is the 1 September principle
again — *a failure to find is not a fact about what exists* — appearing this time
inside a cache, which is the last place anyone looks.

Two smaller defects found in the same hour, both by running the thing rather
than by reading it: it was never called with a resolvable slug, and it printed
`h["figure"]` on a hit that carried a phrase instead.

---

### 12o. A fix scoped to the cases it was written for fails on the first case it did not anticipate

*11 September 2026. The glob finding, third form.*

`issue_slug_for()` exists because `Path(draft).stem` was not a slug: the email
`issue2-cdk46.html` resolved to an issue called `issue2-cdk46`, and **every email
gate run this project had ever done was recorded against it**, so email spend had
never counted toward the $40 cap. That was found and fixed on 1 September, and
the docstring records it at length.

The fix resolves a stem against the case directories and **falls back to the stem**
when nothing matches. A correction email is a document type that fix never saw:
`2026-09-10-corrections` matches no case, so it falls back — and today's **$10.05
across three gate runs is charged to a pseudo-issue that counts toward no cap.**
The same failure, in the same function, by the same mechanism the fix was written
to stop, one document type later.

> The tell is a fix that enumerates: it names the cases it knows and defaults for
> the rest. **The default is where the next instance lands**, and a default that
> silently invents an identifier is a default that hides it.

Recorded, not fixed. The cap is a control and rewiring how spend is attributed
belongs in its own pass, not at the end of a send.

---

### 12q. The last change: the bar becomes "is this false", not "could this be better"

*11 September 2026, thirteen days after the error it corrects.*

Every change made to this correction notice was defensible on its own. Name the
endpoint. Name the source and cutoff. Qualify Tanguy in their own terms. Give the
arm-level counts. Each one genuinely improved it, and each one delayed it.

> **There is always one more improvement, and each is defensible alone.** The
> asymmetry is that every decision to improve the notice is made by us, while the
> cost of the delay falls on the person the error was about. A process with no
> declared last change will keep finding improvements for as long as anyone keeps
> looking, and will experience each delay as diligence.

So the last change is declared, and after it the question changes:

    before   would this be better?
    after    is this false as it stands?

Only the second blocks. This is the direction column applied to our own process
rather than to a finding: an error that flatters survives because nobody
questions it, and **a delay that looks like care survives for exactly the same
reason.**

*Amended 11 September 2026 (failure 33, RV-12 in open-gaps). The cost this entry
rests on — delay falling on a named researcher in "subscribers' inboxes" — was
asserted for thirteen days on a number nobody had counted. The list held two
contacts, both internal. The principle stands; the premise it was argued from
did not, and the argument was used to lower the bar on verification. The number
that sets the bar is measured before the bar is set.*

---

### 12r. Failure 18 applied to spending

Run 3's report is on disk, and the block decision is a pure function of it. The
replay therefore answers "would a fourth run block?" exactly, for nothing.
Running the gate again to *confirm* what the replay already established would
cost $3.65 and buy no information.

> Before spending, decompose what the spend buys into what is already known and
> what is not. **Paying to confirm the known is failure 18 with money instead of
> effort** — an undecomposed estimate, where the part that would actually be
> informative is priced together with the part that would not.

The gate's own cap says the same thing from the other direction: *"runs past it
stop paying."*

---

### 12n. Destroying the evidence for the thing you are about to diagnose

*11 September 2026. Twice, same day, same hand, same shape — which is why it is
one entry and not two.*

- `rm -f …gate.json` cleared the run-2 report before a third run that **refused on
  the cap and wrote nothing**. The report was the evidence for the residue I was
  then instructed to adjudicate.
- The third run was invoked through `| tail -35`, so the captured log holds 37
  lines. Everything the new labelling printed about why it found nothing went to
  the pipe, and the diagnosis had to be reconstructed from the report instead.

> **Do not remove the old evidence until the new evidence exists, and do not
> filter it away either.** A clear-then-regenerate is two steps that look like
> one, and anything refusing between them leaves nothing. **A pipe is a deletion
> that does not look like one** — it destroys on the way past, while appearing to
> be a way of reading.

What limited the damage both times was accidental: the cap ledger lives in a
separate file and survived, and the findings had already been quoted in full into
a report. Luck, in the same shape as the `.venv` fallback and the hook that got
the right answer for the wrong reason.

---

### 12m. "Record it and proceed" is only honest when proceeding does not depend on the thing recorded

*11 September 2026. The reviewer's, and caught by the operator asking why —
the second time in one day.*

Having established that the fact-check gate cannot reach the library, and that
five SERIOUS findings were false in consequence, the reviewer wrote: record the
defect, do not fix it today, and then **run the defective checker again at $3.50**.

Three errors in one paragraph, and they compound:

- **Deferred without decomposing.** Failure 18, third instance in a single day.
  The defect was treated as one indivisible thing — "give the gate the library" —
  when it was three: reachability labelling (small, no model calls, built in one
  pass), passing held source bytes (larger), and subject resolution (genuinely
  hard, no test set, correctly deferred). Estimating the whole at the cost of its
  hardest third is how a cheap fix goes unbuilt.
- **Misapplied failure 16.** Failure 16 is *a protective construct whose
  triggering condition was never tested*, and its remedy is **make the thing fire
  once before trusting it** — a prescription about testing what you build, not a
  reason to decline to build. Cited as a reason for inaction, it inverts into
  cover for the very state it describes.
- **Recorded a defect and then routed the next action through it.** This is the
  one worth naming as a rule, because it feels like diligence:

> **"Record it and proceed" is only honest when proceeding does not depend on
> the thing recorded.** Where the next action runs through the defect, recording
> it is not deferral — it is a note that the next result will be untrustworthy,
> written by someone who then goes and gets that result anyway. Either the defect
> blocks, or the part that blocks gets fixed first. Filing it and continuing is
> the option that is not available.

The decomposition took one read of the gate's own code and produced a fix that
cost nothing to run and was tested against the five findings for free. The
deferral would have spent $3.50 to get a sixth.

---

### 12l. Some figures cannot be sourced by matching

*11 September 2026. The first articulated limit on figure-checking as a method,
and it is a limit on the approach rather than on any run of it.*

`92.2% (84.2 to 96.3)` appears in **two** held documents:

- **S004**, the five-year paper, as its **48-month** OS figure;
- **S014**, the ASCO abstract, as the **5-year** rate: *"5-y rate was 92.2%
  (95% CI, 84.2%–96.3%) for intismeran + pembro vs 71.3% (95% CI, 35.4%–89.6%)."*

Both are correct. The curve is flat between 48 and 60 months in that arm — no
death falls in the interval — so the same number is the honest answer to two
different questions. The 48-month comparator is `85.6% (70.5 to 93.3)`, not
`71.3%`, which is the only visible tell, and only if you look for it.

> **A figure identical across two documents is indistinguishable from a
> mis-sourced one by search alone.** Finding a number in a document is not
> evidence that the number came from it, and the method most people reach for —
> search the source for the figure — cannot tell the two apart.

Only **recorded provenance** separates them: which document the figure was taken
from, written down at the time it was taken. That is what the source ledger is
for, and this is the first case where nothing else would have worked. Anyone
checking `melanoma.html` by searching S004 for `92.2` finds it, concludes the
page mis-attributed a five-year rate to a conference report, and is wrong.

---

### 12k. Where a checker hedged it was guessing; where it was categorical it was wrong

*11 September 2026, across two paid runs of the fact-check gate.*

Five SERIOUS findings. Every one refuted by two documents we hold. And both
genuinely useful things either run produced arrived **inside conditional
findings** — the ones phrased *"if 0.425 is an RFS or DMFS estimate"*, *"if the
endpoints differ"*. Those hedges were the gate noticing it could not resolve
something, and the reason it could not resolve it was that **the email never
named the endpoint** — a real omission, now fixed.

> **Confidence ran opposite to accuracy.** The categorical findings were false;
> the hedged findings were where the defects were. Reading any checker, the
> hedges are the signal — a hedge marks the place the checker could not see, and
> a place a checker cannot see is a place a reader cannot see either.

This inverts the intuition that a confident finding deserves more attention. It
is specific to a checker that cannot reach its sources: being unable to see the
settling document, it reports the mismatch it *can* see, and reports it plainly,
because from where it stands nothing is ambiguous. The ambiguity it does register
is the honest part.

---

### 12j. Reporting a working guard as broken — reasoning from the symptom, with the guard as the target

*10 September 2026. Caught before it was reported, which is the only reason it is
an entry here and not a repair to something that was never wrong.*

While checking the suite before a send, the author ran the pre-commit hook's own
test command and read back:

```
no tests ran in 0.00s
exit=0
```

The conclusion drawn was that the hook built to stop a commit over a red suite
collects nothing and reports success — **a broken alarm in the guard built to
prevent broken alarms**, which is as serious a finding as this catalogue holds.
It was two keystrokes from the report.

**Both halves were false, and each had its own cause.**

- `pytest $TESTS` was run in **zsh**, which does not word-split unquoted parameter
  expansions. pytest received one argument containing fourteen newline-separated
  paths and could not find a file by that name. The hook's shebang is `#!/bin/sh`,
  where the split happens and the paths arrive as fourteen arguments.
- `exit=0` was `tail`'s status, read through a pipe. pytest's real exit was 4.

Run as the hook runs it, under `/bin/sh`: **256 passed**.

**Why this is not failure 20, and needs its own entry.** Failure 20 is reasoning
from the symptom in order to *silence* a check — the motive is to get past it.
Here the motive was the opposite and the direction is reversed: the author was
reasoning from a symptom toward *condemning* a check that was working. The damage
model is different and worse. Had it been reported, the reviewer would have ruled
on it, and a functioning guard would have been "fixed" — a change made to a
working stop, on the authority of a finding, with everyone's attention on it. A
guard weakened by consensus is far harder to recover than one weakened quietly.

**What caught it was performing the check against the object.** Not re-reading the
output, not thinking harder about the shell — running the hook's line under the
hook's own interpreter. That is the same instrument that caught failure 21, where
`announce_interpreter()` compared resolved binaries and reported every interpreter
as the project venv. **Two instances in one session of a confident false reading
produced by running something under the wrong interpreter**, which makes it a
class and not an anecdote.

**The rule it yields:** a finding about a guard is verified by running the guard
the way the guard runs itself — same shell, same interpreter, same arguments,
exit code read directly and never through a pipe. A guard is the last thing that
should be condemned on a reading taken from somewhere else.

---

### 12i. Order corrections by whose interest is served, not by whose error looks worse

**Written 10 September 2026, while the two orderings agree — which is the only time it can
be written honestly.**

Today's correction email leads with a misattribution of a finding to a named
researcher, and puts our own interval mistake second. **That is the right order
and it is also the flattering one.** The attribution error is the least
attributable to sloppiness: a name got transposed. The interval error is ours in
a way that is harder to explain.

So the rule is being set down **now, while nothing turns on it**:

> **Order corrections by whose interest is served, not by whose error looks
> worse.** A correction naming a third party goes first, because it is the only
> class where the cost of silence falls on somebody who is not us. Ours go after,
> in the order a reader needs them, not in the order that flatters.

**Written now because when the two diverge, the argument for the flattering order
will be available and will sound like editorial judgement.** There will be a day
when our worst error and the one affecting a third party are the same length,
the same subject, and in opposite positions on that list — and on that day the
reasoning will be motivated whichever way it comes out. A rule settled in advance
is the only one that is not.

**Note what this rule does not say.** It does not say lead with the worst. Order
by *whose interest*, and the reader's interest usually coincides with severity —
but where they part, the third party comes first, because a reader can weigh a
correction they have been given and a person cannot correct a record they do not
know is wrong.

### 12h. Category (c): the sentences that join claims are where this publication fails

**10 September 2026. Four false claims in one day, all of them connective prose between
correct figures.**

| the false sentence | the figures around it |
|---|---|
| *"binding **every** sentence on this page"* | correct |
| *"131 of this page's 343 sentences"* — bound, when 95 were | 131, 343 correct |
| *"This page has 343 sentences"* — the body has; the page has 656 | 343 correct |
| *"in a message whose other intervals were 95%"* — the email never labelled it | 0.179, 1.004, 0.114, 1.584 all correct |

**Every figure in all four was verified. Every joining sentence was wrong.**

**Every check in this apparatus reads claims.** `b13` asks whether a figure is in
a held document. `spancheck` asks whether a span is present. The epistemic check
asks whether a read-state matches the store. Rule 1 asks whether a sentence names
the words it rests on. **Nothing reads the sentence that puts two verified claims
into a relation** — and a relation is not a claim about a document, so no
document can settle it.

That is the passage-reading stage's whole justification, and it is now
demonstrated rather than argued: **the stage found the first three, and only
because somebody ran it.** The fourth was found while classifying every sentence
by whether it had been verified — which is the same exercise performed by hand.

> **A page can be composed entirely of verified claims and still be false**, and
> every sentence-scoped control in this repository will pass it. The falsehood
> lives in the joins, and the joins are not in any document.

**Why they run flattering** is the part worth keeping. A joining sentence is
written to make two facts land, and the version that lands hardest is the one
that overstates the relation: *every* rather than *most*, *this page* rather than
*this page's body*, *95%* rather than *unlabelled*. **The compression that makes
prose readable is the same operation that loses the qualifier**, and the
qualifier is nearly always the unflattering half.

### 12g. A correction that replaces a summary with another summary fails the same way

**10 September 2026, from two errors in one afternoon, both in the same paragraph.**

> **Summarising loses structure, and the loss runs flattering. State the
> structure and it ends.**

The melanoma change-log entry said the corrections meant binding **every**
sentence. Corrected, it said **131 of 343** — a cleaner number, and still wrong:
95 are bound to a span, 34 are declared judgements, 2 are attested. Each summary
was more accurate than the last and each was a summary, so each had room for the
same error again.

**The pull toward a clean number is what produced both.** A structure has four
figures and a shape; a summary has one figure and reads as settled. The second is
what a writer reaches for and what a reader remembers, and the compression is
where the flattering direction gets in — *"131 bound"* sounds better than *"95
bound, 34 declared, 2 attested, 212 unexamined"*, and it was the sentence that
had to be corrected twice.

**The test:** if the corrected sentence contains a single number where the truth
has a shape, it will need correcting again. The regress ends when the structure is
on the page, because a structure has nowhere left to compress to.

### 12f. Which premises need verifying: the ones that feel settled from repetition

The rule *"verify the premise"* does not say **which** premises, and there are
too many to check them all. This says which.

> **The premises most in need of verification are the ones that feel settled
> because they have been repeated, not because they were ever checked.** A fact
> you have used ten times reads as established; **the repetition is doing the
> work that evidence should.**

**Worked example, 10 September 2026, and the selection is the finding rather than the
error.** In a single ruling the reviewer insisted that a page's own claim be
checked **verbatim, with location, before drafting anything** — and in the same
message asserted, without checking, that Appendix D is on the published page and
that fixing it would require a republish. Appendix D is in the review packet.
`melanoma.html` contains the string "Appendix" zero times, and the number had
been wired into `coverage_md()` hours earlier.

**The difference was not importance.** It was that he noticed he did not know one
and did not notice about the other, because *Appendix D* had appeared in a dozen
of his own rulings and had become furniture in his own reasoning.

**The tell is confidence whose source you cannot name.** Anything referred to
confidently for days is a candidate, and the question that separates them is:
*when did I last check this, as opposed to last use it?*

### 12e. The reference case: a check whose scope matches its subject

**This catalogue records only failures, so until 10 September 2026 there was no written
example of the thing being got right.** There is one, and it is worth more as a
reference than another failure would be.

`backend/scripts/whatholdsup/hooks/pre-push` reads each ref off stdin and skips
anything that is not the deploy branch:

```sh
case "$remote_ref" in
    ...
    *) continue ;;                     # only the branch that deploys
esac
```

**Its subject is deploying and it tests deploying.** Asked on 10 September 2026 to accept a
push of adjudicated-but-unpublished work to a non-deploying branch, it did the
right thing with no bypass, no exception and no judgement call — on a case its
author probably never considered.

**Set it beside two failures in the same file.** The dateline gate read half a
dateline (failure 15). The pre-push *message* describes a push-scoped consequence
for a repo-scoped condition. **Same file: one part correctly scoped, two parts
not.** That is the most useful thing in this entry — the difference is a property
of individual decisions about what a check's subject is, not of the codebase's
general quality, and it cannot be fixed by being more careful in general.

The question that separates them is small and can be asked of anything here:
**what is this check's subject, and is that what it examines?**

---

**The degenerate case of failure 16, 10 September 2026.** A commit went in over a failing
test. The mechanism was not carelessness and the remedy is not care: the command
was `pytest … ; git add … ; git commit …` — three commands in sequence with a
**semicolon** between them. The test ran, printed its failure, and the commit ran
anyway, because nothing connected them.

*A stop is only as good as the test under it.* **Here there was no stop at all** —
only two commands that happened to be adjacent, and adjacency read as dependency.
The fix is mechanical and it is now installed: `hooks/pre-commit` refuses a commit
whose staged paths touch whatholdsup while its tests are red, scoped so a commit
elsewhere is unaffected. Made to fire before being trusted — broken test, refused
commit, restored test, accepted commit.

**Failure 21 — the normalisation step is where the difference you are looking for
goes to die.** *10 September 2026.*

`announce_interpreter()` was written to catch a silent substitution of one Python
for another. It compared `Path(sys.executable).resolve()` against the venv's
`bin/python3`. **A venv's `python3` is a symlink to the base interpreter**, so
`.resolve()` — whose entire purpose is to normalise away exactly that kind of
indirection — made the two paths equal, and the function returned *"this is the
project venv"* for every interpreter on the machine. **It silently passed a silent
substitution, for an hour, having been written to catch one.**

File it with `_norm` equality defeated by a stripped tag. The rule:

> **Before normalising, ask whether the property you are testing survives the
> normalisation.** A normalisation that runs along the same axis as the question
> destroys the answer and returns "same".

**And it runs both ways.** The same week, a declared figure exclusion went stale
because `_norm` collapses whitespace runs but does **not** remove a space before a
full stop — `"343 sentences."` and `"343 sentences ."` are different after `_norm`
— so a declaration written by hand failed to match the page it described.
**Normalising too little reports a false difference; normalising along the
question's own axis reports a false sameness.** The second is worse: a false
difference is a red check somebody investigates, a false sameness is a green one
nobody does.

**Writing a rule down makes its author more likely to CITE it and no more likely
to FOLLOW it.** Stable across three instances on 10 September 2026, which is enough to
state as a form.

| the rule | who wrote it | how it was violated |
|---|---|---|
| §12d — do not cite a location in a document you have not read | the reviewer, 9 September | cited a file path that does not exist, the next day |
| failure 18 — decompose before deferring | the reviewer, 9 September | **deferred all 54 falsifiers citing the 2 that need the world, in the same message that invoked failure 18.** Eighteen are checkable from this repository alone |
| a stop is only as good as the test under it | this repository, long-standing | a commit went in over a red suite, joined to its test by a semicolon |

**The middle one is the sharpest**, because the rule was invoked *by name* in the
act of breaking it: a single number — 54 — hid a buildable majority behind an
unbuildable minority, on a pile deferred whole in the breath that created it.
Citing the rule was not merely compatible with violating it; **citing it supplied
the confidence to skip the step it prescribes.**

> **Only a check changes behaviour.** A written rule is a statement of intent and
> a citation is evidence of memory, not of compliance.

**This is the conclusion the $36.29 entry reached from the other direction**, and
the two were arrived at independently. That one asked why a budget kept being
exceeded despite everyone knowing the number, and answered: because knowing a
limit and being stopped at it are different mechanisms. This one asks why rules
keep being broken by the people who wrote them, and answers the same thing.
**Two paths, one conclusion, no shared premise** — which is the only kind of
corroboration worth much here.

**Failure 20 — reasoning from the symptom.** *When a check fires, the question is
what the data actually is, never what value would silence the check.*

The code-layer version of this is already understood — do not modify a guard to
get past it.

**And that rule is about motive, not about the file, which needs saying because
reading it as "do not touch guards" cost a real repair on 10 September 2026.**
Asked to fix a pre-commit hook that named a virtualenv which does not exist, the
author declined on the grounds that guards are not to be modified, and left a
guard passing for the wrong reason. That is the prohibition inverted. The two
acts are opposites:

> **Bypassing** a guard changes it so that it stops objecting to what you are
> about to do. **Repairing** a guard changes it so that it objects for the right
> reason. The first is forbidden however small the edit; the second is
> maintenance, and declining it leaves a guard whose green result is luck.
>
> The test is the counterfactual: *would I still make this edit if it did not
> unblock me?* If yes, it is repair. If the edit is only worth making because
> something of mine is stuck behind it, stop and report instead. **The data-layer twin is the one that will recur, and it is far
harder to see**, because a datum edited to make a check pass is
**indistinguishable from a correct datum**. It defeats the check permanently and
invisibly, with every test still green and nothing to review.

Worked example, 10 September 2026. `S021` — the PALMARES-2 registry record — was classified
`document_class: record_about` on 9 September because doing so suppressed a false
positive. That is not what it is: it **is** the registry entry, and claims about
the registry entry rest on it. It was reversed to `document` by the same author
the next day, the false positive returned, and it is now recorded as what it
always was — a subject-resolution defect in which a sentence about the *paper*
resolves to the *registry record* because both are called PALMARES-2.

**The tell, and it is available at the moment of the edit:** you are choosing a
value by reference to a check's output rather than by reference to the thing the
field describes.

**IT RUNS TWO WAYS, AND THE SECOND IS WORSE.** Reasoning from the symptom can
edit the **data** to make a check pass, or edit the **page** to make a check
pass. **The second is worse, because the page is the product.** Fixing a datum
corrupts a measurement; fixing the page corrupts the thing the measurement was
about.

This is why the not-examined row added 10 September 2026 is **WARN and not BLOCKED.** An
unexamined sentence is not a failing sentence. A BLOCKED row against 212 sentences
would put an author in front of a choice between writing 212 bindings and deleting
prose, and under time pressure some of that prose would go — true sentences
removed to clear a number, with every check then green and nothing recording what
was lost. A check that can be satisfied by deletion must never be blocking unless
deletion is the correct remedy.

**And the same principle applies to a check's own failure mode.** The first
version of the not-examined row called `page_sentences()`, which raises for a slug
with no page; the row simply vanished, and the rules suite went from 89 passing to
61 without anything saying why. It now reports *"could not be counted … Unknown,
not zero."* **A row that vanishes on error reintroduces the absence it exists to
remove** — the check reporting nothing and the check reporting no problem are
indistinguishable from outside.

Third instance this week of a new call reaching for the real page inside a module
the tests exercise on a synthetic slug. The pattern: **a function added for
production data, in a file whose tests run without any.** Ask what the field means, answer that, and let the check say
whatever it then says.

**Failure 19 — the fixtures are selected by the blind spot that produced the
incidents.** *A test set drawn from known incidents tests the part of the problem
the incidents made visible. The part they did not make visible is the part nobody
has looked at.*

This is not failure 16 restated. Failure 16 says **make the construct fire**.
This says firing is not enough, and the reason is structural rather than careless.

The worked example is `epistemic.py`, 10 September 2026. Five fixtures, three firing and
two not, drawn from three real incidents — a set that satisfies failure 16
exactly. **All five had an unambiguous subject**, because the incidents that
reached the record were the ones a person could see, and subject ambiguity is
invisible until a machine tries to resolve it. Run against the corpus the same
check produced four findings and every one was a false positive, three of them
from the mechanism the fixtures never exercised.

> **Operational rule: run a new check against the whole corpus before wiring it
> into anything.** The test set proves it works on the problem you already
> understood. The corpus tells you what the problem is. It costs one command,
> and here it cost one command and changed what the check is for.

**Failure 18 — decompose before deferring.** *A defect deferred whole is often
three defects, and usually at least one of them is cheap. An estimate of cost is
not a measurement of cost, and the person making it is the person who benefits
from it being high.*

The worked example is passage coherence, filed on 2026-09-09 as *"a different
kind of machinery"*. Decomposed on 10 September 2026 it is three defects:

| class | what it is | remedy |
|---|---|---|
| contradiction | two sentences that cannot both be true | §5.5, a reading |
| **stale predicate** | a sentence asserting a state the system tracks and that has changed | **mechanical — `epistemic.py`** |
| legibility | nothing false; the passage is hard to parse | §12a-iii, a counting rule |

**The middle one was buildable, had five test instances already sitting in the
repository, and was the class that caused the harm.** The deferral sorted by
apparent cost, and apparent cost was a guess.

**FIRST SUCCESSFUL APPLICATION, 10 September 2026, and it is recorded because an entry with
only violations under it is a complaint rather than a rule.**

The hypothesis was that most of the 135 unbound cdk46 sentences would be
judgements lacking a declaration. It was wrong: judgements have **no binding rows
at all**, so none of them are in the 135. The measurement settled it in one pass.

**Had a plan been directed on the hypothesis, the work would have gone to writing
declarations while 140 empirical sentences that no rule examines stayed
unexamined.** The rule that prevented it — decompose and measure before deciding
— was written the day before, against a violation. This is the first time it was
followed instead.

**The consequence for the pile.** Every entry in `whatholdsup-open-gaps.md` was
placed there by the same judgement, which means **the deferred pile is selected
for looking hard rather than for being hard.** It is worth re-reading with that
in mind, one entry at a time, asking of each: is this one defect or three, and
is one of the three cheap.

**And the corrected reason for what is still not built.** Automated contradiction
detection and automated impression assessment are not deferred because they are
expensive. They are deferred because **no test can currently be stated that
distinguishes a working one from a broken one** — failure 16. That is a
different reason from the one given on 2026-09-09, and it is the honest one. The
difference matters: a defect deferred for cost is waiting on effort, and a defect
deferred for want of a test is waiting on an idea.

**Failure 15 — scope.** `header_date()` returns the *Updated* date when one is
present, so the gate that compares a masthead to today has only ever compared
half of the dateline. Melanoma carried "Published 26 August 2026" for twelve
days under a green result, and it was found by hand on 2026-09-09 rather than by
anything that runs. **A green result is only as informative as the scope of the
check that produced it.** This is worse than a missing check: a missing check
leaves a visible hole, and this one returns green over the thing it does not
examine. Fixed the same day — `masthead_dates()` reads both halves and the gate
compares both, and the fixed check was run across every published page rather
than trusting that hand-checking had found them all.

**Failure 16 — protective constructs that were never made to fire.** Three
instances, all 2026-09-09, all in work authored here:

- `bindings._declared_exclusions()` guarded with `except Exception` around a call
  that raises `SystemExit`. `SystemExit` is not an `Exception`, so the guard
  caught nothing while looking defensive, and 22 rules tests went from green to
  red unnoticed. The same distinction is commented four hundred lines away in
  `publish.py`.
- The first version of the SLA regression test asserted
  `... == date(2026, 8, 31) or True`, which passes by construction. Caught and
  removed by its own author before it was committed, which is the only reason it
  is recorded here rather than found in six months.
- The historical case this family is named for: a stop wired to a probe that
  cannot fire.

The tell is identical in all three: **nobody ever made the construct fire once.**
A guard, a stop and an assertion are all claims about what would happen in a
condition that has never been produced. Produce it.

**Failure 17 — the message.** Three times on 2026-09-09 a check's condition was
sound and its message was not: the pre-push guard, the dateline gate, and the
B18 change-log tripwire, whose failure message named a cause (`page_sentences`
reading the footer) that was demonstrably not the cause. A failing test that
names the wrong cause sends the next reader in the wrong direction, and that
reader trusts it because it fired. **We test what our checks detect and we do
not test what they say.**

> **Two pointers in the 2026-09-09 ruling do not resolve, and are not invented
> here.** The ruling directed that failure 16 be filed "beside failure 1d" and
> that the R2 asymmetry be added to "the failures that present as inaction"
> entry. Neither exists: this catalogue numbers 1–14 with no letter
> subdivisions, and no document in `docs/` contains that phrase or the four-day
> lock incident it cites as a companion instance. They are filed as new entries
> 15–17 above and in `whatholdsup-open-gaps.md`. This is the second time today a
> reference maintained in prose has failed to resolve — the first was the family
> instance count settled in §12a — and it is the same defect both times.


**Rule 14 distinguishes two states, and the first version of it did not.** A
change whose reasoning exists but is not linked is a bookkeeping debt: record the
governing document and move on. A change whose reasoning never existed is
unrecoverable, and the log says so rather than reconstructing it. The 175 changes
of 28 August – 4 September are the second kind. The 239 of 8 September are the
first: they were decided in the adjudication, the publish directive, its
amendment and the remediation order, and what is missing is machine-readable
linkage rather than knowledge. Attributing them one diff at a time would produce
a record that looks like 239 decisions and represents four, which is the same
objection that stopped the 175 being backfilled.

**Third instance, 10 September 2026, and the first to reach a directive.** *"7 of 228 cdk46
binding rows carry a locator naming a source"* described the `locator` field and
was reported as if it characterised the row. A binding row carries `source_id` —
34 of 169 on-page rows — and `quotations.py` reads it directly.

**The path is the part that repeats: report → reviewer → instruction.** The
number was quoted back in a ruling as possibly the largest finding on the list,
and a directive was built on it. Nobody derived it at any step, because it
arrived already written.

**And what prevented a false entry in the record was not care about the number.**
It was a refusal to reason from it: the ruling declined to conclude and asked for
the schema instead. Care would not have caught this — the number was accurate
about the field it described. **Only refusing to reason from a summary caught
it**, and that is a different discipline from checking arithmetic.

**A wrong number that looks right propagates further than a wrong argument.**
An argument invites scrutiny; a plausible figure invites copying. Figures
asserted about our own artifacts need the same discipline as figures asserted
about other people's: name what was measured and how.
*Origin:* "the paragraph runs to 2,116 characters" was the text content of an
arbitrary 2,400-character window of raw HTML, reported as a measurement of a
paragraph that is 1,013 characters. 2,116 is an unremarkable size for a
paragraph, so nobody stopped on it — including the person who invented it, twice,
in two later documents. Seven occurrences, four documents, two parties, no
measurement, inside the entries about asserting things without opening them.
RV-08.

**A stop condition is only as good as the test under it.** Before wiring a halt
to a check, establish what its false negative looks like — a fragile test with a
stop attached converts a measurement error into a halted pipeline, and the person
who wrote the test is the least likely to notice its blind spot. Where an
instruction says stop, it means stop on the condition the instruction is about,
not on the literal output of the probe suggested for detecting it.
*Origin:* the 9 September close-out wired a stop to `grep -c "Consensus scores 4
because"` against raw HTML, where the string spans a `</strong>` boundary and can
only ever return 0. Followed literally it would have halted the close-out on a
false alarm; the paragraph was byte-identical to the base at 1152 characters.

**A caveat is not a check.** Naming an uncertainty protects against the failure
you imagined and does nothing about the one you did not. Where a ruling turns on
a historical artifact, open the artifact.

**A check whose own history is a correction should be read before its name is
trusted.** `sources_shown` was mis-described by three separate readers; its
earlier version read bindings only and was wrong in exactly the way that omission
predicts.

Failure 14 was added on 2026-09-08 after one outside review produced five errors
that were all the same error. The reviewer queried the `analyses` field and
concluded a result was posted (RV-01); took an interval computed for one hazard
ratio and attached it to another (RV-02); read 400 characters of a
1,013-character paragraph and reported three sentences absent (RV-03); and read
the rendered page's source list and concluded the document was in the library
when the store held nothing (RV-04); and read a span quoted in Appendix A and
concluded that the document it came from named no trial, when the document names
it eleven times and the span was inside a third-party post the outlet was logging
(RV-05). Five for five. Failure 1 is this failure
pointed at our own library; failure 13 is the narrow case of it. This is the
general one, and its detection is procedural rather than automated: **name the
artefact you actually read in the finding**, so that a mismatch between the
artefact and the claim is visible before anyone acts on it. All four were caught
by the implementation reading the base before editing it, which is rule 11 and is
now five for five on its own account.

Failure 10 has no automated detection and there is no plan to build one. It is
the argument for the review step. The clearest instance: the melanoma page
asserted that blinding solves the assessment-bias problem, and printed, several
thousand words away, injection-site pain at 59.6% against a saline placebo, with
an investigator-assessed primary endpoint. Both halves were ours. Nothing but a
reader was ever going to join them.

### 12a. Failure 1, as an explicit list

Failure 1 — *a conclusion resting on an enumeration built from an incomplete
model of what there was to find, presented as complete* — is the family this
publication keeps producing. It was tallied in prose across four documents until
2026-09-09, when the prose tally and the RV series were found to disagree. **The
tally lives here now and nowhere else.** Each occurrence points to its RV entry
or, where it has none, to the ruling that recorded it. The count is whatever this
list is long; nobody maintains a number.

| # | Occurrence | Recorded in |
|---|---|---|
| 1 | Concluded a trial result was posted from a search that had not covered the registry | RV-01 |
| 2 | Took an interval computed for one hazard ratio and attached it to another | RV-02 |
| 3 | Read 400 characters of a 1,013-character paragraph and reported three sentences absent | RV-03 |
| 4 | Reported a source verified when the store held nothing | RV-04 |
| 5 | Read a span quoted in Appendix A and concluded an outlet named no trial | RV-05 |
| 6 | Withdrew a true self-accusation on arithmetic that had not been done | RV-06 |
| 7 | Quoted a paper's figures without reading the erratum field four lines above them | RV-07 |
| 8 | A paragraph size asserted seven times across four documents, never measured | RV-08 |
| 9 | A citation reported as unlocatable from a search that had not tried the record's own identifiers | RV-09 |
| 10 | The 4 September log paragraph — narrated in the Morning Glory ruling, never given an RV number, and the reason the prose tally and the RV series diverged | `2026-09-09-step3-ruling.md` |
| 11 | A question posed as a binary — index wrong or record incomplete — when both branches were false and the two statements agreed across the UTC boundary | RV-10 |

Note what the last one adds. Every entry above it is an enumeration asserted in a
statement. Number 11 is the same defect asked as a question, and it is the more
dangerous form: an incomplete search invites someone to go looking, whereas a
forced binary invites the reader to pick a side. Picking a side feels like
scrutiny, and whoever picks has already accepted the frame. **The work of asking
whether the alternatives are all of them never gets done.**

### 12a-i. A record has a start date, and the events before it are outside its reach

**"The record does not say so" is not "the record says otherwise."**

The melanoma masthead says the page was published on 26 August.
`published.json`'s first row is 28 August. That looked like a two-day
disagreement and was not one: the page went live on the 26th, and the record
begins on the 28th because `publish.py` and `published.json` were *created* on
the 28th. There was nothing to write a record with and nothing to write it into.
The evidence is in `issues/WHU-001-melanoma/provenance.md`.

This publication established the principle on 2 September, pointed outward: **our
failure to find a document was never evidence it did not exist.** Pointed at our
own record it reads the same. The error was applying a rule about *disagreement*
to a case of *non-coverage* — which is the same move as reading an abstract and
concluding about a paper, one layer in.

**Two things follow, and the second is the transferable one.**

A record does not gain rows for events it did not witness. What is established
afterwards goes in a note that says **when it was established**, never as a row
backdated into the record — because the whole value of the record is that its
rows were written at the time. A backfilled row asserts a witnessing that did not
happen, in the file every publication decision rests on.

And the check encodes the principle rather than the instance.
`publish.record_begins()` derives the record's start from the earliest `at` in
`published.json`, and a masthead earlier than that is reported as *"the page
predates the record"* rather than as a false date. Nothing in it names melanoma.
**Every future page that predates its own tooling is handled correctly by
somebody who has never heard of this one.** That is the difference between
encoding a principle and patching an instance, and where the two are available
the first is always the smaller amount of work over time.

### 12a-ii. Describe the document, not the part of it you went looking for

**A true statement about a document's purpose can be a false impression of its
contents.**

Two instances, and they are the same instance twice.

**RV-07.** EORTC 18071 was supplied for a counterexample and its abstract's
figures were quoted from a PubMed response whose `Erratum in` field sat four
lines above them. The part wanted was read; the field qualifying it was not.

**The MONARCH 3 corrigendum, 10 September 2026.** The page said *"In full, it corrects one
number in Figure 4."* Every word of that is true: the correction is one number.
Read end to end, the notice also **republishes Figure 4 entire**, carrying a
complete chemotherapy-free survival dataset — both arms' patients and events,
medians of 46.7 against 30.6 months, log-rank P = 0.0010 and HR 0.693
(0.557–0.863). A reader of our sentence would picture a one-line notice. The
document is a survival analysis.

The tell in both is a sentence that describes the *answer to the question we
asked* rather than the object we hold. The question "does this notice touch our
figures?" is answerable without reading the notice; "what does this notice
contain?" is not, and only the second produces a sentence a reader can rely on.

**The repair carries the distinction that makes it worth stating.** The page now
says what the notice contains *and* that we use nothing from that endpoint —
because there is a difference between having seen data and not used it, and not
having seen it, and only the first can be checked by a reader.

### 12a-iii. N misreadings of one passage is a finding about the passage

**Adopted 10 September 2026.** Three independent automated readers misread the KOL Pulse
box. Each was disposed of as a false positive, one at a time, and the pattern
was only visible when somebody counted them.

> **Two independent automated misreadings of the same passage is recorded as a
> legibility finding about the PASSAGE, not as two false positives about the
> checkers. Three requires revision before that issue's next publish.**

It costs nothing to adopt: the misreadings are already being produced and logged.
The rule converts a stream of dismissals into a signal, and a dismissal is
exactly where a signal goes to die — each one is individually correct, and being
individually correct is what stops anyone adding them up.

**Applied retroactively, the KOL Pulse box is at three and is therefore already a
required revision item — which it independently is**, by the ruling of
2026-09-09 that recorded it as REQUIRED for the next revision. **The rule and
the ruling agree and were arrived at separately**, which is the only kind of
corroboration worth much: a rule that only ever confirms the decisions of the
person who wrote it is not a rule, it is a description.

### 12b. Every finding records which direction it leans

One clause per finding: does the error, if it had stood, have flattered us or
embarrassed us?

Four in the cycle ending 2026-09-09 lean the same way — the fabricated 2,116
character count, which made a fabricated absence look more forgivable; the 80%
interval printed beside a 95% one, which made an uncertainty look narrower; the
corrections SLA clock, which reported us as more timely than we are; and,
arguably, a correction that happened to be true.

**This is not a claim of bias, and it must not be written up as one.** There is a
mechanism that produces the pattern with nobody intending it: an error that
flatters is not questioned, so it survives; an error that embarrasses is caught
quickly and dies young. What remains live to be found is therefore skewed toward
the flattering ones. Survivorship, not motive.

The clause is cheap and the aggregate is the point. Where a set of findings leans
one way, that is a signal about where to look next — and it stays invisible for
as long as each finding is only ever read on its own, which is what happened here
until somebody counted them.

### 12d. A directive does not cite a location in a document its author has not read

**Standing rule, and it binds the reviewer rather than the repository:**

> A directive names the content and the criterion for where it belongs. It does
> not cite a location in a document the author has not read. Where a directive
> must reference an existing entry, the structure is reported first and the
> reference is written against the report.

**Origin: three unresolvable references in one day, 2026-09-09.**

| reference | what it actually was |
|---|---|
| "failure 1d" | a step number in one of the reviewer's own rulings, later cited as a catalogue entry |
| "the failures that present as inaction entry" | language written in a ruling, never a heading anywhere |
| "instance eleven of the family" | a tally kept in prose across four documents, running ahead of the RV series that had no register (settled in §12a) |

The mechanism is not carelessness. **The reviewer had been writing directives
against a document he had never read** — every reference to this file's internal
structure was a reference to his memory of what he had asked to be put in it,
which is a partial representation of a document treated as the document. That is
the base-drift failure of this cycle, relocated out of the artifacts and into the
directives that govern them.

The correct handling when a pointer does not resolve is the one taken: file the
content as a new entry under a criterion that can be checked, and **record the
mismatch** rather than placing it quietly somewhere plausible. The note filed
with entries 15–17 is the evidence for this rule and stays where it is.

**Violated by its author within a day of being written.** The ruling that
established this rule was delivered on 2026-09-09; the message delivering the
next one, on 10 September 2026, cited a file path — `2026-09-09-record-ruling.md` — that
does not exist. The file was `2026-09-09-record-reach-ruling.md`. A path is the
cheapest possible thing to check and it was not checked.

This is the same evidence as the stale spend figure repeated within an hour of
RV-08, which was the finding that a wrong number propagates because it looks
right. **Writing a rule down does not make its author follow it.** A rule is a
statement of intent; only a check is a control. Every rule in this document that
has no check behind it should be read as a description of what we mean to do,
not as a description of what happens — and §12d currently has no check behind
it.

**A scope figure inherited from a report arrives looking settled, and is
therefore never re-measured.** Named as a habit on 10 September 2026, on its second
occurrence in two days.

The directive to run `confirm-review` against cdk46 was wrong twice and both
errors ran the same way. It asked *"does a review apply across four unrecorded
changes?"* — which is the question that comes **second**: `reconcile()` tests
whether every changed sentence traces to a recorded decision before anything
tests review scope, and 28 did not. And "four commits" was too small: the
review's base (`3ca22e72`, 29 August) predates the last publication record
(`4e4bb50b`, 31 August), which predates the live page. Two stacked gaps, not
one. The figure was carried forward from an earlier report of mine and never
re-checked by either of us.

Both errors made the situation look smaller and more closeable than it was, so
both go in the direction column. The mechanism is the same one as the fabricated
2,116-character paragraph: **a number that arrives already written does not
invite the scrutiny a number being derived does.** The remedy is not care. It is
that a scope figure quoted in a directive is re-derived at the point of use, the
way `record_begins()` and `publication_dates()` are derived rather than
remembered.

**"Zero true findings" is the flattering reading of an inconclusive result.**
Recorded 10 September 2026, because in six weeks the sentence that will be remembered is
*"we ran an epistemic check across all three issues and it found nothing"*, and
that is not what happened.

Four false positives and zero true positives establishes **nothing** about
whether the corpus contains stale epistemic claims. A check that cannot resolve
a sentence's subject cannot establish absence any more than presence. What is
known: the predicate half works. What is open: everything about the corpus.

The retargeted run makes the same point in a number instead of a sentence — it
evaluates **1 of 89** epistemic sentences across three issues, and that one is a
known false positive. **A finding of "nothing" from an instrument with 1%
coverage is a fact about the instrument.**

**A second counter-instance, 10 September 2026, and it is the strongest evidence yet that
question 3 does something.** The first draft of the Appendix D coverage
disclosure said *"evaluated 1 of 89 sentences"* — true, and inviting the reading
*only 1% of this publication's claims are checked*, which is **false**. Those
sentences were checked, by readers, at the time, against documents. What is 1 of
89 is a three-day-old automated cross-check.

**The passage-reading stage caught a false impression in the very disclosure
written to describe that stage's own machinery, on its first use** — and it
caught it leaning the direction this cycle has *not* been leaning. A disclosure
inaccurate in the unflattering direction is still inaccurate, and being modest
does not excuse it. The wording now carries its own scope.

**THE COUNTER-INSTANCE RULE.** An entry in this column with no counter-instances
after a reasonable number of observations is reported as **UNSUPPORTED**, not as
strong. A finding that only ever finds itself is not a finding — it is a search
that stopped when it was satisfied, which is failure 1 wearing a statistic. The
counter-instances go in the entry body at the same prominence as the
confirmations, not in a footnote.

**Keep the axes separate.** A single event can be a counter-instance on one axis
and a confirmation on another, and collapsing them into one narrative loses both.
The 163/132 error below is the worked example: on DIRECTION it is a
counter-instance, because it made our own page look wrong when it was right. On
FAMILY it is a confirmation — a truncated `reconcile` line read instead of the
document, which is the same failure as reading an abstract and concluding about a
paper. It is not "an error that cuts both ways". It is two facts about one event,
on two axes, and each belongs in its own column.

**And it happened twice the same day.** The second: I reported that the count in
*"the fifth position this page has taken on one fact"* was unenumerated on the
page. It was enumerated — the sentence names all five and the next sentence says
why each was wrong. I had read the same truncated `reconcile` line. Two errors,
one cause, four hours apart, in a cycle whose subject is reading the artifact.

**A counter-instance, recorded because a direction column with only one
direction in it is not evidence of anything.** In the same report I stated the
corrigendum corrects an event count "162 → 163". It is **162 → 132**; the page
says 132 and was right. I had read a truncated `reconcile` line rather than the
document, and the error made our own page look wrong when it was not. It leans
against us, which the other five do not.

### 12c. The index is a translation, not a copy

**The record's vocabulary and the reader's vocabulary are not the same
vocabulary.** A word can be correct in the record and misleading on the page.
`record-live` writes `action: "republish"` for a change a person has signed as
NOT touching the argument; rendering that as "updated 9 September 2026" on the
homepage would tell a reader the assessment moved when a nav link was added.

When the two disagree, **the page serves the reader, the record keeps its own
term, and the translation is declared in the generator** — not resolved by
rewriting either side. `index_dates.PUBLICATION_ACTIONS` is that declaration, and
it carries the reasoning beside it. This will recur every time the index gains a
field.

---

---

## 13. Artifacts and naming

```
site/whatholdsup/<issue>.html                 the page
issues/<ID>-<issue>/draft/<issue>.html        the draft
<issue>.html.gate[_n].json                    gate output per run
YYYY-MM-DD-gate-adjudication[_n].md           decisions on gate output
YYYY-MM-DD-internal-pre-review.md             internal reader
YYYY-MM-DD-internal-pre-review-actions.md     what was done about it
YYYY-MM-DD-for-reviewer.html                  the packet sent out
YYYY-MM-DD-review.md                          the review, verbatim, never edited
YYYY-MM-DD-adjudication.md                    our decisions
docs/whatholdsup-open-gaps.md                 known blind spots
```

One issue, one directory. The SHA of the page reviewed appears in the packet
header and the adjudication header.

**Within one document, some sections are records and some are state.** A dated
finding is a record: retro-editing it is falsification, which is rule 16. A live
status list — an Outstanding section, a board, a set of open items — is state:
failing to update it is falsification too, and rule 16 has no counterpart saying
so. Know which you are looking at before deciding whether to touch it.
*Origin:* the melanoma adjudication's Outstanding section had item 1 updated to
CLOSED while items 2 and 4 still described work that had been finished, so the
section read as maintained and was not. The maintainer had a rule against editing
and none requiring it.

**A duplicate of a superseded document is a trap. A duplicate of a document you
are about to edit is a backup.** Do not delete the second kind before the edit is
verified. The 8 September remediation order treated the `_1` download duplicates
as traps and had them deleted; one of them was, hours later, the only surviving
copy of `2026-09-04-update-entry.html` after an unanchored index-based edit ate
three work-list items, a comment close and a paragraph. Had the hygiene item run
after the edit rather than before, the file would have been unrecoverable.

**Two things with the same name, one stale, is the base-drift failure waiting to
happen.** A superseded working copy is deleted, not marked — a marked copy still
answers to a path someone half-remembers. Where deletion is not possible, the
marker goes in the name, not only in a file inside it.

---

## 14. What we know we cannot see

**The strongest instance yet, 10 September 2026, and it is not two machines agreeing.**

Rule 1 has three routes: BOUND, DECLARED, ATTESTED. Within one hour, two readers
looked at the same 131 sentences and each reconstructed the same missing
category — in opposite directions.

- **The reviewer** assumed two routes and computed rule 1 = **129** (95 + 34).
- **The executing agent** read bucket and span, found two rows fitting neither
  known category, and reported them as **unaccounted for** — implying a hole in
  rule 1.

**Same object. Same absent category. Two readers. Opposite errors.** One dropped
the two sentences from the count; the other kept them and called them unexplained.
Neither read the pass logic, which names the third route in a comment eleven lines
long explaining why it exists.

**This is what §14 warns cross-checking handles poorly, demonstrated.** Two
independent readers disagreeing looks like a check working. Here the disagreement
was *produced by the same gap* — both were reasoning from a two-category model, so
their outputs differed while their error was identical. **Agreement would have
been no better than disagreement was:** had both dropped the two, the count 129
would have been confirmed by two readers and been wrong.

The tell is available and it is not "do they agree". It is: **do they agree about
what the categories are?** Two readers reconstructing a taxonomy from instances
will reconstruct the same wrong taxonomy, because the instances they can see are
the same instances.

Carried from `docs/whatholdsup-open-gaps.md` and from Appendix D of the melanoma
packet:

- The page's meta description ships as prose no check reads.
- Material inside `<q>` marks is invisible to the test that decides whether a
  sentence is empirical, so a figure appearing only inside a quotation is not
  required to have a binding row.
- Appendix B is the denominator for every "in the coverage we hold" claim, and
  the melanoma manifest currently skips `S012` with no explanation. The packet
  generator prints ids verbatim and cannot create a gap, so the absence is in
  the source store. **Open.**
- Each gate role reads the page alone. None audits another's output. None holds
  two distant paragraphs together.
- Nothing we own can look for a counterexample to a universal negative.

---

## 15. Amending this document

Add a rule when an error happens, not when one is imagined. Write the incident
into the rule. A rule with no incident attached is a rule nobody can weigh, and
it will be the first one dropped under time pressure.

Delete a rule only by recording why, in the same place — a rule that quietly
disappears is indistinguishable from a rule nobody followed.

**Version history.** v1.0, 2026-09-09 — first written, after the melanoma issue's
fourth revision and its first adjudication. Rules 2, 4, 5, 8, 9, 11–21 are drawn
from errors made between 26 August and 9 September 2026; rules 1, 6, 7 and 10
carry over from the cdk46 and deskilling rounds. §1.5 added the same day, after
reconciling against Standard v1.1; no conflict was found and no rule changed.
