# WHU-002 — the first check of sentences against documents we hold

Three papers entered the library on 1 September: MONALEESA-7's overall-survival
paper (S007, NEJM 2019), MONALEESA-2's (S005, NEJM 2022) and PALOMA-2's primary
paper (S009, NEJM 2016). The operator downloaded all three in a browser after
every automated route was refused; the JCO MONARCH 3 paper (S002) is still
behind a paywall.

This is the first time any figure on this page has been checked against a
document we hold, rather than against what a retrieval returned. It cost
nothing. No model was called. Every check below is a string in a file whose
sha256 is in `library/issues/cdk46.json`, and anyone can repeat them.

## What the figures did

**Eighteen figure-level checks. Eighteen confirmed. No arithmetic error, no
transcription error, no misquoted interval.**

MONALEESA-7 (S007) — median not reached versus 40.9 months, HR 0.71, 95% CI
0.54 to 0.95, one-sided P = 0.00973, prespecified stopping boundary P = 0.01018,
34.6 months median follow-up, and the analysis being protocol-specified: all
verbatim. The paper: *"The one-sided stratified log-rank P value was 0.00973,
which crossed the prespecified stopping boundary (P = 0.01018)."*

MONALEESA-2 (S005) — 63.9 versus 51.4 months, HR 0.76, 95% CI 0.63 to 0.93,
two-sided P = 0.008: verbatim. The page's table says 6.6 years and the source
entry says 80 months; the paper says both, in its abstract and its results.

PALOMA-2 (S009) — 24.8 versus 14.5 months, HR 0.58, 95% CI 0.46 to 0.72,
two-sided P < 0.001: verbatim.

Two ABSENCES, which are the checks that could not be made before, are now made
by something in a position to observe them. The page says the unrounded PALOMA-2
figures 0.576 (0.463–0.718) do not appear in NEJM 2016, and that MONALEESA-7's
0.712 (0.535–0.948) does not appear in NEJM 2019. Neither string occurs in
either document. Both claims were true. Both were, until today, an absence
asserted by something that had never opened the file.

## What the reading found instead

The errors are not in the numbers. They are in how the page says it knows them,
and they are all of one kind: **the page was written around documents nobody
held, and the workarounds are still in it.**

---

## CORR-20 — "every" was asserted from one instance, and is false

**Where.** Body: *"its registry record (NCT01740427) labels every log-rank
p-value on the study `1-sided p-value from the stratified log-rank test`"*. The
source note for NCT01740427 repeats it as *"every such analysis in the posting
is annotated..."*.

**The record.** PALOMA-2's results posting is in the library (S020, sha
5b719bb4d0d7). It contains **20 analyses**, of which **15 are log-rank**. Three
of the fifteen — progression-free survival, the primary overall-survival
analysis, and the final overall-survival analysis — are stratified log-rank and
carry the annotation. **Twelve carry no directionality annotation at all**; they
are unstratified log-rank tests of biomarker subgroups, and the posting says
nothing about their sides.

So "every log-rank p-value on the study" is wrong about twelve of fifteen. The
true claim is narrower and self-evidencing, because the quoted annotation names
its own scope: every **stratified** log-rank analysis in the posting is
annotated one-sided, and there are three of them.

**This is the failure `registry_settle._annotation()` was written to prevent** —
it enumerates the analyses so that "every" is counted rather than generalised
from the first one seen. It was run against MONALEESA-2 and never against this
sentence.

**Fix.** Narrow the claim to the stratified analyses and state the count.

---

## CORR-21 — the page routes around a paper it now holds

**Where.** Body: *"MONALEESA-7's is one-sided: the ASCO 2019 abstract of the same
analysis states that 'statistical comparison was made by 1-sided stratified
log-rank test'."* And in the source note: *"The direction of the test is stated
in the ASCO 2019 abstract of the same analysis — ... — and confirmed
independently in the trial's ClinicalTrials.gov results posting."*

**The record.** The NEJM paper this page cites states it itself, in its results:
*"The one-sided stratified log-rank P value was 0.00973."*

Nothing here is false. But a careful reader is told the direction comes from a
conference abstract and a registry posting, and infers that the publication did
not say it. The publication said it plainly. That construction exists because on
29 August nobody could open the paper, and it survived into a version of the page
where we hold it.

There is a second cost. S023, the ASCO abstract, is `fragment_only` — we do not
hold it, and it is on the page carrying one quotation, for this. The paper
retires the need.

**Fix.** Cite the paper first for the direction of MONALEESA-7's test; keep the
registry as the independent confirmation it is; reconsider whether S023 still
earns its place.

---

## CORR-22 — the page applies opposite rules to two trials on the same question

**Where.** For MONALEESA-2 the page says, deliberately: *"This page prints the
journal's figure, because the journal is what a reader will find, and it does not
call that figure one-sided, because it is not."* Four positions were taken on
that one fact before this one; the fourth is the careful one.

For PALOMA-2 the page says: *"PALOMA-2 is one-sided too, at an alpha of 0.025."*

**The record.** NEJM 2016 prints, for the primary progression-free-survival
analysis, *"two-sided P<0.001"*, twice — in the text and in Figure 1A. Its
sample-size calculation used *"a one-sided alpha level of 0.025"*. The registry
gives the same endpoint a one-sided p-value of <0.000001. Both descriptions are
of one design; they are not in conflict, and the page's own MONALEESA-2 passage
explains exactly why.

The inconsistency is in the treatment, not the facts. The page prints
`two-sided P < .001` in PALOMA-2's source entry and calls PALOMA-2 one-sided in
the body, four hundred words apart, having told the reader in between that it
declines to do that for MONALEESA-2.

**This one needs a decision rather than a fix.** The two candidate rules are:

  A. Print what the journal prints, and discuss direction only where the
     direction changes what a reader should conclude — MONALEESA-2's treatment,
     applied to PALOMA-2.

  B. State the design's alpha for every trial, since the page's argument is
     partly about what these tests were built to detect — PALOMA-2's treatment,
     applied to MONALEESA-2.

Either is defensible. Holding both is not, and the page currently holds both.

---

## What this changes about the read rate

Before today, three sources had been opened by a person and all three produced
corrections; the read rate and the error rate were one number. Three more are
now open. They produced **no factual correction and three corrections of
characterisation**, two of which exist only because the documents had been
unavailable when the sentences were written.

That is a different distribution, and it is worth saying plainly: acquiring the
documents did not mainly find us wrong about the science. It found the page
still carrying the scaffolding it had built to work without them.

**Six documents remain unheld: S002, S003, S006, S008, S010, S011, S023.** The
page rests figures on all of them. S002 and S003 are MONARCH 3, whose survival
result the page's central table prints and whose alpha-spending description it
paraphrases in a full paragraph. Those are the two I would want next.

---

# Second pass: the held-but-unread documents

The nine documents in the library that nobody had opened. Two have now been read
in full. What they found is worse than what the first pass found, and one of the
findings is about this file's own method.

## A correction to this file, made before it was published

I briefed a reader to check whether the network meta-analysis contains the
progression-free figures 0.722 (0.520–1.002) and 0.921 (0.597–1.420). It does
not, and I was ready to write that the page had attributed them to the wrong
study. **The page attributes them correctly.** They belong to the reconstructed
patient-data comparison in *Cancers* 2023, which the sentence immediately before
introduces; "its one-stage model" refers to that study, not to the meta-analysis.
I read the pronoun and not the paragraph. Writing the correction from the finding
rather than from the source is the error this whole file is about, and it got
within one step of being committed by the person writing the file.

---

## CORR-24 — a source that is on the page and not in the ledger

**The finding.** The *Cancers* 2023 reconstructed-patient-data comparison has its
own entry in the page's published source list, carries **eight figures** in the
body — three overall-survival pairs, two progression-free models, 1,827 patients
— and has **no entry in sources.json**. No source id. No access record. No
library entry. No row in the twenty-five we publish as our source count.

It is therefore invisible to every control this project has built: the ledger
does not know it exists, the quotation check cannot ask who opened it, the gap
list cannot report that we do not hold it, and preflight cannot block on it. It
is the S023 failure — "a quotation on the page with NO SOURCE ENTRY AT ALL" —
repeated on a larger scale, and this time on a study **an outside reviewer gave
us**, which the page says in as many words.

**What follows.** It needs an id, an access record that says plainly that nobody
here has opened it, and either acquisition or the demotion of every figure it
carries to what a retrieval returned. Until then the page prints eight numbers
whose provenance the ledger cannot describe.

---

## CORR-25 — a registry hazard ratio wearing a journal's byline

**The finding.** The page's source entry for PALOMA-2's final overall survival
(S010, *J Clin Oncol* 2024) reads: "53.9 vs 51.2 months, HR 0.956 (95% CI
0.777–1.177), one-sided P = .34".

The paper says: *"(HR, 0.96 [95% CI, 0.78 to 1.18]; stratified one-sided P = .34;
Fig 1A)"*. The strings 0.956, 0.777 and 1.177 do not occur anywhere in it.

They occur in the ClinicalTrials.gov posting, NCT01740427, which we also hold:
Overall Survival (OS): Primary Analysis — hazard ratio 0.956, lower 0.777, upper
1.177, p 0.337750. So the figures are real, correctly transcribed, and attributed
to the wrong document — the third time this week a registry number has been
printed under a publication's name.

**Also unmentioned.** The same posting carries a SECOND overall-survival analysis,
"Final Analysis", at HR 0.921 (0.755–1.124), p 0.208706. The page has never said
there are two. And 0.921 is, by coincidence, the point estimate of the *Cancers*
two-stage model quoted four hundred words earlier — the kind of collision that
manufactures a misattribution the next time somebody works from prose.

---

## CORR-26 — "sensitivity analysis" and "established"

Two words, both ours, both stronger than the paper.

The recovered-data analysis: the page calls it "the investigators' recovered-data
sensitivity analysis". The paper's heading is **"Revised Results Including
Recovered Data"**. It is not called a sensitivity analysis anywhere and is not
described as prespecified. The one thing the paper does call a sensitivity
analysis is a different analysis altogether, of time to chemotherapy.

"What PALOMA-2 **established** is that it did not demonstrate a survival benefit."
The authors establish nothing of the sort and say so: *"An imbalance in the number
of patients with unknown survival outcome between the treatment arms (13.3% v
21.2%, respectively) limited interpretation of OS results"*, and they name
crossover and a post-study CDK4/6-inhibitor imbalance — 11.8% versus 26.7% —
as confounders. "Did not demonstrate a survival benefit" is exactly right and
supported by *"OS was not significantly improved"*. "Established" is not.

---

## CORR-27 — full_text_held is wrong for the network meta-analysis

**The finding.** The stored copy of the network meta-analysis contains **zero
`<table>` elements**. Tables 1, 2 and 3 are caption-and-link stubs; the publisher
loads their bodies separately. The page quotes from Table 1 — a row label, "year
of updated data", and MONARCH 3 at HR 0.804 (0.637–1.015). The strings 0.804,
0.637 and 1.015 do not appear in what we hold, and neither does the row label;
the Methods call that variable "year of publication".

An outside reviewer did open the real table in the CORR-01 era and corrected us
from it, so the claim is not unfounded. But the ledger says full_text_held, and
what we hold is the article without the evidence the page cites.

`substance()` classified it full_text because a reference list and a discussion
are present. Both are. The test asks whether the prose is the paper's, and the
answer is yes; the claims rest on tables, and it never asked about those. **A
document can be the whole paper by every test we run and still be missing the
part our sentence depends on.** The check needs to know which part a claim
rests on, which is a harder question than any control here currently asks.

**Also.** The paper contradicts itself on follow-up: 73.3 months in the abstract,
**70.2 months** in the Results, same range either way (48.7–97.2). The page
prints 73.3 and does not say the paper says both.

---

# Third pass: the remaining seven. All nine are now read.

Every one of these was verified a second time by hand against the bytes before
being written here, because the second pass nearly published a correction that
was itself wrong.

## CORR-28 — a safety figure reported as its own floor

The page: diarrhoea "grade 3 in 8%". The VERZENIO label: *"Grade 3 diarrhea
occurred in 8% to 20% of patients receiving VERZENIO."* We printed the bottom of
a range as a point estimate and understated its top by a factor of two and a half.
The 81%–90% incidence and the 3,691-patient, four-trial denominator are right.

## CORR-29 — the wrong product, and a schedule cut in half

Two problems in the ribociclib monitoring passage.

The document we hold is the **KISQALI FEMARA CO-PACK** prescribing information —
ribociclib co-packaged with letrozole — not the standalone KISQALI label. The
phrase appears 85 times and every monitoring instruction is anchored to the
co-pack. The page cites it as KISQALI.

And the schedule is truncated. Label: *"Monitor LFTs every 2 weeks for the first
2 cycles, **at the beginning of each subsequent 4 cycles**, and as clinically
indicated"* — identically for CBC. The page stops at "the first two cycles",
which halves the apparent duration of the monitoring the passage exists to
describe. It also omits the QTcF < 450 ms gate on starting treatment.

The ECG claim is exactly right: before starting, and at approximately day 14 of
the first cycle. There is no cycle-2 ECG; searched.

## CORR-30 — we told readers a trial establishes nothing, and its record says why it stopped

The page: HARMONIA "stopped at 61 patients and never reported, so it establishes
nothing either way", in three places.

The registry record has a `whyStopped` field, and it reads: *"The study was
prematurely halted because enrollment was significantly delayed compared with the
original projections due to the evolving therapeutic landscape."*

Not futility. Not safety. Not a signal about either drug. A recruitment failure
in a changing treatment landscape. "It establishes nothing about the drugs" is
true and is a stronger, cleaner sentence when the reason is given; without it a
reader is left to supply their own, and the available ones are worse.

Two further errors in the same passage. The page says HARMONIA "was restricted to
the HER2-enriched intrinsic subtype". The record's inclusion criterion reads
*"HER2-E or Basal-like subtype as per central PAM50 analysis"*, and the record
lists three arms — the third is a paclitaxel ± tislelizumab exploratory cohort in
basal-like disease. The randomised ribociclib-versus-palbociclib comparison is
HER2-E; the trial as registered is not. And the record carries an ACTUAL
completion date of 26 March 2026, so "terminated" is right but "stopped early and
walked away" would not be.

## CORR-31 — P-VERIFY: an opening we invented, and a sentence we should have quoted

The page: "The Flatiron study says as much itself: it opens by describing its own
purpose as working in the absence of randomised trials that directly compare the
three."

It does not open that way. The abstract opens on inconsistent survival results
across the three randomised trials; the introduction opens on CDK4/6 inhibitors
plus endocrine therapy being standard of care. The phrase *"In the absence of
head-to-head RCTs"* appears mid-introduction and modifies **other authors'**
indirect comparisons, and again in the conclusion. The substance is supported;
the sentence about where and how the paper says it is not.

Meanwhile the paper contains the single most useful sentence on this page's whole
subject, and we do not quote it: *"The statistical non-significant differences in
OS between the three CDK4/6i in the current analysis **do not demonstrate
equivalence**; a formal noninferiority or equivalence analysis would be needed to
draw such conclusions."* A page arguing that nothing separates these drugs should
be carrying its largest source's own warning against reading its null as sameness.

Also unmentioned: median follow-up 33.0 months for palbociclib against 16.2 for
ribociclib and 21.4 for abemaciclib; 74% of the ribociclib arm censored; the
authors disowning their own median survival figures as unstable beyond 30 months.
And in three of thirty-one subgroups the abemaciclib-versus-ribociclib interval
excludes 1 — unadjusted for multiplicity, in a study not powered for it, but the
page's "does not separate them" is a claim about the overall analysis and should
say so.

## CORR-32 — a second erratum, found the same way as the first

The stored copy of MONALEESA-2's updated results is a **University of Edinburgh
Research Explorer landing page** — our records call it a PubMed abstract page —
and on it, under the paper's own outputs, sits:

    Correction: Updated results from MONALEESA-2, a phase III trial of
    first-line ribociclib plus letrozole ... Annals of Oncology, 13 Aug 2019

We print this paper's progression-free figures — 25.3 versus 16.0 months, HR
0.568 (0.457–0.704), all three verbatim correct — from a paper that carries a
published correction we do not hold and have not read.

That is the SECOND erratum discovered today, and both were found by looking at
bibliographic metadata rather than at the paper. Neither was found by any control
this project has built.

## Smaller, and still wrong

The IBRANCE file is section 5 of the prescribing information plus the medication
guide, not the whole label. Both claims we draw from it live in section 5, so
both are supported — but the ledger says we hold the label and we do not.

The 66% is a **Grade ≥3 decrease in neutrophil counts** in the palbociclib plus
letrozole arm. The page says "grade 3 or worse" neutropenia, collapsing a
laboratory measure into an adverse reaction.

The PALMARES-2 registry lists 24 Italian centres; the page says eighteen, from
the paper. Both may be right — the registry is the master protocol, the paper a
subset — but the registry cannot be cited for that number, and the registered
primary endpoint of that comparison is overall survival, while the page prints
its progression-free hazard ratios.
