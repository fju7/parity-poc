# Issue two — draft spine (NOT publishable prose yet)

Every figure below carries its verification status. Nothing marked SURVEY may
reach a published sentence; the gate's SOURCE role has to reach it first.

| Status | Meaning |
|---|---|
| **VERIFIED** | read off a primary document, or corroborated by independent sources this session |
| **SURVEY** | from `factcheck_draft.py --survey`, 2026-08-27. A search result. Not a fact yet |
| **NEEDED** | the argument requires it and we do not have it |

---

## Working title

**Three drugs, one class, and a grade that separates them**

Standfirst: A guideline body ranks one CDK4/6 inhibitor above the other two and
says why. The two studies that compare the three head to head find nothing to
separate them.

---

## The spine

### 1. The distinction, and who makes it

NCCN Breast Cancer v6.2026, first-line HR+/HER2− advanced disease: aromatase
inhibitor plus **ribociclib carries category 1**; the same combination with
**abemaciclib or palbociclib is category 2A**. The guideline states the reason —
the overall-survival benefit seen with ribociclib. **[VERIFIED — read off the
guideline, BINV-P 2 of 3 and the discussion at MS-61, 2026-08-28]**

The distinction is setting-specific and the piece must say so. With fulvestrant,
**ribociclib and abemaciclib are both category 1** and palbociclib is not.
**[VERIFIED]**

So the claim is narrow: *first-line with an aromatase inhibitor, ribociclib is
the only one at category 1.* Any broader statement is false.

### 2. What that grade rests on

A category 1 rating means high-level evidence and uniform panel consensus. Here
it rests on ribociclib's own trial showing an overall-survival benefit where the
other two did not show one in theirs.

**MONALEESA-2** (ribociclib + letrozole vs letrozole, first-line, postmenopausal,
HR+/HER2− advanced): 668 patients, 334 per arm. Median OS **63.9 months
(95% CI 52.4–71.0) versus 51.4 (47.2–59.7)**, **HR 0.76 (95% CI 0.63–0.93),
two-sided P = 0.008**, at a median follow-up of 80 months. Overall survival was
a key secondary endpoint. **[VERIFIED — three independent reports agree, and one
states the two-sidedness explicitly. 2026-08-28]**

**This result is not weak and the article must not imply it is.** A 12.5-month
median difference, 668 patients, nearly seven years of follow-up, and a P value
an order of magnitude inside the conventional threshold. Whatever else is true,
ribociclib plus letrozole beat letrozole alone on survival, convincingly.

*[NEEDED, not blocking: the prespecified alpha boundary for the OS analysis. None
of the three sources gives it. P = 0.008 clears any conventional boundary, so the
comparison below is fair without it — but the piece should not assert a boundary
it has not seen.]*

### 2b. The four trials

Two tables, because on 2026-08-28 they stopped agreeing.

**Table A — as read off the guideline, 2026-08-28.** This is what the first
version of the page printed. No page locator was written down at the time, which
is the reason the disagreement below is still open: the category statement was
cited to BINV-P 2 of 3 and MS-61, and this table was cited to nothing.

| Trial | Drug + AI | PFS | OS | OS significant |
|---|---|---|---|---|
| MONARCH 3 | abemaciclib | NR vs 14.7 mo — HR **0.54** (0.41–0.72) | 66.8 vs 53.7 mo — HR **0.80** (0.64–1.02) | no |
| MONALEESA-2 | ribociclib, postmenopausal | 25.3 vs 16.0 mo — HR **0.56** (0.45–0.70) | 63.9 vs 51.4 mo — HR **0.76** (0.63–0.93) | yes |
| MONALEESA-7 | ribociclib, pre/perimenopausal | 23.8 vs 13.0 mo | 58.7 vs 48.0 mo — HR **0.76** (0.61–0.96) | yes |
| PALOMA-2 | palbociclib | 24.8 vs 14.5 mo — HR **0.58** (0.46–0.72) | 53.9 vs 51.2 mo — HR **0.96** (0.78–1.20) | no |

**Table B — the trial publications' own figures, each cell naming its
analysis. [VERIFIED against primary sources, 2026-08-28.]** This is what the page
prints now. The earlier version of this table claimed "the latest analysis each
reports", which the second gate run destroyed: these trials have reported four
and five times each, and "latest" is not one thing. Name the analysis instead.

| Trial | PFS | OS |
|---|---|---|
| MONARCH 3 | **primary, JCO 2017**: not reached vs 14.7 mo, HR **0.54** (0.41–0.72), P = .000021 | **final, 8.1 y, Ann Oncol 2024**: 66.8 vs 53.7 mo, HR **0.804** (0.637–1.015), P = **.0664** — **not significant** |
| MONALEESA-2 | **updated, Ann Oncol 2018**: 25.3 vs 16.0 mo, HR **0.568** (0.457–0.704), P = 9.63×10⁻⁸ | **final, 80 mo, NEJM 2022**: 63.9 vs 51.4 mo, HR **0.76** (0.63–0.93), two-sided P = **0.008** — **significant** |
| MONALEESA-7 | **primary, Lancet Oncol 2018**: 23.8 vs 13.0 mo, HR **0.55**, P < .0001 *(CI still NEEDED)* | **protocol-specified, 34.6 mo, NEJM 2019**: not reached vs 40.9 mo, HR **0.712**, P = **.00973** — **significant**, crossed the prespecified stopping boundary.<br>**exploratory, 53.5 mo, Clin Cancer Res 2022;28:851**: 58.7 vs 48.0 mo, HR **0.76** (0.61–0.96) |
| PALOMA-2 | **primary, NEJM 2016**: 24.8 vs 14.5 mo, HR **0.576** (0.463–0.718), P < .0001 | **final, 90.1 mo, JCO 2024 / PMC10950136**: 53.9 vs 51.2 mo, HR **0.956** (0.777–1.177), one-sided P = .34 — **not significant**. Missing survival status 13.3% vs 21.2%; recovered-data sensitivity analysis 9.2% vs 11.7%, HR **0.92** (0.76–1.12), P = .21 |

Also recorded, because the second run asked for them and the page now shows them:

- **PALOMA-2 extended follow-up PFS** (37.6 mo, Breast Cancer Res Treat 2018): 27.6 vs 14.5 mo, HR 0.563 (0.461–0.687). Not used — the page uses each trial's primary PFS, which is the analysis every one of them was powered for and the analysis the argument is about. **[VERIFIED]**
- **MONARCH 3 final PFS** (npj Breast Cancer 2018): 28.18 vs 14.76 mo, HR 0.540 (0.418–0.698). **Updated** subgroup analysis (2018 cutoff): 28.2 vs 14.8 mo, HR 0.525 (0.415–0.665). Ann Oncol 2024 restates PFS at 8.1 y as 29.0 vs 14.8, HR 0.535 (0.429–0.668). Four MONARCH 3 PFS readouts exist. **[VERIFIED]** — and this is why the table names its analysis.
- **The robustness claim now on the page:** across every published PFS analysis of all four trials, every hazard ratio falls between **0.52 and 0.58**. Checked against the eight readouts above. **[VERIFIED]**
- **The 97% overlap** is ours. On the rounded bounds the page shows (0.63–0.93 inside 0.64–1.02) it is 0.29 ÷ 0.30 = 96.7%; on the unrounded published bounds (0.637, 1.015) it is 0.293 ÷ 0.30 = 97.7%. The page prints 97% and shows both. **[VERIFIED — our arithmetic, stated on the page so a reader can redo it]**

**[RESOLVED 2026-08-28 — the guideline is accurate. We were not.]** Fred read
v6.2026 and quoted its sentences. Every figure in Table A is the guideline's,
quoted correctly, and every one of the guideline's is defensible:

| cell | guideline prints | what it is | verdict |
|---|---|---|---|
| MONARCH 3 PFS | "median not reached vs 14.7 months; HR, 0.54; 95% CI, 0.41–0.72" | the **2017 primary analysis**, verbatim — JCO 2017 gives exactly 0.54 (0.41–0.72), P = .000021 | guideline correct |
| MONALEESA-2 PFS | "25.3 vs 16.0 months; HR 0.56; 95% CI, 0.45–0.70" | the **2018 updated analysis**, 0.568 (0.457–0.704), **truncated** to two decimals rather than rounded | guideline correct, precision convention differs from ours |
| PALOMA-2 OS | "53.9 vs 51.2 months; HR, 0.96; 95% CI, 0.78–**1.2**" | the final analysis, 0.956 (0.777–1.177), upper bound to **one** decimal | guideline correct |

So the three charges dissolve, and what is left is two mistakes of ours:

1. **We printed 1.20 where the guideline printed 1.2.** One character, and it
   asserts a precision the source did not claim — in the one sentence of the
   article that is *about* where an upper bound falls. The publication's figure
   is 1.177, which is 1.18, not 1.20.
2. **We put registrational readouts in a table of final analyses.** The
   guideline cites MONARCH 3's 2017 PFS, which is what a guideline does. We
   copied that row into a table whose OS column carries the 2024 final analysis,
   so one line of the page compared a 2017 PFS against a 2024 OS. This is
   `WRONG_READOUT_COMPARISON`, recorded four times as a fault of the gate's
   SOURCE role and committed here for the first time by us.

The page now carries Table B throughout: each trial's PFS and OS drawn from the
same, latest analysis, rounded rather than truncated, with the exploratory status
of MONALEESA-7's OS stated.

### 2c. Scope — settled by gate run 3, 2026-08-28

**The comparison is the three postmenopausal aromatase-inhibitor trials.**
MONARCH 3, MONALEESA-2 and PALOMA-2. Those are the three the guideline grades
against each other, and they are the only three that can be set side by side
without doing the thing this piece exists to criticise.

**MONALEESA-7 is a different trial in a different population.** Pre/perimenopausal
women on ovarian suppression, with an aromatase inhibitor **or tamoxifen**. Run 3
found it sitting on the interval chart beside the other three under the heading
"Overall survival, first-line" — a cross-trial comparison across populations, in
a piece whose second half warns against cross-trial comparison. It is off the
chart. It stays in the table, labelled, as supporting evidence.

Two consequences the same finding forced:

- **"The one first-line OS result in the class that reached significance"** was
  false as written. MONALEESA-7 also reached significance for first-line OS. It
  is true only of the three postmenopausal AI trials, and now says so. Recorded
  twice on the page, fixed twice. **[VERIFIED]**
- **The four p-values are not on one scale and were printed in one column.**
  MONALEESA-2: two-sided P = 0.008 against a conventional threshold. MONALEESA-7:
  **P = .00973 at an interim, against a prespecified group-sequential stopping
  boundary of P = .01018** — a stricter test than 0.05 and a different one.
  PALOMA-2: one-sided P = .34. **[VERIFIED — boundary confirmed, ASCO Post,
  10 October 2019.]** *[NEEDED, not blocking: whether MONALEESA-7's p is stated
  one-sided in NEJM 2019. The page does not assert sidedness for it, because we
  have not read that sentence. It states the boundary instead, which is what we
  have and is the more useful fact.]*

The page now carries a warn box saying the p-values cannot be ranked and that
each supports only the binary its own trial reported.

**Note for the piece:** there is no finding against the guideline here, and the
draft must not reach for one. Three separate charges against NCCN have now been
tested in this issue and all three failed. That is worth one honest sentence in
the published piece and no more.

### 2d. Added by gate runs 4-6, 2026-08-28

**PALMARES-2** (Annals of Oncology, April 2025; 1,982 patients, 18 Italian
centres, IPTW). Real-world **progression-free** survival:

| comparison | aHR | 95% CI | p |
|---|---|---|---|
| abemaciclib vs palbociclib | 0.76 | 0.63–0.92 | 0.004 |
| ribociclib vs palbociclib | 0.83 | 0.73–0.95 | 0.007 |
| **abemaciclib vs ribociclib** | **0.91** | **0.73–1.14** | **0.425** |

OS was exploratory and immature (464 events): abemaciclib vs palbociclib HR 0.85
(p=0.014), ribociclib vs palbociclib 0.83 (p<0.001). **[VERIFIED 2026-08-28 —
two independent secondary reports of the Annals paper agree on all three CIs.
Note: the ASCO 2024 conference presentation of the same study gave 0.91
(0.70–1.19) for abemaciclib vs ribociclib. The page uses the published figures
and says so, because the gate flagged our number against the conference one —
sixth occurrence of WRONG_READOUT_COMPARISON.]**

**Flatiron cohort, corrected.** The page previously gave only p-values and called
PALMARES-2 "the largest". Both wrong. Flatiron is **9,146** patients — 6,831
palbociclib, 1,279 ribociclib, 1,036 abemaciclib — and compares **overall**
survival: ribociclib vs palbociclib 0.98 (0.87–1.10, P=0.7531); abemaciclib vs
palbociclib 0.95 (0.84–1.08, P=0.4292); **abemaciclib vs ribociclib 0.97
(0.82–1.14, P=0.6956)**. **[VERIFIED — PubMed 39754979]**

**The reconciliation, which is the finding.** The two real-world studies are
routinely described as disagreeing. They do not: **Flatiron measured overall
survival, PALMARES-2 measured progression-free survival.** A drug can delay
progression without extending life. Both find nothing between abemaciclib and
ribociclib.

**MONARCH 3's threshold was .034, not .05.** The SABCS 2023 presentation states
the cumulative two-sided type I error of 0.05 was maintained by Lan-DeMets with
an O'Brien-Fleming spending function, alpha split with the visceral-disease
subgroup, leaving **0.034** at the final OS analysis. P = .0664 missed it — and
would have missed .05 too, which the page says explicitly so nobody reads this
as a rescue. It also settles that MONARCH 3's p-values are **two-sided**.
**[VERIFIED — SABCS 2023 GS01-12 slide deck]** *[STILL NEEDED: the direction of
MONALEESA-7's test. Not stated in any source reached. The page says so.]*

**The three labels.** **[VERIFIED — US prescribing information, 2025]**

- **Ribociclib** (KISQALI): ECG before starting and at ~day 14 of cycle 1;
  serum electrolytes before starting and at the beginning of each of the first
  6 cycles; LFTs every 2 weeks for 2 cycles, then each 4 cycles; CBC likewise.
- **Abemaciclib** (VERZENIO): venous thromboembolic events in **2% to 5%** of
  patients across the metastatic trials, with monitoring required; diarrhoea in
  **81% to 90%** of 3,691 patients across four trials, grade 3 in **8% to 20%**.
- **Palbociclib** (IBRANCE): neutropenia in **80%** of PALOMA-2 patients, grade
  ≥3 in **66%**; CBC on day 15 of each of the first two cycles and at the start
  of every cycle.

This replaced the claim that ribociclib's cardiac requirement was "the one
documented difference" and "runs the other way from the grade" — a SELECTIVE
omission the gate caught twice in one run. It also makes the ending better: the
three burdens do not line up with the grade in any direction, which is a
stronger statement than the one it replaced.

**Fulvestrant, confirmed by direct reading 2026-08-28.** Fulvestrant + ribociclib
category 1; fulvestrant + abemaciclib category 1; fulvestrant + palbociclib not.
The guideline's stated reason: *"Since ribociclib and abemaciclib in combination
with fulvestrant have shown OS benefit (in MONARCH 2 and MONALEESA-3 trials),
these two regimens are listed as category 1 options."* **[VERIFIED — read off v6.2026 on 2026-08-28 and again on 2026-08-29, after the gate disputed it. The gate's SOURCE role reported that palbociclib is also category 1 with fulvestrant; it is not, and the role could not open v6.2026 — its own notes in the same run say v4.2026 was the latest it could reach. Declined in draft_decisions.json with the guideline's own sentence quoted.]** This is now the centre of both the page and the email: abemaciclib is
category 1 in one setting and 2A in another, on one standard consistently
applied. The grade records which trial produced a significant survival result,
and the guideline says so itself.

**PALOMA-2's sensitivity analysis, restated.** The page said the recovered-data
analysis meant "the result did not move" (0.96 → 0.92). The gate pointed out
that a piece arguing four hundredths separates a category 1 from a category 2A
cannot call four hundredths no movement. It now says the point estimate moved and
the conclusion did not. **[VERIFIED — PMC10950136]**

### 2e. Added by gate runs 7-9, 2026-08-28

**P-VERIFY, named and sourced.** The 9,146-patient US cohort has a name: the
**Palbociclib Verifying Evidence of Real-world Impact** study. Its SABCS 2024
poster states: *"This study was funded by Pfizer Inc."* Pfizer makes palbociclib.
**[VERIFIED — study's own poster]** A second paper from the same cohort (ESMO
Open, Sept 2025; PubMed 40896879) reports real-world progression-free survival
and also finds no significant differences; the PFS2 analysis gives HR 0.95-0.99,
all P > .42, medians 35.8 / 41.7 / 35.6 months. **[VERIFIED]**

**The reconciliation was wrong and has been withdrawn.** The page had said the
two real-world studies did not really disagree because they measured different
endpoints. Both programmes reported both endpoints. **They contradict each other
on palbociclib**, and the page now says so and adds it to Not established. This
was the fourth tidy construction of the day that the evidence did not support,
and the only one that survived long enough to be published to a gate.

The funding fact is reported as a fact with an explicit refusal to draw an
inference from it. Two contradictory studies, one industry-sponsored and one
academic; the reader is told which is which and nothing more is claimed.

**What survives: on abemaciclib vs ribociclib, nothing separates them anywhere.**
NMA: no significant difference. P-VERIFY (OS): 0.97 (0.82-1.14), P = 0.6956.
PALMARES-2 (PFS): 0.91 (0.73-1.14), p = 0.425. That is the comparison the
category difference rests on, and it is the one comparison every study agrees on.

### 2f. The absolute scale — Fred's note, 2026-08-28

A hazard ratio is not a probability and not a percentage of people. HR 0.80 does
not mean 20% fewer deaths. It is a ratio of instantaneous rates over follow-up,
averaged, and it conceals any change in that ratio over time. The page now says
this in as many words, and gives the absolute figures:

| Trial | Median OS | Difference | HR | Category |
|---|---|---|---|---|
| MONARCH 3 (abemaciclib) | 66.8 vs 53.7 mo | **13.1 mo** | 0.80 | 2A |
| MONALEESA-2 (ribociclib) | 63.9 vs 51.4 mo | **12.5 mo** | 0.76 | **1** |
| PALOMA-2 (palbociclib) | 53.9 vs 51.2 mo | 2.7 mo | 0.96 | 2A |

**[VERIFIED — arithmetic on figures already sourced in Table B above.]**

On the absolute scale the category 2A drug's trial reported the larger figure.
Six-tenths of a month, across trials with different patients and follow-up, is
noise — which is the point: the two are indistinguishable on the absolute scale
as well as the relative one, and the ordering happens to run the other way from
the grade.

The page carries two warnings with that table, both aimed at us: these are
medians and not lifespans, and comparing medians across trials is the same
cross-trial move the piece criticises elsewhere. It is an illustration of scale,
not a comparison of drugs.

### 3. What happens when you compare them directly

**Nobody has run the head-to-head randomised trial.** The guideline says so
itself, and says it accurately. **[VERIFIED — the guideline's sentence, read
2026-08-28. The claim that it overstated the gap was withdrawn 2026-08-28; see
section 4.]**

Two studies compare the three anyway:

- **Network meta-analysis** (Elliott et al., *Scientific Reports* 2024): seven
  phase III RCTs, 4,415 patients, 73.3 months median follow-up. No statistically
  significant pairwise OS difference between palbociclib, ribociclib and
  abemaciclib. **[VERIFIED 2026-08-28 — nature.com/articles/s41598-024-53151-8.
  Caveat, now on the page: it predates MONARCH 3's final OS analysis and used the
  interim HR 0.754 where the final is 0.804. Its direction does not turn on that
  one input, but the input is stale.]**
- **Real-world weighted comparison** (Flatiron cohort, *Annals of Oncology*
  2025, stabilised IPTW): ribociclib vs palbociclib aHR 0.98 (P=0.75);
  abemaciclib vs palbociclib 0.95 (P=0.43); abemaciclib vs ribociclib 0.97
  (P=0.70). **[VERIFIED 2026-08-28 — PMC11758200. Note for section 4: the paper
  frames its own purpose as working "in the absence of RCTs to directly compare"
  the three. It does not call itself a direct comparison.]**

Neither is a randomised head-to-head trial, and the piece must not pretend
otherwise. What they are is the best comparative evidence that exists, and both
point the same way: no separation.

### 4. WITHDRAWN — the sentence that did not give the game away

**Withdrawn 2026-08-28, after the gate. This section was the article's intended
centre. It does not hold.**

What it said: the guideline records that the three have not been directly
compared in **clinical** trials; the Flatiron cohort *is* a direct comparison of
all three, not randomised but direct; therefore the guideline overstates how
little comparative evidence exists.

Why it fails: in guideline language "directly compared in clinical trials" means
a randomised head-to-head trial. That is the conventional reading, and it is the
reading the Flatiron authors themselves use — their paper opens by describing its
own purpose as working *"in the absence of RCTs to directly compare"* the three.
The argument took a term of art, substituted a broader definition of our own,
and then charged the source with overstating on the strength of our definition.
Every fact in the paragraph was true and the accusation still did not hold.

Three of the gate's six roles flagged it independently — ADVOCATE, INFERENCE and
COVERAGE — which is what a real defect looks like as against a calibration
wobble.

**This is the second time in two issues.** Issue one accused the coverage of
passing off an earlier trial's figures without checking a single outlet. Recorded
as `SOURCE_FAULTED_ON_OUR_OWN_DEFINITION` in
`backend/tests/fixtures/factcheck_known_errors.json`, and seeded as `s15` in the
recall fixture so it is measured from now on.

What replaces it on the page: the guideline is accurate as written, and what the
two comparisons add is not a correction to it but the only evidence there is on a
question it correctly records as untested. That is a smaller claim. It is also
one we can defend.

### 5. Why the individual trials look different from each other

The case for a real difference between these drugs rests on their trials
diverging. They do — but on things that are not the drugs.

- **PALOMA-2** (palbociclib, first-line): final OS HR 0.956, medians 53.9 vs
  51.2 months. No benefit. The investigators' own caveat: interpretation is
  limited by a large and disproportionate imbalance in missing survival data
  between arms — unknown survival status in 13.3% of the palbociclib arm and
  21.2% of the placebo arm. **They then ran a recovered-data sensitivity
  analysis** cutting the unknowns to 9.2% and 11.7%: HR 0.92 (0.76–1.12),
  one-sided P = .21. The result did not move. **[VERIFIED 2026-08-28 —
  PMC10950136. The page cited the defect without the remedy until this revision,
  which overstated the defect and hid that the authors' own fix agrees with us.]**
- **MONARCH 3** (abemaciclib, first-line): final OS HR 0.804 (95% CI
  0.637–1.015, P=0.0664) on a 13.1-month median improvement — 66.8 vs 53.7
  months — in 493 patients, underpowered for the endpoint. **[VERIFIED
  2026-08-28 — Ann Oncol 2024, S0923-7534(24)00139-X, via ASCO Post. Not
  statistically significant, and the page now says so.]**
- **PALOMA-3** (palbociclib, second-line): the protocol analysis gave medians
  34.9 vs 28.0, HR 0.81 (0.64–1.03), **P = 0.09 two-sided against a prespecified
  threshold of 0.047** — it missed. A later unplanned exploratory analysis at
  longer follow-up gave the same point estimate with an interval clearing 1
  (0.65–0.99) **and no test attached at all**. **[VERIFIED this session against
  three independent reports]**

**The comparison that is actually being made.** Every one of these trials tested
a CDK4/6 inhibitor against endocrine therapy alone. None tested one against
another. MONALEESA-2 beat letrozole by a wide, clean margin. PALOMA-2 and
MONARCH 3 did not beat their controls significantly — one on 493 patients and
underpowered for the endpoint, one with a missing-data imbalance its own
investigators flagged.

A drug that beat placebo by more than another drug beat placebo, in separate
trials with different populations, different follow-up and different data
quality, has not been shown to beat that other drug. That inference is the whole
of the category difference, and it is not an inference the evidence supports.

It is also testable, and it has been tested twice — by the network meta-analysis
and the Flatiron cohort — and both times the difference does not appear.

### 6. Where the three genuinely do differ

Ribociclib is the only one whose label requires cardiac monitoring — ECGs before
starting and during treatment. **[SURVEY — brief records this as resolved
against the label; still needs SOURCE]**

This matters to the argument's honesty: the piece is not saying the drugs are
identical. It is saying the evidence does not establish that one works better,
while the monitoring burden — a real, documented difference — points the other
way from the grade.

---

## Established / not established

**Established**
- The category difference exists and the guideline states its reason [VERIFIED]
- No head-to-head randomised trial has been run [VERIFIED]
- The two direct comparisons that exist find no significant pairwise difference
  [SURVEY → must be VERIFIED before publication]
- Ribociclib alone carries a cardiac monitoring requirement [SURVEY]

**Not established**
- That any of the three is more effective than another
- That the category difference predicts a difference in outcome
- That the trials' divergent p-values reflect anything about the molecules
- Whether a head-to-head trial would find a difference. Nobody has run one

---

## What the reader is owed

Anyone taking one of these, or choosing between them, wants to know whether the
grade means their drug is worse. On the evidence: the grade reflects which trial
produced a survival result, not which drug produces better survival. That is a
statement about evidence, not a recommendation — the piece says nothing about
what anyone should take, and says so.

---

## Before this can be drafted as prose

1. SOURCE verification of every SURVEY figure above
2. Correct the corpus's PALOMA-3 p-value at source (task 34) — independent of
   this piece, but it is the same corpus this issue draws on
3. Register the issue in `publish.py` and create the case file properly
