# WHU-002 — the 1 September corrections

Run 3 of the page gate, taken past the cycle cap with the operator's approval and
the reason on the record, cost **$5.82** and returned five findings that are real.
Four are fixed here. The fifth needs a source nobody here can currently open.

The cap's premise — that runs past two stop paying — has now been falsified three
times running on this page. That is not an argument for running forever. It is
evidence that this page was wrong in more places than any of us assumed, and that
**several of the errors were introduced by the corrections**: HARMONIA's false
reason came in with the 30 August fix, the p-value conflation came in with the
31 August registry fix. A pass that fixes four things and introduces two is not
converging.

Labels CORR-14..CORR-17 are cited by `changes.json`.

---

## CORR-14 — we put our own observation under someone else's name

**The finding.** Raised by the gate on the EMAIL, as a SERIOUS FACT. The email said
the width of abemaciclib's interval "is itself a consequence of what that trial was
powered to detect — a point Tanguy and colleagues made formally in npj Breast Cancer
in 2018."

I reported to the operator that the email had overstated something the page stated
carefully. **That was wrong, and it was wrong in the way this file keeps recording.**
I compared the gate's summary of the page against the gate's summary of the paper.
I did not read either sentence against the source, because every automated route to
the paper — Europe PMC, three times over forty minutes — returned HTTP 429.

The operator went and got the full text.

**What the paper says.** It computes the statistical power of PALOMA-2, MONALEESA-2,
MONALEESA-7 and MONARCH-3 to reach significance on overall survival, using Freedman's
formula at a **two-sided** 5% type I error. Verbatim: *"PALOMA-2 and MONALEESA trials
have an almost similar power despite different allocation ratios, while MONARCH-3 has
a more limited power."* All four are under 70% power unless the median OS gain exceeds
twelve months. Its conclusion: *"if a significant OS improvement is observed in some
but not at all trials, this discrepancy might be more attributable to chance than to
a truly different drug efficacy."*

**What it does not say, anywhere: anything about confidence interval width.**

**And the page had the same error.** It read:

> where an interval ends is set by how many patients were enrolled, how many events
> occurred and how variable they were. It is a real measurement of how confidently
> each trial spoke. **Nor is this observation ours:** Tanguy and colleagues made it
> formally in npj Breast Cancer in 2018 ... arguing that MONARCH 3 was less powered
> than PALOMA-2 and MONALEESA-2 to detect a survival difference

The observation being handed over is the interval-width one, which is ours. The next
clause then describes their actual argument correctly, which is exactly what made the
sentence survive four days and one outside review: the misattribution is in the
handoff, not in the description.

**Disposition** — ACCEPT, in both documents.

**Change.** The page now says the observation is ours, says plainly that the paper
contains nothing about interval width, and states what the paper did establish, with
its own conclusion quoted (Q-18). The email now separates the two the same way. The
page also gains MONALEESA-7, which the paper includes and our characterisation had
dropped.

**S024 rewritten** with the paper's real findings, a `WHAT_IT_DOES_NOT_SAY` field, and
its declared interests: *"F.-C. Bidard is part of advisory boards and received research
grants (unrelated to this study) from Pfizer, Novartis, and Lilly."* This page runs a
disclosure-symmetry argument about P-VERIFY and PALMARES-2, and a source it leans on
for the power argument carries the same entanglement. Recorded; not yet on the page.

Access state **human_read**, by the operator, on 2026-09-01 — the first time anyone
here had opened it.

---

## CORR-15 — a true conclusion with a false reason under it

**The finding.** SERIOUS FACT. The page said of the two head-to-head trials:

> Neither is first line with an aromatase inhibitor, which is why neither contradicts
> the guideline sentence.

HARMONIA's registry record lists its arms as **"Ribociclib + Letrozole OR Fulvestrant"**
and **"Palbociclib + Letrozole OR Fulvestrant"**, and it enrolled first-line patients.
Letrozole is an aromatase inhibitor. Read from the ClinicalTrials.gov v2 API,
NCT05207709, `armsInterventionsModule`, on 1 September.

The conclusion is right and the reason we published for it is false. That is worse than
a visible error: nothing downstream looks wrong, and the first person to check is a
reader opening the registry.

**What actually holds** is in the trial's own title: HARMONIA was restricted to the
**HER2-enriched intrinsic subtype**, a molecularly selected population, not the
unselected HR+/HER2− population the guideline sentence describes. Shaaban is second
line with fulvestrant.

This reason entered with the 30 August correction (CORR-01), which was itself fixing a
worse error. It was never checked against the registry, although the registry was
already being read for that trial's dates and enrolment on the same day.

**Disposition** — ACCEPT.

**Change.** The page gives the real reason, says what it said before, and says that a
reader opening the registry would have found it first.

---

## CORR-16 — an endpoint downgraded

**The finding.** SERIOUS FACT, from the inference role. The page called PALMARES-2's
overall survival "an exploratory endpoint". NCT06805812's registry record lists
**Overall Survival (OS) as the study's primary outcome**, with real-world
progression-free survival, time to next treatment and time to chemotherapy secondary.
Read from the API on 1 September.

The published paper treats rwPFS as primary *for that data cut*. We collapsed the
analysis's endpoint hierarchy into the study's, and in the direction that made the
survival signal easier to set aside.

**Disposition** — ACCEPT.

**Change.** The page says the endpoint is the study's registered primary and that what
is immature is this particular look at it.

---

## CORR-17 — the third time the same flattening

**The finding.** SERIOUS CONTRADICTION. A third sentence said the two head-to-head
trials "neither separated them". HARMONIA reported nothing. Two other instances of
this were fixed on 31 August; this one is in the summary section and was missed
because the wording differs.

**Disposition** — ACCEPT.

**Change.** One found no significant difference; the other stopped at 61 patients and
never reported, so it establishes nothing either way.

---

## Open, and not fixed here

**The Shaaban trial's primary endpoint.** The gate says twice — body and source note —
that the page calls it "response rate" when the paper's primary endpoint is **clinical
benefit rate**. CBR includes stable disease at ≥24 weeks and response rate does not, so
they are different endpoints, and in a piece whose whole argument is about being precise
concerning what trials were built to measure, this matters. Europe PMC has refused every
request for PMC11700305 today. **Not changed, because nobody here has read the sentence.**

Fifteen calibration findings are recorded and deliberately not acted on.

---

## CORR-18 — the correction that deleted something true

**The finding.** Not a finding about the page. A finding about how this page is
corrected, and it is the clearest instance yet.

On 31 August the fact-check gate objected that the source note's "randomisation
in **29 blocks** of four by opaque sealed envelope" could not be verified: no
source it reached stated a number of blocks. I reasoned that 29 is 116 divided
by four, concluded it was our own arithmetic printed as the paper's statement,
withdrew it, and wrote a note on the page saying so.

The paper, Materials and Methods, *Methods of randomization*, p. 3040:

> Legible patients were randomised into either arm **using 29 blocks with block
> size of four**. Randomization method was done with opaque sealed envelopes.

**The number was the paper's. The correction removed a true statement**, and
the note explaining the removal was itself false.

**Why it happened, exactly.** Nobody here had opened the paper. S017's access
record said `machine_read` — "whatever the search tool returned for this URL" —
and the correction was written from the gate's finding, which is prose *about* a
source, rather than from the source. When the operator supplied the PDF on
1 September the Methods section settled it in one line.

This is the same failure as the Tanguy misattribution six hours earlier, where I
compared the gate's summary of our page against the gate's summary of the paper.
Both were resolved the same way: a person went and got the document.

**Why no check would have caught it.** Every control in this repository asks
whether a claim on the page is supported. **Not one asks whether a deletion
was.** A pipeline that validates what the page says is structurally blind to
what a correction takes out — and a correction that removes a true sentence
leaves a page that passes every check, reads more cautious, and is less
accurate. It is recorded in `error_taxonomy.py` as its own class,
`DELETED_A_TRUTH`, with no check proposed, because the honest answer is that the
rule is the control:

    WRITE THE CORRECTION FROM THE SOURCE RECORD, NOT FROM THE FINDING.

Adopted 1 September at the operator's direction.

**Disposition** — ACCEPT. The withdrawal is reverted.

**Change.** "29 blocks of four" restored in both places, quoted from the paper
(Q-19). The source note now records that this page withdrew the paper's own
number on a finding, and why. S017 rewritten from the full text, access state
**human_read**.

---

## CORR-19 — the trial names one primary endpoint and powers on another

**The finding.** The gate said, as a SERIOUS FACT and twice over, that the page
calls the Shaaban trial "powered on response rate" when its primary endpoint is
clinical benefit rate. Reading the paper, **both statements are true and they
are about different sentences in it.**

Introduction, p. 3040:

> The primary objectives are to compare the **clinical benefit rate (CBR)**,
> quality of life and toxicity profiles of Ribociclib and Palbociclib. Secondary
> objectives were assessment of Progression free survival and Overall survival.

Sample size calculation, p. 3040:

> Sample size was calculated using Medcalc 15.8. **The primary outcome of
> interest is the overall response rate (ORR).** Previous studies found ORR was
> 55% in Ribociclib (MONALEESA 2) and 25% in Palbociclib (PALOMA 3). With an
> alpha error of 5% and study power of 80%... the sample size is 58 patients per
> group at least.

CBR counts stable disease at ≥24 weeks; ORR does not. They are different
endpoints. The paper names one as its objective and sizes the trial on the other.

**Disposition** — ACCEPT, as a disclosure rather than a correction. The page's
"powered on response rate" was accurate and incomplete; the gate's objection was
accurate and incomplete; the source disagrees with itself.

**Change.** The page now quotes both sentences and says plainly that the paper
names one endpoint and powers on the other. Recorded in S017 as
`ENDPOINT_DISCREPANCY`. Same shape as the network meta-analysis printing 73.3 in
its abstract and 70.2 in its results — the second time on this page that a
gate finding turned out to be a source contradicting itself, and the second time
the right answer was to print both.
