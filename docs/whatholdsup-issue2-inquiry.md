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

1. **PALOMA-3 overall survival.** What did the ITT analysis report, at what
   alpha, in which population, and at which data cut? What does p=0.0221 in
   our corpus refer to? Both corpus claims need checking against the primary
   publication, and one of them is probably wrong or incomplete.
2. **PALOMA-2 overall survival.** Same treatment. The final OS analysis and its
   prespecified plan.
3. **Guideline position.** The corpus contains four claims opposing the
   proposition that ASCO expresses a preference among CDK4/6 inhibitors, none
   supporting. Do current NCCN and ASCO guidelines distinguish between them,
   and on what basis? This matters because "the guidelines treat them as
   interchangeable" would be the strongest counter to the whole piece.
4. **Ribociclib's QTc requirement.** One claim, unverified, that ECG monitoring
   is unique to ribociclib. If true it is a real cost on the other side of the
   ledger and the piece is unbalanced without it.

## Process gates

- [ ] `factcheck_draft.py --survey "CDK4/6 inhibitor overall survival
      differences palbociclib ribociclib abemaciclib"` — run BEFORE drafting.
      Rule 11: find the best coverage first. Somebody may have written this
      well already, in which case the piece changes shape or does not run.
- [ ] Open questions 1–4 resolved against primary sources.
- [ ] Draft written.
- [ ] `factcheck_draft.py` exits 0 across all six roles.
- [ ] Read against every rule in `whatholdsup-editorial-standard.md`,
      not recalled from memory. Rule 2 in particular: this piece is dense with
      hazard ratios and must not convert one into lives.
