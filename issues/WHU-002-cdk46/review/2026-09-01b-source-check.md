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
