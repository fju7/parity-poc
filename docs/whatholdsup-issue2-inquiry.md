# Issue two — inquiry brief (NOT a draft)

Status: **pre-draft.** The editorial standard requires `factcheck_draft.py
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

## Open questions — resolve BEFORE drafting

1. **PALOMA-3 overall survival.** Still open. What did the ITT analysis
   report, at what alpha, in which population, and at which data cut? What does
   p=0.0221 in our corpus refer to? The survey resolved PALOMA-2 and not this.
2. ~~PALOMA-2 overall survival.~~ Answered by the survey: HR 0.956, medians
   53.9 vs 51.2, non-significant, with a documented missing-data imbalance.
   Still requires SOURCE verification before publication.
3. **Guideline position.** The corpus contains four claims opposing the
   proposition that ASCO expresses a preference among CDK4/6 inhibitors, none
   supporting. Do current NCCN and ASCO guidelines distinguish between them,
   and on what basis? This matters because "the guidelines treat them as
   interchangeable" would be the strongest counter to the whole piece.
4. **Ribociclib's QTc requirement.** One claim, unverified, that ECG monitoring
   is unique to ribociclib. If true it is a real cost on the other side of the
   ledger and the piece is unbalanced without it.

## Process gates

- [x] `factcheck_draft.py --survey` — run 2026-08-27. It changed the piece.
      See SURVEY RESULT above.
- [ ] Decide whether the corpus needs the comparative literature added before
      anything is published from it. The network meta-analysis and the
      real-world study are load-bearing and absent.
- [ ] Open questions 1–4 resolved against primary sources.
- [ ] Draft written.
- [ ] `factcheck_draft.py` exits 0 across all six roles.
- [ ] Read against every rule in `whatholdsup-editorial-standard.md`,
      not recalled from memory. Rule 2 in particular: this piece is dense with
      hazard ratios and must not convert one into lives.
