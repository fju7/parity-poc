# WHU-002 — adjudication round, opened 10 September 2026

**This round is not "unblocking a publish."** Naming it after its destination
would put the destination before the work and invite exactly the shortcut
`confirm-review` refused. Twenty-eight changes to a published page need
decisions. Whether a publish follows is a consequence, not the objective.

---

## The drift, at its real size

`confirm-review cdk46` declined on 10 September 2026: 28 changed sentences have no
recorded decision behind them. Two distinct absences are stacked here and the
second one blocks before the first is reached.

| | sha | date |
|---|---|---|
| latest recorded outside review | `3ca22e72` | 2026-08-29T13:18 |
| latest publication record | `4e4bb50b` | 2026-08-31T16:58 |
| live page | `112e7a39` | 3 September onward |

**The review's base is older than the last recorded publish, which is older than
the live page.** The page has changed twice over: once between the review and
the record, once between the record and now.

**"Four commits" under-described this and should not be repeated.** That figure
was carried from an earlier report into a directive without being re-measured,
because a scope figure inherited from a report arrives looking settled. Both of
the framing errors in that directive — asking the question that comes second,
and the undersized count — made the situation look smaller and more closeable
than it is.

---

## OR-A — the MONARCH 3 corrigendum: what the notice contains, in full

**Read end to end on 10 September 2026**, not searched for one item. `S025`, held PDF,
sha `95b62889…`, 255,647 bytes, 3,336 characters of extracted text. The whole
notice:

1. The corrigendum heading and the original's citation, *[Ann Oncol 2024; 35:
   718-727]*, with the original's DOI.
2. The full author list — twenty-one authors, Goetz through Johnston — with
   affiliations.
3. **The correction itself**, entire: *"in the originally published version of
   this article, there was an error in Figure 4. In the 'Placebo + NSAI' arm,
   the number of events was incorrectly reported as 162. The correct number is
   132."*
4. Two sentences of apology.
5. **The corrected Figure 4, republished in full.** This is the part a search
   for the error would not surface, and it is the reason the question had to be
   asked the other way round. It carries, for chemotherapy-free survival:
   patients and events per arm (abemaciclib + NSAI 328/230; placebo + NSAI
   165/132), medians of **46.7 vs 30.6 months (Δ = 16.1)**, **log-rank
   P = 0.0010**, **HR = 0.693 (95% CI 0.557–0.863)**, and a complete
   numbers-at-risk table across eighteen time points.
6. Correspondence details, the CC BY-NC-ND licence statement, page 1556, the
   corrigendum's own DOI and the volume/issue line.

**One reading is stated rather than assumed.** `pdftotext` renders the figure
legend as "Abemaciclib + NSAI 328 230 / Placebo + NSAI 132 165", reversing the
placebo row against the header "Patients Events". Patients = 165 and
events = 132 is settled by two independent things in the same document: the
numbers-at-risk row, which begins at 165 for placebo + NSAI at time zero, and
the correction sentence itself, which names 132 as the event count.

**Does any of it reach the page?** No. The page prints nothing about
chemotherapy-free survival — no median, no hazard ratio, no P value from that
endpoint. The overall-survival figures, the alpha-spending description and the
follow-up duration are untouched.

**Decision required.** The page says *"In full, it corrects one number in
Figure 4."* That is true of the correction and incomplete about the document:
the notice also republishes an entire survival analysis. Nothing the page uses
is affected, so this is a question of what a reader is told about a document we
have read, not a factual error. **Ruling needed on whether the sentence stays as
written or names what else the notice carries.**

---

## OR-B — the paywall reversal: settled, and the page is currently wrong

The page says: *"An earlier version of this page said it sat behind a paywall;
the next said that was wrong and it was open access. **The first was right.**"*

**The first was not right.** Three independent sources, checked 10 September 2026, all
from an unauthenticated session:

| source | says |
|---|---|
| the held PDF's own footer | *"This is an open access article under the CC BY-NC-ND license (http://creativecommons.org/licenses/by-nc-nd/4.0/)"* |
| Crossref, `10.1016/j.annonc.2025.07.002` | version of record carries `creativecommons.org/licenses/by-nc-nd/4.0/`, `content-version: vor`, effective 2025-07-09 |
| Europe PMC, PMID 41093689 | `license: cc by-nc-nd` — **and** `isOpenAccess: N`, `inEPMC: N`, `inPMC: N`, `hasPDF: N` |

**Europe PMC's row is the whole explanation for three positions on one fact.**
Its `isOpenAccess: N` is a statement about the Europe PMC open-access *subset* —
whether the full text sits in their repository — and not about the article's
licence, which the same record gives as `cc by-nc-nd` two fields away. Reading
that flag as the licence is what produced the reversal, and it is the same
mistake in kind as reading an abstract and concluding about a paper: taking a
field that answers a neighbouring question.

**And the 403 is not a paywall.** An unauthenticated GET to
`annalsofoncology.org/article/S0923-7534(25)00851-8/fulltext` returns **HTTP
403** with 5,849 bytes containing no paywall language at all — no "subscribe",
no "sign in", no "purchase access". That is a bot block. The DOI resolves 200 to
Elsevier's linking hub. **A retrieval failure is a fact about our tooling, not
about the licence**, which this page has already said once, on 1 September,
about a different source.

**The method is recorded so this is a fact with provenance rather than a fourth
assertion:** three sources, named, dated 10 September 2026, from a session holding no
credentials of any kind.

**Decision required, and it is a page correction.** The sentence "The first was
right" is a live reader-facing error on a published page. `corrections.md`
compounds it — its 31 August entry says the corrigendum *"remains unread and is
still disclosed as unread"*, and it has been held in full since 1 September.
Both need fixing, and the page cannot be fixed without a publish.

---

## OR-C — "the fifth position this page has taken on one fact"

The page says of itself: *"This is the fifth position this page has taken on one
fact."*

That sentence is either the most honest thing in the issue or a symptom, and
which it is is a decision rather than a description. **It needs a ruling that
says why it stays, not a note that it exists.**

If it stays, the five must be enumerable by a reader. A publication whose
subject is that claims should be checkable cannot ask to be taken on trust about
its own history — that is the request it exists to refuse. The count is
currently unenumerated on the page, and this round has already found two counts
maintained in prose that were wrong: the family instance tally and "four
commits".

**Decision required:** enumerate the five in the change log and point the
sentence at them, or remove the count and keep the substance.

---

## The remaining 25

Not adjudicated here. They fall into groups that should be decided together
rather than one at a time: the one-sided/two-sided rework, the guideline's
category definitions replaced with its own wording, the "directly compared"
reading marked as ours rather than the guideline's, and the `/the-rubric` nav
link, which is furniture and needs only to be recorded as such.

---

## Standing

Nothing publishes out of this round until the 28 have decisions. The masthead
correction — "1 September", committed 2026-08-31 20:43 ET off a UTC clock —
rides whatever publish eventually follows and does not get its own republish.
When that publish happens, its record must state that four intermediate states
existed and were never recorded: a single row spanning eight days and four
commits reads as one event and was not.

---

## Rulings applied, 10 September 2026

**OR-A — ACCEPTED, and the completeness question answered first.**

The page does **not** invite the impression that MONARCH 3 failed to demonstrate
benefit. It carries the trial's significant primary result in three places, two
of them in the body and one in the most prominent structure on the page:

- the comparison table: *MONARCH 3 · abemaciclib · not reached vs 14.7 mo,
  HR 0.54 (0.41–0.72), primary analysis, JCO 2017*, set beside the survival
  result in the adjacent column;
- *"On the endpoint every one of these trials was powered to measure, nothing
  separates them… the progression-free hazard ratios are 0.54, 0.57 and 0.58"*;
- under **Established**: *"All three drugs substantially improve progression-free
  survival against endocrine therapy alone… Every one of them is statistically
  significant."*

Every "did not" on the page attaches to overall survival and names the boundary
it was tested against. One sentence actively refuses the misreading: *"abemaciclib
is a category 1 drug in one setting and a category 2A drug in another — on the
same evidence standard, consistently applied."* **No completeness problem, and
the clause was drafted on that basis.**

The source note now states what the notice contains and that we use nothing from
that endpoint.

**OR-B — ACCEPTED. Two live errors removed from the page and one from the log.**

*"The first was right"* is gone; so is the internally contradictory tail that
said, four sentences after *"we have now read it"*, that we could not say whether
the corrigendum touched anything *"because that requires reading it"*. The page
carries the verified access state, the method, the Europe PMC mechanism and the
403. `corrections.md`'s 31 August entry is **annotated, not rewritten** — it is a
dated record.

**OR-C — the count stays, dated. And the premise I gave you was wrong.**

I reported the five as unenumerated. They were enumerated: the sentence names all
five and the next sentence says why each was wrong. What was missing was dates.
Each now carries the day it was on the page — **28 August** two-sided unsourced,
**29 August** unknowable, **30 August** the registry's directionality on the
journal's number, **31 August** the doubling as arithmetic, **1 September** the
paper's own account — derived from `git log -S` over this page's history, not
from memory, and pointing at the change log.

I had read the same truncated `reconcile` line that produced the 163/132 error.
Two errors, one cause, four hours apart, in a cycle about reading the artifact.

---

## Where the round stands

| | |
|---|---|
| reconciled | **217** |
| **undecided** | **27** |
| recorded entries not matching the page | 108 |

Twenty-one changes were decided under OR-A, OR-B and OR-C, cited by label and
resolvable through this file. **27 pre-existing changes still need
decisions** — the one-sided/two-sided rework, the guideline's category
definitions replaced with its own wording, the *"directly compared"* reading
marked as ours, and the `/the-rubric` nav link, which is furniture.

Nothing publishes until those 27 are decided.


---

## G1 — the test direction: state the position, move the history, say why we are confident

**Operator ruling, 10 September 2026.** The body states the current position. The
five-position sequence moves to the change log. And the substantive addition:
**a page that has changed position five times owes the reader the resolution
condition, not a sixth assertion** — if we are not confident, say what specific
thing would settle it; if we are, say so and say what makes us confident.

**We are confident, and the ground is stated on the page:** the paper states its
own test direction in its own sentence, in a statistical section we have read,
and the trial's registry posting independently gives the one-sided form of the
same p-value against the same hazard ratio. Two documents, one from the journal
and one from the sponsor, agreeing on a fact neither is arguing about.

The body now says that and points at the change log. The change log carries all
five with the day each was on the page and what was wrong with each — *because a
reader wants the answer and an auditor wants the sequence, and only one of them
should have to read the other.*

## G2 — the scoped negative: deleted, and what remains is scoped

**Operator ruling, 10 September 2026: explain or delete, default to delete.** The reader
test failed at the friendliest possible reader — the operator, who knows this
material, could not tell what the sentence meant in context.

*"We asked, on 3 September 2026, and there is no such sentence"* is **deleted.**
It added a date to a claim the previous sentence already made, and the search it
reported had no stated scope: not which version, not which sections, not what
string. **A sentence that needs a paragraph of explanation to earn its place
usually has not earned it.**

The claim it was attached to stays, and is now scoped where it was not:
*"Nowhere in **version 6.2026** does it state the general rule we have drawn from
them… **That generalisation is ours.**"* The document and its version are named,
and the thing being asserted is our own inference rather than an absence a reader
cannot check.

The verbatim quotation of the guideline's category definitions **stays**, as
ruled.

## G3 — the alternative reading, given plainly

**Operator ruling, 10 September 2026: marking a reading as ours is not sufficient.** A
reader needs the other reading in plain terms, what follows from it, and why we
chose ours — enough to see exactly where they diverge and what changes
downstream.

The page now gives all four:

- **the narrow reading (ours)** — a trial that randomises one of these drugs
  against another; on it the guideline's sentence is true;
- **the wider reading** — any head-to-head comparison counts, randomised or not;
  on it the guideline's sentence would be **false**, because four comparative
  studies on this page do exactly that and three report abemaciclib against
  ribociclib directly;
- **where a reader who prefers the wider one diverges from us** — they would say
  the guideline is out of date rather than accurate, and that the comparison it
  calls untested has been attempted four times;
- **why we take the narrow one** — a guideline that grades observational evidence
  elsewhere would not describe observational comparisons as absent, and the
  randomised trial is the only thing that would make the sentence plainly false.

And the part that matters most to a reader deciding whether to care:
**nothing downstream changes either way.** On both readings, no study of any
design separates abemaciclib from ribociclib.


---

## To fix when this issue publishes: the correction names only the right answer

**Found 10 September 2026, verifying the correction email's destinations from served bytes.**

cdk46's live change log says:

> *"Also corrected: an author surname in the section on trial power. The page
> named the wrong researcher; the first author of that 2018 npj Breast Cancer
> paper is Marie-Laure Tanguy, and the page now says so."*

**It does not contain the word "Jacot."**

**A correction that names only the RIGHT answer, and not the error, cannot be
verified by the reader who remembers the error.** Somebody who read "Jacot and
colleagues" in the 29 August email, and comes to the log to check whether we
fixed it, finds a correction about *"an author surname"* and a name they have
never seen. They cannot match the two without taking our word that they are the
same sentence — which is the one thing a correction log exists to avoid.

**Melanoma's entries name what was wrong.** *"We had printed, at five years,
68.8% of combination patients recurrence-free against 49.1%"*; *"This page said
it was behind a paywall"*; *"we said every sentence on this page was bound"*.
Each quotes the false thing before correcting it. cdk46's does not.

**Fix when this issue publishes:** the entry names "Jacot" as the wrong name it
replaced. The email going out today carries a parenthesis warning readers that
the entry does not — which is a patch on the email for a defect in the page, and
the page is where it belongs.
