# melanoma — adjudication of the outside review, 2026-09-08

Reviewed content: `2026-09-04-for-reviewer.html`, sha256 `a788f00ab1521235`
Standard: version 1.1 — the version applied to cdk46 on 2026-08-29. Confirm it is
still current before filing.

The review itself is in `2026-09-08-review.md`, with
`2026-09-08-rebase-note.md` and `2026-09-08-verification-addendum.md` beside it,
and none of the three is edited after the fact, including by us. This file sits
beside them and is where our decisions go.

**This draft was prepared by the reviewer, which is a compromise of the thing
this file is for.** In cdk46 the review and the adjudication have different
authors, and that separation is most of what makes an adjudication worth
reading — a reviewer writing up the disposition of their own findings will grade
them generously and will not notice doing it. Every disposition below is sourced
to an implementation decision that was actually made and reported, not invented
here, and where a decision has not been made the entry says so. It was verified
on 2026-09-09 by a session that did not author it, and accepted the same day —
see the record at `2026-09-09-verification-record.md` and the acceptance at the
end of this file. If any disposition reads as more settled
than it was, that is the predictable failure of this arrangement and not evidence
against the finding.

**This is issue one's first adjudication file.** The practice began with issue
two on 2026-08-29. Melanoma had published on 26 August and was already in
revision, and was never brought under it. What that means for the rounds before
this one is recorded under Outstanding, item 5, rather than repaired.

Twenty-two findings. Nineteen accepted, one accepted and superseded, one not
acted on, one partially resolved. Two errors by the reviewer, both rejected
before they reached the page. Every source the reviewer cited was opened and read
here before any change was made — that rule is why two of their errors were
caught, and it is the rule this issue most needed, because the worst error in
this issue came from treating an absence in our own library as a fact about the
world.

---

## OR-001

**Finding**

> "The August announcement was a prespecified interim look, and the register says so."
>
> BREACH: factual error. The word *interim* appears nowhere in the NCT05933577
> record, which has not been updated since 24 September 2025 — eleven months
> before the announcement it is cited about.

**Disposition** — ACCEPT

**Reason**

Verified against the ClinicalTrials.gov v2 API before acting: zero occurrences of
the string, any case, in the full record; `lastUpdatePostDate` 2025-09-24. The
interim fact is real and comes from both company releases, which use the phrase.

The error is not the misattribution alone. This page had been using the
registry's silence as evidence that no Phase 3 effect size exists, and a file
nobody has touched since last September cannot carry that weight. A stale record
is not a live absence, and we had been reading one as the other in a piece whose
subject is what an absence of numbers does and does not establish.

**Change**

The clause is replaced, the fact attributed to the releases, and the registry's
last-update date now appears wherever its emptiness is used as evidence.

**Note appended 2026-09-09.** The verification could not distinguish, from the
library alone, whether S013 was re-pulled on 8 September or merely read: the
store is content-addressed, so a re-fetch returning identical bytes leaves
`held: 2026-09-02` and `superseded: []` unchanged, exactly as a non-fetch would.
The reviewer confirms the re-pull happened — NCT05933577 was fetched from the
ClinicalTrials.gov v2 API on 8 September and the content was byte-identical to
the 2 September copy. So both records are accurate and neither needs correcting:
the entry's "re-pulled 2026-09-08" and the library's "held 2026-09-02" are the
same event seen from two sides. Recorded here because the next person to compare
them will otherwise read a contradiction.

This also settles the page's own dated claim. The sentence "…the trial's own
registry record, which as of 2 September 2026 carries no posted results at all"
is correct as written: 2 September is the date of the bytes we hold, and the
re-pull confirmed they had not changed.

**Sources considered** — S013 (NCT05933577, re-pulled 2026-09-08), S001 (Merck
release), new: Moderna release of 19 August 2026

---

## OR-002

**Finding**

> "Every number above traces to one of these, and none to a news report — a check
> that runs before this page can publish refuses it otherwise."
>
> BREACH: unsupported claim about our own machinery. The five-year rates rest on
> an ASCO meeting abstract, which is not a company release, a registry record or
> a peer-reviewed paper; and the checks do not classify documents that way.

**Disposition** — ACCEPT, and corrected further than the finding asked

**Reason**

Both halves stand. The enumeration had three slots and the document fits none —
a conference abstract is selected, not peer-reviewed, which is the same reason
source quality scores 3 on this page.

The second half is the more serious and the reviewer understated it. They
proposed repairing the enumeration. On inspection the checks test whether bound
spans match held documents, whether figures appear in held documents, and whether
bound sources are represented to readers. They have no opinion on what counts as
news. Repairing the list would have left a sentence offering readers a guarantee
no code provides. The prose now describes what the checks do.

This is the second time on this page that a careful check has been described by
careless prose. The 2 September entry identifies that as the failure worth
keeping in view, and it recurred within a week of being named.

**Change**

Sources and Checking both now read "traces to a company release, a peer-reviewed
paper, a conference abstract or a trial registry record", with outlet-attribution
claims handled separately, followed by a description of what the pre-publication
checks actually test.

**Sources considered** — S014 (ASCO 2026 abstract 9500), the publish gate source

---

## OR-003

**Finding**

> "the upper bound had come in from 0.906, the lower bound had drifted out from 0.288"
>
> BREACH: factual error. 0.288 → 0.294 is the lower bound moving inward. Both
> bounds came in; the interval narrowed at both ends.

**Disposition** — ACCEPT

**Reason**

Arithmetic, and wrong on every available reading of "out": 0.294 is closer to
1.0, closer to the 0.510 point estimate, and closer to the upper bound than 0.288
was. Width 0.618 → 0.593.

Worth noting where it sat. This sentence is in the passage that teaches readers
how to read an interval.

**Change**

> "both bounds came in — the upper from 0.906 to 0.887, the lower from 0.288 to
> 0.294 — so the interval narrowed only slightly"

**Note appended 2026-09-09.** The change landed as adjudicated and is on the
page. The wording moved afterwards: "only" was dropped on 8 September under the
negatives-check ruling, because no span the sentence rests on carries that word's
force and signing a quantifier disposition to preserve one word was the wrong
trade. The page now reads "so the interval narrowed slightly". Recorded in the
step-3 ruling and in `change-reviews.json`. This note is appended rather than the
Change block being rewritten, because the block is a dated record of what was
decided on 8 September.

**Sources considered** — S004, S007

---

## OR-004

**Finding**

> "Any-grade immune-related adverse events were similar — 45.2% on the combination
> versus 44% — but grade 3 or worse treatment-related events were higher: 25%
> versus 18%."
>
> BREACH: two figures placed in a contrast neither can bear. Different AE
> categories, different documents, different follow-up.

**Disposition** — ACCEPT

**Reason**

Verified against both documents before acting. 45.2/44 is immune-related, any
grade, five-year company release. 25/18 is treatment-related, grade 3 or worse,
the *Lancet*'s roughly two-year cut. The sentence's grammar — "similar … but …
higher" — presents them as one measure at two severities.

A like-for-like pair was available in a single document we already held: the
*Lancet* reports immune-mediated events at 36% in each arm alongside grade 3+
treatment-related at 25% against 18%, same patients, same cut. We had the
comparison and did not use it.

This is the article's own subject occurring in the article's own summary: two
correctly sourced numbers set side by side, doing work neither can do.

**Change**

The *Lancet*'s own pair now carries the contrast; the five-year figures are given
separately with their window named.

**Sources considered** — S003 (*Lancet* 2024, abstract re-read), S002 (five-year
release)

---

## OR-005

**Finding**

> "Reading only the first pair would tell you the added therapy costs nothing, and
> it does."
>
> BREACH: ambiguity that inverts the sentence. "and it does" reads most naturally
> as "and it does cost nothing".

**Disposition** — ACCEPT

**Reason**

Accepted without argument. In a piece about sentences that mislead without being
false, this one misled by being ambiguous.

**Change**

> "…costs nothing. The second pair says otherwise."

**Sources considered** — none required

---

## OR-006

**Finding**

> "Expect the score to move by roughly a full point when it lands, in whichever
> direction the numbers point."
>
> BREACH: internal contradiction with our own rubric. Both stated moves are
> upward regardless of what the numbers show, and the sentence did not survive the
> 3 September scorecard split.

**Disposition** — ACCEPT

**Reason**

Recomputed against the two-score structure. Source quality 3→5 lifts *is the
effect real* from 3.94 to about 4.56. Data support 1→4 or 5 lifts *how large is
it* from 1.0 to 4 or 5. Neither depends on what the numbers say, because the
rubric scores whether the evidence has been shown, not whether it flatters.

The sentence was written for a single composite and outlived it by six days. It
is a small instance of the same problem as the four misdated log paragraphs: a
change was made and its dependants were not swept.

**Change**

> "That single release moves both scores, and both upward whatever the numbers
> say, because the rubric is measuring whether the evidence has been shown rather
> than whether it is good…"

**Sources considered** — the published rubric

---

## OR-007

**Finding**

> "Every outlet whose article we hold attributed those figures correctly to
> KEYNOTE-942 in its own voice"
>
> BREACH: the inference record's quoted spans support the 49% attribution only;
> none contains the 59% figure. KOL Pulse names no trial at all.

**Disposition** — ACCEPT

**Reason**

The record carries six spans and not one of them quotes the 59% figure, while the
sentence claims both. Separately, KOL Pulse's span reads "In a phase 2 trial
earlier this year" — an outlet that never names KEYNOTE-942 has not attributed
the figures to KEYNOTE-942. That is not misattribution, which is our point, but
it is not what the sentence said.

Appendix C had already flagged the "in its own voice" qualifier and asked whether
it was a fair distinction or a hedge. The reviewer's answer — fair, but not the
load-bearing problem — is accepted.

**Change**

The sentence is narrowed and KOL Pulse described as having identified the figures
as coming from an earlier phase 2 trial without naming it.

**Sources considered** — S006, S011, S016, S018, S019, S017

---

## OR-008

**Finding**

> "this page holds no document about one" — a CTLA-4 inhibitor.
>
> BREACH: destroys universal negative 6. EORTC 18071 reported overall survival
> against placebo as a prespecified secondary endpoint: 65.4% v 54.4% at five
> years, HR 0.72 (95.1% CI 0.58–0.88), p=0.001.

**Disposition** — ACCEPT

**Reason**

Read in full before acting, from the NEJM abstract via PubMed (PMID 27717298).
Every figure confirmed.

The PD-1-scoped sentence was correct and stands. What the finding destroys is the
paragraph around it. It opened with adjuvant melanoma trials whose recurrence
benefits "sometimes never did" translate into survival, listed three negatives,
and closed by noting we held no document about a CTLA-4 inhibitor — a true
sentence functioning as a reason not to look. There is such a trial, it is the
one adjuvant checkpoint inhibitor in this disease with a demonstrated survival
benefit against placebo, and omitting it left readers with an impression we had
not checked and could not have defended.

The two caveats cut our way and are on the page: 10 mg/kg is not clinical
practice, and five patients died of immune-related events. That is why the drug
is not standard care, and it is not because it failed on survival.

**Change**

The clause is deleted and the trial added, with its figures, to the paragraph and
to the sources. Universal negative 6 is removed from Appendix C.

**Sources considered** — new: Eggermont et al., N Engl J Med 2016;375:1845–1855,
DOI 10.1056/NEJMoa1611299, PMID 27717298, PMCID PMC5648545

---

## OR-009

**Finding**

> The CheckMate 238 exclusion is honest but the reason given is the weaker half.
> Ipilimumab is itself the comparator with a proven survival benefit against
> placebo, so failing to separate from it is a harder test, not a null one.

**Disposition** — ACCEPT

**Reason**

Appendix C had asked reviewers to check whether that exclusion was "honest and
not convenient". It is honest. The argument given — that every patient received
an active treatment — is correct and incomplete. Adding what the comparator
actually is turns an exclusion into an argument.

**Change**

A clause added to the same paragraph noting what ipilimumab has shown, linking to
OR-008.

**Sources considered** — S021, and the EORTC 18071 paper added at OR-008

---

## OR-010

**Finding**

> "The single most useful question to ask of any interval: does it cross 1.0?"
>
> BREACH: internal contradiction with our own cited source. Greenland et al.
> exists to argue against exactly this dichotomisation, and we quote that argument
> elsewhere in the appendix.

**Disposition** — ACCEPT

**Reason**

The rule is the significance dichotomy in interval form, the chart's amber/green
colouring hard-codes it, and our own statistics source calls that a degradation
of the P value — in a span this page already quotes. The inference record knew
the rule was editorial advice rather than a finding. The reader was never told.

**Change**

Demoted from "the single most useful question" to the first of two, with width
and the meaning of the far end as the second, and a note that the first question
is a convention rather than a verdict. The chart carries the same caption.

**Sources considered** — S022 (Greenland et al.)

---

## OR-011

**Finding**

> The confidence-interval chart judges the 2023 readout by a two-sided 95%
> interval — the 0.05 standard the piece later says this trial never used.

**Disposition** — ACCEPT, with the reviewer's proposed wording rejected. See
RV-02.

**Reason**

The tension is real and the fix is not the one proposed. The chart draws 95%
intervals; the trial registered a one-sided alpha of 0.10; two sections later the
piece says 0.053 is a near miss only against a line this trial never used. Naming
the standard the chart applies resolves it.

**Change**

The chart caption now states that these are 95% intervals, the convention readers
meet elsewhere, that the trial registered a one-sided alpha of 0.10, and that the
amber/green split is a convention rather than a verdict. The 2023 sentence now
reads "on a two-sided 5% criterion", which names the standard being applied
instead of leaving it implicit.

**Sources considered** — S007, S003, S005

---

## OR-012

**Finding**

> The p-value section defends the trial with its one-sided alpha of 0.10 without
> telling the reader that 0.10 one-sided is four times more permissive than the
> 0.05 convention taught two paragraphs earlier.

**Disposition** — ACCEPT

**Reason**

The asymmetry is the problem, not the defence. The piece is scrupulous about
flagging when a comparison flatters, and here it supplied the exculpating context
and withheld the qualifying half of it.

**Change**

> "— a permissive threshold, equivalent to a two-sided 0.20, and a normal choice
> for a phase 2b trial built to find a signal rather than settle one."

**Note appended 2026-09-09.** The change landed as adjudicated. The wording moved
afterwards: "equivalent to a two-sided 0.20" was removed on 8 September because
0.20 is the page's own doubling of the registered one-sided 0.10 and appears in no
held document, which rule 1 flagged as a figure in no span the sentence is bound
to. The nearest 0.20 in S022 belongs to an unrelated replication-crisis
calculation, and binding to it would have repeated RV-02. The page now reads "a
permissive threshold, and a normal choice for a phase 2b trial built to find a
signal rather than settle one."

**Where this is recorded, and the gap in it.** Only at round level, in the
`ROUND-2026-09-08` change set — there is no entry-level decision for it. That is
why the trail is hard to follow, and it is the entry-level pointer.

**Sources considered** — S007

---

## OR-013

**Finding**

> S023 (Spruance et al., *Hazard ratio in clinical trials*) is in the manifest
> marked `not_opened`, and contains two things the hazard-ratio explainer needs:
> the proportional-hazards assumption, and a legitimate patient-level gloss.

**Disposition** — ACCEPT

**Reason**

Read in full from PMC478551 before acting. Two substantive gaps confirmed.

First, our gloss — "at any given moment during the trial, someone in the
treatment group was recurring or dying at about half the rate" — *states* the
proportional-hazards assumption as fact. The three-year paper's own methods
assume it, fitting a stratified Cox model. This page carries three estimates that
move with follow-up: OS 0.425 → 0.471, DMFS 0.384 → 0.411, RFS unchanged. Two of
three drift toward the null, and we gave the reader no way to tell noise from
non-proportionality.

Second, we correctly forbade "49% of patients were saved" and left the reader
with rate language. There is a legitimate patient-level reading and we did not
offer it.

**Change**

An assumption note in the hazard-ratio card, and in "The number that matters
more" the pairwise reading — about a 66% chance a treated patient goes longer
without recurrence, against 50% if the therapy did nothing — with Spruance's
race-and-margin framing. S023 moves to `full_text_held` and enters the sources.

**Sources considered** — S023 (PMID 15273082, PMCID PMC478551), S007

---

## OR-014

**Finding**

> The summary strip carries two Phase 2b figures with no trial label, directly
> under a Phase 3 headline — the error J02 diagnoses, in the page's own furniture.

**Disposition** — ACCEPT

**Reason**

Accepted. The strip is above the fold and is the first thing a scanner reads.

**Change**

The two figures now say Phase 2b.

**Sources considered** — none required

---

## OR-015

**Finding**

> The reassurance that blinding solves the assessment problem sits on the same
> page as injection-site pain 59.6% and chills 51.0%, against a saline placebo,
> with an investigator-assessed primary endpoint. The two halves are never joined.

**Disposition** — ACCEPT

**Reason**

The strongest finding in the review, and the one no check could have produced: it
requires holding two distant passages together and knowing what reactogenicity
does to a blind. The registry names the comparator as normal saline or dextrose.
A therapy causing injection-site pain in three of five recipients against an inert
injection can functionally unblind patients and treating physicians, and the
primary endpoint — and the key secondary — are investigator-assessed.

We asserted that blinding closes the gap, held the evidence that it may only
narrow it, and did not say so.

**Change**

A caveat paragraph in the blinding section, and the key secondary's assessment
basis now stated alongside the primary's.

**Sources considered** — S013, S002, S003

---

## OR-016

**Finding**

> "Whether the benefit holds in stage IIB/IIC patients, whom the earlier trial
> never enrolled." Incomplete: the Phase 3 also added IIIA.

**Disposition** — ACCEPT

**Reason**

Verified. Registry inclusion criterion reads "Stage IIB or IIC, III, or IV
cutaneous melanoma"; the *Lancet* confirms KEYNOTE-942 enrolled IIIB–IV. IIIA
patients were never enrolled either and are also lower-risk. The body paragraph
already said the Phase 3 added IIIA; the bullet had dropped it.

**Change**

"stage IIB, IIC and IIIA patients", with an inference record added for the IIIA
step.

**Sources considered** — S013, S003

---

## OR-017

**Finding**

> KEYNOTE-054's overall-survival result carries an anticipated posting date of
> November 2026 — the most decision-relevant date available to a piece whose
> central open question is whether this therapy extends life.

**Disposition** — ACCEPT

**Reason**

In a registry record we already cite, in a field we had not read. Two months out
at the time of review.

**Change**

Both dates now on the page — November 2026 for KEYNOTE-054, October 2033 for
KEYNOTE-716 — in the survival paragraph and in "What would settle this", and in
the source notes for both records.

**Sources considered** — NCT02362594, NCT03553836

---

## OR-018 — partially acted on

**Finding**

> Reproducibility 4, Consensus 4 and Recency 5 carry no reasoning anywhere on the
> page or in the inference records. They contribute 1.90 of the 3.15 numerator
> behind 3.94 — 60% of that score. "The arithmetic is shown so you can disagree
> with it" invites disagreement with numbers a reader has no basis to evaluate.

**Disposition** — PARTIALLY ACTED ON. Prose applied; records not.

**Reason**

The finding as written above is half wrong, and the wrong half is mine. All three
sentences were on the page already: the 9 September pass added them and the change
report records them under **Score rationale — Added**, verbatim. I reported them
absent because I read the scoring paragraph through a 400-character truncation of
a 1,013-character paragraph (1,152 as an HTML element) and the three sentences
begin at plain character 484. [figure corrected 2026-09-09; this originally read 2,116, which was never measured — see RV-08]
See the verification addendum, section 7, and RV-03 below.

What was genuinely missing is the other half. Appendix A carried no inference
record for any of the three — it covered the two composites, rigor and source
quality, and stopped. The reasoning was on the page and its provenance was not.
That is the half worth acting on and it has now been acted on.

The three replacement sentences I drafted for the operator's resolution were NOT
applied, and should not be. Two of the three are worse than what the page has. My
recency sentence ends "Nothing newer exists on this programme", an unscoped
universal negative that would have bought an Appendix C entry the page does not
need; the page's sentence asserts what the evidence is rather than what it is not.
My consensus sentence asserts "nothing in the coverage we hold disputes… and we
found no published dissent when we looked", where the page's sentence — "the held
sources agree on the directional Phase 3 result" — is already scoped to the
coverage we hold and says the same thing positively and at no cost. On
reproducibility the two are substantively identical.

**Change** — three inference records added, one per sentence, against the existing
prose: reproducibility on S001 (both endpoints met) and S004 (the 0.510 with
nothing to be set beside it); consensus on the eight coverage sources in
Appendix B that report the Phase 3 announcement, scoped to them in the sentence
itself; recency on the datelines of S001 (19 August 2026) and S002 (1 June 2026).
Every span verified against the held document at write time. No page prose
changed. Both scores unchanged at 3.94 and 1.0.

**Sources considered** — the published rubric

---

## OR-019 — accepted, then superseded

**Finding**

> The survival bullet compares an 80% interval to a 95% interval as though they
> were the same instrument.

**Disposition** — ACCEPT, applied, and now superseded by better evidence

**Reason**

Applied as "at 95% it would be wider still", which is true and vague. On reading
the three-year paper in full the actual figure was in the same table row: OS HR
0.425, 80% CI 0.179–1.004, **95% CI 0.114–1.584**.

At equal width the three-year interval is the *wider* of the two — 0.114–1.584
against the five-year 0.165–1.345 — which is what nine deaths buys against
fourteen, and the opposite of what the mixed presentation implies. Using the
narrower instrument for the sparser analysis made the weaker evidence look
tidier.

**Change** — the hedge stands on the page. Replacing it with the figure requires
no new source. Carried to Outstanding, item 2.

**Sources considered** — S007, read in full 2026-09-08

---

## OR-020 — partially resolved

**Finding**

> Appendix B skips S012 (S011 → S013), and S008 is marked `full_text_held` while
> cited by no inference and appearing in no source entry.

**Disposition** — PARTIALLY RESOLVED

**Reason**

S003 and S008 are distinct documents, not one paper under two ids. S023 was
already `full_text_held`, so that half of the reviewer's instruction was stale.
S012 remains unexplained, and the implementation correctly declined to invent an
answer.

One thing was established after the fact: `review_packet.py` iterates
`store.sources()` and prints `s["id"]` verbatim, with no filter, renumbering or
skip condition. The generator cannot create an id gap, so the absence is in the
source store.

**Change** — none required for S003/S008/S023. S012 carried to Outstanding,
item 3.

**Sources considered** — `review_packet.py`, the source store

---

## RV-01 — reviewer error, rejected

**Raised**

> The reviewer verified our earlier claim that KEYNOTE-054 and KEYNOTE-716 "each
> posted an overall-survival result that carries no statistical analysis at all",
> reporting it as "verified true as stated".

**Disposition** — REJECT

**Reason**

They queried the `analyses` field and not the one that decides it. Both records
carry `reportingStatus: NOT_POSTED` with `anticipatedPostingDate` 2026-11 and
2033-10. Nothing has been posted.

This page had already been corrected on 4 September. Accepting the confirmation
would have restored an error we had fixed, and the difference matters: a result
withheld reads as evasion, a result not yet due is a schedule.

The reviewer identified and corrected this themselves on 2026-09-08 and it is
recorded in the rebase note.

**Sources considered** — NCT02362594, NCT03553836

---

## RV-02 — reviewer error, rejected

**Raised**

> The reviewer proposed a chart caption attaching the three-year paper's 80%
> interval, 0.351–0.743, to the 2023 readout.

**Disposition** — REJECT

**Reason**

That interval belongs to the three-year HR 0.510. Confirmed from Table 1 of the
three-year paper: "RFS: HR 0.510 · 80% CI 0.351 to 0.743 · 95% CI 0.288 to
0.906". No 80% interval for the 2023 result exists in any document we hold — the
nearest values, HR 0.564 and 0.571, are TMB subgroups from the three-year
analysis.

The caption would have put a figure on a result it was never computed for and
sourced it to a document that does not contain the pairing. Caught by the
implementation refusing the span and stopping, which is the rule working.

**Change** — the 80/95 distinction is explained without the attribution. See
OR-011.

**Sources considered** — S007, read in full

---

## RV-03 — reviewer error, rejected

**Raised**

> The reviewer reported, in the verification addendum, that directive item D2 had
> not been applied: that reproducibility, consensus and recency "still carry no
> reasoning anywhere on the page" and that "the scoring paragraph still explains
> only rigor and data support".

**Disposition** — REJECT

**Reason**

All three sentences were on the page. They were added by the 9 September pass and
recorded in the change report the reviewer held. The reviewer grepped the scoring
paragraph through `cut -c1-400`; the paragraph runs to 1,013 characters of plain
text, 1,152 as an HTML element, and the three sentences begin at plain character
484, so the cut lands inside the data support sentence. [figure corrected 2026-09-09; this originally read 2,116, which was never measured — see RV-08] An absence was reported from the right-hand
edge of a terminal.

Caught by the implementation reading the base before editing it, and stopping
rather than applying an insert whose stated precondition — a paragraph explaining
only two dimensions — was false. Applying it literally would have put six
sentences in the paragraph, two per dimension, in two different sentence patterns.

This is the same error as RV-01 and RV-02, and that is now three of three. RV-01
queried the `analyses` field and not the one that decided the question. RV-02 took
an interval computed in one context and set it down in another. RV-03 read 400
characters of a 1,013-character paragraph. [figure corrected 2026-09-09; this originally read 2,116, which was never measured — see RV-08] Each is a partial view of a document
treated as a fact about the document, which is standing rule 2 and the subject of
the article under review. A reviewer whose three errors in a round are all one
error is a finding about the review process, not about any of the three.

**Change** — none to the page. The verification addendum carries a correction at
section 7; it is appended rather than edited, per the no-edit-after-the-fact rule
in the header above.

**Sources considered** — the change report, the scoring paragraph as installed

---

## RV-04 — reviewer error, rejected

**Raised**

> The verification addendum reported: "The EORTC 18071 insertion is verbatim
> accurate against the NEJM abstract … Sources entry carries DOI, PMID and PMCID."

**Disposition** — REJECT, on the second clause

**Reason**

The figures were right; the status claim was not. The reviewer verified the
citation against the **rendered page**, where the entry does carry DOI, PMID and
PMCID. The source store held nothing: there was no S-number for the paper, no
bytes in the library, and `b13` reported 0.58 as a figure in no document we hold.
"Held" is a fact about the store, and the store was never asked.

The same error stood in the 8 September log entry as drafted — "The paper is now
held and cited" — which would have published a false claim about a document's
status inside the entry correcting our claims about documents.

Fixed rather than only recorded: the paper was fetched from PubMed Central on
2026-09-08, stored as S029 with the store confirming identity independently
("contains its identifier PMC5648545") and classifying substance as full_text,
and the ledger records `full_text_held`. The clause is now true. The page's link
was also repointed from the PubMed abstract to the PMC full text, because that is
the representation we actually read and hold.

This is the fourth reviewer error in this round and the fourth instance of one
error: RV-01 read a field and not the record, RV-02 took an interval from one
context to another, RV-03 read a truncation and not the paragraph, RV-04 read a
rendering and not the store. It is now failure 14 in the process document, whose
detection is to name the artefact you actually read.

**Change** — S029 added and held; page link repointed; log clause now true.

**Sources considered** — S029, `sources.json`, the library index, `b13`

---

## RV-05 — reviewer error, half of OR-007 rejected

**Raised**

> Within OR-007: "KOL Pulse names no trial at all", and the reasoning that "an
> outlet that never names KEYNOTE-942 has not attributed the figures to
> KEYNOTE-942."

**Disposition** — REJECT that half. The rest of OR-007 stands.

**Reason**

KOL Pulse names KEYNOTE-942 eleven times in its own editorial text and attributes
the circulating hazard ratios to it in terms: "hazard-ratio figures circulating on
announcement day are these KEYNOTE-942 Phase 2b numbers." The span the reviewer
read — "In a phase 2 trial earlier this year" — is inside a third-party social
post the outlet was logging, not the outlet's own voice.

The reviewer read a span quoted in Appendix A and drew a conclusion about the
document the span came from. Appendix A shows what a sentence rests on; it does
not show what else the document says, and a span chosen to support one claim is
not evidence about any other.

That is failure 14 for the fifth time in one round — the `analyses` field, the
80% interval, a truncated paragraph, the rendered HTML, and now a quoted span.
Five for five, and all five caught by the implementation opening the source
before acting on the finding.

**Change** — the sentence was rewritten to attribute the wording to the post KOL
Pulse logged rather than to the outlet, and both it and the five-outlet
enumeration are now bound: each of the five names KEYNOTE-942 in the same
sentence as the 49% figure, and the KOL Pulse row carries both spans and the step
that separates them. The count of five stands. The half of OR-007 about the 59%
figure stands and was acted on.

**Sources considered** — S019, read in full

---

## RV-06 — reviewer error, rejected

**Raised**

> Ruling 1 of 8 September: that the page's "out by 0.05" self-accusation was
> false because 3.35 rounds to 3.4, and that the correction should be withdrawn.

**Disposition** — REJECT

**Reason**

The August page's own printed arithmetic came to 3.4000 exactly. It used a
different weight set — reproducibility and recency at .15 each, where the rubric
gives .20 and .10. Both sets sum to 1.00; the entire 0.05 is that one swap,
corrected in commit 87b8d9d on 3 September alongside the rubric's publication. No
rounding was ever involved. The page's original account was wrong and so was the
reviewer's replacement for it.

The reviewer did attach a caveat — "check what the 26 August page printed before
finalising" — but attached it to the display convention, which was not the failure
mode. A caveat covers the axis its author happened to imagine. It is not a check,
and it reads as diligence to everyone including the person who wrote it. The five
errors before this one were caught by opening the artifact; this one was not
caught by naming an uncertainty about it.

The implementation resolved it by reading the commit history, which is the
artifact neither account had opened.

**Change** — the scoring section and the relocated log paragraph now state the
weight swap; and because "out by 0.05" was published on 4 September and has stood
since, the newest entry carries a correction saying the page overstated its own
error.

**Sources considered** — `git log` and `git show` on
`site/whatholdsup/melanoma.html` and `site/whatholdsup/the-rubric.html`, commits
2c71b8e through 87b8d9d

---

## RV-07 — reviewer error, and the first one a check caught

**Raised**

> Supplying EORTC 18071 for the counterexample paragraph, and quoting its
> figures, without recording that the paper has been formally corrected.

**Disposition** — REJECT the omission; the paper stays.

**Reason**

The erratum field was in the same PubMed response the figures were quoted from,
four lines above them:

    Erratum in
        N Engl J Med. 2018 Nov 29;379(22):2185. doi: 10.1056/NEJMx180040.

Seventh instance of one failure: taking the part of a document that was wanted
and not attending to the field that qualified it. RV-01 read the `analyses`
field and not the one that decided it; RV-02 moved an interval between hazard
ratios; RV-03 read 400 characters of 1,013; RV-04 read the rendered page and
called the store; RV-05 read a span from Appendix A and called the document;
RV-06 attached a caveat to the display convention rather than opening the commit
history. This is the same shape again.

**One thing distinguishes it, and it is the good news.** The other six were
caught by a reader opening an artifact. This one was caught by `errata.py`
running on its own, on a source that had been in the store for a day. The
machinery found what the reviewer missed, which is the reverse of this cycle's
pattern, and it is the evidence that the errata check earns its cost.

**What was established, and what was not.** The erratum exists, is PMID
31442371, and covers `10.1056/NEJMoa1611299` as one of thirteen NEJM articles in
one notice. It could not be obtained: NEJM 403, Europe PMC `isOpenAccess N` and
`inEPMC N`, Crossref title and date only with no `update-to`, PubMed carrying the
coverage list and no text. That the shape of a thirteen-paper notice spanning
2013 to 2018 with overlapping author groups is characteristic of a disclosure
correction is a pattern argument, is recorded as one, and is not the basis of any
decision here.

**Change** — the paper stays. Removing a true, well-sourced counterexample on the
strength of an unread notice would restore the impression OR-008 exists to
correct. The page now carries the gap in its own source note, where a reader is,
rather than only in the record; the PubMed record of the erratum is held as S030,
with the notice itself explicitly not held; and S029 keeps an open errata item,
undispositioned, until the notice is read. If it is ever obtained and touches a
figure on this page, that is a correction and goes in the log.

**Sources considered** — S029, S030, NCBI efetch for PMID 31442371, Europe PMC
and Crossref for 10.1056/NEJMx180040

---

## RV-08 — reviewer error, upheld by the verification

**Raised**

> By the rule 13 verification, 2026-09-09: RV-03, OR-018 and the process document
> all state that the scoring paragraph "runs to 2,116 characters". It does not.

**Disposition** — UPHELD. The figure was fabricated; the mechanism it described
was not.

**Reason**

Measured on the declared base and on the installed page, which are byte-identical
for that paragraph:

| | |
|---|---|
| paragraph, plain text | **1,013** |
| paragraph, as an HTML element | **1,152** |
| `Reproducibility scores 4` begins at plain character | **484** |
| plain character 400 falls inside | the data support sentence |

So the mechanism in RV-03 is exact and stands: a 400-character cut does land
before the three sentences, and "roughly character 480" was right. Only the size
was invented.

Where it came from: the original probe was a fixed 2,400-character window of raw
HTML, `re.search(r'Two scores, not one.{0,2400}', s)`, tag-stripped afterwards.
2,116 is the text content of an arbitrary window. It was never a measurement of a
paragraph, and it was then reported as one.

**It was wrong in the direction that flattered.** 400 of 2,116 is a defensible
sliver of a long paragraph; 400 of 1,013 is most of a short one. The fabricated
number made the original error look more forgivable than it was, inside the entry
whose subject is asserting things about documents without opening them.

It was then propagated seven times across four documents by two parties, neither
of whom measured it: the 8 September directive amendment where it originates, the
verification addendum §7, OR-018, RV-03, the process document, the remediation
order, and the RV list at RV-07.

**Change** — all seven corrected in place to 1,013 plain / 1,152 HTML with the
484 offset, each carrying a marker recording what it originally said, so the
correction does not erase the evidence. The lesson is in the process document
beside failure 14: a wrong number that looks right propagates further than a
wrong argument.

**Found by** — the rule 13 verification, on its first run. Not by any check, and
not by either author.

**Sources considered** — `melanoma.revised.html` and the installed page, both
measured; the seven documents carrying the figure

---

## RV-09 — reviewer error, and the second one caught downstream

**Raised**

> "S028 is not there … Do not re-run those searches. Report only what the S028
> record itself contains." Issued with the finding that the citation "cannot be
> located from what we recorded", after searching Europe PMC full text, the
> journal's melanoma listing, the open web and the operator's Downloads folder —
> every PDF text-extracted, every HTML/TXT/MD/JSON grepped.

**Disposition** — REJECT the finding. The document was locatable, and from our
own file.

**Reason**

The S028 record has carried `doi: 10.1007/s11845-026-04315-0` and
`pubmed: 41920444` since 4 September. Neither had ever been queried. Both resolve
immediately:

* PubMed efetch on 41920444 returns the article, title matching the record.
* Crossref on the DOI returns the full bibliographic record — *Irish Journal of
  Medical Science*, volume 195, pages 1251–1252, April 2026, first author Laiba
  Riaz (ORCID 0009-0009-6649-3059) — **and the twelve references the publisher
  deposited.** Reference 12 is the Morning Glory Sciences news flash, verbatim.

So the counterexample is machine-readable from the publisher and reproducible by
anyone with the DOI. Four searches of the outside world were run and declared
exhaustive while the nearest source — our own source file — went unread.

**Ninth instance of one failure family, in a new direction.** The other eight
were partial views of a document treated as facts about it. This is a search
declared exhaustive without checking the nearest place, which is the same error
with the arrow reversed: not "I read part of it and concluded about the whole"
but "I looked everywhere except the obvious place and concluded it was nowhere".

**What makes this one worth more than the correction.** The instruction that
carried the error also specified the remedy: an appended note, in `sources.json`
and `corrections.md`, stating that the counterexample "rests on a reference-list
observation of a document we have not read and could not reach." Written as
directed, that would have put a false statement into the two files this
publication uses to record what it can and cannot show — inside a correction
about a false statement. It was caught because the executing agent queried the
identifiers before writing the note, found the premise false, and declined it.

That is the second time in this cycle the reviewer was corrected by something
downstream rather than by the reviewer. RV-07 was caught by `errata.py` running
on its own; this was caught by the implementation refusing a premise. Neither was
caught by review.

**Change** — the notes in `sources.json` and `corrections.md` record what the
lookup actually showed rather than what the instruction assumed. Appendix C
records item 10 as FALSIFIED rather than "falsified or unverifiable": we hold the
disproof. The page is unchanged and stays merits-only — reference 12 is one
citation of a news flash about multiple myeloma and supports no claim about the
outlet's standing in either direction.

**Sources considered** — S028's own record, NCBI efetch for PMID 41920444,
Crossref for DOI 10.1007/s11845-026-04315-0

---

## ROUND-2026-09-08 — the change set, and what decided it

**What this is**

Not a finding. A round-level attribution for `reconcile()`, recorded because the
prose changes between the reviewed snapshot and the published page were decided
in documents rather than one sentence at a time.

**Span** — from `a788f00ab1521235`, the page as the outside review read it, to the
page this adjudication closes over. Both ends are pinned: the moment the page
changes again this set stops covering and the next round records its own.

**What decided the changes in that span**

- `issues/WHU-001-melanoma/review/2026-09-08-review.md` — the 22 findings
- `issues/WHU-001-melanoma/review/2026-09-08-rebase-note.md` — which of them were
  still live against the 4 September base, and which were already fixed
- `issues/WHU-001-melanoma/review/2026-09-08-adjudication.md` — this file:
  OR-001 to OR-020 and RV-01 to RV-05
- `issues/WHU-001-melanoma/review/2026-09-08-stop-and-remediation.md` — the eight
  remediation items and the two rulings that followed

**Why it is a set and not 247 entries**

Rule 14 distinguishes two states and its first version did not. A change whose
reasoning never existed is unrecoverable and the log says so; that is the 175
changes of 28 August to 4 September, closed by decision and not by research. A
change whose reasoning exists but is not linked is a bookkeeping debt. These are
the second kind. Writing them out one diff at a time would produce a record that
looks like 247 decisions and represents four documents, which misrepresents how
the work was decided — the same objection that stopped the 175 being backfilled.

**What stops this being a waiver**

Both shas are pinned, every document named must exist on disk, and this label must
resolve as a decision label like any other. A set-attributed change is reported as
set-attributed and never as though someone had written a reason for that
particular sentence. The schema change is in `publish.py`, `recorded_change_sets`
and `valid_change_sets`.

---

## Outstanding after this adjudication

*This section is state, not a record: it is kept current, and items closed after
the adjudication say so with the date. The dated entries above are records and
are not retro-edited — where one needs correcting, a dated note is appended to
it. See §13 of the process document.*

1. **OR-018 — CLOSED.** The prose was already on the page; the missing half was
   Appendix A, and three inference records have been added against the existing
   sentences. Not outstanding. The finding as originally written — that the three
   scores carry no reasoning anywhere — was wrong about the page and is corrected
   in the entry above and in RV-03.
2. **OR-019 — CLOSED 2026-09-08.** The hedge was replaced with the figure. The
   page carries "95% CI 0.114 to 1.584" and "at 95% it would be wider still" is
   gone. No new source was needed; the pair sits in one row of S007's Table 1.
   Not outstanding.
3. **S012.** The gap is in the source store, not the generator. Appendix B is the
   denominator for every "in the coverage we hold" claim, so a silently retired
   document is exactly what that denominator should not lose. Not blocking
   publication of the page; blocking the next review packet.
4. **The 4 September log entry, and the misdated paragraphs — CLOSED
   2026-09-08.** The entry is in the log. Six paragraphs were misdated, not four:
   the diff found three under "Updated 28 August 2026" and one edited in place
   inside the 2 September entry; reading every paragraph against the date of its
   own heading found two more. One of those was ruled to stay — "Statistical
   language", whose closing clause is a signposted forward reference to a later
   entry rather than a misdated claim — and the other, "What the evidence
   supports", was split, its middle moving to 4 September. The header now reads
   9 September and matches the newest entry. Not outstanding.
5. **The record before this file.** 175 of 208 prose changes between 28 August
   and 4 September reconcile to no written decision. No melanoma adjudication
   file exists for any earlier round; the practice began with issue two on
   29 August and issue one was never brought under it. Those justifications
   cannot be recovered and will not be reconstructed — rationale written now
   would read as more confident than the decision it replaces, because it is
   written knowing the change survived. The log will say so instead. This item is
   recorded here so that the absence is a decision rather than an oversight, and
   it is closed by that sentence, not by research.

---

## What this review demonstrated

Three of the six factual errors were in sentences with no inference record among
the 37. That is not a coincidence and it is the most useful thing in this
adjudication: Appendix A covers steps from facts to conclusions, and these three —
a claim about what a registry says, a description of which way two bounds moved,
a comparison between two figures — are all inference-shaped and none was
recorded. The coverage rule needs widening before the next issue, not after.

The gate had already run its budgeted passes for this issue and Appendix D said
so, naming five sentences no role had read. None of the six errors was in that
list. The gate did not miss them because it ran out of runs; it missed them
because they are not the kind of thing it reads for. OR-015 in particular
required holding two passages several thousand words apart and knowing what a
reactogenic injectable does to a blind. No number of further runs produces that.

Two of the errors are recurrences. OR-002 is prose overstating what a check
provides, which the 2 September entry names as the failure worth keeping in view;
it recurred within a week. OR-001 is treating an absence in our own library as a
fact about the world, which is the error the 1 September correction was about.
Both were caught by readers.

And the review itself was run against a stale base. The packet handed to the
reviewer was the 3 September build; the live page was the 4 September one, and
four of the twenty-two findings were already fixed before the review began. The
bundle warns about exactly this in its own header. The fix is one line in the
reviewer prompt — *if a newer `for-reviewer` build exists, review that* — and a
reviewer whose first action is to list the directory rather than trust the
attachment.

---

## Accepted for publication

Verification: `2026-09-09-verification-record.md`, against page sha
7ae5304cf5b7313b, performed by a session that did not author this adjudication.

I have not independently verified its technical content and am not attesting to
it. I am recording a publication decision: this issue publishes under this
publication's name, with one item open by my ruling — the S029 erratum, which
we have not read and which the page discloses.

Accepted by Fred Ugast, 9 September 2026.

*Transcribed verbatim into this file by the verifying session, 2026-09-09. The
wording is the operator's and was not edited. The acceptance is his act; this
was the clerical half of it.*
