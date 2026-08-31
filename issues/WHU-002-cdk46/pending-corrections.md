# WHU-002 — corrections queued, not yet published

Held back deliberately. Each is verified and ready; they go out together in one
gated publish rather than one at a time, because a re-gate of this page costs
about $5 and four separate ones cost about $20 for the same page.

Nothing here is live yet. When it goes out it moves to `corrections.md`, which
is the history a reader sees.

## 1. The MONALEESA-7 entry cites PALOMA-2's registry number

**Status.** Written and verified on 2026-08-31, then reverted from the branch so
unrelated code could be pushed — the pre-push guard correctly refused a
published page changing without a publication record.

The MONALEESA-7 overall-survival source entry reads:

> confirmed independently in the trial's ClinicalTrials.gov results posting
> (NCT01740427), which annotates each log-rank p-value "1-sided p-value from
> the stratified log-rank test"

NCT01740427 is PALOMA-2. MONALEESA-7 is NCT02278120. The sentence carrying the
piece's central correction — that the direction of the test was in the registry
all along — points at a different trial's registry.

**And it is not a number to swap.** NCT02278120's own results posting gives the
overall-survival analysis as p = 0.00973, matching the figure the page already
prints, annotated "One-sided stratified log-rank test". Different wording, and
one analysis rather than "each log-rank p-value" — the quoted string is
PALOMA-2's annotation, carried across with the number. Renumbering alone would
leave a quotation attributed to a document that does not contain those words.

**The replacement text**, verified against the registry on 2026-08-31:

> confirmed independently in the trial's ClinicalTrials.gov results posting
> (NCT02278120), whose overall-survival analysis is posted with p = 0.00973 and
> the annotation "One-sided stratified log-rank test".

## 2. The network meta-analysis contradicts itself about its own follow-up

The page states the Scientific Reports network meta-analysis pooled seven trials
"at a median follow-up of 73.3 months", and notes the 48.7–97.2 month range.

That figure is the paper's **abstract**. Its results section says:

> The median follow-up was 70.2 months (range: 48.7–97.2 months).

Same range, different median. Verified 2026-08-31 against the full text at
PMC10850180. The page's figure is not wrong — it is what the abstract says —
but the page states it as a fact about the study without noting that the study
gives two answers.

**Why it matters here specifically.** This page's own standard, in its sources
section, is that "where a correction to one of those sources is known to us, it
is noted in that source's entry". An internal contradiction in a cited paper is
exactly that, and the page already applies the standard to the MONARCH 3
corrigendum.

**Suggested addition** to the Comparison source entry: note that the abstract
gives 73.3 months and the results section 70.2, over the same range, and that
the figure used here is the abstract's.
