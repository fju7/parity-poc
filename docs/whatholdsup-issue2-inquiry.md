# Issue two — inquiry brief (NOT a draft)

Status: **ready to draft.** Open questions resolved 2026-08-27. The editorial standard requires `factcheck_draft.py
--survey` to run before anything is written, and two factual questions below
must go through the SOURCE role first. Nothing here is settled.

Sourced from `backend/data/signal/propositions_breast-cancer-therapies.json`,
mined 2026-08-27 from the Parity Signal corpus of 207 scored claims.

---

## The claim under examination

**CDK4/6 inhibitors are a drug class, and the three approved members —
palbociclib, ribociclib, abemaciclib — are broadly interchangeable.**

This is the working assumption behind how they are prescribed, guidelined and
reported. It is not a fringe position and it is not obviously wrong. It has a
strong version, which is question 1 of the four.

## SURVEY RESULT — this brief's provisional conclusion was wrong

Run 2026-08-27, `factcheck_draft.py --survey`. Six careful treatments found,
three of them SERIOUS contradictions of the premise below. **These are search
results and not verified facts; every figure here still goes through SOURCE.**

Two studies compare the three drugs DIRECTLY, and neither is in our corpus:

- **Network meta-analysis** — Elliott et al., *Scientific Reports* 2024. Seven
  phase III RCTs, 4,415 patients, 73.3 months median follow-up. Reports **no
  statistically significant pairwise OS differences** between palbociclib,
  ribociclib and abemaciclib, despite the differing significance levels of the
  individual trials.
  https://www.nature.com/articles/s41598-024-53151-8
- **Real-world weighted comparison** — Flatiron Health cohort, *Annals of
  Oncology* 2025, stabilised IPTW. Ribociclib vs palbociclib aHR 0.98
  (P=0.75); abemaciclib vs palbociclib 0.95 (P=0.43); abemaciclib vs
  ribociclib 0.97 (P=0.70).
  https://pubmed.ncbi.nlm.nih.gov/39754979/

And the individual trials look different from how the corpus renders them:

- **PALOMA-2** final OS: HR 0.956, medians 53.9 vs 51.2 months — no benefit.
  The investigators' own caveat is that interpretation "is limited by the large
  and disproportionate percentage of patients with missing survival data
  between the treatment arms". 10% of the palbociclib arm versus 2% of placebo
  were still on treatment at final analysis.
- **MONARCH 3** final OS: HR 0.804 (95% CI 0.637–1.015, P=0.0664) — NOT
  significant, on a 13.1-month median improvement (66.8 vs 53.7 months), in a
  trial of 493 patients underpowered for the endpoint.
- **monarchE** (abemaciclib, early breast cancer, 2025): HR 0.842
  (0.722–0.981, P=0.027), significant — with a 7-year absolute difference of
  1.8% (86.8% vs 85.0%) and 52% of the control arm crossing over to a CDK4/6
  inhibitor after progression.

### What this means for the inquiry

The provisional conclusion drafted below — ribociclib significant in three
trials, abemaciclib in one, palbociclib contested — reads divergent
individual-trial p-values as evidence of a difference BETWEEN DRUGS. The
comparative evidence says it is not. Trials differ in power, in missing data,
in endocrine partner, in line of therapy and in crossover, and those
differences are sufficient to produce divergent p-values from drugs that are
indistinguishable on overall survival.

**The piece is therefore not "ribociclib is the one with the survival
evidence".** That is the intuitive reading, it is what the trial-by-trial
record looks like, and it appears to be wrong.

The piece the survey identifies as unwritten:

> No outlet has synthesised the three methodological caveats together —
> PALOMA-2's missing-data imbalance, MONARCH 3's underpowering, monarchE's 52%
> crossover — to explain why the indirect and real-world comparisons find no
> inter-drug OS difference even when individual trial p-values diverge.

That is a better piece and a more useful one. A patient told their drug is the
one without survival evidence has an interest in knowing that the direct
comparisons find no difference, and in why the trials nonetheless disagree.

### What this means for the method

Our corpus contains none of the comparative literature above. P3 was the
strongest proposition the miner found in this topic — 17 bearing claims, 15 to
2, direction stable across runs, magnitude quantified, mean evidence 3.64 — and
it points somewhere the wider literature does not support.

**A corpus mined for propositions will confidently support a proposition the
outside literature refutes, if the corpus lacks the studies that do the
refuting.** Every check we have built would pass it: the status is stable, the
sides do not reverse, the evidence is quantified, the claims are individually
true. Coverage of the evidence base is an axis we have not measured at all, and
it is upstream of everything we have.

Consequence: COVERAGE must run before MINING, not only before drafting.

---

## The provisional reading, kept for the record

Everything below was written before the survey and is preserved so the
correction is visible rather than tidied away. Read it as what the corpus
alone suggested.

## 1. The strongest version of the claim

All three drugs improve progression-free survival when combined with an
aromatase inhibitor in first-line HR+/HER2- metastatic breast cancer, at hazard
ratios that sit close together — roughly 0.54 to 0.58. That is a genuine
class effect, replicated across separate phase III programmes, and the corpus
supports it: 12 claims bear on it, all 12 supporting, mean evidence quality
4.04, the highest-scoring proposition in the topic.

A clinician choosing among them on efficacy grounds has good reason to treat
the PFS evidence as equivalent.

## 2. What the evidence supports

Overall survival is where they separate, and the corpus is consistent about it:

- MONALEESA-2 — ribociclib + letrozole, median OS 63.9 vs 51.4 months,
  HR 0.76, p=0.004
- MONALEESA-3 — ribociclib + fulvestrant, HR 0.724, p=0.00455
- MONALEESA-7 — ribociclib + endocrine therapy, 42-month OS 58.7% vs 45.9%,
  HR 0.71, p=0.00973
- MONARCH-2 — abemaciclib + fulvestrant, median OS 46.7 vs 37.3 months,
  HR 0.757, p=0.0137
- Pooled meta-analysis across phase III CDK4/6 trials — OS HR 0.80
  (95% CI 0.73–0.88)

Seventeen claims bear on the proposition that ribociclib's OS benefit is more
consistent across its programme than palbociclib's across PALOMA. Fifteen
support it, two oppose. Seven carry a confidence interval, p-value or event
counts. The direction held across independent measurement runs.

## 3. What weakens or qualifies it

**There are no head-to-head trials.** One claim states it plainly: no trial has
compared palbociclib, ribociclib and abemaciclib against each other, and the
indirect comparisons that exist come from network meta-analyses carrying known
methodological limitations. Every statement about one being "more consistent"
than another is a comparison across trials that differ in population, endocrine
partner, line of therapy and follow-up.

This qualifier is load-bearing and belongs high in the piece, not in a footnote.

**And the corpus contradicts itself on palbociclib.** Two claims, both bearing
on the same proposition:

> "In the updated overall survival analysis of PALOMA-3, median OS was 34.9
> months in the palbociclib plus fulvestrant arm versus 28.0 months (HR 0.81,
> p=0.0221)."

> "PALOMA-2 and PALOMA-3 showed numerical but not statistically significant
> overall survival benefit for palbociclib combinations."

p=0.0221 clears the conventional two-sided threshold. These cannot both be
simply true as stated. The likely reconciliation involves analysis population
or a prespecified alpha the nominal p did not meet — **but that is a guess and
must be resolved against the primary sources before a word is written.** See
the open questions.

That contradiction is not an embarrassment in the data. It is the most
interesting thing here: two answers to "did palbociclib improve survival" are
in circulation, and which one a reader meets depends on which analysis they
happen to encounter.

## 4. What a reasonable person can conclude

Provisionally, pending the checks below:

The three CDK4/6 inhibitors look equivalent on the endpoint most trials were
designed around, and do not look equivalent on the endpoint patients ask about.
Ribociclib has shown a statistically significant overall survival benefit in
three separate phase III trials; abemaciclib in one; palbociclib's position is
genuinely contested and depends on which analysis is cited. Nobody has run the
trial that would settle it, and nobody is likely to.

That is not "palbociclib does not work" — its PFS benefit is large, replicated
and not in dispute. It is that a class treated as interchangeable is
interchangeable on one endpoint and not demonstrably so on another, and a
patient has an interest in knowing which.

---

## Open questions — RESOLVED 2026-08-27, against primary sources

Resolved by reading the sources, not by searching for summaries of them. Every
figure below still goes through SOURCE before publication; what is settled here
is which document says what.

### 1. PALOMA-3 overall survival — resolved, and it is the piece

There are two analyses and they give different answers from the same hazard
ratio.

**The protocol-specified final analysis** (NEJM 2018, Pfizer's own release of
20 October 2018): median OS 34.9 months (95% CI 28.8–40.0) versus 28.0 (23.6–34.6),
**HR 0.81 (95% CI 0.64–1.03), one-sided p = 0.0429**. Pfizer's release says
plainly that this "did not achieve statistical significance at the prespecified
threshold."

**The later analysis** (Clinical Cancer Research 2022, data cut 17 August 2020,
393 events in 521 patients): median OS 34.8 versus 28.0, **stratified HR 0.81
(95% CI 0.65–0.99)** — and the paper reports **no P value at all**, because it
describes itself as a "final unplanned exploratory OS analysis."

Same point estimate, 0.81, both times. In the analysis that was planned, the
interval crosses 1 and the result misses its threshold. In the analysis that
was not planned, two more years of events pull the upper bound to 0.99 and the
interval clears the line — with no test attached to it.

**Our corpus's p = 0.0221 matches no published figure. RESOLVED 2026-08-28:
DROPPED. It is not to be published, quoted, or repaired.**

Traced to `category_audit_with_context.json`, claim
`30008938-02ac-4a52-ac5a-80b946ffa773`: *"In the updated overall survival
analysis of PALOMA-3, median OS was 34.9 months in the palbociclib plus
fulvestrant arm versus 28.0 months in the placebo plus fulvestrant arm (HR 0.81,
p=0.0221)."* The record carries the claim text and three categorisation votes
and **no source, no URL, and no document reference of any kind**. There is
nothing to trace it to.

Every P value PALOMA-3 has published for overall survival:

| Analysis | Result | P |
|---|---|---|
| Protocol-specified, stratified | HR 0.81, 34.9 vs 28.0 months | 0.09, two-sided |
| Protocol-specified, unstratified | HR 0.79 | 0.05 |
| Prespecified significance threshold | — | 0.047, two-sided |
| Endocrine-sensitive subgroup (n=410) | HR 0.72, 39.7 vs 29.7 months | not reported |
| 2022 updated exploratory | HR 0.806, 34.8 vs 28.0 months | none — no test attached |

0.0221 is not among them, and it is not a subgroup figure misattributed to the
whole population: the corpus pairs it with the whole-population medians and
HR 0.81, not the subgroup's 0.72. The earlier note that a one-sided p on the
exploratory analysis "would land near 0.022" was itself a guess, and the
exploratory analysis reports no test at all, so there is nothing for a one-sided
version of it to be.

**What the number does is the point.** The trial did not meet its endpoint —
P = 0.09 against a prespecified threshold of 0.047. The corpus says p = 0.0221,
"which is statistically significant," and proposition 2's entire
`why_it_could_be_false` is built on it. A single unsourced figure reverses a
trial's conclusion inside the corpus that drives our scoring.

That is a corpus defect, not a drafting one, and it needs correcting at source
in `category_audit_with_context.json` and
`propositions_breast-cancer-therapies.json` — not merely avoided here.

Sources: [NEJM 2018 as summarised by Nature Reviews Clinical
Oncology](https://www.nature.com/articles/s41571-018-0125-9);
[MDedge on the protocol analysis and the endocrine-sensitive
subgroup](https://www.mdedge.com/hematology-oncology/article/177741/breast-cancer/paloma-3-overall-survival-better-endocrine);
[Oncology News Central on the extended
follow-up](https://www.oncologynewscentral.com/conference-news/palbociclib-plus-fulvestrant-prolongs-survival-paloma-3-extended-follow-up).
The journals themselves (NEJM, AACR) and PubMed all refuse automated access, so
these are secondary reports of primary figures and must go through SOURCE with
that noted.

This is the same fault as issue one, in a different costume: a number that
answers a question the reader thinks it answers, and does not.

### 2. PALOMA-2 overall survival — answered by the survey

HR 0.956, medians 53.9 versus 51.2 months, non-significant, with a documented
missing-data imbalance (10% of the palbociclib arm still on treatment at final
analysis versus 2% of placebo). Still requires SOURCE verification.

### 3. Guideline position — resolved, and it cuts against the comparative evidence

NCCN does both things at once. It states that the CDK4/6 inhibitors "have not
been directly compared in randomized trials, and treatment selection should
consider efficacy, toxicity, comorbidities, monitoring requirements, and
patient preference" — and it lists **ribociclib plus an aromatase inhibitor as
category 1**, on the strength of the MONALEESA overall-survival results, while
**palbociclib and abemaciclib remain category 2A**.

So the guidelines do distinguish, on exactly the ground the comparative
literature does not support: divergent individual-trial p-values. That is not a
counter to the piece. It is the piece — the category difference is the
institutional form of the inference the network meta-analysis and the
Flatiron real-world comparison both fail to reproduce.

**Caveat, load-bearing: this is a secondary summary of NCCN v4.2026, not NCCN
itself, which is behind registration.** It must be confirmed against the
guideline document before a word of it is published. If the category ratings
are wrong the section collapses.

### STATUS 2026-08-28: CONFIRMED against NCCN v6.2026 — with three corrections

Confirmed by the operator against his own licensed copy of the guideline. Note
the version: **v6.2026, not the v4.2026 this brief cited.** Every reference to
v4.2026 in the published piece must be corrected.

**Confirmed:** on BINV-P (2 of 3), first-line, aromatase inhibitor + ribociclib
carries category 1; abemaciclib and palbociclib carry no marking, and the
guideline's stated convention is that unmarked recommendations are category 2A.
The discussion text says the same in words, and gives the reason: ribociclib's
combination with an AI is category 1 because of the overall-survival benefit
seen with it. That reason is the article — an institution assigning a higher
category to one drug on the strength of its own trial's survival result, in a
class whose members have never been compared against each other.

**Correction 1 — the version.** v6.2026, not v4.2026.

**Correction 2 — RESOLVED: the word is "clinical". Established by the operator
reading the printed line, 2026-08-28.**

Page 188 (MS-61), right column, the paragraph beginning "AI in combination with
CDK4/6 inhibitor", last sentence: the guideline says the CDK4/6 inhibitors have
not been directly compared in **clinical** trials.

**Why this is a paragraph of the article and not a footnote.** "Not compared in
randomized trials" would be narrow and true — no head-to-head RCT exists.
"Not compared in clinical trials" asserts that no direct comparison of any kind
has been done, and one has: the Flatiron weighted cohort in *Annals of Oncology*
compares all three directly, and finds no significant difference between any
pair. It is not randomised. It is a direct comparison.

So in the same passage where the guideline declines to distinguish the three
drugs on comparative grounds, it overstates the absence of the comparative
evidence — and its category ratings distinguish them anyway. The guideline
commits, in one sentence, the error this publication exists to describe.

**How this was settled, because the route matters.** A direct visual read of the
rendered page gave *clinical*. A PDF reader's assistant, asked three times, gave
*randomized* (with a quotation that is not on the page), then *clinical*, then
*clinical* — and by the third it was agreeing with a position relayed back to
it, so it was a loop rather than a witness. What settled it was a human reading
one line. That is the whole method: when a claim is load-bearing and the
instruments disagree, a person looks at the source.

The sentence is still never quoted in the published piece — NCCN content is
licensed and the facts are enough. The article reports what the guideline says,
in its own words, and cites the section.

**Superseded note — the quotation is not the words.** This brief quoted the
guideline as saying the inhibitors "have not been directly compared in
randomized trials, and treatment selection should consider efficacy, toxicity,
comorbidities, monitoring requirements, and patient preference." The guideline's
sentence is shorter and says *clinical* trials, not randomized trials; the
treatment-selection clause is not part of it. **Still to confirm: which word.**
It matters — "not compared in randomized trials" leaves room for the
non-randomised comparisons this piece is built on, and "clinical trials" does
not.

**Correction 3 — the uniqueness is setting-specific. Still to confirm.**
Ribociclib appears to be the only category 1 CDK4/6 inhibitor *first-line with
an aromatase inhibitor*. In the fulvestrant combinations, abemaciclib is
category 1 as well. If so, the claim the piece can make is narrower than
"ribociclib is the category 1 CDK4/6 inhibitor," and the narrower claim is the
only one to make.

**On quoting.** NCCN content is licensed; the category ratings are facts and
ours to report, the guideline's wording is not. Nothing from the document is to
be reproduced verbatim in the published piece without going through NCCN's
"Permission to Cite or Use NCCN Content" process. Paraphrase, cite the section
(BINV-P, and the discussion at MS-61), and move on.

What was tried, and what it is worth:

- **[OncoDaily's summary of v4.2026](https://oncodaily.com/oncolibrary/breast-oncology/breast-cancer-nccn-v4)**
  states exactly what this section states: ribociclib plus AI category 1 on the
  MONALEESA overall-survival results, abemaciclib and palbociclib plus AI
  category 2A, and the "have not been directly compared in randomized trials"
  sentence verbatim. **This is not corroboration.** This brief records no source
  for its NCCN summary, so OncoDaily may well *be* that source — in which case
  reading it back proves only that it says what it said. Matching a claim
  against its own origin is the shape of a check without the substance of one.
- **[Novartis, March 2023](https://www.novartis.com/us-en/news/media-releases/novartis-ribociclib-kisqali-only-category-1-preferred-first-line-treatment-option-hrher2-mbc-combination-ai-updated-nccn-clinical-practice-guidelines-oncology-nccn-guidelines)**
  states ribociclib was "the only Category 1 preferred CDK4/6i" first-line with
  an AI in v4.2023. Genuinely independent of OncoDaily, and worth something: it
  corroborates the *pattern* across three years and two sources. But it is the
  manufacturer of the drug it is describing, announcing its own advantage, and
  it gives no categories for palbociclib or abemaciclib. Using it to establish
  that ribociclib ranks above its competitors is precisely the sourcing this
  publication exists to criticise.
- **NCCN's own free materials do not carry the ratings.** The 2026 metastatic
  breast cancer congress deck on education.nccn.org covers HER2+ and
  triple-negative disease and gives no category designations for the
  first-line HR+/HER2- CDK4/6i combinations. The patient guidelines do not carry
  category ratings either. The full guideline needs registration.

**What has to happen.** NCCN registration is free for individuals. Someone with
an account opens Breast Cancer v4.2026 and reads off four things:

1. the category assigned to ribociclib + AI, first-line HR+/HER2- metastatic
2. the category assigned to palbociclib + AI, same setting
3. the category assigned to abemaciclib + AI, same setting
4. the "have not been directly compared" sentence, verbatim and in context

Until then this section cannot be published. Not softened, not attributed to a
secondary source — **not published**, because the argument is that an
institution drew a distinction the comparative evidence does not support, and
that argument is worthless if we have the distinction wrong.

There is a real observation sitting underneath this — the guideline that shapes
prescribing is not publicly readable — and it belongs in the piece only *after*
the ratings are confirmed, never as a substitute for confirming them.

### 4. Ribociclib's ECG requirement — resolved, and it is real

Ribociclib is the only one of the three whose label requires cardiac
monitoring. From the KISQALI prescribing information: "Perform ECG in all
patients prior to starting KISQALI" and "Repeat ECG at approximately Day 14 of
the first cycle, and as clinically indicated", with dose interruption at QTcF
480–500 ms, dose reduction above 500 ms, and permanent discontinuation if
QTcF > 500 ms or a > 60 ms change from baseline occurs with Torsades de
Pointes, syncope or serious arrhythmia. Serum electrolytes must be monitored
"prior to the initiation of KISQALI at the beginning of the first 6 cycles".

The other two labels require none of it:

- **IBRANCE (palbociclib)** — Warnings and Precautions are 5.1 Neutropenia and
  5.2 Embryo-Fetal Toxicity. QTc appears only under Clinical Pharmacology:
  palbociclib "had no large effect on QTc (i.e., >20 ms)".
- **VERZENIO (abemaciclib)** — Warnings and Precautions are diarrhea,
  neutropenia, interstitial lung disease, hepatotoxicity, venous
  thromboembolism and embryo-fetal toxicity. QTc appears only under
  Pharmacodynamics: abemaciclib "did not cause large mean increases (i.e.,
  20 ms) in the QTc interval".

So the claim in the corpus holds. The drug the guidelines rate highest is also
the only one that costs the patient a baseline ECG, a second ECG two weeks in,
and six cycles of electrolyte monitoring. That belongs in the piece, and it is
the reason the piece cannot end at "they are the same, take any of them".

---

## What the piece is, after the resolutions

Not "ribociclib is the one with the survival evidence" — the survey killed that.
Not "they are identical" either, because the monitoring burden is not identical
and the guideline categories are not identical.

The piece is: **three drugs that the direct comparisons cannot tell apart, a
guideline system that ranks them anyway, and one trial whose answer to "does
this drug help you live longer" depends on which of two analyses you happen to
read.** The methodological caveats — PALOMA-2's missing-data imbalance,
MONARCH 3's underpowering, monarchE's 52% crossover, PALOMA-3's planned versus
unplanned analyses — are what reconcile divergent p-values with no measurable
difference between the drugs. The survey found no outlet that has put them
together.

## Process gates

- [x] `factcheck_draft.py --survey` — run 2026-08-27. It changed the piece.
      See SURVEY RESULT above.
- [ ] Decide whether the corpus needs the comparative literature added before
      anything is published from it. The network meta-analysis and the
      real-world study are load-bearing and absent.
- [x] Open questions 1–4 resolved against primary sources, 2026-08-27.
      Q1 changed the piece; Q3 must be re-confirmed against NCCN itself;
      the corpus's PALOMA-3 p = 0.0221 must be sourced or dropped.
- [ ] Draft written.
- [ ] `factcheck_draft.py` exits 0 across all six roles.
- [ ] Read against every rule in `whatholdsup-editorial-standard.md`,
      not recalled from memory. Rule 2 in particular: this piece is dense with
      hazard ratios and must not convert one into lives.
